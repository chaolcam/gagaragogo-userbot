# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: General Utilities, Tools & Converters
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import re
import shutil
import asyncio
import uuid
import logging
import yt_dlp
import requests
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument
from deep_translator import GoogleTranslator
from utils import ggr

# ================= ÇEVİRİ MODÜLÜ =================
@ggr.cmd(["ceviridil", "cevdil"], info="Çeviri (.cevir) için varsayılan hedef dilinizi ayarlar.", usage=".ceviridil [dil kodu] (Örn: .ceviridil en)", category="Araçlar")
async def dil_ayarla(client, message):
    logging.info("Kullanıcı %s .dil komutunu çalıştırdı.", message.from_user.id if message.from_user else 'Bilinmeyen')
    if len(message.command) > 1:
        yeni_dil = message.command[1].lower()
        ggr.set("cevir_hedef_dil", yeni_dil)
        await message.edit_text(f"🌍 <b>Çeviri Dili Ayarlandı!</b>\nArtık <code>.cevir</code> komutunu kullandığınızda mesajlar otomatik olarak <code>{yeni_dil}</code> diline çevrilecek.")
    else:
        mevcut_dil = ggr.get("cevir_hedef_dil", "tr")
        await message.edit_text(f"Lütfen bir dil kodu belirtin. (Örn: <code>.dil en</code>)\n\n🌍 <b>Mevcut Hedef Dil:</b> <code>{mevcut_dil}</code>")

@ggr.cmd(["cevir", "çevir"], info="Yanıtladığınız mesajı ayarladığınız varsayılan dile otomatik çevirir.", usage="Yanıtlayarak: .cevir", category="Araçlar")
async def ceviri_yap(client, message):
    logging.info("Kullanıcı %s .cevir komutunu çalıştırdı.", message.from_user.id if message.from_user else 'Bilinmeyen')
    if not message.reply_to_message or not message.reply_to_message.text:
        await message.edit_text(ggr.t("err_reply_text_required"))
        return
        
    hedef_dil = ggr.get("cevir_hedef_dil", "tr")
    kaynak_metin = message.reply_to_message.text
    
    await message.edit_text("⏳ <i>Çevriliyor...</i>")
    
    try:
        ceviri = GoogleTranslator(source='auto', target=hedef_dil).translate(kaynak_metin)
        sonuc_metni = f"🌍 <b>Çeviri ({hedef_dil}):</b>\n\n<code>{ggr.safe_html(ceviri)}</code>"
        await message.edit_text(sonuc_metni)
    except Exception as e:
        await message.edit_text(f"❌ Çeviri başarısız oldu:\n<code>{e}</code>")


