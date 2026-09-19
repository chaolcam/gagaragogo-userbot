# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Multi-Tier Group & Admin Tagger (plugins/etiket.py)
# Description: High-speed member tagger (.tag, .tagall, .all, .alladmin) with FloodWait
#              protection, forum topic routing, and fallback member scraping.
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

import asyncio
import logging
from pyrogram.enums import ChatType, ChatMembersFilter
from pyrogram.errors import FloodWait
from utils import ggr

# Devam eden etiketleme süreçlerini takip eden sözlük {chat_id: bool}
ggr_aktif_etiketler = {}
AKTIF_ETIKETLEMELER = ggr_aktif_etiketler


async def uyeleri_topla(client, chat_id, sadece_admin=False):
    """
    Gruptaki üyeleri çeker.
    Telethon'daki iter_participants benzeri ChatMembersFilter.RECENT kullanımı,
    standart arama, harf arama ve 'Üyeleri Gizle' modu için sohbet geçmişi (chat history)
    kombinasyonuyla en kapsamlı üye toplama motorudur.
    """
    uyeler = []
    seen_ids = set()

    # 1. Aşama: Yöneticileri Çek
    try:
        async for m in client.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
            if m.user and not m.user.is_bot and not m.user.is_deleted and not m.user.is_self:
                if m.user.id not in seen_ids:
                    seen_ids.add(m.user.id)
                    uyeler.append(m.user)
    except Exception as e:
        logging.error(f"Admin listesi çekme hatası: {e}")
    if sadece_admin:
        return uyeler

    # 2. Aşama: Telethon'daki gibi RECENT (son aktif üyeler) filtresi ile çekme
    try:
        async for m in client.get_chat_members(chat_id, filter=ChatMembersFilter.RECENT):
            if not ggr_aktif_etiketler.get(chat_id):
                break
            if m.user and not m.user.is_bot and not m.user.is_deleted and not m.user.is_self:
                if m.user.id not in seen_ids:
                    seen_ids.add(m.user.id)
                    uyeler.append(m.user)
    except Exception as e:
        logging.warning(f"RECENT üye çekme uyarısı: {e}")

    # 3. Aşama: Standart get_chat_members ile ekleme
    if len(uyeler) < 10 and ggr_aktif_etiketler.get(chat_id):
        try:
            async for m in client.get_chat_members(chat_id):
                if not ggr_aktif_etiketler.get(chat_id):
                    break
                if m.user and not m.user.is_bot and not m.user.is_deleted and not m.user.is_self:
                    if m.user.id not in seen_ids:
                        seen_ids.add(m.user.id)
                        uyeler.append(m.user)
        except Exception as e:
            logging.warning(f"Standart üye çekme uyarısı: {e}")

    # 4. Aşama: Harf bazlı arama (Supergroup SEARCH filtreleri için)
    if len(uyeler) < 10 and ggr_aktif_etiketler.get(chat_id):
        harfler = ["a", "e", "i", "o", "u", "b", "c", "d", "m", "s", "t", "1", "2"]
        for harf in harfler:
            if not ggr_aktif_etiketler.get(chat_id):
                break
            try:
                async for m in client.get_chat_members(chat_id, query=harf):
                    if not ggr_aktif_etiketler.get(chat_id):
                        break
                    if m.user and not m.user.is_bot and not m.user.is_deleted and not m.user.is_self:
                        if m.user.id not in seen_ids:
                            seen_ids.add(m.user.id)
                            uyeler.append(m.user)
            except Exception:
                continue

    # 5. Aşama: 'Üyeleri Gizle' modu açıksa veya Telegram kısıtlıysa, son sohbet mesajlarından aktif üyeleri topla!
    if len(uyeler) < 5 and ggr_aktif_etiketler.get(chat_id):
        try:
            async for msg in client.get_chat_history(chat_id, limit=300):
                if not ggr_aktif_etiketler.get(chat_id):
                    break
                u = msg.from_user
                if u and not u.is_bot and not u.is_deleted and not u.is_self:
                    if u.id not in seen_ids:
                        seen_ids.add(u.id)
                        uyeler.append(u)
        except Exception as e:
            logging.warning(f"Sohbet geçmişinden üye toplama uyarısı: {e}")

    return uyeler


