# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: TikTok Media & Live Stream Downloader
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import sys
import os
import json
import time
import asyncio
import subprocess
import shutil
import psutil
import logging
from pyrogram import Client, filters
from utils import ggr, get_yedek_grup_id, ayar_getir
from TikTokLive import TikTokLiveClient

def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except Exception as _exc:
        logging.debug("Suppressed: %s", _exc)

ggr_tiktok_db_file = "tiktok_takip.json"
ggr_recording_users = {} # {username: True}
ggr_recording_procs = {} # {username: subprocess_ptr}
ggr_record_cooldown = {} # {username: timestamp_until_next_try}
ggr_last_post_check = {} # {username: timestamp}
ggr_post_check_interval = 300 # 5 dakika (300 saniye)
RECORDING_USERS = ggr_recording_users
RECORDING_PROCS = ggr_recording_procs
RECORD_COOLDOWN = ggr_record_cooldown
LAST_POST_CHECK = ggr_last_post_check
POST_CHECK_INTERVAL = ggr_post_check_interval

def db_yukle():
    if not os.path.exists(ggr_tiktok_db_file):
        default = {"users": {}, "target_chat": ggr.backup_chat_id()}
        with open(ggr_tiktok_db_file, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    try:
        with open(ggr_tiktok_db_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data.get("users"), list):
                new_users = {}
                for u in data["users"]:
                    new_users[u] = {"topic_id": None, "last_post_id": None}
                data["users"] = new_users
            return data
    except Exception:
        return {"users": {}, "target_chat": ggr.backup_chat_id()}

def db_kaydet(data):
    with open(ggr_tiktok_db_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    # Bulut yedekleme tetikleyici (Kayıtlı Mesajlar'daki TEK kalıcı mesaja yazar)
    try:
        from utils import bot_client
        if bot_client:
            loop = asyncio.get_running_loop()
            loop.create_task(ggr.sync_cloud(bot_client))
    except Exception as _exc:
        logging.debug("Suppressed: %s", _exc)

async def bulut_db_yukle_tiktok(client):
    """TikTok takip listesini ve çerezlerini Telegram Kayıtlı Mesajlar'daki tek bulut DB'den indirir."""
    try:
        from utils import tek_bulut_db_yukle
        await tek_bulut_db_yukle(client)
        # Diskte yoksa ama ayarlar veritabanında varsa diske geri yaz
        saved_cookie = ggr.get("tiktok_cookie")
        if saved_cookie and not os.path.exists("tiktok_cookies.txt"):
            with open("tiktok_cookies.txt", "w", encoding="utf-8") as f:
                f.write(saved_cookie)
            logging.info("🍪 TikTok çerezleri bulut veritabanından diske başarıyla geri yüklendi.")
    except Exception as e:
        logging.error("TikTok bulut veritabanı okuma hatası: %s", e)


def _inject_tiktok_cookies(live_client):
    """Mevcut tiktok_cookies.txt dosyasindan session ID'yi live_client'a enjekte eder."""
    try:
        if not os.path.exists("tiktok_cookies.txt"):
            return
        with open("tiktok_cookies.txt", "r") as f:
            for line in f:
                if "sessionid" in line and not line.startswith("#"):
                    parts = line.strip().split("\t")
                    if len(parts) >= 7 and parts[5] == "sessionid":
                        session_id = parts[6]
                        live_client.web.cookies.set("sessionid", session_id)
                        if hasattr(live_client.web, 'httpx_client'):
                            live_client.web.httpx_client.cookies.set("sessionid", session_id)
                        break
    except Exception as e:
        logging.error("Cookie injection error: %s", e)


async def _extract_stream_url(live_client, username):
    """TikTok API'sinden direkt stream URL'sini cekmeye calisir."""
    target_url = f"https://www.tiktok.com/@{username}/live"
    try:
        from TikTokLive.client.web.routes.fetch_room_id_api import FetchRoomIdAPIRoute
        import json
        room_data = await FetchRoomIdAPIRoute.fetch_user_room_data(live_client.web, username)
        if "data" not in room_data or "liveRoom" not in room_data["data"]:
            return target_url, False
        lr = room_data["data"]["liveRoom"]
        if "streamData" not in lr or "pull_data" not in lr["streamData"]:
            return target_url, False
        stream_data = json.loads(lr["streamData"]["pull_data"]["stream_data"])
        data_obj = stream_data.get("data", {})
        priority = ["origin", "hd", "sd", "ld"] + [q for q in data_obj if q not in ("origin", "hd", "sd", "ld")]
        for quality in priority:
            if quality not in data_obj or "main" not in data_obj[quality]:
                continue
            main_urls = data_obj[quality]["main"]
            if main_urls.get("flv"):
                logging.info("\u2705 @%s direkt FLV stream URL alindi (kalite: %s)", username, quality)
                return main_urls["flv"], True
            if main_urls.get("hls"):
                logging.info("\u2705 @%s direkt HLS stream URL alindi (kalite: %s)", username, quality)
                return main_urls["hls"], True
    except Exception as ex:
        logging.error("Stream URL extraction error: %s", ex)
    return target_url, False


def _build_record_cmd(output_file_base, target_url, is_direct_stream):
    """Kayit icin yt-dlp komut listesini olusturur."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--impersonate", "chrome",
        "--retries", "2",
        "--fragment-retries", "2",
    ]
    if os.path.exists("tiktok_cookies.txt"):
        cmd.extend(["--cookies", "tiktok_cookies.txt"])
    if is_direct_stream:
        cmd.extend(["-o", f"{output_file_base}.%(ext)s", target_url])
    else:
        cmd.extend(["--downloader-args", "ffmpeg:-live_start_index -1"])
        cmd.extend(["-o", f"{output_file_base}.%(ext)s", "--remux-video", "mp4", target_url])
    return cmd


async def _check_disk_space(client, username, download_dir, target_chat, topic_id):
    """Disk alanini kontrol eder; yetersizse True doner."""
    try:
        disk_stat = shutil.disk_usage(download_dir if os.path.exists(download_dir) else ".")
        free_mb = disk_stat.free / (1024 * 1024)
        if free_mb < 700:
            logging.warning("\u26a0\ufe0f Dusuk disk alani (%.1f MB)! @%s kaydi guvenle tamamlaniyor.", free_mb, username)
            await client.send_message(
                target_chat,
                f"\u26a0\ufe0f <b>Disk Alani Korumasi:</b> Sunucu bos alani kritik seviyede ({free_mb:.1f} MB). Disk tasmasini onlemek icin kayit sonlandirildi.",
                reply_to_message_id=topic_id
            )
            return True
    except Exception as _exc:
        logging.debug("Disk kontrol hatasi: %s", _exc)
    return False


async def _run_recording_proc(client, cmd, username, target_chat, topic_id):
    """yt-dlp kayit surecini baslatir, 15dk bekler, timeout'ta graceful shutdown yapar."""
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    ggr_recording_procs[username] = proc
    has_fatal_error = False
    try:
        _, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=900)
        if proc.returncode != 0 and stderr_data:
            err_msg = stderr_data.decode('utf-8', errors='ignore')
            offline_kw = ("offline", "not currently live", "this livestream has ended")
            if "error:" in err_msg.lower() and not any(kw in err_msg.lower() for kw in offline_kw):
                await client.send_message(
                    target_chat,
                    f"\u274c <b>Kayit Hatasi</b> (<code>@{username}</code>):\n<code>{ggr.safe_html(err_msg[-800:])}</code>",
                    reply_to_message_id=topic_id
                )
            has_fatal_error = True
    except asyncio.TimeoutError:
        try:
            import signal
            proc.send_signal(signal.SIGINT)
            await asyncio.wait_for(proc.wait(), timeout=15)
        except Exception:
            try:
                kill_process_tree(proc.pid)
                await proc.wait()
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)
    except Exception as wait_ex:
        await client.send_message(target_chat, f"\U0001f6e0 <b>Bekleme Hatasi:</b> <code>{wait_ex}</code>", reply_to_message_id=topic_id)
    return proc, has_fatal_error