# ================= SOSYAL MEDYA İNDİRİCİ =================
def download_with_ytdlp(url, download_dir):
    """YouTube, Reddit ve genel platformlardan video/ses içeriklerini yt-dlp ile en iyi kalitede indirir."""
    ydl_opts = {
        'outtmpl': os.path.join(download_dir, '%(id)s_%(autonumber)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'playlist_items': '1-50',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_tiktok_tikwm(url, download_dir):
    """TikTok videolarını filigransız (HD) veya fotoğraf kaydırmalı albüm olarak TikWM API üzerinden indirir."""
    api_url = f"https://www.tikwm.com/api/?url={url}"
    try:
        r = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15).json()
        if r.get("code") == 0 and "data" in r:
            data = r["data"]
            username = data.get("author", {}).get("unique_id", "Bilinmeyen")
            if "images" in data and data["images"]:
                for i, img_url in enumerate(data["images"]):
                    img_data = requests.get(img_url, timeout=15).content
                    with open(os.path.join(download_dir, f"tiktok_{i}.jpg"), "wb") as f:
                        f.write(img_data)
                return username
            elif "play" in data:
                vid_url = "https://www.tikwm.com" + data["play"] if data["play"].startswith("/") else data["play"]
                vid_data = requests.get(vid_url, timeout=30).content
                with open(os.path.join(download_dir, "tiktok_video.mp4"), "wb") as f:
                    f.write(vid_data)
                return username
    except Exception as e:
        logging.warning("TikWM hatası (%s), yt-dlp deneniyor...", e)
    return None

def download_twitter_media(url, download_dir):
    """Twitter (X) görsellerini ve videolarını vxtwitter API üzerinden yüksek hızda çeker."""
    from concurrent.futures import ThreadPoolExecutor
    api_url = url.replace("twitter.com", "api.vxtwitter.com").replace("x.com", "api.vxtwitter.com")
    resp = requests.get(api_url, timeout=15).json()
    all_media = resp.get("media_extended", [])
    if not all_media:
        return False
        
    def download_item(args):
        i, item = args
        try:
            item_url = item.get("url")
            data = requests.get(item_url, timeout=15).content
            ext = "mp4" if item.get("type") in ["video", "gif"] else "jpg"
            with open(os.path.join(download_dir, f"tw_{i}.{ext}"), "wb") as f:
                f.write(data)
        except Exception as _exc:
            logging.debug("Download item failed: %s", _exc)
        
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(download_item, enumerate(all_media))


def _get_cached_tt_topic(username: str, chat_str: str, tt_topics: dict) -> tuple:
    import json
    topic_id = None
    if os.path.exists("tiktok_takip.json"):
        try:
            with open("tiktok_takip.json", "r", encoding="utf-8") as fh:
                tt_db = json.load(fh)
                if "users" in tt_db and username in tt_db["users"]:
                    topic_id = tt_db["users"][username].get("topic_id")
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)

    if not topic_id and chat_str in tt_topics and username in tt_topics[chat_str]:
        topic_id = tt_topics[chat_str][username]
    return topic_id


async def _resolve_tiktok_topic(client, url, hedef_chat, hedef_konu, username):
    """TikTok kullanıcısı için forum konu ID'sini belirler."""
    if not username or not str(hedef_chat).startswith("-100"):
        return hedef_konu
    import json
    from utils import create_forum_topic_helper

    tt_topics = {}
    if os.path.exists("tt_topics_db.json"):
        try:
            with open("tt_topics_db.json", "r", encoding="utf-8") as fh:
                tt_topics = json.load(fh)
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)

    chat_str = str(hedef_chat)
    topic_id = _get_cached_tt_topic(username, chat_str, tt_topics)

    if not topic_id:
        topic_id = await create_forum_topic_helper(client, hedef_chat, f"TT: {username}")
        if topic_id:
            tt_topics.setdefault(chat_str, {})[username] = topic_id
            try:
                with open("tt_topics_db.json", "w", encoding="utf-8") as fh:
                    json.dump(tt_topics, fh, ensure_ascii=False, indent=4)
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)

    return topic_id if topic_id else hedef_konu


async def _send_media_files(client, dosyalar, hedef_chat, hedef_konu):
    """Dosya listesini Telegram'a gönderir (fotoğraf, video veya belge)."""
    if len(dosyalar) > 1:
        for chunk_start in range(0, len(dosyalar), 10):
            chunk = dosyalar[chunk_start:chunk_start + 10]
            media_group = []
            for dosya_yolu in chunk:
                ext = dosya_yolu.lower().split('.')[-1]
                if ext in ('jpg', 'jpeg', 'png', 'webp'):
                    media_group.append(InputMediaPhoto(dosya_yolu))
                elif ext in ('mp4', 'mkv', 'webm', 'mov'):
                    media_group.append(InputMediaVideo(dosya_yolu))
                else:
                    media_group.append(InputMediaDocument(dosya_yolu))
            await client.send_media_group(chat_id=hedef_chat, media=media_group, reply_to_message_id=hedef_konu)
            await asyncio.sleep(2)
    else:
        dosya_yolu = dosyalar[0]
        ext = dosya_yolu.lower().split('.')[-1]
        if ext in ('jpg', 'jpeg', 'png', 'webp'):
            await client.send_photo(chat_id=hedef_chat, photo=dosya_yolu, reply_to_message_id=hedef_konu)
        elif ext in ('mp4', 'mkv', 'webm', 'mov'):
            await client.send_video(chat_id=hedef_chat, video=dosya_yolu, reply_to_message_id=hedef_konu)
        else:
            await client.send_document(chat_id=hedef_chat, document=dosya_yolu, reply_to_message_id=hedef_konu)


