# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Core Utilities & Cloud Storage Hub (utils.py)
# Description: Admin/log group management, multi-provider cloud image uploader,
#              settings persistence, progress bar visualizers, and helper tools.
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
import json
import asyncio
import logging

# Dinamik ayarlar için getter fonksiyonları (Ana Admin / Yedek Grubu ve Log)
def get_yedek_grup_id():
    """Ana admin grup ID'sini döner. '0' veya boş ise 0 döner (otomatik grup açılmasını tetikler)."""
    val = ayar_getir("YEDEK_GRUP_ID", os.environ.get("YEDEK_GRUP_ID", 0))
    try:
        val_str = str(val).strip()
        if not val_str or val_str == "0":
            return 0
        return int(val_str)
    except Exception:
        return 0

def get_yedek_konu():
    """Geriye dönük uyumluluk: yedek konu ID'sini döner."""
    return ayar_getir("yedek_konu_id")

def get_log_konu():
    """Geriye dönük uyumluluk: log konu ID'sini döner."""
    return ayar_getir("log_topic_id")

async def get_or_create_log_topic(client, chat_id):
    """Ana admin grubunda sistem logları için otomatik forum konusu oluşturur/getirir."""
    topic_id = ayar_getir("log_topic_id")
    if not topic_id and str(chat_id).startswith("-100"):
        try:
            topic_id = await create_forum_topic_helper(client, chat_id, "🛠 Sistem Logları")
            if topic_id:
                ayar_kaydet("log_topic_id", topic_id)
        except Exception as e:
            print(f"Log topic oluşturma hatası: {e}")
    return topic_id

bot_client = None
YARDIMCI_BOT_USERNAME = None
OWNER_ID = None

def get_owner_id():
    global OWNER_ID
    if OWNER_ID:
        return OWNER_ID
    if bot_client and hasattr(bot_client, "me") and bot_client.me:
        OWNER_ID = bot_client.me.id
        return OWNER_ID
    return None

async def tlog(metin):
    """Sistem hatalarını Telegram'a loglar"""
    if bot_client:
        try:
            yedek_id = get_yedek_grup_id()
            if not yedek_id or yedek_id == 0: return
            topic_id = await get_or_create_log_topic(bot_client, yedek_id)
            await bot_client.send_message(
                chat_id=yedek_id, 
                text=f"🛠 <b>SİSTEM LOGU:</b>\n\n<code>{guvenli_isim(str(metin)[:4000])}</code>", 
                reply_to_message_id=topic_id
            )
        except Exception as e:
            print(f"Telegram'a log atılamadı: {e}")



def guvenli_isim(metin):
    """Telegram HTML ayrıştırma hatalarını önlemek için metindeki özel karakterleri (&, <, >) kaçırır."""
    return str(metin).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def ram_dosyasini_isimlendir(msg, ram_dosyasi):
    """RAM'e (in_memory BytesIO) indirilen medyalara Telegram yüklemesi için uygun dosya adı ve uzantı atar."""
    if msg.photo: ram_dosyasi.name = "gorsel.jpg"
    elif msg.video: ram_dosyasi.name = "video.mp4"
    elif msg.voice: ram_dosyasi.name = "ses_kaydi.ogg"
    elif msg.audio: ram_dosyasi.name = getattr(msg.audio, "file_name", "muzik.mp3")
    elif msg.video_note: ram_dosyasi.name = "yuvarlak_video.mp4"
    elif msg.document: ram_dosyasi.name = getattr(msg.document, "file_name", "belge.file")
    else: ram_dosyasi.name = "dosya.dat"
    return ram_dosyasi

KOMUT_BILGILERI = {
    "admin": {"isim": "Admin", "komutlar": {}},
    "eğlence": {"isim": "Eğlence", "komutlar": {}}
}

def komut_ekle(kategori, komut_adi, aciklama, kullanim):
    """Eklentilerdeki komutları merkezi bir yardım menüsüne kaydeder."""
    kategori_anahtar = kategori.lower()
    if kategori_anahtar not in KOMUT_BILGILERI:
        KOMUT_BILGILERI[kategori_anahtar] = {"isim": kategori, "komutlar": {}}
        
    KOMUT_BILGILERI[kategori_anahtar]["komutlar"][komut_adi.lower()] = {
        "aciklama": aciklama,
        "kullanim": kullanim
    }

