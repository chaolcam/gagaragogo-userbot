# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Anti-Delete & View-Once Media Protector
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import time
import asyncio
from io import BytesIO
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
import logging
from cachetools import LRUCache
from utils import ggr, create_forum_topic_helper

async def get_or_create_antidelete_topic(client, hedef_chat):
    """Ana admin grubunda silinen mesajlar için otomatik forum konusu oluşturur/getirir."""
    topic_id = ggr.get("antidelete_topic_id")
    if not topic_id and str(hedef_chat).startswith("-100"):
        try:
            topic_id = await create_forum_topic_helper(client, hedef_chat, "🗑 Silinen Mesajlar")
            if topic_id:
                ggr.set("antidelete_topic_id", topic_id)
        except Exception as e:
            logging.error("Anti-delete forum topic oluşturma hatası: %s", e)
    return topic_id

async def get_or_create_sureli_topic(client, hedef_chat):
    """Ana admin grubunda süreli medyalar için otomatik forum konusu oluşturur/getirir."""
    topic_id = ggr.get("sureli_topic_id")
    if not topic_id and str(hedef_chat).startswith("-100"):
        try:
            topic_id = await create_forum_topic_helper(client, hedef_chat, "⏳ Süreli Medyalar")
            if topic_id:
                ggr.set("sureli_topic_id", topic_id)
        except Exception as e:
            logging.error("Süreli medya forum topic oluşturma hatası: %s", e)
    return topic_id


# ================= ANTI-DELETE MODÜLÜ (SADECE ÖZEL SOHBETLER) =================
# 512 MB RAM optimizasyonu: Özel sohbetler için son 500 mesaj önbellekte tutulur
ggr_mesaj_onbellegi = LRUCache(maxsize=500)

@ggr.cmd("antidelete", info="Özel sohbetlerde (DM) silinen mesajları yakalama modunu açar veya kapatır.", usage=".antidelete on | .antidelete off", category="Araçlar")
async def antidelete_ayar(client, message):
    logging.info("Kullanıcı %s .antidelete komutunu çalıştırdı.", message.from_user.id if message.from_user else 'Bilinmeyen')
    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg == "on":
            ggr.set("antidelete_durumu", True)
            await message.edit_text(ggr.t("antidelete_on"))
        elif arg == "off":
            ggr.set("antidelete_durumu", False)
            await message.edit_text(ggr.t("antidelete_off"))
        else:
            await message.edit_text(ggr.t("err_missing_args"))
    else:
        durum = ggr.get("antidelete_durumu", False)
        durum_metni = "AÇIK ✅" if durum else "KAPALI ❌"
        await message.edit_text(f"Özel Sohbet Anti-Delete: <b>{durum_metni}</b>\n\n📌 Kayıt Hedefi: <code>Ana Admin Grubu</code>")

@ggr.on(filters.private, group=-20)
async def mesaj_hafizala(client, message):
    if ggr.get("antidelete_durumu", False):
        ggr_mesaj_onbellegi[message.id] = message

async def _forward_deleted_msg(client, orjinal, hedef_chat, topic_id):
    """Silinen mesajı yedek konusuna iletir veya indirip yükler."""
    gonderen = orjinal.from_user
    isim = ggr.safe_html(gonderen.first_name) if gonderen else "Bilinmeyen Kişi"
    kullanici_id = gonderen.id if gonderen else "Yok"
    kullanici_adi = f"@{gonderen.username}" if (gonderen and gonderen.username) else "Yok"

    bilgi_metni = (
        "🗑 <b>Silinen Mesaj Yakalandı!</b>\n"
        "────────────────────────\n"
        f"👤 <b>Gönderen:</b> <a href=\"tg://user?id={kullanici_id}\">{isim}</a>\n"
        f"🆔 <b>Kullanıcı ID:</b> <code>{kullanici_id}</code>\n"
        f"🔗 <b>Kullanıcı Adı:</b> {kullanici_adi}\n"
    )

    try:
        kopyalanan = await orjinal.copy(chat_id=hedef_chat, reply_to_message_id=topic_id)
        await kopyalanan.reply(bilgi_metni)
        return
    except Exception as _copy_err:
        logging.debug("Antidelete direkt kopyalama başarısız, indirme deneniyor: %s", _copy_err)

    try:
        if orjinal.media:
            indirilen_ram = await client.download_media(orjinal, in_memory=True)
            if not indirilen_ram:
                return

            indirilen = ggr.format_file(orjinal, BytesIO(indirilen_ram.getvalue()))
            if orjinal.photo:
                await client.send_photo(chat_id=hedef_chat, photo=indirilen, caption=bilgi_metni, reply_to_message_id=topic_id)
            elif orjinal.video:
                await client.send_video(chat_id=hedef_chat, video=indirilen, caption=bilgi_metni, reply_to_message_id=topic_id)
            elif getattr(orjinal, 'voice', None) or getattr(orjinal, 'audio', None):
                await client.send_audio(chat_id=hedef_chat, audio=indirilen, caption=bilgi_metni, reply_to_message_id=topic_id)
            else:
                await client.send_document(chat_id=hedef_chat, document=indirilen, caption=bilgi_metni, reply_to_message_id=topic_id)
        else:
            await client.send_message(chat_id=hedef_chat, text=f"{bilgi_metni}\n📝 <b>Mesaj:</b>\n\n{ggr.safe_html(orjinal.text)}", reply_to_message_id=topic_id)
    except Exception as e:
        logging.error("Anti-Delete Bypass Hatası: %s", e)


