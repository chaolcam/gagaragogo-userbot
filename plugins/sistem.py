# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: MIT License
# Copyright (c) 2026 chaolcam
#
# Module: System Diagnostics & Maintenance (plugins/sistem.py)
# Description: Commands for .alive card, banner customization (.setalive),
#              latency ping (.ping), in-place hot restart (.restart), and GitHub updates.
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
import subprocess
import re
import time
import psutil
import asyncio
import logging
from utils import ggr, KOMUT_BILGILERI, ggr_commands, tlog

# Komut kayıtları (Yardım menüsünde listelenmesi için)
ggr.cmd("setalive", info="Alive menüsündeki afiş görselini ayarlar veya sıfırlar.", usage=".setalive [link] | .setalive reset", category="Sistem")

@ggr.cmd(["alive", "yardim", "yardım", "help"], info="Botun canlı durum kartını, sistem metriklerini ve kontrol panelini açar.", usage=".alive", category="Sistem")
async def alive_menusu(client, message):
    """Yardımcı bot aracılığıyla şık .alive kartını ve interaktif kategori menüsünü açar."""
    logging.info(f"Kullanıcı {message.from_user.id if message.from_user else 'Bilinmeyen'} .alive komutunu çalıştırdı.")
    try:
        import utils
        if utils.YARDIMCI_BOT_USERNAME:
            try:
                await message.delete()
            except Exception:
                pass
            
            try:
                results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, "alive")
                if results and results.results:
                    reply_to_id = message.reply_to_message_id or getattr(message, "message_thread_id", None)
                    res = await client.send_inline_bot_result(
                        message.chat.id,
                        results.query_id,
                        results.results[0].id,
                        reply_to_message_id=reply_to_id
                    )
                    sent_msg_id = None
                    for u in getattr(res, "updates", []):
                        m = getattr(u, "message", None)
                        if m and hasattr(m, "id") and isinstance(m.id, int):
                            sent_msg_id = m.id
                            break
                    if not sent_msg_id and hasattr(res, "id") and isinstance(res.id, int):
                        sent_msg_id = res.id

                    if not sent_msg_id:
                        try:
                            async for last_m in client.get_chat_history(message.chat.id, limit=3):
                                if last_m.from_user and last_m.from_user.is_self and last_m.via_bot:
                                    sent_msg_id = last_m.id
                                    break
                        except Exception:
                            pass

                    if sent_msg_id:
                        utils.LAST_YARDIM_MENU = (message.chat.id, sent_msg_id)
                    else:
                        utils.LAST_YARDIM_MENU = (message.chat.id, None)
                    return
            except Exception as e:
                logging.error(f"Inline bot hatası: {e}")
                
        else:
            await message.edit_text("❌ Yardımcı bot aktif değil. Lütfen `BOT_TOKEN` ayarını kontrol edin.")
    except Exception as e:
        await message.edit_text(f"❌ Alive menüsü hatası: `{e}`")
        import utils
        await utils.tlog(f"🚨 `.alive` Hatası:\n`{e}`")