async def _process_single_social_url(client, url, download_dir, hedef_chat, hedef_konu):
    """Tek bir sosyal medya bağlantısını indirip hedefe yükler."""
    username = None
    if "tiktok.com" in url:
        username = await asyncio.to_thread(download_tiktok_tikwm, url, download_dir)
    elif "x.com" in url or "twitter.com" in url:
        await asyncio.to_thread(download_twitter_media, url, download_dir)
    else:
        await asyncio.to_thread(download_with_ytdlp, url, download_dir)

    hedef_konu_mevcut = await _resolve_tiktok_topic(client, url, hedef_chat, hedef_konu, username)

    dosyalar = [
        os.path.join(download_dir, dosya)
        for dosya in os.listdir(download_dir)
        if not dosya.endswith(('.part', '.ytdl'))
    ]

    if not dosyalar:
        raise ValueError("Medya bulunamadı veya engellendi (Gizli profil vb).")

    await _send_media_files(client, dosyalar, hedef_chat, hedef_konu_mevcut)


@ggr.cmd(["yt", "tt", "x", "rd"], info="YouTube, TikTok, Twitter ve Reddit medyalarını indirir.", usage=".yt [link] | .tt [link]", category="Araçlar")
async def sosyal_indirici(client, message):
    """YouTube, TikTok, Twitter ve Reddit linklerini toplu/tekil indirip Telegram'a yükler."""
    links = message.text.split()[1:]
    logging.info("Kullanıcı %s sosyal indirme komutunu çalıştırdı. İstekler: %s", message.from_user.id if message.from_user else 'Bilinmeyen', links)
    if not links:
        try:
            await message.edit_text("❌ Kullanım: `.yt link1 link2` veya `.ig link` vb.")
        except Exception:
            await message.reply_text("❌ Kullanım: `.yt link1 link2` veya `.ig link` vb.")
        return

    try:
        durum_mesaji = await message.edit_text(f"⏳ {len(links)} adet medya aranıyor ve indiriliyor...")
    except Exception:
        durum_mesaji = await message.reply_text(f"⏳ {len(links)} adet medya aranıyor ve indiriliyor...")

    hedef_chat = message.chat.id
    hedef_konu = getattr(message, "message_thread_id", None)
    if not hedef_konu and message.reply_to_message:
        hedef_konu = getattr(message.reply_to_message, "message_thread_id", None) or message.reply_to_message.id
    if not hedef_konu:
        hedef_konu = message.id

    basarili = 0
    hatali = 0
    hata_loglari = []

    for url_idx, url in enumerate(links, 1):
        await durum_mesaji.edit_text(f"⏳ İndiriliyor ({url_idx}/{len(links)})...\n🔗 `{url}`")

        indirme_idsi = str(uuid.uuid4())
        download_dir = os.path.join("downloads", indirme_idsi)
        os.makedirs(download_dir, exist_ok=True)

        try:
            await _process_single_social_url(client, url, download_dir, hedef_chat, hedef_konu)
            basarili += 1
            await asyncio.sleep(2)
        except Exception as indir_err:
            hatali += 1
            hata_loglari.append(f"🔗 `{url}`: `{str(indir_err)[:150]}`")
        finally:
            if os.path.exists(download_dir):
                try:
                    shutil.rmtree(download_dir)
                except Exception as _exc:
                    logging.debug("Suppressed: %s", _exc)

    sonuc_metni = f"✅ <b>İşlem Tamamlandı!</b>\n📥 İndirilen Link: <code>{basarili}</code> | ❌ Hatala: <code>{hatali}</code>\n"
    if hata_loglari:
        sonuc_metni += "\n📋 <b>HATA RAPORU:</b>\n" + "\n".join(hata_loglari)
    if len(sonuc_metni) > 4000:
        sonuc_metni = sonuc_metni[:4000] + "\n... (Liste kırpıldı)"

    await durum_mesaji.edit_text(sonuc_metni)


