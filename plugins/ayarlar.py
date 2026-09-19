# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: System Configuration & Group Pairing (plugins/ayarlar.py)
# Description: Handles manual admin group binding (.setyedekgrup) and automatic
#              supergroup forum configuration.
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
from utils import ggr

def format_grup_id(id_val):
    id_str = str(id_val).strip()
    if id_str.isdigit() or (id_str.startswith('-') and not id_str.startswith('-100')):
        return int(f"-100{id_str.lstrip('-')}")
    try: return int(id_str)
    except: return id_str

@ggr.cmd("setyedekgrup", info="Ana Admin / Arşiv Grup ID'sini manuel olarak ayarlar.", usage=".setyedekgrup [id]", category="Sistem")
async def set_yedek_grup(client, message):
    """Mevcut bir grubu ana admin grubu olarak bağlar; forum konularını açar, botu yönetici yapar ve karşılama mesajını sabitler."""
    if len(message.command) > 1:
        yeni_id = format_grup_id(message.command[1])
    elif str(message.chat.id).startswith("-100"):
        yeni_id = message.chat.id
    else:
        await message.edit_text("❌ Kullanım: `.setyedekgrup [id]` veya oluşturduğunuz grup içinde doğrudan `.setyedekgrup` yazın.")
        return

    try:
        await message.edit_text(f"⏳ Grup (`{yeni_id}`) ana merkez olarak bağlanıyor, forum konuları açılıyor ve yapılandırılıyor...")
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
            f"✅ <b>Admin Grubu Başarıyla Yapılandırıldı!</b>\n\n"
            f"🆔 <b>Grup ID:</b> <code>{yeni_id}</code>\n"
            f"{konu_metni}\n"
            f"📌 Karşılama ve güvenlik uyarısı mesajı gruba sabitlendi.\n"
            f"🔒 Telegram Kayıtlı Mesajlar'daki TEK kalıcı bulut veritabanı güncellendi!\n\n"
            f"<i>Bot her yeniden başladığında bu grubu hatırlayacak ve asla yeni grup açmayacaktır.</i>"
        )
    except Exception as e:
        await message.edit_text(f"❌ Grup yapılandırma hatası:\n`{e}`")