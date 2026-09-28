# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: System Info, Alive Card & Diagnostics
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
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
from core.locales import t

# Komut kayıtları (Yardım menüsünde listelenmesi için)
ggr.cmd("setalive", info=t("cmd_info_alive_55"), usage=".setalive [link] | .setalive reset", category="Sistem")

@ggr.cmd(["alive", "yardim", t("cat_help"), "help"], info=t("cmd_info_botun_72"), usage=".alive", category="Sistem")
async def alive_menusu(client, message):
    """Yardımcı bot aracılığıyla şık .alive kartını ve interaktif kategori menüsünü açar."""
    logging.info(t("log_kullanc_s_alive_komu_40"), message.from_user.id if message.from_user else 'Bilinmeyen')
    try:
        import utils
        if utils.YARDIMCI_BOT_USERNAME:
            try:
                await message.delete()
            except Exception as _exc:
                logging.debug("Suppressed: %s", _exc)
            
            try:
                results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, "alive")
                if results and results.results:
                    res = await utils.send_inline_result_in_context(
                        client,
                        message,
                        results.query_id,
                        results.results[0].id
                    )
                    sent_msg_id = utils.extract_sent_message_id(res)

                    if not sent_msg_id:
                        try:
                            async for last_m in client.get_chat_history(message.chat.id, limit=3):
                                if last_m.from_user and last_m.from_user.is_self and last_m.via_bot:
                                    sent_msg_id = last_m.id
                                    break
                        except Exception as _exc:
                            logging.debug("Suppressed: %s", _exc)

                    if sent_msg_id:
                        utils.LAST_YARDIM_MENU = (message.chat.id, sent_msg_id)
                    else:
                        utils.LAST_YARDIM_MENU = (message.chat.id, None)
                    return
            except Exception as e:
                logging.error(t("log_inline_bot_hatas_s_21"), e)
                
        else:
            from core.locales import t
            await message.edit_text(t("err_bot_token_missing"))
    except Exception as e:
        await message.edit_text(t("system_alive_menusu_hatasi_e", e = e))
        import utils
        await utils.tlog(f"🚨 `.alive` Hatası:\n`{e}`")


@ggr.cmd(["setalive", "aliveresim", "alivelogo"], info=t("cmd_info_alive_55"), usage=t("cmd_usage_setalive_72"), category="Sistem")
async def set_alive_logo(client, message):
    """Alive menüsünde gösterilecek logoyu/afişi günceller."""
    import utils
    args = message.text.split(maxsplit=1)[1:] if message.text else []
    param = args[0].strip() if args else ""
    
    # 1. Sıfırlama (reset)
    if param.lower() in ["reset", "varsayilan", "default", "sifirla"]:
        ggr.set("alive_logo", utils.DEFAULT_ALIVE_LOGO)
        await message.edit_text(
            t("system_b_alive_afisi_varsayilana_sifirlandi_b_k")
        )
        return
        
    # 2. Doğrudan link verilmişse
    if param.startswith("http://") or param.startswith("https://"):
        ggr.set("alive_logo", param)
        await message.edit_text(
            t("system_alive_afisi_guncellendi", url=param)
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
        durum = await message.edit_text(t("system_i_gorsel_indiriliyor_ve_buluta"))
        try:
            indirilen = await client.download_media(reply)
            if indirilen:
                uploaded_url = utils.upload_image_to_cloud(indirilen)
                
                try: 
                    os.remove(indirilen)
                except Exception as _exc:
                    logging.debug("Suppressed: %s", _exc)
                
                if uploaded_url:
                    ggr.set("alive_logo", uploaded_url)
                    await durum.edit_text(
                        t("system_alive_afisi_ayarlandi", url=uploaded_url)
                    )
                    return
                else:
                    await durum.edit_text(
                        t("system_i_gorsel_bulut_sunucularina_yuklenemedi_")
                    )
                    return
        except Exception as err:
            await durum.edit_text(t("system_b_gorsel_isleme_hatasi_b_code_err_code", err = err))
            return
            
    # Parametre veya yanıt yoksa kullanım kılavuzunu göster
    mevcut_logo = utils.get_alive_logo()
    await message.edit_text(
        t("system_alive_afisi_yardim", url=mevcut_logo)
    )


@ggr.cmd("ayarlar", info=t("cmd_info_zelliklerin_69"), usage=".ayarlar", category="Sistem")
async def ayarlar_menusu(client, message):
    """Yardımcı bot aracılığıyla özelliklerin açılıp kapatılabildiği interaktif kontrol panelini açar."""
    logging.info(t("log_kullanc_s_ayarlar_ko_42"), message.from_user.id if message.from_user else 'Bilinmeyen')
    import utils
    if utils.YARDIMCI_BOT_USERNAME:
        try:
            await message.delete()
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)
        
        try:
            results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, "ayarlar")
            if results and results.results:
                res = await utils.send_inline_result_in_context(
                    client,
                    message,
                    results.query_id,
                    results.results[0].id
                )
                sent_msg_id = utils.extract_sent_message_id(res)
                if sent_msg_id:
                    utils.LAST_YARDIM_MENU = (message.chat.id, sent_msg_id)
                return
        except Exception as e:
            logging.error(t("log_inline_ayarlar_hatas_25"), e)
            
    from core.locales import t
    await message.edit_text(t("err_bot_token_missing"))