@ggr.cmd(["setalive", "aliveresim", "alivelogo"], info="Alive menüsündeki afiş görselini ayarlar veya sıfırlar.", usage=".setalive [link] | .setalive (fotoğrafa yanıt vererek) | .setalive reset", category="Sistem")
async def set_alive_logo(client, message):
    """Alive menüsünde gösterilecek logoyu/afişi günceller."""
    import utils
    args = message.text.split(maxsplit=1)[1:] if message.text else []
    param = args[0].strip() if args else ""
    
    # 1. Sıfırlama (reset)
    if param.lower() in ["reset", "varsayilan", "default", "sifirla"]:
        ggr.set("alive_logo", utils.DEFAULT_ALIVE_LOGO)
        await message.edit_text(
            "✅ <b>Alive afişi varsayılana sıfırlandı!</b>\n\n"
            "Kontrol etmek için: <code>.alive</code>"
        )
        return
        
    # 2. Doğrudan link verilmişse
    if param.startswith("http://") or param.startswith("https://"):
        ggr.set("alive_logo", param)
        await message.edit_text(
            f"✅ <b>Alive afişi başarıyla güncellendi!</b>\n\n"
            f"🔗 <b>Yeni Görsel:</b> <a href=\"{param}\">Görüntüle</a>\n"
            "Kontrol etmek için: <code>.alive</code>"
        )
        return
        
    # 3. Fotoğrafa, çıkartmaya veya görsele yanıt verilmişse
    reply = message.reply_to_message
    is_media = reply and (
        reply.photo or 
        reply.sticker or 
        reply.animation or 
        (reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image/"))
    )
    if is_media:
        durum = await message.edit_text("⏳ <i>Görsel indiriliyor ve buluta yükleniyor...</i>")
        try:
            indirilen = await client.download_media(reply)
            if indirilen:
                uploaded_url = utils.upload_image_to_cloud(indirilen)
                
                try: 
                    os.remove(indirilen)
                except Exception: 
                    pass
                
                if uploaded_url:
                    ggr.set("alive_logo", uploaded_url)
                    await durum.edit_text(
                        f"✅ <b>Alive afişi başarıyla ayarlandı!</b>\n\n"
                        f"🖼 <b>Görsel URL:</b> <a href=\"{uploaded_url}\">Görüntüle</a>\n"
                        "Kontrol etmek için: <code>.alive</code>"
                    )
                    return
                else:
                    await durum.edit_text(
                        "⚠️ <i>Görsel bulut sunucularına yüklenemedi. Lütfen görselin doğrudan internet linkini girin:</i>\n"
                        "Örnek: <code>.setalive https://i.imgur.com/ornek.jpg</code>"
                    )
                    return
        except Exception as err:
            await durum.edit_text(f"❌ <b>Görsel işleme hatası:</b> <code>{err}</code>")
            return
            
    # Parametre veya yanıt yoksa kullanım kılavuzunu göster
    mevcut_logo = utils.get_alive_logo()
    await message.edit_text(
        "🖼 <b>ALIVE AFİŞİ AYARLAMA</b>\n"
        "────────────────────────\n"
        "Canlı durum (.alive) kartının en üstünde yer alan afişi değiştirmek için:\n\n"
        "1. <b>Link ile:</b> <code>.setalive https://resim-linki.jpg</code>\n"
        "2. <b>Fotoğraf ile:</b> Bir fotoğrafa yanıt vererek <code>.setalive</code> yazın.\n"
        "3. <b>Sıfırlamak için:</b> <code>.setalive reset</code>\n\n"
        f"🔗 <b>Mevcut Afiş:</b> <a href=\"{mevcut_logo}\">Görüntüle</a>"
    )


@ggr.cmd("ayarlar", info="Özelliklerin açılıp kapatılabildiği interaktif kontrol panelini açar.", usage=".ayarlar", category="Sistem")
async def ayarlar_menusu(client, message):
    """Yardımcı bot aracılığıyla özelliklerin açılıp kapatılabildiği interaktif kontrol panelini açar."""
    logging.info(f"Kullanıcı {message.from_user.id if message.from_user else 'Bilinmeyen'} .ayarlar komutunu çalıştırdı.")
    import utils
    if utils.YARDIMCI_BOT_USERNAME:
        try:
            await message.delete()
        except: pass
        
        try:
            results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, "ayarlar")
            if results and results.results:
                res = await client.send_inline_bot_result(
                    message.chat.id,
                    results.query_id,
                    results.results[0].id,
                    reply_to_message_id=message.reply_to_message_id
                )
                sent_msg_id = None
                if hasattr(res, "id"):
                    sent_msg_id = res.id
                elif hasattr(res, "updates"):
                    for u in res.updates:
                        if hasattr(u, "message") and hasattr(u.message, "id"):
                            sent_msg_id = u.message.id
                            break
                        if hasattr(u, "id"):
                            sent_msg_id = u.id
                            break
                if sent_msg_id:
                    utils.LAST_YARDIM_MENU = (message.chat.id, sent_msg_id)
                return
        except Exception as e:
            logging.error(f"Inline ayarlar hatası: {e}")
            
    await message.edit_text("❌ Yardımcı bot aktif değil. Lütfen ayarlardan `BOT_TOKEN` ekleyin.")


# ================= SUNUCU DURUMU, GÜNCELLEME VE PING =================