def _locate_candidate_source(download_dir, output_file_base, part_no):
    for ext in (".flv", ".ts", ".mp4.part", ".flv.part", ".mkv"):
        candidate = f"{output_file_base}{ext}"
        if os.path.exists(candidate) and os.path.getsize(candidate) > 100:
            return candidate

    try:
        part_prefix = f"part_{part_no:03d}"
        for fname in os.listdir(download_dir):
            if fname.startswith(part_prefix) and not fname.endswith(".ytdl"):
                candidate = os.path.join(download_dir, fname)
                if os.path.getsize(candidate) > 100:
                    return candidate
    except Exception as _exc:
        logging.debug("Suppressed: %s", _exc)
    return None


async def _remux_candidate_to_mp4(found_source, output_file):
    try:
        logging.info("Manuel remux: %s -> %s", found_source, output_file)
        remux_proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", found_source, "-c", "copy", output_file,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        await remux_proc.communicate()
        if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
            os.remove(found_source)
            logging.info("\u2705 Remux basarili: %s", output_file)
        else:
            logging.warning("Remux basarisiz, kaynak dosya kullanilacak: %s", found_source)
            if os.path.exists(output_file):
                os.remove(output_file)
            os.rename(found_source, output_file)
    except Exception as e:
        logging.error("Manuel remux hatasi: %s", e)
        try:
            os.rename(found_source, output_file)
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)


