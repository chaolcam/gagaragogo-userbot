# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Instant Broadcast & Auto-Message UI
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import logging
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import utils
from bot_plugins.ui.common import safe_edit, format_sure

logger = logging.getLogger(__name__)


def get_ilet_hub_content():
    """Grup & İletim ana geçiş menüsü."""
    from core.locales import t
    keyboard = [
        [InlineKeyboardButton("📢 Anlık İletim (.ilet)", callback_data="sub_ilet_anlik")],
        [InlineKeyboardButton("⏰ Otomatik Mesaj (.otomesaj)", callback_data="sub_ilet_otomesaj")],
        [InlineKeyboardButton("📇 Rehber & Grup Yönetim Merkezi (.rehbermenu)", callback_data="sub_ilet_rehber")],
        [
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu"),
            InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")
        ]
    ]
    metin = (
        "<b>GAGARAGOGO</b> ⬝ <b>Grup & İletim Yönetimi</b>\n"
        "────────────────────────\n"
        "Yönetmek istediğiniz modülü seçin:\n\n"
        "• <b>Anlık İletim:</b> Seçtiğiniz gruplara tek dokunuşla anında mesaj veya medya gönderimi.\n"
        "• <b>Otomatik Mesaj:</b> Belirli zaman aralıklarıyla otomatik tekrarlanan mesaj motoru.\n"
        "• <b>Rehber & Grup:</b> Grupları üye sayısına göre sıralama, üye çekme ve ekleme."
    )
    return InlineKeyboardMarkup(keyboard), metin


