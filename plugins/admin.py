# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Group Administration & Moderation (plugins/admin.py)
# Description: Provides group management commands including user bans (.ban),
#              unbans (.unban), mutes (.mute), unmutes (.unmute), and message purge (.purge).
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# -----------------------------------------------------------------------------

import re
import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import ChatPermissions
from utils import ggr

def parse_time_arg(arg):
    """Zaman parametresini (örn: 30s, 15m, 2h, 7d) ayrıştırarak bitiş zamanını ve açıklamasını döndürür."""
    match = re.match(r"^(\d+)([smhd])$", arg.lower())
    if not match:
        return None, None
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    if unit == 's': delta = timedelta(seconds=amount)
    elif unit == 'm': delta = timedelta(minutes=amount)
    elif unit == 'h': delta = timedelta(hours=amount)
    elif unit == 'd': delta = timedelta(days=amount)
    
    until_date = datetime.now() + delta
    
    if unit == 's': string_zaman = f"{amount} saniye"
    elif unit == 'm': string_zaman = f"{amount} dakika"
    elif unit == 'h': string_zaman = f"{amount} saat"
    elif unit == 'd': string_zaman = f"{amount} gün"
    
    return until_date, string_zaman

async def extract_target_time_reason(client, message):
    """Komuttan veya yanıtlanan mesajdan hedef kullanıcıyı, süre parametresini ve sebebi ayrıştırır."""
    user = None
    until_date = None
    string_zaman = None
    reason = ""
    
    args = message.command[1:] if len(message.command) > 1 else []
    
    if message.reply_to_message:
        if message.reply_to_message.forward_from:
            user = message.reply_to_message.forward_from
        elif message.reply_to_message.from_user:
            user = message.reply_to_message.from_user
    else:
        if args:
            target = args.pop(0)
            if target.isdigit() or target.startswith("-"):
                try: 
                    user = await client.get_users(int(target))
                except: 
                    try:
                        member = await client.get_chat_member(message.chat.id, int(target))
                        user = member.user
                    except:
                        user = int(target)
            else:
                try: user = await client.get_users(target)
                except: pass
                    
    if args:
        ud, sz = parse_time_arg(args[0])
        if ud:
            until_date = ud
            string_zaman = sz
            args.pop(0)
            
    if args:
        reason = " ".join(args)
        
    return user, until_date, string_zaman, reason

@ggr.cmd("ban", info="Gruptaki bir kullanıcıyı yasaklar.", usage="Yanıtlayarak: .ban [zaman] [sebep] | Örn: .ban 1d Spam", category="Admin", filter=filters.group)
async def ban_user(client, message):
    """Gruptaki bir kullanıcıyı kalıcı veya süreli olarak yasaklar."""
    user, until_date, string_zaman, reason = await extract_target_time_reason(client, message)
    if not user:
        await message.edit_text("❌ Kimi yasaklayacağımı bulamadım.")
        return
        
    try:
        user_id = getattr(user, "id", user)
        user_name = getattr(user, "first_name", str(user))
        
        if until_date:
            await client.ban_chat_member(message.chat.id, user_id, until_date=until_date)
        else:
            await client.ban_chat_member(message.chat.id, user_id)
            
        metin = f"🔨 <a href=\"tg://user?id={user_id}\">{ggr.safe_html(user_name)}</a> başarıyla yasaklandı!"
        if string_zaman: metin += f"\n⏳ <b>Süre:</b> <code>{string_zaman}</code>"
        if reason: metin += f"\n📝 <b>Sebep:</b> <code>{reason}</code>"
        await message.edit_text(metin)
    except Exception as e:
        await message.edit_text(f"❌ Yasaklama başarısız: <code>{e}</code>")

@ggr.cmd("unban", info="Kullanıcının yasağını kaldırır.", usage="Yanıtlayarak: .unban | ID: .unban 1234", category="Admin", filter=filters.group)
async def unban_user(client, message):
    """Kullanıcının grup yasağını kaldırır."""
    user, _, _, _ = await extract_target_time_reason(client, message)
    if not user:
        await message.edit_text("❌ Kimi açacağımı bulamadım.")
        return
        
    try:
        user_id = getattr(user, "id", user)
        user_name = getattr(user, "first_name", str(user))
        await client.unban_chat_member(message.chat.id, user_id)
        await message.edit_text(f"🕊 <a href=\"tg://user?id={user_id}\">{ggr.safe_html(user_name)}</a> yasağı kaldırıldı!")
    except Exception as e:
        await message.edit_text(f"❌ İşlem başarısız: <code>{e}</code>")