async def _find_and_remux_output(download_dir, output_file_base, part_no):
    """Indirilen dosyayi bulur ve gerekirse MP4'e remux eder."""
    output_file = f"{output_file_base}.mp4"
    if os.path.exists(output_file):
        return output_file
    found_source = _locate_candidate_source(download_dir, output_file_base, part_no)
    if not found_source or found_source == output_file:
        return output_file
    await _remux_candidate_to_mp4(found_source, output_file)
    return output_file


async def _upload_video_part(client, output_file, username, part_no, target_chat, topic_id, proc):
    """Kaydedilen video parcasini Telegram'a yukler. Devam edilmeli mi doner."""
    if os.path.exists(output_file):
        try:
            sz = os.path.getsize(output_file)
            if sz < 100:
                raise Exception(f"Video dosyasi cok kucuk veya bos ({sz} byte).")
            await client.send_document(
                chat_id=target_chat,
                document=output_file,
                caption=f"\U0001f3a5 <b>TikTok Canli Yayin Parcasi</b>\n\U0001f464 <code>@{username}</code>\n\U0001f4e6 Dosya: <code>part_{part_no:03d}.mp4</code>",
                reply_to_message_id=topic_id
            )
            os.remove(output_file)
        except Exception as e:
            await client.send_message(target_chat, f"\U0001f6e0 <b>Yukleme Hatasi:</b> <code>{e}</code>", reply_to_message_id=topic_id)
            try:
                os.remove(output_file)
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)
        return True
    if proc.returncode != 0:
        await client.send_message(
            target_chat,
            f"\u2139\ufe0f <b>Bilgi:</b> Yayin su an cevrimdisi veya bitti (<code>@{username}</code>). 5 dakika boyunca tekrar denenmeyecek.",
            reply_to_message_id=topic_id
        )
        ggr_record_cooldown[username] = time.time() + 300
    return False


