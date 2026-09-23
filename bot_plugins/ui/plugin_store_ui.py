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
    from core.locales import t
    keyboard = [
        [InlineKeyboardButton(t("btn_plugin_store"), callback_data="eklenti_magaza_1")],
        [
            InlineKeyboardButton(t("btn_my_plugins"), callback_data="eklenti_yuklu_1"),
            InlineKeyboardButton(t("btn_remove_plugin"), callback_data="eklenti_kaldir_1")
        ],
        [
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu"),
            InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")
        ]
    ]
    metin = t("plugin_store_header", channel=PLUGIN_STORE_CHANNEL)
    return InlineKeyboardMarkup(keyboard), metin


async def build_eklenti_magaza_keyboard(page=1):
    from plugins.plugin_manager import fetch_store_plugins, PLUGIN_STORE_CHANNEL
    userbot = utils.bot_client
    from core.locales import t
    if not userbot:
        return InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back"), callback_data="eklenti_ana_menu")]]), "❌ Userbot aktif değil."

    plugins = await fetch_store_plugins(userbot, limit=50)
    if not plugins:
        keyboard = [
            [InlineKeyboardButton(t("btn_refresh"), callback_data="eklenti_magaza_1")],
            [
                InlineKeyboardButton(f"◀️ {t('btn_plugin_store').replace('🛒 ', '')}", callback_data="eklenti_ana_menu"),
                InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
            ],
            [InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")]
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

    from core.locales import t
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(t("btn_prev"), callback_data=f"eklenti_magaza_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{toplam_sayfa}", callback_data="yardim_noop"))
    if page < toplam_sayfa:
        nav_row.append(InlineKeyboardButton(t("btn_next"), callback_data=f"eklenti_magaza_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(f"◀️ {t('btn_plugin_store').replace('🛒 ', '')}", callback_data="eklenti_ana_menu"),
        InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
    ])
    keyboard.append([InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")])

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
