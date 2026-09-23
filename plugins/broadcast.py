# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Group Broadcast & Message Dispatcher
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import asyncio
import time
import logging
from pyrogram import Client, filters, errors
from pyrogram.enums import ChatType
import utils
from utils import ggr

# Komut kayıtları (Yardım menüsü için)
ggr.cmd(
    "ilet", 
    info="Yanıtlanan mesajı, doğrudan metni veya gönderilen medyayı tüm seçili gruplara iletir.", 
    usage=".ilet (veya mesaja yanıt: .ilet | veya medya altyazısına: .ilet [yazı])",
    category="Grup & İletim"
)
ggr.cmd(
    "iletmenu", 
    info="Grupları numaralandırarak listeler ve tek tıkla açıp kapatmanızı sağlar.", 
    usage=".iletmenu (veya hızlı: .iletmenu [numara])",
    category="Grup & İletim"
)

# Sabit güvenli aralık (kullanıcı isteği: ~0.8 sn)
ggr_ilet_bekleme = 0.8

# Hızlı numara erişimi için önbellek
ggr_son_listelenen_gruplar = []
SON_LISTELENEN_GRUPLAR = ggr_son_listelenen_gruplar



def get_kapali_gruplar():
    """Gönderim kapalı olan grup ID listesini döner."""
    cfg = ggr.get("ilet_kapali_gruplar", [])
    if not isinstance(cfg, list):
        cfg = []
    return cfg

def set_kapali_gruplar(yeni_liste):
    """Gönderim kapalı olan grup ID listesini kaydeder."""
    ggr.set("ilet_kapali_gruplar", list(set(yeni_liste)))


def is_group_active(chat_id):
    """Grup aktif mi (kapalı listesinde değilse aktiftir)."""
    kapali = get_kapali_gruplar()
    return int(chat_id) not in kapali


def toggle_group(chat_id):
    """Grup durumunu tersine çevirir (Açık -> Kapalı veya Kapalı -> Açık)."""
    kapali = get_kapali_gruplar()
    chat_id = int(chat_id)
    if chat_id in kapali:
        kapali.remove(chat_id)
        aktif = True
    else:
        kapali.append(chat_id)
        aktif = False
    set_kapali_gruplar(kapali)
    return aktif


CACHED_GROUPS = []
LAST_CACHE_TIME = 0

async def _fetch_raw_chats(client, groups_map):
    """MTProto GetAllChats ile grupları çeker."""
    try:
        from pyrogram.raw.functions.messages import GetAllChats
        from pyrogram.raw.types import Chat as RawChat, Channel as RawChannel
        res = await client.invoke(GetAllChats(except_ids=[]))
        for c in getattr(res, "chats", []):
            if isinstance(c, RawChat):
                cid = -c.id
                groups_map[cid] = c.title or "Grup"
            elif isinstance(c, RawChannel):
                if getattr(c, "megagroup", False) or not getattr(c, "broadcast", False):
                    cid = int(f"-100{c.id}")
                    groups_map[cid] = c.title or "Süper Grup"
    except Exception as e:
        logging.warning("GetAllChats uyarısı: %s", e)


async def _fetch_dialog_groups(client, groups_map):
    """Standart get_dialogs taraması ile grupları toplar."""
    try:
        async for dialog in client.get_dialogs(limit=150):
            chat = getattr(dialog, "chat", None)
            if not chat:
                continue
            chat_type_str = str(getattr(chat, "type", "")).lower()
            if "group" in chat_type_str or getattr(chat, "type", None) in (ChatType.GROUP, ChatType.SUPERGROUP):
                groups_map[chat.id] = chat.title or "Grup"
    except Exception as e:
        logging.warning("get_dialogs uyarısı: %s", e)


async def get_all_user_groups(client, force_refresh=False):
    """Kullanıcının üye olduğu tüm grupları hem MTProto GetAllChats hem de get_dialogs ile eksiksiz ve hatasız çeker."""
    global CACHED_GROUPS, LAST_CACHE_TIME, ggr_son_listelenen_gruplar, SON_LISTELENEN_GRUPLAR
    now = time.time()
    if not force_refresh and CACHED_GROUPS and (now - LAST_CACHE_TIME < 600):
        return CACHED_GROUPS

    groups_map = {}
    yedek_id = utils.get_yedek_grup_id()

    await _fetch_raw_chats(client, groups_map)
    await _fetch_dialog_groups(client, groups_map)

    groups = [
        {"id": cid, "title": title}
        for cid, title in groups_map.items()
        if not (yedek_id and str(cid) == str(yedek_id))
    ]

    if groups:
        CACHED_GROUPS = groups
        ggr_son_listelenen_gruplar = groups
        LAST_CACHE_TIME = now
    elif CACHED_GROUPS:
        groups = CACHED_GROUPS

    return groups


