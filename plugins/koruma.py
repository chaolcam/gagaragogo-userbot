# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: DM Protection & Privacy Guardian (plugins/koruma.py)
# Description: Intercepts and archives deleted direct messages (.antidelete)
#              and ephemeral self-destructing media (.sureli) to the admin backup group.
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
            logging.error(f"Anti-delete forum topic oluşturma hatası: {e}")
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
            logging.error(f"Süreli medya forum topic oluşturma hatası: {e}")
    return topic_id


# ================= ANTI-DELETE MODÜLÜ (SADECE ÖZEL SOHBETLER) =================
# 512 MB RAM optimizasyonu: Özel sohbetler için son 500 mesaj önbellekte tutulur
ggr_mesaj_onbellegi = LRUCache(maxsize=500)

@ggr.cmd("antidelete", info="Özel sohbetlerde (DM) silinen mesajları yakalama modunu açar veya kapatır.", usage=".antidelete on | .antidelete off", category="Araçlar")
async def antidelete_ayar(client, message):
    logging.info(f"Kullanıcı {message.from_user.id if message.from_user else 'Bilinmeyen'} .antidelete komutunu çalıştırdı.")
    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg == "on":
            ggr.set("antidelete_durumu", True)
            await message.edit_text("✅ <b>Anti-Delete Modu Açıldı!</b>\nÖzel sohbetlerde silinen mesajlar Ana Admin Grubundaki <code>Silinen Mesajlar</code> konusuna kaydedilecek.")
        elif arg == "off":
            ggr.set("antidelete_durumu", False)
            await message.edit_text("❌ <b>Anti-Delete Modu Kapatıldı!</b>\nArtık silinen mesajlar yakalanmayacak.")
        else:
            await message.edit_text("Hatalı kullanım: <code>.antidelete on</code> veya <code>.antidelete off</code>")
    else:
        durum = ggr.get("antidelete_durumu", False)
        durum_metni = "AÇIK ✅" if durum else "KAPALI ❌"
        await message.edit_text(f"Özel Sohbet Anti-Delete: <b>{durum_metni}</b>\n\n📌 Kayıt Hedefi: <code>Ana Admin Grubu</code>")

@ggr.on(filters.private, group=-20)
async def mesaj_hafizala(client, message):
    if ggr.get("antidelete_durumu", False):
        ggr_mesaj_onbellegi[message.id] = message

@Client.on_deleted_messages()
async def silinen_mesajlari_yakala(client, messages):
    if not ggr.get("antidelete_durumu", False): return
        
    hedef_chat = ggr.backup_chat_id()
    if not hedef_chat or hedef_chat == 0: return
    
    topic_id = await get_or_create_antidelete_topic(client, hedef_chat)
    
    for msg in messages:
        if msg.id in ggr_mesaj_onbellegi:
            orjinal = ggr_mesaj_onbellegi[msg.id]
            
            # Sadece özel sohbet kontrolü (gruplar işlenmez)
            if hasattr(orjinal, "chat") and orjinal.chat and str(orjinal.chat.type).lower() not in ["chat_type.private", "private"]:
                continue
                
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
                continue 
            except Exception as e: pass 
                
            try:
                if orjinal.media:
                    indirilen_ram = await client.download_media(orjinal, in_memory=True)
                    if not indirilen_ram: continue
                        
                    indirilen = ggr.format_file(orjinal, BytesIO(indirilen_ram.getvalue()))
                    
                    if orjinal.photo: await client.send_photo(chat_id=hedef_chat, photo=indirilen, caption=bilgi_metni, reply_to_message_id=topic_id)
                    elif orjinal.video: await client.send_video(chat_id=hedef_chat, video=indirilen, caption=bilgi_metni, reply_to_message_id=topic_id)
                    elif getattr(orjinal, 'voice', None) or getattr(orjinal, 'audio', None): await client.send_audio(chat_id=hedef_chat, audio=indirilen, caption=bilgi_metni, reply_to_message_id=topic_id)
                    else: await client.send_document(chat_id=hedef_chat, document=indirilen, caption=bilgi_metni, reply_to_message_id=topic_id)
                else:
                    await client.send_message(chat_id=hedef_chat, text=f"{bilgi_metni}\n📝 <b>Mesaj:</b>\n\n{ggr.safe_html(orjinal.text)}", reply_to_message_id=topic_id)
            except Exception as e: logging.error(f"Anti-Delete Bypass Hatası: {e}")


# ================= SÜRELİ MEDYA MODÜLÜ =================
@ggr.cmd("sureli", info="Tek gösterimlik süreli medyaları otomatik yakalayıp kaydeder.", usage=".sureli on | .sureli off", category="Araçlar")
async def sureli_ayar(client, message):
    logging.info(f"Kullanıcı {message.from_user.id if message.from_user else 'Bilinmeyen'} .sureli komutunu çalıştırdı.")
    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg == "on":
            ggr.set("hayalet_durumu", True)
            await message.edit_text("⏳ <b>Süreli Medya Modu Açıldı!</b>\nTek gösterimlik medyalar Ana Admin Grubundaki <code>Süreli Medyalar</code> konusuna kaydedilecek.")
        elif arg == "off":
            ggr.set("hayalet_durumu", False)
            await message.edit_text("❌ <b>Süreli Medya Modu Kapatıldı!</b>\nArtık tek gösterimlik medyalar yakalanmayacak.")
        else:
            await message.edit_text("Hatalı kullanım: <code>.sureli on</code> veya <code>.sureli off</code>")
    else:
        durum = ggr.get("hayalet_durumu", False)
        durum_metni = "AÇIK ⏳" if durum else "KAPALI ❌"
        await message.edit_text(f"Süreli Medya Modu: <b>{durum_metni}</b>\n\n📌 Kayıt Hedefi: <code>Ana Admin Grubu</code>")

@ggr.on(filters.private & (filters.photo | filters.video | filters.voice | filters.video_note | filters.animation))
async def sureli_medya_yakalayici(client, message):
    if not ggr.get("hayalet_durumu", False):
        return
        
    is_ghost = False
    
    if getattr(message, "ttl_seconds", None): is_ghost = True
    elif getattr(message.photo, "ttl_seconds", None): is_ghost = True
    elif getattr(message.video, "ttl_seconds", None): is_ghost = True
    elif getattr(message.voice, "ttl_seconds", None): is_ghost = True
    elif getattr(message.video_note, "ttl_seconds", None): is_ghost = True
        
    if getattr(message, "view_once", None) is True: 
        is_ghost = True
        
    if getattr(message, "has_protected_content", None) is True:
        is_ghost = True

    if not is_ghost: return 
    
    try:
        dl = await client.download_media(message, in_memory=True)
        if not dl: return
        
        hedef_chat = ggr.backup_chat_id()
        if not hedef_chat or hedef_chat == 0: return
        
        topic_id = await get_or_create_sureli_topic(client, hedef_chat)
        
        try:
            gonderen = message.from_user
            kisi = ggr.safe_html(gonderen.first_name) if gonderen else "Bilinmiyor"
            kullanici_id = gonderen.id if gonderen else "Yok"
            kullanici_adi = f"@{gonderen.username}" if (gonderen and gonderen.username) else "Yok"
            
            dl = ggr.format_file(message, BytesIO(dl.getvalue()))
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
        except Exception as e: 
            logging.error(f"Süreli medya yakalama hatası: {e}")
    except Exception as e: 
        logging.error(f"Hayalet indirme hatası: {e}")
