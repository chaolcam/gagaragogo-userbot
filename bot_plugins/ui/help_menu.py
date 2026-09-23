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

    from core.locales import t
    owner_name = t("alive_user", user="Userbot").replace("<b>Kullanıcı:</b> ", "").replace("<b>User:</b> ", "")
    if utils.bot_client and hasattr(utils.bot_client, "me") and utils.bot_client.me:
        owner_name = utils.bot_client.me.first_name or owner_name

    metin = (
        f"{t('menu_alive_header')}\n"
        "────────────────────────\n"
        f"{t('menu_alive_owner', owner=owner_name)}\n"
        f"{t('menu_alive_status', commit=commit, version_info=durum_surum)}\n"
        f"{t('menu_alive_uptime', uptime=uptime_str)}\n"
        "────────────────────────\n"
        f"🖥 <b>CPU:</b> <code>{cpu_bar} %{cpu}</code>\n"
        f"🧠 <b>RAM:</b> <code>{ram_bar} %{ram_percent} ({ram_str})</code>\n"
        "────────────────────────\n"
        f"{t('menu_alive_select_cat')}"
    )
    return metin


def get_main_menu_keyboard():
    """Yardım menüsü için dengeli 2 sütunlu interaktif kategori klavyesi oluşturur."""
    from core.locales import t
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

    def get_kat_label(k_key, fallback_name):
        map_keys = {
            "admin": "cat_admin",
            "araçlar": "cat_tools",
            "araclar": "cat_tools",
            "sistem": "cat_system",
            "medya": "cat_media",
            "eğlence": "cat_fun",
            "eglence": "cat_fun",
            "grup & iletim": "cat_broadcast"
        }
        loc_k = map_keys.get(k_key.lower())
        return t(loc_k) if loc_k else fallback_name

    num_kat = len(kategoriler)
    if num_kat % 2 == 1:
        for i in range(0, num_kat - 1, 2):
            k1, k2 = kategoriler[i], kategoriler[i+1]
            l1 = get_kat_label(k1, KOMUT_BILGILERI[k1]['isim'])
            l2 = get_kat_label(k2, KOMUT_BILGILERI[k2]['isim'])
            keyboard.append([
                InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[k1]['isim'])} {l1}", callback_data=f"kat_{k1}_1"),
                InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[k2]['isim'])} {l2}", callback_data=f"kat_{k2}_1")
            ])
        son_kat = kategoriler[-1]
        l_son = get_kat_label(son_kat, KOMUT_BILGILERI[son_kat]['isim'])
        keyboard.append([
            InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[son_kat]['isim'])} {l_son}", callback_data=f"kat_{son_kat}_1"),
            InlineKeyboardButton(t("btn_plugins"), callback_data="eklenti_ana_menu")
        ])
        keyboard.append([InlineKeyboardButton(t("btn_control_panel"), callback_data="ayarlar_menu")])
    else:
        for i in range(0, num_kat, 2):
            k1, k2 = kategoriler[i], kategoriler[i+1]
            l1 = get_kat_label(k1, KOMUT_BILGILERI[k1]['isim'])
            l2 = get_kat_label(k2, KOMUT_BILGILERI[k2]['isim'])
            keyboard.append([
                InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[k1]['isim'])} {l1}", callback_data=f"kat_{k1}_1"),
                InlineKeyboardButton(f"{get_icon(KOMUT_BILGILERI[k2]['isim'])} {l2}", callback_data=f"kat_{k2}_1")
            ])
        keyboard.append([
            InlineKeyboardButton("🔌 Eklentiler", callback_data="eklenti_ana_menu"),
            InlineKeyboardButton("⚙️ Ayarlar", callback_data="ayarlar_menu")
        ])

    keyboard.append([InlineKeyboardButton("❌ Menüyü Kapat", callback_data="yardim_close")])
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard():
    """Botun özelliklerini açıp kapatmaya ve sistem komutlarını yönetmeye yarayan kontrol paneli."""
    from core.locales import t
    hayalet = utils.ayar_getir("hayalet_durumu", False)
    antidelete = utils.ayar_getir("antidelete_durumu", False)

    hayalet_btn = t("status_on") if hayalet else t("status_off")
    antidelete_btn = t("status_on") if antidelete else t("status_off")

    keyboard = [
        [InlineKeyboardButton(t("btn_sureli_label", status=hayalet_btn), callback_data="toggle_sureli")],
        [InlineKeyboardButton(t("btn_antidelete_label", status=antidelete_btn), callback_data="toggle_antidelete")],
        [
            InlineKeyboardButton(t("btn_update_label"), callback_data="btn_update"),
            InlineKeyboardButton(t("btn_restart_label"), callback_data="btn_restart")
        ],
        [InlineKeyboardButton(t("btn_hardware_status"), callback_data="btn_durum")],
        [InlineKeyboardButton(t("btn_switch_language"), callback_data="toggle_lang")],
        [
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu"),
            InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")
        ]
    ]

    yedek_id = utils.get_yedek_grup_id()
    log_konu = utils.ayar_getir("log_topic_id", "Auto")

    metin = t(
        "settings_panel_header",
        backup_chat=yedek_id,
        log_topic=log_konu
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

    from core.locales import t
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_refresh"), callback_data="btn_durum")],
        [
            InlineKeyboardButton(f"◀️ {t('cat_settings')}", callback_data="ayarlar_menu"),
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
        ],
        [InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")]
    ])
    return keyboard, metin