@ggr.cmd("durum", info="Sunucu donanım kaynaklarını (CPU, RAM, Disk, Uptime ve İşletim Sistemi) detaylı olarak raporlar.", usage=".durum", category="Sistem")
async def sunucu_durumu(client, message):
    """Sunucu donanım kaynaklarını (CPU, RAM, Disk, Uptime ve İşletim Sistemi) detaylı olarak raporlar."""
    logging.info(f"Kullanıcı {message.from_user.id if message.from_user else 'Bilinmeyen'} .durum komutunu çalıştırdı.")
    try:
        import platform
        import sys
        
        cpu = psutil.cpu_percent(interval=0.5)
        cpu_cores = psutil.cpu_count(logical=True)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_str = f"{int(uptime_seconds // 86400)}g {int((uptime_seconds % 86400) // 3600)}s {int((uptime_seconds % 3600) // 60)}d"
        
        # OS Info
        os_info = f"{platform.system()} {platform.release()}"
        py_ver = sys.version.split(' ')[0]
        
        mesaj = (
            "💻 <b>Sunucu Durumu (Detaylı)</b>\n"
            "────────────────────────\n"
            f"⚙️ <b>Sistem:</b> <code>{os_info}</code>\n"
            f"⏳ <b>Çalışma Süresi:</b> <code>{uptime_str}</code>\n"
            f"🐍 <b>Python:</b> <code>{py_ver}</code>\n\n"
            f"🖥 <b>CPU:</b> <code>%{cpu}</code> ({cpu_cores} Çekirdek)\n"
            f"🧠 <b>RAM:</b> <code>%{ram.percent}</code> ({ram.used / (1024**2):.1f}MB / {ram.total / (1024**2):.1f}MB)\n"
            f"💾 <b>Disk:</b> <code>%{disk.percent}</code> ({disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB)"
        )
        await message.edit_text(mesaj)
    except Exception as e:
        await ggr.log(f"🚨 <b>.durum komutu hatası:</b>\n<code>{e}</code>")
        await message.edit_text(f"❌ Durum alınamadı: <code>{e}</code>")


def _git_hazirla():
    """Git deposunun hazır olduğundan ve origin'in doğru ayarlandığından emin olur (Render Docker uyumluluğu)."""
    import subprocess, os
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", "*"], capture_output=True)
    repo_url = os.getenv("UPSTREAM_REPO", "https://github.com/chaolcam/gagaragogo-userbot.git")
    
    check = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    if check.returncode != 0:
        subprocess.run(["git", "init"], capture_output=True)
        subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", repo_url], capture_output=True)
        subprocess.run(["git", "fetch", "origin", "main"], capture_output=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True)
        subprocess.run(["git", "branch", "-M", "main"], capture_output=True)
        subprocess.run(["git", "branch", "-u", "origin/main", "main"], capture_output=True)
    else:
        remotes = subprocess.run(["git", "remote"], capture_output=True, text=True).stdout
        if "origin" not in remotes:
            subprocess.run(["git", "remote", "add", "origin", repo_url], capture_output=True)
        else:
            subprocess.run(["git", "remote", "set-url", "origin", repo_url], capture_output=True)


