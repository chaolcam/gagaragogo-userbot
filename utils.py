# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Core Utilities & Helper Functions
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import sys
import time
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
    if not kategori:
        return
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

# Core modülünden veritabanı, önbellekleme ve ağ bileşenlerini içe aktar (Geriye dönük uyumluluk)
from core.cache import (
    EntityCache,
    cached_get_chat,
    cached_get_users,
    USER_CACHE,
    CHAT_CACHE,
    ADMIN_PERM_CACHE,
)
from core.network import safe_api_call
from core.database import (
    tek_bulut_db_yukle,
    tek_bulut_db_guncelle,
    db_yukle,
    db_kaydet,
    ayar_getir,
    ayar_kaydet,
    BULUT_DB_ETIKET,
    BULUT_DB_DOSYA_ADI,
    DB_FILE,
)
from core.decorators import ggr_cmd

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
            logging.info("ℹ️ Grupta (%s) 'Konular' (Forum) özelliği kapalı olduğu için '%s' konusu açılamadı. Mesajlar doğrudan ana gruba aktarılacak.", chat_id, title)
        else:
            logging.warning("CreateForumTopic (%s) uyarısı: %s", title, e)
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
                    logging.info("✅ Daha önce oluşturulmuş Admin Grubu Telegram Tek Bulut DB'den bulundu: %s", cand_id)
                    return cand_id
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)

    current_id = get_yedek_grup_id()
    if not zorla_yeni and current_id != 0:
        try:
            chat = await client.get_chat(current_id)
            if chat:
                return current_id
        except Exception:
            logging.warning("Mevcut admin grubuna (%s) erişilemedi...", current_id)

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
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)
            
        await grubu_yapilandir_ve_hazirla(client, chat_id)
        logging.info("✅ Otomatik Admin Grubu başarıyla kuruldu ve yapılandırıldı! ID: %s", chat_id)
        return chat_id
    except Exception as e:
        logging.error("Otomatik admin grubu oluşturma hatası: %s", e)
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
    except Exception as _exc:
        logging.debug("Suppressed: %s", _exc)

    # 3. Yardımcı botu ekle ve yönetici yap
    if YARDIMCI_BOT_USERNAME:
        try:
            await client.add_chat_members(chat_id, YARDIMCI_BOT_USERNAME)
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)
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
            logging.info("✅ Yardımcı bot (@%s) gruba eklendi/yönetici yapıldı.", YARDIMCI_BOT_USERNAME)
        except Exception as bot_err:
            logging.warning("Yardımcı bot yetkilendirme uyarısı: %s", bot_err)

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
    except Exception as _exc:
        logging.debug("Suppressed: %s", _exc)

    if not pin_basarili:
        try:
            msg = await client.send_message(chat_id, genel_mesaj, parse_mode=ParseMode.HTML)
            await msg.pin(both_sides=True)
        except Exception as pin_err:
            logging.warning("Genel konu mesaj pinleme uyarısı: %s", pin_err)

    # 6. Telegram Kayıtlı Mesajlar'daki TEK bulut veritabanını güncelle
    await tek_bulut_db_guncelle(client)
    return True

