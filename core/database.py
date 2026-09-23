# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Cloud JSON Database & State Persistence
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from pyrogram.enums import ParseMode
from pyrogram.types import InputMediaDocument

logger = logging.getLogger("ggr.database")

BULUT_DB_ETIKET = "#GAGARAGOGO_TEK_BULUT_DB"
BULUT_DB_DOSYA_ADI = "gagaragogo_bulut_db.json"

BULUT_DB_CAPTION = (
    "📁 <b>GagaraGogo Userbot - Kalıcı Bulut Veritabanı Dosyası</b>\n\n"
    "📌 <i>Bu dosya botun tüm ayarlarını, admin grubunu, forum konularını ve "
    "TikTok takiplerini barındıran TEK bulut veritabanıdır.</i>\n\n"
    "🔒 <b>DİKKAT:</b> Lütfen bu dosyayı silmeyin! Sunucunuz sıfırlansa dahi bot "
    "tüm durumunu bu dosyadan geri yükler.\n"
    "──────────────────────────────\n"
    f"{BULUT_DB_ETIKET}"
)

DB_FILE = "ayarlar.json"


def db_yukle() -> Dict[str, Any]:
    """Yerel ayarlar.json dosyasını yükler."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("ayarlar.json okuma hatası: %s", e)
    return {}


def db_kaydet(data: Dict[str, Any]) -> None:
    """Yerel ayarlar.json dosyasını yazar."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error("ayarlar.json yazma hatası: %s", e)


def ayar_getir(anahtar: str, varsayilan: Any = None) -> Any:
    return db_yukle().get(anahtar, varsayilan)


def ayar_kaydet(anahtar: str, deger: Any) -> None:
    data = db_yukle()
    data[anahtar] = deger
    db_kaydet(data)