@ggr.cmd("mute", info="Kullanıcıyı susturur.", usage="Yanıtlayarak: .mute [zaman] [sebep] | Örn: .mute 2h Küfür", category="Admin", filter=filters.group)
async def mute_user(client, message):
    """Kullanıcının grupta mesaj yazmasını engeller (susturur)."""
    user, until_date, string_zaman, reason = await extract_target_time_reason(client, message)
    if not user:
        await message.edit_text("❌ Kimi susturacağımı bulamadım. Yanıt verin veya @kullanici belirtin.")
        return
        
    try:
        user_id = getattr(user, "id", user)
        user_name = getattr(user, "first_name", str(user))
        
        if until_date:
            await client.restrict_chat_member(message.chat.id, user_id, ChatPermissions(can_send_messages=False), until_date=until_date)
        else:
            await client.restrict_chat_member(message.chat.id, user_id, ChatPermissions(can_send_messages=False))
            
        metin = f"🤐 <a href=\"tg://user?id={user_id}\">{ggr.safe_html(user_name)}</a> başarıyla susturuldu!"
        if string_zaman: metin += f"\n⏳ <b>Süre:</b> <code>{string_zaman}</code>"
        if reason: metin += f"\n📝 <b>Sebep:</b> <code>{reason}</code>"
        await message.edit_text(metin)
    except Exception as e:
        await message.edit_text(f"❌ Susturma başarısız: <code>{e}</code>")

@ggr.cmd("unmute", info="Kullanıcının susturmasını kaldırır.", usage="Yanıtlayarak: .unmute | ID: .unmute 1234", category="Admin", filter=filters.group)
async def unmute_user(client, message):
    """Kullanıcının susturmasını kaldırarak tüm mesaj gönderme yetkilerini geri verir."""
    user, _, _, _ = await extract_target_time_reason(client, message)
    if not user:
        await message.edit_text("❌ Kimi açacağımı bulamadım.")
        return
        
    try:
        user_id = getattr(user, "id", user)
        user_name = getattr(user, "first_name", str(user))
        tam_yetki = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_send_polls=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        await client.restrict_chat_member(message.chat.id, user_id, tam_yetki)
        await message.edit_text(f"🔊 <a href=\"tg://user?id={user_id}\">{ggr.safe_html(user_name)}</a> kullanıcısının susturması kaldırıldı!")
    except Exception as e:
        await message.edit_text(f"❌ İşlem başarısız: <code>{e}</code>")

@ggr.cmd("purge", info="Yanıtlanan mesajdan itibaren (kendisi dahil) tüm mesajları siler.", usage="Yanıtlayarak: .purge", category="Admin")
async def purge_messages(client, message):
    """Yanıtlanan mesajdan mevcut komut mesajına kadar olan tüm mesajları topluca siler."""
    if not message.reply_to_message:
        await message.edit_text("❌ Lütfen silinmeye başlanacak mesaja yanıt verin.")
        return

    start_id = message.reply_to_message.id
    end_id = message.id

    if end_id - start_id > 10000:
        await message.edit_text("❌ Çok fazla mesaj var (10000+). Lütfen daha dar bir aralık seçin.")
        return

    await message.edit_text("🧹 <i>Temizleniyor...</i>")

    message_ids = list(range(start_id, end_id + 1))
    
    deleted_count = 0
    chunk_size = 100
    for i in range(0, len(message_ids), chunk_size):
        chunk = message_ids[i:i + chunk_size]
        try:
            await client.delete_messages(
                chat_id=message.chat.id,
                message_ids=chunk,
                revoke=True
            )
            deleted_count += len(chunk)
            await asyncio.sleep(0.5)
        except Exception:
            pass

    try:
        msg = await client.send_message(message.chat.id, f"✅ <code>{deleted_count}</code> mesaj başarıyla temizlendi.")
        await asyncio.sleep(3)
        await msg.delete()
    except Exception:
        pass

