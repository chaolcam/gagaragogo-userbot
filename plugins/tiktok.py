# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Automated TikTok Live Stream Monitor (plugins/tiktok.py)
# Description: Monitors target TikTok creators, automatically records live streams
#              and new posts, and uploads video recordings directly to the backup group.
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
    except:
        pass

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
    except:
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
    except:
        pass

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
        logging.error(f"TikTok bulut veritabanı okuma hatası: {e}")


async def record_tiktok_stream(client, username, target_chat, topic_id=None):
    """TikTok canlı yayınını indirir ve parçalar halinde yükler"""
    download_dir = f"downloads/tiktok_{username}"
    os.makedirs(download_dir, exist_ok=True)
    
    logging.info(f"🔴 @{username} canlı yayını kaydedilmeye başlanıyor...")
    try:
        await client.send_message(
            chat_id=target_chat,
            text=f"🔴 <b>Canlı Yayın Başladı!</b>\n👤 <code>@{username}</code> şu an yayında, kayıt arka planda başlatıldı. 🎥",
            reply_to_message_id=topic_id
        )
    except Exception as e:
        logging.error(f"TikTok bildirim hatası: {e}")
        
    ggr_recording_users[username] = True

    try:
        part_no = 1
        while username in ggr_recording_users:
            # Check if still live
            live_client = TikTokLiveClient(unique_id=username)
            
            # Inject sessionid from cookies if available
            try:
                if os.path.exists("tiktok_cookies.txt"):
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
                logging.error(f"Cookie injection error: {e}")
                
            is_live = await live_client.is_live()
            if not is_live:
                break # Yayın bitmiş
                
            output_file_base = os.path.join(download_dir, f"part_{part_no:03d}")
            
            # Try to get raw stream url to bypass webpage blocks (especially age-restricted streams)
            target_url = f"https://www.tiktok.com/@{username}/live"
            is_direct_stream = False
            try:
                from TikTokLive.client.web.routes.fetch_room_id_api import FetchRoomIdAPIRoute
                import json
                
                room_data = await FetchRoomIdAPIRoute.fetch_user_room_data(live_client.web, username)
                if "data" in room_data and "liveRoom" in room_data["data"]:
                    lr = room_data["data"]["liveRoom"]
                    if "streamData" in lr and "pull_data" in lr["streamData"]:
                        stream_data_str = lr["streamData"]["pull_data"]["stream_data"]
                        stream_data = json.loads(stream_data_str)
                        
                        data_obj = stream_data.get("data", {})
                        for quality in ["origin", "hd", "sd", "ld"]:
                            if quality in data_obj and "main" in data_obj[quality]:
                                main_urls = data_obj[quality]["main"]
                                if main_urls.get("flv"):
                                    target_url = main_urls["flv"]
                                    is_direct_stream = True
                                    logging.info(f"✅ @{username} direkt FLV stream URL alındı (kalite: {quality})")
                                    break
                                elif main_urls.get("hls"):
                                    target_url = main_urls["hls"]
                                    is_direct_stream = True
                                    logging.info(f"✅ @{username} direkt HLS stream URL alındı (kalite: {quality})")
                                    break
                        else:
                            for quality_data in data_obj.values():
                                if isinstance(quality_data, dict) and "main" in quality_data:
                                    main_urls = quality_data["main"]
                                    if main_urls.get("flv"):
                                        target_url = main_urls["flv"]
                                        is_direct_stream = True
                                        break
                                    elif main_urls.get("hls"):
                                        target_url = main_urls["hls"]
                                        is_direct_stream = True
                                        break
            except Exception as ex:
                logging.error(f"Stream URL extraction error: {ex}")
            
            if not is_direct_stream:
                logging.warning(f"⚠️ @{username} direkt stream URL alınamadı, webpage URL kullanılacak")
            
            # yt-dlp komutunu oluştur
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--impersonate", "chrome",
                "--retries", "2",
                "--fragment-retries", "2"
            ]
            
            if os.path.exists("tiktok_cookies.txt"):
                cmd.extend(["--cookies", "tiktok_cookies.txt"])
            
            if is_direct_stream:
                # Direkt stream URL'si varsa: ffmpeg ile doğrudan kaydet, remux yapma
                # yt-dlp'nin kendi remux'u "Invalid argument" hatası veriyor
                cmd.extend(["-o", f"{output_file_base}.%(ext)s", target_url])
            else:
                # Webpage URL kullanıyorsa: yt-dlp kendi remux'unu yapsın
                cmd.extend(["--downloader-args", "ffmpeg:-live_start_index -1"])
                cmd.extend(["-o", f"{output_file_base}.%(ext)s", "--remux-video", "mp4", target_url])
            
            # Disk doluluk kontrolü (Render 5GB disk sınırı koruması)
            try:
                disk_stat = shutil.disk_usage(download_dir if os.path.exists(download_dir) else ".")
                free_mb = disk_stat.free / (1024 * 1024)
                if free_mb < 700: # 700 MB'dan az boş yer kaldıysa yeni parça başlatma
                    logging.warning(f"⚠️ Düşük disk alanı ({free_mb:.1f} MB)! @{username} kaydı güvenle tamamlanıyor.")
                    await client.send_message(target_chat, f"⚠️ <b>Disk Alanı Koruması:</b> Sunucu boş alanı kritik seviyede ({free_mb:.1f} MB). Disk taşmasını önlemek için kayıt sonlandırıldı.", reply_to_message_id=topic_id)
                    break
            except: pass

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            ggr_recording_procs[username] = proc
            
            has_fatal_error = False
            try:
                # 15 dakika bekle (Render 512MB RAM & 5GB disk için optimize parça boyutu)
                _, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=900)
                
                # Eğer timeout olmazsa, yani 15 dakikadan önce biterse
                has_fatal_error = False
                if proc.returncode != 0 and stderr_data:
                    err_msg = stderr_data.decode('utf-8', errors='ignore')
                    if "error:" in err_msg.lower() and "offline" not in err_msg.lower() and "not currently live" not in err_msg.lower() and "this livestream has ended" not in err_msg.lower():
                        await client.send_message(target_chat, f"❌ <b>Kayıt Hatası</b> (<code>@{username}</code>):\n<code>{ggr.safe_html(err_msg[-800:])}</code>", reply_to_message_id=topic_id)
                    has_fatal_error = True
                    
            except asyncio.TimeoutError:
                # 15 dakika doldu, süreci sonlandır (Graceful Shutdown)
                try:
                    import signal
                    proc.send_signal(signal.SIGINT)
                    await asyncio.wait_for(proc.wait(), timeout=15)
                except:
                    try:
                        kill_process_tree(proc.pid)
                        await proc.wait()
                    except: pass
            except Exception as wait_ex:
                await client.send_message(target_chat, f"🛠 <b>Bekleme Hatası:</b> <code>{wait_ex}</code>", reply_to_message_id=topic_id)
            
            # Kaydedilen dosyayı bul ve MP4'e çevir
            output_file = f"{output_file_base}.mp4"
            
            # Önce download_dir'deki tüm dosyalara bak, part_XXX ile başlayan dosyaları topla
            found_source = None
            if not os.path.exists(output_file):
                # Olası uzantıları kontrol et
                for ext in [".flv", ".ts", ".mp4.part", ".flv.part", ".mkv"]:
                    candidate = f"{output_file_base}{ext}"
                    if os.path.exists(candidate) and os.path.getsize(candidate) > 100:
                        found_source = candidate
                        break
                
                # Hâlâ bulunamadıysa klasördeki part_XXX ile başlayan dosyaları ara
                if not found_source:
                    try:
                        part_prefix = f"part_{part_no:03d}"
                        for fname in os.listdir(download_dir):
                            if fname.startswith(part_prefix) and not fname.endswith(".ytdl"):
                                candidate = os.path.join(download_dir, fname)
                                if os.path.getsize(candidate) > 100:
                                    found_source = candidate
                                    break
                    except Exception:
                        pass
                
                # Bulunan dosyayı MP4'e çevir
                if found_source and found_source != output_file:
                    try:
                        logging.info(f"Manuel remux: {found_source} -> {output_file}")
                        remux_proc = await asyncio.create_subprocess_exec(
                            "ffmpeg", "-y", "-i", found_source, "-c", "copy", output_file,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                        )
                        remux_stderr = await remux_proc.communicate()
                        if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
                            os.remove(found_source)
                            logging.info(f"✅ Remux başarılı: {output_file}")
                        else:
                            # Remux başarısız, kaynak dosyayı doğrudan kullan
                            logging.warning(f"Remux başarısız, kaynak dosya kullanılacak: {found_source}")
                            if os.path.exists(output_file):
                                os.remove(output_file) 
                            os.rename(found_source, output_file)
                    except Exception as e:
                        logging.error(f"Manuel remux hatası: {e}")
                        try:
                            os.rename(found_source, output_file) # fallback
                        except:
                            pass
                        
            if os.path.exists(output_file):
                try:
                    # Dosya boş mu kontrol et
                    sz = os.path.getsize(output_file)
                    if sz < 100:
                        raise Exception(f"Video dosyası çok küçük veya boş ({sz} byte).")
                        
                    await client.send_document(
                        chat_id=target_chat,
                        document=output_file,
                        caption=f"🎥 <b>TikTok Canlı Yayın Parçası</b>\n👤 <code>@{username}</code>\n📦 Dosya: <code>part_{part_no:03d}.mp4</code>",
                        reply_to_message_id=topic_id
                    )
                    os.remove(output_file)
                except Exception as e:
                    await client.send_message(target_chat, f"🛠 <b>Yükleme Hatası:</b> <code>{e}</code>", reply_to_message_id=topic_id)
                    try:
                        os.remove(output_file)
                    except:
                        pass
            else:
                if proc.returncode != 0:
                    await client.send_message(target_chat, f"ℹ️ <b>Bilgi:</b> Yayın şu an çevrimdışı veya bitti (<code>@{username}</code>). 5 dakika boyunca tekrar denenmeyecek.", reply_to_message_id=topic_id)
                    ggr_record_cooldown[username] = time.time() + 300 # 5 dakika bekle
                break
            part_no += 1
            if has_fatal_error:
                break
            await asyncio.sleep(5)
            
    except Exception as e:
        await client.send_message(target_chat, f"🛠 <b>Kayıt Döngüsü Çöktü:</b> <code>{e}</code>", reply_to_message_id=topic_id)
        logging.error(f"TikTok kayıt tetikleme hatası: {type(e).__name__} - {e}")
    finally:
        ggr_recording_users.pop(username, None)
        ggr_recording_procs.pop(username, None)
        
        # Son temizlik
        if os.path.exists(download_dir):
            try:
                shutil.rmtree(download_dir)
            except:
                pass
        
        logging.info(f"⚫ @{username} canlı yayın kaydı tamamlandı ve temizlendi.")

        try:
            await client.send_message(
                chat_id=target_chat,
                text=f"⚫ <b>Canlı Yayın Bitti!</b>\n👤 <code>@{username}</code> yayını kapattı. Tüm video parçaları yukarıda paylaşıldı. 🎬",
                reply_to_message_id=topic_id
            )
        except Exception as e:
            pass

