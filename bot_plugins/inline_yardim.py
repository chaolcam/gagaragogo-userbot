# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Inline Helper & Interactive Control Panel (bot_plugins/inline_yardim.py)
# Description: Manages interactive inline query responses, .alive status card,
#              two-column category navigation, plugin store UI, and settings panel.
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
import sys
import asyncio
import subprocess
import time
import json
import requests
import uuid
from pyrogram import Client, filters
from pyrogram.types import (InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent, 
                            InlineKeyboardMarkup, InlineKeyboardButton)

# We import the KOMUT_BILGILERI from the userbot's system plugin
from plugins.sistem import KOMUT_BILGILERI
from plugins.plugin_manager import PLUGIN_STORE_CHANNEL
import utils

_LAST_GIT_FETCH_TIME = 0

def check_update_status():
    """GitHub reposunu kontrol ederek güncellik durumunu tespit eder."""
    global _LAST_GIT_FETCH_TIME
    now = time.time()
    commit = "v2.6"
    try:
        c_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        if c_res.stdout.strip():
            commit = c_res.stdout.strip()
    except Exception:
        pass
        
    # Her 30 saniyede bir origin/main fetch yap
    if now - _LAST_GIT_FETCH_TIME > 30:
        try:
            subprocess.run(["git", "config", "--global", "--add", "safe.directory", "*"], capture_output=True)
            repo_url = os.getenv("UPSTREAM_REPO", "https://github.com/chaolcam/gagaragogo-userbot.git")
            subprocess.run(["git", "remote", "set-url", "origin", repo_url], capture_output=True)
            subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, timeout=10)
            _LAST_GIT_FETCH_TIME = now
        except Exception:
            pass
            
    try:
        r_res = subprocess.run(["git", "rev-parse", "--short", "origin/main"], capture_output=True, text=True)
        remote = r_res.stdout.strip()
        if remote and remote != commit:
            return commit, "Yeni Güncelleme Mevcut"
        return commit, "Son Sürüm"
    except Exception:
        return commit, "Son Sürüm"

def get_main_menu_text():
    """Canlı durum ve sistem paneli (.alive) metnini üretir."""
    import psutil, time
    
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_str = f"{int(uptime_seconds // 86400)}g {int((uptime_seconds % 86400) // 3600)}s {int((uptime_seconds % 3600) // 60)}d"
    except:
        uptime_str = "Aktif"
        
    try:
        cpu = psutil.cpu_percent(interval=None)
    except:
        cpu = 0
        
    try:
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_str = f"{ram.used / (1024**2):.0f}MB / {ram.total / (1024**2):.0f}MB"
    except:
        ram_percent = 0
        ram_str = "0MB"
        
    commit, durum_surum = check_update_status()
    alive_logo = utils.get_alive_logo()
    cpu_bar = utils.progress_bar(cpu, 10)
    ram_bar = utils.progress_bar(ram_percent, 10)
    
    owner_name = "Userbot Sahibi"
    if utils.bot_client and hasattr(utils.bot_client, "me") and utils.bot_client.me:
        owner_name = utils.bot_client.me.first_name or "Userbot Sahibi"
        
    metin = (
        "⚡ <b>GAGARAGOGO USERBOT</b> ⬝ <b>Canlı Durum</b>\n"
        "────────────────────────\n"
        f"👤 <b>Sahip:</b> <code>{owner_name}</code>\n"
        f"⚡ <b>Durum:</b> <code>Çevrimiçi</code> ⬝ 📌 <b>Sürüm:</b> <code>{commit} ({durum_surum})</code>\n"
        f"⏳ <b>Çalışma Süresi:</b> <code>{uptime_str}</code>\n"
        "────────────────────────\n"
        f"🖥 <b>CPU:</b> <code>{cpu_bar} %{cpu}</code>\n"
        f"🧠 <b>RAM:</b> <code>{ram_bar} %{ram_percent} ({ram_str})</code>\n"
        "────────────────────────\n"
        "İncelemek istediğiniz kategoriyi seçin:"
    )
    return metin