@ggr.cmd("delme", info="Bu sohbette attığınız son N adet mesajınızı siler.", usage=".delme [sayı]", category="Admin")
async def delme_messages(client, message):
    """Kullanıcının sohbette gönderdiği kendi son mesajlarını siler."""
    args = message.command[1:] if len(message.command) > 1 else []
    limit = 10
    if args and args[0].isdigit():
        limit = int(args[0])
    
    if limit > 200:
        limit = 200
        
    await message.edit_text(f"🧹 <i>Son {limit} adet mesajınız taranıyor...</i>")
    
    my_id = (await client.get_me()).id
    to_delete = []
    
    async for msg in client.get_chat_history(message.chat.id, limit=limit + 50):
        if msg.from_user and msg.from_user.id == my_id:
            to_delete.append(msg.id)
            if len(to_delete) >= limit:
                break
                
    if to_delete:
        await client.delete_messages(chat_id=message.chat.id, message_ids=to_delete, revoke=True)
    
    try:
        bilgi = await client.send_message(message.chat.id, f"✅ <b>{len(to_delete)}</b> adet mesajınız başarıyla temizlendi.")
        await asyncio.sleep(3)
        await bilgi.delete()
    except Exception:
        pass

LOCK_FIELDS = {
    "msg": ("can_send_messages", "Mesaj Gönderme"),
    "mesaj": ("can_send_messages", "Mesaj Gönderme"),
    "yazi": ("can_send_messages", "Mesaj Gönderme"),
    "media": ("can_send_media_messages", "Medya Gönderme"),
    "medya": ("can_send_media_messages", "Medya Gönderme"),
    "sticker": ("can_send_other_messages", "Çıkartma & GIF"),
    "etiket": ("can_send_other_messages", "Çıkartma & GIF"),
    "gif": ("can_send_other_messages", "Çıkartma & GIF"),
    "link": ("can_add_web_page_previews", "Bağlantı Önizlemesi"),
    "baglanti": ("can_add_web_page_previews", "Bağlantı Önizlemesi"),
    "poll": ("can_send_polls", "Anket Gönderme"),
    "anket": ("can_send_polls", "Anket Gönderme"),
    "invite": ("can_invite_users", "Üye Ekleme"),
    "davet": ("can_invite_users", "Üye Ekleme"),
    "pin": ("can_pin_messages", "Mesaj Sabitleme"),
    "sabitle": ("can_pin_messages", "Mesaj Sabitleme")
}

@ggr.cmd("lock", info="Grupta belirli bir medya veya işlem türünü kilitler.", usage=".lock [msg/media/sticker/link/poll/invite/all]", category="Admin")
async def lock_chat(client, message):
    if not message.chat or message.chat.type.name not in ["GROUP", "SUPERGROUP"]:
        await message.edit_text("❌ Bu komut yalnızca gruplarda kullanılabilir.")
        return
        
    args = message.command[1:] if len(message.command) > 1 else []
    if not args:
        rehber = (
            "🔒 <b>Yetki Kilitleme Rehberi (.lock):</b>\n\n"
            "• <code>.lock msg</code> — Tüm mesaj yazmayı kilitler.\n"
            "• <code>.lock media</code> — Fotoğraf & video gönderimini kilitler.\n"
            "• <code>.lock sticker</code> — Çıkartma & GIF gönderimini kilitler.\n"
            "• <code>.lock link</code> — Bağlantı önizlemelerini kilitler.\n"
            "• <code>.lock poll</code> — Anket gönderimini kilitler.\n"
            "• <code>.lock invite</code> — Üye eklemeyi kilitler.\n"
            "• <code>.lock all</code> — Gruptaki tüm izinleri kilitler."
        )
        await message.edit_text(rehber)
        return

    tur = args[0].lower()
    
    try:
        chat = await client.get_chat(message.chat.id)
        current = chat.permissions or ChatPermissions()
        
        perm_kwargs = {
            "can_send_messages": getattr(current, "can_send_messages", True),
            "can_send_media_messages": getattr(current, "can_send_media_messages", True),
            "can_send_other_messages": getattr(current, "can_send_other_messages", True),
            "can_add_web_page_previews": getattr(current, "can_add_web_page_previews", True),
            "can_send_polls": getattr(current, "can_send_polls", True),
            "can_change_info": getattr(current, "can_change_info", True),
            "can_invite_users": getattr(current, "can_invite_users", True),
            "can_pin_messages": getattr(current, "can_pin_messages", True),
        }
        
        if tur in ["all", "hepsi"]:
            for k in perm_kwargs:
                perm_kwargs[k] = False
            await client.set_chat_permissions(message.chat.id, ChatPermissions(**perm_kwargs))
            await message.edit_text("🔒 <b>Gruptaki tüm üye yetkileri kilitlendi!</b>")
            return
            
        if tur in LOCK_FIELDS:
            attr_name, desc = LOCK_FIELDS[tur]
            perm_kwargs[attr_name] = False
            if attr_name == "can_send_messages":
                perm_kwargs["can_send_media_messages"] = False
                perm_kwargs["can_send_other_messages"] = False
                perm_kwargs["can_add_web_page_previews"] = False
                perm_kwargs["can_send_polls"] = False
                
            await client.set_chat_permissions(message.chat.id, ChatPermissions(**perm_kwargs))
            await message.edit_text(f"🔒 <b>{desc} yetkisi bu grupta kilitlendi!</b>")
        else:
            await message.edit_text(f"❌ Bilinmeyen yetki türü: <code>{tur}</code>\nGeçerli türler: msg, media, sticker, link, poll, invite, all")
    except Exception as e:
        await message.edit_text(f"❌ Yetki kilitlenirken hata: <code>{e}</code>")

