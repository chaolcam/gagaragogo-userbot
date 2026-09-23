# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Speech-to-Text & Audio Transcription Tool
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import uuid
import asyncio
import logging
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
import speech_recognition as sr
import utils
from core.decorators import ggr_cmd

logger = logging.getLogger("ggr.stt")


def _convert_to_wav(input_path: str, output_path: str) -> bool:
    """FFmpeg ile ses veya video dosyasını Google Speech uyumlu 16kHz mono WAV'a çevirir."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        output_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)  # nosec B603,B607
        return res.returncode == 0
    except Exception as e:
        logger.error("FFmpeg dönüştürme hatası: %s", e)
        return False


def _recognize_audio(wav_path: str, lang: str = "tr-TR") -> str:
    """WAV dosyasını Google Speech Recognition motoru ile metne döker."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
    return recognizer.recognize_google(audio_data, language=lang)


def _resolve_stt_language(command_list: list) -> str:
    if len(command_list) <= 1:
        return "tr-TR"
    param = command_list[1].strip().lower()
    lang_map = {
        ("en", "us", "uk"): "en-US",
        ("de", "almanca"): "de-DE",
        ("ru", "rusça", "rusca"): "ru-RU",
        ("ar", "arapça", "arapca"): "ar-SA",
        ("fr", "fransızca", "fransizca"): "fr-FR",
        ("az", "azerbaycanca"): "az-AZ",
    }
    for keys, val in lang_map.items():
        if param in keys:
            return val
    return f"{param}-{param.upper()}" if len(param) == 2 else param


def _safe_cleanup_files(*file_paths):
    for f in file_paths:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except Exception as _exc:
                logger.debug("Dosya silme uyarısı: %s", _exc)


async def _process_speech_recognition(wav_file: str, lang: str):
    try:
        metin = await asyncio.to_thread(_recognize_audio, wav_file, lang)
        return True, metin
    except sr.UnknownValueError:
        return False, "🔇 <b>Ses anlaşılamadı.</b> (Ortamda çok fazla gürültü olabilir veya konuşma tespit edilemedi.)"
    except sr.RequestError as req_err:
        return False, f"⚠️ <b>Google Servis Hatası:</b> <code>{req_err}</code>"


@Client.on_message(filters.command(["stt", "yaziya", "yaziyadok"], prefixes=[".", "/"]) & filters.me)
@ggr_cmd("stt", category="araçlar", desc="Sesli mesajları veya ses dosyalarını yazıya döker", usage=".stt [dil_kodu] (Örn: .stt tr)")
async def stt_handler(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply or not (reply.voice or reply.audio or reply.video or reply.video_note):
        await message.edit(
            "💡 <b>Lütfen bir sesli mesaja, sese veya videoya yanıt vererek <code>.stt</code> yazın.</b>\n\n"
            "<i>Örnek:</i>\n"
            "• <code>.stt</code> (Varsayılan Türkçe)\n"
            "• <code>.stt en</code> (İngilizce sesler için)"
        )
        return

    lang = _resolve_stt_language(message.command)
    await message.edit("🎙️ <i>Ses kaydı indiriliyor ve dinleniyor...</i>")

    os.makedirs("downloads", exist_ok=True)
    unique_id = uuid.uuid4().hex[:8]
    input_file = f"downloads/stt_in_{unique_id}"
    wav_file = f"downloads/stt_out_{unique_id}.wav"

    try:
        downloaded = await reply.download(file_name=input_file)
        if not downloaded or not os.path.exists(downloaded):
            await message.edit("❌ <b>Ses dosyası indirilemedi!</b>")
            return

        await message.edit("⚙️ <i>Ses işleniyor ve metne dönüştürülüyor...</i>")

        converted = await asyncio.to_thread(_convert_to_wav, downloaded, wav_file)
        if not converted or not os.path.exists(wav_file):
            await message.edit("❌ <b>Ses dosyası işlenirken hata oluştu (FFmpeg kurulu mu?).</b>")
            return

        ok, res_text = await _process_speech_recognition(wav_file, lang)
        if not ok:
            await message.edit(res_text)
            return

        sonuc_mesaji = (
            f"📝 <b>SESLİ MESAJ METNİ ({lang.split('-')[0].upper()}):</b>\n"
            "────────────────────────\n"
            f"<blockquote>{utils.guvenli_isim(res_text)}</blockquote>"
        )
        await message.edit(sonuc_mesaji)

    except Exception as e:
        logger.error("STT genel hatası: %s", e)
        await message.edit(f"❌ <b>Beklenmeyen hata:</b> <code>{e}</code>")

    finally:
        _safe_cleanup_files(input_file, wav_file)