# ================= INSTAGRAM & RAPIDAPI =================
# Instagram ve RapidAPI modülü plugins/instagram.py dosyasına ayrılmıştır.


async def _send_single_tg_media(client, m, hedef_chat, hedef_konu):
    """Tekil bir Telegram medya mesajını indirip hedefe gönderir."""
    dosya_yolu = None
    try:
        dosya_yolu = await client.download_media(m)
        if not (dosya_yolu and os.path.exists(dosya_yolu) and os.path.getsize(dosya_yolu) > 0):
            return False, "Telegram boş dosya indirdi, es geçildi."

        if m.photo:
            await client.send_photo(chat_id=hedef_chat, photo=dosya_yolu, reply_to_message_id=hedef_konu)
        elif m.video:
            await client.send_video(chat_id=hedef_chat, video=dosya_yolu, reply_to_message_id=hedef_konu)
        elif getattr(m, "animation", None):
            await client.send_animation(chat_id=hedef_chat, animation=dosya_yolu, reply_to_message_id=hedef_konu)
        elif getattr(m, "audio", None) or getattr(m, "voice", None):
            await client.send_audio(chat_id=hedef_chat, audio=dosya_yolu, reply_to_message_id=hedef_konu)
        elif getattr(m, "document", None):
            await client.send_document(chat_id=hedef_chat, document=dosya_yolu, reply_to_message_id=hedef_konu)
        elif getattr(m, "video_note", None):
            await client.send_video_note(chat_id=hedef_chat, video_note=dosya_yolu, reply_to_message_id=hedef_konu)
        return True, None
    finally:
        if dosya_yolu and os.path.exists(dosya_yolu):
            try:
                os.remove(dosya_yolu)
            except Exception as _exc:
                logging.debug("Temp file remove failed: %s", _exc)


def _extract_tg_links(text_to_search: str) -> list:
    links = re.findall(r'https://t\.me/(?:c/)?[a-zA-Z0-9_/-]+', text_to_search or "")
    return list(dict.fromkeys([link.split("?")[0].rstrip("/") for link in links]))


def _resolve_target_thread(message):
    hedef_chat = message.chat.id
    hedef_konu = getattr(message, "message_thread_id", None)
    if not hedef_konu and message.reply_to_message:
        hedef_konu = getattr(message.reply_to_message, "message_thread_id", None) or message.reply_to_message.id
    if not hedef_konu:
        hedef_konu = message.id
    return hedef_chat, hedef_konu


async def _fetch_single_tg_msg(client, link, durum_mesaji, i, total_links):
    link_path = link.split("t.me/")[1].split("?")[0].strip("/")
    path_parts = link_path.split("/")
    msg_id = int(path_parts[-1])
    chat_id_super = int("-100" + path_parts[1]) if path_parts[0] == "c" else path_parts[0]

    try:
        msg = await client.get_messages(chat_id_super, msg_id)
    except Exception as e:
        if "Peer" in str(e).capitalize() or "PEER_ID_INVALID" in str(e):
            await durum_mesaji.edit_text(f"🕵️‍♂️ Gizli grup aranıyor ({i}/{total_links})...")
            msg = None
        else:
            raise e

    if not msg or getattr(msg, "empty", False) or not getattr(msg, "media", None):
        raise Exception("Mesaj bos veya yazi mesaji iceriyor.")

    if getattr(msg, "media_group_id", None):
        try:
            return await client.get_media_group(msg.chat.id, msg_id)
        except Exception:
            return [msg]
    return [msg]


async def _process_tg_album(client, album_mesajlari, hedef_chat, hedef_konu, hata_loglari):
    for m in album_mesajlari:
        try:
            ok, err_msg = await _send_single_tg_media(client, m, hedef_chat, hedef_konu)
            if not ok:
                hata_loglari.append(f"❌ Msg {m.id}: {err_msg}")
        except Exception as e:
            hata_loglari.append(f"❌ Msg {m.id}: Yüklenirken Hata - {str(e)}")