def komut_sil(komut_adi):
    """KOMUT_BILGILERI sözlüğünden belirtilen komutu kaldırır."""
    komut_low = komut_adi.lower().strip()
    for kat_key, kat_val in list(KOMUT_BILGILERI.items()):
        if "komutlar" in kat_val:
            for c_name in list(kat_val["komutlar"].keys()):
                if c_name == komut_low or c_name == f"custom_{komut_low}":
                    del kat_val["komutlar"][c_name]

DB_FILE = "ayarlar.json"

def db_yukle():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

from datetime import datetime

BULUT_DB_ETIKET = "#GAGARAGOGO_TEK_BULUT_DB"
BULUT_DB_UYARI_BASLIK = (
    "⚠️⚠️⚠️ <b>DİKKAT: BU MESAJI ASLA SİLMEYİN!</b> ⚠️⚠️⚠️\n\n"
    "📌 Bu mesaj <b>GagaraGogo Userbot</b>'un tüm sistem ayarlarını, admin grubunu, forum konularını ve TikTok takip verilerini barındıran <b>TEK BULUT VERİTABANIDIR</b>.\n\n"
    "🔒 Sunucunuz kapansa, yeniden kurulsa veya dosyalarınız silinse bile botunuz her şeyi bu mesajdan okuyarak hatasız çalışmaya devam eder ve <b>asla mükerrer grup açmaz</b>.\n\n"
    "🚫 <i>Lütfen bu mesajı SİLMEYİN, İÇERİĞİNİ DEĞİŞTİRMEYİN! (Bot güncellemeleri bu mesajı silmeden doğrudan düzenleyerek üzerine yazar.)</i>\n"
    "──────────────────────────────\n"
    f"{BULUT_DB_ETIKET}\n\n"
)

