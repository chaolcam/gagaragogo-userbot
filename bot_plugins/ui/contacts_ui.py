# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Contact & Group Management UI
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import time
import uuid
import asyncio
import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import UserStatus
from pyrogram.errors import (
    FloodWait, UserAlreadyParticipant, UserPrivacyRestricted,
    UserNotMutualContact, UserChannelsTooMuch, ChatAdminRequired, PeerFlood
)
import utils
from core.cache import EntityCache
from bot_plugins.ui.common import make_progress_bar, safe_edit

logger = logging.getLogger("ggr.rehber_ui")

REHBER_ACTIVE_TASKS = {}
_LAST_CONTACTS_COUNT = 0
_LAST_CONTACTS_FETCH = 0.0


def is_active_member(u) -> bool:
    """Ölü hesapları, botları ve silinmiş kullanıcıları eler."""
    if not u or getattr(u, "is_bot", False) or getattr(u, "is_deleted", False) or getattr(u, "is_self", False):
        return False
    status = getattr(u, "status", None)
    if status in (UserStatus.LONG_AGO, UserStatus.LAST_MONTH):
        return False
    return True


async def get_cached_contacts_count(userbot) -> str:
    """Rehberdeki kişi sayısını 2 dakika önbellekte tutarak anında döner."""
    global _LAST_CONTACTS_COUNT, _LAST_CONTACTS_FETCH
    simdi = time.time()
    if _LAST_CONTACTS_COUNT > 0 and (simdi - _LAST_CONTACTS_FETCH < 120):
        return str(_LAST_CONTACTS_COUNT)
    try:
        count = await userbot.get_contacts_count()
        _LAST_CONTACTS_COUNT = count
        _LAST_CONTACTS_FETCH = simdi
        return str(count)
    except Exception:
        return str(_LAST_CONTACTS_COUNT) if _LAST_CONTACTS_COUNT > 0 else "Bilinmeyen"