# =============================================================================
# 1. TOPLU İLETİM MOTORU (.ilet)
# =============================================================================
def _ilet_filtre_kontrol(_, __, m):
    """Hem mesaj metninde hem de medya altyazısında .ilet komutunu yakalar."""
    if not m.from_user or not m.from_user.is_self:
        return False
    icerik = (m.text or m.caption or "").strip()
    return icerik == ".ilet" or icerik.startswith(".ilet ") or icerik.startswith(".ilet\n")

ilet_filtresi = filters.create(_ilet_filtre_kontrol)


async def _send_to_chat(client, chat_id, kaynak_mesaj, gonderilecek_caption, gonderilecek_metin):
    """Tek bir gruba mesaj/medya gönderir."""
    if kaynak_mesaj:
        if gonderilecek_caption is not None:
            await kaynak_mesaj.copy(chat_id, caption=gonderilecek_caption)
        else:
            await kaynak_mesaj.copy(chat_id)
    else:
        await client.send_message(chat_id, gonderilecek_metin)


async def _safe_edit_status(message, is_caption: bool, text: str):
    """İletim durum mesajını hata fırlatmadan düzenler."""
    try:
        if is_caption:
            await message.edit_caption(text)
        else:
            await message.edit_text(text)
    except Exception as _e:
        logging.debug("Durum mesajı düzenlenemedi: %s", _e)


def _detect_ilet_content(message, is_caption: bool, ek_metin: str):
    """İletilecek içeriği ve başlığı belirler."""
    if is_caption:
        return message, (ek_metin if ek_metin else None), None, None
    if message.reply_to_message:
        return message.reply_to_message, ek_metin, None, None
    if ek_metin:
        return None, None, ek_metin, None
    return None, None, None, (
        "❌ <b>Lütfen iletilecek bir içerik belirtin!</b>\n\n"
        "💡 <b>Kullanım:</b>\n"
        "• Mesaja yanıt vererek: <code>.ilet</code>\n"
        "• Metin yazarak: <code>.ilet [Metin]</code>\n"
        "• Fotoğraf/Video altyazısına: <code>.ilet</code> veya <code>.ilet [Açıklama]</code>"
    )


async def _send_single_group_with_retry(client, chat_id, chat_title, kaynak_mesaj, gonderilecek_caption, gonderilecek_metin) -> bool:
    try:
        await _send_to_chat(client, chat_id, kaynak_mesaj, gonderilecek_caption, gonderilecek_metin)
        return True
    except errors.FloodWait as e:
        logging.warning("FloodWait: %s sn bekleniyor...", e.value)
        await asyncio.sleep(e.value + 1)
        try:
            await _send_to_chat(client, chat_id, kaynak_mesaj, gonderilecek_caption, gonderilecek_metin)
            return True
        except Exception:
            return False
    except Exception as err:
        logging.warning("Grup iletim hatası (%s): %s", chat_title, err)
        return False


async def _broadcast_to_groups(client, message, hedef_gruplar, kaynak_mesaj, gonderilecek_caption, gonderilecek_metin, is_caption):
    toplam = len(hedef_gruplar)
    basarili, hatali = 0, 0
    for idx, grup in enumerate(hedef_gruplar, start=1):
        chat_id = grup["id"]
        chat_title = grup["title"]
        ok = await _send_single_group_with_retry(client, chat_id, chat_title, kaynak_mesaj, gonderilecek_caption, gonderilecek_metin)
        if ok:
            basarili += 1
        else:
            hatali += 1

        if idx % 3 == 0 or idx == toplam:
            durum_metni = (
                f"📤 <b>İletiliyor...</b> <code>[{idx}/{toplam}]</code> (%{int((idx/toplam)*100)})\n"
                f"✅ Başarılı: <code>{basarili}</code> | ❌ Hata: <code>{hatali}</code>"
            )
            await _safe_edit_status(message, is_caption, durum_metni)

        if idx < toplam:
            await asyncio.sleep(ggr_ilet_bekleme)
    return basarili, hatali