@ggr.cmd("unlock", info="Grupta kilitlenen bir yetkiyi tekrar açar.", usage=".unlock [msg/media/sticker/link/poll/invite/all]", category="Admin")
async def unlock_chat(client, message):
    if not message.chat or message.chat.type.name not in ["GROUP", "SUPERGROUP"]:
        await message.edit_text("❌ Bu komut yalnızca gruplarda kullanılabilir.")
        return
        
    args = message.command[1:] if len(message.command) > 1 else []
    if not args:
        rehber = (
            "🔓 <b>Yetki Açma Rehberi (.unlock):</b>\n\n"
            "• <code>.unlock msg</code> — Mesaj yazma kilidini açar.\n"
            "• <code>.unlock media</code> — Medya gönderme kilidini açar.\n"
            "• <code>.unlock sticker</code> — Çıkartma & GIF kilidini açar.\n"
            "• <code>.unlock link</code> — Bağlantı kilidini açar.\n"
            "• <code>.unlock poll</code> — Anket kilidini açar.\n"
            "• <code>.unlock invite</code> — Üye ekleme kilidini açar.\n"
            "• <code>.unlock all</code> — Gruptaki tüm izinleri açar."
        )
        await message.edit_text(rehber)
        return

    tur = args[0].lower()
    
    try:
        chat = await client.get_chat(message.chat.id)
        current = chat.permissions or ChatPermissions()
        
        perm_kwargs = {
            "can_send_messages": getattr(current, "can_send_messages", True),
            "can_send_media_messages": getattr(current, "can_send_media_messages", True),
            "can_send_other_messages": getattr(current, "can_send_other_messages", True),
            "can_add_web_page_previews": getattr(current, "can_add_web_page_previews", True),
            "can_send_polls": getattr(current, "can_send_polls", True),
            "can_change_info": getattr(current, "can_change_info", True),
            "can_invite_users": getattr(current, "can_invite_users", True),
            "can_pin_messages": getattr(current, "can_pin_messages", True),
        }
        
        if tur in ["all", "hepsi"]:
            for k in perm_kwargs:
                perm_kwargs[k] = True
            await client.set_chat_permissions(message.chat.id, ChatPermissions(**perm_kwargs))
            await message.edit_text("🔓 <b>Gruptaki tüm üye yetkileri açıldı!</b>")
            return
            
        if tur in LOCK_FIELDS:
            attr_name, desc = LOCK_FIELDS[tur]
            perm_kwargs[attr_name] = True
            if attr_name == "can_send_messages":
                perm_kwargs["can_send_media_messages"] = True
                perm_kwargs["can_send_other_messages"] = True
                perm_kwargs["can_add_web_page_previews"] = True
                perm_kwargs["can_send_polls"] = True
                
            await client.set_chat_permissions(message.chat.id, ChatPermissions(**perm_kwargs))
            await message.edit_text(f"🔓 <b>{desc} yetkisi bu grupta açıldı!</b>")
        else:
            await message.edit_text(f"❌ Bilinmeyen yetki türü: <code>{tur}</code>\nGeçerli türler: msg, media, sticker, link, poll, invite, all")
    except Exception as e:
        await message.edit_text(f"❌ Yetki açılırken hata: <code>{e}</code>")