async def download_and_send_tiktok_post(client, username, video_id, title, target_chat, topic_id=None):
    from pyrogram.types import InputMediaPhoto, InputMediaVideo
    import requests
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
                except: return None
                
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
            except: pass
            
        if not dosyalar: return False
        
        if len(dosyalar) > 1:
            for i in range(0, len(dosyalar), 10):
                chunk = dosyalar[i:i + 10]
                media_group = []
                for idx, d in enumerate(chunk):
                    ext = d.lower().split('.')[-1]
                    cap = caption if idx == 0 else ""
                    if ext in ['jpg', 'jpeg', 'png', 'webp']: media_group.append(InputMediaPhoto(d, caption=cap))
                    elif ext in ['mp4', 'mkv', 'webm', 'mov']: media_group.append(InputMediaVideo(d, caption=cap))
                
                if topic_id:
                    await client.send_media_group(chat_id=target_chat, media=media_group, reply_to_message_id=topic_id)
                else:
                    await client.send_media_group(chat_id=target_chat, media=media_group)
                await asyncio.sleep(2)
        else:
            d = dosyalar[0]
            ext = d.lower().split('.')[-1]
            if topic_id:
                if ext in ['jpg', 'jpeg', 'png', 'webp']: await client.send_photo(chat_id=target_chat, photo=d, caption=caption, reply_to_message_id=topic_id)
                elif ext in ['mp4', 'mkv', 'webm', 'mov']: await client.send_video(chat_id=target_chat, video=d, caption=caption, reply_to_message_id=topic_id)
            else:
                if ext in ['jpg', 'jpeg', 'png', 'webp']: await client.send_photo(chat_id=target_chat, photo=d, caption=caption)
                elif ext in ['mp4', 'mkv', 'webm', 'mov']: await client.send_video(chat_id=target_chat, video=d, caption=caption)
                
        return True
    except Exception as e:
        logging.error(f"TikTok indirme hatası (@{username}): {e}")
        return False
    finally:
        try:
            import shutil
            shutil.rmtree(download_dir)
        except: pass