async def record_tiktok_stream(client, username, target_chat, topic_id=None):
    """TikTok canli yayinini indirir ve parcalar halinde yukler"""
    download_dir = f"downloads/tiktok_{username}"
    os.makedirs(download_dir, exist_ok=True)
    logging.info("\U0001f534 @%s canli yayin kaydedilmeye baslaniyor...", username)
    try:
        await client.send_message(
            chat_id=target_chat,
            text=f"\U0001f534 <b>Canli Yayin Basladi!</b>\n\U0001f464 <code>@{username}</code> su an yayinda, kayit arka planda baslatildi. \U0001f3a5",
            reply_to_message_id=topic_id
        )
    except Exception as e:
        logging.error("TikTok bildirim hatasi: %s", e)

    ggr_recording_users[username] = True
    try:
        part_no = 1
        while username in ggr_recording_users:
            live_client = TikTokLiveClient(unique_id=username)
            _inject_tiktok_cookies(live_client)
            is_live = await live_client.is_live()
            if not is_live:
                break
            output_file_base = os.path.join(download_dir, f"part_{part_no:03d}")
            target_url, is_direct_stream = await _extract_stream_url(live_client, username)
            if not is_direct_stream:
                logging.warning("\u26a0\ufe0f @%s direkt stream URL alinamadi, webpage URL kullanilacak", username)
            if await _check_disk_space(client, username, download_dir, target_chat, topic_id):
                break
            cmd = _build_record_cmd(output_file_base, target_url, is_direct_stream)
            proc, has_fatal_error = await _run_recording_proc(client, cmd, username, target_chat, topic_id)
            output_file = await _find_and_remux_output(download_dir, output_file_base, part_no)
            should_continue = await _upload_video_part(client, output_file, username, part_no, target_chat, topic_id, proc)
            if not should_continue:
                break
            part_no += 1
            if has_fatal_error:
                break
            await asyncio.sleep(5)
    except Exception as e:
        await client.send_message(target_chat, f"\U0001f6e0 <b>Kayit Dongusu Coktu:</b> <code>{e}</code>", reply_to_message_id=topic_id)
        logging.error("TikTok kayit tetikleme hatasi: %s - %s", type(e).__name__, e)
    finally:
        ggr_recording_users.pop(username, None)
        ggr_recording_procs.pop(username, None)
        if os.path.exists(download_dir):
            try:
                shutil.rmtree(download_dir)
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)
        logging.info("\u26ab @%s canli yayin kaydi tamamlandi ve temizlendi.", username)
        try:
            await client.send_message(
                chat_id=target_chat,
                text=f"\u26ab <b>Canli Yayin Bitti!</b>\n\U0001f464 <code>@{username}</code> yayini kapatti. Tum video parcalari yukarida paylasildi. \U0001f3ac",
                reply_to_message_id=topic_id
            )
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)


async def _download_tiktok_media_files(data: dict, download_dir: str) -> list:
    import requests
    dosyalar = []
    if "images" in data and isinstance(data["images"], list) and len(data["images"]) > 0:
        from concurrent.futures import ThreadPoolExecutor

        def download_img(args):
            i, img_url = args
            try:
                img_data = requests.get(img_url, timeout=10).content
                path = os.path.join(download_dir, f"tiktok_{i}.jpg")
                with open(path, "wb") as f:
                    f.write(img_data)
                return path
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)
                return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            dl_list = list(executor.map(download_img, enumerate(data["images"])))
        dosyalar = [d for d in dl_list if d]

    elif "play" in data:
        try:
            vid_data = await asyncio.to_thread(requests.get, data["play"], timeout=15)
            path = os.path.join(download_dir, "tiktok_video.mp4")
            with open(path, "wb") as f:
                f.write(vid_data.content)
            dosyalar.append(path)
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)
    return dosyalar