@Client.on_deleted_messages()
async def silinen_mesajlari_yakala(client, messages):
    if not ggr.get("antidelete_durumu", False):
        return

    hedef_chat = ggr.backup_chat_id()
    if not hedef_chat or hedef_chat == 0:
        return

    topic_id = await get_or_create_antidelete_topic(client, hedef_chat)

    for msg in messages:
        if msg.id in ggr_mesaj_onbellegi:
            orjinal = ggr_mesaj_onbellegi[msg.id]
            if hasattr(orjinal, "chat") and orjinal.chat and str(orjinal.chat.type).lower() not in ["chat_type.private", "private"]:
                continue
            await _forward_deleted_msg(client, orjinal, hedef_chat, topic_id)


# ================= SÜRELİ MEDYA MODÜLÜ =================
@ggr.cmd("sureli", info="Tek gösterimlik süreli medyaları otomatik yakalayıp kaydeder.", usage=".sureli on | .sureli off", category="Araçlar")
async def sureli_ayar(client, message):
    logging.info("Kullanıcı %s .sureli komutunu çalıştırdı.", message.from_user.id if message.from_user else 'Bilinmeyen')
    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg == "on":
            ggr.set("hayalet_durumu", True)
            await message.edit_text(ggr.t("sureli_on"))
        elif arg == "off":
            ggr.set("hayalet_durumu", False)
            await message.edit_text(ggr.t("sureli_off"))
        else:
            await message.edit_text(ggr.t("err_missing_args"))
    else:
        durum = ggr.get("hayalet_durumu", False)
        durum_metni = "AÇIK ⏳" if durum else "KAPALI ❌"
        await message.edit_text(f"Süreli Medya Modu: <b>{durum_metni}</b>\n\n📌 Kayıt Hedefi: <code>Ana Admin Grubu</code>")


def _is_ghost_media(message) -> bool:
    """Mesajın süreli (tek gösterimlik / korumalı) medya olup olmadığını kontrol eder."""
    for target in (message, getattr(message, "photo", None), getattr(message, "video", None), getattr(message, "voice", None), getattr(message, "video_note", None)):
        if target and getattr(target, "ttl_seconds", None):
            return True
    return bool(getattr(message, "view_once", None) or getattr(message, "has_protected_content", None))


async def _send_ghost_media_backup(client, message, dl_raw, hedef_chat, topic_id):
    """Süreli medyayı yedek grubundaki ilgili konuya yükler."""
    gonderen = message.from_user
    kisi = ggr.safe_html(gonderen.first_name) if gonderen else "Bilinmiyor"
    kullanici_id = gonderen.id if gonderen else "Yok"
    kullanici_adi = f"@{gonderen.username}" if (gonderen and gonderen.username) else "Yok"

    dl = ggr.format_file(message, BytesIO(dl_raw.getvalue()))
    suresi = getattr(message, "ttl_seconds", None) or getattr(message.photo, "ttl_seconds", None) or getattr(message.video, "ttl_seconds", None) or "Bilinmeyen"

    caption = (
        "⏳ <b>Süreli Medya Yakalandı!</b>\n"
        "────────────────────────\n"
        f"👤 <b>Gönderen:</b> <a href=\"tg://user?id={kullanici_id}\">{kisi}</a>\n"
        f"🆔 <b>ID:</b> <code>{kullanici_id}</code>\n"
        f"🔗 <b>Kullanıcı Adı:</b> {kullanici_adi}\n"
        f"⏱️ <b>Süre:</b> <code>{suresi}</code> saniye"
    )

    if message.photo:
        await client.send_photo(chat_id=hedef_chat, photo=dl, caption=caption, reply_to_message_id=topic_id)
    elif message.video or message.animation:
        await client.send_video(chat_id=hedef_chat, video=dl, caption=caption, reply_to_message_id=topic_id)
    elif message.voice:
        await client.send_voice(chat_id=hedef_chat, voice=dl, caption=caption, reply_to_message_id=topic_id)
    elif message.video_note:
        await client.send_video_note(chat_id=hedef_chat, video_note=dl, reply_to_message_id=topic_id)
        await client.send_message(chat_id=hedef_chat, text=caption, reply_to_message_id=topic_id)


@ggr.on(filters.private & (filters.photo | filters.video | filters.voice | filters.video_note | filters.animation))
async def sureli_medya_yakalayici(client, message):
    if not ggr.get("hayalet_durumu", False) or not _is_ghost_media(message):
        return

    try:
        dl = await client.download_media(message, in_memory=True)
        if not dl:
            return

        hedef_chat = ggr.backup_chat_id()
        if not hedef_chat or hedef_chat == 0:
            return

        topic_id = await get_or_create_sureli_topic(client, hedef_chat)
        try:
            await _send_ghost_media_backup(client, message, dl, hedef_chat, topic_id)
        except Exception as e:
            logging.error("Süreli medya yakalama hatası: %s", e)
    except Exception as e:
        logging.error("Hayalet indirme hatası: %s", e)
