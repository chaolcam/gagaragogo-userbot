# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: Dynamic Plugin Manager & Store (plugins/plugin_manager.py)
# Description: Hot-reloads, installs (.install), uninstalls (.uninstall),
#              and lists (.plugins) plugins with store integration and cloud sync.
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
import sys
import ast
import json
import shutil
import asyncio
import importlib
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from utils import ggr

# Sabit resmi eklenti mağazası kanalı
ggr_plugin_store_channel = "gagaragogoplugin"
PLUGIN_STORE_CHANNEL = ggr_plugin_store_channel

# Kesinlikle silinemez ve üzerine yazılamaz çekirdek dahili eklentiler
ggr_builtin_plugins = {
    "admin", "araclar", "ayarlar", "bypasser", "cevir", "etiket",
    "ilet", "instagram", "koruma", "medya", "otomesaj", "sistem",
    "sohbet", "tiktok", "plugin_manager", "afk"
}
BUILTIN_PLUGINS = ggr_builtin_plugins

ggr_custom_plugins_file = "custom_plugins.json"
CUSTOM_PLUGINS_FILE = ggr_custom_plugins_file

# Canlı hafızadaki dinamik handler'ları takip eden sözlük
# Format: { "modul_adi": [(handler, group), ...] }
ggr_active_handlers = {}
ACTIVE_HANDLERS = ggr_active_handlers

def get_custom_plugins():
    if not os.path.exists(ggr_custom_plugins_file):
        return {}
    try:
        with open(ggr_custom_plugins_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_custom_plugins(data):
    try:
        with open(ggr_custom_plugins_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"custom_plugins.json yazma hatası: {e}")

def is_builtin(name):
    clean = name.lower().strip()
    if clean.startswith("custom_"):
        clean = clean[7:]
    if clean.endswith(".py"):
        clean = clean[:-3]
    return clean in ggr_builtin_plugins

def validate_python_code(file_path):
    """Python kodunun sözdizimi (syntax) hatası içerip içermediğini kontrol eder."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        ast.parse(code)
        return True, "Sözdizimi geçerli."
    except SyntaxError as se:
        return False, f"Sözdizimi Hatası (Satır {se.lineno}): {se.msg}"
    except Exception as e:
        return False, f"Hata: {str(e)}"

def load_plugin_runtime(client, module_name):
    """Eklenti modülünü hafızaya alır ve Pyrogram client'ına canlı olarak bağlar."""
    try:
        if module_name in sys.modules:
            mod = importlib.reload(sys.modules[module_name])
        else:
            mod = importlib.import_module(module_name)
    except Exception as e:
        logging.error(f"Modül import hatası ({module_name}): {e}")
        return False, f"İçe aktarma hatası: {str(e)}"

    registered = []
    # Modüldeki Client.on_... ile süslenmiş tüm işleyicileri tara
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name, None)
        if attr and hasattr(attr, "handlers") and isinstance(attr.handlers, list):
            for handler, group in attr.handlers:
                try:
                    client.add_handler(handler, group)
                    registered.append((handler, group))
                except Exception as he:
                    logging.warning(f"Handler ekleme uyarısı: {he}")

    ggr_active_handlers[module_name] = registered
    logging.info(f"✅ {module_name} eklentisi {len(registered)} işleyici ile canlı yüklendi.")
    return True, f"{len(registered)} işleyici aktif edildi."

def unload_plugin_runtime(client, module_name):
    """Eklenti işleyicilerini canlı Pyrogram istemcisinden söker ve hafızadan temizler."""
    registered = ggr_active_handlers.pop(module_name, [])
    removed_count = 0

    if registered and client:
        for handler, group in registered:
            try:
                client.remove_handler(handler, group)
                removed_count += 1
            except Exception as e:
                logging.warning(f"Handler kaldırma hatası: {e}")

    # Modülü sys.modules'dan kaldır
    if module_name in sys.modules:
        del sys.modules[module_name]

    return removed_count

async def fetch_store_plugins(client, limit=50):
    """@gagaragogoplugin resmi kanalındaki .py eklenti mesajlarını listeler."""
    plugins = []
    try:
        async for message in client.get_chat_history(ggr_plugin_store_channel, limit=limit):
            if message.document and message.document.file_name and message.document.file_name.endswith(".py"):
                file_name = message.document.file_name
                mod_name = file_name[:-3]
                caption = message.caption or message.text or "Açıklama belirtilmemiş."
                lines = [l.strip() for l in caption.split("\n") if l.strip()]
                baslik = lines[0] if lines else mod_name
                
                plugins.append({
                    "id": message.id,
                    "dosya_adi": file_name,
                    "modul_adi": mod_name,
                    "baslik": baslik[:40],
                    "aciklama": caption,
                    "boyut": message.document.file_size
                })
    except Exception as e:
        logging.warning(f"Mağaza kanalından eklentiler çekilemedi ({ggr_plugin_store_channel}): {e}")
    return plugins