# ================= SUNUCU DURUMU, GÜNCELLEME VE PING =================

@ggr.cmd("durum", info=t("cmd_info_sunucu_96"), usage=".durum", category="Sistem")
async def sunucu_durumu(client, message):
    """Sunucu donanım kaynaklarını (CPU, RAM, Disk, Uptime ve İşletim Sistemi) detaylı olarak raporlar."""
    logging.info(t("log_kullanc_s_durum_komu_40"), message.from_user.id if message.from_user else 'Bilinmeyen')
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
        await message.edit_text(t("system_durum_alinamadi_code_e_code", e = e))


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


async def _apply_update_now(durum):
    import subprocess
    import sys
    import utils
    _git_hazirla()
    eski_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    fetch_res = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True)
    if "fatal" in fetch_res.stderr.lower() or "error" in fetch_res.stderr.lower():
        await durum.edit_text(t("system_b_git_hatasi_b_code_var_1_code_n_nmanuel", var_1 = fetch_res.stderr))
        return

    remote_commit = subprocess.run(["git", "rev-parse", "--short", "origin/main"], capture_output=True, text=True).stdout.strip()
    if eski_commit and remote_commit and eski_commit == remote_commit:
        from core.locales import t
        await durum.edit_text(t("sys_up_to_date", old_commit=eski_commit))
        return

    await durum.edit_text(t("system_b_yeni_surum_indiriliyor_b_code_eski_com", eski_commit = eski_commit, remote_commit = remote_commit))
    subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True, text=True)
    yeni_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    
    await durum.edit_text(t("system_b_yeni_kodlar_esitlendi_b_code_eski_comm", eski_commit = eski_commit, yeni_commit = yeni_commit))
    pip_cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    pip_res = subprocess.run(pip_cmd + ["--break-system-packages"], capture_output=True, text=True)
    if pip_res.returncode != 0:
        pip_res = subprocess.run(pip_cmd, capture_output=True, text=True)
    
    if pip_res.returncode == 0:
        from core.locales import t
        await durum.edit_text(t("sys_update_done", new_commit=yeni_commit))
    else:
        logging.warning(t("log_pip_uyars_s_15"), pip_res.stderr)
        
    utils.restart_bildirimi_kaydet(
        action="update",
        chat_id=durum.chat.id,
        message_id=durum.id,
        eski_commit=eski_commit,
        yeni_commit=yeni_commit
    )
    os.execl(sys.executable, sys.executable, *sys.argv)  # nosec


async def _check_update_status(durum):
    import subprocess
    _git_hazirla()
    eski_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    fetch_res = subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True)
    
    if "fatal" in fetch_res.stderr.lower() or "error" in fetch_res.stderr.lower():
        await durum.edit_text(t("system_b_git_hatasi_b_code_var_1_code", var_1 = fetch_res.stderr))
        return
        
    remote_commit = subprocess.run(["git", "rev-parse", "--short", "origin/main"], capture_output=True, text=True).stdout.strip()
    if eski_commit == remote_commit:
        from core.locales import t
        await durum.edit_text(t("sys_up_to_date", old_commit=eski_commit))
        return

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


@ggr.cmd("update", info=t("cmd_info_github_103"), usage=".update | .update now", category="Sistem")
async def botu_guncelle(client, message):
    """GitHub reposundaki yeni commitleri denetler (.update) veya indirip botu yeniden başlatır (.update now)."""
    logging.info(t("log_kullanc_s_update_kom_41"), message.from_user.id if message.from_user else 'Bilinmeyen')
    args = message.text.split()
    durum = await message.edit_text(t("system_b_guncellemeler_denetleniyor_b"))
    try:
        if len(args) > 1 and args[1].lower() == "now":
            await _apply_update_now(durum)
        else:
            await _check_update_status(durum)
    except FileNotFoundError:
        await durum.edit_text(t("system_sunucuda_code_git_code_bulunam"))
    except Exception as e:
        from core.locales import t
        await durum.edit_text(t("sys_update_err", e=str(e)))


@ggr.cmd("ping", info=t("cmd_info_bot_72"), usage=".ping", category="Sistem")
async def ping_komutu(client, message):
    """Bot ile Telegram sunucuları arasındaki gecikme süresini (ping ms) ölçer."""
    baslangic = time.time()
    durum = await message.edit_text(t("system_pong"))
    bitis = time.time()
    gecikme = (bitis - baslangic) * 1000
    await durum.edit_text(ggr.t("sys_ping_pong", ms=f"{gecikme:.2f}"))


@ggr.cmd("restart", info=t("cmd_info_python_68"), usage=".restart", category="Sistem")
async def botu_yeniden_baslat(client, message):
    """Python sürecini sunucuya veya terminale dokunmadan yeniden başlatır."""
    logging.info(t("log_kullanc_s_restart_ko_42"), message.from_user.id if message.from_user else 'Bilinmeyen')
    await message.edit_text(ggr.t("sys_restarting"))
    import utils
    utils.restart_bildirimi_kaydet(
        action="restart",
        chat_id=message.chat.id,
        message_id=message.id
    )
    os.execl(sys.executable, sys.executable, *sys.argv)  # nosec
