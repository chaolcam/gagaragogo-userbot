# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Periodic Scheduled Broadcast Engine (plugins/otomesaj.py)
# Description: Background daemon for interval-based broadcast tasks, supporting
#              text and media messages with interactive inline management (.otomesaj).
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


import os
import re
import json
import time
import asyncio
import logging
from pyrogram import Client, filters, errors
from utils import ggr
import utils

ggr_otomesaj_db_file = "otomesaj.json"
ggr_otomesaj_bekleme = 0.8
ggr_otomesaj_min_aralik = 5.0  # Spam koruması için minimum 5 dakika
MIN_ARALIK_DAKIKA = ggr_otomesaj_min_aralik


# =============================================================================
# 1. VERİTABANI YÖNETİMİ & BULUT SENKRONİZASYONU
# =============================================================================

def otomesaj_db_yukle():
    """Tüm otomesaj görevlerini JSON dosyasından yükler."""
    if not os.path.exists(ggr_otomesaj_db_file):
        return {}
    try:
        with open(ggr_otomesaj_db_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"otomesaj.json okuma hatası: {e}")
        return {}


def otomesaj_db_kaydet(data, sync_cloud=True):
    """Görevleri diske yazar ve isteğe bağlı tek bulut veritabanına kaydeder."""
    try:
        with open(ggr_otomesaj_db_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        if sync_cloud:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ggr.sync_cloud())
            except Exception:
                pass
    except Exception as e:
        logging.error(f"otomesaj.json kaydetme hatası: {e}")


def get_next_task_id(db):
    """Sıradaki benzersiz sayısal görev ID'sini döner."""
    if not db:
        return 1
    existing_ids = [int(k) for k in db.keys() if str(k).isdigit()]
    return max(existing_ids) + 1 if existing_ids else 1


# =============================================================================
# 2. ESNEK SÜRE VE AKILLI BAŞLIK YARDIMCILARI
# =============================================================================

def parse_sure(sure_str):
    """
    Kullanıcıdan gelen serbest süreyi dakikaya çevirir.
    Örnekler:
      '2.5 saat' -> 150.0
      '45 dk', '45m' -> 45.0
      '1.5 gün', '1.5d' -> 2160.0
      '90' -> 90.0
    """
    if not sure_str:
        return None
    s = sure_str.strip().lower().replace(",", ".")
    
    # Gün tespiti
    match_gun = re.search(r"(\d+(?:\.\d+)?)\s*(?:gün|gun|g|d|days?)\b", s)
    if match_gun:
        return max(ggr_otomesaj_min_aralik, float(match_gun.group(1)) * 1440.0)
        
    # Saat tespiti
    match_saat = re.search(r"(\d+(?:\.\d+)?)\s*(?:saat|sa|h|hours?)\b", s)
    if match_saat:
        return max(ggr_otomesaj_min_aralik, float(match_saat.group(1)) * 60.0)
        
    # Dakika tespiti
    match_dk = re.search(r"(\d+(?:\.\d+)?)\s*(?:dakika|dak|dk|m|mins?)\b", s)
    if match_dk:
        return max(ggr_otomesaj_min_aralik, float(match_dk.group(1)))
        
    # Yalın sayı (varsayılan dakika)
    match_num = re.match(r"^(\d+(?:\.\d+)?)$", s)
    if match_num:
        return max(ggr_otomesaj_min_aralik, float(match_num.group(1)))
        
    return None


def format_sure(dakika):
    """Dakikayı okunabilir güzel Türkçe metne çevirir."""
    if not dakika or dakika <= 0:
        return "Belirsiz"
    dakika = float(dakika)
    if dakika >= 1440:
        gun = dakika / 1440.0
        return f"{int(gun)} gün" if gun.is_integer() else f"{gun:.1f} gün"
    if dakika >= 60:
        saat = dakika / 60.0
        return f"{int(saat)} saat" if saat.is_integer() else f"{saat:.1f} saat"
    return f"{int(dakika)} dakika"


