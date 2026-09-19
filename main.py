# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Core Process Manager & Entry Point (main.py)
# Description: Initializes userbot client, helper bot, background task loops,
#              health-check web server, and async event loop.
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

import os
import asyncio
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Ortam değişkenlerini (.env dosyasını) yükle
load_dotenv()

# --- PYTHON 3.14+ YAMASI ---
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
# ---------------------------

from pyrogram import Client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("pyrogram").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("TikTokLive").setLevel(logging.WARNING)

class SaglikKontrolu(BaseHTTPRequestHandler):
    """Render ve bulut sunucuları için HTTP sağlık kontrolü (Healthcheck) ve UptimeRobot yanıtlayıcısı."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Userbot Modüler (Plugins) Mimari ile Aktif!".encode("utf-8"))
        
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        
    def log_message(self, format, *args):
        # HTTP erişim loglarının konsolu gereksiz kirletmesini engeller
        return 

def web_sunucusunu_baslat():
    """Arka plan iş parçacığında (Thread) HTTP portunu dinleyerek sunucunun kapanmasını önler."""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SaglikKontrolu)
    server.serve_forever()

Thread(target=web_sunucusunu_baslat, daemon=True).start()

API_ID = int(os.environ.get("API_ID") or 2040)
API_HASH = os.environ.get("API_HASH") or "b18441a1ff607e10a989891a5462e627"
STRING_SESSION = os.environ.get("STRING_SESSION")

if not STRING_SESSION:
    logging.critical("❌ HATA: STRING_SESSION ortam değişkeni bulunamadı veya boş! Lütfen Render panelinde Environment sekmesinden STRING_SESSION değişkeninizi ekleyin.")


def susturucu(hata_loop, context):
    """Zararsız Telegram peer/diyalog hatalarını filtreler, kritik çökmeleri Telegram log konusuna raporlar."""
    hata_metni = str(context.get("exception", ""))
    if "Peer id invalid" not in hata_metni and "ID not found" not in hata_metni and "CHANNEL_INVALID" not in hata_metni:
        hata_loop.default_exception_handler(context)
        import utils
        hata_loop.create_task(utils.tlog(f"🚨 <b>KRİTİK GLOBAL HATA:</b>\n{hata_metni}"))

loop.set_exception_handler(susturucu)

# YETİM / SİLİNMİŞ ÖZEL EKLENTİLERİ DİSKTEN TEMİZLE
# custom_plugins.json içinde kayıtlı olmayan veya silinmiş custom_*.py dosyalarını diskten temizle
try:
    from plugins.plugin_manager import get_custom_plugins, ggr_builtin_plugins
    c_plugins = get_custom_plugins()
    allowed_custom_files = {info.get("dosya_adi", f"custom_{name}.py") for name, info in c_plugins.items()}
    if os.path.exists("plugins"):
        for fname in os.listdir("plugins"):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            base_name = fname[:-3].lower()
            if base_name in ggr_builtin_plugins:
                continue # Dahili çekirdek sistem eklentisi
            if fname not in allowed_custom_files:
                try:
                    os.remove(os.path.join("plugins", fname))
                    logging.info(f"🗑️ Yetim/silinmiş eklenti temizlendi: {fname}")
                except Exception as del_err:
                    logging.warning(f"Yetim eklenti silinemedi ({fname}): {del_err}")
except Exception as _e:
    logging.warning(f"Yetim eklenti temizleme uyarısı: {_e}")

# PLUGINS (EKLENTİ) KLASÖRÜNÜ BOTA TANITMA
plugins = dict(root="plugins")

app = Client(
    "moduler_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION,
    plugins=plugins
)

logging.info("🚀 Modüler Userbot Başlatılıyor...")
import utils
utils.bot_client = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if BOT_TOKEN:
    logging.info("🤖 Yardımcı Bot Başlatılıyor...")
    bot_app = Client(
        "yardimci_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        plugins=dict(root="bot_plugins")
    )
else:
    bot_app = None

async def periyodik_bellek_temizleyici():
    """Render 512 MB RAM & 5 GB disk sınırı için periyodik çöp toplayıcı ve yetim dosya temizleyici."""
    import gc
    import time
    while True:
        await asyncio.sleep(600) # 10 dakikada bir çalışır
        try:
            gc.collect()
            for folder in ["downloads", "tiktok_downloads"]:
                if os.path.exists(folder):
                    for f in os.listdir(folder):
                        f_path = os.path.join(folder, f)
                        # 30 dakikadan eski kalmış geçici dosyaları sil
                        if os.path.isfile(f_path) and (time.time() - os.path.getmtime(f_path)) > 1800:
                            try: os.remove(f_path)
                            except: pass
        except: pass

async def baslat():
    await app.start()
    utils.OWNER_ID = app.me.id
    logging.info(f"👤 Userbot Sahibi: {app.me.first_name} (ID: {app.me.id})")
    if bot_app:
        await bot_app.start()
        me = await bot_app.get_me()
        utils.YARDIMCI_BOT_USERNAME = me.username
        logging.info(f"✅ Yardımcı Bot Aktif: @{me.username}")
    
    # Restart veya Güncelleme sonrası durum bildirimini "hazır" olarak düzenle
    try:
        await utils.restart_bildirimi_isle(app, bot_app)
    except Exception as re_err:
        logging.warning(f"Restart bildirim güncelleme hatası: {re_err}")
    
    # Otomatik Admin Grubu ve Konularının Kurulumu
    await utils.otomatik_admin_grubu_olusturucu(app)
    await utils.bulut_db_baslangic_yukle(app)
    
    # Kurtarılan veya yüklü özel eklentileri canlı hafızaya bağla
    try:
        from plugins.plugin_manager import get_custom_plugins, load_plugin_runtime
        c_plugins = get_custom_plugins()
        for p_name, p_info in c_plugins.items():
            mod_name = p_info.get("modul", f"plugins.custom_{p_name}")
            load_plugin_runtime(app, mod_name)
    except Exception as pe:
        logging.warning(f"Özel eklenti yükleme kontrolü: {pe}")
    
    # RAM ve Disk koruma temizleyicisini arka planda başlat
    asyncio.create_task(periyodik_bellek_temizleyici())
    
    # Otomatik Mesaj (Otomesaj) arka plan zamanlayıcısını başlat
    try:
        from plugins.otomesaj import otomesaj_monitor_loop
        asyncio.create_task(otomesaj_monitor_loop(app))
    except Exception as e:
        logging.error(f"Otomesaj başlatma hatası: {e}")
    
    import pyrogram
    await pyrogram.idle()
    
    await app.stop()
    if bot_app:
        await bot_app.stop()

loop.run_until_complete(baslat())

