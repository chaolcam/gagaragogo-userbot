# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Entity & Data Cache Subsystem
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import time
import logging
from typing import Any, Optional, Dict
from cachetools import TTLCache

# Kullanıcılar için 2 saatlik önbellek (Maksimum 2000 varlık)
USER_CACHE = TTLCache(maxsize=2000, ttl=7200)

# Gruplar/Kanallar için 4 saatlik önbellek (Maksimum 500 sohbet)
CHAT_CACHE = TTLCache(maxsize=500, ttl=14400)

# Admin yetkileri için 30 dakikalık önbellek
ADMIN_PERM_CACHE = TTLCache(maxsize=1000, ttl=1800)


class EntityCache:
    """
    Telegram MTProto isteklerini (get_chat, get_users vb.) bellekte tutarak
    tekrarlanan ağ çağrılarını önler, botu hızlandırır ve FloodWait riskini düşürür.
    """

    @staticmethod
    def get_user(user_id_or_username: Any) -> Optional[Any]:
        key = str(user_id_or_username).lower().lstrip("@")
        return USER_CACHE.get(key)

    @staticmethod
    def set_user(user_id_or_username: Any, user_obj: Any) -> None:
        if not user_obj:
            return
        # Hem ID hem de username üzerinden erişilebilsin diye iki anahtarla kaydet
        if hasattr(user_obj, "id"):
            USER_CACHE[str(user_obj.id)] = user_obj
        if getattr(user_obj, "username", None):
            USER_CACHE[str(user_obj.username).lower()] = user_obj
        key = str(user_id_or_username).lower().lstrip("@")
        USER_CACHE[key] = user_obj

    @staticmethod
    def get_chat(chat_id_or_username: Any) -> Optional[Any]:
        key = str(chat_id_or_username).lower().lstrip("@")
        return CHAT_CACHE.get(key)

    @staticmethod
    def set_chat(chat_id_or_username: Any, chat_obj: Any) -> None:
        if not chat_obj:
            return
        if hasattr(chat_obj, "id"):
            CHAT_CACHE[str(chat_obj.id)] = chat_obj
        if getattr(chat_obj, "username", None):
            CHAT_CACHE[str(chat_obj.username).lower()] = chat_obj
        key = str(chat_id_or_username).lower().lstrip("@")
        CHAT_CACHE[key] = chat_obj

    @staticmethod
    def get_admin_status(chat_id: Any, user_id: Any) -> Optional[bool]:
        key = f"{chat_id}:{user_id}"
        return ADMIN_PERM_CACHE.get(key)

    @staticmethod
    def set_admin_status(chat_id: Any, user_id: Any, is_admin: bool) -> None:
        key = f"{chat_id}:{user_id}"
        ADMIN_PERM_CACHE[key] = is_admin

    @staticmethod
    def clear() -> None:
        USER_CACHE.clear()
        CHAT_CACHE.clear()
        ADMIN_PERM_CACHE.clear()


async def cached_get_chat(client, chat_id_or_username):
    """Önce EntityCache'e bakar, yoksa Telegram'dan çekip önbelleğe alır."""
    cached = EntityCache.get_chat(chat_id_or_username)
    if cached:
        return cached
    chat = await client.get_chat(chat_id_or_username)
    EntityCache.set_chat(chat_id_or_username, chat)
    return chat


async def cached_get_users(client, user_ids):
    """Tekli kullanıcılar için EntityCache kontrolü yapar."""
    if isinstance(user_ids, (int, str)):
        cached = EntityCache.get_user(user_ids)
        if cached:
            return cached
        user = await client.get_users(user_ids)
        EntityCache.set_user(user_ids, user)
        return user
    # Liste halinde gelirse doğrudan client çağrısı
    return await client.get_users(user_ids)