async def tek_bulut_db_guncelle(client=None):
    """Tüm verileri (Grup ID, ayarlar, TikTok takipleri) Telegram Kayıtlı Mesajlar'daki TEK mesaja edit ile yazar. Asla silmez."""
    c = client or bot_client
    if not c:
        return
    try:
        from pyrogram.enums import ParseMode
        admin_id = get_yedek_grup_id()
        ayarlar_data = db_yukle()
        
        # TikTok takip veritabanını da dahil et
        tiktok_data = {}
        if os.path.exists("tiktok_takip.json"):
            try:
                with open("tiktok_takip.json", "r", encoding="utf-8") as f:
                    tiktok_data = json.load(f)
            except: pass
            
        # Otomesaj veritabanını da dahil et
        otomesaj_data = {}
        if os.path.exists("otomesaj.json"):
            try:
                with open("otomesaj.json", "r", encoding="utf-8") as f:
                    otomesaj_data = json.load(f)
            except: pass

        # Özel eklenti (Custom plugins) veritabanını da dahil et
        custom_plugins_data = {}
        if os.path.exists("custom_plugins.json"):
            try:
                with open("custom_plugins.json", "r", encoding="utf-8") as f:
                    custom_plugins_data = json.load(f)
            except: pass

        full_payload = {
            "admin_grup_id": admin_id,
            "ayarlar": ayarlar_data,
            "tiktok_takip": tiktok_data,
            "otomesaj": otomesaj_data,
            "custom_plugins": custom_plugins_data,
            "son_guncelleme": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        json_str = json.dumps(full_payload, ensure_ascii=False, indent=2)
        tam_metin = f"{BULUT_DB_UYARI_BASLIK}<pre>{json_str}</pre>"
        
        # Kayıtlı Mesajlar'da (me) mevcut bulut mesajını ara
        mevcut_mesaj = None
        async for m in c.search_messages("me", query=BULUT_DB_ETIKET, limit=1):
            mevcut_mesaj = m
            break
            
        # Eğer bulunamadıysa eski etiketlere de bakıp dönüştür
        if not mevcut_mesaj:
            async for m in c.search_messages("me", query="#GAGARAGOGO_ADMIN_DB", limit=1):
                mevcut_mesaj = m
                break
                
        if mevcut_mesaj:
            # MESAJI ASLA SİLME, SADECE DÜZENLE (EDIT)!
            try:
                await mevcut_mesaj.edit_text(tam_metin, parse_mode=ParseMode.HTML)
            except Exception as edit_err:
                if "MESSAGE_NOT_MODIFIED" not in str(edit_err):
                    print(f"Bulut DB düzenleme uyarısı: {edit_err}")
        else:
            # İlk defa kuruluyorsa 1 kez oluştur
            await c.send_message("me", tam_metin, parse_mode=ParseMode.HTML)
            
    except Exception as e:
        print(f"Tek bulut db güncelleme hatası: {e}")

async def tek_bulut_db_yukle(client=None):
    """Telegram Kayıtlı Mesajlar'daki TEK bulut mesajından tüm ayarları, grup ID'sini ve TikTok verilerini çeker."""
    c = client or bot_client
    if not c:
        return None
    try:
        mevcut_mesaj = None
        async for m in c.search_messages("me", query=BULUT_DB_ETIKET, limit=1):
            mevcut_mesaj = m
            break
            
        if not mevcut_mesaj:
            async for m in c.search_messages("me", query="#GAGARAGOGO_ADMIN_DB", limit=1):
                mevcut_mesaj = m
                break
                
        if not mevcut_mesaj:
            return None
            
        text_content = mevcut_mesaj.text or mevcut_mesaj.caption or ""
        start_idx = text_content.find("{")
        end_idx = text_content.rfind("}")
        
        if start_idx != -1 and end_idx != -1:
            raw_json = text_content[start_idx:end_idx+1]
            try:
                data = json.loads(raw_json)
                
                admin_id = data.get("admin_grup_id")
                ayarlar = data.get("ayarlar", {})
                tiktok_takip = data.get("tiktok_takip", {})
                
                # Ayarları diske yaz
                if ayarlar:
                    with open(DB_FILE, "w", encoding="utf-8") as f:
                        json.dump(ayarlar, f, ensure_ascii=False, indent=4)
                    
                    # Eğer bulutta kayıtlı tiktok_cookie varsa tiktok_cookies.txt dosyasına yaz
                    saved_tt_cookie = ayarlar.get("tiktok_cookie")
                    if saved_tt_cookie:
                        try:
                            with open("tiktok_cookies.txt", "w", encoding="utf-8") as cf:
                                cf.write(saved_tt_cookie)
                        except Exception:
                            pass
                        
                if admin_id and admin_id != 0:
                    ayar_kaydet("YEDEK_GRUP_ID", admin_id)
                    
                # TikTok takip dosyasını diske yaz
                if tiktok_takip:
                    with open("tiktok_takip.json", "w", encoding="utf-8") as f:
                        json.dump(tiktok_takip, f, ensure_ascii=False, indent=4)
                        
                # Otomesaj dosyasını diske yaz
                otomesaj_data = data.get("otomesaj", {})
                if otomesaj_data:
                    with open("otomesaj.json", "w", encoding="utf-8") as f:
                        json.dump(otomesaj_data, f, ensure_ascii=False, indent=4)
                
                # Özel eklentiler verisini diske yaz ve eksikse Kayıtlı Mesajlar'dan indir
                custom_plugins_data = data.get("custom_plugins", {})
                if custom_plugins_data:
                    with open("custom_plugins.json", "w", encoding="utf-8") as f:
                        json.dump(custom_plugins_data, f, ensure_ascii=False, indent=4)
                    
                    if c:
                        for p_name, p_info in custom_plugins_data.items():
                            dosya_adi = p_info.get("dosya_adi")
                            if dosya_adi:
                                hedef_yol = os.path.join("plugins", dosya_adi)
                                if not os.path.exists(hedef_yol):
                                    yedek_id = p_info.get("yedek_msg_id")
                                    if yedek_id:
                                        try:
                                            msg = await c.get_messages("me", message_ids=yedek_id)
                                            if msg and msg.document:
                                                await c.download_media(msg, file_name=hedef_yol)
                                                print(f"📦 Özel eklenti Kayıtlı Mesajlar'dan başarıyla kurtarıldı: {dosya_adi}")
                                        except Exception as kurtar_hata:
                                            print(f"Eklenti kurtarma hatası ({dosya_adi}): {kurtar_hata}")
                        
                print("✅ Tek Bulut Veritabanı Telegram Kayıtlı Mesajlar'dan başarıyla yüklendi!")
                return admin_id
            except json.JSONDecodeError:
                pass
        
        # Eski format regex kontrolü
        import re
        found_id = re.search(r"ID:\s*`?(-?\d+)`?", text_content)
        if found_id:
            cand_id = int(found_id.group(1))
            ayar_kaydet("YEDEK_GRUP_ID", cand_id)
            return cand_id
    except Exception as e:
        print(f"Tek bulut db yükleme hatası: {e}")
    return None

# Geriye dönük uyumluluk takma adları
async def bulut_db_kaydet(data=None):
    await tek_bulut_db_guncelle()

async def bulut_db_baslangic_yukle(client=None):
    await tek_bulut_db_yukle(client)

async def create_forum_topic_helper(client, chat_id, title):
    try:
        from pyrogram.raw.functions.channels import CreateForumTopic
        import random
        peer = await client.resolve_peer(chat_id)
        res = await client.invoke(
            CreateForumTopic(
                channel=peer,
                title=title,
                random_id=random.randint(1, 2147483647)
            )
        )
        for update in res.updates:
            if hasattr(update, "message") and hasattr(update.message, "id"):
                return update.message.id
    except Exception as e:
        if "CHANNEL_FORUM_MISSING" in str(e):
            logging.info(f"ℹ️ Grupta ({chat_id}) 'Konular' (Forum) özelliği kapalı olduğu için '{title}' konusu açılamadı. Mesajlar doğrudan ana gruba aktarılacak.")
        else:
            logging.warning(f"CreateForumTopic ({title}) uyarısı: {e}")
    return None

async def otomatik_admin_grubu_olusturucu(client, zorla_yeni=False):
    """Admin grubu yoksa otomatik olarak Forum özellikli Süpergroup oluşturur ve yapılandırır."""
    from pyrogram.raw.functions.channels import CreateChannel, ToggleForum
    from pyrogram.types import ChatPrivileges
    
    # 1. Telegram Kayıtlı Mesajlar'daki Tek Bulut DB'yi kontrol et
    if not zorla_yeni:
        cand_id = await tek_bulut_db_yukle(client)
        if cand_id and cand_id != 0:
            try:
                chat = await client.get_chat(cand_id)
                if chat:
                    logging.info(f"✅ Daha önce oluşturulmuş Admin Grubu Telegram Tek Bulut DB'den bulundu: {cand_id}")
                    return cand_id
            except Exception:
                pass

    current_id = get_yedek_grup_id()
    if not zorla_yeni and current_id != 0:
        try:
            chat = await client.get_chat(current_id)
            if chat:
                return current_id
        except Exception:
            logging.warning(f"Mevcut admin grubuna ({current_id}) erişilemedi...")

    logging.info("🚀 Yeni Admin Grubu oluşturuluyor...")
    try:
        res = await client.invoke(
            CreateChannel(
                title="GagaraGogo Admin & Arşiv",
                about="GagaraGogo Userbot Otomatik Yönetim, Log ve Arşiv Paneli",
                megagroup=True,
                forum=True
            )
        )
        created_chat = res.chats[0]
        chat_id = int(f"-100{created_chat.id}")
        
        # Forum özelliğini aç ve teyit et
        try:
            peer = await client.resolve_peer(chat_id)
            await client.invoke(ToggleForum(channel=peer, enabled=True))
        except Exception:
            pass
            
        await grubu_yapilandir_ve_hazirla(client, chat_id)
        logging.info(f"✅ Otomatik Admin Grubu başarıyla kuruldu ve yapılandırıldı! ID: {chat_id}")
        return chat_id
    except Exception as e:
        logging.error(f"Otomatik admin grubu oluşturma hatası: {e}")
        return None

async def grubu_yapilandir_ve_hazirla(client, chat_id):
    """Verilen süper grubu ana admin grubu olarak yapılandırır: Forum açar, botu yönetici yapar, konuları açar ve karşılama mesajını sabitler."""
    from pyrogram.raw.functions.channels import ToggleForum
    from pyrogram.types import ChatPrivileges
    from pyrogram.enums import ParseMode

    # 1. Eski ID kontrolü ve yeni ID'yi kaydet
    eski_grup_id = ayar_getir("YEDEK_GRUP_ID")
    grup_degisti = (str(eski_grup_id) != str(chat_id))
    ayar_kaydet("YEDEK_GRUP_ID", chat_id)

    # 2. Forum özelliğini açmayı dene
    try:
        peer = await client.resolve_peer(chat_id)
        await client.invoke(ToggleForum(channel=peer, enabled=True))
    except Exception:
        pass

    # 3. Yardımcı botu ekle ve yönetici yap
    if YARDIMCI_BOT_USERNAME:
        try:
            await client.add_chat_members(chat_id, YARDIMCI_BOT_USERNAME)
        except Exception:
            pass
        try:
            await client.promote_chat_member(
                chat_id, 
                YARDIMCI_BOT_USERNAME,
                privileges=ChatPrivileges(
                    can_manage_chat=True,
                    can_delete_messages=True,
                    can_manage_video_chats=True,
                    can_restrict_members=True,
                    can_promote_members=True,
                    can_change_info=True,
                    can_post_messages=True,
                    can_edit_messages=True,
                    can_invite_users=True,
                    can_pin_messages=True
                )
            )
            logging.info(f"✅ Yardımcı bot (@{YARDIMCI_BOT_USERNAME}) gruba eklendi/yönetici yapıldı.")
        except Exception as bot_err:
            logging.warning(f"Yardımcı bot yetkilendirme uyarısı: {bot_err}")

    # 4. Otomatik Forum Konularını Aç (Grup değiştiyse eski ID'leri yok say ve yeni konular aç)
    log_topic = None if grup_degisti else ayar_getir("log_topic_id")
    if not log_topic:
        log_topic = await create_forum_topic_helper(client, chat_id, "🛠 Sistem Logları")
        if log_topic: ayar_kaydet("log_topic_id", log_topic)

    silinen_topic = None if grup_degisti else ayar_getir("antidelete_topic_id")
    if not silinen_topic:
        silinen_topic = await create_forum_topic_helper(client, chat_id, "🗑 Silinen Mesajlar")
        if silinen_topic: ayar_kaydet("antidelete_topic_id", silinen_topic)

    sureli_topic = None if grup_degisti else ayar_getir("sureli_topic_id")
    if not sureli_topic:
        sureli_topic = await create_forum_topic_helper(client, chat_id, "⏳ Süreli Medyalar")
        if sureli_topic: ayar_kaydet("sureli_topic_id", sureli_topic)

    # 5. General / Ana Konuya bilgilendirme mesajı gönder ve sabitle (pin)
    genel_mesaj = (
        "🚀 <b>GagaraGogo Userbot Kullanıma Hazır!</b>\n\n"
        "Bu grup, botunuz için oluşturulmuş / bağlanmış <b>Ana Yönetim, Log ve Arşiv Paneli</b>dir.\n\n"
        "⚠️⚠️⚠️ <b>DİKKAT: BU GRUBU ASLA SİLMEYİN VE AYRILMAYIN!</b> ⚠️⚠️⚠️\n"
        "• Bu grup botunuzun ana çalışma merkezidir.\n"
        "• Sunucunuz yeniden başlasa bile botunuz bu grubu hatırlar ve buraya bağlı kalır.\n"
        "• Grubu silerseniz veya ayrılırsanız loglar, silinen mesajlar ve gönderi arşivleri hedefsiz kalır!\n\n"
        "📌 <b>Oluşturulan Otomatik Konular:</b>\n"
        "• <b>🛠 Sistem Logları:</b> Sistem hata raporları ve çalışma logları buraya gelir.\n"
        "• <b>🗑 Silinen Mesajlar:</b> Özel sohbetlerde (DM) silinen mesajlar buraya arşivlenir.\n"
        "• <b>⏳ Süreli Medyalar:</b> Tek gösterimlik fotoğraf/videolar kalıcı olarak buraya kaydedilir.\n"
        "• <b>TikTok Yayınları & Gönderileri:</b> Takip ettiğiniz kullanıcılar için otomatik özel konular açılır.\n\n"
        "💡 <b>Hızlı Komutlar:</b>\n"
        "• <code>.yardim</code> — Butonlu interaktif yardım menüsünü açar.\n"
        "• <code>.durum</code> — Sunucu donanım durumunu (CPU, RAM, Disk, Uptime) gösterir.\n\n"
        f"🆔 <b>Grup ID:</b> <code>{chat_id}</code>"
    )

    pin_basarili = False
    try:
        # Forum süpergruplarında General konusu id=1'dir
        msg = await client.send_message(chat_id, genel_mesaj, reply_to_message_id=1, parse_mode=ParseMode.HTML)
        await msg.pin(both_sides=True)
        pin_basarili = True
    except Exception:
        pass

    if not pin_basarili:
        try:
            msg = await client.send_message(chat_id, genel_mesaj, parse_mode=ParseMode.HTML)
            await msg.pin(both_sides=True)
        except Exception as pin_err:
            logging.warning(f"Genel konu mesaj pinleme uyarısı: {pin_err}")

    # 6. Telegram Kayıtlı Mesajlar'daki TEK bulut veritabanını güncelle
    await tek_bulut_db_guncelle(client)
    return True

def db_kaydet(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(bulut_db_kaydet(data))
    except: pass

def ayar_getir(key, default_value=None):
    db = db_yukle()
    return db.get(key, default_value)

def ayar_kaydet(key, value):
    db = db_yukle()
    db[key] = value
    db_kaydet(db)

# Eski uyumluluk için varsayılan değişkenler
YEDEK_GRUP_ID = get_yedek_grup_id()

RESTART_BILGI_DOSYASI = ".restart_bilgisi.json"

def restart_bildirimi_kaydet(action="restart", inline_message_id=None, chat_id=None, message_id=None, eski_commit=None, yeni_commit=None):
    """Yeniden başlatma/güncelleme öncesi hedef mesaj bilgilerini geçici dosyaya kaydeder."""
    import json, time
    data = {
        "action": action,
        "inline_message_id": inline_message_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "eski_commit": eski_commit,
        "yeni_commit": yeni_commit,
        "time": time.time()
    }
    try:
        with open(RESTART_BILGI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logging.warning(f"Restart bilgisi kaydedilemedi: {e}")

async def restart_bildirimi_isle(user_app, bot_app=None):
    """Bot başlatıldığında yarım kalan yeniden başlatma/güncelleme mesajını 'kullanıma hazır' olarak günceller."""
    import json, os, time
    if not os.path.exists(RESTART_BILGI_DOSYASI):
        return
        
    try:
        with open(RESTART_BILGI_DOSYASI, "r", encoding="utf-8") as f:
            data = json.load(f)
        os.remove(RESTART_BILGI_DOSYASI)
    except Exception as e:
        logging.warning(f"Restart bilgisi okunamadı: {e}")
        return

    # 10 dakikadan eski kalmışsa güncelleme yapma
    if time.time() - data.get("time", 0) > 600:
        return

    action = data.get("action", "restart")
    inline_message_id = data.get("inline_message_id")
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    yeni_commit = data.get("yeni_commit")

    if not yeni_commit:
        import subprocess
        try:
            yeni_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        except Exception:
            yeni_commit = "v2.6"

    if action == "update":
        metin = (
            "✅ <b>Gagaragogo Userbot Başarıyla Güncellendi!</b>\n"
            "────────────────────────\n"
            f"📌 <b>Aktif Sürüm:</b> <code>{yeni_commit} (Son Sürüm)</code>\n\n"
            "🚀 <i>Tüm sistemler ve eklentiler yüklendi, botunuz kullanıma hazır!</i>"
        )
    else:
        metin = (
            "✅ <b>Gagaragogo Userbot Başarıyla Başlatıldı!</b>\n"
            "────────────────────────\n"
            f"📌 <b>Aktif Sürüm:</b> <code>{yeni_commit}</code>\n\n"
            "🚀 <i>Yeniden başlatma tamamlandı, botunuz kullanıma hazır!</i>"
        )

    # 1. Inline mesaj güncelleme (yardım / ayarlar menüsü üzerinden inline query olarak açılmışsa)
    if inline_message_id and bot_app:
        try:
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu"),
                    InlineKeyboardButton("⚙️ Ayarlar", callback_data="ayarlar_menu")
                ],
                [InlineKeyboardButton("❌ Kapat", callback_data="yardim_close")]
            ])
            try:
                await bot_app.edit_inline_text(inline_message_id, text=metin, reply_markup=kb)
            except Exception:
                await bot_app.edit_inline_caption(inline_message_id, caption=metin, reply_markup=kb)
            logging.info("✅ [RESTART] Inline durum mesajı başarıyla güncellendi.")
            return
        except Exception as e:
            logging.warning(f"⚠️ [RESTART] Inline mesaj güncellenemedi: {e}")

    # 2. Normal sohbet mesajı güncelleme (.restart / .update now mesajı veya bota direkt yazılan mesaj)
    if chat_id and message_id:
        try:
            await user_app.edit_message_text(chat_id, message_id, metin)
            logging.info("✅ [RESTART] Kullanıcı sohbet mesajı başarıyla güncellendi.")
            return
        except Exception:
            if bot_app:
                try:
                    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")]
                    ])
                    await bot_app.edit_message_text(chat_id, message_id, metin, reply_markup=kb)
                    logging.info("✅ [RESTART] Yardımcı bot sohbet mesajını güncelledi.")
                    return
                except Exception:
                    pass

