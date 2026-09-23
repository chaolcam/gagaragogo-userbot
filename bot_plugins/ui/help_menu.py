# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Help & System Settings Menus
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import sys
import time
import logging
import platform
import subprocess
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.system import KOMUT_BILGILERI
import utils
from bot_plugins.ui.common import check_update_status, safe_edit

logger = logging.getLogger(__name__)


def get_main_menu_text():
    """Canlı durum ve sistem paneli (.alive) metnini üretir."""
    import psutil

    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_str = f"{int(uptime_seconds // 86400)}g {int((uptime_seconds % 86400) // 3600)}s {int((uptime_seconds % 3600) // 60)}d"
    except Exception:
        uptime_str = "Aktif"

    try:
        cpu = psutil.cpu_percent(interval=None)
    except Exception:
        cpu = 0

    try:
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_str = f"{ram.used / (1024**2):.0f}MB / {ram.total / (1024**2):.0f}MB"
    except Exception:
        ram_percent = 0
        ram_str = "0MB"

    commit, durum_surum = check_update_status()
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
    """Yardım menüsü için dengeli 2 sütunlu interaktif kategori klavyesi oluşturur."""
    oncelik_haritasi = {
        "admin": 10,
        "araçlar": 20,
        "araclar": 20,
        "eğlence": 30,
        "eglence": 30,
        "sistem": 40,
        "grup & iletim": 50,
        "medya": 60
    }
    kategoriler = [k for k in KOMUT_BILGILERI.keys() if k.lower() != "ayarlar"]
    kategoriler.sort(key=lambda x: oncelik_haritasi.get(x.lower(), 99))
    keyboard = []

    def get_icon(isim):
        isim_low = isim.lower()
        if "admin" in isim_low: return "🛡"
        if "araç" in isim_low or "arac" in isim_low: return "🛠"
        if "grup" in isim_low or "ilet" in isim_low or "toplu" in isim_low: return "📢"
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
        [InlineKeyboardButton("🌐 Dil Değiştir (TR / EN)", callback_data="toggle_lang")],
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
    import psutil

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
    except Exception:
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