def akilli_baslik_uret(message, custom_title=None, task_id=1):
    """Kullanıcı başlık yazmazsa mesajın ilk kelimelerinden veya türünden şık bir başlık oluşturur."""
    if custom_title and custom_title.strip():
        return custom_title.strip()[:35]
        
    raw_text = (message.caption or message.text or "").strip()
    if raw_text:
        # İlk 3-4 kelimeyi veya ilk 25 karakteri al
        words = raw_text.split()
        cand = " ".join(words[:4]) if len(words) >= 4 else raw_text
        cleaned = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇ]", "", cand).strip()
        if len(cleaned) > 25:
            cleaned = cleaned[:25].strip()
        if cleaned:
            return cleaned[:30]
            
    if message.photo:
        return f"Fotoğraf İletisi #{task_id}"
    if message.video:
        return f"Video İletisi #{task_id}"
    if message.document:
        return f"Belge İletisi #{task_id}"
    if message.voice or message.audio:
        return f"Ses İletisi #{task_id}"
        
    return f"Otomatik İleti #{task_id}"


def get_task_preview(message_text, has_media=False):
    """Mesajın kısa bir önizlemesini döner."""
    prefix = "🖼 [Medya] " if has_media else ""
    if not message_text:
        return prefix + "(Yazısız Medya)"
    clean = message_text.replace("\n", " ").strip()
    if len(clean) > 40:
        clean = clean[:37] + "..."
    return prefix + clean


# =============================================================================
# 3. İLETİM VE ARKA PLAN MONITOR MOTORU
# =============================================================================

async def execute_task_broadcast(client, task_id, task_data):
    """Belirli bir görevi hedef gruplarına iletir. onceki_sil aktifse eski mesajı silip yenisini atar."""
    hedef_gruplar = task_data.get("hedef_gruplar", [])
    saved_msg_id = task_data.get("saved_msg_id")
    baslik = task_data.get("baslik", f"Görev #{task_id}")
    onceki_sil = task_data.get("onceki_sil", False)
    son_mesajlar = task_data.get("son_mesajlar", {})
    if not isinstance(son_mesajlar, dict):
        son_mesajlar = {}
    
    if not hedef_gruplar:
        logging.warning(f"Otomesaj #{task_id} ({baslik}) hedef grup listesi boş, atlandı.")
        return 0, 0
        
    if not saved_msg_id:
        logging.error(f"Otomesaj #{task_id} ({baslik}) kayıtlı mesaj ID'si bulunamadı!")
        return 0, 0
        
    try:
        kaynak_mesaj = await client.get_messages("me", saved_msg_id)
        if not kaynak_mesaj or kaynak_mesaj.empty:
            logging.error(f"Otomesaj #{task_id} Kayıtlı Mesajlar'dan mesaj çekilemedi.")
            return 0, 0
    except Exception as e:
        logging.error(f"Otomesaj #{task_id} kaynak mesaj çekme hatası: {e}")
        return 0, 0
        
    basarili = 0
    hatali = 0
    
    for idx, chat_id in enumerate(hedef_gruplar, 1):
        chat_key = str(chat_id)
        
        # 1. Eğer 'Önceki Mesajı Sil' modu açıksa önceki mesajı sil
        if onceki_sil and chat_key in son_mesajlar:
            try:
                await client.delete_messages(chat_id, son_mesajlar[chat_key])
            except Exception:
                pass

        # 2. Yeni mesajı kopyala
        try:
            sent_msg = await kaynak_mesaj.copy(chat_id)
            if sent_msg and hasattr(sent_msg, "id"):
                son_mesajlar[chat_key] = sent_msg.id
            basarili += 1
        except errors.FloodWait as e:
            logging.warning(f"Otomesaj FloodWait: {e.value} sn bekleniyor...")
            await asyncio.sleep(e.value + 1)
            try:
                sent_msg = await kaynak_mesaj.copy(chat_id)
                if sent_msg and hasattr(sent_msg, "id"):
                    son_mesajlar[chat_key] = sent_msg.id
                basarili += 1
            except Exception:
                hatali += 1
        except Exception as err:
            logging.warning(f"Otomesaj #{task_id} iletim hatası (Chat: {chat_id}): {err}")
            hatali += 1
            
        if idx < len(hedef_gruplar):
            await asyncio.sleep(ggr_otomesaj_bekleme)
            
    # Görevdeki son_mesajlar haritasını güncelle ve kaydet
    task_data["son_mesajlar"] = son_mesajlar
    db = otomesaj_db_yukle()
    if str(task_id) in db:
        db[str(task_id)]["son_mesajlar"] = son_mesajlar
        otomesaj_db_kaydet(db, sync_cloud=True)

    logging.info(f"📢 Otomesaj #{task_id} ({baslik}) tamamlandı: {basarili} başarılı, {hatali} hata.")
    return basarili, hatali


