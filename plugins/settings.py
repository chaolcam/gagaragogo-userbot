# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: System Settings & Group Configuration
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
from utils import ggr
from core.locales import t

def format_grup_id(id_val):
    id_str = str(id_val).strip()
    if id_str.isdigit() or (id_str.startswith('-') and not id_str.startswith('-100')):
        return int(f"-100{id_str.lstrip('-')}")
    try: return int(id_str)
    except Exception: return id_str

@ggr.cmd("setyedekgrup", info=t("cmd_info_ana_53"), usage=".setyedekgrup [id]", category="Sistem")
async def set_yedek_grup(client, message):
    """Mevcut bir grubu ana admin grubu olarak bağlar; forum konularını açar, botu yönetici yapar ve karşılama mesajını sabitler."""
    if len(message.command) > 1:
        yeni_id = format_grup_id(message.command[1])
    elif str(message.chat.id).startswith("-100"):
        yeni_id = message.chat.id
    else:
        await message.edit_text(ggr.t("err_setyedekgrup_usage"))
        return

    try:
        await message.edit_text(t("settings_grup_yeni_id_ana_merkez_olarak_baglaniyo", yeni_id = yeni_id))
        import utils
        await utils.grubu_yapilandir_ve_hazirla(client, yeni_id)

        has_topics = bool(ggr.get("log_topic_id"))
        konu_metni = (
            "📌 <b>Açılan Forum Konuları:</b> <code>🛠 Sistem Logları</code>, <code>🗑 Silinen Mesajlar</code>, <code>⏳ Süreli Medyalar</code>\n"
            if has_topics else
            "ℹ️ <b>Grup Modu:</b> Standart Grup (Grupta 'Konular' kapalı olduğu için tüm loglar ve arşivler doğrudan bu ana gruba gönderilecek).\n"
            "💡 <i>Eğer forum konuları açmak isterseniz Telegram'da Grubu Düzenle > 'Konular'ı (Topics) açıp tekrar .setyedekgrup yazabilirsiniz.</i>\n"
        )

        await message.edit_text(
            t("settings_admin_grubu_yapilandirildi", chat_id=yeni_id, title=konu_metni)
        )
    except Exception as e:
        await message.edit_text(t("settings_grup_yapilandirma_hatasi_n_e", e = e))


@ggr.cmd(["dil", "lang", "botlang", "setlang", "botdil"], info="Bot dilini ayarlar / Changes bot language.", usage=".dil [tr/en] veya .lang [tr/en]", category="Sistem")
async def lang_komutu(client, message):
    """Bot dilini anında değiştirir ve veritabanına kaydeder."""
    from core.locales import get_current_lang, set_current_lang, t
    args = message.text.split()[1:] if message.text else []
    if not args:
        cur = get_current_lang()
        await message.edit_text(t("lang_usage", lang=cur, lang_val=cur.upper()))
        return

    secim = args[0].lower()
    if secim in ["tr", "turkce", "türkçe"]:
        set_current_lang("tr")
        from core.database import tek_bulut_db_guncelle
        import asyncio
        asyncio.create_task(tek_bulut_db_guncelle())
        await message.edit_text(t("lang_changed", lang="tr"))
    elif secim in ["en", "english", "ingilizce"]:
        set_current_lang("en")
        from core.database import tek_bulut_db_guncelle
        import asyncio
        asyncio.create_task(tek_bulut_db_guncelle())
        await message.edit_text(t("lang_changed", lang="en"))
    else:
        await message.edit_text(ggr.t("err_missing_args"))