async def build_rehber_menu_main(userbot, force_refresh: bool = False, back_target: str = "sub_ilet_hub"):
    """Rehber & Grup Yönetim Merkezi ana panelini oluşturur."""
    from core.locales import t
    if not userbot:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_back"), callback_data=back_target)],
            [InlineKeyboardButton(t("btn_home"), callback_data="main_menu")]
        ])
        return kb, "❌ <b>Userbot oturumu aktif değil.</b>"

    gruplar = []
    try:
        from plugins.contacts import get_sorted_user_groups
        gruplar = await get_sorted_user_groups(userbot, force_refresh=force_refresh)
    except Exception as e:
        logger.debug("Rehber grupları yüklenirken hata: %s", e)

    rehber_sayisi = await get_cached_contacts_count(userbot)

    metin = (
        "📇 <b>GagaraGogo Rehber & Grup Yönetim Merkezi</b>\n"
        "───────────────────────────\n"
        f"📊 <b>Rehberdeki Kişi:</b> <code>{rehber_sayisi}</code> | 👥 <b>Kayıtlı Grup:</b> <code>{len(gruplar)}</code>\n\n"
        "Lütfen yapmak istediğiniz işlemi seçin:\n"
        "• <b>Gruptan Gruba Aktar:</b> Bir gruptan üyeleri toplayıp diğer gruba ekler.\n"
        "• <b>Gruptan Rehbere Çek:</b> Seçtiğiniz grubun üyelerini rehberinize kaydeder.\n"
        "• <b>Rehberden Gruba Ekle:</b> Rehberinizdeki kişileri seçilen gruba davet eder.\n\n"
        "⚠️ <i>Dikkat: Toplu ve otonom işlemlerde hesabınızın Telegram tarafından spam yemesi veya kısıtlanması durumunda sorumluluk kullanıcıya aittir.</i>"
    )

    from core.locales import t
    keyboard = [
        [InlineKeyboardButton("🔄 Gruptan Gruba Üye Aktar", callback_data="rm_act_g2g")],
        [
            InlineKeyboardButton("📥 Gruptan Rehbere Çek", callback_data="rm_act_cek"),
            InlineKeyboardButton("📤 Rehberden Gruba Ekle", callback_data="rm_act_ekle")
        ],
        [
            InlineKeyboardButton("📋 Grupları Sıralı Gör", callback_data="rm_list_1"),
            InlineKeyboardButton(t("btn_refresh"), callback_data="rm_rf")
        ],
        [
            InlineKeyboardButton(t("btn_back"), callback_data=back_target),
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu"),
            InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard), metin


def _build_rehber_action_keyboard(action: str, page: int, total_pages: int, page_groups: list, start: int, src_idx: int = None):
    """Rehber grupları için sayı ve navigasyon butonlarını üretir."""
    keyboard = []
    if action != "list":
        num_row = []
        for i, _ in enumerate(page_groups, start=start + 1):
            if action == "g2g_tgt" and i == src_idx:
                continue
            cb = f"rm_gt_{src_idx}_t_{i}" if action == "g2g_tgt" else f"rm_gs_{action}_s_{i}"
            num_row.append(InlineKeyboardButton(str(i), callback_data=cb))
            if len(num_row) == 5:
                keyboard.append(num_row)
                num_row = []
        if num_row:
            keyboard.append(num_row)

    from core.locales import t
    nav_row = []
    src_param = str(src_idx) if src_idx else "0"
    if page > 1:
        nav_row.append(InlineKeyboardButton(t("btn_prev"), callback_data=f"rm_gp_{action}_{page-1}_{src_param}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="rm_noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(t("btn_next"), callback_data=f"rm_gp_{action}_{page+1}_{src_param}"))
    if nav_row:
        keyboard.append(nav_row)

    bot_row = []
    if action == "g2g_tgt":
        bot_row.append(InlineKeyboardButton("◀️ Kaynak Seçimine Dön", callback_data="rm_act_g2g"))
    else:
        bot_row.append(InlineKeyboardButton("◀️ Rehber Menüsü", callback_data="rm_main"))
    bot_row.append(InlineKeyboardButton(t("btn_close"), callback_data="yardim_close"))
    keyboard.append(bot_row)
    return InlineKeyboardMarkup(keyboard)


async def build_rehber_menu_groups(userbot, action: str, page: int = 1, src_idx: int = None, back_target: str = "rm_main"):
    """İşlem için grup seçim ekranını oluşturur."""
    if not userbot:
        return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Geri", callback_data=back_target)]]), "❌ Userbot aktif değil."

    gruplar = []
    try:
        from plugins.contacts import get_sorted_user_groups
        gruplar = await get_sorted_user_groups(userbot, force_refresh=False)
    except Exception as e:
        logger.debug("Grup listesi hatası: %s", e)

    if not gruplar:
        metin = (
            "ℹ️ <b>Grup bulunamadı!</b>\n\n"
            "Hesabınızın üye olduğu grup tespit edilemedi veya taranamadı."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Tekrar Tara", callback_data="rm_rf")],
            [InlineKeyboardButton("◀️ Geri", callback_data=back_target)]
        ])
        return kb, metin

    per_page = 10
    total_pages = max(1, (len(gruplar) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = min(start + per_page, len(gruplar))
    page_groups = gruplar[start:end]

    action_titles = {
        "list": "📋 GRUPLARINIZ (Üye Sayısına Göre)",
        "g2g": "🔄 ÜYE ÇEKİLECEK KAYNAK GRUBU SEÇİN",
        "g2g_tgt": "📤 ÜYELERİN EKLENECEĞİ HEDEF GRUBU SEÇİN",
        "cek": "📥 REHBERE EKLENECEK ÜYELERİN GRUBUNU SEÇİN",
        "ekle": "📤 REHBERDEKİLERİN EKLENECEĞİ GRUBU SEÇİN",
    }
    header = action_titles.get(action, "👥 GRUP LİSTESİ")

    metin = f"<b>{header}</b>\n───────────────────────────\n"
    if src_idx and action == "g2g_tgt" and 1 <= src_idx <= len(gruplar):
        src_grp = gruplar[src_idx - 1]
        metin += f"📥 <b>Kaynak:</b> <code>{utils.guvenli_isim(src_grp['title'][:25])}</code>\n───────────────────────────\n"

    for i, g in enumerate(page_groups, start=start + 1):
        u_sayisi = f"{g['count']:,}".replace(",", ".")
        t_clean = utils.guvenli_isim(g["title"][:24])
        metin += f"<b>{i}.</b> {t_clean} ⬝ <code>{u_sayisi}</code> üye\n"

    metin += f"\n📄 Sayfa: <b>{page}/{total_pages}</b> ⬝ Toplam: <b>{len(gruplar)}</b> grup"
    kb = _build_rehber_action_keyboard(action, page, total_pages, page_groups, start, src_idx)
    return kb, metin


async def build_rehber_menu_counts(userbot, action: str, src_idx: int, tgt_idx: int = None):
    """İşlem için adet seçimi ekranını oluşturur."""
    from plugins.contacts import get_sorted_user_groups
    gruplar = await get_sorted_user_groups(userbot, force_refresh=False)
    src_grp = gruplar[src_idx - 1] if 1 <= src_idx <= len(gruplar) else None
    tgt_grp = gruplar[tgt_idx - 1] if tgt_idx and 1 <= tgt_idx <= len(gruplar) else None

    src_title = utils.guvenli_isim(src_grp["title"][:25]) if src_grp else "Bilinmiyor"
    tgt_title = utils.guvenli_isim(tgt_grp["title"][:25]) if tgt_grp else "Bilinmiyor"

    if action == "g2g":
        metin = (
            "🔄 <b>Gruptan Gruba Üye Aktarımı</b>\n"
            "───────────────────────────\n"
            f"📥 <b>Kaynak Grup:</b> <b>{src_title}</b> (<code>{src_grp['count']}</code> üye)\n"
            f"📤 <b>Hedef Grup:</b> <b>{tgt_title}</b> (<code>{tgt_grp['count']}</code> üye)\n\n"
            "Kaç üye aktarmak istiyorsunuz? Seçin:\n"
            "💡 <i>Hesap güvenliğiniz için tek seferde 50-100 önerilir.</i>"
        )
    elif action == "cek":
        metin = (
            "📥 <b>Gruptan Rehbere Üye Kaydetme</b>\n"
            "───────────────────────────\n"
            f"👥 <b>Seçilen Grup:</b> <b>{src_title}</b> (<code>{src_grp['count']}</code> üye)\n\n"
            "Gruptan kaç üye rehberinize kaydedilsin? Seçin:"
        )
    else:
        metin = (
            "📤 <b>Rehberden Gruba Üye Ekleme</b>\n"
            "───────────────────────────\n"
            f"👥 <b>Hedef Grup:</b> <b>{src_title}</b> (<code>{src_grp['count']}</code> üye)\n\n"
            "Rehberinizden bu gruba kaç kişi eklensin? Seçin:"
        )

    counts = [25, 50, 100, 200, 300, 500]
    keyboard = []
    row = []
    for c in counts:
        if action == "g2g":
            cb = f"rm_r_{action}_{src_idx}_{tgt_idx}_{c}"
        else:
            cb = f"rm_r_{action}_{src_idx}_{c}"
        row.append(InlineKeyboardButton(f"{c} Kişi", callback_data=cb))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    back_cb = f"rm_gs_g2g_s_{src_idx}" if action == "g2g" else f"rm_act_{action}"
    keyboard.append([
        InlineKeyboardButton("◀️ Grup Seçimine Dön", callback_data=back_cb),
        InlineKeyboardButton("❌ İptal", callback_data="yardim_close")
    ])
    return InlineKeyboardMarkup(keyboard), metin


async def _add_single_member_to_chat(userbot, chat_id, user_id):
    """Ortak üye ekleme işlemi ve hata yakalama (Tekrarlanan kodun tek merkezde toplanması)."""
    try:
        await userbot.add_chat_members(chat_id, user_id)
        await asyncio.sleep(1.5)
        return "ok", None
    except UserAlreadyParticipant:
        return "already", None
    except (UserPrivacyRestricted, UserNotMutualContact):
        return "privacy", None
    except UserChannelsTooMuch:
        return "error", None
    except ChatAdminRequired:
        return "admin_required", None
    except PeerFlood:
        return "peer_flood", None
    except FloodWait as fw:
        return "flood_wait", fw.value
    except Exception as _e:
        logger.debug("Üye ekleme hatası: %s", _e)
        return "error", None


async def _handle_add_result(status, fw_val, stats, tgt_title, stop_kb, safe_update):
    """Üye ekleme sonucunu istatistiklere işler ve kritik durumlarda durdurma sinyali döner."""
    if status == "ok":
        stats["basarili"] += 1
    elif status == "already":
        stats["zaten"] += 1
    elif status == "privacy":
        stats["gizlilik"] += 1
    elif status == "admin_required":
        await safe_update(f"❌ <b>Yetki Hatası:</b> <b>{tgt_title}</b> grubuna üye ekleme yetkiniz yok.\n\nEklenen: <code>{stats['basarili']}</code> kişi.")
        return False
    elif status == "peer_flood":
        await safe_update(f"⚠️ <b>Telegram Sınırı (PeerFlood):</b> Hesabınız geçici davet sınırına ulaştı.\n\nEklenen: <code>{stats['basarili']}</code> kişi.")
        return False
    elif status == "flood_wait":
        await safe_update(f"⏳ <b>FloodWait ({fw_val} sn)...</b>", stop_kb)
        await asyncio.sleep(fw_val + 1)
    else:
        stats["hatali"] += 1
    return True


async def _rehber_worker_g2g(userbot, callback_query, task_id, src_group, tgt_group, src_title, tgt_title, limit, stop_kb, safe_update):
    src_id, tgt_id = src_group["id"], tgt_group["id"]
    await safe_update(
        f"🔄 <b>Gruptan Gruba Aktarım Başlatılıyor...</b>\n───────────────────────────\n"
        f"📥 <b>Kaynak:</b> <b>{src_title}</b>\n📤 <b>Hedef:</b> <b>{tgt_title}</b>\n"
        f"🎯 <b>Hedeflenen:</b> <code>{limit}</code> kişi\n\n⏳ <i>Üyeler taranıyor...</i>",
        stop_kb
    )
    stats = {"basarili": 0, "gizlilik": 0, "zaten": 0, "hatali": 0}
    son_guncelleme = time.time()
    durduruldu = False
    try:
        async for member in userbot.get_chat_members(src_id):
            if not REHBER_ACTIVE_TASKS.get(task_id, True):
                durduruldu = True
                break
            u = member.user
            if not is_active_member(u):
                continue
            EntityCache.set_user(u.id, u)
            status, fw_val = await _add_single_member_to_chat(userbot, tgt_id, u.id)
            if not await _handle_add_result(status, fw_val, stats, tgt_title, stop_kb, safe_update):
                return

            if stats["basarili"] >= limit:
                break

            if time.time() - son_guncelleme > 2.5:
                pbar = make_progress_bar(stats["basarili"], limit)
                yuzde = int((stats["basarili"] / limit) * 100)
                await safe_update(
                    f"🔄 <b>Gruptan Gruba Üye Aktarımı Sürüyor...</b>\n───────────────────────────\n"
                    f"📥 <b>Kaynak:</b> <b>{src_title}</b>\n📤 <b>Hedef:</b> <b>{tgt_title}</b>\n\n"
                    f"📊 <code>[{pbar}]</code> %{yuzde} (<code>{stats['basarili']}/{limit}</code>)\n\n"
                    f"✅ <b>Eklenen:</b> <code>{stats['basarili']}</code>\n🔒 <b>Gizlilik Engeli:</b> <code>{stats['gizlilik']}</code>\n"
                    f"⏭️ <b>Zaten Grupta:</b> <code>{stats['zaten']}</code>\n❌ <b>Hatalar:</b> <code>{stats['hatali']}</code>",
                    stop_kb
                )
                son_guncelleme = time.time()
    except Exception as _g2g_err:
        logger.debug("G2G aktarım döngüsü hatası: %s", _g2g_err)
        stats["hatali"] += 1

    durum_baslik = "🛑 <b>İşlem Durduruldu!</b>" if durduruldu else "🎉 <b>Aktarım Tamamlandı!</b>"
    await safe_update(
        f"{durum_baslik}\n───────────────────────────\n"
        f"📥 <b>Kaynak:</b> <b>{src_title}</b>\n📤 <b>Hedef:</b> <b>{tgt_title}</b>\n\n"
        f"✅ <b>Başarıyla Eklenen:</b> <code>{stats['basarili']}</code>\n"
        f"🔒 <b>Gizlilik Engeli:</b> <code>{stats['gizlilik']}</code>\n"
        f"⏭️ <b>Zaten Grupta:</b> <code>{stats['zaten']}</code>\n"
        f"❌ <b>Başarısız/Hatalı:</b> <code>{stats['hatali']}</code>",
        InlineKeyboardMarkup([[InlineKeyboardButton("📇 Rehber Menüsü", callback_data="rm_main")]])
    )


async def _rehber_worker_cek(userbot, callback_query, task_id, src_group, src_title, limit, stop_kb, safe_update):
    """Gruptan kişileri çekip Telegram rehberine kaydeder."""
    src_id = src_group["id"]
    await safe_update(
        f"📥 <b>Gruptan Rehbere Kayıt Başlatılıyor...</b>\n───────────────────────────\n"
        f"👥 <b>Grup:</b> <b>{src_title}</b>\n🎯 <b>Hedef:</b> <code>{limit}</code> kişi\n\n⏳ <i>Üyeler taranıyor...</i>",
        stop_kb
    )
    basarili = zaten = hatali = 0
    son_guncelleme = time.time()
    durduruldu = False

    try:
        async for member in userbot.get_chat_members(src_id):
            if not REHBER_ACTIVE_TASKS.get(task_id, True):
                durduruldu = True
                break
            u = member.user
            if not is_active_member(u):
                continue
            EntityCache.set_user(u.id, u)

            if getattr(u, "is_contact", False):
                zaten += 1
                continue

            ad = u.first_name or "Telegram"
            soyad = u.last_name or f"Üyesi {u.id % 1000}"
            telefon = u.phone_number or ""

            try:
                await userbot.add_contact(user_id=u.id, first_name=ad, last_name=soyad, phone_number=telefon)
                basarili += 1
                await asyncio.sleep(1.0)
            except FloodWait as fw:
                await safe_update(f"⏳ <b>FloodWait ({fw.value} sn)...</b>", stop_kb)
                await asyncio.sleep(fw.value + 1)
            except Exception:
                hatali += 1

            if basarili >= limit:
                break

            if time.time() - son_guncelleme > 2.5:
                pbar = make_progress_bar(basarili, limit)
                yuzde = int((basarili / limit) * 100)
                await safe_update(
                    f"📥 <b>Rehbere Kayıt Sürüyor...</b>\n───────────────────────────\n"
                    f"👥 <b>Grup:</b> <b>{src_title}</b>\n\n"
                    f"📊 <code>[{pbar}]</code> %{yuzde} (<code>{basarili}/{limit}</code>)\n\n"
                    f"✅ <b>Kaydedilen:</b> <code>{basarili}</code>\n⏭️ <b>Zaten Rehberde:</b> <code>{zaten}</code>\n"
                    f"❌ <b>Hatalar:</b> <code>{hatali}</code>",
                    stop_kb
                )
                son_guncelleme = time.time()
    except Exception:
        hatali += 1

    durum_baslik = "🛑 <b>İşlem Durduruldu!</b>" if durduruldu else "🎉 <b>Rehbere Kayıt Tamamlandı!</b>"
    await safe_update(
        f"{durum_baslik}\n───────────────────────────\n"
        f"👥 <b>Grup:</b> <b>{src_title}</b>\n\n"
        f"✅ <b>Başarıyla Kaydedilen:</b> <code>{basarili}</code>\n"
        f"⏭️ <b>Zaten Rehberde Olan:</b> <code>{zaten}</code>\n"
        f"❌ <b>Hatalar:</b> <code>{hatali}</code>",
        InlineKeyboardMarkup([[InlineKeyboardButton("📇 Rehber Menüsü", callback_data="rm_main")]])
    )


async def _rehber_worker_ekle(userbot, callback_query, task_id, tgt_group, tgt_title, limit, stop_kb, safe_update):
    """Rehberdeki kişileri hedef gruba ekler."""
    tgt_id = tgt_group["id"]
    await safe_update(
        f"📤 <b>Rehberden Gruba Ekleme Başlatılıyor...</b>\n───────────────────────────\n"
        f"👥 <b>Hedef Grup:</b> <b>{tgt_title}</b>\n🎯 <b>Hedef:</b> <code>{limit}</code> kişi\n\n⏳ <i>Rehber taranıyor...</i>",
        stop_kb
    )
    stats = {"basarili": 0, "gizlilik": 0, "zaten": 0, "hatali": 0}
    son_guncelleme = time.time()
    durduruldu = False

    try:
        contacts = await userbot.get_contacts()
        for contact in contacts:
            if not REHBER_ACTIVE_TASKS.get(task_id, True):
                durduruldu = True
                break
            if not contact or contact.is_bot or contact.is_deleted or contact.is_self:
                continue

            status, fw_val = await _add_single_member_to_chat(userbot, tgt_id, contact.id)
            if not await _handle_add_result(status, fw_val, stats, tgt_title, stop_kb, safe_update):
                return

            if stats["basarili"] >= limit:
                break

            if time.time() - son_guncelleme > 2.5:
                pbar = make_progress_bar(stats["basarili"], limit)
                yuzde = int((stats["basarili"] / limit) * 100)
                await safe_update(
                    f"📤 <b>Rehberden Gruba Davet Sürüyor...</b>\n───────────────────────────\n"
                    f"👥 <b>Hedef Grup:</b> <b>{tgt_title}</b>\n\n"
                    f"📊 <code>[{pbar}]</code> %{yuzde} (<code>{stats['basarili']}/{limit}</code>)\n\n"
                    f"✅ <b>Eklenen:</b> <code>{stats['basarili']}</code>\n🔒 <b>Gizlilik Engeli:</b> <code>{stats['gizlilik']}</code>\n"
                    f"⏭️ <b>Zaten Grupta:</b> <code>{stats['zaten']}</code>\n❌ <b>Hatalar:</b> <code>{stats['hatali']}</code>",
                    stop_kb
                )
                son_guncelleme = time.time()
    except Exception as _ekle_err:
        logger.debug("Rehberden gruba ekleme döngü hatası: %s", _ekle_err)
        stats["hatali"] += 1

    durum_baslik = "🛑 <b>İşlem Durduruldu!</b>" if durduruldu else "🎉 <b>Gruba Ekleme Tamamlandı!</b>"
    await safe_update(
        f"{durum_baslik}\n───────────────────────────\n"
        f"👥 <b>Hedef Grup:</b> <b>{tgt_title}</b>\n\n"
        f"✅ <b>Başarıyla Eklenen:</b> <code>{stats['basarili']}</code>\n"
        f"🔒 <b>Gizlilik Engeli:</b> <code>{stats['gizlilik']}</code>\n"
        f"⏭️ <b>Zaten Grupta:</b> <code>{stats['zaten']}</code>\n"
        f"❌ <b>Hatalar:</b> <code>{stats['hatali']}</code>",
        InlineKeyboardMarkup([[InlineKeyboardButton("📇 Rehber Menüsü", callback_data="rm_main")]])
    )


async def run_rehber_action_worker(userbot, callback_query, task_id: str, action: str, src_idx: int, tgt_idx: int, limit: int):
    REHBER_ACTIVE_TASKS[task_id] = True
    stop_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 İşlemi Durdur", callback_data=f"rm_stop_{task_id}")]])

    async def safe_update(text, reply_markup=None):
        try:
            await safe_edit(callback_query, userbot, text=text, reply_markup=reply_markup)
        except Exception as _safe_err:
            logger.debug("Rehber safe_update hatası: %s", _safe_err)

    from plugins.contacts import get_sorted_user_groups
    gruplar = await get_sorted_user_groups(userbot, force_refresh=False)
    src_grp = gruplar[src_idx - 1] if 1 <= src_idx <= len(gruplar) else None
    tgt_grp = gruplar[tgt_idx - 1] if tgt_idx and 1 <= tgt_idx <= len(gruplar) else None

    src_title = utils.guvenli_isim(src_grp["title"][:25]) if src_grp else "Grup"
    tgt_title = utils.guvenli_isim(tgt_grp["title"][:25]) if tgt_grp else "Grup"

    if action == "g2g":
        await _rehber_worker_g2g(userbot, callback_query, task_id, src_grp, tgt_grp, src_title, tgt_title, limit, stop_kb, safe_update)
    elif action == "cek":
        await _rehber_worker_cek(userbot, callback_query, task_id, src_grp, src_title, limit, stop_kb, safe_update)
    elif action == "ekle":
        await _rehber_worker_ekle(userbot, callback_query, task_id, src_grp, src_title, limit, stop_kb, safe_update)

    REHBER_ACTIVE_TASKS.pop(task_id, None)


async def _handle_rehber_selection(client, callback_query, data, userbot):
    """Grup seçim ve sayfalandırma callback'lerini yönetir."""
    if data.startswith("rm_act_"):
        action = data.split("_")[2]
        kb, metin = await build_rehber_menu_groups(userbot, action=action, page=1)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data.startswith("rm_list_") or data.startswith("rehber_pg_"):
        parts = data.split("_")
        page = int(parts[2]) if data.startswith("rm_list_") else int(parts[4])
        kb, metin = await build_rehber_menu_groups(userbot, action="list", page=page)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data.startswith("rm_gp_"):
        parts = data.split("_")
        page = int(parts[-2])
        src_idx = int(parts[-1]) if parts[-1] != "0" else None
        action = "_".join(parts[2:-2])
        kb, metin = await build_rehber_menu_groups(userbot, action=action, page=page, src_idx=src_idx)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data.startswith("rm_gs_"):
        parts = data.split("_")
        action, idx = parts[2], int(parts[4])
        if action == "g2g":
            kb, metin = await build_rehber_menu_groups(userbot, action="g2g_tgt", page=1, src_idx=idx)
        else:
            kb, metin = await build_rehber_menu_counts(userbot, action=action, src_idx=idx)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data.startswith("rm_gt_"):
        parts = data.split("_")
        src_idx, tgt_idx = int(parts[2]), int(parts[4])
        kb, metin = await build_rehber_menu_counts(userbot, action="g2g", src_idx=src_idx, tgt_idx=tgt_idx)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    return False


async def _handle_rehber_execution(client, callback_query, data, userbot):
    """Görev başlatma ve durdurma callback'lerini yönetir."""
    if data.startswith("rm_r_"):
        parts = data.split("_")
        action = parts[2]
        task_id = str(uuid.uuid4())[:8]
        if action == "g2g":
            src_idx, tgt_idx, count = int(parts[3]), int(parts[4]), int(parts[5])
            await callback_query.answer("🚀 Gruptan gruba aktarım başlatılıyor...", show_alert=False)
            asyncio.create_task(run_rehber_action_worker(userbot, callback_query, task_id, "g2g", src_idx, tgt_idx, count))
        elif action in ("cek", "ekle"):
            src_idx, count = int(parts[3]), int(parts[4])
            label = "Rehbere kayıt" if action == "cek" else "Gruba davet"
            await callback_query.answer(f"🚀 {label} başlatılıyor...", show_alert=False)
            asyncio.create_task(run_rehber_action_worker(userbot, callback_query, task_id, action, src_idx, None, count))
        return True

    if data.startswith("rm_stop_"):
        tid = data.split("_")[2]
        REHBER_ACTIVE_TASKS[tid] = False
        await callback_query.answer("🛑 İşlem durduruluyor...", show_alert=True)
        return True

    return False


async def handle_rehber_callbacks(client, callback_query, data):
    """rm_ ve rehber_ callback'lerinin tamamını hatasız yöneten ana yönlendirici."""
    if data in ("rm_noop", "rehber_noop"):
        await callback_query.answer()
        return True

    userbot = utils.bot_client
    if not userbot:
        await callback_query.answer("❌ Userbot aktif değil!", show_alert=True)
        return True

    if data == "rm_main":
        kb, metin = await build_rehber_menu_main(userbot)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data.startswith(("rm_rf", "rehber_rf_")):
        await callback_query.answer("🔄 Gruplar yenileniyor...", show_alert=False)
        kb, metin = await build_rehber_menu_main(userbot, force_refresh=True)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        return True

    if await _handle_rehber_selection(client, callback_query, data, userbot):
        return True

    return await _handle_rehber_execution(client, callback_query, data, userbot)