@ggr.cmd(["tg", "indir"], info="Telegram medya mesajını veya bağlantısını indirip Yedek grubuna gönderir.", usage=".tg [link] veya yanıta .indir", category="Araçlar")
async def manuel_linkten_tg(client, message):
    logging.info("Kullanıcı %s .tg komutunu çalıştırdı.", message.from_user.id if message.from_user else 'Bilinmeyen')
    try:
        durum_mesaji = await message.edit_text("⏳ Sistem yanıt verdi, linkler taranıyor...")
        text_to_search = message.text or ""
        if message.reply_to_message:
            text_to_search += " " + (message.reply_to_message.text or message.reply_to_message.caption or "")

        links = _extract_tg_links(text_to_search)
        if not links:
            await durum_mesaji.edit_text("❌ Kullanım: .tg https://t.me/...")
            return

        await durum_mesaji.edit_text(f"⏳ Toplu indirme başlatılıyor... Toplam Link: {len(links)}")
        hedef_chat, hedef_konu = _resolve_target_thread(message)

        basarili, hatali = 0, 0
        hata_loglari = []

        for i, link in enumerate(links, 1):
            try:
                await durum_mesaji.edit_text(f"⏳ İndiriliyor ({i}/{len(links)})...")
                album = await _fetch_single_tg_msg(client, link, durum_mesaji, i, len(links))
                await _process_tg_album(client, album, hedef_chat, hedef_konu, hata_loglari)
                basarili += 1
                await asyncio.sleep(2)
            except Exception as e:
                hatali += 1
                hata_loglari.append(f"❌ Msg {link.split('/')[-1]}: {str(e)}")

        sonuc_metni = f"✅ <b>İşlem Tamamlandı!</b>\n📥 İşlenen Link: <code>{basarili}</code> | ❌ Hatalı: <code>{hatali}</code>\n"
        if hata_loglari:
            sonuc_metni += "\n📋 <b>HATA RAPORU:</b>\n" + "\n".join(hata_loglari)
            
        if len(sonuc_metni) > 4000:
            sonuc_metni = sonuc_metni[:4000] + "\n... (Liste kirpildi)"

        await durum_mesaji.edit_text(sonuc_metni)
    except Exception as e: 
        await ggr.log(f"🚨 .tg komutu kritik hatası:\n{str(e)}")
        await message.edit_text(f"Kritik Hata: {str(e)}")


