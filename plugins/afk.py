# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Away From Keyboard (AFK) System (plugins/afk.py)
# Description: Automatically manages AFK status, auto-replies to mentions and PMs,
#              records ping notifications, and persists state in Telegram Cloud DB.
# -----------------------------------------------------------------------------

import time
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from utils import ggr

# Canlı hafızadaki AFK durumu
AFK_STATE = {
    "is_afk": False,
    "reason": "Şu an meşgulüm / AFK'yım.",
    "start_time": 0,
    "pings": []
}

# Spam engelleme: Kullanıcı başına son cevap zamanı
AFK_COOLDOWN = {}

def format_afk_duration(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours > 0: parts.append(f"{hours} saat")
    if minutes > 0: parts.append(f"{minutes} dakika")
    parts.append(f"{secs} saniye")
    return " ".join(parts)

# Sunucu açıldığında bulut veritabanından mevcut AFK durumunu geri yükle
kayitli_afk = ggr.get("afk_durumu")
if isinstance(kayitli_afk, dict) and kayitli_afk.get("is_afk"):
    AFK_STATE.update(kayitli_afk)
    logging.info(f"💤 AFK durumu bulut veritabanından yüklendi (Sebep: {AFK_STATE['reason']})")


@ggr.cmd("afk", info="AFK (Uzakta/Meşgul) modunu açar.", usage=".afk [sebep]", category="Araçlar")
async def afk_modunu_ac(client, message):
    reason = "Şu an meşgulüm / AFK'yım."
    if len(message.command) > 1:
        reason = message.text.split(maxsplit=1)[1].strip()
    
    simdi = time.time()
    AFK_STATE["is_afk"] = True
    AFK_STATE["reason"] = reason
    AFK_STATE["start_time"] = simdi
    AFK_STATE["pings"] = []
    
    ggr.set("afk_durumu", {
        "is_afk": True,
        "reason": reason,
        "start_time": simdi,
        "pings": []
    })
    await ggr.sync_cloud(client)
    
    await message.edit_text(
        f"💤 <b>AFK Modu Aktif Edildi!</b>\n\n"
        f"📝 <b>Sebep:</b> <i>{ggr.safe_html(reason)}</i>\n\n"
        f"⏱️ <i>Geri dönene kadar özel mesaj atanlara veya sizi etiketleyenlere otomatik bilgi verilecek ve bildirimler kaydedilecek.</i>"
    )


# Gelen etiket veya özel mesajları yanıtlama handler'ı
@Client.on_message(~filters.me & (filters.private | filters.mentioned), group=25)
async def afk_yanitlayici(client, message):
    if not AFK_STATE.get("is_afk"):
        return
        
    sender = message.from_user
    if not sender or sender.is_bot:
        return
        
    user_id = sender.id
    now = time.time()
    
    # 45 saniyede bir aynı kişiye cevap ver (flood önleme)
    last_replied = AFK_COOLDOWN.get(user_id, 0)
    
    # Bildirimi pings listesine ekle
    chat_adi = message.chat.title if message.chat.type != ChatType.PRIVATE else "Özel Sohbet"
    mesaj_ozet = (message.text or message.caption or "[Medya/Çıkartma]")[:80]
    
    AFK_STATE["pings"].append({
        "name": sender.first_name,
        "user_id": user_id,
        "chat": chat_adi,
        "text": mesaj_ozet,
        "time": now
    })
    
    if now - last_replied >= 45:
        AFK_COOLDOWN[user_id] = now
        elapsed = format_afk_duration(now - AFK_STATE.get("start_time", now))
        
        yanit = (
            f"💤 <b>Sahibim şu anda AFK (Uzakta)!</b>\n\n"
            f"📝 <b>Sebep:</b> <i>{ggr.safe_html(AFK_STATE.get('reason'))}</i>\n"
            f"⏱️ <b>Geçen Süre:</b> <code>{elapsed}</code>\n\n"
            f"📩 <i>Mesajınız kaydedildi. Kendisi sohbete döndüğünde görecektir.</i>"
        )
        try:
            await message.reply_text(yanit, disable_web_page_preview=True)
        except Exception:
            pass


# Sahibin sohbette mesaj yazmasıyla AFK'dan çıkma handler'ı
@Client.on_message(filters.me, group=-5)
async def afk_otomatik_kapat(client, message):
    if not AFK_STATE.get("is_afk"):
        return
        
    # Eğer komut .afk ise çıkış yapma (yeni sebep ayarlanıyor olabilir)
    if message.text and message.text.strip().lower().startswith(".afk"):
        return
        
    AFK_STATE["is_afk"] = False
    now = time.time()
    elapsed = format_afk_duration(now - AFK_STATE.get("start_time", now))
    pings = AFK_STATE.get("pings", [])
    
    # DB'den temizle
    ggr.set("afk_durumu", {"is_afk": False, "reason": "", "start_time": 0, "pings": []})
    await ggr.sync_cloud(client)
    
    ozet = (
        f"☀️ <b>Artık AFK Değilim!</b>\n\n"
        f"⏱️ <b>Uzak Kalınan Süre:</b> <code>{elapsed}</code>\n"
    )
    
    if pings:
        ozet += f"\n📩 <b>Siz Yokken Gelen Bildirimler ({len(pings)} Adet):</b>\n"
        # En son 8 bildirimi göster
        for p in pings[-8:]:
            isim = ggr.safe_html(p.get("name") or "Kullanıcı")
            u_id = p.get("user_id")
            c_name = ggr.safe_html(p.get("chat") or "Sohbet")
            t_str = ggr.safe_html(p.get("text") or "")
            ozet += f"• <a href=\"tg://user?id={u_id}\">{isim}</a> (<i>{c_name}</i>): <code>{t_str}</code>\n"
        if len(pings) > 8:
            ozet += f"• <i>...ve {len(pings) - 8} bildirim daha.</i>\n"
            
    try:
        bilgi = await client.send_message(message.chat.id, ozet, disable_web_page_preview=True)
        await asyncio.sleep(7)
        await bilgi.delete()
    except Exception:
        pass
