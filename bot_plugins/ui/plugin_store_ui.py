# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Plugin Store & Manager UI
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import utils
from bot_plugins.ui.common import safe_edit


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
        return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data="eklenti_ana_menu")]]), "❌ Userbot aktif değil."

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
            "ℹ️ Şu anda mağazada yayınlanmış eklenti bulunamadı."
        )
        return InlineKeyboardMarkup(keyboard), metin

    per_page = 5
    toplam_sayfa = max(1, (len(plugins) + per_page - 1) // per_page)
    page = max(1, min(page, toplam_sayfa))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sayfa_items = plugins[start_idx:end_idx]

    keyboard = []
    for item in sayfa_items:
        baslik = item["baslik"].strip()
        msg_id = item["id"]
        keyboard.append([InlineKeyboardButton(f"📦 {baslik[:28]}", callback_data=f"eklenti_detay_{msg_id}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Geri", callback_data=f"eklenti_magaza_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{toplam_sayfa}", callback_data="yardim_noop"))
    if page < toplam_sayfa:
        nav_row.append(InlineKeyboardButton("İleri ▶️", callback_data=f"eklenti_magaza_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton("◀️ Eklenti Menüsü", callback_data="eklenti_ana_menu"),
        InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")
    ])
    keyboard.append([InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")])

    metin = (
        f"🛒 <b>EKLENTİ MAĞAZASI</b> ⬝ <code>@{PLUGIN_STORE_CHANNEL}</code>\n"
        "────────────────────────\n"
        "Kurmak istediğiniz eklentinin üzerine dokunun:"
    )
    return InlineKeyboardMarkup(keyboard), metin


async def handle_eklenti_callbacks(client, callback_query, data):
    if data == "eklenti_ana_menu":
        kb, metin = await build_eklenti_ana_menu_keyboard()
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data.startswith("eklenti_magaza_"):
        page = int(data.split("_")[2])
        kb, metin = await build_eklenti_magaza_keyboard(page)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    return False
