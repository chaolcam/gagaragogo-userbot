# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Instagram Interactive Media UI
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import uuid
import asyncio
import logging
import requests
import json
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import utils

logger = logging.getLogger(__name__)


async def handle_ig_callbacks(client, callback_query, data):
    """ig_ callback'lerini yönetir."""
    if data.startswith("ig_menu_"):
        username = data.split("_")[2]
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
        await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
        return True

    if data.startswith("ig_"):
        await _handle_ig_media(client, callback_query, data)
        return True

    return False


async def _handle_ig_media(client, callback_query, data):
    try:
        from plugins.instagram import fetch_instagram_data, get_rapidapi_keys_list
    except ImportError:
        from plugins.tools import fetch_instagram_data, get_rapidapi_keys_list

    if not get_rapidapi_keys_list():
        await callback_query.answer(
            "⚠️ RapidAPI anahtarınız yok! Lütfen sohbette .rapidapi [anahtar] yazarak anahtarınızı ekleyin.",
            show_alert=True,
        )
        return

    parts = data.split("_")
    action = parts[1]
    username = parts[2]
    index = int(parts[3])

    await callback_query.answer("Veriler çekiliyor, lütfen bekleyin...", show_alert=False)

    endpoint_map = {"story": "stories", "post": "posts", "high": "highlights"}
    if action == "dl":
        dl_type = parts[4]
        endpoint = endpoint_map.get(dl_type, "stories")
    elif action in endpoint_map:
        endpoint = endpoint_map[action]
    else:
        return

    try:
        resp = await asyncio.to_thread(fetch_instagram_data, endpoint, username)
        items = resp.get("result", {}).get("edges", []) if endpoint == "posts" else resp.get("result", [])

        if not items:
            await callback_query.edit_message_text(f"❌ `@{username}` için içerik bulunamadı.")
            return

        if index < 0:
            index = len(items) - 1
        if index >= len(items):
            index = 0

        item = items[index]
        media_url = _extract_ig_media_url(endpoint, item)

        if action == "dl" and media_url:
            await _ig_download_to_archive(client, callback_query, username, media_url, index, action)
            return

        if not media_url:
            media_url = "Medya bulunamadı"

        metin = (
            f"<b>Instagram:</b> <code>@{username}</code> ⬝ <b>{endpoint.capitalize()}</b>\n"
            "────────────────────────\n"
            f"Medya {index + 1} / {len(items)}\n\n"
            f'<a href="{media_url}">Medyayı Görüntüle</a>'
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("◀️ Önceki", callback_data=f"ig_{action}_{username}_{index - 1}"),
                InlineKeyboardButton("Sonraki ▶️", callback_data=f"ig_{action}_{username}_{index + 1}"),
            ],
            [InlineKeyboardButton("📥 Arşive İndir", callback_data=f"ig_dl_{username}_{index}_{action}")],
            [InlineKeyboardButton("◀️ Menü", callback_data=f"ig_menu_{username}")],
        ])
        await callback_query.edit_message_text(text=metin, reply_markup=keyboard)
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Instagram verisi alınamadı: {e}")


def _extract_ig_media_url(endpoint, item):
    if endpoint == "posts":
        node = item.get("node", {})
        if node.get("is_video"):
            return node.get("video_url")
        display_res = node.get("display_resources", [])
        return display_res[-1]["src"] if display_res else node.get("display_url")

    video_versions = item.get("video_versions", [])
    if video_versions:
        return video_versions[0]["url"]
    candidates = item.get("image_versions2", {}).get("candidates", [])
    return candidates[0]["url"] if candidates else None


async def _ig_download_to_archive(client, callback_query, username, media_url, index, action):
    await callback_query.answer("İndiriliyor, lütfen bekleyin...", show_alert=False)
    dl_path = None
    try:
        from utils import get_yedek_grup_id, create_forum_topic_helper, bot_client as userbot

        hedef_chat = get_yedek_grup_id()
        if not hedef_chat:
            await client.send_message(callback_query.message.chat.id, "Yedek grup ayarlanmamış!")
            return

        ig_db_file = "ig_topics.json"
        ig_topics = {}
        if os.path.exists(ig_db_file):
            try:
                with open(ig_db_file, "r", encoding="utf-8") as file_handle:
                    ig_topics = json.load(file_handle)
            except Exception as _ig_read_err:
                logger.debug("ig_topics.json okunamadı: %s", _ig_read_err)

        topic_id = ig_topics.get(username)
        if not topic_id:
            topic_id = await create_forum_topic_helper(userbot, hedef_chat, f"IG: {username}")
            if topic_id:
                ig_topics[username] = topic_id
                with open(ig_db_file, "w", encoding="utf-8") as file_handle:
                    json.dump(ig_topics, file_handle, ensure_ascii=False, indent=4)

        ext = "mp4" if ("mp4" in media_url or "video" in media_url) else "jpg"
        dl_path = f"downloads/ig_dl_{uuid.uuid4().hex[:6]}.{ext}"
        os.makedirs("downloads", exist_ok=True)
        res = requests.get(media_url, timeout=15).content
        with open(dl_path, "wb") as file_handle:
            file_handle.write(res)

        try:
            if ext == "mp4":
                await userbot.send_video(chat_id=hedef_chat, video=dl_path, caption=f"@{username} medyası", reply_to_message_id=topic_id)
            else:
                await userbot.send_photo(chat_id=hedef_chat, photo=dl_path, caption=f"@{username} medyası", reply_to_message_id=topic_id)
        except Exception as send_err:
            await userbot.send_message(chat_id=hedef_chat, text=f"Medya yüklenirken hata oluştu: {send_err}", reply_to_message_id=topic_id)

        if dl_path and os.path.exists(dl_path):
            os.remove(dl_path)
        await callback_query.answer("Medya arşive (IG Konusuna) başarıyla gönderildi!", show_alert=True)
    except Exception as arch_err:
        if dl_path and os.path.exists(dl_path):
            try:
                os.remove(dl_path)
            except Exception as _del_err:
                logger.debug("dl_path silinemedi: %s", _del_err)
        await callback_query.answer(f"Arşive yükleme hatası: {arch_err}", show_alert=True)
