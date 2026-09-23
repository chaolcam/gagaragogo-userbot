# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Network Resiliency & FloodWait Handler
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import asyncio
import logging
from typing import Any, Callable, Coroutine
from pyrogram.errors import FloodWait, SlowmodeWait

logger = logging.getLogger("ggr.network")


async def safe_api_call(
    coro_func: Callable[[], Coroutine[Any, Any, Any]],
    max_retries: int = 3,
    max_wait_seconds: int = 60,
    action_name: str = "Telegram API Çağrısı"
) -> Any:
    """
    FloodWait veya SlowmodeWait ile karşılaşıldığında işlemi çökertmek yerine
    belirtilen süre kadar güvenli şekilde asenkron bekler ve tekrar dener.
    Eğer bekleme süresi max_wait_seconds'tan büyükse hesabı korumak için hata fırlatır.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_func()
        except FloodWait as e:
            wait_time = int(e.value) + 1
            logger.warning(
                "⏳ [FloodWait] %s için %d saniye bekleme istendi. (Deneme: %d/%d)",
                action_name, wait_time, attempt, max_retries
            )
            if wait_time > max_wait_seconds:
                logger.error(
                    "❌ [FloodWait Sınırı Aşıldı] Bekleme süresi (%ds) belirlenen güvenlik sınırını (%ds) aşıyor!",
                    wait_time, max_wait_seconds
                )
                raise e
            await asyncio.sleep(wait_time)
        except SlowmodeWait as e:
            wait_time = int(e.value) + 1
            logger.warning("⏳ [SlowmodeWait] %s için %d saniye bekleniyor...", action_name, wait_time)
            await asyncio.sleep(wait_time)
        except Exception as e:
            # Diğer hatalarda son deneme değilse kısa bir gecikmeyle tekrar dene (ağ kopmaları vb.)
            if "Connection" in str(e) or "Timeout" in str(e):
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
            raise e
    return None
