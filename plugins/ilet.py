# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Instant Broadcast Engine (plugins/ilet.py)
# Description: Broadcasts text, replies, or media to selected groups (.ilet)
#              with interactive multi-page group toggle management (.iletmenu).
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
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
    category="Toplu İletim"
)
ggr.cmd(
    "iletmenu", 
    info="Grupları numaralandırarak listeler ve tek tıkla açıp kapatmanızı sağlar.", 
    usage=".iletmenu (veya hızlı: .iletmenu [numara])",
    category="Toplu İletim"
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

async def get_all_user_groups(client, force_refresh=False):
    """Kullanıcının üye olduğu tüm grupları hem MTProto GetAllChats hem de get_dialogs ile eksiksiz ve hatasız çeker."""
    global CACHED_GROUPS, LAST_CACHE_TIME, ggr_son_listelenen_gruplar, SON_LISTELENEN_GRUPLAR
    now = time.time()
    if not force_refresh and CACHED_GROUPS and (now - LAST_CACHE_TIME < 600):
        return CACHED_GROUPS
        
    groups_map = {}
    yedek_id = utils.get_yedek_grup_id()

    # 1. Hızlı ve Güvenilir MTProto Çağrısı (GetAllChats)
    try:
        from pyrogram.raw.functions.messages import GetAllChats
        from pyrogram.raw.types import Chat as RawChat, Channel as RawChannel
        res = await client.invoke(GetAllChats(except_ids=[]))
        for c in getattr(res, "chats", []):
            if isinstance(c, RawChat):
                cid = -c.id
                groups_map[cid] = c.title or "Grup"
            elif isinstance(c, RawChannel):
                # Sadece süpergrupları al, yayın kanallarını hariç tut
                if getattr(c, "megagroup", False) or not getattr(c, "broadcast", False):
                    cid = int(f"-100{c.id}")
                    groups_map[cid] = c.title or "Süper Grup"
    except Exception as e:
        logging.warning(f"GetAllChats uyarısı: {e}")

    # 2. Standart get_dialogs taraması (Destekleyici)
    try:
        async for dialog in client.get_dialogs(limit=150):
            chat = getattr(dialog, "chat", None)
            if not chat:
                continue
            chat_type_str = str(getattr(chat, "type", "")).lower()
            if "group" in chat_type_str or getattr(chat, "type", None) in (ChatType.GROUP, ChatType.SUPERGROUP):
                groups_map[chat.id] = chat.title or "Grup"
    except Exception as e:
        logging.warning(f"get_dialogs uyarısı: {e}")

    # Admin/log grubunu filtrele
    groups = []
    for cid, title in groups_map.items():
        if yedek_id and str(cid) == str(yedek_id):
            continue
        groups.append({
            "id": cid,
            "title": title
        })

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


@ggr.on(ilet_filtresi)
async def toplu_ilet_komutu(client, message):
    """Mesajı, yanıtlanan içeriği veya altyazılı medyayı seçili gruplara iletir."""
    logging.info(f"Kullanıcı {message.from_user.id if message.from_user else 'Bilinmeyen'} .ilet komutunu çalıştırdı.")
    
    is_caption = bool(message.caption)
    raw_text = (message.caption if is_caption else message.text or "").strip()
    
    # '.ilet' sonrasındaki ek metni ayıkla
    ek_metin = raw_text[5:].strip() if len(raw_text) > 5 else None

    # İletilecek içerik tespiti
    kaynak_mesaj = None
    gonderilecek_caption = None
    gonderilecek_metin = None

    if is_caption:
        # 1. KULLANICI MEDYA GÖNDERİRKEN ALTYAZISINA .ilet YAZMIŞ
        kaynak_mesaj = message
        gonderilecek_caption = ek_metin if ek_metin else None
    elif message.reply_to_message:
        # 2. KULLANICI BİR MESAJI YANITLAYARAK .ilet YAZMIŞ
        kaynak_mesaj = message.reply_to_message
        # Yanıtlanan mesajda ek altyazı belirtilmişse onu kullan, yoksa orijinalini koru
        if ek_metin:
            gonderilecek_caption = ek_metin
    elif ek_metin:
        # 3. YANITSIZ DOĞRUDAN METİN GÖNDERİLMİŞ
        gonderilecek_metin = ek_metin
    else:
        await message.edit_text(
            "❌ <b>Lütfen iletilecek bir içerik belirtin!</b>\n\n"
            "💡 <b>Kullanım:</b>\n"
            "• Mesaja yanıt vererek: <code>.ilet</code>\n"
            "• Metin yazarak: <code>.ilet [Metin]</code>\n"
            "• Fotoğraf/Video altyazısına: <code>.ilet</code> veya <code>.ilet [Açıklama]</code>"
        )
        return

    # Durum bildirimi
    if is_caption:
        try: await message.edit_caption("🔄 <i>Gruplar taranıyor...</i>")
        except Exception: pass
    else:
        try: await message.edit_text("🔄 <i>Gruplar taranıyor...</i>")
        except Exception: pass

    # Hedef grupları çek ve filtrele
    butun_gruplar = await get_all_user_groups(client)
    hedef_gruplar = [g for g in butun_gruplar if is_group_active(g["id"])]
    
    if not hedef_gruplar:
        msg = "⚠️ <b>Hiçbir grup açık değil!</b> <code>.iletmenu</code> yazarak grupları açabilirsiniz."
        if is_caption:
            try: await message.edit_caption(msg)
            except Exception: pass
        else:
            try: await message.edit_text(msg)
            except Exception: pass
        return

    toplam = len(hedef_gruplar)
    basarili = 0
    hatali = 0
    baslangic = time.time()

    # Gönderim döngüsü
    for idx, grup in enumerate(hedef_gruplar, start=1):
        chat_id = grup["id"]
        chat_title = grup["title"]

        try:
            if kaynak_mesaj:
                if gonderilecek_caption is not None:
                    await kaynak_mesaj.copy(chat_id, caption=gonderilecek_caption)
                else:
                    await kaynak_mesaj.copy(chat_id)
            else:
                await client.send_message(chat_id, gonderilecek_metin)
            basarili += 1
        except errors.FloodWait as e:
            logging.warning(f"FloodWait: {e.value} sn bekleniyor...")
            await asyncio.sleep(e.value + 1)
            try:
                if kaynak_mesaj:
                    if gonderilecek_caption is not None:
                        await kaynak_mesaj.copy(chat_id, caption=gonderilecek_caption)
                    else:
                        await kaynak_mesaj.copy(chat_id)
                else:
                    await client.send_message(chat_id, gonderilecek_metin)
                basarili += 1
            except Exception:
                hatali += 1
        except Exception as err:
            logging.warning(f"Grup iletim hatası ({chat_title}): {err}")
            hatali += 1

        # Canlı durum göstergesi (her 3 grupta bir veya son grupta)
        if idx % 3 == 0 or idx == toplam:
            durum_metni = (
                f"📤 <b>İletiliyor...</b> <code>[{idx}/{toplam}]</code> (%{int((idx/toplam)*100)})\n"
                f"✅ Başarılı: <code>{basarili}</code> | ❌ Hata: <code>{hatali}</code>"
            )
            try:
                if is_caption:
                    await message.edit_caption(durum_metni)
                else:
                    await message.edit_text(durum_metni)
            except Exception:
                pass

        if idx < toplam:
            await asyncio.sleep(ggr_ilet_bekleme)

    # Tamamlandı raporu
    gecen = time.time() - baslangic
    sonuc_metni = f"✅ <b>İletildi!</b> ({basarili}/{toplam} grup | ⏱️ {gecen:.1f} sn)"
    
    if is_caption and ek_metin:
        # Kullanıcının orijinal açıklamasını koruyup sonuna raporu ekle
        sonuc_metni = f"{ek_metin}\n\n{sonuc_metni}"

    try:
        if is_caption:
            await message.edit_caption(sonuc_metni)
        else:
            await message.edit_text(sonuc_metni)
    except Exception:
        pass


# =============================================================================
# 2. NUMARALI BUTONLU GRUP YÖNETİM MENÜSÜ (.iletmenu)
# =============================================================================
@ggr.cmd("iletmenu", info="Grupları numaralandırarak listeler ve tek tıkla açıp kapatmanızı sağlar.", usage=".iletmenu | .iletmenu [numara]", category="Toplu İletim")
async def ilet_menu_komutu(client, message):
    """Grupları listeler ve altındaki numara butonlarıyla açıp kapatmayı sağlar."""
    global ggr_son_listelenen_gruplar
    args = message.command[1:] if len(message.command) > 1 else []
    
    # Kullanıcı metinle numara yazmışsa (Örn: .iletmenu 15) doğrudan toggle yap
    if args and args[0].isdigit():
        idx = int(args[0])
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
            return
        else:
            await message.edit_text(f"❌ Geçersiz numara! 1 ile {len(ggr_son_listelenen_gruplar)} arasında olmalıdır.")
            return

    durum = await message.edit_text("🔄 <i>Gruplar hazırlanıyor...</i>")
    
    # 1. Grupları önceden hazırla/önbelleğe al
    force = bool(args and args[0].lower() in ["yenile", "refresh"])
    gruplar = await get_all_user_groups(client, force_refresh=force)
    ggr_son_listelenen_gruplar = gruplar
    
    if not gruplar:
        await durum.edit_text("ℹ️ Üye olduğunuz herhangi bir grup bulunamadı.")
        return

    # 2. Yardımcı bot aktifse inline menüyü aç
    if utils.YARDIMCI_BOT_USERNAME:
        try:
            results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, "ilet_1")
            if results and results.results:
                res = await client.send_inline_bot_result(
                    message.chat.id,
                    results.query_id,
                    results.results[0].id
                )
                sent_msg_id = None
                if hasattr(res, "id"):
                    sent_msg_id = res.id
                elif hasattr(res, "updates"):
                    for u in res.updates:
                        if hasattr(u, "message") and hasattr(u.message, "id"):
                            sent_msg_id = u.message.id
                            break
                        if hasattr(u, "id"):
                            sent_msg_id = u.id
                            break
                if sent_msg_id:
                    utils.LAST_ILET_MENU = (message.chat.id, sent_msg_id)
                await durum.delete()
                return
        except Exception as e:
            logging.warning(f"İlet inline menü uyarısı ({e}), metin listesine geçiliyor...")

    # 3. Yardımcı bot yoksa veya inline timeout verirse doğrudan metin listesini sun
    metin = "📢 <b>Toplu İletim Grupları:</b>\n\n"
    for i, g in enumerate(gruplar, 1):
        durum_str = "✅ Açık" if is_group_active(g["id"]) else "⛔ Kapalı"
        metin += f"<b>{i}.</b> {ggr.safe_html(g['title'])} — [{durum_str}]\n"
    metin += "\n💡 Durum değiştirmek için: <code>.iletmenu [numara]</code> (Örn: <code>.iletmenu 3</code>)\n🔄 Listeyi tazelemek için: <code>.iletmenu yenile</code>"
    await durum.edit_text(metin)
