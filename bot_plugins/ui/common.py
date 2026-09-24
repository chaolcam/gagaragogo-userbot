# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Common UI Utilities & Progress Builders
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import sys
import time
import logging
import subprocess
from pyrogram.enums import ParseMode

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
    except Exception as _exc:
        logging.debug("Suppressed: %s", _exc)

    if now - _LAST_GIT_FETCH_TIME > 30:
        try:
            subprocess.run(["git", "config", "--global", "--add", "safe.directory", "*"], capture_output=True)
            repo_url = os.getenv("UPSTREAM_REPO", "https://github.com/chaolcam/gagaragogo-userbot.git")
            subprocess.run(["git", "remote", "set-url", "origin", repo_url], capture_output=True)
            subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, timeout=10)
            _LAST_GIT_FETCH_TIME = now
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)

    try:
        r_res = subprocess.run(["git", "rev-parse", "--short", "origin/main"], capture_output=True, text=True)
        remote = r_res.stdout.strip()
        from core.locales import t
        if remote and remote != commit:
            return commit, t("status_update_avail")
        return commit, t("status_latest")
    except Exception:
        from core.locales import t
        return commit, t("status_latest")


def make_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Yüzdeye göre modern ilerleme çubuğu üretir."""
    if total <= 0:
        return "░" * length
    fraction = min(1.0, max(0.0, current / total))
    filled = int(round(fraction * length))
    return "█" * filled + "░" * (length - filled)


def format_sure(dakika):
    """Dakika değerini insan tarafından okunabilir süre formatına çevirir."""
    try:
        dakika = float(dakika)
        if dakika < 60:
            return f"{int(dakika) if dakika.is_integer() else dakika:.1f} Dk"
        saat = dakika / 60
        if saat < 24:
            return f"{int(saat) if saat.is_integer() else saat:.1f} Saat"
        gun = saat / 24
        return f"{int(gun) if gun.is_integer() else gun:.1f} Gün"
    except Exception:
        return f"{dakika} Dk"


async def safe_edit(callback_query, client, *args, **kwargs):
    """
    Hem normal bot mesajlarını hem de inline gönderilen mesajları
    MESSAGE_NOT_MODIFIED hatasına takılmadan güvenle düzenler.
    """
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = ParseMode.HTML

    try:
        if callback_query.inline_message_id:
            return await client.edit_inline_text(
                inline_message_id=callback_query.inline_message_id,
                *args, **kwargs
            )
        elif callback_query.message:
            return await callback_query.message.edit_text(*args, **kwargs)
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            logging.warning("safe_edit uyarısı: %s", e)