async def _send_single_tiktok_file(client, file_path, caption, target_chat, topic_id):
    ext = file_path.lower().split('.')[-1]
    kwargs = {"chat_id": target_chat, "caption": caption}
    if topic_id:
        kwargs["reply_to_message_id"] = topic_id
    if ext in ['jpg', 'jpeg', 'png', 'webp']:
        await client.send_photo(photo=file_path, **kwargs)
    elif ext in ['mp4', 'mkv', 'webm', 'mov']:
        await client.send_video(video=file_path, **kwargs)


async def _send_tiktok_media_group(client, dosyalar, caption, target_chat, topic_id):
    from pyrogram.types import InputMediaPhoto, InputMediaVideo
    for i in range(0, len(dosyalar), 10):
        chunk = dosyalar[i:i + 10]
        media_group = []
        for idx, d in enumerate(chunk):
            ext = d.lower().split('.')[-1]
            cap = caption if idx == 0 else ""
            if ext in ['jpg', 'jpeg', 'png', 'webp']:
                media_group.append(InputMediaPhoto(d, caption=cap))
            elif ext in ['mp4', 'mkv', 'webm', 'mov']:
                media_group.append(InputMediaVideo(d, caption=cap))

        if topic_id:
            await client.send_media_group(chat_id=target_chat, media=media_group, reply_to_message_id=topic_id)
        else:
            await client.send_media_group(chat_id=target_chat, media=media_group)
        await asyncio.sleep(2)


async def download_and_send_tiktok_post(client, username, video_id, title, target_chat, topic_id=None):
    import uuid
    indirme_idsi = str(uuid.uuid4())
    download_dir = os.path.join("downloads", indirme_idsi)
    os.makedirs(download_dir, exist_ok=True)

    url = f"https://www.tiktok.com/@{username}/video/{video_id}"
    api_url = f"https://tikwm.com/api/?url={url}&hd=1"
    caption = f"🎵 <b>Yeni TikTok Gönderisi</b>\n👤 <code>@{username}</code>\n\n📝 {ggr.safe_html(title)}"

    try:
        from curl_cffi import requests as c_requests
        resp = await asyncio.to_thread(c_requests.get, api_url, impersonate="chrome110")
        resp_json = resp.json()
        if resp_json.get("code") != 0:
            return False

        data = resp_json.get("data", {})
        dosyalar = await _download_tiktok_media_files(data, download_dir)
        if not dosyalar:
            return False

        if len(dosyalar) > 1:
            await _send_tiktok_media_group(client, dosyalar, caption, target_chat, topic_id)
        else:
            await _send_single_tiktok_file(client, dosyalar[0], caption, target_chat, topic_id)
        return True
    except Exception as e:
        logging.error("TikTok indirme hatası (@%s): %s", username, e)
        return False
    finally:
        try:
            import shutil
            shutil.rmtree(download_dir)
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)

async def _check_live_for_user(client, username, target_chat, topic_id):
    """Tek bir kullanıcının canlı yayın durumunu kontrol eder."""
    if username in ggr_recording_users:
        return
    if time.time() < ggr_record_cooldown.get(username, 0):
        return  # Cooldown devrede
    try:
        live_client = TikTokLiveClient(unique_id=username)
        if await live_client.is_live():
            asyncio.create_task(record_tiktok_stream(client, username, target_chat, topic_id))
    except Exception as live_err:
        logging.error("TikTok canlı sorgu hatası @%s: %s - %s", username, type(live_err).__name__, live_err)