def db_kaydet(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(bulut_db_kaydet(data))
    except Exception as _b_err:
        logging.debug("bulut_db_kaydet başlatılamadı: %s", _b_err)

def ayar_getir(key, default_value=None):
    db = db_yukle()
    return db.get(key, default_value)

def ayar_kaydet(key, value):
    db = db_yukle()
    db[key] = value
    db_kaydet(db)

# =============================================================================
# CLOUDFLARE GUARD (GİZLİ DEPLOY & KULLANIM KARA LİSTESİ)
# =============================================================================
CLOUD_GUARD_URL = "https://morning-cake-f2f0.emre252687.workers.dev"
_GUARD_CACHE = {}  # {user_id: (is_banned, reason, timestamp)}

def check_cloud_blacklist(user_id: int):
    """
    Cloudflare Worker üzerinden kullanıcının deploy veya bot kullanım yetkisini doğrular.
    (is_banned: bool, reason: str) döner.
    """
    if not user_id:
        return False, None
    
    uid = int(user_id)
    now = time.time()
    
    # 5 dakikalık önbellek (her mesaja tekrar Cloudflare'a istek atıp yavaşlatmasın)
    if uid in _GUARD_CACHE:
        banned, reason, ts = _GUARD_CACHE[uid]
        if now - ts < 300:
            return banned, reason

    try:
        import httpx
        r = httpx.get(f"{CLOUD_GUARD_URL}?id={uid}", timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            if not data.get("allowed", True):
                reason = data.get("reason", "Geliştirici tarafından kara listeye alınmıştır.")
                _GUARD_CACHE[uid] = (True, reason, now)
                return True, reason
            else:
                _GUARD_CACHE[uid] = (False, None, now)
                return False, None
    except Exception as e:
        logging.debug("Cloud Guard kontrol hatası: %s", e)
        
    return False, None

def is_blacklisted(user_id: int) -> bool:
    """Verilen user_id'nin kara listede olup olmadığını kontrol eder."""
    if not user_id:
        return False
    banned, _ = check_cloud_blacklist(user_id)
    return banned

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
        logging.warning("Restart bilgisi kaydedilemedi: %s", e)

def _build_restart_message(action, yeni_commit):
    """Yeniden başlatma veya güncelleme durum bildirim metnini oluşturur."""
    if action == "update":
        return (
            "✅ <b>Gagaragogo Userbot Başarıyla Güncellendi!</b>\n"
            "────────────────────────\n"
            f"📌 <b>Aktif Sürüm:</b> <code>{yeni_commit} (Son Sürüm)</code>\n\n"
            "🚀 <i>Tüm sistemler ve eklentiler yüklendi, botunuz kullanıma hazır!</i>"
        )
    return (
        "✅ <b>Gagaragogo Userbot Başarıyla Başlatıldı!</b>\n"
        "────────────────────────\n"
        f"📌 <b>Aktif Sürüm:</b> <code>{yeni_commit}</code>\n\n"
        "🚀 <i>Yeniden başlatma tamamlandı, botunuz kullanıma hazır!</i>"
    )

async def _update_restart_inline(bot_app, inline_message_id, metin):
    """Inline mesaj üzerinden durum güncellemesi yapar."""
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
        return True
    except Exception as e:
        logging.warning("⚠️ [RESTART] Inline mesaj güncellenemedi: %s", e)
        return False

async def _update_restart_chat(user_app, bot_app, chat_id, message_id, metin):
    """Normal sohbet mesajı üzerinden durum güncellemesi yapar."""
    try:
        await user_app.edit_message_text(chat_id, message_id, metin)
        logging.info("✅ [RESTART] Kullanıcı sohbet mesajı başarıyla güncellendi.")
        return True
    except Exception:
        if bot_app:
            try:
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")]
                ])
                await bot_app.edit_message_text(chat_id, message_id, metin, reply_markup=kb)
                logging.info("✅ [RESTART] Yardımcı bot sohbet mesajını güncelledi.")
                return True
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)
    return False

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
        logging.warning("Restart bilgisi okunamadı: %s", e)
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
        except Exception as _git_err:
            logging.debug("Git commit alınamadı: %s", _git_err)
            yeni_commit = "v2.6"

    metin = _build_restart_message(action, yeni_commit)

    # 1. Inline mesaj güncelleme
    if inline_message_id and bot_app:
        if await _update_restart_inline(bot_app, inline_message_id, metin):
            return

    # 2. Normal sohbet mesajı güncelleme
    if chat_id and message_id:
        await _update_restart_chat(user_app, bot_app, chat_id, message_id, metin)

DEFAULT_ALIVE_LOGO = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1000"

def get_alive_logo():
    """Kullanıcının özel olarak ayarladığı veya varsayılan alive afiş görselini döndürür."""
    return ayar_getir("alive_logo", DEFAULT_ALIVE_LOGO)

def progress_bar(percent, length=10):
    """Verilen yüzdeye göre modern blok ilerleme çubuğu oluşturur. Örn: [████░░░░░░]"""
    try:
        val = float(percent)
    except Exception:
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
                logging.info("✅ Görsel Catbox'a yüklendi: %s", r.text.strip())
                return r.text.strip()
    except Exception as e:
        logging.warning("Catbox yükleme uyarısı: %s", e)

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
                    logging.info("✅ Görsel Uguu'ya yüklendi: %s", url)
                    return url
    except Exception as e:
        logging.warning("Uguu yükleme uyarısı: %s", e)

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
                    logging.info("✅ Görsel Tmpfiles'a yüklendi: %s", direct_url)
                    return direct_url
    except Exception as e:
        logging.warning("Tmpfiles yükleme uyarısı: %s", e)

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
                logging.info("✅ Görsel Litterbox'a yüklendi: %s", r.text.strip())
                return r.text.strip()
    except Exception as e:
        logging.warning("Litterbox yükleme uyarısı: %s", e)

    return None


# =============================================================================
# GAGARAGOGO CORE FRAMEWORK & DECORATOR ENGINE
# Telif Hakkı (c) 2026 chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# =============================================================================

