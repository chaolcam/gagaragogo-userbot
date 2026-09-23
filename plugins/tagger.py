# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Group Member Tagging & Mention Utility
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import asyncio
import logging
from pyrogram.enums import ChatType, ChatMembersFilter
from pyrogram.errors import FloodWait
from utils import ggr

# Devam eden etiketleme süreçlerini takip eden sözlük {chat_id: bool}
ggr_aktif_etiketler = {}
AKTIF_ETIKETLEMELER = ggr_aktif_etiketler


async def _topla_filter_members(client, chat_id, member_filter, seen_ids, uyeler):
    """Belirli bir filtreyle grup üyelerini çeker."""
    try:
        async for m in client.get_chat_members(chat_id, filter=member_filter):
            if not ggr_aktif_etiketler.get(chat_id):
                break
            if m.user and not m.user.is_bot and not m.user.is_deleted and not m.user.is_self:
                if m.user.id not in seen_ids:
                    seen_ids.add(m.user.id)
                    uyeler.append(m.user)
    except Exception as e:
        logging.warning("Üye filtresi çekme uyarısı (%s): %s", member_filter, e)


async def _topla_harf_bazli(client, chat_id, seen_ids, uyeler):
    """Harf bazlı arama ile supergroup üyelerini bulur."""
    harfler = ["a", "e", "i", "o", "u", "b", "c", "d", "m", "s", "t", "1", "2"]
    for harf in harfler:
        if not ggr_aktif_etiketler.get(chat_id):
            break
        try:
            async for m in client.get_chat_members(chat_id, query=harf):
                if not ggr_aktif_etiketler.get(chat_id):
                    break
                if m.user and not m.user.is_bot and not m.user.is_deleted and not m.user.is_self:
                    if m.user.id not in seen_ids:
                        seen_ids.add(m.user.id)
                        uyeler.append(m.user)
        except Exception as _h_err:
            logging.debug("Harf arama hatası: %s", _h_err)
            continue


async def _topla_gecmis_mesajlar(client, chat_id, seen_ids, uyeler):
    """Gizli üyeli gruplarda son mesaj geçmişinden aktif üyeleri toplar."""
    try:
        async for msg in client.get_chat_history(chat_id, limit=300):
            if not ggr_aktif_etiketler.get(chat_id):
                break
            u = msg.from_user
            if u and not u.is_bot and not u.is_deleted and not u.is_self:
                if u.id not in seen_ids:
                    seen_ids.add(u.id)
                    uyeler.append(u)
    except Exception as e:
        logging.warning("Sohbet geçmişinden üye toplama uyarısı: %s", e)


async def uyeleri_topla(client, chat_id, sadece_admin=False):
    """Gruptaki üyeleri çeker."""
    uyeler = []
    seen_ids = set()

    # 1. Aşama: Yöneticileri Çek
    await _topla_filter_members(client, chat_id, ChatMembersFilter.ADMINISTRATORS, seen_ids, uyeler)
    if sadece_admin:
        return uyeler

    # 2. Aşama: RECENT (son aktif üyeler)
    await _topla_filter_members(client, chat_id, ChatMembersFilter.RECENT, seen_ids, uyeler)

    # 3. Aşama: Standart get_chat_members
    if len(uyeler) < 10 and ggr_aktif_etiketler.get(chat_id):
        try:
            async for m in client.get_chat_members(chat_id):
                if not ggr_aktif_etiketler.get(chat_id):
                    break
                if m.user and not m.user.is_bot and not m.user.is_deleted and not m.user.is_self:
                    if m.user.id not in seen_ids:
                        seen_ids.add(m.user.id)
                        uyeler.append(m.user)
        except Exception as e:
            logging.warning("Standart üye çekme uyarısı: %s", e)

    # 4. Aşama: Harf bazlı arama
    if len(uyeler) < 10 and ggr_aktif_etiketler.get(chat_id):
        await _topla_harf_bazli(client, chat_id, seen_ids, uyeler)

    # 5. Aşama: Sohbet geçmişi
    if len(uyeler) < 5 and ggr_aktif_etiketler.get(chat_id):
        await _topla_gecmis_mesajlar(client, chat_id, seen_ids, uyeler)

    return uyeler


def _parse_tag_arguments(cmd: str, args: list, subcmd: str):
    """Komut argümanlarından admin modu ve ek mesajı ayıklar."""
    if cmd == "alladmin" or subcmd in ["admin", "adminler", "yonetici", "yoneticiler"]:
        sadece_admin = True
        ek_mesaj = " ".join(args[1:] if subcmd in ["admin", "adminler", "yonetici", "yoneticiler"] else args).strip()
    elif subcmd in ["herkes", "all", "uyeler"]:
        sadece_admin = False
        ek_mesaj = " ".join(args[1:]).strip() if len(args) > 1 else ""
    else:
        sadece_admin = False
        ek_mesaj = " ".join(args).strip()
    return sadece_admin, ek_mesaj