def get_ilet_anlik_content():
    """Anlık iletim (.ilet) detay menüsü."""
    from core.locales import t
    keyboard = [
        [InlineKeyboardButton("📋 Grup Seçim Menüsü (.iletmenu)", callback_data="open_ilet_groups")],
        [
            InlineKeyboardButton(t("btn_back"), callback_data="sub_ilet_hub"),
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
        ],
        [InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")]
    ]
    metin = (
        "📢 <b>ANLIK TOPLU İLETİM</b>\n"
        "────────────────────────\n"
        "Mesaj veya medyaları seçili gruplarınıza tek seferde iletir:\n\n"
        "• <code>.ilet</code> — Yanıtlanan mesajı seçili tüm gruplara yollar.\n"
        "• <code>.ilet [yazı]</code> — Yazılan metni doğrudan tüm gruplara gönderir.\n"
        "• <code>.iletmenu</code> — Gönderilecek grupları açıp kapatabileceğiniz panel."
    )
    return InlineKeyboardMarkup(keyboard), metin


def get_ilet_otomesaj_content():
    """Otomatik mesaj (.otomesaj) detay menüsü."""
    from core.locales import t
    keyboard = [
        [InlineKeyboardButton("⚙️ Otomesaj Yönetim Paneli", callback_data="otomsg_list")],
        [
            InlineKeyboardButton(t("btn_back"), callback_data="sub_ilet_hub"),
            InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
        ],
        [InlineKeyboardButton(t("btn_close"), callback_data="yardim_close")]
    ]
    metin = (
        "⏰ <b>OTOMATİK ZAMANLANMIŞ MESAJ MOTORU</b>\n"
        "────────────────────────\n"
        "Gruplara belirlediğiniz süre aralıklarıyla otomatik mesaj yollar:\n\n"
        "• <code>.otomesaj</code> — İnteraktif görev yönetim panelini açar.\n"
        "• <code>.otomesaj ekle [başlık]</code> — Yanıtlanan mesajı periyodik görev yapar.\n"
        "• <code>.otomesaj sure [id] [dk]</code> — Görev süresini günceller (örn: 15 dk).\n"
        "• <code>.otomesaj sil [id]</code> — Belirtilen görevi siler."
    )
    return InlineKeyboardMarkup(keyboard), metin


async def build_ilet_menu_keyboard(page=1):
    from plugins.broadcast import get_all_user_groups, is_group_active
    userbot = utils.bot_client
    if not userbot:
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Userbot aktif değil", callback_data="none")]]), "Userbot aktif değil"

    gruplar = await get_all_user_groups(userbot)
    if not gruplar:
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Grup bulunamadı", callback_data="none")]]), "Hiçbir grup bulunamadı."

    per_page = 10
    toplam_sayfa = max(1, (len(gruplar) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > toplam_sayfa: page = toplam_sayfa

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sayfa_gruplari = gruplar[start_idx:end_idx]

    metin = "📢 <b>Toplu İletim Grup Listesi</b>\n\n"
    for i, g in enumerate(sayfa_gruplari, start=start_idx + 1):
        durum_ikon = "✅ Açık" if is_group_active(g["id"]) else "⛔ Kapalı"
        title = utils.guvenli_isim(g["title"][:26])
        metin += f"{i}. {title} — {durum_ikon}\n"

    metin += "\n💡 Durumunu değiştirmek istediğiniz grubun numarasına tıklayın."

    keyboard = []
    current_row = []
    for i, g in enumerate(sayfa_gruplari, start=start_idx + 1):
        aktif = is_group_active(g["id"])
        btn_text = f"✅ {i}" if aktif else f"⛔ {i}"
        current_row.append(InlineKeyboardButton(btn_text, callback_data=f"ilet_n_{i}_{page}"))
        if len(current_row) == 5:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)

    from core.locales import t
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(t("btn_prev"), callback_data=f"ilet_p_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page}/{toplam_sayfa}", callback_data="ilet_noop"))
    if page < toplam_sayfa:
        nav_row.append(InlineKeyboardButton(t("btn_next"), callback_data=f"ilet_p_{page+1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(f"◀️ {t('cat_broadcast')}", callback_data="sub_ilet_anlik"),
        InlineKeyboardButton(t("btn_home"), callback_data="main_menu")
    ])
    keyboard.append([InlineKeyboardButton(t("btn_close"), callback_data="ilet_close")])
    return InlineKeyboardMarkup(keyboard), metin


async def handle_ilet_callbacks(client, callback_query, data):
    from plugins.broadcast import get_all_user_groups, toggle_group

    if data == "ilet_noop":
        await callback_query.answer()
        return True

    if data.startswith("ilet_n_"):
        parts = data.split("_")
        idx = int(parts[2])
        page = int(parts[3])
        userbot = utils.bot_client
        if userbot:
            gruplar = await get_all_user_groups(userbot)
            if 1 <= idx <= len(gruplar):
                hedef = gruplar[idx - 1]
                yeni_durum = toggle_group(hedef["id"])
                durum_str = "AÇIK ✅" if yeni_durum else "KAPALI ⛔"
                kb, metin = await build_ilet_menu_keyboard(page)
                await safe_edit(callback_query, client, text=metin, reply_markup=kb)
                await callback_query.answer(f"{idx}. {hedef['title'][:20]} -> {durum_str}")
                return True
        await callback_query.answer("Hata oluştu.", show_alert=True)
        return True

    if data.startswith("ilet_p_"):
        page = int(data.split("_")[2])
        kb, metin = await build_ilet_menu_keyboard(page)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data == "ilet_close":
        if callback_query.message:
            try:
                await callback_query.message.delete()
            except Exception as _del_err:
                logger.debug("İlet mesajı silinemedi: %s", _del_err)
        await callback_query.answer()
        return True

    if data == "open_ilet_groups":
        kb, metin = await build_ilet_menu_keyboard(1)
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    return False


# --- OTOMESAJ PANELİ ---

async def build_otomesaj_list_keyboard():
    from plugins.automessage import otomesaj_db_yukle
    db = otomesaj_db_yukle()
    if not db:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yeni Görev Ekleme Rehberi", callback_data="otomsg_add_guide")],
            [InlineKeyboardButton("◀️ İletim Menüsü", callback_data="sub_ilet_otomesaj")],
            [InlineKeyboardButton("❌ Kapat", callback_data="otomsg_close")]
        ]), "⏰ <b>Kayıtlı otomatik mesaj görevi bulunamadı.</b>\n\nEklemek için bir mesaja yanıt verip: <code>.otomesaj ekle [başlık]</code> yazın."

    keyboard = []
    metin = "⏰ <b>OTOMATİK MESAJ GÖREVLERİ</b>\n────────────────────────\nDetaylarını görmek veya düzenlemek için bir göreve tıklayın:\n\n"
    for tid, tinfo in db.items():
        durum = "🟢" if tinfo.get("aktif") else "🔴"
        sure = format_sure(tinfo.get("aralik_dakika", 60))
        baslik = tinfo.get("baslik", f"Görev #{tid}")[:20]
        keyboard.append([InlineKeyboardButton(f"{durum} #{tid} {baslik} ({sure})", callback_data=f"otomsg_det_{tid}")])

    from core.locales import t
    keyboard.append([
        [InlineKeyboardButton(t("btn_back"), callback_data="sub_ilet_otomesaj"),
         InlineKeyboardButton(t("btn_home"), callback_data="main_menu")],
        [InlineKeyboardButton(t("btn_close"), callback_data="otomsg_close")]
    ])
    return InlineKeyboardMarkup(keyboard), metin