def _safe_read_json(file_path: str, default_val: Any = None) -> Any:
    """Verilen JSON dosyasını güvenle okur, hata durumunda varsayılan değeri döner."""
    if not os.path.exists(file_path):
        return default_val if default_val is not None else {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as _read_err:
        logger.debug("%s okunamadı: %s", file_path, _read_err)
        return default_val if default_val is not None else {}


async def _find_cloud_db_messages(client):
    """Kayıtlı mesajlar içinden mevcut dosya ve eski text mesajını arar."""
    mevcut_dosya = None
    eski_text = None

    async for m in client.search_messages("me", query=BULUT_DB_ETIKET, limit=5):
        if m.document and m.document.file_name == BULUT_DB_DOSYA_ADI:
            mevcut_dosya = m
            break
        elif m.text and BULUT_DB_ETIKET in m.text and not eski_text:
            eski_text = m

    if not mevcut_dosya and not eski_text:
        async for m in client.search_messages("me", query="#GAGARAGOGO_ADMIN_DB", limit=1):
            if m.text:
                eski_text = m
                break

    return mevcut_dosya, eski_text


def _extract_json_from_text(ham_metin: str) -> Optional[dict]:
    """Eski metin tabanlı bulut yedeğinden JSON verisini ayrıştırır."""
    json_str = ""
    if "<pre>" in ham_metin and "</pre>" in ham_metin:
        json_str = ham_metin.split("<pre>")[1].split("</pre>")[0].strip()
    elif "{" in ham_metin and "}" in ham_metin:
        start = ham_metin.find("{")
        end = ham_metin.rfind("}") + 1
        json_str = ham_metin[start:end].strip()

    if json_str:
        try:
            return json.loads(json_str)
        except Exception as _json_err:
            logger.debug("Metin JSON ayrıştırma hatası: %s", _json_err)
    return None


async def _migrate_legacy_text_db(client, eski_text_mesaji) -> Optional[dict]:
    """Eski text mesajındaki JSON verisini dosyaya taşır (Migration)."""
    logger.info("🔄 Eski TEXT formatında Bulut DB bulundu. Birebir DOSYA formatına taşınıyor...")
    json_data = _extract_json_from_text(eski_text_mesaji.text or "")
    if not json_data:
        return None

    try:
        await _verileri_yerel_dosyalara_isle(json_data, client)

        dosya_akisi = io.BytesIO(json.dumps(json_data, ensure_ascii=False, indent=2).encode("utf-8"))
        dosya_akisi.name = BULUT_DB_DOSYA_ADI

        await client.send_document(
            chat_id="me",
            document=dosya_akisi,
            caption=BULUT_DB_CAPTION,
            parse_mode=ParseMode.HTML
        )

        goc_notu = (
            "✅ <b>GagaraGogo Bulut Veritabanı Başarıyla DOSYA Formatına Taşındı!</b>\n\n"
            "📌 <i>Tüm ayarlarınız, forum konularınız ve TikTok takipleriniz BİREBİR "
            f"<code>{BULUT_DB_DOSYA_ADI}</code> dosyasına aktarılmıştır.</i>\n\n"
            "ℹ️ Bu eski metin mesajı arşiv niteliğindedir. Artık tüm güncellemeler "
            "yeni dosya üzerinden yürütülecektir.\n"
            "──────────────────────────────\n"
            "#GAGARAGOGO_ESKI_METIN_ARSIV"
        )
        try:
            await eski_text_mesaji.edit_text(goc_notu, parse_mode=ParseMode.HTML)
        except Exception as _edit_err:
            logger.debug("Eski text mesajı düzenlenemedi: %s", _edit_err)

        logger.info("🎉 Bulut DB sıfır kayıpla TEXT -> DOSYA formatına başarıyla taşındı!")
        return json_data
    except Exception as parse_err:
        logger.error("Eski text DB göç hatası: %s", parse_err)
        return None


async def tek_bulut_db_yukle(client=None) -> Optional[Dict[str, Any]]:
    """Kayıtlı Mesajlar'daki bulut veritabanını yükler veya eski metni dosyaya dönüştürür."""
    if not client:
        return None

    try:
        mevcut_dosya_mesaji, eski_text_mesaji = await _find_cloud_db_messages(client)

        if mevcut_dosya_mesaji:
            logger.info("📦 Bulut Veritabanı DOSYA formatında bulundu. İndiriliyor...")
            ram_file = await client.download_media(mevcut_dosya_mesaji, in_memory=True)
            if ram_file and hasattr(ram_file, "getvalue"):
                raw_bytes = ram_file.getvalue()
                json_data = json.loads(raw_bytes.decode("utf-8"))
                await _verileri_yerel_dosyalara_isle(json_data, client)
                logger.info("✅ Bulut DB dosyasından tüm ayarlar başarıyla yerel diske işlendi.")
                return json_data

        if eski_text_mesaji:
            return await _migrate_legacy_text_db(client, eski_text_mesaji)

    except Exception as e:
        logger.error("Bulut DB yükleme genel hatası: %s", e)

    return None


async def tek_bulut_db_guncelle(client=None) -> None:
    """Tüm verileri Telegram Kayıtlı Mesajlar'daki JSON DOSYASINA yazar."""
    if not client:
        import utils
        client = utils.bot_client

    if not client:
        return

    try:
        from utils import get_yedek_grup_id
        admin_id = get_yedek_grup_id()
        ayarlar_data = db_yukle()
        tiktok_data = _safe_read_json("tiktok_takip.json", {})
        otomesaj_data = _safe_read_json("otomesaj.json", {})
        custom_plugins_data = _safe_read_json("custom_plugins.json", {})

        full_payload = {
            "admin_grup_id": admin_id,
            "ayarlar": ayarlar_data,
            "tiktok_takip": tiktok_data,
            "otomesaj": otomesaj_data,
            "custom_plugins": custom_plugins_data,
            "son_guncelleme": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        raw_bytes = json.dumps(full_payload, ensure_ascii=False, indent=2).encode("utf-8")
        dosya_akisi = io.BytesIO(raw_bytes)
        dosya_akisi.name = BULUT_DB_DOSYA_ADI

        mevcut_dosya_mesaji = None
        async for m in client.search_messages("me", query=BULUT_DB_ETIKET, limit=5):
            if m.document and m.document.file_name == BULUT_DB_DOSYA_ADI:
                mevcut_dosya_mesaji = m
                break

        if mevcut_dosya_mesaji:
            try:
                await client.edit_message_media(
                    chat_id="me",
                    message_id=mevcut_dosya_mesaji.id,
                    media=InputMediaDocument(dosya_akisi, caption=BULUT_DB_CAPTION, parse_mode=ParseMode.HTML)
                )
                logger.debug("Bulut DB dosyası başarıyla edit_message_media ile güncellendi.")
                return
            except Exception as edit_err:
                logger.warning("edit_message_media yapılamadı (%s), yeni dosya gönderilip eskisi temizleniyor...", edit_err)
                try:
                    await mevcut_dosya_mesaji.delete()
                except Exception as _del_err:
                    logger.debug("Mevcut dosya silinemedi: %s", _del_err)

        await client.send_document(
            chat_id="me",
            document=dosya_akisi,
            caption=BULUT_DB_CAPTION,
            parse_mode=ParseMode.HTML
        )
        logger.info("Bulut DB dosyası başarıyla Saved Messages'a gönderildi.")

    except Exception as e:
        logger.error("Bulut DB güncelleme hatası: %s", e)


async def _verileri_yerel_dosyalara_isle(json_data: Dict[str, Any], client=None) -> None:
    """Bulut DB'den indirilen JSON verilerini yerel diske yazar ve eksik özel eklentileri kurtarır."""
    try:
        # 1. ayarlar.json
        ayarlar = json_data.get("ayarlar", {})
        if "admin_grup_id" in json_data and json_data["admin_grup_id"]:
            ayarlar["YEDEK_GRUP_ID"] = json_data["admin_grup_id"]
        db_kaydet(ayarlar)

        # 2. tiktok_takip.json
        tiktok_data = json_data.get("tiktok_takip", {})
        if tiktok_data:
            with open("tiktok_takip.json", "w", encoding="utf-8") as f:
                json.dump(tiktok_data, f, ensure_ascii=False, indent=4)

        # 3. otomesaj.json
        otomesaj_data = json_data.get("otomesaj", {})
        if otomesaj_data:
            with open("otomesaj.json", "w", encoding="utf-8") as f:
                json.dump(otomesaj_data, f, ensure_ascii=False, indent=4)

        # 4. custom_plugins.json
        custom_data = json_data.get("custom_plugins", {})
        if custom_data:
            with open("custom_plugins.json", "w", encoding="utf-8") as f:
                json.dump(custom_data, f, ensure_ascii=False, indent=4)

            # Eğer client varsa ve plugins/ içinde eksik custom_*.py varsa Saved Messages'dan indir
            if client:
                for p_name, p_info in custom_data.items():
                    dosya_adi = p_info.get("dosya_adi")
                    if dosya_adi:
                        hedef_yol = os.path.join("plugins", dosya_adi)
                        if not os.path.exists(hedef_yol):
                            yedek_id = p_info.get("yedek_msg_id")
                            if yedek_id:
                                try:
                                    msg = await client.get_messages("me", message_ids=yedek_id)
                                    if msg and msg.document:
                                        await client.download_media(msg, file_name=hedef_yol)
                                        logger.info("📦 Özel eklenti Kayıtlı Mesajlar'dan kurtarıldı: %s", dosya_adi)
                                except Exception as kurtar_hata:
                                    logger.warning("Eklenti kurtarma hatası (%s): %s", dosya_adi, kurtar_hata)

    except Exception as e:
        logger.error("Yerel dosyalara işleme hatası: %s", e)