# ================= WHOIS & PROFİL ANALİZİ =================
async def _resolve_whois_target_user(client, message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    if len(message.command) > 1:
        param = message.command[1].strip()
        if param.isdigit() or (param.startswith("-") and param[1:].isdigit()):
            return await client.get_users(int(param))
        return await client.get_users(param)
    return message.from_user


def _format_whois_text(hedef_user, chat_detay, ortak_sayisi):
    dc_id = getattr(hedef_user, "dc_id", None)
    ad = ggr.safe_html(hedef_user.first_name or "")
    soyad = ggr.safe_html(hedef_user.last_name or "")
    kullanici_adi = f"@{hedef_user.username}" if hedef_user.username else "Yok"
    bio = ggr.safe_html(getattr(chat_detay, "bio", "") or "Biyografi yok")
    bot_mu = "Evet 🤖" if hedef_user.is_bot else "Hayır 👤"
    dogrulanmis = "Evet ✅" if getattr(hedef_user, "is_verified", False) else "Hayır ❌"
    scam = "Evet ⚠️ (Şüpheli)" if (getattr(hedef_user, "is_scam", False) or getattr(hedef_user, "is_fake", False)) else "Temiz 🛡️"
    premium = "Evet ⭐" if getattr(hedef_user, "is_premium", False) else "Hayır"

    return (
        f"👤 <b>KULLANICI BİLGİSİ (WHOIS)</b>\n"
        f"────────────────────────\n"
        f"• <b>İsim:</b> {ad} {soyad}\n"
        f"• <b>Kullanıcı Adı:</b> {kullanici_adi}\n"
        f"• <b>Kullanıcı ID:</b> <code>{hedef_user.id}</code>\n"
        f"• <b>Kalıcı Profil:</b> <a href=\"tg://user?id={hedef_user.id}\">Profili Aç</a>\n"
        f"• <b>Veri Merkezi (DC):</b> <code>{dc_id or 'Bilinmiyor'}</code>\n"
        f"• <b>Tür:</b> {bot_mu}\n"
        f"• <b>Doğrulanmış:</b> {dogrulanmis}\n"
        f"• <b>Premium:</b> {premium}\n"
        f"• <b>Güvenlik Durumu:</b> {scam}\n"
        f"• <b>Ortak Gruplar:</b> <code>{ortak_sayisi}</code> adet\n"
        f"• <b>Biyografi:</b> <i>{bio}</i>"
    )


@ggr.cmd(["whois", "info"], info="Kullanıcı hakkında detaylı kimlik ve profil analizi yapar.", usage=".whois [kullanıcı_adı | id | yanıtla]", category="Araçlar")
async def whois_user(client, message):
    try:
        hedef_user = await _resolve_whois_target_user(client, message)
    except Exception as e:
        await message.edit_text(f"❌ Kullanıcı bulunamadı: <code>{e}</code>")
        return

    if not hedef_user:
        await message.edit_text(ggr.t("whois_user_not_found"))
        return

    durum = await message.edit_text(ggr.t("whois_searching"))

    try:
        chat_detay = None
        try:
            chat_detay = await client.get_chat(hedef_user.id)
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)

        ortak_sayisi = 0
        try:
            ortak = await client.get_common_chats(hedef_user.id)
            ortak_sayisi = len(ortak)
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)

        metin = _format_whois_text(hedef_user, chat_detay, ortak_sayisi)
        await durum.edit_text(metin, disable_web_page_preview=True)
    except Exception as e:
        await durum.edit_text(ggr.t("err_general", error=str(e)))

# ================= OCR (GÖRSELDEN METİN OKUMA) =================
@ggr.cmd("ocr", info="Yanıtlanan görseldeki yazıları okur (OCR).", usage="Görsele yanıtlayarak: .ocr [dil]", category="Araçlar")
async def ocr_read(client, message):
    if not message.reply_to_message or not (message.reply_to_message.photo or message.reply_to_message.document):
        await message.edit_text(ggr.t("err_image_required"))
        return

    lang = "tur"
    if len(message.command) > 1:
        lang = message.command[1].lower()

    durum = await message.edit_text(ggr.t("ocr_reading"))

    temp_file = None
    try:
        temp_file = await client.download_media(message.reply_to_message)
        if not temp_file or not os.path.exists(temp_file):
            await durum.edit_text(ggr.t("err_image_required"))
            return

        with open(temp_file, "rb") as f:
            file_data = f.read()

        resp = await asyncio.to_thread(
            requests.post,
            "https://api.ocr.space/parse/image",
            files={"filename": ("ocr.jpg", file_data)},
            data={"apikey": "helloworld", "language": lang, "isOverlayRequired": False},
            timeout=30
        )

        res_json = resp.json()
        parsed_results = res_json.get("ParsedResults", [])
        if parsed_results:
            okunan = parsed_results[0].get("ParsedText", "").strip()
            if okunan:
                metin = (
                    ggr.t("ocr_result_header") +
                    f"<code>{ggr.safe_html(okunan[:3900])}</code>"
                )
                await durum.edit_text(metin)
            else:
                await durum.edit_text(ggr.t("ocr_no_text"))
        else:
            hata = res_json.get("ErrorMessage", ["Bilinmeyen hata"])
            hata_mesaji = hata[0] if isinstance(hata, list) else str(hata)
            await durum.edit_text(ggr.t("err_general", error=hata_mesaji))
    except Exception as e:
        await durum.edit_text(ggr.t("err_general", error=str(e)))
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)