@ggr.cmd("update", info="GitHub reposundaki yeni commitleri denetler (.update) veya indirip botu yeniden başlatır (.update now).", usage=".update | .update now", category="Sistem")
async def botu_guncelle(client, message):
    """GitHub reposundaki yeni commitleri denetler (.update) veya indirip botu yeniden başlatır (.update now)."""
    logging.info(f"Kullanıcı {message.from_user.id if message.from_user else 'Bilinmeyen'} .update komutunu çalıştırdı.")
    args = message.text.split()
    
    # 1. Update Now (Güncellemeyi Uygula)
    if len(args) > 1 and args[1].lower() == "now":
        durum = await message.edit_text("🔄 <b>Güncellemeler denetleniyor...</b>")
        try:
            import subprocess
            _git_hazirla()
            
            # Mevcut commit hash'i
            eski_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
            
            # Origin'den en son hali çek
            fetch_res = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True)
            if "fatal" in fetch_res.stderr.lower() or "error" in fetch_res.stderr.lower():
                await durum.edit_text(f"❌ <b>Git Hatası:</b> <code>{fetch_res.stderr}</code>\n\nManuel Deploy yapabilirsiniz.")
                return

            remote_commit = subprocess.run(["git", "rev-parse", "--short", "origin/main"], capture_output=True, text=True).stdout.strip()

            # Zaten en son sürümdeysek yeniden yükleme veya yeniden başlatma yapma
            if eski_commit and remote_commit and eski_commit == remote_commit:
                await durum.edit_text(f"✅ <b>Bot zaten en güncel sürümde!</b>\n\n📌 <b>Mevcut Sürüm:</b> <code>{eski_commit}</code>")
                return

            await durum.edit_text(f"🔄 <b>Yeni sürüm indiriliyor...</b> (<code>{eski_commit}</code> ➔ <code>{remote_commit}</code>)")

            # Hard reset ile origin/main ile birebir eşitle
            reset_res = subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True, text=True)
            yeni_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
            
            await durum.edit_text(f"📥 <b>Yeni kodlar eşitlendi!</b> (<code>{eski_commit}</code> ➔ <code>{yeni_commit}</code>)\nKütüphaneler kontrol ediliyor...")
            
            import sys
            pip_res = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--break-system-packages"], capture_output=True, text=True)
            
            if pip_res.returncode == 0:
                await durum.edit_text(f"✅ <b>Güncelleme Tamamlandı!</b> (<code>{yeni_commit}</code>)\nBot yeniden başlatılıyor...")
            else:
                await durum.edit_text(f"⚠️ <b>Kütüphane uyarısı:</b> <code>{pip_res.stderr}</code>\nYine de yeniden başlatılıyor...")
                
            import utils
            utils.restart_bildirimi_kaydet(
                action="update",
                chat_id=durum.chat.id,
                message_id=durum.id,
                eski_commit=eski_commit,
                yeni_commit=yeni_commit
            )
            os.execl(sys.executable, sys.executable, *sys.argv)
        except FileNotFoundError:
            await durum.edit_text("❌ Sunucuda <code>git</code> bulunamadı.")
        except Exception as e:
            await durum.edit_text(f"❌ <b>Güncelleme sırasında hata:</b>\n<code>{e}</code>")
        return

    # 2. Sadece Güncellemeleri Denetle (git fetch)
    durum = await message.edit_text("🔄 <b>Güncellemeler denetleniyor...</b>")
    try:
        _git_hazirla()
        eski_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        fetch_res = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True)
        
        if "fatal" in fetch_res.stderr.lower() or "error" in fetch_res.stderr.lower():
            await durum.edit_text(f"❌ <b>Git Hatası:</b> <code>{fetch_res.stderr}</code>")
            return
            
        remote_commit = subprocess.run(["git", "rev-parse", "--short", "origin/main"], capture_output=True, text=True).stdout.strip()
        
        if eski_commit == remote_commit:
            await durum.edit_text(f"✅ <b>Bot güncel sürümde!</b>\n\n📌 <b>Mevcut Commit:</b> <code>{eski_commit}</code>")
        else:
            log_res = subprocess.run(["git", "log", "HEAD..origin/main", "--oneline"], capture_output=True, text=True)
            commits = log_res.stdout.strip().split("\n") if log_res.stdout.strip() else [f"{remote_commit} Yeni sürüm yayınlandı"]
            metin = (
                "🆕 <b>Yeni Güncelleme Mevcut!</b>\n"
                "────────────────────────\n"
                f"📌 <b>Mevcut:</b> <code>{eski_commit}</code> ➔ <b>Yeni:</b> <code>{remote_commit}</code>\n\n"
            )
            
            for c in commits[:5]:
                metin += f"• <code>{c}</code>\n"
                
            if len(commits) > 5:
                metin += f"<i>(...ve {len(commits)-5} commit daha)</i>\n"
                
            metin += "\n🚀 Yüklemek ve yeniden başlatmak için:\n👉 <code>.update now</code>"
            await durum.edit_text(metin)
            
    except FileNotFoundError:
        await durum.edit_text("❌ Sunucuda <code>git</code> bulunamadı.")
    except Exception as e:
        await durum.edit_text(f"❌ <b>Denetleme sırasında hata:</b>\n<code>{e}</code>")

@ggr.cmd("ping", info="Bot ile Telegram sunucuları arasındaki gecikme süresini (ping ms) ölçer.", usage=".ping", category="Sistem")
async def ping_komutu(client, message):
    """Bot ile Telegram sunucuları arasındaki gecikme süresini (ping ms) ölçer."""
    baslangic = time.time()
    durum = await message.edit_text("🏓 Pong!")
    bitis = time.time()
    gecikme = (bitis - baslangic) * 1000
    await durum.edit_text(f"🏓 <b>Pong!</b> <code>{gecikme:.2f}ms</code>")

@ggr.cmd("restart", info="Python sürecini sunucuya veya terminale dokunmadan yeniden başlatır.", usage=".restart", category="Sistem")
async def botu_yeniden_baslat(client, message):
    """Python sürecini sunucuya veya terminale dokunmadan yeniden başlatır."""
    logging.info(f"Kullanıcı {message.from_user.id if message.from_user else 'Bilinmeyen'} .restart komutunu çalıştırdı.")
    await message.edit_text("🔄 <b>Bot yeniden başlatılıyor...</b> <i>(Lütfen birkaç saniye bekleyin)</i>")
    import utils
    utils.restart_bildirimi_kaydet(
        action="restart",
        chat_id=message.chat.id,
        message_id=message.id
    )
    os.execl(sys.executable, sys.executable, *sys.argv)