async def _check_post_for_user(client, db, username, user_data, target_chat, topic_id):
    """Tek bir kullanıcının yeni gönderilerini kontrol eder."""
    if time.time() - ggr_last_post_check.get(username, 0) <= ggr_post_check_interval:
        return
    try:
        from curl_cffi import requests as c_requests
        api_url = f"https://tikwm.com/api/user/posts?unique_id={username}&count=5"
        resp = await asyncio.to_thread(c_requests.get, api_url, impersonate="chrome110")
        resp_json = resp.json()
        ggr_last_post_check[username] = time.time()

        if not (resp_json.get("code") == 0 and "videos" in resp_json.get("data", {})):
            return

        videos = resp_json["data"]["videos"]
        if not videos:
            return

        last_post_id = user_data.get("last_post_id")
        if last_post_id is None:
            latest = videos[0]
            newest_id = str(latest.get("video_id", ""))
            title = latest.get("title", "")[:500]
            if await download_and_send_tiktok_post(client, username, newest_id, title, target_chat, topic_id):
                db["users"][username]["last_post_id"] = newest_id
                db_kaydet(db)
                logging.info("✅ @%s ilk tiktok gönderisi gönderildi ve id atandı.", username)
            return

        yeni_videolar = []
        for vid_data in videos:
            vid = str(vid_data.get("video_id", ""))
            if vid == str(last_post_id):
                break
            yeni_videolar.append(vid_data)
        yeni_videolar.reverse()

        if not yeni_videolar:
            return

        en_son_id = str(last_post_id)
        for vid_data in yeni_videolar:
            vid = str(vid_data.get("video_id", ""))
            title = vid_data.get("title", "")[:500]
            if await download_and_send_tiktok_post(client, username, vid, title, target_chat, topic_id):
                en_son_id = vid
                logging.info("✅ @%s yeni tiktok gönderisi gönderildi: %s", username, vid)
            else:
                break

        if en_son_id != str(last_post_id):
            db["users"][username]["last_post_id"] = en_son_id
            db_kaydet(db)

    except Exception as post_err:
        if "Expecting value: line 1 column 1 (char 0)" in str(post_err):
            logging.debug("TikTok post check block @%s (Olası Rate Limit / Engel)", username)
        else:
            logging.error("TikTok post check error @%s: %s", username, post_err)
        ggr_last_post_check[username] = time.time()


async def tiktok_monitor_loop(client):
    """TikTok canlı yayın ve gönderi takip döngüsü."""
    logging.info("🕵️‍♂️ TikTok Canlı Yayın Takip Motoru Başlatıldı!")
    while True:
        try:
            db = db_yukle()
            users = db.get("users", {})
            target_chat = db.get("target_chat", get_yedek_grup_id())

            for username, user_data in list(users.items()):
                topic_id = user_data.get("topic_id")
                filt = user_data.get("filter", "both")

                if not topic_id and str(target_chat).startswith("-100"):
                    try:
                        from utils import create_forum_topic_helper
                        topic_id = await create_forum_topic_helper(client, target_chat, f"TT: {username}")
                        db["users"][username]["topic_id"] = topic_id
                        db_kaydet(db)
                    except Exception as topic_err:
                        logging.error("TikTok stalker loop topic oluşturulamadı: %s", topic_err)

                if filt in ("both", "live"):
                    await _check_live_for_user(client, username, target_chat, topic_id)

                if filt in ("both", "post"):
                    await _check_post_for_user(client, db, username, user_data, target_chat, topic_id)

                await asyncio.sleep(2)

        except Exception as loop_err:
            logging.error("TikTok monitor ana döngü hatası: %s - %s", type(loop_err).__name__, loop_err)

        await asyncio.sleep(20)  # Her 20 saniyede bir kontrol et


# ================= TETİKLEYİCİ VE KOMUTLAR =================
ggr_tiktok_loop_started = False

@ggr.on(group=-99) # Gizli başlangıç tetikleyicisi
async def auto_start_tiktok_monitor(client, message):
    global ggr_tiktok_loop_started
    if not ggr_tiktok_loop_started:
        ggr_tiktok_loop_started = True
        await bulut_db_yukle_tiktok(client)
        asyncio.create_task(tiktok_monitor_loop(client))
    message.continue_propagation()