def get_araclar_hub_content():
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
                kategori_key = k
                break

    if not kategori_data:
        return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="main_menu")]]), "Kategori bulunamadı."

    kategori_adi = kategori_data["isim"]
    komutlar = kategori_data.get("komutlar", {})
    komut_listesi = list(komutlar.keys())

    sayfa = int(sayfa)
    sayfa_basi = 6
    toplam_sayfa = (len(komut_listesi) + sayfa_basi - 1) // sayfa_basi or 1

    if sayfa < 1: sayfa = 1
    if sayfa > toplam_sayfa: sayfa = toplam_sayfa

    start = (sayfa - 1) * sayfa_basi
    end = start + sayfa_basi
    sayfa_komutlari = komut_listesi[start:end]

    keyboard = []
    for i in range(0, len(sayfa_komutlari), 2):
        row = []
        c1 = sayfa_komutlari[i]
        c1_label = f".{c1}" if not c1.startswith("custom_") else f".{c1[7:]}"
        row.append(InlineKeyboardButton(c1_label, callback_data=f"cmd_{kategori_key}_{sayfa}_{c1}"))
        if i + 1 < len(sayfa_komutlari):
            c2 = sayfa_komutlari[i+1]
            c2_label = f".{c2}" if not c2.startswith("custom_") else f".{c2[7:]}"
            row.append(InlineKeyboardButton(c2_label, callback_data=f"cmd_{kategori_key}_{sayfa}_{c2}"))
        keyboard.append(row)

    nav_row = []
    if sayfa > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Önceki", callback_data=f"kat_{kategori_key}_{sayfa-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {sayfa}/{toplam_sayfa}", callback_data="yardim_noop"))
    if sayfa < toplam_sayfa:
        nav_row.append(InlineKeyboardButton("Sonraki ➡️", callback_data=f"kat_{kategori_key}_{sayfa+1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton("◀️ Ana Menü", callback_data="main_menu"),
        InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
    ])

    from core.locales import t
    metin = t("cat_header", category=kategori_adi.upper())
    return InlineKeyboardMarkup(keyboard), metin


async def handle_yardim_close(client, callback_query):
    """yardim_close callback'ini yönetir."""
    deleted = False
    userbot = utils.bot_client

    if callback_query.message:
        try:
            await callback_query.message.delete()
            deleted = True
        except Exception as _del_err:
            logger.debug("Yardım mesajı silinemedi: %s", _del_err)

    if deleted:
        try:
            await callback_query.answer("🗑️ Menü kapatıldı.", show_alert=False)
        except Exception as _ans_err:
            logger.debug("Callback answer hatası: %s", _ans_err)
        return

    try:
        await callback_query.edit_message_reply_markup(reply_markup=None)
    except Exception as _rm_err:
        logger.debug("Reply markup kaldırılamadı: %s", _rm_err)
    try:
        await callback_query.answer("Menü kapatıldı.", show_alert=False)
    except Exception as _ans_err:
        logger.debug("Callback answer hatası: %s", _ans_err)


async def handle_main_and_settings(client, callback_query, data):
    """main_menu, ayarlar_menu, btn_, toggle_ callback'lerini yönetir."""
    if data == "main_menu":
        metin = get_main_menu_text()
        keyboard = get_main_menu_keyboard()
        await safe_edit(callback_query, client, text=metin, reply_markup=keyboard)
        await callback_query.answer()
        return True

    if data == "ayarlar_menu":
        keyboard, metin = get_settings_keyboard()
        await safe_edit(callback_query, client, text=metin, reply_markup=keyboard)
        await callback_query.answer()
        return True

    if data == "btn_durum":
        keyboard, metin = get_detailed_status_content()
        await safe_edit(callback_query, client, text=metin, reply_markup=keyboard)
        await callback_query.answer()
        return True

    if data == "btn_restart":
        await callback_query.answer("🔄 Bot yeniden başlatılıyor...", show_alert=True)
        try:
            await callback_query.edit_message_text(
                "🔄 <b>Bot yeniden başlatılıyor...</b>\n"
                "<i>Lütfen birkaç saniye bekleyin, bot kısa süre içinde aktif olacaktır.</i>"
            )
        except Exception as _res_err:
            logger.debug("Restart mesajı düzenlenemedi: %s", _res_err)
        subprocess.Popen([sys.executable] + sys.argv)
        raise SystemExit(0)

    if data == "btn_update":
        await handle_btn_update(client, callback_query)
        return True

    if data == "toggle_sureli":
        mevcut = utils.ayar_getir("hayalet_durumu", False)
        utils.ayar_kaydet("hayalet_durumu", not mevcut)
        keyboard, metin = get_settings_keyboard()
        await safe_edit(callback_query, client, text=metin, reply_markup=keyboard)
        await callback_query.answer("Süreli modu değiştirildi.")
        return True

    if data == "toggle_antidelete":
        mevcut = utils.ayar_getir("antidelete_durumu", False)
        utils.ayar_kaydet("antidelete_durumu", not mevcut)
        keyboard, metin = get_settings_keyboard()
        await safe_edit(callback_query, client, text=metin, reply_markup=keyboard)
        await callback_query.answer("Anti-Delete modu değiştirildi.")
        return True

    if data == "toggle_lang":
        from core.locales import get_current_lang, set_current_lang
        cur = get_current_lang()
        yeni = "en" if cur == "tr" else "tr"
        set_current_lang(yeni)
        keyboard, metin = get_settings_keyboard()
        await safe_edit(callback_query, client, text=metin, reply_markup=keyboard)
        await callback_query.answer(f"Dil değiştirildi: {yeni.upper()}", show_alert=True)
        return True

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
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        return True

    return False


async def handle_btn_update(client, callback_query):
    """btn_update callback'ini yönetir."""
    await callback_query.answer()
    try:
        subprocess.run(["git", "config", "--global", "--add", "safe.directory", "*"], capture_output=True)
        repo_url = os.getenv("UPSTREAM_REPO", "https://github.com/chaolcam/gagaragogo-userbot.git")
        subprocess.run(["git", "remote", "set-url", "origin", repo_url], capture_output=True)

        eski_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "v2.6"
        fetch_res = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True)

        remote_commit = subprocess.run(["git", "rev-parse", "--short", "origin/main"], capture_output=True, text=True).stdout.strip() or eski_commit

        if eski_commit == remote_commit:
            metin = (
                "<b>GÜNCELLEME DENETİMİ</b>\n"
                "────────────────────────\n"
                "✅ <b>Tebrikler, botunuz en son sürümde!</b>\n\n"
                f"📌 <b>Mevcut Sürüm:</b> <code>{eski_commit} (Son Sürüm)</code>\n"
                f"📡 <b>GitHub:</b> <code>{remote_commit}</code>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tekrar Kontrol Et", callback_data="btn_update")],
                [
                    InlineKeyboardButton("◀️ Ayarlar", callback_data="ayarlar_menu"),
                    InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
                ],
            ])
            await callback_query.edit_message_text(text=metin, reply_markup=kb)
            return

        await callback_query.edit_message_text(
            f"🔄 <b>Yeni Güncelleme Bulundu!</b> (<code>{eski_commit}</code> ➔ <code>{remote_commit}</code>)\n"
            "Kodlar eşitleniyor ve bot yeniden başlatılıyor..."
        )
        subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--break-system-packages"], capture_output=True)
        subprocess.Popen([sys.executable] + sys.argv)
        raise SystemExit(0)
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Güncelleme hatası: {e}")