class GgrEngine:
    """
    GagaraGogo Userbot Core Framework Engine
    Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
    License: GNU GPL v3.0
    """
    __signature__ = "ggr-engine-v2.6-chaolcam"
    __fingerprint__ = "chaolcam-gagaragogo-telegram-framework"
    __author__ = "chaolcam"
    logger = logging.getLogger("ggr")

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
        if category:
            komut_ekle(category, main_cmd, info, use_str)
        
        flt = filters.command(commands, prefixes=["."])
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
    def t(key, lang=None, **kwargs):
        from core.locales import t as _loc_t
        return _loc_t(key, lang=lang, **kwargs)

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


async def send_inline_result_in_context(client, message, query_id: int, result_id: str, disable_notification: bool = None):
    """
    Inline bot sonucunu komutun verildiği sohbete ve konu (forum topic) varsa
    doğrudan o konunun içine gönderir (General/ana konuya kaçmasını kesin olarak önler).
    """
    from pyrogram import raw
    
    # Telegram ve Pyrogram forum / konu özniteliklerini eksiksiz tespit et
    reply_to_top = getattr(message, "reply_to_top_message_id", None)
    reply_to_msg = getattr(message, "reply_to_message_id", None)
    msg_thread = getattr(message, "message_thread_id", None)
    chat = getattr(message, "chat", None)
    is_forum = getattr(chat, "is_forum", False)
    is_topic = getattr(message, "topic_message", False) or getattr(message, "is_topic_message", False)

    # Konu / Thread ID belirleme:
    topic_id = reply_to_top or msg_thread
    if not topic_id and (is_forum or is_topic) and reply_to_msg:
        # Forumda doğrudan konuya yazılmışsa reply_to_msg konunun kök id'sidir
        topic_id = reply_to_msg

    # Hedef reply mesajı
    msg_id = getattr(message, "id", None)
    reply_target_id = msg_id or reply_to_msg or topic_id

    try:
        peer = await client.resolve_peer(message.chat.id)
    except Exception as e:
        logging.error("send_inline_result_in_context peer hatası: %s", e)
        return None

    # 1. Öncelik: Eğer forum konusu tespit edildiyse doğrudan konuya gönder
    if topic_id:
        # Deneme 1.1: Hem top_msg_id hem de reply_to_msg_id ile doğrudan konunun içine ve mesaja yanıt
        try:
            return await client.invoke(
                raw.functions.messages.SendInlineBotResult(
                    peer=peer,
                    query_id=query_id,
                    id=result_id,
                    random_id=client.rnd_id(),
                    silent=disable_notification or None,
                    reply_to_msg_id=reply_target_id,
                    top_msg_id=topic_id,
                )
            )
        except Exception as e1:
            logging.debug("SendInlineBotResult konu+mesaj denemesi: %s", e1)

        # Deneme 1.2: Konu kök mesajına yanıt olarak doğrudan konunun içine gönder
        try:
            return await client.invoke(
                raw.functions.messages.SendInlineBotResult(
                    peer=peer,
                    query_id=query_id,
                    id=result_id,
                    random_id=client.rnd_id(),
                    silent=disable_notification or None,
                    reply_to_msg_id=topic_id,
                    top_msg_id=topic_id,
                )
            )
        except Exception as e2:
            logging.debug("SendInlineBotResult konu kökü denemesi: %s", e2)

    # 2. Standart grup / özel sohbet veya genel gönderim
    try:
        return await client.invoke(
            raw.functions.messages.SendInlineBotResult(
                peer=peer,
                query_id=query_id,
                id=result_id,
                random_id=client.rnd_id(),
                silent=disable_notification or None,
                reply_to_msg_id=reply_target_id if not topic_id else topic_id,
                top_msg_id=topic_id,
            )
        )
    except Exception as e3:
        logging.warning("SendInlineBotResult MTProto hatası (%s), standart API'ye dönülüyor...", e3)
        fallback_reply = topic_id or reply_target_id
        return await client.send_inline_bot_result(
            message.chat.id,
            query_id,
            result_id,
            disable_notification=disable_notification,
            reply_to_message_id=fallback_reply
        )


def extract_sent_message_id(res):
    """SendInlineBotResult veya send_inline_bot_result dönüşünden gönderilen mesaj ID'sini ayıklar."""
    if not res:
        return None
    if hasattr(res, "id") and isinstance(res.id, int):
        return res.id
    if hasattr(res, "updates"):
        for u in res.updates:
            m = getattr(u, "message", None)
            if m and hasattr(m, "id") and isinstance(m.id, int):
                return m.id
            if hasattr(u, "id") and isinstance(u.id, int):
                return u.id
    return None