DEFAULT_ALIVE_LOGO = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1000"

def get_alive_logo():
    """Kullanıcının özel olarak ayarladığı veya varsayılan alive afiş görselini döndürür."""
    return ayar_getir("alive_logo", DEFAULT_ALIVE_LOGO)

def progress_bar(percent, length=10):
    """Verilen yüzdeye göre modern blok ilerleme çubuğu oluşturur. Örn: [████░░░░░░]"""
    try:
        val = float(percent)
    except:
        val = 0.0
    dolu = int(round((val / 100) * length))
    dolu = max(0, min(length, dolu))
    bos = length - dolu
    return f"[{'█' * dolu}{'░' * bos}]"

def upload_image_to_cloud(file_path):
    """
    Yerel bir görseli birden fazla güvenilir bulut sağlayıcısına sırayla yükler.
    (Catbox, Uguu, Tmpfiles, Litterbox)
    Başarılı olursa doğrudan erişilebilir HTTPS linkini döndürür.
    """
    import httpx
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    filename = os.path.basename(file_path)
    if not "." in filename:
        filename += ".jpg"

    # 1. Catbox.moe
    try:
        with open(file_path, "rb") as f:
            r = httpx.post(
                "https://catbox.moe/user/api.php",
                headers=headers,
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (filename, f)},
                timeout=15
            )
            if r.status_code == 200 and r.text.strip().startswith("http"):
                logging.info(f"✅ Görsel Catbox'a yüklendi: {r.text.strip()}")
                return r.text.strip()
    except Exception as e:
        logging.warning(f"Catbox yükleme uyarısı: {e}")

    # 2. Uguu.se
    try:
        with open(file_path, "rb") as f:
            r = httpx.post(
                "https://uguu.se/upload",
                headers=headers,
                files={"files[]": (filename, f)},
                timeout=15
            )
            if r.status_code == 200:
                js = r.json()
                if js.get("success") and js.get("files"):
                    url = js["files"][0]["url"]
                    logging.info(f"✅ Görsel Uguu'ya yüklendi: {url}")
                    return url
    except Exception as e:
        logging.warning(f"Uguu yükleme uyarısı: {e}")

    # 3. Tmpfiles.org
    try:
        with open(file_path, "rb") as f:
            r = httpx.post(
                "https://tmpfiles.org/api/v1/upload",
                headers=headers,
                files={"file": (filename, f)},
                timeout=15
            )
            if r.status_code == 200:
                js = r.json()
                raw_url = js.get("data", {}).get("url", "")
                if raw_url:
                    direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                    logging.info(f"✅ Görsel Tmpfiles'a yüklendi: {direct_url}")
                    return direct_url
    except Exception as e:
        logging.warning(f"Tmpfiles yükleme uyarısı: {e}")

    # 4. Litterbox (Catbox geçici depolama)
    try:
        with open(file_path, "rb") as f:
            r = httpx.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                headers=headers,
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": (filename, f)},
                timeout=15
            )
            if r.status_code == 200 and r.text.strip().startswith("http"):
                logging.info(f"✅ Görsel Litterbox'a yüklendi: {r.text.strip()}")
                return r.text.strip()
    except Exception as e:
        logging.warning(f"Litterbox yükleme uyarısı: {e}")

    return None