async def otomesaj_monitor_loop(client):
    """Arka planda her 30 saniyede bir görevleri kontrol eden ana zamanlayıcı."""
    await asyncio.sleep(10)  # Bot ilk açılırken sistemin oturması için bekle
    logging.info("⏰ Otomatik Mesaj İletim Motoru (Otomesaj) Başlatıldı!")
    
    while True:
        try:
            db = otomesaj_db_yukle()
            now = time.time()
            degisti = False
            
            for task_id_str, task in list(db.items()):
                if not task.get("aktif", True):
                    continue
                    
                aralik_dk = task.get("aralik_dakika", 60.0)
                aralik_sn = aralik_dk * 60.0
                son_gonderim = task.get("son_gonderim", 0)
                
                # Zamanı gelmiş mi kontrol et
                if (now - son_gonderim) >= aralik_sn:
                    task_id = int(task_id_str)
                    logging.info(f"🚀 Otomesaj #{task_id} zamanı geldi, iletiliyor...")
                    
                    basarili, hatali = await execute_task_broadcast(client, task_id, task)
                    
                    # Son gönderim zamanını güncelle
                    task["son_gonderim"] = now
                    db[task_id_str] = task
                    degisti = True
                    
                    # İsteğe bağlı sistem loguna bildirim
                    try:
                        log_metin = (
                            f"⏰ <b>Otomesaj İletildi!</b>\n"
                            f"📌 <b>Görev:</b> {task.get('baslik')}\n"
                            f"👥 <b>İletilen Grup:</b> {basarili}/{len(task.get('hedef_gruplar', []))}\n"
                            f"⏱ <b>Periyot:</b> {format_sure(aralik_dk)}"
                        )
                        await utils.tlog(log_metin)
                    except Exception:
                        pass
                        
            if degisti:
                otomesaj_db_kaydet(db, sync_cloud=True)
                
        except Exception as e:
            logging.error(f"Otomesaj döngü hatası: {e}")
            
        await asyncio.sleep(30)


# =============================================================================
# 4. KOMUT İŞLEYİCİLERİ (.otomesaj)
# =============================================================================