@ggr.cmd("ttcookie", info="TikTok çerezlerini kaydeder, siler veya durumunu gösterir.", usage=".ttcookie [dosya yanıtla | sessionid | sil]", category="Araçlar")
async def ttcookie_kaydet(client, message):
    args = message.text.split()[1:] if message.text else []
    
    # 1. Çerez Silme İsteği (.ttcookie sil / reset)
    if args and args[0].lower() in ["sil", "reset", "clear", "kaldir"]:
        ggr.set("tiktok_cookie", "")
        if os.path.exists("tiktok_cookies.txt"):
            try:
                os.remove("tiktok_cookies.txt")
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)
        await ggr.sync_cloud(client)
        await message.edit_text("🗑️ <b>TikTok Çerezleri Başarıyla Silindi!</b>\nBulut veritabanından temizlendi.")
        return

    cerez_icerik = None
    
    # 2. Dosya Yanıtlayarak Yükleme
    if message.reply_to_message and message.reply_to_message.document:
        try:
            indirilen = await client.download_media(message.reply_to_message, in_memory=True)
            cerez_icerik = indirilen.getvalue().decode("utf-8")
        except Exception as e:
            await message.edit_text(f"❌ Belge okunurken hata oluştu: {e}")
            return
    elif len(message.command) > 1:
        # 3. Metin veya SessionID Olarak Girme
        cerez_icerik = message.text.split(maxsplit=1)[1].strip()

    # 4. Argümansız Kullanım: Mevcut Durum veya Yardım Rehberi
    if not cerez_icerik:
        mevcut_cerez = ggr.get("tiktok_cookie")
        if mevcut_cerez or os.path.exists("tiktok_cookies.txt"):
            await message.edit_text(
                "✅ <b>TikTok Çereziniz Aktif!</b>\n\n"
                "🔒 Çerezleriniz <b>Telegram Bulut Veritabanı</b>'na kayıtlıdır. Sunucu yeniden kurulsa bile otomatik olarak geri yüklenir.\n\n"
                "• <i>Güncellemek için:</i> <code>.ttcookie [yeni_sessionid]</code> veya <code>cookies.txt</code> dosyasını yanıtlayın.\n"
                "• <i>Silmek için:</i> <code>.ttcookie sil</code>"
            )
        else:
            await message.edit_text(
                "💡 <b>TikTok Çerez (Cookie) Nasıl Eklenir?</b>\n\n"
                "Yaş kısıtlamalı ve korumalı canlı yayınları sorunsuz izleyip kaydedebilmek için hesabınızın çerezini ekleyin:\n\n"
                "1️⃣ <b>Pratik Yöntem (SessionID):</b>\n"
                "Tarayıcınızdan TikTok hesabınıza girin. F12 (Geliştirici Araçları) ➔ <b>Application</b> ➔ <b>Cookies</b> sekmesindeki <code>sessionid</code> değerini kopyalayıp yazın:\n"
                "👉 <code>.ttcookie [sessionid_değeri]</code>\n\n"
                "2️⃣ <b>Dosya Yöntemi (cookies.txt):</b>\n"
                "Cookie-Editor eklentisiyle <i>Export ➔ Netscape formatında</i> aldığınız <code>cookies.txt</code> dosyasını sohbete atıp yanıtlayarak <code>.ttcookie</code> yazın.\n\n"
                "🔒 <i>Tüm çerezler Telegram Kayıtlı Mesajlar bulut veritabanınızda kalıcı ve güvenli saklanır.</i>"
            )
        return

    # Eğer sadece tek bir sessionid verilmişse Netscape formatına otomatik dönüştür
    if "\t" not in cerez_icerik and ";" not in cerez_icerik and len(cerez_icerik.strip()) >= 16:
        sess_val = cerez_icerik.strip().strip("'\"")
        cerez_icerik = f"# Netscape HTTP Cookie File\n.tiktok.com\tTRUE\t/\tTRUE\t2147483647\tsessionid\t{sess_val}\n"

    # Diske yaz
    with open("tiktok_cookies.txt", "w", encoding="utf-8") as f:
        f.write(cerez_icerik)

    # Bulut Veritabanına (ayarlar.json & #GAGARAGOGO_TEK_BULUT_DB) kaydet
    ggr.set("tiktok_cookie", cerez_icerik)
    await ggr.sync_cloud(client)
        
    await message.edit_text(
        "✅ <b>TikTok Çerezleri (Cookies) Başarıyla Kaydedildi!</b>\n\n"
        "🔒 <b>Bulut Veritabanına Yedeklendi:</b> Sunucunuz yeniden başlasa, kapansa veya Render yeniden build alsa bile çereziniz asla kaybolmaz!\n"
        "🕵️‍♂️ Artık bot, kısıtlı veya gizli yayınları kendi hesabınız üzerinden engel yemeden kaydedecek."
    )