@ggr.on(ilet_filtresi)
async def toplu_ilet_komutu(client, message):
    """Mesajı, yanıtlanan içeriği veya altyazılı medyayı seçili gruplara iletir."""
    logging.info("Kullanıcı %s .ilet komutunu çalıştırdı.", message.from_user.id if message.from_user else 'Bilinmeyen')

    is_caption = bool(message.caption)
    raw_text = (message.caption if is_caption else message.text or "").strip()
    ek_metin = raw_text[5:].strip() if len(raw_text) > 5 else None

    kaynak_mesaj, gonderilecek_caption, gonderilecek_metin, err = _detect_ilet_content(message, is_caption, ek_metin)
    if err:
        await message.edit_text(err)
        return

    await _safe_edit_status(message, is_caption, "🔄 <i>Gruplar taranıyor...</i>")

    butun_gruplar = await get_all_user_groups(client)
    hedef_gruplar = [g for g in butun_gruplar if is_group_active(g["id"])]

    if not hedef_gruplar:
        msg = "⚠️ <b>Hiçbir grup açık değil!</b> <code>.iletmenu</code> yazarak grupları açabilirsiniz."
        await _safe_edit_status(message, is_caption, msg)
        return

    toplam = len(hedef_gruplar)
    baslangic = time.time()

    basarili, hatali = await _broadcast_to_groups(
        client, message, hedef_gruplar, kaynak_mesaj, gonderilecek_caption, gonderilecek_metin, is_caption
    )

    gecen = time.time() - baslangic
    sonuc_metni = f"✅ <b>İletildi!</b> ({basarili}/{toplam} grup | ⏱️ {gecen:.1f} sn)"
    if is_caption and ek_metin:
        sonuc_metni = f"{ek_metin}\n\n{sonuc_metni}"

    await _safe_edit_status(message, is_caption, sonuc_metni)


# =============================================================================
# 2. NUMARALI BUTONLU GRUP YÖNETİM MENÜSÜ (.iletmenu)
# =============================================================================
async def _handle_manual_group_toggle(client, message, idx: int):
    global ggr_son_listelenen_gruplar
    if not ggr_son_listelenen_gruplar:
        ggr_son_listelenen_gruplar = await get_all_user_groups(client)
    if 1 <= idx <= len(ggr_son_listelenen_gruplar):
        secilen = ggr_son_listelenen_gruplar[idx - 1]
        yeni_durum = toggle_group(secilen["id"])
        durum_str = "✅ <b>AÇIK (Gönderilecek)</b>" if yeni_durum else "⛔ <b>KAPALI (Atlanacak)</b>"
        await message.edit_text(
            f"🔧 <b>{idx}. {ggr.safe_html(secilen['title'])}</b>\n"
            f"Yeni Durum: {durum_str}"
        )
    else:
        await message.edit_text(f"❌ Geçersiz numara! 1 ile {len(ggr_son_listelenen_gruplar)} arasında olmalıdır.")


async def _show_inline_ilet_menu(client, message, durum) -> bool:
    if not utils.YARDIMCI_BOT_USERNAME:
        return False
    try:
        results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, "ilet_1")
        if results and results.results:
            res = await utils.send_inline_result_in_context(
                client,
                message,
                results.query_id,
                results.results[0].id
            )
            sent_msg_id = utils.extract_sent_message_id(res)
            if sent_msg_id:
                utils.LAST_ILET_MENU = (message.chat.id, sent_msg_id)
            await durum.delete()
            return True
    except Exception as e:
        logging.warning("İlet inline menü uyarısı (%s), metin listesine geçiliyor...", e)
    return False


@ggr.cmd("iletmenu", info="Grupları numaralandırarak listeler ve tek tıkla açıp kapatmanızı sağlar.", usage=".iletmenu | .iletmenu [numara]", category="Grup & İletim")
async def ilet_menu_komutu(client, message):
    """Grupları listeler ve altındaki numara butonlarıyla açıp kapatmayı sağlar."""
    global ggr_son_listelenen_gruplar
    args = message.command[1:] if len(message.command) > 1 else []

    if args and args[0].isdigit():
        await _handle_manual_group_toggle(client, message, int(args[0]))
        return

    durum = await message.edit_text("🔄 <i>Gruplar hazırlanıyor...</i>")
    force = bool(args and args[0].lower() in ["yenile", "refresh"])
    gruplar = await get_all_user_groups(client, force_refresh=force)
    ggr_son_listelenen_gruplar = gruplar

    if not gruplar:
        await durum.edit_text("ℹ️ Üye olduğunuz herhangi bir grup bulunamadı.")
        return

    opened_inline = await _show_inline_ilet_menu(client, message, durum)
    if opened_inline:
        return

    metin = "📢 <b>Toplu İletim Grupları:</b>\n\n"
    for i, g in enumerate(gruplar, 1):
        durum_str = "✅ Açık" if is_group_active(g["id"]) else "⛔ Kapalı"
        metin += f"<b>{i}.</b> {ggr.safe_html(g['title'])} — [{durum_str}]\n"
    metin += (
        "\n💡 Durum değiştirmek için: <code>.iletmenu [numara]</code> (Örn: <code>.iletmenu 3</code>)\n"
        "🔄 Listeyi tazelemek için: <code>.iletmenu yenile</code>\n\n"
        "⚠️ <i>Sorumluluk Reddi: Toplu mesaj gönderiminde hesabınızın Telegram tarafından spam yemesi veya kısıtlanması durumunda sorumluluk kullanıcıya aittir.</i>"
    )
    await durum.edit_text(metin)