def get_araclar_hub_content():
    from core.locales import t
    keyboard = [
        [
            InlineKeyboardButton(t("btn_sub_downloaders"), callback_data="sub_arac_indir"),
            InlineKeyboardButton(t("btn_sub_converters"), callback_data="sub_arac_donustur")
        ],
        [
            InlineKeyboardButton(t("btn_sub_protection"), callback_data="sub_arac_koruma"),
            InlineKeyboardButton(t("btn_sub_translate_bypass"), callback_data="sub_arac_cevir")
        ],
        [
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu"),
            InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")
        ]
    ]
    metin = t("tools_hub_header")
    return InlineKeyboardMarkup(keyboard), metin


def get_araclar_indir_content():
    from core.locales import t
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
            InlineKeyboardButton(t("btn_back"), callback_data="sub_arac_hub"),
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
        ],
        [InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")]
    ]
    metin = t("tools_indir_header")
    return InlineKeyboardMarkup(keyboard), metin


def get_araclar_donustur_content():
    from core.locales import t
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
            InlineKeyboardButton(t("btn_back"), callback_data="sub_arac_hub"),
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
        ],
        [InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")]
    ]
    metin = t("tools_donustur_header")
    return InlineKeyboardMarkup(keyboard), metin


def get_araclar_koruma_content():
    from core.locales import t
    hayalet = utils.ayar_getir("hayalet_durumu", False)
    antidelete = utils.ayar_getir("antidelete_durumu", False)
    hayalet_btn = t("status_on") if hayalet else t("status_off")
    antidelete_btn = t("status_on") if antidelete else t("status_off")

    keyboard = [
        [InlineKeyboardButton(t("btn_sureli_label", status=hayalet_btn), callback_data="toggle_sureli_from_koruma")],
        [InlineKeyboardButton(t("btn_antidelete_label", status=antidelete_btn), callback_data="toggle_antidelete_from_koruma")],
        [
            InlineKeyboardButton(".antidelete", callback_data="csub:Araçlar:sub_arac_koruma:antidelete"),
            InlineKeyboardButton(".sureli", callback_data="csub:Araçlar:sub_arac_koruma:sureli")
        ],
        [
            InlineKeyboardButton(t("btn_back"), callback_data="sub_arac_hub"),
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
        ],
        [InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")]
    ]
    metin = t("tools_koruma_header", sureli=hayalet_btn, antidelete=antidelete_btn)
    return InlineKeyboardMarkup(keyboard), metin


def get_araclar_cevir_content():
    from core.locales import t
    keyboard = [
        [
            InlineKeyboardButton(".cevir", callback_data="csub:Araçlar:sub_arac_cevir:cevir"),
            InlineKeyboardButton(".dil", callback_data="csub:Araçlar:sub_arac_cevir:dil")
        ],
        [InlineKeyboardButton(".bypass", callback_data="csub:Araçlar:sub_arac_cevir:bypass")],
        [
            InlineKeyboardButton(t("btn_back"), callback_data="sub_arac_hub"),
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
        ],
        [InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")]
    ]
    metin = t("tools_cevir_header")
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

    from core.locales import t
    nav_row = []
    if sayfa > 1:
        nav_row.append(InlineKeyboardButton(t("btn_prev"), callback_data=f"kat_{kategori_key}_{sayfa-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {sayfa}/{toplam_sayfa}", callback_data="yardim_noop"))
    if sayfa < toplam_sayfa:
        nav_row.append(InlineKeyboardButton(t("btn_next"), callback_data=f"kat_{kategori_key}_{sayfa+1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(t("btn_home"), callback_data="main_menu"),
        InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")
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
        
        utils.restart_bildirimi_kaydet(
            action="restart",
            inline_message_id=callback_query.inline_message_id,
            chat_id=callback_query.message.chat.id if callback_query.message else None,
            message_id=callback_query.message.id if callback_query.message else None
        )
        try:
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception:
            subprocess.Popen([sys.executable] + sys.argv)
            raise SystemExit(0)
        return True

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
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--break-system-packages"], capture_output=True, timeout=30)
        except Exception as _pip_err:
            logger.debug("Pip install uyarısı: %s", _pip_err)

        yeni_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or remote_commit

        utils.restart_bildirimi_kaydet(
            action="update",
            inline_message_id=callback_query.inline_message_id,
            chat_id=callback_query.message.chat.id if callback_query.message else None,
            message_id=callback_query.message.id if callback_query.message else None,
            eski_commit=eski_commit,
            yeni_commit=yeni_commit
        )

        try:
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception:
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

    from core.locales import t

    if data.startswith("csub:"):
        # Format: csub:<kategori>:<return_sub>:<komut_adi>
        parts = data.split(":", 3)
        if len(parts) == 4:
            _, kat, return_sub, cmd = parts
            detay = _find_komut_detay(kat, cmd)
            if detay:
                metin = _build_komut_metin(cmd, detay)
            else:
                clean_cmd = cmd.lower().replace("custom_", "")
                metin = _build_komut_metin(cmd, {"aciklama": t(f"cmd_{clean_cmd}_info"), "kullanim": f".{clean_cmd}"})
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(t("btn_back"), callback_data=return_sub)],
                [
                    InlineKeyboardButton(t("btn_home"), callback_data="main_menu"),
                    InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")
                ]
            ])
            await safe_edit(callback_query, client, text=metin, reply_markup=kb)
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
        else:
            clean_cmd = komut_adi.lower().replace("custom_", "")
            metin = _build_komut_metin(komut_adi, {"aciklama": t(f"cmd_{clean_cmd}_info"), "kullanim": f".{clean_cmd}"})

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_back"), callback_data=f"kat_{kategori_key}_{sayfa}")],
            [
                InlineKeyboardButton(t("btn_home"), callback_data="main_menu"),
                InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")
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
    
    # Try localized command description and usage from active locale JSON
    loc_key = f"cmd_{clean_cmd}_info"
    desc = t(loc_key)
    if desc == loc_key:
        desc = raw_desc

    usage_key = f"cmd_{clean_cmd}_usage"
    usage_val = t(usage_key)
    if usage_val == usage_key:
        usage_val = kullanim

    title = t("cmd_info_title", command=clean_cmd)
    desc_label = t("cmd_desc", desc=desc)
    usage_label = t("cmd_usage", usage=usage_val)

    return f"{title}\n────────────────────────\n{desc_label}\n\n{usage_label}"