@ggr.cmd(["tag", "tagall", "all", "alladmin", "etiket"], info="Gruplardaki üyeleri veya adminleri etiketler.", usage=".tag [mesaj] | .tag dur", category="Admin")
async def tag_komutu(client, message):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.edit_text("❌ <b>Bu komut yalnızca gruplarda kullanılabilir!</b>")
        return

    chat_id = message.chat.id
    cmd = message.command[0].lower() if message.command else "tag"
    args = message.text.split()[1:] if message.text else []
    subcmd = args[0].lower() if args else ""

    # -------------------------------------------------------------------------
    # DURDURMA: .tag dur / .tagall iptal / .all dur
    # -------------------------------------------------------------------------
    if subcmd in ["dur", "stop", "iptal", "cancel"]:
        if ggr_aktif_etiketler.get(chat_id):
            ggr_aktif_etiketler[chat_id] = False
            await message.edit_text("🛑 <b>Etiketleme durduruldu!</b>")
        else:
            await message.edit_text("ℹ️ Şu anda bu grupta aktif bir etiketleme işlemi yok.")
        return

    if ggr_aktif_etiketler.get(chat_id):
        await message.edit_text("⚠️ <b>Bu grupta zaten devam eden bir etiketleme var!</b>\nDurdurmak için: <code>.tag dur</code>")
        return

    # Mod ve ek mesaj tespiti
    if cmd == "alladmin" or subcmd in ["admin", "adminler", "yonetici", "yoneticiler"]:
        sadece_admin = True
        ek_mesaj = " ".join(args[1:] if subcmd in ["admin", "adminler", "yonetici", "yoneticiler"] else args).strip()
    elif subcmd in ["herkes", "all", "uyeler"]:
        sadece_admin = False
        ek_mesaj = " ".join(args[1:]).strip() if len(args) > 1 else ""
    else:
        sadece_admin = False
        ek_mesaj = " ".join(args).strip()

    # Forum ve konu (topic) desteği
    thread_id = getattr(message, "message_thread_id", None)
    reply_id = message.reply_to_message.id if message.reply_to_message else (thread_id or message.id)

    async def guvenli_mesaj_gonder(text):
        """Forum konularını ve normal sohbetleri hatasız destekleyen mesaj gönderici."""
        try:
            return await client.send_message(chat_id, text, reply_to_message_id=reply_id)
        except Exception:
            try:
                if thread_id:
                    return await client.send_message(chat_id, text, reply_to_message_id=thread_id)
                return await client.send_message(chat_id, text)
            except Exception as e:
                logging.error(f"Mesaj gönderme hatası: {e}")
                return None

    ggr_aktif_etiketler[chat_id] = True
    baslik_tur = "👑 Yöneticiler" if sadece_admin else "👥 Üyeler"
    
    await message.edit_text(
        f"⏳ <b>{baslik_tur} taranıyor, lütfen bekleyin...</b>\n"
        "💡 <i>Durdurmak için:</i> <code>.tag dur</code>"
    )

    try:
        uyeler = await uyeleri_topla(client, chat_id, sadece_admin=sadece_admin)

        if not uyeler:
            await message.edit_text(
                "⚠️ <b>Etiketlenecek üye bulunamadı!</b>\n\n"
                "• Grubun gizlilik ayarlarında <i>'Üyeleri Gizle'</i> açık olabilir ve son mesajlarda üye bulunamamış olabilir.\n"
                "• Grupta aktif ya da etiketlenebilecek kullanıcı kalmamış olabilir."
            )
            ggr_aktif_etiketler[chat_id] = False
            return

        toplam_sayi = len(uyeler)
        await message.edit_text(
            f"🚀 <b>Toplam {toplam_sayi} kişi bulundu!</b> Etiketleme başlıyor...\n"
            "💡 <i>Durdurmak için:</i> <code>.tag dur</code>"
        )

        sayac = 0
        paket = []

        for user in uyeler:
            if not ggr_aktif_etiketler.get(chat_id):
                break

            ad = ggr.safe_html(user.first_name or ("Yönetici" if sadece_admin else "Üye"))
            mention = f"<a href=\"tg://user?id={user.id}\">{ad}</a>"
            paket.append(mention)
            sayac += 1

            if len(paket) >= 5:
                metin = f"📢 <b>{ggr.safe_html(ek_mesaj)}</b>\n\n" if ek_mesaj else ""
                metin += " ".join(paket)
                try:
                    await guvenli_mesaj_gonder(metin)
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 1)
                    await guvenli_mesaj_gonder(metin)
                except Exception as send_err:
                    logging.warning(f"Paket gönderme hatası: {send_err}")
                paket = []
                await asyncio.sleep(1.5)

        # Kalan son paketi gönder
        if paket and ggr_aktif_etiketler.get(chat_id):
            metin = f"📢 <b>{ggr.safe_html(ek_mesaj)}</b>\n\n" if ek_mesaj else ""
            metin += " ".join(paket)
            try:
                await guvenli_mesaj_gonder(metin)
            except FloodWait as fw:
                await asyncio.sleep(fw.value + 1)
                await guvenli_mesaj_gonder(metin)
            except Exception as send_err:
                logging.warning(f"Son paket gönderme hatası: {send_err}")

        if ggr_aktif_etiketler.get(chat_id):
            await guvenli_mesaj_gonder(
                f"✅ <b>Etiketleme Tamamlandı!</b>\n"
                f"Toplam <code>{sayac}</code> kişi başarıyla etiketlendi."
            )

    except Exception as e:
        logging.error(f"Etiketleme hatası ({chat_id}): {e}")
        await guvenli_mesaj_gonder(f"❌ <b>Etiketleme Hatası:</b> <code>{e}</code>")
    finally:
        ggr_aktif_etiketler[chat_id] = False