async def tiktok_monitor_loop(client):
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
                    except Exception as e:
                        logging.error(f"TikTok stalker loop topic oluşturulamadı: {e}")
                        
                # 1. CANLI YAYIN KONTROLÜ
                now = time.time()
                if filt in ["both", "live"] and username not in ggr_recording_users:
                    if now < ggr_record_cooldown.get(username, 0):
                        pass # Cooldown devrede
                    else:
                        try:
                            live_client = TikTokLiveClient(unique_id=username)
                            is_live = await live_client.is_live()
                            
                            if is_live:
                                asyncio.create_task(record_tiktok_stream(client, username, target_chat, topic_id))
                        except Exception as e:
                            logging.error(f"TikTok canlı sorgu hatası @{username}: {type(e).__name__} - {e}")
                
                # 2. GÖNDERİ KONTROLÜ (TIKWM API - LİMİTLİ)
                if filt in ["both", "post"]:
                    now = time.time()
                    if now - ggr_last_post_check.get(username, 0) > ggr_post_check_interval:
                        try:
                            from curl_cffi import requests as c_requests
                            api_url = f"https://tikwm.com/api/user/posts?unique_id={username}&count=5"
                            resp = await asyncio.to_thread(c_requests.get, api_url, impersonate="chrome110")
                            resp_json = resp.json()
                            
                            ggr_last_post_check[username] = time.time() # Başarılı ya da başarısız, limiti güncelle
                            
                            if resp_json.get("code") == 0 and "data" in resp_json and "videos" in resp_json["data"]:
                                videos = resp_json["data"]["videos"]
                                if videos:
                                    last_post_id = user_data.get("last_post_id")
                                    
                                    if last_post_id is None:
                                        # İlk eklendiğinde sadece en yeniyi at ve kaydet
                                        latest_video = videos[0]
                                        newest_post_id = str(latest_video.get("video_id", ""))
                                        title = latest_video.get("title", "")
                                        if len(title) > 500: title = title[:500] + "..."
                                        success = await download_and_send_tiktok_post(client, username, newest_post_id, title, target_chat, topic_id)
                                        if success:
                                            db["users"][username]["last_post_id"] = newest_post_id
                                            db_kaydet(db)
                                            logging.info(f"✅ @{username} ilk tiktok gönderisi gönderildi ve id atandı.")
                                    else:
                                        # Birden fazla video atılmış olabilir, hepsini bul
                                        yeni_videolar = []
                                        for v in videos:
                                            vid = str(v.get("video_id", ""))
                                            if vid == str(last_post_id):
                                                break
                                            yeni_videolar.append(v)
                                            
                                        # Eskiden yeniye doğru (kronolojik) paylaşmak için listeyi ters çevir
                                        yeni_videolar.reverse()
                                        
                                        if yeni_videolar:
                                            en_son_basarili_id = str(last_post_id)
                                            for v in yeni_videolar:
                                                vid = str(v.get("video_id", ""))
                                                title = v.get("title", "")
                                                if len(title) > 500: title = title[:500] + "..."
                                                
                                                success = await download_and_send_tiktok_post(client, username, vid, title, target_chat, topic_id)
                                                if success:
                                                    en_son_basarili_id = vid
                                                    logging.info(f"✅ @{username} yeni tiktok gönderisi gönderildi: {vid}")
                                                else:
                                                    # Biri hata verirse döngüden çık, sonrakileri bir dahaki kontrolde dener
                                                    break
                                            
                                            if en_son_basarili_id != str(last_post_id):
                                                db["users"][username]["last_post_id"] = en_son_basarili_id
                                                db_kaydet(db)
                        except Exception as e:
                            err_str = str(e)
                            if "Expecting value: line 1 column 1 (char 0)" in err_str:
                                logging.debug(f"TikTok post check block @{username} (Olası Rate Limit / Engel)")
                            else:
                                logging.error(f"TikTok post check error @{username}: {e}")
                            ggr_last_post_check[username] = time.time() # Hata olsa da tekrar 5 dk beklemesini sağla
                
                await asyncio.sleep(2)
                
        except Exception as e:
            logging.error(f"TikTok monitor ana döngü hatası: {type(e).__name__} - {e}")
            
        await asyncio.sleep(20) # Her 20 saniyede bir kontrol et


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
            except Exception:
                pass
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
            logging.error(f"Topic oluşturulamadı: {e}")
            
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
        except:
            pass
            
    try:
        await message.edit_text(f"❌ `@{username}` TikTok takip listesinden çıkarıldı.")
    except:
        await message.reply_text(f"❌ `@{username}` TikTok takip listesinden çıkarıldı.")
