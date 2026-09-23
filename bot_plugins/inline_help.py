# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Interactive Botfather Helper & Inline Router
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import logging
from pyrogram import Client, filters
from pyrogram.types import (
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
import utils
from bot_plugins.ui import (
    get_main_menu_text,
    get_main_menu_keyboard,
    get_settings_keyboard,
    handle_yardim_close,
    handle_main_and_settings,
    handle_sub_callbacks,
    handle_kat_and_cmd,
    handle_ilet_callbacks,
    handle_otomsg_callbacks,
    handle_rehber_callbacks,
    handle_eklenti_callbacks,
    handle_ig_callbacks,
    build_ilet_menu_keyboard,
    build_rehber_menu_main,
    build_otomesaj_list_keyboard,
)

logger = logging.getLogger("ggr.inline_ui")


# =============================================================================
# INLINE QUERY HANDLERS
# =============================================================================

@Client.on_inline_query(filters.regex("^(alive|yardim|ayarlar)"))
async def inline_yardim(client, inline_query):
    """Kullanıcı @YardimciBot yardim yazdığında açılan ana kontrol paneli."""
    owner_id = utils.get_owner_id()
    if owner_id and inline_query.from_user.id != owner_id:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    query = inline_query.query.strip().lower()
    alive_logo = utils.get_alive_logo()

    if query == "ayarlar":
        keyboard, metin = get_settings_keyboard()
        title = "GagaraGogo Kontrol Paneli & Ayarlar"
        description = "Sistem ayarlarını, logları ve özellikleri yönetin."
    else:
        metin = get_main_menu_text()
        keyboard = get_main_menu_keyboard()
        title = "GagaraGogo İnteraktif Yardım Menüsü"
        description = "Tüm komutları ve durum raporunu görsel butonlarla keşfedin."

    if alive_logo:
        results = [
            InlineQueryResultPhoto(
                photo_url=alive_logo,
                title=title,
                description=description,
                caption=metin,
                reply_markup=keyboard,
            )
        ]
    else:
        results = [
            InlineQueryResultArticle(
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(metin),
                reply_markup=keyboard,
            )
        ]

    await inline_query.answer(results, cache_time=1, is_personal=True)


@Client.on_inline_query(filters.regex(r"^ig\s+(.+)"))
async def inline_ig(client, inline_query):
    """Instagram profili için inline query arayüzü."""
    owner_id = utils.get_owner_id()
    if owner_id and inline_query.from_user.id != owner_id:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    username = inline_query.matches[0].group(1).strip().lstrip("@")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Hikayeler", callback_data=f"ig_story_{username}_0")],
        [InlineKeyboardButton("🖼 Gönderiler", callback_data=f"ig_post_{username}_0")],
        [InlineKeyboardButton("⭐ Öne Çıkanlar", callback_data=f"ig_high_{username}_0")],
    ])
    metin = (
        f"<b>Instagram:</b> <code>@{username}</code>\n"
        "────────────────────────\n"
        "Görüntülemek istediğiniz medya türünü seçin:"
    )
    results = [
        InlineQueryResultArticle(
            title=f"Instagram: @{username}",
            description="Hikaye, gönderi veya öne çıkanları keşfet",
            input_message_content=InputTextMessageContent(metin),
            reply_markup=keyboard,
        )
    ]
    await inline_query.answer(results, cache_time=1, is_personal=True)


@Client.on_inline_query(filters.regex(r"^(otomesaj|otomsg)"))
async def inline_otomesaj(client, inline_query):
    owner_id = utils.get_owner_id()
    if owner_id and inline_query.from_user.id != owner_id:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    keyboard, metin = await build_otomesaj_list_keyboard()
    results = [
        InlineQueryResultArticle(
            title="Otomatik Mesaj Yönetim Paneli",
            description="Zamanlanmış mesaj görevlerini görüntüle ve yönet",
            input_message_content=InputTextMessageContent(metin),
            reply_markup=keyboard,
        )
    ]
    await inline_query.answer(results, cache_time=1, is_personal=True)


@Client.on_inline_query(filters.regex(r"^ilet"))
async def inline_ilet(client, inline_query):
    owner_id = utils.get_owner_id()
    if owner_id and inline_query.from_user.id != owner_id:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    keyboard, metin = await build_ilet_menu_keyboard(page=1)
    results = [
        InlineQueryResultArticle(
            title="Toplu İletim Grup Listesi (.iletmenu)",
            description="Mesaj iletilecek grupları açıp kapatın",
            input_message_content=InputTextMessageContent(metin),
            reply_markup=keyboard,
        )
    ]
    await inline_query.answer(results, cache_time=1, is_personal=True)


@Client.on_inline_query(filters.regex(r"^(rehber|rehbermenu)"))
async def inline_rehber_menu(client, inline_query):
    owner_id = utils.get_owner_id()
    if owner_id and inline_query.from_user.id != owner_id:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    userbot = utils.bot_client
    keyboard, metin = await build_rehber_menu_main(userbot)
    results = [
        InlineQueryResultArticle(
            title="Rehber & Grup Yönetim Merkezi",
            description="Gruplardan üye aktarımı ve rehber senkronizasyonu",
            input_message_content=InputTextMessageContent(metin),
            reply_markup=keyboard,
        )
    ]
    await inline_query.answer(results, cache_time=1, is_personal=True)


# =============================================================================
# CALLBACK QUERY ROUTER (DISPATCHER)
# =============================================================================

async def _route_yardim_callback(client, callback_query, data):
    """Gelen callback_data'yı ilgili alt UI modülüne yönlendirir."""
    if data == "yardim_noop":
        await callback_query.answer()
        return True

    if data == "yardim_close":
        await handle_yardim_close(client, callback_query)
        return True

    if data.startswith("ilet_") or data == "open_ilet_groups":
        return await handle_ilet_callbacks(client, callback_query, data)

    if data.startswith("otomsg_"):
        return await handle_otomsg_callbacks(client, callback_query, data)

    if data in (
        "main_menu", "ayarlar_menu", "btn_durum", "btn_restart", "btn_update",
        "toggle_sureli", "toggle_antidelete", "toggle_lang",
        "toggle_sureli_from_koruma", "toggle_antidelete_from_koruma"
    ):
        return await handle_main_and_settings(client, callback_query, data)

    if data.startswith("eklenti_"):
        return await handle_eklenti_callbacks(client, callback_query, data)

    if data.startswith("sub_"):
        return await handle_sub_callbacks(client, callback_query, data)

    if data.startswith(("kat_", "cmd_")):
        return await handle_kat_and_cmd(client, callback_query, data)

    if data.startswith(("rm_", "rehber_")):
        return await handle_rehber_callbacks(client, callback_query, data)

    if data.startswith("ig_"):
        return await handle_ig_callbacks(client, callback_query, data)

    return False


@Client.on_callback_query()
async def yardim_callback(client, callback_query):
    owner_id = utils.get_owner_id()
    if owner_id and callback_query.from_user and callback_query.from_user.id != owner_id:
        await callback_query.answer("⛔ Bu butonlar sadece bot sahibine aittir!", show_alert=True)
        return

    data = callback_query.data
    logger.debug("[INLINE_UI] Butona tıklandı: %s", data)

    try:
        routed = await _route_yardim_callback(client, callback_query, data)
        if not routed:
            await callback_query.answer()
    except Exception as err:
        logger.error("[INLINE_UI] Hata (Veri: %s): %s", data, err)
        try:
            await callback_query.answer(f"Hata: {type(err).__name__}", show_alert=True)
        except Exception as _cb_err:
            logger.debug("Callback answer hatası: %s", _cb_err)