async def install_plugin_from_file(client, temp_file_path, raw_name, kaynak="dosya", kanal_msg_id=None, aciklama=None):
    """Verilen .py dosyasını denetler, yedekler ve bota canlı olarak kurar."""
    # 1. Sözdizimi Kontrolü
    valid, msg = validate_python_code(temp_file_path)
    if not valid:
        return False, f"❌ <b>Eklenti Kodunda Hata Bulundu:</b>\n<code>{msg}</code>"

    # 2. İsim Temizleme & Çakışma Kontrolü
    clean_name = "".join(c for c in raw_name.lower() if c.isalnum() or c == "_").strip("_")
    if not clean_name:
        clean_name = f"eklenti_{int(datetime.now().timestamp())}"

    if is_builtin(clean_name):
        return False, f"⛔ <b>İsim Çakışması:</b>\n<code>{clean_name}</code> dahili sistem eklentisidir. Güvenliğiniz için üzerine yazılamaz!"

    target_filename = f"custom_{clean_name}.py"
    target_path = os.path.join("plugins", target_filename)

    # 3. Dosyayı plugins/ klasörüne kopyala
    shutil.copy2(temp_file_path, target_path)

    # 4. Kayıtlı Mesajlar'a (me) Kalıcı Yedek Gönder
    backup_caption = (
        f"📦 <b>GagaraGogo Eklenti Yedeği:</b> <code>{clean_name}</code>\n\n"
        f"🔹 <b>Kaynak:</b> {kaynak}\n"
        f"📅 <b>Yüklenme Tarihi:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        "⚠️ <b>DİKKAT: BU MESAJI SİLMEYİN!</b>\n"
        "<i>Sunucunuz kapansa, yeniden kurulsa veya dosyalarınız silinse bile botunuz bu eklentiyi buradan otomatik olarak geri yükler.</i>"
    )
    yedek_msg_id = None
    try:
        sent = await client.send_document("me", document=target_path, caption=backup_caption)
        yedek_msg_id = sent.id
    except Exception as be:
        logging.warning(f"Kayıtlı mesajlara eklenti yedekleme hatası: {be}")

    # 5. Metadata kaydet
    custom_plugins = get_custom_plugins()
    custom_plugins[clean_name] = {
        "dosya_adi": target_filename,
        "modul": f"plugins.custom_{clean_name}",
        "baslik": clean_name,
        "aciklama": aciklama or "Kullanıcı tarafından yüklendi.",
        "kaynak": kaynak,
        "kanal_msg_id": kanal_msg_id,
        "yedek_msg_id": yedek_msg_id,
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_custom_plugins(custom_plugins)

    # 6. Tek Bulut Veritabanını Güncelle (Arka planda çalıştır)
    asyncio.create_task(ggr.sync_cloud(client))

    # 7. Canlı Olarak Yükle (Hot-Reload)
    ok, load_msg = load_plugin_runtime(client, f"plugins.custom_{clean_name}")
    if not ok:
        return False, f"⚠️ Dosya kaydedildi ancak canlı yükleme uyarısı verdi:\n<code>{load_msg}</code>"

    return True, f"✅ <b>Eklenti Başarıyla Kuruldu!</b>\n\n📦 <b>Ad:</b> <code>{clean_name}</code>\n⚡ <b>Durum:</b> {load_msg}\n💾 <b>Yedek:</b> Kayıtlı Mesajlar'a arşivlendi."

async def uninstall_custom_plugin(client, plugin_name):
    """Özel eklentiyi hafızadan ve diskten güvenle siler."""
    clean_name = plugin_name.lower().strip()
    if clean_name.startswith("custom_"):
        clean_name = clean_name[7:]
    if clean_name.endswith(".py"):
        clean_name = clean_name[:-3]

    if is_builtin(clean_name):
        return False, f"⛔ <b>Dahili Sistem Eklentisi Korundu!</b>\n\n<code>{clean_name}</code> botun temel çekirdek eklentisidir ve silinemez."

    custom_plugins = get_custom_plugins()
    if clean_name not in custom_plugins:
        # custom_plugins'te yok ama plugins/custom_...py dosyası varsa
        target_filename = f"custom_{clean_name}.py"
        target_path = os.path.join("plugins", target_filename)
        if not os.path.exists(target_path):
            return False, f"❌ <code>{clean_name}</code> adında yüklü bir özel eklenti bulunamadı."
    else:
        target_filename = custom_plugins[clean_name].get("dosya_adi", f"custom_{clean_name}.py")
        target_path = os.path.join("plugins", target_filename)

    # Canlı Pyrogram işleyicilerini kaldır
    mod_name = f"plugins.custom_{clean_name}"
    removed = unload_plugin_runtime(client, mod_name)

    # Dosyayı sil
    if os.path.exists(target_path):
        try:
            os.remove(target_path)
        except Exception as fe:
            logging.warning(f"Dosya silme hatası ({target_path}): {fe}")

    # Metadata'dan çıkar
    if clean_name in custom_plugins:
        del custom_plugins[clean_name]
        save_custom_plugins(custom_plugins)

    # Komut kayıtlarından temizle
    try:
        ggr.remove_cmd(clean_name)
    except Exception:
        pass

    # Bulut DB güncelle
    asyncio.create_task(ggr.sync_cloud(client))

    return True, f"🗑️ <b>Eklenti Başarıyla Kaldırıldı!</b>\n\n<code>{clean_name}</code> sistemden ve canlı hafızadan tamamen silindi ({removed} işleyici devre dışı bırakıldı)."


# =============================================================================
# KOMUT İŞLEYİCİLERİ
# =============================================================================

@ggr.cmd(["install"], info="Telegram'daki bir .py dosyasına yanıt vererek veya mağazadan (.install 4) canlı eklenti kurar.", usage=".install (yanıtlayarak) veya .install [sayı]", category="Araçlar")
async def cmd_install(client, message):
    args = message.text.split()[1:] if message.text else []

    # DURUM 1: Bir mesaja/dosyaya yanıt vererek yükleme
    if message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        if not doc.file_name or not doc.file_name.endswith(".py"):
            await message.edit_text("❌ Lütfen <code>.py</code> uzantılı geçerli bir Python eklenti dosyasına yanıt verin!")
            return

        await message.edit_text("⏳ <i>Eklenti dosyası indiriliyor ve kontrol ediliyor...</i>")
        os.makedirs("downloads", exist_ok=True)
        temp_path = os.path.join("downloads", f"temp_{doc.file_name}")

        try:
            await client.download_media(message.reply_to_message, file_name=temp_path)
            raw_name = doc.file_name[:-3]
            success, msg = await install_plugin_from_file(
                client, temp_path, raw_name, kaynak="Yanıtlanan Belge"
            )
            await message.edit_text(msg)
        except Exception as e:
            await message.edit_text(f"❌ Yükleme sırasında beklenmeyen hata oluştu: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
        return

    # DURUM 2: Resmi mağaza kanalından numara ile yükleme (.install 4)
    if args and args[0].isdigit():
        target_num = int(args[0])
        await message.edit_text(f"⏳ <i>@{ggr_plugin_store_channel} kanalındaki #{target_num} eklenti aranıyor...</i>")

        try:
            target_msg = None
            # Önce doğrudan mesaj ID'si olarak dene
            try:
                msg_check = await client.get_messages(ggr_plugin_store_channel, message_ids=target_num)
                if msg_check and msg_check.document and msg_check.document.file_name and msg_check.document.file_name.endswith(".py"):
                    target_msg = msg_check
            except Exception:
                pass

            # Doğrudan bulunamadıysa mağaza listesindeki sırasına bak
            if not target_msg:
                store_plugins = await fetch_store_plugins(client, limit=50)
                # target_num 1-tabanlı liste indeksi olabilir
                if 1 <= target_num <= len(store_plugins):
                    item = store_plugins[target_num - 1]
                    target_msg = await client.get_messages(ggr_plugin_store_channel, message_ids=item["id"])
                else:
                    # veya item['id'] == target_num eşleşmesi
                    for item in store_plugins:
                        if item["id"] == target_num:
                            target_msg = await client.get_messages(ggr_plugin_store_channel, message_ids=item["id"])
                            break

            if not target_msg or not target_msg.document:
                await message.edit_text(
                    f"❌ <b>Eklenti Bulunamadı!</b>\n\n"
                    f"@{ggr_plugin_store_channel} kanalında #{target_num} numaralı geçerli bir <code>.py</code> eklentisi bulunamadı."
                )
                return

            doc = target_msg.document
            os.makedirs("downloads", exist_ok=True)
            temp_path = os.path.join("downloads", f"temp_{doc.file_name}")

            await client.download_media(target_msg, file_name=temp_path)
            raw_name = doc.file_name[:-3]
            caption = target_msg.caption or target_msg.text or ""

            success, msg = await install_plugin_from_file(
                client,
                temp_path,
                raw_name,
                kaynak=f"@{ggr_plugin_store_channel} (No: #{target_num})",
                kanal_msg_id=target_msg.id,
                aciklama=caption
            )
            await message.edit_text(msg)
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass

        except Exception as e:
            await message.edit_text(f"❌ Mağazadan indirme hatası: {str(e)}")
        return

    # Hatalı kullanım uyarısı
    await message.edit_text(
        "💡 <b>Nasıl Eklenti Yüklenir?</b>\n\n"
        "1️⃣ <b>Kendi Eklentinizi Yüklemek İçin:</b>\n"
        "Sohbetteki herhangi bir <code>.py</code> eklenti dosyasına yanıt vererek <code>.install</code> yazın.\n\n"
        "2️⃣ <b>Resmi Mağazadan Yüklemek İçin:</b>\n"
        f"@{ggr_plugin_store_channel} kanalındaki eklenti numarasını belirtin: <code>.install 4</code>\n\n"
        "3️⃣ <b>İnline Menü:</b>\n"
        "<code>.yardim</code> yazarak <b>[ 🔌 Eklentiler & Mağaza ]</b> butonundan tek tıkla kurabilirsiniz."
    )


@ggr.cmd(["uninstall"], info="Yalnızca sonradan yüklenmiş olan özel bir eklentiyi hafızadan ve sistemden kaldırır.", usage=".uninstall [eklenti_adı]", category="Araçlar")
async def cmd_uninstall(client, message):
    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.edit_text(
            "❌ <b>Eklenti Adı Belirtmelisiniz!</b>\n\n"
            "Kullanım: <code>.uninstall [eklenti_adı]</code>\n"
            "Örnek: <code>.uninstall afk</code>\n\n"
            "💡 Yüklü eklentileri görmek için <code>.plugins</code> yazabilirsiniz."
        )
        return

    plugin_name = args[0]
    await message.edit_text(f"⏳ <i><code>{plugin_name}</code> eklentisi kaldırılıyor...</i>")
    success, res_msg = await uninstall_custom_plugin(client, plugin_name)
    await message.edit_text(res_msg)


@ggr.cmd(["plugins"], info="Tüm dahili sistem eklentilerini ve sonradan yüklenen özel eklentileri listeler.", usage=".plugins", category="Araçlar")
async def cmd_plugins(client, message):
    custom_plugins = get_custom_plugins()

    # Dahili sistem eklentileri
    dahili_str = ", ".join([f"<code>{p}</code>" for p in sorted(ggr_builtin_plugins)])

    # Özel eklentiler
    if custom_plugins:
        ozel_satirlar = []
        for name, info in custom_plugins.items():
            tarih = info.get("tarih", "Bilinmiyor")
            kaynak = info.get("kaynak", "Dosya")
            dosya = info.get("dosya_adi", f"custom_{name}.py")
            boyut_kb = 0
            tam_yol = os.path.join("plugins", dosya)
            if os.path.exists(tam_yol):
                boyut_kb = round(os.path.getsize(tam_yol) / 1024, 1)

            ozel_satirlar.append(
                f"🔹 <b>{name}</b> ({boyut_kb} KB)\n"
                f"   └ 📅 {tarih} | 🌐 {kaynak}\n"
                f"   └ 🗑 Kaldırmak için: <code>.uninstall {name}</code>"
            )
        ozel_str = "\n".join(ozel_satirlar)
    else:
        ozel_str = "<i>Henüz sonradan yüklenmiş özel eklentiniz bulunmuyor.</i>\n💡 Bir <code>.py</code> dosyasına yanıt vererek <code>.install</code> yazabilir veya <code>.yardim</code> menüsündeki mağazayı kullanabilirsiniz."

    metin = (
        "🔌 <b>GagaraGogo Eklenti Listesi</b>\n\n"
        f"🛡️ <b>Dahili Sistem Eklentileri (Çekirdek - Silinemez):</b>\n{dahili_str}\n\n"
        f"📦 <b>Yüklü Özel Eklentiler:</b>\n{ozel_str}"
    )

    await message.edit_text(metin)
