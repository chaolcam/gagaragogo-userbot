# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Image & Media Processing Utilities
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import io
import urllib.parse
import urllib.request
import asyncio
import logging
import requests
from io import BytesIO
from PIL import Image
from utils import ggr

ggr_medya_temp_dir = "downloads/medya_temp"
os.makedirs(ggr_medya_temp_dir, exist_ok=True)


# =============================================================================
# 1. YUVARLAK VİDEO MESAJ (.yuvarlak / .note)
# =============================================================================

@ggr.cmd(["yuvarlak", "note", "telescope"], info="Yanıtlanan videoyu 1:1 yuvarlak video mesaja (Telescope) dönüştürür.", usage="Yanıtlayarak: .yuvarlak veya .note", category="Araçlar")
async def yuvarlak_video_komutu(client, message):
    kaynak = message.reply_to_message
    if not kaynak or (not kaynak.video and not kaynak.animation and not kaynak.video_note):
        await message.edit_text("❌ <b>Lütfen bir videoya veya GIF'e yanıt vererek <code>.yuvarlak</code> yazın!</b>")
        return

    durum = await message.edit_text("⏳ <i>Video indiriliyor...</i>")
    input_path = os.path.join(ggr_medya_temp_dir, f"in_{message.id}.mp4")
    output_path = os.path.join(ggr_medya_temp_dir, f"note_{message.id}.mp4")

    try:
        await client.download_media(kaynak, file_name=input_path)
        await durum.edit_text("🔄 <i>Yuvarlak video formatına (1:1) dönüştürülüyor...</i>")

        # FFmpeg ile kare kırpma ve 384x384 boyutlandırma
        # En fazla 60 saniye kesit alınır
        cmd = [
            "ffmpeg", "-y", "-ss", "0", "-t", "60",
            "-i", input_path,
            "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=384:384",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k",
            "-movflags", "+faststart",
            output_path
        ]

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await proc.communicate()

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            await durum.edit_text("❌ Video dönüştürme başarısız oldu!")
            return

        await durum.edit_text("📤 <i>Yuvarlak video gönderiliyor...</i>")
        await client.send_video_note(message.chat.id, output_path, reply_to_message_id=kaynak.id)
        await durum.delete()

    except Exception as e:
        logging.error("Yuvarlak video hatası: %s", e)
        await durum.edit_text(f"❌ Hata: <code>{e}</code>")
    finally:
        for p in [input_path, output_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception as _exc:
                    logging.debug("Temp dosya silinemedi: %s", _exc)


# =============================================================================
# 2. SESLİ MESAJ DÖNÜŞTÜRÜCÜ (.ses / .voice)
# =============================================================================

@ggr.cmd(["ses", "voice"], info="Yanıtlanan video veya ses dosyasını Telegram sesli mesajına (Voice Note) dönüştürür.", usage="Yanıtlayarak: .ses veya .voice", category="Araçlar")
async def sesli_mesaj_komutu(client, message):
    kaynak = message.reply_to_message
    if not kaynak or (not kaynak.audio and not kaynak.voice and not kaynak.video and not kaynak.video_note):
        await message.edit_text("❌ <b>Lütfen bir ses veya video dosyasına yanıt vererek <code>.ses</code> yazın!</b>")
        return

    durum = await message.edit_text("⏳ <i>Medya indiriliyor...</i>")
    input_path = os.path.join(ggr_medya_temp_dir, f"in_audio_{message.id}")
    output_path = os.path.join(ggr_medya_temp_dir, f"voice_{message.id}.ogg")

    try:
        await client.download_media(kaynak, file_name=input_path)
        await durum.edit_text("🔄 <i>Sesli mesaja (Opus OGG) dönüştürülüyor...</i>")

        # FFmpeg ile Opus OGG sesli mesaja dönüştür
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vn", "-c:a", "libopus",
            "-b:a", "48k", "-ar", "48000", "-ac", "1",
            output_path
        ]

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await proc.communicate()

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            await durum.edit_text("❌ Ses dönüştürme başarısız oldu!")
            return

        await durum.edit_text("📤 <i>Sesli mesaj gönderiliyor...</i>")
        await client.send_voice(message.chat.id, output_path, reply_to_message_id=kaynak.id)
        await durum.delete()

    except Exception as e:
        logging.error("Ses dönüştürme hatası: %s", e)
        await durum.edit_text(f"❌ Hata: <code>{e}</code>")
    finally:
        for p in [input_path, output_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception as _exc:
                    logging.debug("Temp dosya silinemedi: %s", _exc)


# =============================================================================
# 3. STANDART TELEGRAM ÇIKARTMASI (.sticker)
# =============================================================================

@ggr.cmd(["sticker", "stiker"], info="Yanıtlanan fotoğrafı Telegram standart çıkartmasına (WebP) dönüştürür.", usage="Yanıtlayarak: .sticker", category="Araçlar")
async def sticker_yap_komutu(client, message):
    kaynak = message.reply_to_message
    if not kaynak or (not kaynak.photo and not kaynak.document and not kaynak.sticker):
        await message.edit_text("❌ <b>Lütfen bir fotoğrafa veya görsele yanıt vererek <code>.sticker</code> yazın!</b>")
        return

    durum = await message.edit_text("⏳ <i>Görsel çıkartmaya dönüştürülüyor...</i>")

    try:
        # Görseli RAM üzerinde indir
        img_bytes = await client.download_media(kaynak, in_memory=True)
        img_bytes.seek(0)
        
        # PIL ile aç ve oranını koruyarak 512x512 sınırına uyarla
        img = Image.open(img_bytes).convert("RGBA")
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        
        # WebP olarak kaydet
        out_io = BytesIO()
        out_io.name = "sticker.webp"
        img.save(out_io, format="WEBP", quality=95)
        out_io.seek(0)

        await client.send_sticker(message.chat.id, out_io, reply_to_message_id=kaynak.id)
        await durum.delete()

    except Exception as e:
        logging.error("Sticker dönüştürme hatası: %s", e)
        await durum.edit_text(f"❌ Hata: <code>{e}</code>")


# =============================================================================
# 4. METİN SESLENDİRME (.tts)
# =============================================================================

@ggr.cmd(["tts", "seslendir", "soyle"], info="Yazılan metni Türkçe seslendirip sesli mesaj olarak gönderir.", usage=".tts [metin] veya metne yanıtlayarak: .tts", category="Araçlar")
async def tts_komutu(client, message):
    metin = " ".join(message.command[1:]).strip() if len(message.command) > 1 else None
    
    if not metin and message.reply_to_message:
        metin = (message.reply_to_message.text or message.reply_to_message.caption or "").strip()
        
    if not metin:
        await message.edit_text(
            "❌ <b>Lütfen seslendirilecek bir metin girin veya bir mesaja yanıt verin!</b>\n\n"
            "💡 <b>Örnek:</b> <code>.tts Merhaba, nasılsınız?</code>"
        )
        return

    if len(metin) > 300:
        metin = metin[:297] + "..."

    durum = await message.edit_text("🎙 <i>Seslendiriliyor...</i>")

    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={urllib.parse.quote(metin)}&tl=tr&total=1&idx=0&textlen={len(metin)}&client=tw-ob"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        mp3_data = await asyncio.to_thread(lambda: requests.get(url, headers=headers, timeout=10).content)

        voice_io = BytesIO(mp3_data)
        voice_io.name = "seslendirme.mp3"

        reply_id = message.reply_to_message.id if message.reply_to_message else None
        await client.send_voice(message.chat.id, voice_io, reply_to_message_id=reply_id)
        await durum.delete()

    except Exception as e:
        logging.error("TTS hatası: %s", e)
        await durum.edit_text(f"❌ Seslendirme hatası: `{e}`")
