# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Command Decorators & Dispatch Handlers
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import logging
from functools import wraps
from typing import Callable, Optional
from pyrogram import filters
from pyrogram.types import Message


def ggr_cmd(
    command: str,
    category: str = "genel",
    desc: str = "",
    usage: str = "",
    prefixes: str = "."
):
    """
    Hem Pyrogram filtrelerini bağlayan hem de komutu otomatik olarak
    merkezi yardım sistemine kaydeden modern komut dekoratörü.
    Manuel utils.komut_ekle yazma gereksinimini ortadan kaldırır.
    """
    import utils
    # Otomatik olarak merkezi yardım sistemine kaydet
    utils.komut_ekle(category, command, desc, usage or f"{prefixes}{command}")

    def decorator(func: Callable):
        cmd_filter = filters.command(command, prefixes=prefixes) & filters.me

        @wraps(func)
        async def wrapper(client, message: Message, *args, **kwargs):
            try:
                return await func(client, message, *args, **kwargs)
            except Exception as e:
                err_text = str(e)
                # Peer / FloodWait dışındaki kritik hataları log konusuna gönder
                if "PEER_ID_INVALID" not in err_text and "FloodWait" not in err_text:
                    await utils.tlog(f"⚠️ <b>KOMUT HATASI [.{command}]:</b>\n<code>{utils.guvenli_isim(err_text)}</code>")
                try:
                    await message.edit(f"❌ <b>Hata:</b> <code>{utils.guvenli_isim(err_text[:300])}</code>")
                except Exception as _m_err:
                    logging.debug("Hata mesajı iletilemedi: %s", _m_err)

        # Pyrogram Client.on_message decorator'ı ile doğrudan kullanılabilsin diye filtreyi iliştir
        wrapper.custom_filter = cmd_filter
        wrapper.cmd_name = command
        wrapper.cmd_category = category
        wrapper.cmd_desc = desc
        wrapper.cmd_usage = usage or f"{prefixes}{command}"
        return wrapper

    return decorator