async def build_otomesaj_detail_keyboard(task_id):
    from plugins.automessage import otomesaj_db_yukle
    db = otomesaj_db_yukle()
    tinfo = db.get(str(task_id))
    if not tinfo:
        return None, "Görev bulunamadı."

    aktif = tinfo.get("aktif", False)
    onceki_sil = tinfo.get("onceki_sil", False)
    sure_str = format_sure(tinfo.get("aralik_dakika", 60))

    btn_aktif = "Durdur ⏸" if aktif else "Başlat ▶️"
    btn_delprev = "Önceki Sil: AÇIK ✅" if onceki_sil else "Önceki Sil: KAPALI ❌"

    keyboard = [
        [InlineKeyboardButton(btn_aktif, callback_data=f"otomsg_tog_{task_id}"),
         InlineKeyboardButton("⚡ Şimdi Gönder", callback_data=f"otomsg_run_{task_id}")],
        [InlineKeyboardButton(f"⏱ Süre: {sure_str}", callback_data=f"otomsg_time_{task_id}"),
         InlineKeyboardButton(btn_delprev, callback_data=f"otomsg_togold_{task_id}")],
        [InlineKeyboardButton("👥 Hedef Grupları Seç", callback_data=f"otomsg_grp_{task_id}_1")],
        [InlineKeyboardButton("🗑 Bu Görevi Sil", callback_data=f"otomsg_del_{task_id}")],
        [InlineKeyboardButton("◀️ Görev Listesi", callback_data="otomsg_list"),
         InlineKeyboardButton("❌ Kapat", callback_data="otomsg_close")]
    ]
    metin = (
        f"⏰ <b>GÖREV DETAYI: #{task_id} {tinfo.get('baslik', '')}</b>\n"
        "────────────────────────\n"
        f"• <b>Durum:</b> {'🟢 Aktif' if aktif else '🔴 Duraklatıldı'}\n"
        f"• <b>İletim Aralığı:</b> {sure_str}\n"
        f"• <b>Önceki Mesajı Silme:</b> {'Açık' if onceki_sil else 'Kapalı'}\n"
        f"• <b>Seçili Grup Sayısı:</b> {len(tinfo.get('gruplar', []))}"
    )
    return InlineKeyboardMarkup(keyboard), metin


async def handle_otomsg_callbacks(client, callback_query, data):
    if data == "otomsg_list":
        kb, metin = await build_otomesaj_list_keyboard()
        await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data.startswith("otomsg_det_"):
        tid = int(data.split("_")[2])
        kb, metin = await build_otomesaj_detail_keyboard(tid)
        if kb:
            await safe_edit(callback_query, client, text=metin, reply_markup=kb)
        await callback_query.answer()
        return True

    if data.startswith("otomsg_tog_"):
        from plugins.automessage import otomesaj_db_yukle, otomesaj_db_kaydet
        tid = int(data.split("_")[2])
        db = otomesaj_db_yukle()
        if str(tid) in db:
            yeni = not db[str(tid)].get("aktif", False)
            db[str(tid)]["aktif"] = yeni
            otomesaj_db_kaydet(db, sync_cloud=True)
            kb, metin = await build_otomesaj_detail_keyboard(tid)
            if kb:
                await safe_edit(callback_query, client, text=metin, reply_markup=kb)
            await callback_query.answer(f"Görev #{tid} {'Başlatıldı' if yeni else 'Durduruldu'}")
            return True

    if data == "otomsg_close":
        if callback_query.message:
            try:
                await callback_query.message.delete()
            except Exception as _del_err:
                logger.debug("Otomesaj menüsü silinemedi: %s", _del_err)
        await callback_query.answer()
        return True

    return False