async def _send_tag_batches(uyeler, chat_id, ek_mesaj, sadece_admin, guvenli_mesaj_gonder):
    """Üyeleri 5'erli paketler halinde etiketler."""
    sayac = 0
    paket = []

    for user in uyeler:
        if not ggr_aktif_etiketler.get(chat_id):
            break

        ad = ggr.safe_html(user.first_name or ("Yönetici" if sadece_admin else "Üye"))
        mention = f"<a href=\"tg://user?id={user.id}\">{ad}</a>"
        paket.append(mention)
        sayac += 1

        if len(paket) >= 5:
            metin = f"📢 <b>{ggr.safe_html(ek_mesaj)}</b>\n\n" if ek_mesaj else ""
            metin += " ".join(paket)
            try:
                await guvenli_mesaj_gonder(metin)
            except FloodWait as fw:
                await asyncio.sleep(fw.value + 1)
                await guvenli_mesaj_gonder(metin)
            except Exception as send_err:
                logging.warning("Paket gönderme hatası: %s", send_err)
            paket = []
            await asyncio.sleep(1.5)

    if paket and ggr_aktif_etiketler.get(chat_id):
        metin = f"📢 <b>{ggr.safe_html(ek_mesaj)}</b>\n\n" if ek_mesaj else ""
        metin += " ".join(paket)
        try:
            await guvenli_mesaj_gonder(metin)
        except FloodWait as fw:
            await asyncio.sleep(fw.value + 1)
            await guvenli_mesaj_gonder(metin)
        except Exception as send_err:
            logging.warning("Son paket gönderme hatası: %s", send_err)

    return sayac


@ggr.cmd(["tag", "tagall", "all", "alladmin", "etiket"], info="Gruplardaki üyeleri veya adminleri etiketler.", usage=".tag [mesaj] | .tag dur", category="Admin")
async def tag_komutu(client, message):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.edit_text("❌ <b>Bu komut yalnızca gruplarda kullanılabilir!</b>")
        return

    chat_id = message.chat.id
    cmd = message.command[0].lower() if message.command else "tag"
    args = message.text.split()[1:] if message.text else []
    subcmd = args[0].lower() if args else ""

    if subcmd in ["dur", "stop", "iptal", "cancel"]:
        if ggr_aktif_etiketler.get(chat_id):
            ggr_aktif_etiketler[chat_id] = False
            await message.edit_text(ggr.t("tagger_stopped"))
        else:
            await message.edit_text(ggr.t("tagger_no_active"))
        return

    if ggr_aktif_etiketler.get(chat_id):
        await message.edit_text(ggr.t("tagger_already_running"))
        return

    sadece_admin, ek_mesaj = _parse_tag_arguments(cmd, args, subcmd)

    thread_id = getattr(message, "message_thread_id", None)
    reply_id = message.reply_to_message.id if message.reply_to_message else (thread_id or message.id)

    async def guvenli_mesaj_gonder(text):
        try:
            return await client.send_message(chat_id, text, reply_to_message_id=reply_id)
        except Exception:
            try:
                if thread_id:
                    return await client.send_message(chat_id, text, reply_to_message_id=thread_id)
                return await client.send_message(chat_id, text)
            except Exception as e:
                logging.error("Mesaj gönderme hatası: %s", e)
                return None

    ggr_aktif_etiketler[chat_id] = True
    baslik_tur = "👑 Yöneticiler" if sadece_admin else "👥 Üyeler"
    
    await message.edit_text(
        f"⏳ <b>{baslik_tur} taranıyor, lütfen bekleyin...</b>\n"
        "💡 <i>Durdurmak için:</i> <code>.tag dur</code>"
    )

    try:
        uyeler = await uyeleri_topla(client, chat_id, sadece_admin=sadece_admin)
        if not uyeler:
            await message.edit_text(
                "⚠️ <b>Etiketlenecek üye bulunamadı!</b>\n\n"
                "• Grubun gizlilik ayarlarında <i>'Üyeleri Gizle'</i> açık olabilir ve son mesajlarda üye bulunamamış olabilir.\n"
                "• Grupta aktif ya da etiketlenebilecek kullanıcı kalmamış olabilir."
            )
            return

        toplam_sayi = len(uyeler)
        await message.edit_text(
            f"🚀 <b>Toplam {toplam_sayi} kişi bulundu!</b> Etiketleme başlıyor...\n"
            "💡 <i>Durdurmak için:</i> <code>.tag dur</code>"
        )

        sayac = await _send_tag_batches(uyeler, chat_id, ek_mesaj, sadece_admin, guvenli_mesaj_gonder)

        if ggr_aktif_etiketler.get(chat_id):
            await guvenli_mesaj_gonder(
                f"✅ <b>Etiketleme Tamamlandı!</b>\n"
                f"Toplam <code>{sayac}</code> kişi başarıyla etiketlendi."
            )
    except Exception as e:
        logging.error("Etiketleme hatası (%s): %s", chat_id, e)
        await guvenli_mesaj_gonder(f"❌ <b>Etiketleme Hatası:</b> <code>{e}</code>")
    finally:
        ggr_aktif_etiketler[chat_id] = False