@ggr.cmd("tttakip", info="Bir TikTok kullanıcısını otomatik canlı yayın kayıt listesine ekler.", usage=".tttakip [kullanıcı_adı] [yayin/post]", category="Araçlar")
async def tttakip_ekle(client, message):
    if len(message.command) < 2:
        await message.edit_text("Hatalı kullanım. Örnek: <code>.tttakip kullanici_adi [yayin/post]</code>")
        return
        
    username = message.command[1].strip().lower().replace("@", "")
    filtre = "both"
    if len(message.command) > 2:
        f_arg = message.command[2].lower()
        if f_arg in ["yayin", "yayın", "live", "canlı"]: filtre = "live"
        elif f_arg in ["post", "gönderi", "gonderi"]: filtre = "post"
        
    db = db_yukle()
    target_chat = db.get("target_chat", ggr.backup_chat_id())
    topic_id = None
    
    if username in db["users"]:
        topic_id = db["users"][username].get("topic_id")
        db["users"][username]["filter"] = filtre
    else:
        db["users"][username] = {"topic_id": None, "last_post_id": None, "filter": filtre}
        
    if not topic_id and str(target_chat).startswith("-100"):
        try:
            from utils import create_forum_topic_helper
            topic_id = await create_forum_topic_helper(client, target_chat, f"TT: {username}")
            db["users"][username]["topic_id"] = topic_id
        except Exception as e:
            logging.error("Topic oluşturulamadı: %s", e)
            
    db_kaydet(db)
    
    fm = "Tümü (Yayın + Post)"
    if filtre == "live": fm = "Sadece Canlı Yayın"
    elif filtre == "post": fm = "Sadece Post"
    
    topic_msg = f" (Topic ID: {topic_id})" if topic_id else ""
    await message.edit_text(f"✅ <code>@{username}</code> TikTok takip listesine başarıyla eklendi/güncellendi!{topic_msg}\n📌 <b>Filtre:</b> {fm}")

@ggr.cmd("tttakiptencikar", info="Bir TikTok kullanıcısını kayıt listesinden çıkarır.", usage=".tttakiptencikar [kullanıcı_adı]", category="Araçlar")
async def tttakip_cikar(client, message):
    if len(message.command) < 2:
        await message.edit_text("Hatalı kullanım. Örnek: `.tttakiptencikar kullanici_adi`")
        return
        
    username = message.command[1].strip().lower().replace("@", "")
    db = db_yukle()
    
    if username not in db["users"]:
        await message.edit_text(f"👤 `@{username}` TikTok takip listesinde bulunamadı.")
        return
        
    del db["users"][username]
    db_kaydet(db)
    
    # Eğer o an kaydediliyorsa kaydı durdur
    if username in ggr_recording_users:
        ggr_recording_users.pop(username, None)
    
    if username in ggr_recording_procs:
        try:
            kill_process_tree(ggr_recording_procs[username].pid)
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)
            
    try:
        await message.edit_text(f"❌ `@{username}` TikTok takip listesinden çıkarıldı.")
    except Exception:
        await message.reply_text(f"❌ `@{username}` TikTok takip listesinden çıkarıldı.")