async def handle_sub_callbacks(client, callback_query, data):
    """sub_ arayüz geçişlerini yönetir."""
    if data == "sub_arac_hub":
        kb, metin = get_araclar_hub_content()
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True
    if data == "sub_arac_indir":
        kb, metin = get_araclar_indir_content()
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True
    if data == "sub_arac_donustur":
        kb, metin = get_araclar_donustur_content()
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True
    if data == "sub_arac_koruma":
        kb, metin = get_araclar_koruma_content()
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True
    if data == "sub_arac_cevir":
        kb, metin = get_araclar_cevir_content()
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True
    return False


async def handle_kat_and_cmd(client, callback_query, data):
    """kat_ ve cmd_ komut detaylarını yönetir."""
    if data.startswith("kat_"):
        parts = data.split("_")
        kategori_key = "_".join(parts[1:-1])
        sayfa = parts[-1]

        if kategori_key.lower() in ("araçlar", "araclar"):
            kb, metin = get_araclar_hub_content()
            await safe_edit(callback_query, client, text=metin, reply_markup=kb)
            await callback_query.answer()
            return True

        keyboard, metin = get_category_keyboard(kategori_key, sayfa)
        await safe_edit(callback_query, client, text=metin, reply_markup=keyboard)
        await callback_query.answer()
        return True

    if data.startswith("cmd_"):
        parts = data.split("_")
        kategori_key = parts[1]
        sayfa = parts[2]
        komut_adi = "_".join(parts[3:])

        detay = _find_komut_detay(kategori_key, komut_adi)
        if detay:
            metin = _build_komut_metin(komut_adi, detay)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Geri", callback_data=f"kat_{kategori_key}_{sayfa}")],
                [
                    InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
                    InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")
                ]
            ])
            await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    return False


def _find_komut_detay(kategori_key, komut_adi):
    for k, v in KOMUT_BILGILERI.items():
        if k.lower() == kategori_key.lower():
            komutlar = v.get("komutlar", {})
            if komut_adi in komutlar:
                return komutlar[komut_adi]
            if f"custom_{komut_adi}" in komutlar:
                return komutlar[f"custom_{komut_adi}"]
    return None


def _build_komut_metin(komut_adi, detay):
    from core.locales import t
    raw_desc = detay.get("aciklama", "Açıklama bulunamadı.")
    kullanim = detay.get("kullanim", f".{komut_adi}")
    clean_cmd = komut_adi.lower().replace("custom_", "")
    
    # Try localized command description from active locale JSON, fallback to registered info
    loc_key = f"cmd_{clean_cmd}_info"
    desc = t(loc_key)
    if desc == loc_key:
        desc = raw_desc

    title = t("cmd_info_title", command=clean_cmd)
    desc_label = t("cmd_desc", desc=desc)
    usage_label = t("cmd_usage", usage=kullanim)

    return f"{title}\n────────────────────────\n{desc_label}\n\n{usage_label}"
