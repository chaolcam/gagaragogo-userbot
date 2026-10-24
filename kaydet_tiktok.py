import os
import sys
import time
import json
import asyncio
import subprocess
from datetime import datetime

def load_tiktok_session():
    """tiktok_cookies.txt dosyasından sessionid ve tt-target-idc çeker."""
    session_id = None
    tt_target_idc = "alisg"
    if os.path.exists("tiktok_cookies.txt"):
        with open("tiktok_cookies.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.startswith("#") and "\t" in line:
                    parts = line.strip().split("\t")
                    if len(parts) >= 7:
                        name, val = parts[5], parts[6]
                        if name == "sessionid":
                            session_id = val
                        elif name == "tt-target-idc":
                            tt_target_idc = val
    return session_id, tt_target_idc

async def extract_stream_url(username: str):
    """TikTok API ile odanın canlı durumunu ve direkt FLV akış bağlantısını çeker."""
    try:
        from TikTokLive import TikTokLiveClient
        session_id, tt_target_idc = load_tiktok_session()
        
        client = TikTokLiveClient(unique_id=username)
        if session_id:
            client.web.set_session(session_id=session_id, tt_target_idc=tt_target_idc)
            print(f"[*] TikTok oturumu yuklendi (sessionid: {session_id[:8]}...)")

        print(f"[*] @{username} canli yayin bilgileri sorgulaniyor...")
        try:
            room_id = await client.web.fetch_room_id_from_api(username)
        except Exception as e:
            err = str(e)
            if "offline" in err.lower() or "not found" in err.lower():
                print(f"[-] @{username} su an yayinda degil.")
                return None, False
            print(f"[!] Oda ID sorgu hatasi: {e}")
            return None, False

        print(f"[+] Canli Oda ID bulundu: {room_id}")
        info = await client.web.fetch_room_info(room_id)
        
        stream_url_obj = info.get("stream_url", {})
        flv_pull = stream_url_obj.get("flv_pull_url", {})
        
        target_flv = None
        for q in ["FULL_HD1", "HD1", "SD1", "SD2"]:
            if q in flv_pull:
                target_flv = flv_pull[q]
                print(f"[+] Akis kalitesi: {q}")
                break

        if not target_flv and flv_pull:
            target_flv = list(flv_pull.values())[0]

        if not target_flv:
            rtmp_url = stream_url_obj.get("rtmp_pull_url")
            if rtmp_url:
                target_flv = rtmp_url

        if target_flv:
            title = info.get("title", "Yayinda")
            print(f"[+] Yayin Basligi: {title}")
            return target_flv, True
            
        print("[-] Yayina ait direkt video akis baglantisi alinamadi.")
        return None, False
        
    except Exception as ex:
        print(f"[!] Baglanti hatasi: {ex}")
        return None, False

def record_stream(flv_url: str, username: str):
    """yt-dlp ile akisi yerel MP4 dosyasina kaydeder."""
    output_dir = "kayitlar"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{username}_{timestamp}.mp4")
    
    print("=" * 60)
    print(f"[>] KAYIT BASLATILIYOR...")
    print(f"[>] Hedef Dosya: {output_file}")
    print(f"[>] Durdurmak icin istediginiz zaman CTRL+C tuslarina basabilirsiniz.")
    print("=" * 60)
    
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--remux-video", "mp4",
        "-o", output_file,
        flv_url
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[*] Kayit kullanici tarafindan durduruldu.")
    
    if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"[+] TEBRIKLER! Video basariyla kaydedildi: {output_file} ({size_mb:.2f} MB)")
    else:
        print(f"[*] Kayit tamamlandi.")

def main():
    username = sys.argv[1] if len(sys.argv) > 1 else "melodiazra1"
    username = username.lstrip("@").strip()
    
    print("=" * 60)
    print(f"🎬 Gagaragogo TikTok Yerel Canli Yayin Kaydedici")
    print(f"📌 Hedef Kullanici: @{username}")
    print("=" * 60)
    
    while True:
        flv_url, is_live = asyncio.run(extract_stream_url(username))
        if is_live and flv_url:
            record_stream(flv_url, username)
            print("[*] Yayin sonlandi veya kayit bitti. 15 saniye sonra tekrar kontrol edilecek...")
        else:
            print("[*] 15 saniye sonra tekrar kontrol edilecek... (Cikis icin CTRL+C)")
        
        try:
            time.sleep(15)
        except KeyboardInterrupt:
            print("\n[*] Program kapatildi.")
            break

if __name__ == "__main__":
    main()