# =============================================================================
# GAGARAGOGO CORE FRAMEWORK & DECORATOR ENGINE
# Telif Hakkı (c) 2026 chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# =============================================================================

class GgrEngine:
    """
    GagaraGogo Userbot Core Framework Engine
    Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
    License: MIT License
    """
    __signature__ = "ggr-engine-v2.6-chaolcam"
    __fingerprint__ = "chaolcam-gagaragogo-telegram-framework"
    __author__ = "chaolcam"

    @staticmethod
    def cmd(command, info="GagaraGogo Komutu", usage=None, category="Genel", group=0, allow_all=False, filter=None):
        """GagaraGogo Userbot core command decorator.
        Registers command metadata in KOMUT_BILGILERI and binds Pyrogram on_message handler.
        """
        from pyrogram import Client, filters
        if isinstance(command, str):
            commands = [command]
            main_cmd = command
        else:
            commands = list(command)
            main_cmd = commands[0]
            
        use_str = usage or f".{main_cmd}"
        komut_ekle(category, main_cmd, info, use_str)
        
        flt = filters.command(commands, prefixes=[".", "!", "/"])
        if not allow_all:
            flt = flt & filters.me
        if filter is not None:
            flt = flt & filter
        return Client.on_message(flt, group=group)

    @staticmethod
    def on(custom_filters=None, group=0):
        """Decorator for custom message filters on Client."""
        from pyrogram import Client
        if custom_filters is None:
            return Client.on_message(group=group)
        return Client.on_message(custom_filters, group=group)

    @staticmethod
    def callback(regex_pattern=None, group=0):
        """Decorator for inline callback query buttons."""
        from pyrogram import Client, filters
        flt = filters.regex(regex_pattern) if regex_pattern else None
        return Client.on_callback_query(flt, group=group)

    @property
    def client(self):
        return bot_client

    @staticmethod
    def get(key, default=None):
        return ayar_getir(key, default)

    @staticmethod
    def set(key, value):
        return ayar_kaydet(key, value)

    @staticmethod
    def bar(percent, length=10):
        return progress_bar(percent, length)

    @staticmethod
    async def sync_cloud(client=None):
        return await tek_bulut_db_guncelle(client)

    @staticmethod
    def backup_chat_id():
        return get_yedek_grup_id()

    @staticmethod
    async def log(text):
        return await tlog(text)

    @staticmethod
    def safe_html(text):
        return guvenli_isim(text)

    @staticmethod
    def format_file(msg, ram_io):
        return ram_dosyasini_isimlendir(msg, ram_io)

    @staticmethod
    def remove_cmd(command_name):
        return komut_sil(command_name)

# Global framework instance & distinctive aliases
ggr = GgrEngine()
ggr_commands = KOMUT_BILGILERI
ggr_config = ayar_getir
ggr_save_config = ayar_kaydet
ggr_cloud_tag = BULUT_DB_ETIKET
ggr_db_file = DB_FILE
ggr_progress = progress_bar