def get_main_menu_keyboard():
    """Yardım menüsü için dengeli ve simetrik 2 sütunlu interaktif kategori klavyesi oluşturur."""
    oncelik_haritasi = {
        "admin": 10,
        "araçlar": 20,
        "araclar": 20,
        "eğlence": 30,
        "eglence": 30,
        "sistem": 40,
        "toplu iletim": 50,
        "ilet": 50,
        "medya": 60
    }
    kategoriler = [k for k in KOMUT_BILGILERI.keys() if k.lower() != "ayarlar"]
    kategoriler.sort(key=lambda x: oncelik_haritasi.get(x.lower(), 99))
    keyboard = []
    
    def get_icon(isim):
        isim_low = isim.lower()
        if "admin" in isim_low: return "🛡"
        if "araç" in isim_low or "arac" in isim_low: return "🛠"
        if "ilet" in isim_low or "toplu" in isim_low: return "📢"
        if "sistem" in isim_low: return "💻"
        if "eğlence" in isim_low or "eglence" in isim_low: return "🎮"
        if "medya" in isim_low: return "🎬"
        return "📦"

    num_kat = len(kategoriler)
    if num_kat % 2 == 1:
        for i in range(0, num_kat - 1, 2):
            k1, k2 = kategoriler[i], kategoriler[i+1]
            keyboard.append([
                InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[k1]['isim'])} {KOMUT_BILGILERI[k1]['isim']}", callback_data=f"kat_{k1}_1"),
                InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[k2]['isim'])} {KOMUT_BILGILERI[k2]['isim']}", callback_data=f"kat_{k2}_1")
            ])
        son_kat = kategoriler[-1]
        keyboard.append([
            InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[son_kat]['isim'])} {KOMUT_BILGILERI[son_kat]['isim']}", callback_data=f"kat_{son_kat}_1"),
            InlineKeyboardButton("🔌 Eklentiler", callback_data="eklenti_ana_menu")
        ])
        keyboard.append([InlineKeyboardButton("⚙️ Ayarlar & Kontrol Paneli", callback_data="ayarlar_menu")])
    else:
        for i in range(0, num_kat, 2):
            k1, k2 = kategoriler[i], kategoriler[i+1]
            keyboard.append([
                InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[k1]['isim'])} {KOMUT_BILGILERI[k1]['isim']}", callback_data=f"kat_{k1}_1"),
                InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[k2]['isim'])} {KOMUT_BILGILERI[k2]['isim']}", callback_data=f"kat_{k2}_1")
            ])
        keyboard.append([
            InlineKeyboardButton("🔌 Eklentiler", callback_data="eklenti_ana_menu"),
            InlineKeyboardButton("⚙️ Ayarlar", callback_data="ayarlar_menu")
        ])
        
    keyboard.append([InlineKeyboardButton("❌ Menüyü Kapat", callback_data="yardim_close")])
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard():
    """Botun özelliklerini açıp kapatmaya ve sistem komutlarını yönetmeye yarayan kontrol paneli."""
    hayalet = utils.ayar_getir("hayalet_durumu", False)
    antidelete = utils.ayar_getir("antidelete_durumu", False)
    
    hayalet_btn = "AÇIK ✅" if hayalet else "KAPALI ❌"
    antidelete_btn = "AÇIK ✅" if antidelete else "KAPALI ❌"
    
    keyboard = [
        [InlineKeyboardButton(f"⏳ Süreli Medya: {hayalet_btn}", callback_data="toggle_sureli")],
        [InlineKeyboardButton(f"🗑 Silinen Mesaj: {antidelete_btn}", callback_data="toggle_antidelete")],
        [
            InlineKeyboardButton("🔄 Güncelle", callback_data="btn_update"),
            InlineKeyboardButton("🔁 Yeniden Başlat", callback_data="btn_restart")
        ],
        [InlineKeyboardButton("💻 Detaylı Sistem Durumu", callback_data="btn_durum")],
        [
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
            InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
        ]
    ]
    
    yedek_id = utils.get_yedek_grup_id()
    log_konu = utils.ayar_getir("log_topic_id", "Otomatik Açılır")
    
    metin = (
        "<b>GAGARAGOGO</b> ⬝ <b>Sistem Ayarları & Kontrol Paneli</b>\n"
        "────────────────────────\n"
        "Özellikleri ve sistemi tek dokunuşla yönetebilirsiniz:\n\n"
        f"• <b>Admin / Yedek Grup:</b> <code>{yedek_id}</code>\n"
        f"• <b>Sistem Log Konusu:</b> <code>{log_konu}</code>\n\n"
        "💡 <i>Güncelleme veya yeniden başlatma işlemlerini aşağıdaki butonlarla tek tıkla yapabilirsiniz.</i>"
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_detailed_status_content():
    """Detaylı CPU, RAM, Disk, Uptime ve İşletim Sistemi durum ekranını üretir."""
    import psutil, time, platform, sys, subprocess
    
    cpu = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_count(logical=True)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_str = f"{int(uptime_seconds // 86400)}g {int((uptime_seconds % 86400) // 3600)}s {int((uptime_seconds % 3600) // 60)}d"
    
    os_info = f"{platform.system()} {platform.release()}"
    py_ver = sys.version.split(' ')[0]
    
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "v2.6"
    except:
        commit = "v2.6"

    metin = (
        "💻 <b>Sunucu & Donanım Durumu</b>\n"
        "────────────────────────\n"
        f"⚙️ <b>Sistem:</b> <code>{os_info}</code>\n"
        f"⏳ <b>Çalışma Süresi:</b> <code>{uptime_str}</code>\n"
        f"🐍 <b>Python:</b> <code>{py_ver}</code> ⬝ 📌 <b>Commit:</b> <code>{commit}</code>\n\n"
        f"🖥 <b>CPU:</b> <code>%{cpu}</code> ({cpu_cores} Çekirdek)\n"
        f"🧠 <b>RAM:</b> <code>%{ram.percent}</code> ({ram.used / (1024**2):.1f}MB / {ram.total / (1024**2):.1f}MB)\n"
        f"💾 <b>Disk:</b> <code>%{disk.percent}</code> ({disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB)"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Durumu Yenile", callback_data="btn_durum")],
        [
            InlineKeyboardButton("◀️ Ayarlar", callback_data="ayarlar_menu"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ])
    return keyboard, metin

def get_ilet_hub_content():
    """Toplu İletim ana geçiş menüsü (2 ayrı pencere: Anlık ve Otomatik)."""
    keyboard = [
        [InlineKeyboardButton("📢 Anlık İletim (.ilet)", callback_data="sub_ilet_anlik")],
        [InlineKeyboardButton("⏰ Otomatik Mesaj (.otomesaj)", callback_data="sub_ilet_otomesaj")],
        [
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
            InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
        ]
    ]
    metin = (
        "<b>GAGARAGOGO</b> ⬝ <b>İletim & Mesaj Yönetimi</b>\n"
        "────────────────────────\n"
        "Yönetmek istediğiniz iletim modunu seçin:\n\n"
        "• <b>Anlık İletim:</b> Seçtiğiniz gruplara tek dokunuşla anında mesaj veya medya gönderimi.\n"
        "• <b>Otomatik Mesaj:</b> Belirli zaman aralıklarıyla (örn: 10 dk) otomatik tekrarlanan mesaj motoru."
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_ilet_anlik_content():
    """Anlık iletim (.ilet) detay ve hızlı eylem menüsü."""
    keyboard = [
        [InlineKeyboardButton("📋 Grup Seçim Menüsü (.iletmenu)", callback_data="open_ilet_groups")],
        [
            InlineKeyboardButton("◀️ İletim Paneli", callback_data="kat_toplu iletim_1"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ]
    metin = (
        "📢 <b>ANLIK TOPLU İLETİM</b>\n"
        "────────────────────────\n"
        "Mesaj veya medyaları seçili gruplarınıza tek seferde iletir:\n\n"
        "• <code>.ilet</code> — Yanıtlanan mesajı seçili tüm gruplara yollar.\n"
        "• <code>.ilet [yazı]</code> — Yazılan metni doğrudan tüm gruplara gönderir.\n"
        "• <code>.iletmenu</code> — Gönderilecek grupları açıp kapatabileceğiniz panel."
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_ilet_otomesaj_content():
    """Otomatik mesaj (.otomesaj) detay ve yönetim menüsü."""
    keyboard = [
        [InlineKeyboardButton("⚙️ Otomesaj Yönetim Paneli", callback_data="otomsg_list")],
        [
            InlineKeyboardButton("◀️ İletim Paneli", callback_data="kat_toplu iletim_1"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ]
    metin = (
        "⏰ <b>OTOMATİK ZAMANLANMIŞ MESAJ MOTORU</b>\n"
        "────────────────────────\n"
        "Gruplara belirlediğiniz süre aralıklarıyla otomatik mesaj yollar:\n\n"
        "• <code>.otomesaj</code> — İnteraktif görev yönetim panelini açar.\n"
        "• <code>.otomesaj ekle [başlık]</code> — Yanıtlanan mesajı periyodik görev yapar.\n"
        "• <code>.otomesaj sure [id] [dk]</code> — Görev süresini günceller (örn: 15 dk).\n"
        "• <code>.otomesaj sil [id]</code> — Belirtilen görevi siler."
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_araclar_hub_content():
    """Araçlar ana geçiş menüsü (4 mantıksal alt kategori)."""
    keyboard = [
        [
            InlineKeyboardButton("📥 İndiriciler", callback_data="sub_arac_indir"),
            InlineKeyboardButton("🔄 Dönüştürücü", callback_data="sub_arac_donustur")
        ],
        [
            InlineKeyboardButton("🛡 Koruma", callback_data="sub_arac_koruma"),
            InlineKeyboardButton("🌐 Çeviri & Bypass", callback_data="sub_arac_cevir")
        ],
        [
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
            InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
        ]
    ]
    metin = (
        "<b>GAGARAGOGO</b> ⬝ <b>Araçlar Menüsü</b>\n"
        "────────────────────────\n"
        "İncelemek istediğiniz araç kategorisini seçin:\n\n"
        "• <b>📥 İndiriciler:</b> TikTok, YouTube, Instagram ve Telegram.\n"
        "• <b>🔄 Dönüştürücü:</b> Yuvarlak video, sesli mesaj, sticker ve seslendirme.\n"
        "• <b>🛡 Koruma:</b> DM silinen mesajlar ve süreli medya koruması.\n"
        "• <b>🌐 Çeviri & Bypass:</b> Anında çeviri ve reklamlı link aşma araçları."
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_araclar_indir_content():
    keyboard = [
        [
            InlineKeyboardButton(".tg", callback_data="csub:Araçlar:sub_arac_indir:tg"),
            InlineKeyboardButton(".tt", callback_data="csub:Araçlar:sub_arac_indir:tt"),
            InlineKeyboardButton(".yt", callback_data="csub:Araçlar:sub_arac_indir:yt")
        ],
        [
            InlineKeyboardButton(".ig", callback_data="csub:Araçlar:sub_arac_indir:ig"),
            InlineKeyboardButton(".rapidapi", callback_data="csub:Araçlar:sub_arac_indir:rapidapi")
        ],
        [
            InlineKeyboardButton(".tttakip", callback_data="csub:Araçlar:sub_arac_indir:tttakip"),
            InlineKeyboardButton(".tttakiptencikar", callback_data="csub:Araçlar:sub_arac_indir:tttakiptencikar")
        ],
        [
            InlineKeyboardButton("◀️ Geri", callback_data="kat_araçlar_1"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ]
    metin = (
        "📥 <b>MEDYA İNDİRİCİLER & CANLI TAKİP</b>\n"
        "────────────────────────\n"
        "Detayını görmek istediğiniz komuta tıklayın:\n\n"
        "• <code>.tg</code> — Korumalı Telegram medyalarını indirir.\n"
        "• <code>.tt</code> — TikTok filigransız video ve albüm indirir.\n"
        "• <code>.yt</code> — YouTube video ve Shorts indirir.\n"
        "• <code>.ig</code> — Instagram hikaye, gönderi ve öne çıkanlar interaktif gezgini.\n"
        "• <code>.tttakip</code> — TikTok otomatik canlı yayın kayıt motoru."
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_araclar_donustur_content():
    keyboard = [
        [
            InlineKeyboardButton(".yuvarlak", callback_data="csub:Araçlar:sub_arac_donustur:yuvarlak"),
            InlineKeyboardButton(".ses", callback_data="csub:Araçlar:sub_arac_donustur:ses")
        ],
        [
            InlineKeyboardButton(".sticker", callback_data="csub:Araçlar:sub_arac_donustur:sticker"),
            InlineKeyboardButton(".tts", callback_data="csub:Araçlar:sub_arac_donustur:tts")
        ],
        [
            InlineKeyboardButton("◀️ Geri", callback_data="kat_araçlar_1"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ]
    metin = (
        "🔄 <b>MEDYA DÖNÜŞTÜRÜCÜLER</b>\n"
        "────────────────────────\n"
        "Detayını görmek istediğiniz komuta tıklayın:\n\n"
        "• <code>.yuvarlak</code> — Videoyu yuvarlak mesaja (Telescope) çevirir.\n"
        "• <code>.ses</code> — Medyayı Telegram sesli mesajına dönüştürür.\n"
        "• <code>.sticker</code> — Fotoğrafı çıkartmaya (WebP) çevirir.\n"
        "• <code>.tts</code> — Yazıyı Türkçe sesli mesaja dönüştürür."
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_araclar_koruma_content():
    hayalet = utils.ayar_getir("hayalet_durumu", False)
    antidelete = utils.ayar_getir("antidelete_durumu", False)
    hayalet_btn = "AÇIK ✅" if hayalet else "KAPALI ❌"
    antidelete_btn = "AÇIK ✅" if antidelete else "KAPALI ❌"

    keyboard = [
        [InlineKeyboardButton(f"⏳ Süreli Medya: {hayalet_btn}", callback_data="toggle_sureli_from_koruma")],
        [InlineKeyboardButton(f"🗑 Silinen Mesaj: {antidelete_btn}", callback_data="toggle_antidelete_from_koruma")],
        [
            InlineKeyboardButton(".antidelete", callback_data="csub:Araçlar:sub_arac_koruma:antidelete"),
            InlineKeyboardButton(".sureli", callback_data="csub:Araçlar:sub_arac_koruma:sureli")
        ],
        [
            InlineKeyboardButton("◀️ Geri", callback_data="kat_araçlar_1"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ]
    metin = (
        "🛡 <b>KORUMA & GİZLİLİK ARAÇLARI</b>\n"
        "────────────────────────\n"
        "Özel sohbetlerde mesaj ve medya yakalama modları:\n\n"
        f"• <b>Süreli Medya Koruması:</b> {hayalet_btn}\n"
        f"• <b>Silinen Mesaj Koruması:</b> {antidelete_btn}\n\n"
        "💡 <i>Yukarıdaki butonlara tıklayarak özellikleri anında açıp kapatabilirsiniz.</i>"
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_araclar_cevir_content():
    keyboard = [
        [
            InlineKeyboardButton(".cevir", callback_data="csub:Araçlar:sub_arac_cevir:cevir"),
            InlineKeyboardButton(".dil", callback_data="csub:Araçlar:sub_arac_cevir:dil")
        ],
        [InlineKeyboardButton(".bypass", callback_data="csub:Araçlar:sub_arac_cevir:bypass")],
        [
            InlineKeyboardButton("◀️ Geri", callback_data="kat_araçlar_1"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ]
    metin = (
        "🌐 <b>ÇEVİRİ & LİNK BYPASS ARAÇLARI</b>\n"
        "────────────────────────\n"
        "Detayını görmek istediğiniz komuta tıklayın:\n\n"
        "• <code>.cevir</code> — Yanıtlanan mesajı otomatik çevirir.\n"
        "• <code>.dil</code> — Çeviri hedef dilini ayarlar (örn: .dil tr, .dil en).\n"
        "• <code>.bypass</code> — Ouo.io, TinyURL vb. reklamlı linkleri çözer."
    )
    return InlineKeyboardMarkup(keyboard), metin

def get_category_keyboard(kategori_key, sayfa):
    kategori_data = KOMUT_BILGILERI.get(kategori_key)
    if not kategori_data:
        for k, v in KOMUT_BILGILERI.items():
            if k.lower() == kategori_key.lower():
                kategori_data = v
                break
    if not kategori_data:
        return None, "Kategori bulunamadı."
        
    komutlar_listesi = list(kategori_data.get("komutlar", {}).items())
    
    # Kategori boş ise (eklenti yüklü değilse) kullanıcıyı Mağazaya yönlendir
    if not komutlar_listesi:
        kat_isim = kategori_data.get("isim", kategori_key.capitalize())
        keyboard = [
            [InlineKeyboardButton("🛒 Mağazaya Git", callback_data="eklenti_magaza_1")],
            [InlineKeyboardButton("🔌 Eklentilerim", callback_data="eklenti_yuklu_1")],
            [
                InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
                InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
            ]
        ]
        metin = (
            f"<b>KATEGORİ:</b> <code>{kat_isim}</code>\n"
            "────────────────────────\n"
            "ℹ️ <i>Bu kategoride henüz yüklü bir eklenti veya komut bulunmuyor.</i>\n\n"
            "💡 <b>Resmi Eklenti Mağazası</b> üzerinden yeni eklentileri tek tıkla yükleyebilirsiniz!"
        )
        return InlineKeyboardMarkup(keyboard), metin
    
    limit = 6
    toplam_sayfa = (len(komutlar_listesi) + limit - 1) // limit
    if toplam_sayfa < 1: toplam_sayfa = 1
    if sayfa < 1: sayfa = 1
    if sayfa > toplam_sayfa: sayfa = toplam_sayfa
    
    baslangic = (sayfa - 1) * limit
    bitis = baslangic + limit
    gosterilecek_komutlar = komutlar_listesi[baslangic:bitis]
    
    keyboard = []
    for i in range(0, len(gosterilecek_komutlar), 2):
        row = []
        cmd1_adi, cmd1_data = gosterilecek_komutlar[i]
        row.append(InlineKeyboardButton(f".{cmd1_adi}", callback_data=f"cmd_{kategori_key}_{sayfa}_{cmd1_adi}"))
        
        if i + 1 < len(gosterilecek_komutlar):
            cmd2_adi, cmd2_data = gosterilecek_komutlar[i+1]
            row.append(InlineKeyboardButton(f".{cmd2_adi}", callback_data=f"cmd_{kategori_key}_{sayfa}_{cmd2_adi}"))
            
        keyboard.append(row)
        
    if toplam_sayfa > 1:
        nav_row = []
        if sayfa > 1:
            nav_row.append(InlineKeyboardButton("◀️ Geri", callback_data=f"kat_{kategori_key}_{sayfa-1}"))
        nav_row.append(InlineKeyboardButton(f"📄 {sayfa}/{toplam_sayfa}", callback_data="yardim_noop"))
        if sayfa < toplam_sayfa:
            nav_row.append(InlineKeyboardButton("İleri ▶️", callback_data=f"kat_{kategori_key}_{sayfa+1}"))
        keyboard.append(nav_row)
        
    keyboard.append([
        InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
        InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
    ])
    
    metin = (
        f"<b>KATEGORİ:</b> <code>{kategori_data['isim']}</code>\n"
        "────────────────────────\n"
        "Detayını görmek istediğiniz komuta tıklayın:"
    )
    return InlineKeyboardMarkup(keyboard), metin


@Client.on_inline_query(filters.regex("^(alive|yardim|ayarlar)"))
async def inline_yardim(client, inline_query):
    query_text = inline_query.query.strip().lower()
    
    if query_text == "ayarlar":
        keyboard, metin = get_settings_keyboard()
        title = "GagaraGogo Kontrol Paneli"
        desc = "Ayarları anında yönetin."
        results = [
            InlineQueryResultArticle(
                title=title,
                input_message_content=InputTextMessageContent(metin),
                reply_markup=keyboard,
                description=desc,
                thumb_url=utils.get_alive_logo()
            )
        ]
    else:
        metin = get_main_menu_text()
        keyboard = get_main_menu_keyboard()
        title = "GagaraGogo Canlı Durum (.alive)"
        desc = "GagaraGogo Userbot canlı durum kartını ve kontrol panelini yollar."
        logo_url = utils.get_alive_logo()
        results = [
            InlineQueryResultPhoto(
                photo_url=logo_url,
                thumb_url=logo_url,
                title=title,
                description=desc,
                caption=metin,
                reply_markup=keyboard
            )
        ]
    
    await inline_query.answer(results, cache_time=1)

@Client.on_inline_query(filters.regex(r"^ig\s+(.+)"))
async def inline_ig(client, inline_query):
    username = inline_query.matches[0].group(1).strip()
    
    from plugins.araclar import get_rapidapi_keys_list, RAPIDAPI_YARDIM_METNI
    if not get_rapidapi_keys_list():
        results = [
            InlineQueryResultArticle(
                title="⚠️ RapidAPI Anahtarı Gerekli!",
                input_message_content=InputTextMessageContent(RAPIDAPI_YARDIM_METNI, disable_web_page_preview=True),
                description="Instagram araçlarını kullanmak için .rapidapi [anahtar] yazın."
            )
        ]
        await inline_query.answer(results, cache_time=1)
        return
        
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Hikayeler", callback_data=f"ig_story_{username}_0")],
        [InlineKeyboardButton("🖼 Gönderiler", callback_data=f"ig_post_{username}_0")],
        [InlineKeyboardButton("⭐ Öne Çıkanlar", callback_data=f"ig_high_{username}_0")]
    ])
    
    metin = (
        f"<b>Instagram:</b> <code>@{username}</code>\n"
        "────────────────────────\n"
        "Görüntülemek istediğiniz medya türünü seçin:"
    )
    
    results = [
        InlineQueryResultArticle(
            title=f"@{username} Instagram Arama",
            input_message_content=InputTextMessageContent(metin),
            reply_markup=keyboard,
            description="Hikayeler, gönderiler ve öne çıkanları görüntüle."
        )
    ]
    await inline_query.answer(results, cache_time=1)

async def build_ilet_menu_keyboard(page=1):
    from plugins.ilet import get_all_user_groups, is_group_active
    userbot = utils.bot_client
    if not userbot:
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Userbot aktif değil", callback_data="none")]]), "Userbot aktif değil"
    
    gruplar = await get_all_user_groups(userbot)
    if not gruplar:
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Grup bulunamadı", callback_data="none")]]), "Hiçbir grup bulunamadı."
        
    per_page = 10
    toplam_sayfa = max(1, (len(gruplar) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > toplam_sayfa: page = toplam_sayfa
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sayfa_gruplari = gruplar[start_idx:end_idx]
    
    # Metin listesi oluştur
    metin = "📢 <b>Toplu İletim Grup Listesi</b>\n\n"
    for i, g in enumerate(sayfa_gruplari, start=start_idx + 1):
        durum_ikon = "✅ Açık" if is_group_active(g["id"]) else "⛔ Kapalı"
        title = utils.guvenli_isim(g["title"][:26])
        metin += f"{i}. {title} — {durum_ikon}\n"
        
    metin += "\n💡 Durumunu değiştirmek istediğiniz grubun numarasına tıklayın."
    
    # 5 sütunlu numara butonları (örn: 1-5, 6-10)
    keyboard = []
    current_row = []
    for i, g in enumerate(sayfa_gruplari, start=start_idx + 1):
        aktif = is_group_active(g["id"])
        btn_text = f"✅ {i}" if aktif else f"⛔ {i}"
        current_row.append(InlineKeyboardButton(btn_text, callback_data=f"ilet_n_{i}_{page}"))
        if len(current_row) == 5:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
        
    # Sayfalama butonları
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Geri", callback_data=f"ilet_p_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{toplam_sayfa}", callback_data="ilet_noop"))
    if page < toplam_sayfa:
        nav_row.append(InlineKeyboardButton("İleri ▶️", callback_data=f"ilet_p_{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([
        InlineKeyboardButton("◀️ İletim Paneli", callback_data="sub_ilet_anlik"),
        InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
    ])
    keyboard.append([InlineKeyboardButton("❌ Menüyü Kapat", callback_data="ilet_close")])
    return InlineKeyboardMarkup(keyboard), metin


# =============================================================================
# OTOMATİK MESAJ (OTOMESAJ) İNTERAKTİF PANELLERİ
# =============================================================================

# Otomesaj için formatlayıcı fonksiyonlar
def format_sure(dakika):
    if dakika < 60:
        return f"{dakika} dk"
    elif dakika % 60 == 0:
        return f"{dakika // 60} saat"
    elif dakika % 1440 == 0:
        return f"{dakika // 1440} gün"
    else:
        saat = round(dakika / 60, 1)
        if saat.is_integer():
            return f"{int(saat)} saat"
        return f"{saat} saat"

async def build_otomesaj_list_keyboard():
    from plugins.otomesaj import get_all_tasks
    gorevler = get_all_tasks()
    
    if not gorevler:
        keyboard = [
            [InlineKeyboardButton("➕ Yeni Görev Ekleme Rehberi", callback_data="otomsg_guide")],
            [InlineKeyboardButton("❌ Menüyü Kapat", callback_data="otomsg_close")]
        ]
        metin = (
            "⏰ <b>Zamanlanmış Otomatik Mesajlar (Otomesaj)</b>\n\n"
            "ℹ️ Şu anda tanımlanmış aktif bir otomatik mesaj göreviniz bulunmuyor.\n\n"
            "💡 <b>Nasıl Eklenir?</b>\n"
            "İletilmesini istediğiniz herhangi bir mesaja yanıt vererek:\n"
            "<code>.otomesaj ekle [Başlık]</code> yazabilirsiniz."
        )
        return InlineKeyboardMarkup(keyboard), metin

    keyboard = []
    for tid, data in gorevler.items():
        durum_ikon = "🟢" if data.get("aktif", True) else "🔴"
        baslik = data.get("baslik", f"Görev #{tid}")
        btn_text = f"{durum_ikon} #{tid} - {baslik[:22]}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"otomsg_view_{tid}")])

    keyboard.append([
        InlineKeyboardButton("➕ Yeni Görev Rehberi", callback_data="otomsg_guide"),
        InlineKeyboardButton("❌ Kapat", callback_data="otomsg_close")
    ])

    metin = (
        "⏰ <b>Zamanlanmış Mesaj Görev Listeniz</b>\n\n"
        "Yönetmek istediğiniz görevin butonuna tıklayarak gruplarını, süresini, durumunu düzenleyebilir veya silebilirsiniz."
    )
    return InlineKeyboardMarkup(keyboard), metin

async def build_otomesaj_detail_keyboard(task_id):
    from plugins.otomesaj import get_task
    task = get_task(task_id)
    if not task:
        return None, "Görev bulunamadı."

    durum_str = "AÇIK ✅" if task.get("aktif", True) else "KAPALI ❌"
    onceki_sil_str = "AÇIK ✅" if task.get("onceki_sil", True) else "KAPALI ❌"
    sure_str = format_sure(task.get("aralik_dakika", 60))
    grup_sayisi = len(task.get("hedef_gruplar", []))
    son_iletilme = task.get("son_gonderim", "Henüz İletilmedi")
    icerik_onizleme = task.get("metin", "")[:80] if task.get("metin") else "[Medya İçeriği]"

    keyboard = [
        [InlineKeyboardButton(f"⚡ Durum: {durum_str}", callback_data=f"otomsg_tog_{task_id}")],
        [InlineKeyboardButton(f"🗑️ Önceki Mesajı Sil: {onceki_sil_str}", callback_data=f"otomsg_delprev_{task_id}")],
        [
            InlineKeyboardButton(f"⏱️ Süre: {sure_str}", callback_data=f"otomsg_time_{task_id}"),
            InlineKeyboardButton(f"👥 Gruplar ({grup_sayisi})", callback_data=f"otomsg_grp_{task_id}_1")
        ],
        [InlineKeyboardButton("🚀 Şimdi Manuel İlet", callback_data=f"otomsg_run_{task_id}")],
        [InlineKeyboardButton("🗑️ Bu Görevi Sil", callback_data=f"otomsg_del_{task_id}")],
        [
            InlineKeyboardButton("◀️ Görev Listesi", callback_data="otomsg_list"),
            InlineKeyboardButton("❌ Kapat", callback_data="otomsg_close")
        ]
    ]

    metin = (
        f"📋 <b>Otomatik Mesaj Detayı: #{task_id} - {task.get('baslik')}</b>\n\n"
        f"🔹 <b>Durum:</b> {durum_str}\n"
        f"🔹 <b>İletim Aralığı:</b> {sure_str}\n"
        f"🔹 <b>Önceki Mesajı Sil:</b> {onceki_sil_str} <i>(Sohbette kalabalık etmez)</i>\n"
        f"🔹 <b>Hedef Grup Sayısı:</b> {grup_sayisi} grup seçili\n"
        f"🔹 <b>Son İletim:</b> {son_iletilme}\n"
        f"🔹 <b>İçerik Özeti:</b> <i>{icerik_onizleme}...</i>\n\n"
        "💡 Aşağıdaki butonlardan ayarları değiştirebilirsiniz."
    )
    return InlineKeyboardMarkup(keyboard), metin

async def build_otomesaj_time_keyboard(task_id):
    from plugins.otomesaj import get_task
    task = get_task(task_id)
    if not task: return None, "Görev bulunamadı."
    
    mevcut = task.get("aralik_dakika", 60)
    
    presetler = [
        (15, "15 dk"), (30, "30 dk"), (45, "45 dk"),
        (60, "1 saat"), (120, "2 saat"), (150, "2.5 saat"),
        (180, "3 saat"), (360, "6 saat"), (720, "12 saat"),
        (1440, "1 gün"), (2880, "2 gün"), (4320, "3 gün")
    ]
    
    keyboard = []
    current_row = []
    for mins, label in presetler:
        secili = "🔘 " if mins == mevcut else ""
        current_row.append(InlineKeyboardButton(f"{secili}{label}", callback_data=f"otomsg_setm_{task_id}_{mins}"))
        if len(current_row) == 3:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
        
    keyboard.append([
        InlineKeyboardButton("➖ 15 dk", callback_data=f"otomsg_adj_{task_id}_-15"),
        InlineKeyboardButton("➕ 15 dk", callback_data=f"otomsg_adj_{task_id}_15"),
        InlineKeyboardButton("➕ 1 saat", callback_data=f"otomsg_adj_{task_id}_60")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Göreve Dön", callback_data=f"otomsg_view_{task_id}")])
    
    metin = (
        f"⏱️ <b>Görev #{task_id} İçin Süre Ayarı</b>\n\n"
        f"Şu anki süre: <b>{format_sure(mevcut)}</b>\n\n"
        "Hızlı süre butonlarından birini seçebilir veya hassas artır/azalt butonlarını kullanabilirsiniz.\n\n"
        "💡 <i>İpucu: Komutla serbest süre belirlemek için:</i>\n"
        f"<code>.otomesaj sure {task_id} 2.5 saat</code> veya <code>45 dk</code>"
    )
    return InlineKeyboardMarkup(keyboard), metin

async def build_otomesaj_groups_keyboard(task_id, page=1):
    from plugins.otomesaj import get_task
    from plugins.ilet import get_all_user_groups
    task = get_task(task_id)
    if not task: return None, "Görev bulunamadı."
    
    userbot = utils.bot_client
    if not userbot: return None, "Userbot aktif değil."
    
    gruplar = await get_all_user_groups(userbot)
    if not gruplar: return None, "Hiçbir grup bulunamadı."
    
    hedef_gruplar = set(task.get("hedef_gruplar", []))
    
    per_page = 10
    toplam_sayfa = max(1, (len(gruplar) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > toplam_sayfa: page = toplam_sayfa
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sayfa_gruplari = gruplar[start_idx:end_idx]
    
    metin = f"👥 <b>Görev #{task_id} İçin Hedef Gruplar</b>\n\n"
    for i, g in enumerate(sayfa_gruplari, start=start_idx + 1):
        durum_ikon = "✅ Seçili" if g["id"] in hedef_gruplar else "⛔ Kapalı"
        title = utils.guvenli_isim(g["title"][:26])
        metin += f"{i}. {title} — {durum_ikon}\n"
        
    metin += f"\n📊 Toplam Seçili Grup: <b>{len(hedef_gruplar)} / {len(gruplar)}</b>\n"
    metin += "💡 Numaraya basarak o grubun seçimini açıp kapatabilirsiniz."
    
    keyboard = []
    current_row = []
    for i, g in enumerate(sayfa_gruplari, start=start_idx + 1):
        secili = g["id"] in hedef_gruplar
        btn_text = f"✅ {i}" if secili else f"⛔ {i}"
        current_row.append(InlineKeyboardButton(btn_text, callback_data=f"otomsg_tgrp_{task_id}_{g['id']}_{page}"))
        if len(current_row) == 5:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
        
    # Toplu seçim butonları
    keyboard.append([
        InlineKeyboardButton("✅ Sayfayı Tümünü Seç", callback_data=f"otomsg_grpass_{task_id}_{page}_on"),
        InlineKeyboardButton("⛔ Sayfayı Tümünü Kapat", callback_data=f"otomsg_grpass_{task_id}_{page}_off")
    ])
    
    # Sayfalama
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Geri", callback_data=f"otomsg_grp_{task_id}_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{toplam_sayfa}", callback_data="otomsg_noop"))
    if page < toplam_sayfa:
        nav_row.append(InlineKeyboardButton("İleri ▶️", callback_data=f"otomsg_grp_{task_id}_{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton("🔙 Göreve Dön", callback_data=f"otomsg_view_{task_id}")])
    return InlineKeyboardMarkup(keyboard), metin


@Client.on_inline_query(filters.regex(r"^otomesaj"))
async def inline_otomesaj(client, inline_query):
    kb, metin = await build_otomesaj_list_keyboard()
    title = "⏰ Otomatik Zamanlanmış Mesaj Paneli"
    desc = "Zamanlanmış otomatik mesajları yönetin."

    results = [
        InlineQueryResultArticle(
            title=title,
            input_message_content=InputTextMessageContent(metin),
            reply_markup=kb,
            description=desc,
            thumb_url="https://img.icons8.com/color/512/alarm-clock.png"
        )
    ]
    await inline_query.answer(results, cache_time=1, is_personal=True)


# =============================================================================
# EKLENTİ YÖNETİMİ & MAĞAZA KLAVYELERİ
# =============================================================================

async def build_eklenti_ana_menu_keyboard():
    from plugins.plugin_manager import PLUGIN_STORE_CHANNEL
    keyboard = [
        [InlineKeyboardButton("🛒 Eklenti Mağazası", callback_data="eklenti_magaza_1")],
        [
            InlineKeyboardButton("📦 Eklentilerim", callback_data="eklenti_yuklu_1"),
            InlineKeyboardButton("🗑️ Eklenti Kaldır", callback_data="eklenti_kaldir_1")
        ],
        [
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
            InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
        ]
    ]
    metin = (
        "<b>GAGARAGOGO</b> ⬝ <b>Eklenti & Mağaza</b>\n"
        "────────────────────────\n"
        f"Resmi mağazadaki (<code>@{PLUGIN_STORE_CHANNEL}</code>) eklentileri tek tıkla kurabilir veya özel eklentilerinizi yönetebilirsiniz.\n\n"
        "• <b>Özel Eklenti:</b> <code>.py</code> dosyasına <code>.install</code> ile yanıt verin.\n"
        "• <b>Mağazadan:</b> <code>.install [No]</code> veya mağazayı inceleyin."
    )
    return InlineKeyboardMarkup(keyboard), metin

async def build_eklenti_magaza_keyboard(page=1):
    from plugins.plugin_manager import fetch_store_plugins, PLUGIN_STORE_CHANNEL
    userbot = utils.bot_client
    if not userbot:
        return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="eklenti_ana_menu"), InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")]]), "❌ Userbot henüz aktif değil."

    plugins = await fetch_store_plugins(userbot, limit=50)
    if not plugins:
        keyboard = [
            [InlineKeyboardButton("🔄 Yenile", callback_data="eklenti_magaza_1")],
            [
                InlineKeyboardButton("◀️ Eklentiler", callback_data="eklenti_ana_menu"),
                InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
            ],
            [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
        ]
        metin = (
            f"<b>EKLENTİ MAĞAZASI</b> ⬝ <code>@{PLUGIN_STORE_CHANNEL}</code>\n"
            "────────────────────────\n"
            "ℹ️ Şu anda mağazada yayınlanmış eklenti bulunamadı.\n\n"
            "💡 <i>Kanalda yeni bir .py paylaşıldığında burada otomatik olarak listelenir.</i>"
        )
        return InlineKeyboardMarkup(keyboard), metin

    per_page = 5
    toplam_sayfa = max(1, (len(plugins) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > toplam_sayfa: page = toplam_sayfa

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sayfa_items = plugins[start_idx:end_idx]

    keyboard = []
    for item in sayfa_items:
        baslik = item["baslik"].strip()
        msg_id = item["id"]
        has_emoji = any(ord(c) > 127 for c in baslik[:3])
        btn_text = baslik if has_emoji else f"📦 {baslik}"
        if len(btn_text) > 30:
            btn_text = btn_text[:28] + ".."
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"eklenti_detay_{msg_id}")])

    if toplam_sayfa > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️ Geri", callback_data=f"eklenti_magaza_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"📄 {page}/{toplam_sayfa}", callback_data="yardim_noop"))
        if page < toplam_sayfa:
            nav_row.append(InlineKeyboardButton("İleri ▶️", callback_data=f"eklenti_magaza_{page+1}"))
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton("◀️ Eklentiler", callback_data="eklenti_ana_menu"),
        InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
    ])
    keyboard.append([InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")])

    metin = (
        f"<b>EKLENTİ MAĞAZASI</b> ⬝ <code>@{PLUGIN_STORE_CHANNEL}</code>\n"
        "────────────────────────\n"
        "İncelemek ve kurmak istediğiniz eklentiyi seçin:"
    )
    return InlineKeyboardMarkup(keyboard), metin

async def build_eklenti_detay_keyboard(msg_id):
    from plugins.plugin_manager import PLUGIN_STORE_CHANNEL
    userbot = utils.bot_client
    if not userbot:
        return None, "Userbot aktif değil."

    try:
        msg = await userbot.get_messages(PLUGIN_STORE_CHANNEL, message_ids=msg_id)
    except Exception as e:
        return None, f"Mesaj çekilemedi: {e}"

    if not msg or not msg.document:
        return None, "Eklenti dosyası bulunamadı."

    file_name = msg.document.file_name or "eklenti.py"
    mod_name = file_name[:-3] if file_name.endswith(".py") else file_name
    caption = msg.caption or msg.text or "Açıklama bulunmuyor."
    boyut_kb = round(msg.document.file_size / 1024, 1)

    keyboard = [
        [InlineKeyboardButton("⬇️ Hemen Yükle ve Aktif Et", callback_data=f"eklenti_kur_{msg_id}")],
        [
            InlineKeyboardButton("◀️ Mağazaya Dön", callback_data="eklenti_magaza_1"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ]

    metin = (
        f"<b>MODÜL DETAYI</b> ⬝ <code>{mod_name}</code>\n"
        "────────────────────────\n"
        f"<b>Dosya:</b> <code>{file_name}</code> ({boyut_kb} KB)\n\n"
        f"<b>Açıklama:</b>\n{caption}"
    )
    return InlineKeyboardMarkup(keyboard), metin

async def build_eklenti_yuklu_keyboard(page=1):
    from plugins.plugin_manager import get_custom_plugins
    custom_plugins = get_custom_plugins()

    if not custom_plugins:
        keyboard = [
            [InlineKeyboardButton("🛒 Mağazaya Git", callback_data="eklenti_magaza_1")],
            [
                InlineKeyboardButton("◀️ Eklentiler", callback_data="eklenti_ana_menu"),
                InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
            ],
            [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
        ]
        metin = (
            "<b>YÜKLÜ ÖZEL EKLENTİLER</b>\n"
            "────────────────────────\n"
            "ℹ️ Henüz sonradan yüklenmiş bir özel eklentiniz bulunmuyor.\n\n"
            "💡 <i>Mağazadan veya bir .py dosyasına yanıt verip <code>.install</code> yazarak eklenti yükleyebilirsiniz.</i>"
        )
        return InlineKeyboardMarkup(keyboard), metin

    items = list(custom_plugins.items())
    per_page = 5
    toplam_sayfa = max(1, (len(items) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > toplam_sayfa: page = toplam_sayfa

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sayfa_items = items[start_idx:end_idx]

    keyboard = []
    for name, info in sayfa_items:
        baslik = info.get("baslik", name).strip()
        has_emoji = any(ord(c) > 127 for c in baslik[:3])
        btn_text = baslik if has_emoji else f"📦 {baslik}"
        if len(btn_text) > 28:
            btn_text = btn_text[:26] + ".."
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"eklenti_bilgi_{name}")])

    if toplam_sayfa > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️ Geri", callback_data=f"eklenti_yuklu_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"📄 {page}/{toplam_sayfa}", callback_data="yardim_noop"))
        if page < toplam_sayfa:
            nav_row.append(InlineKeyboardButton("İleri ▶️", callback_data=f"eklenti_yuklu_{page+1}"))
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton("◀️ Eklentiler", callback_data="eklenti_ana_menu"),
        InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
    ])
    keyboard.append([InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")])

    metin = (
        "<b>YÜKLÜ ÖZEL EKLENTİLER</b>\n"
        "────────────────────────\n"
        "Detayını görmek veya kaldırmak için eklentiye tıklayın:"
    )
    return InlineKeyboardMarkup(keyboard), metin

async def build_eklenti_bilgi_keyboard(plugin_name):
    from plugins.plugin_manager import get_custom_plugins
    custom_plugins = get_custom_plugins()
    info = custom_plugins.get(plugin_name)

    if not info:
        return None, "Eklenti bilgisi bulunamadı."

    dosya = info.get("dosya_adi", f"custom_{plugin_name}.py")
    tarih = info.get("tarih", "Bilinmiyor")
    kaynak = info.get("kaynak", "Bilinmiyor")
    aciklama = info.get("aciklama", "Açıklama yok.")
    tam_yol = os.path.join("plugins", dosya)
    boyut_kb = round(os.path.getsize(tam_yol) / 1024, 1) if os.path.exists(tam_yol) else 0

    keyboard = [
        [InlineKeyboardButton("🗑️ Bu Eklentiyi Kaldır", callback_data=f"eklenti_sil_{plugin_name}")],
        [
            InlineKeyboardButton("◀️ Eklentilerim", callback_data="eklenti_yuklu_1"),
            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
        ],
        [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
    ]

    metin = (
        f"<b>MODÜL BİLGİSİ</b> ⬝ <code>{plugin_name}</code>\n"
        "────────────────────────\n"
        f"<b>Dosya:</b> <code>{dosya}</code> ({boyut_kb} KB)\n"
        f"<b>Yüklenme:</b> {tarih}\n"
        f"<b>Kaynak:</b> {kaynak}\n\n"
        f"<b>Açıklama:</b>\n{aciklama}"
    )
    return InlineKeyboardMarkup(keyboard), metin

async def build_eklenti_kaldir_keyboard(page=1):
    from plugins.plugin_manager import get_custom_plugins
    custom_plugins = get_custom_plugins()

    if not custom_plugins:
        keyboard = [
            [
                InlineKeyboardButton("◀️ Eklentiler", callback_data="eklenti_ana_menu"),
                InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
            ],
            [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
        ]
        metin = (
            "<b>EKLENTİ KALDIRMA</b>\n"
            "────────────────────────\n"
            "ℹ️ Şu anda kaldırılabilecek özel bir eklenti yüklü değil.\n"
            "<i>(Not: Dahili sistem eklentileri koruma altındadır ve silinemez.)</i>"
        )
        return InlineKeyboardMarkup(keyboard), metin

    items = list(custom_plugins.items())
    per_page = 5
    toplam_sayfa = max(1, (len(items) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > toplam_sayfa: page = toplam_sayfa

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sayfa_items = items[start_idx:end_idx]

    keyboard = []
    for name, info in sayfa_items:
        baslik = info.get("baslik", name)
        keyboard.append([InlineKeyboardButton(f"❌ {baslik} Kaldır", callback_data=f"eklenti_sil_{name}")])

    if toplam_sayfa > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️ Geri", callback_data=f"eklenti_kaldir_{page-1}"))
        nav_row.append(InlineKeyboardButton(f"📄 {page}/{toplam_sayfa}", callback_data="yardim_noop"))
        if page < toplam_sayfa:
            nav_row.append(InlineKeyboardButton("İleri ▶️", callback_data=f"eklenti_kaldir_{page+1}"))
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton("◀️ Eklentiler", callback_data="eklenti_ana_menu"),
        InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
    ])
    keyboard.append([InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")])

    metin = (
        "<b>EKLENTİ KALDIRMA</b>\n"
        "────────────────────────\n"
        "Kaldırmak istediğiniz özel eklentiyi seçin:"
    )
    return InlineKeyboardMarkup(keyboard), metin


@Client.on_inline_query(filters.regex(r"^ilet"))
async def inline_ilet(client, inline_query):
    kb, metin = await build_ilet_menu_keyboard(1)
    results = [
        InlineQueryResultArticle(
            title="📢 Toplu İletim Grup Seçim Paneli",
            input_message_content=InputTextMessageContent(metin),
            reply_markup=kb,
            description="Grupların yayın izinlerini butonlarla yönetin.",
            thumb_url="https://img.icons8.com/color/512/speaker.png"
        )
    ]
    await inline_query.answer(results, cache_time=1, is_personal=True)


@Client.on_callback_query()
async def yardim_callback(client, callback_query):
    owner_id = utils.get_owner_id()
    if owner_id and callback_query.from_user and callback_query.from_user.id != owner_id:
        await callback_query.answer("⛔ Bu butonlar sadece bot sahibine aittir!", show_alert=True)
        return

    orig_edit_text = callback_query.edit_message_text

    async def safe_edit_text(*args, **kwargs):
        try:
            return await orig_edit_text(*args, **kwargs)
        except Exception as e:
            err = str(e).upper()
            if "MESSAGE_NOT_MODIFIED" in err:
                return None
            try:
                text = kwargs.get("text") or (args[0] if args else "")
                reply_markup = kwargs.get("reply_markup") or (args[1] if len(args) > 1 else None)
                parse_mode = kwargs.get("parse_mode")
                return await callback_query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception as e2:
                if "MESSAGE_NOT_MODIFIED" in str(e2).upper():
                    return None
                raise e2

    callback_query.edit_message_text = safe_edit_text

    data = callback_query.data
    print(f"ℹ️ [INLINE_YARDIM] Butona tıklandı. İstek: '{data}'")
    
    try:
        if data == "ilet_noop":
            await callback_query.answer()
            return

        if data.startswith("ilet_n_"):
            from plugins.ilet import get_all_user_groups, toggle_group
            parts = data.split("_")
            idx = int(parts[2])
            page = int(parts[3])
            userbot = utils.bot_client
            if userbot:
                gruplar = await get_all_user_groups(userbot)
                if 1 <= idx <= len(gruplar):
                    hedef = gruplar[idx - 1]
                    yeni_durum = toggle_group(hedef["id"])
                    durum_str = "AÇIK ✅" if yeni_durum else "KAPALI ⛔"
                    kb, metin = await build_ilet_menu_keyboard(page)
                    try:
                        await callback_query.edit_message_text(text=metin, reply_markup=kb)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e):
                            raise e
                    await callback_query.answer(f"{idx}. {hedef['title'][:20]} -> {durum_str}")
                    return
            await callback_query.answer("Hata oluştu.", show_alert=True)
            return

        if data.startswith("ilet_p_"):
            page = int(data.split("_")[2])
            kb, metin = await build_ilet_menu_keyboard(page)
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e):
                    raise e
            await callback_query.answer()
            return

        if data == "ilet_close":
            deleted = False
            # 1. Eğer normal bir bot mesajıysa doğrudan bot silsin
            if callback_query.message:
                try:
                    await callback_query.message.delete()
                    deleted = True
                except Exception:
                    pass

            # 2. Eğer inline mesajsa userbot üzerinden mesaj silinsin
            if not deleted and getattr(utils, "LAST_ILET_MENU", None):
                try:
                    chat_id, msg_id = utils.LAST_ILET_MENU
                    userbot = utils.bot_client
                    if userbot:
                        await userbot.delete_messages(chat_id, msg_id)
                        deleted = True
                except Exception as e:
                    print(f"İlet menü userbot silme hatası: {e}")

            # 3. Silinemezse fallback olarak inline mesaj içeriğini ve butonlarını temizle
            if not deleted and callback_query.inline_message_id:
                try:
                    await callback_query.edit_message_text("🗑️ <b>Menü kapatıldı.</b>")
                except Exception:
                    pass

            await callback_query.answer()
            return

        # ---------------------------------------------------------------------
        # OTOMESAJ CALLBACK İŞLEYİCİLERİ
        # ---------------------------------------------------------------------
        if data == "otomsg_noop":
            await callback_query.answer()
            return

        if data == "otomsg_list":
            kb, metin = await build_otomesaj_list_keyboard()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("otomsg_view_"):
            tid = int(data.split("_")[2])
            kb, metin = await build_otomesaj_detail_keyboard(tid)
            if kb:
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=kb)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("otomsg_toggle_"):
            from plugins.otomesaj import otomesaj_db_yukle, otomesaj_db_kaydet
            tid = int(data.split("_")[2])
            db = otomesaj_db_yukle()
            if str(tid) in db:
                yeni = not db[str(tid)].get("aktif", True)
                db[str(tid)]["aktif"] = yeni
                otomesaj_db_kaydet(db, sync_cloud=True)
                durum_msg = "Başlatıldı ✅" if yeni else "Duraklatıldı ⏸"
                kb, metin = await build_otomesaj_detail_keyboard(tid)
                if kb:
                    try:
                        await callback_query.edit_message_text(text=metin, reply_markup=kb)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer(f"Görev #{tid} {durum_msg}")
            else:
                await callback_query.answer("Görev bulunamadı!", show_alert=True)
            return

        if data.startswith("otomsg_togold_"):
            from plugins.otomesaj import otomesaj_db_yukle, otomesaj_db_kaydet
            tid = int(data.split("_")[2])
            db = otomesaj_db_yukle()
            if str(tid) in db:
                yeni = not db[str(tid)].get("onceki_sil", False)
                db[str(tid)]["onceki_sil"] = yeni
                otomesaj_db_kaydet(db, sync_cloud=True)
                durum_msg = "Önceki Mesajı Sil: AÇIK ✅" if yeni else "Önceki Mesajı Sil: KAPALI ❌"
                kb, metin = await build_otomesaj_detail_keyboard(tid)
                if kb:
                    try:
                        await callback_query.edit_message_text(text=metin, reply_markup=kb)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer(durum_msg)
            else:
                await callback_query.answer("Görev bulunamadı!", show_alert=True)
            return

        if data.startswith("otomsg_time_"):
            tid = int(data.split("_")[2])
            kb, metin = await build_otomesaj_time_keyboard(tid)
            if kb:
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=kb)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("otomsg_settime_"):
            from plugins.otomesaj import otomesaj_db_yukle, otomesaj_db_kaydet, format_sure
            parts = data.split("_")
            tid = int(parts[2])
            mins = float(parts[3])
            db = otomesaj_db_yukle()
            if str(tid) in db:
                db[str(tid)]["aralik_dakika"] = mins
                otomesaj_db_kaydet(db, sync_cloud=True)
                kb, metin = await build_otomesaj_time_keyboard(tid)
                if kb:
                    try:
                        await callback_query.edit_message_text(text=metin, reply_markup=kb)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer(f"Süre: {format_sure(mins)}")
            return

        if data.startswith("otomsg_adjtime_"):
            from plugins.otomesaj import otomesaj_db_yukle, otomesaj_db_kaydet, format_sure, MIN_ARALIK_DAKIKA
            parts = data.split("_")
            tid = int(parts[2])
            delta = float(parts[3])
            db = otomesaj_db_yukle()
            if str(tid) in db:
                curr = db[str(tid)].get("aralik_dakika", 60.0)
                new_m = max(MIN_ARALIK_DAKIKA, curr + delta)
                db[str(tid)]["aralik_dakika"] = new_m
                otomesaj_db_kaydet(db, sync_cloud=True)
                kb, metin = await build_otomesaj_time_keyboard(tid)
                if kb:
                    try:
                        await callback_query.edit_message_text(text=metin, reply_markup=kb)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer(f"Yeni Süre: {format_sure(new_m)}")
            return

        if data.startswith("otomsg_grp_"):
            parts = data.split("_")
            tid = int(parts[2])
            page = int(parts[3])
            kb, metin = await build_otomesaj_groups_keyboard(tid, page)
            if kb:
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=kb)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("otomsg_toggleg_"):
            from plugins.otomesaj import otomesaj_db_yukle, otomesaj_db_kaydet
            from plugins.ilet import get_all_user_groups
            parts = data.split("_")
            tid = int(parts[2])
            idx = int(parts[3])
            page = int(parts[4])
            db = otomesaj_db_yukle()
            userbot = utils.bot_client
            if str(tid) in db and userbot:
                gruplar = await get_all_user_groups(userbot)
                if 1 <= idx <= len(gruplar):
                    g_id = gruplar[idx - 1]["id"]
                    hedef = db[str(tid)].get("hedef_gruplar", [])
                    if g_id in hedef:
                        hedef.remove(g_id)
                        yeni_d = "KAPALI ⛔"
                    else:
                        hedef.append(g_id)
                        yeni_d = "AÇIK ✅"
                    db[str(tid)]["hedef_gruplar"] = hedef
                    otomesaj_db_kaydet(db, sync_cloud=True)
                    kb, metin = await build_otomesaj_groups_keyboard(tid, page)
                    if kb:
                        try:
                            await callback_query.edit_message_text(text=metin, reply_markup=kb)
                        except Exception as e:
                            if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                    await callback_query.answer(f"{idx}. Grup -> {yeni_d}")
                    return
            await callback_query.answer("Hata oluştu.", show_alert=True)
            return

        if data.startswith("otomsg_grpall_"):
            from plugins.otomesaj import otomesaj_db_yukle, otomesaj_db_kaydet
            from plugins.ilet import get_all_user_groups
            parts = data.split("_")
            tid = int(parts[2])
            action = parts[3]
            page = int(parts[4])
            db = otomesaj_db_yukle()
            userbot = utils.bot_client
            if str(tid) in db and userbot:
                gruplar = await get_all_user_groups(userbot)
                if action == "all":
                    db[str(tid)]["hedef_gruplar"] = [g["id"] for g in gruplar]
                    msg = "Tüm gruplar seçildi ✅"
                else:
                    db[str(tid)]["hedef_gruplar"] = []
                    msg = "Tüm gruplar kaldırıldı ⛔"
                otomesaj_db_kaydet(db, sync_cloud=True)
                kb, metin = await build_otomesaj_groups_keyboard(tid, page)
                if kb:
                    try:
                        await callback_query.edit_message_text(text=metin, reply_markup=kb)
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer(msg)
                return

        if data.startswith("otomsg_sendnow_"):
            from plugins.otomesaj import otomesaj_db_yukle, execute_task_broadcast
            tid = int(data.split("_")[2])
            db = otomesaj_db_yukle()
            task = db.get(str(tid))
            userbot = utils.bot_client
            if task and userbot:
                asyncio.create_task(execute_task_broadcast(userbot, tid, task))
                await callback_query.answer(f"🚀 Görev #{tid} şimdi iletiliyor...", show_alert=False)
            else:
                await callback_query.answer("Görev başlatılamadı!", show_alert=True)
            return

        if data.startswith("otomsg_del_"):
            from plugins.otomesaj import otomesaj_db_yukle, otomesaj_db_kaydet
            tid = int(data.split("_")[2])
            db = otomesaj_db_yukle()
            if str(tid) in db:
                silinen = db.pop(str(tid))
                otomesaj_db_kaydet(db, sync_cloud=True)
                kb, metin = await build_otomesaj_list_keyboard()
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=kb)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer(f"🗑 Görev #{tid} ({silinen['baslik']}) silindi.")
            return

        if data == "otomsg_close":
            deleted = False
            if callback_query.message:
                try:
                    await callback_query.message.delete()
                    deleted = True
                except Exception:
                    pass

            if not deleted and getattr(utils, "LAST_OTOMESAJ_MENU", None):
                try:
                    chat_id, msg_id = utils.LAST_OTOMESAJ_MENU
                    userbot = utils.bot_client
                    if userbot:
                        await userbot.delete_messages(chat_id, msg_id)
                        deleted = True
                except Exception as e:
                    print(f"Otomesaj menü userbot silme hatası: {e}")

            if not deleted and callback_query.inline_message_id:
                try:
                    await callback_query.edit_message_text("🗑️ <b>Menü kapatıldı.</b>")
                except Exception:
                    pass

            await callback_query.answer()
            return

        if data == "yardim_noop":
            await callback_query.answer()
            return

        if data == "yardim_close":
            deleted = False
            userbot = utils.bot_client

            # 1. Normal sohbet mesajı ise
            if callback_query.message:
                try:
                    await callback_query.message.delete()
                    deleted = True
                except Exception:
                    pass

            # 2. Kayıtlı son menü ID'si varsa userbot ile sil
            if not deleted and getattr(utils, "LAST_YARDIM_MENU", None):
                try:
                    chat_id, msg_id = utils.LAST_YARDIM_MENU
                    if userbot and msg_id:
                        await userbot.delete_messages(chat_id, msg_id)
                        deleted = True
                        utils.LAST_YARDIM_MENU = None
                except Exception as e:
                    print(f"Yardım menü userbot silme hatası: {e}")

            # 3. Inline message id'den chat/msg id çözerek userbot ile sil
            if not deleted and callback_query.inline_message_id and userbot:
                try:
                    import pyrogram.utils
                    unpacked = pyrogram.utils.unpack_inline_message_id(callback_query.inline_message_id)
                    u_id = getattr(unpacked, "id", None)
                    u_owner = getattr(unpacked, "owner_id", None)
                    if u_id and u_owner:
                        candidate_chats = [int(f"-100{u_owner}"), -u_owner, u_owner]
                        for c_chat in candidate_chats:
                            try:
                                await userbot.delete_messages(c_chat, u_id)
                                deleted = True
                                break
                            except Exception:
                                pass
                except Exception:
                    pass

            # 4. Eğer hala silinemediyse, kullanıcının son via_bot mesajını ara ve sil
            if not deleted and userbot and getattr(utils, "LAST_YARDIM_MENU", None):
                try:
                    chat_id, _ = utils.LAST_YARDIM_MENU
                    async for m in userbot.get_chat_history(chat_id, limit=5):
                        if m.from_user and m.from_user.is_self and m.via_bot:
                            await m.delete()
                            deleted = True
                            break
                except Exception:
                    pass

            if deleted:
                try:
                    await callback_query.answer("🗑️ Menü kapatıldı.", show_alert=False)
                except Exception:
                    pass
            else:
                try:
                    await callback_query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
                try:
                    await callback_query.answer("Menü kapatıldı.", show_alert=False)
                except Exception:
                    pass
            return

        if data == "main_menu":
            metin = get_main_menu_text()
            keyboard = get_main_menu_keyboard()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            print(f"✅ [INLINE_YARDIM] 'main_menu' başarıyla yüklendi.")
            return
            
        if data == "ayarlar_menu":
            keyboard, metin = get_settings_keyboard()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            print(f"✅ [INLINE_YARDIM] 'ayarlar_menu' başarıyla yüklendi.")
            return

        if data == "btn_durum":
            keyboard, metin = get_detailed_status_content()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data == "btn_restart":
            await callback_query.answer("🔄 Bot yeniden başlatılıyor...", show_alert=True)
            try:
                await callback_query.edit_message_text(
                    "🔄 <b>Bot yeniden başlatılıyor...</b>\n"
                    "<i>Lütfen birkaç saniye bekleyin, bot kısa süre içinde aktif olacaktır.</i>"
                )
            except Exception:
                pass
            utils.restart_bildirimi_kaydet(
                action="restart",
                inline_message_id=callback_query.inline_message_id,
                chat_id=callback_query.message.chat.id if callback_query.message else None,
                message_id=callback_query.message.id if callback_query.message else None
            )
            os.execl(sys.executable, sys.executable, *sys.argv)
            return

        if data == "btn_update":
            await callback_query.answer()
            try:
                subprocess.run(["git", "config", "--global", "--add", "safe.directory", "*"], capture_output=True)
                repo_url = os.getenv("UPSTREAM_REPO", "https://github.com/chaolcam/gagaragogo-userbot.git")
                subprocess.run(["git", "remote", "set-url", "origin", repo_url], capture_output=True)

                eski_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "v2.6"
                fetch_res = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True)

                if fetch_res.returncode != 0 and ("fatal" in fetch_res.stderr.lower() or "error" in fetch_res.stderr.lower()):
                    await callback_query.edit_message_text(
                        f"❌ <b>Git Hatası:</b>\n<code>{fetch_res.stderr[:100]}</code>",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("◀️ Ayarlar", callback_data="ayarlar_menu"),
                            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
                        ]])
                    )
                    return

                remote_commit = subprocess.run(["git", "rev-parse", "--short", "origin/main"], capture_output=True, text=True).stdout.strip() or eski_commit

                if eski_commit == remote_commit:
                    metin = (
                        "<b>GÜNCELLEME DENETİMİ</b>\n"
                        "────────────────────────\n"
                        "✅ <b>Tebrikler, botunuz en son sürümde!</b>\n\n"
                        f"📌 <b>Mevcut Sürüm:</b> <code>{eski_commit} (Son Sürüm)</code>\n"
                        f"📡 <b>GitHub:</b> <code>{remote_commit}</code>\n\n"
                        "🕒 <i>Yeni bir güncelleme bulunmuyor, tüm sistemler güncel.</i>"
                    )
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Tekrar Kontrol Et", callback_data="btn_update")],
                        [
                            InlineKeyboardButton("◀️ Ayarlar", callback_data="ayarlar_menu"),
                            InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
                        ]
                    ])
                    await callback_query.edit_message_text(text=metin, reply_markup=kb)
                    return

                # Yeni güncelleme bulundu, güncelle ve yeniden başlat
                try:
                    await callback_query.edit_message_text(
                        f"🔄 <b>Yeni Güncelleme Bulundu!</b> (<code>{eski_commit}</code> ➔ <code>{remote_commit}</code>)\n"
                        "Kodlar eşitleniyor ve bot yeniden başlatılıyor..."
                    )
                except Exception:
                    pass

                subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True)
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--break-system-packages"], capture_output=True)
                utils.restart_bildirimi_kaydet(
                    action="update",
                    inline_message_id=callback_query.inline_message_id,
                    chat_id=callback_query.message.chat.id if callback_query.message else None,
                    message_id=callback_query.message.id if callback_query.message else None,
                    eski_commit=eski_commit,
                    yeni_commit=remote_commit
                )
                os.execl(sys.executable, sys.executable, *sys.argv)
            except Exception as e:
                await callback_query.edit_message_text(
                    f"❌ <b>Güncelleme Hatası:</b> <code>{e}</code>",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Ayarlar", callback_data="ayarlar_menu")]])
                )
            return

        # ---------------------------------------------------------------------
        # EKLENTİ YÖNETİMİ & MAĞAZA CALLBACK İŞLEYİCİLERİ
        # ---------------------------------------------------------------------
        if data == "eklenti_ana_menu":
            kb, metin = await build_eklenti_ana_menu_keyboard()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("eklenti_magaza_"):
            page = int(data.split("_")[2])
            kb, metin = await build_eklenti_magaza_keyboard(page)
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("eklenti_detay_"):
            msg_id = int(data.split("_")[2])
            kb, metin = await build_eklenti_detay_keyboard(msg_id)
            if kb:
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=kb)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("eklenti_kur_"):
            msg_id = int(data.split("_")[2])
            userbot = utils.bot_client
            if not userbot:
                try: await callback_query.answer("❌ Userbot aktif değil!", show_alert=True)
                except: pass
                return

            try:
                await callback_query.edit_message_text(
                    "⏳ <b>Eklenti İndiriliyor ve Kuruluyor...</b>\n\n"
                    "Lütfen bekleyin, eklenti dosyası mağazadan indiriliyor, güvenlik kontrolünden geçiriliyor ve canlı hafızaya bağlanıyor..."
                )
            except Exception:
                pass

            from plugins.plugin_manager import PLUGIN_STORE_CHANNEL, install_plugin_from_file
            try:
                target_msg = await userbot.get_messages(PLUGIN_STORE_CHANNEL, message_ids=msg_id)
                if not target_msg or not target_msg.document:
                    try: await callback_query.answer("❌ Eklenti dosyası bulunamadı!", show_alert=True)
                    except: pass
                    try:
                        await callback_query.edit_message_text(
                            "❌ <b>Eklenti Bulunamadı:</b>\n\nKanalda bu numaraya ait geçerli bir eklenti belgesi bulunamadı.",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Mağazaya Dön", callback_data="eklenti_magaza_1")]])
                        )
                    except: pass
                    return

                doc = target_msg.document
                os.makedirs("downloads", exist_ok=True)
                temp_path = os.path.join("downloads", f"temp_{doc.file_name}")
                await userbot.download_media(target_msg, file_name=temp_path)

                raw_name = doc.file_name[:-3] if doc.file_name.endswith(".py") else doc.file_name
                caption = target_msg.caption or target_msg.text or ""

                success, res_msg = await install_plugin_from_file(
                    userbot,
                    temp_path,
                    raw_name,
                    kaynak=f"@{PLUGIN_STORE_CHANNEL} (Mağaza)",
                    kanal_msg_id=msg_id,
                    aciklama=caption
                )
                if os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except: pass

                if success:
                    try: await callback_query.answer("✅ Eklenti başarıyla yüklendi!", show_alert=False)
                    except: pass
                    kb, _ = await build_eklenti_yuklu_keyboard(1)
                    try:
                        await callback_query.edit_message_text(
                            text=(
                                "<b>EKLENTİ AKTİF EDİLDİ</b>\n"
                                "────────────────────────\n"
                                f"Modül: <code>{raw_name}</code> • Durum: <b>Canlı Aktif</b>"
                            ),
                            reply_markup=kb
                        )
                    except Exception:
                        pass
                else:
                    try: await callback_query.answer("❌ Kurulum hatası!", show_alert=True)
                    except: pass
                    try:
                        await callback_query.edit_message_text(
                            text=f"❌ <b>Kurulum Tamamlanamadı:</b>\n\n{res_msg}",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Mağazaya Dön", callback_data="eklenti_magaza_1")]])
                        )
                    except Exception:
                        pass
            except Exception as ke:
                try: await callback_query.answer("❌ Beklenmeyen hata oluştu!", show_alert=True)
                except: pass
                try:
                    await callback_query.edit_message_text(
                        text=f"❌ <b>Beklenmeyen Hata:</b>\n<code>{str(ke)}</code>",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Mağazaya Dön", callback_data="eklenti_magaza_1")]])
                    )
                except Exception:
                    pass
            return

        if data.startswith("eklenti_yuklu_"):
            page = int(data.split("_")[2])
            kb, metin = await build_eklenti_yuklu_keyboard(page)
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("eklenti_bilgi_"):
            p_name = data.split("_", 2)[2]
            kb, metin = await build_eklenti_bilgi_keyboard(p_name)
            if kb:
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=kb)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("eklenti_kaldir_"):
            page = int(data.split("_")[2])
            kb, metin = await build_eklenti_kaldir_keyboard(page)
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data.startswith("eklenti_sil_"):
            p_name = data.split("_", 2)[2]
            userbot = utils.bot_client
            from plugins.plugin_manager import uninstall_custom_plugin
            success, res_msg = await uninstall_custom_plugin(userbot, p_name)
            if success:
                await callback_query.answer(f"🗑️ '{p_name}' başarıyla kaldırıldı.", show_alert=True)
                kb, metin = await build_eklenti_kaldir_keyboard(1)
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=kb)
                except Exception: pass
            else:
                await callback_query.answer(res_msg, show_alert=True)
            return
            
        if data == "toggle_sureli":
            mevcut = utils.ayar_getir("hayalet_durumu", False)
            utils.ayar_kaydet("hayalet_durumu", not mevcut)
            keyboard, metin = get_settings_keyboard()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer("Süreli modu değiştirildi.")
            print(f"✅ [INLINE_YARDIM] 'toggle_sureli' başarıyla çalıştırıldı. Yeni Durum: {not mevcut}")
            return
            
        if data == "toggle_antidelete":
            mevcut = utils.ayar_getir("antidelete_durumu", False)
            utils.ayar_kaydet("antidelete_durumu", not mevcut)
            keyboard, metin = get_settings_keyboard()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer("Anti-Delete modu değiştirildi.")
            print(f"✅ [INLINE_YARDIM] 'toggle_antidelete' başarıyla çalıştırıldı. Yeni Durum: {not mevcut}")
            return
            
        # ---------------------------------------------------------------------
        # TOPLU İLETİM & ARAÇLAR ALT PENCERE CALLBACK'LERİ
        # ---------------------------------------------------------------------
        if data == "sub_ilet_anlik":
            kb, metin = get_ilet_anlik_content()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data == "sub_ilet_otomesaj":
            kb, metin = get_ilet_otomesaj_content()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data == "open_ilet_groups":
            kb, metin = await build_ilet_menu_keyboard(1)
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data == "sub_arac_indir":
            kb, metin = get_araclar_indir_content()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data == "sub_arac_donustur":
            kb, metin = get_araclar_donustur_content()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data == "sub_arac_koruma":
            kb, metin = get_araclar_koruma_content()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data == "sub_arac_cevir":
            kb, metin = get_araclar_cevir_content()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            await callback_query.answer()
            return

        if data in ("toggle_sureli_from_koruma", "toggle_antidelete_from_koruma"):
            if data == "toggle_sureli_from_koruma":
                mevcut = utils.ayar_getir("hayalet_durumu", False)
                utils.ayar_kaydet("hayalet_durumu", not mevcut)
                await callback_query.answer("Süreli medya modu değiştirildi.")
            else:
                mevcut = utils.ayar_getir("antidelete_durumu", False)
                utils.ayar_kaydet("antidelete_durumu", not mevcut)
                await callback_query.answer("Anti-Delete modu değiştirildi.")
            kb, metin = get_araclar_koruma_content()
            try:
                await callback_query.edit_message_text(text=metin, reply_markup=kb)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
            return

        if data.startswith("kat_"):
            parts = data.split("_")
            kategori_key = parts[1]
            sayfa = int(parts[2])
            kategori_low = kategori_key.lower()
            
            # Toplu İletim ve Araçlar için özel alt hub pencereleri
            if "toplu" in kategori_low or "ilet" in kategori_low:
                keyboard, metin = get_ilet_hub_content()
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer()
                return

            if "araç" in kategori_low or "arac" in kategori_low:
                keyboard, metin = get_araclar_hub_content()
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer()
                return

            keyboard, metin = get_category_keyboard(kategori_key, sayfa)
            if keyboard:
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer()
                print(f"✅ [INLINE_YARDIM] Kategori '{kategori_key}' (Sayfa {sayfa}) yüklendi.")
            else:
                await callback_query.answer(metin, show_alert=True)
                print(f"⚠️ [INLINE_YARDIM] Kategori bulunamadı: '{kategori_key}'")
            return
            
        if data.startswith("csub:"):
            _, kategori_key, back_target, komut_adi = data.split(":", 3)
            
            komut_detay = None
            kategori_data = KOMUT_BILGILERI.get(kategori_key)
            if not kategori_data:
                for k, v in KOMUT_BILGILERI.items():
                    if k.lower() == kategori_key.lower():
                        kategori_data = v
                        break

            if kategori_data and komut_adi in kategori_data.get("komutlar", {}):
                komut_detay = kategori_data["komutlar"][komut_adi]
            else:
                for cat in KOMUT_BILGILERI.values():
                    if komut_adi in cat.get("komutlar", {}):
                        komut_detay = cat["komutlar"][komut_adi]
                        break

            if komut_detay:
                metin = (
                    f"<b>KOMUT:</b> <code>.{komut_adi}</code>\n"
                    "────────────────────────\n"
                    f"<b>Açıklama:</b> {komut_detay['aciklama']}\n"
                    f"<b>Kullanım:</b> <code>{komut_detay['kullanim']}</code>"
                )
                
                # Dinamik Ayar Göstergeleri
                if komut_adi == "dil":
                    metin += f"\n\n🌍 <b>Varsayılan Dil:</b> <code>{utils.ayar_getir('cevir_hedef_dil', 'tr')}</code>"
                elif komut_adi == "antidelete":
                    durum = "AÇIK ✅" if utils.ayar_getir("antidelete_durumu", False) else "KAPALI ❌"
                    metin += f"\n\n🗑 <b>Durum:</b> <code>{durum}</code>"
                elif komut_adi == "sureli":
                    durum = "AÇIK ⏳" if utils.ayar_getir("hayalet_durumu", False) else "KAPALI ❌"
                    metin += f"\n\n⏳ <b>Durum:</b> <code>{durum}</code>"
                elif komut_adi == "setyedekgrup":
                    metin += f"\n\n🔸 <b>Admin / Yedek Grup:</b> <code>{utils.get_yedek_grup_id()}</code>"
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Geri", callback_data=back_target)],
                    [
                        InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
                        InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
                    ]
                ])
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer()
                print(f"✅ [INLINE_YARDIM] Komut detayı '{komut_adi}' yüklendi.")
                return
                    
            await callback_query.answer("Detay bulunamadı.", show_alert=True)
            print(f"⚠️ [INLINE_YARDIM] Komut detayı bulunamadı: '{komut_adi}'")
            return
            
        if data.startswith("cmd_"):
            parts = data.split("_", 3)
            kategori_key = parts[1]
            sayfa = parts[2]
            komut_adi = parts[3]
            
            # Komut detayını ara (önce belirtilen kategoriden, yoksa tüm kategorilerden)
            kategori_data = KOMUT_BILGILERI.get(kategori_key)
            if not kategori_data:
                for k, v in KOMUT_BILGILERI.items():
                    if k.lower() == kategori_key.lower():
                        kategori_data = v
                        break

            komut_detay = None
            if kategori_data and komut_adi in kategori_data.get("komutlar", {}):
                komut_detay = kategori_data["komutlar"][komut_adi]
            else:
                for cat in KOMUT_BILGILERI.values():
                    if komut_adi in cat.get("komutlar", {}):
                        komut_detay = cat["komutlar"][komut_adi]
                        break

            if komut_detay:
                metin = (
                    f"<b>KOMUT:</b> <code>.{komut_adi}</code>\n"
                    "────────────────────────\n"
                    f"<b>Açıklama:</b> {komut_detay['aciklama']}\n"
                    f"<b>Kullanım:</b> <code>{komut_detay['kullanim']}</code>"
                )
                
                # Dinamik Ayar Göstergeleri
                if komut_adi == "dil":
                    metin += f"\n\n🌍 <b>Varsayılan Dil:</b> <code>{utils.ayar_getir('cevir_hedef_dil', 'tr')}</code>"
                elif komut_adi == "antidelete":
                    durum = "AÇIK ✅" if utils.ayar_getir("antidelete_durumu", False) else "KAPALI ❌"
                    metin += f"\n\n🗑 <b>Durum:</b> <code>{durum}</code>"
                elif komut_adi == "sureli":
                    durum = "AÇIK ⏳" if utils.ayar_getir("hayalet_durumu", False) else "KAPALI ❌"
                    metin += f"\n\n⏳ <b>Durum:</b> <code>{durum}</code>"
                elif komut_adi == "setyedekgrup":
                    metin += f"\n\n🔸 <b>Admin / Yedek Grup:</b> <code>{utils.get_yedek_grup_id()}</code>"
                
                # Alt kategoriden gelinmişse o alt kategoriye geri dönsün
                back_target = sayfa if sayfa.startswith("sub_") else f"kat_{kategori_key}_{sayfa}"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Geri", callback_data=back_target)],
                    [
                        InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
                        InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
                    ]
                ])
                try:
                    await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
                except Exception as e:
                    if "MESSAGE_NOT_MODIFIED" not in str(e): raise e
                await callback_query.answer()
                print(f"✅ [INLINE_YARDIM] Komut detayı '{komut_adi}' yüklendi.")
                return
                    
            await callback_query.answer("Detay bulunamadı.", show_alert=True)
            print(f"⚠️ [INLINE_YARDIM] Komut detayı bulunamadı: '{komut_adi}'")
            return
            
        if data.startswith("ig_"):
            try:
                from plugins.instagram import fetch_instagram_data, get_rapidapi_keys_list
            except ImportError:
                from plugins.araclar import fetch_instagram_data, get_rapidapi_keys_list

            if not get_rapidapi_keys_list():
                await callback_query.answer("⚠️ RapidAPI anahtarınız yok! Lütfen sohbette .rapidapi [anahtar] yazarak anahtarınızı ekleyin.", show_alert=True)
                return

            parts = data.split("_")
            action = parts[1]
            username = parts[2]
            index = int(parts[3])
            
            await callback_query.answer("Veriler çekiliyor, lütfen bekleyin...", show_alert=False)
            
            if action == "story":
                endpoint = "stories"
            elif action == "post":
                endpoint = "posts"
            elif action == "high":
                endpoint = "highlights"
            elif action == "dl":
                endpoint_map = {"story": "stories", "post": "posts", "high": "highlights"}
                dl_type = parts[4]
                endpoint = endpoint_map.get(dl_type, "stories")
            else:
                return
                
            try:
                resp = await asyncio.to_thread(fetch_instagram_data, endpoint, username)
                
                items = []
                if endpoint == "posts":
                    items = resp.get("result", {}).get("edges", [])
                else:
                    items = resp.get("result", [])
                    
                if not items:
                    await callback_query.edit_message_text(f"❌ `@{username}` için içerik bulunamadı.")
                    return
                    
                if index < 0: index = len(items) - 1
                if index >= len(items): index = 0
                
                item = items[index]
                
                # Extract URL
                media_url = None
                if endpoint == "posts":
                    node = item.get("node", {})
                    if "video_versions" in node and node["video_versions"]:
                        media_url = node["video_versions"][0]["url"]
                    elif "image_versions2" in node and node["image_versions2"] and "candidates" in node["image_versions2"]:
                        media_url = node["image_versions2"]["candidates"][0]["url"]
                else:
                    if "video_versions" in item and item["video_versions"]:
                        media_url = item["video_versions"][0]["url"]
                    elif "image_versions2" in item and item["image_versions2"] and "candidates" in item["image_versions2"]:
                        media_url = item["image_versions2"]["candidates"][0]["url"]
                        
                if action == "dl" and media_url:
                    await callback_query.answer("İndiriliyor, lütfen bekleyin...", show_alert=False)
                    try:
                        from utils import get_yedek_grup_id, create_forum_topic_helper
                        
                        hedef_chat = get_yedek_grup_id()
                        if not hedef_chat:
                            await client.send_message(callback_query.message.chat.id, "Yedek grup ayarlanmamış!")
                            return
                            
                        from utils import bot_client as userbot
                        
                        # Cache IG topic IDs
                        ig_db_file = "ig_topics.json"
                        ig_topics = {}
                        if os.path.exists(ig_db_file):
                            try:
                                with open(ig_db_file, "r", encoding="utf-8") as f:
                                    ig_topics = json.load(f)
                            except: pass
                            
                        topic_id = ig_topics.get(username)
                        if not topic_id:
                            topic_id = await create_forum_topic_helper(userbot, hedef_chat, f"IG: {username}")
                            if topic_id:
                                ig_topics[username] = topic_id
                                with open(ig_db_file, "w", encoding="utf-8") as f:
                                    json.dump(ig_topics, f, ensure_ascii=False, indent=4)
                        
                        # Helper bot sends the media directly to the chat
                        ext = "mp4" if "mp4" in media_url or "video" in media_url else "jpg"
                        path = f"downloads/ig_dl_{uuid.uuid4().hex[:6]}.{ext}"
                        os.makedirs("downloads", exist_ok=True)
                        res = requests.get(media_url, timeout=15).content
                        with open(path, "wb") as f: f.write(res)
                        
                        try:
                            if ext == "mp4":
                                await userbot.send_video(chat_id=hedef_chat, video=path, caption=f"@{username} medyası", reply_to_message_id=topic_id)
                            else:
                                await userbot.send_photo(chat_id=hedef_chat, photo=path, caption=f"@{username} medyası", reply_to_message_id=topic_id)
                        except Exception as e:
                            await userbot.send_message(chat_id=hedef_chat, text=f"Medya yüklenirken hata oluştu: {e}", reply_to_message_id=topic_id)
                        os.remove(path)
                        await callback_query.answer("Medya arşive (IG Konusuna) başarıyla gönderildi!", show_alert=True)
                        return
                    except Exception as ex:
                        try: os.remove(path)
                        except: pass
                        await callback_query.answer(f"Arşive yüklenirken hata oluştu (Bot grupta admin mi?): {ex}", show_alert=True)
                        return
                
                if not media_url:
                    media_url = "Medya bulunamadı"
                    
                metin = (
                    f"<b>Instagram:</b> <code>@{username}</code> ⬝ <b>{endpoint.capitalize()}</b>\n"
                    "────────────────────────\n"
                    f"Medya {index+1} / {len(items)}\n\n"
                    f"<a href=\"{media_url}\">Medyayı Görüntüle</a>"
                )
                
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("◀️ Önceki", callback_data=f"ig_{action}_{username}_{index-1}"),
                        InlineKeyboardButton("Sonraki ▶️", callback_data=f"ig_{action}_{username}_{index+1}")
                    ],
                    [InlineKeyboardButton("📥 Hedefe İndir", callback_data=f"ig_dl_{username}_{index}_{action}")],
                    [InlineKeyboardButton("🏠 Geri", callback_data=f"ig_menu_{username}")]
                ])
                
                await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
                
            except Exception as e:
                await callback_query.edit_message_text(f"❌ Hata: <code>{str(e)}</code>")
            return
            
        if data.startswith("ig_menu_"):
            username = data.split("_")[2]
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📸 Hikayeler", callback_data=f"ig_story_{username}_0")],
                [InlineKeyboardButton("🖼 Gönderiler", callback_data=f"ig_post_{username}_0")],
                [InlineKeyboardButton("⭐ Öne Çıkanlar", callback_data=f"ig_high_{username}_0")]
            ])
            metin = (
                f"<b>Instagram:</b> <code>@{username}</code>\n"
                "────────────────────────\n"
                "Görüntülemek istediğiniz medya türünü seçin:"
            )
            await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
            return
            
    except Exception as e:
        print(f"❌ [INLINE_YARDIM] Hata oluştu (Veri: {data}): {type(e).__name__} - {e}")
        try:
            await callback_query.answer(f"Bir hata oluştu: {type(e).__name__}", show_alert=True)
        except: pass