@ggr.cmd(["otomesaj", "otomesajlar"], info="Otomatik zamanlanmış mesaj yönetim panelini açar.", usage=".otomesaj | .otomesaj ekle [başlık]", category="Toplu İletim")
async def otomesaj_komutu(client, message):
    """Otomatik mesaj ana komutu ve alt komutları yönetir."""
    args = message.text.split()[1:] if message.text else []
    subcmd = args[0].lower() if args else ""
    
    # -------------------------------------------------------------------------
    # A) YENİ GÖREV EKLEME: .otomesaj ekle [isteğe bağlı başlık]
    # -------------------------------------------------------------------------
    if subcmd in ["ekle", "add", "yeni"]:
        kaynak_mesaj = message.reply_to_message
        ek_metin = " ".join(args[1:]).strip() if len(args) > 1 else None
        
        if not kaynak_mesaj and not ek_metin:
            await message.edit_text(
                "❌ <b>Lütfen kaydedilecek bir içerik belirtin!</b>\n\n"
                "💡 <b>Kullanım:</b>\n"
                "• Mesaja yanıt vererek: <code>.otomesaj ekle [Başlık]</code>\n"
                "• Metin yazarak: <code>.otomesaj ekle [Metin]</code>"
            )
            return
            
        durum = await message.edit_text("⏳ <i>Mesaj kaydediliyor ve ayarlanıyor...</i>")
        
        # Eğer yanıtlanan mesaj yoksa kullanıcının yazdığı metinden mesaj oluşturup me'ye at
        if not kaynak_mesaj:
            saved = await client.send_message("me", ek_metin)
            custom_title = None
        else:
            saved = await kaynak_mesaj.copy("me")
            custom_title = ek_metin
            
        db = otomesaj_db_yukle()
        task_id = get_next_task_id(db)
        baslik = akilli_baslik_uret(saved, custom_title=custom_title, task_id=task_id)
        
        # Kullanıcının mevcut açık gruplarını varsayılan hedef grup yap
        from plugins.ilet import get_all_user_groups, is_group_active
        butun = await get_all_user_groups(client)
        varsayilan_gruplar = [g["id"] for g in butun if is_group_active(g["id"])]
        
        db[str(task_id)] = {
            "id": task_id,
            "baslik": baslik,
            "saved_msg_id": saved.id,
            "saved_chat_id": "me",
            "preview": get_task_preview(saved.text or saved.caption, bool(saved.photo or saved.video or saved.document)),
            "aralik_dakika": 60.0,
            "son_gonderim": 0,
            "aktif": True,
            "onceki_sil": False,
            "son_mesajlar": {},
            "hedef_gruplar": varsayilan_gruplar
        }
        otomesaj_db_kaydet(db, sync_cloud=True)
        
        # Başarılı bildirim ve inline menüyü sun
        await durum.delete()
        if utils.YARDIMCI_BOT_USERNAME:
            try:
                results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, f"otomsg_view_{task_id}")
                if results and results.results:
                    res = await client.send_inline_bot_result(
                        message.chat.id,
                        results.query_id,
                        results.results[0].id
                    )
                    sent_id = getattr(res, "id", None)
                    if not sent_id and hasattr(res, "updates"):
                        for u in res.updates:
                            if hasattr(u, "message") and hasattr(u.message, "id"):
                                sent_id = u.message.id; break
                    if sent_id:
                        utils.LAST_OTOMESAJ_MENU = (message.chat.id, sent_id)
                    return
            except Exception:
                pass
                
        await client.send_message(
            message.chat.id,
            f"✅ <b>Otomesaj #{task_id} Başarıyla Eklendi!</b>\n\n"
            f"📌 <b>Başlık:</b> <code>{baslik}</code>\n"
            "⏱ <b>Süre:</b> 1 saat (60 dk)\n"
            f"👥 <b>Hedef:</b> {len(varsayilan_gruplar)} grup seçildi.\n\n"
            "💡 Yönetmek için: <code>.otomesaj</code>"
        )
        return

    # -------------------------------------------------------------------------
    # B) SÜRE AYARLAMA: .otomesaj sure [id] [süre]
    # -------------------------------------------------------------------------
    if subcmd in ["sure", "süre", "time"]:
        if len(args) < 3:
            await message.edit_text(
                "❌ <b>Hatalı Kullanım!</b>\n\n"
                "💡 <b>Örnekler:</b>\n"
                "• <code>.otomesaj sure 1 2.5 saat</code>\n"
                "• <code>.otomesaj sure 1 45 dk</code>\n"
                "• <code>.otomesaj sure 1 1.5 gun</code>\n"
                "• <code>.otomesaj sure 1 90</code>"
            )
            return
            
        task_id_str = args[1]
        sure_giris = " ".join(args[2:])
        dakika = parse_sure(sure_giris)
        
        if not dakika:
            await message.edit_text(f"❌ Geçersiz süre: <code>{sure_giris}</code>\nÖrnek: <code>2.5 saat</code>, <code>45 dk</code>, <code>1 gün</code>")
            return
            
        db = otomesaj_db_yukle()
        if task_id_str not in db:
            await message.edit_text(f"❌ Görev #{task_id_str} bulunamadı!")
            return
            
        db[task_id_str]["aralik_dakika"] = dakika
        otomesaj_db_kaydet(db, sync_cloud=True)
        
        await message.edit_text(
            f"✅ <b>Otomesaj #{task_id_str} Süresi Güncellendi!</b>\n\n"
            f"📌 <b>Başlık:</b> <code>{db[task_id_str]['baslik']}</code>\n"
            f"⏱ <b>Yeni Süre:</b> <code>{format_sure(dakika)}</code> ({dakika:.1f} dakika)"
        )
        return

    # -------------------------------------------------------------------------
    # C) GÖREV SİLME: .otomesaj sil [id]
    # -------------------------------------------------------------------------
    if subcmd in ["sil", "del", "delete"]:
        if len(args) < 2:
            await message.edit_text("❌ Kullanım: <code>.otomesaj sil [id]</code> (Örn: <code>.otomesaj sil 1</code>)")
            return
            
        task_id_str = args[1]
        db = otomesaj_db_yukle()
        if task_id_str not in db:
            await message.edit_text(f"❌ Görev #{task_id_str} bulunamadı!")
            return
            
        silinen = db.pop(task_id_str)
        otomesaj_db_kaydet(db, sync_cloud=True)
        await message.edit_text(f"🗑 <b>Otomesaj #{task_id_str} ({silinen['baslik']}) silindi.</b>")
        return

    # -------------------------------------------------------------------------
    # D) ANA LİSTE VE İNTERAKTİF BUTON PANELİ: .otomesaj
    # -------------------------------------------------------------------------
    durum = await message.edit_text("🔄 <i>Otomesaj paneli yükleniyor...</i>")
    db = otomesaj_db_yukle()
    
    if not db:
        await durum.edit_text(
            "ℹ️ <b>Kayıtlı otomatik mesajınız bulunmuyor.</b>\n\n"
            "💡 <b>Yeni Mesaj Eklemek İçin:</b>\n"
            "Herhangi bir mesaja yanıt vererek:\n"
            "<code>.otomesaj ekle [Başlık]</code> yazabilirsiniz."
        )
        return

    if utils.YARDIMCI_BOT_USERNAME:
        try:
            results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, "otomesaj")
            if results and results.results:
                res = await client.send_inline_bot_result(
                    message.chat.id,
                    results.query_id,
                    results.results[0].id
                )
                sent_id = getattr(res, "id", None)
                if not sent_id and hasattr(res, "updates"):
                    for u in res.updates:
                        if hasattr(u, "message") and hasattr(u.message, "id"):
                            sent_id = u.message.id; break
                if sent_id:
                    utils.LAST_OTOMESAJ_MENU = (message.chat.id, sent_id)
                await durum.delete()
                return
        except Exception as e:
            logging.warning(f"Inline otomesaj menü hatası: {e}")

    # Fallback metin listesi
    metin = "⏰ <b>Kayıtlı Otomatik Mesaj Görevleri:</b>\n\n"
    for tid, t in db.items():
        durum_str = "🟢 Aktif" if t.get("aktif", True) else "🔴 Duraklatıldı"
        sure_str = format_sure(t.get("aralik_dakika", 60))
        metin += f"<b>{tid}. {t.get('baslik')}</b>\n"
        metin += f"   • Durum: {durum_str} | ⏱ {sure_str} | 👥 {len(t.get('hedef_gruplar', []))} Grup\n\n"
    metin += "💡 Süre değiştirmek: <code>.otomesaj sure [id] 2.5 saat</code>\n🗑 Silmek: <code>.otomesaj sil [id]</code>"
    await durum.edit_text(metin)
