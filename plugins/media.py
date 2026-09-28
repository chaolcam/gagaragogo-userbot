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
from core.locales import t

ggr_medya_temp_dir = "downloads/medya_temp"
os.makedirs(ggr_medya_temp_dir, exist_ok=True)


# =============================================================================
# 1. YUVARLAK VİDEO MESAJ (.yuvarlak / .note)
# =============================================================================

@ggr.cmd(["yuvarlak", "note", "telescope"], info=t("cmd_info_yantlanan_68"), usage=t("cmd_usage_yantlayarak_34"), category=t("cat_aralar"))
async def yuvarlak_video_komutu(client, message):
    kaynak = message.reply_to_message
    if not kaynak or (not kaynak.video and not kaynak.animation and not kaynak.video_note):
        await message.edit_text(ggr.t("err_video_or_gif_required"))
        return

    durum = await message.edit_text(ggr.t("media_downloading_video"))
    input_path = os.path.join(ggr_medya_temp_dir, f"in_{message.id}.mp4")
    output_path = os.path.join(ggr_medya_temp_dir, f"note_{message.id}.mp4")

    try:
        await client.download_media(kaynak, file_name=input_path)
        await durum.edit_text(ggr.t("media_converting_note"))

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
            await durum.edit_text(ggr.t("media_conversion_failed"))
            return

        await durum.edit_text(ggr.t("media_sending_note"))
        await client.send_video_note(message.chat.id, output_path, reply_to_message_id=kaynak.id)
        await durum.delete()

    except Exception as e:
        logging.error(t("log_yuvarlak_video_hatas_25"), e)
        await durum.edit_text(t("media_hata_code_e_code", e = e))
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

@ggr.cmd(["ses", "voice"], info=t("cmd_info_yantlanan_84"), usage=t("cmd_usage_yantlayarak_30"), category=t("cat_aralar"))
async def sesli_mesaj_komutu(client, message):
    kaynak = message.reply_to_message
    if not kaynak or (not kaynak.audio and not kaynak.voice and not kaynak.video and not kaynak.video_note):
        await message.edit_text(ggr.t("err_audio_or_video_required"))
        return

    durum = await message.edit_text(ggr.t("media_downloading_video"))
    input_path = os.path.join(ggr_medya_temp_dir, f"in_audio_{message.id}")
    output_path = os.path.join(ggr_medya_temp_dir, f"voice_{message.id}.ogg")

    try:
        await client.download_media(kaynak, file_name=input_path)
        await durum.edit_text(ggr.t("media_converting_voice"))

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
            await durum.edit_text(ggr.t("media_voice_conversion_failed"))
            return

        await durum.edit_text(ggr.t("media_sending_voice"))
        await client.send_voice(message.chat.id, output_path, reply_to_message_id=kaynak.id)
        await durum.delete()

    except Exception as e:
        logging.error(t("log_ses_dntrme_hatas_s_25"), e)
        await durum.edit_text(t("media_hata_code_e_code", e = e))
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

@ggr.cmd(["sticker", "stiker"], info=t("cmd_info_yantlanan_70"), usage=t("cmd_usage_yantlayarak_22"), category=t("cat_aralar"))
async def sticker_yap_komutu(client, message):
    kaynak = message.reply_to_message
    if not kaynak or (not kaynak.photo and not kaynak.document and not kaynak.sticker):
        await message.edit_text(ggr.t("err_image_required"))
        return

    durum = await message.edit_text(ggr.t("media_converting_sticker"))

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
        logging.error(t("log_sticker_dntrme_hatas_29"), e)
        await durum.edit_text(t("media_hata_code_e_code", e = e))


# =============================================================================
# 4. METİN SESLENDİRME (.tts)
# =============================================================================

@ggr.cmd(["tts", "seslendir", "soyle"], info=t("cmd_info_yazlan_61"), usage=t("cmd_usage_tts_42"), category=t("cat_aralar"))
async def tts_komutu(client, message):
    metin = " ".join(message.command[1:]).strip() if len(message.command) > 1 else None
    
    if not metin and message.reply_to_message:
        metin = (message.reply_to_message.text or message.reply_to_message.caption or "").strip()
        
    if not metin:
        await message.edit_text(ggr.t("err_text_or_reply_required", example=".tts Merhaba"))
        return

    if len(metin) > 300:
        metin = metin[:297] + "..."

    durum = await message.edit_text(ggr.t("media_generating_tts"))

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
        logging.error(t("log_tts_hatas_s_14"), e)
        await durum.edit_text(t("media_seslendirme_hatasi_e", e = e))
