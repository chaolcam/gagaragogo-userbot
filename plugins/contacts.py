# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Contact & Group Management Operations
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import asyncio
import time
import logging
from typing import Dict, List, Optional
from pyrogram import Client
from pyrogram.enums import ChatType, UserStatus
from pyrogram.types import Message
from pyrogram.raw.functions.messages import GetAllChats
from pyrogram.raw.types import Chat as RawChat, Channel as RawChannel
from pyrogram.errors import (
    FloodWait,
    UserPrivacyRestricted,
    UserNotMutualContact,
    UserAlreadyParticipant,
    UserChannelsTooMuch,
    ChatAdminRequired,
    PeerFlood,
    RPCError,
)
import utils
from utils import ggr
from core.cache import EntityCache
from core.network import safe_api_call

def is_active_user(u) -> bool:
    """
    Geez / Paperplane tarzı akıllı üye filtresi:
    Ölü hesapları, botları ve silinmiş kullanıcıları eler.
    Sadece son zamanlarda aktif olan gerçek kullanıcıları seçer.
    """
    if not u or getattr(u, "is_bot", False) or getattr(u, "is_deleted", False) or getattr(u, "is_self", False):
        return False
    status = getattr(u, "status", None)
    if status in (UserStatus.LONG_AGO, UserStatus.LAST_MONTH):
        return False
    return True

from pyrogram.raw.functions.channels import GetChannels
from pyrogram.raw.types import InputChannel

# Ön bellek (grupların her defasında tekrar tekrar MTProto üzerinden çekilmesini hızlandırır)
_cached_groups: List[Dict] = []
_last_fetch_time: float = 0.0
CACHE_TTL = 600  # 10 dakika önbellek süresi


def _parse_raw_chats_to_map(raw_chats):
    groups_map: Dict[int, Dict] = {}
    input_channels: List[InputChannel] = []
    for chat in getattr(raw_chats, "chats", []):
        if isinstance(chat, RawChat):
            if getattr(chat, "deactivated", False) or getattr(chat, "left", False):
                continue
            cnt = getattr(chat, "participants_count", 0)
            cid = -int(chat.id)
            groups_map[cid] = {
                "id": cid,
                "title": getattr(chat, "title", "Grup") or "Grup",
                "count": int(cnt) if cnt else 0,
                "is_supergroup": False,
            }
        elif isinstance(chat, RawChannel):
            if getattr(chat, "broadcast", False) or getattr(chat, "left", False):
                continue
            cid = int(f"-100{chat.id}")
            groups_map[cid] = {
                "id": cid,
                "title": getattr(chat, "title", "Süper Grup") or "Süper Grup",
                "count": 0,
                "is_supergroup": True,
            }
            a_hash = getattr(chat, "access_hash", None)
            if a_hash:
                input_channels.append(InputChannel(channel_id=chat.id, access_hash=a_hash))
    return groups_map, input_channels


async def _fallback_dialog_groups(client: Client, groups_map: Dict[int, Dict]):
    if groups_map:
        return
    try:
        async for dialog in client.get_dialogs(limit=50):
            chat = getattr(dialog, "chat", None)
            if not chat:
                continue
            chat_type_str = str(getattr(chat, "type", "")).lower()
            is_grp = "group" in chat_type_str or getattr(chat, "type", None) in (ChatType.GROUP, ChatType.SUPERGROUP)
            if is_grp:
                cnt = getattr(chat, "members_count", 0) or 0
                if chat.id not in groups_map:
                    groups_map[chat.id] = {
                        "id": chat.id,
                        "title": chat.title or "Grup",
                        "count": int(cnt),
                        "is_supergroup": "super" in chat_type_str or getattr(chat, "type", None) == ChatType.SUPERGROUP,
                    }
    except Exception as e:
        logging.warning("[Rehber Plugin] get_dialogs fallback uyarısı: %s", e)


async def _batch_update_channel_counts(client: Client, input_channels: List[InputChannel], groups_map: Dict[int, Dict]):
    if not input_channels:
        return
    try:
        for i in range(0, len(input_channels), 100):
            batch = input_channels[i:i + 100]
            channels_res = await client.invoke(GetChannels(id=batch))
            for ch in getattr(channels_res, "chats", []):
                cid = int(f"-100{ch.id}")
                cnt = getattr(ch, "participants_count", None)
                if cid in groups_map and cnt is not None:
                    groups_map[cid]["count"] = int(cnt)
    except Exception as e:
        logging.warning("[Rehber Plugin] GetChannels toplu sorgu uyarısı: %s", e)


async def get_sorted_user_groups(client: Client, force_refresh: bool = False) -> List[Dict]:
    """
    Kullanıcının üye olduğu grupları ve süpergrupları çeker.
    Üye sayılarını tek bir toplu MTProto RPC sorgusuyla alır (0.2 - 0.4 saniye).
    En fazla üyeden en aza doğru sıralar.
    """
    global _cached_groups, _last_fetch_time
    simdi = time.time()
    if not force_refresh and _cached_groups and (simdi - _last_fetch_time < CACHE_TTL):
        return _cached_groups

    groups_map: Dict[int, Dict] = {}
    input_channels: List[InputChannel] = []
    yedek_id = utils.get_yedek_grup_id()

    try:
        raw_chats = await client.invoke(GetAllChats(except_ids=[]))
        groups_map, input_channels = _parse_raw_chats_to_map(raw_chats)
    except Exception as e:
        logging.warning("[Rehber Plugin] GetAllChats uyarısı: %s", e)

    await _fallback_dialog_groups(client, groups_map)
    await _batch_update_channel_counts(client, input_channels, groups_map)

    gruplar = [g for cid, g in groups_map.items() if not (yedek_id and str(cid) == str(yedek_id))]
    gruplar.sort(key=lambda x: int(x.get("count") or 0), reverse=True)

    _cached_groups = gruplar
    _last_fetch_time = simdi
    return gruplar


def find_target_group(arg_val: str, groups: List[Dict], current_chat_id: int) -> Optional[Dict]:
    """
    Parametre olarak verilen grup numarası veya ID'ye göre hedef grubu bulur.
    """
    if not arg_val:
        for g in groups:
            if g["id"] == current_chat_id:
                return g
        return None

    if arg_val.isdigit():
        idx = int(arg_val) - 1
        if 0 <= idx < len(groups):
            return groups[idx]

    try:
        cid = int(arg_val)
        for g in groups:
            if g["id"] == cid:
                return g
    except ValueError:
        pass

    arg_lower = arg_val.lower()
    for g in groups:
        if arg_lower in g["title"].lower():
            return g

    return None


def _format_rehber_panel_text(gruplar: List[Dict], sayfa: int, toplam_sayfa: int, rehber_sayisi) -> str:
    sayfa_basi = 10
    baslangic = (sayfa - 1) * sayfa_basi
    bitis = baslangic + sayfa_basi
    gosterilen = gruplar[baslangic:bitis]

    metin_parcalari = [
        "📇 <b>GagaraGogo Rehber & Grup Yönetim Paneli</b>\n",
        "───────────────────────────\n",
        f"📊 <b>Rehberdeki Toplam Kişi:</b> <code>{rehber_sayisi}</code>\n",
        f"👥 <b>Toplam Grup Sayısı:</b> <code>{len(gruplar)}</code> | <b>Sayfa:</b> <code>{sayfa}/{toplam_sayfa}</code>\n\n",
        "🏆 <b>Gruplarınız (En Çok Üyeden En Aza):</b>\n",
    ]

    for idx, g in enumerate(gosterilen, start=baslangic + 1):
        sayi = int(g.get("count") or 0)
        u_sayisi = f"{sayi:,}".replace(",", ".") if sayi > 0 else "Bilinmiyor"
        metin_parcalari.append(f"<b>{idx}.</b> <b>{ggr.safe_html(g['title'][:28])}</b> — <code>{u_sayisi} üye</code>\n")

    metin_parcalari.extend([
        "───────────────────────────\n",
        "🔄 <b>İnteraktif Butonlu Menü:</b> <code>.rehbermenu</code>\n\n",
        "📥 <b>Gruptan Rehbere Üye Çekme:</b>\n",
        "👉 <code>.rehberekle [Grup No] [30/50/100/200]</code>\n",
        "<i>Örnek: <code>.rehberekle 1 50</code> (1. gruptan 50 kişiyi rehberinize kaydeder)</i>\n\n",
        "📤 <b>Rehberdeki Kişileri Gruba Ekleme:</b>\n",
        "👉 <code>.grubaekle [Grup No] [30/50/100/200]</code>\n",
        "<i>Örnek: <code>.grubaekle 2 50</code> (Rehberden 50 kişiyi 2. gruba davet eder)</i>\n\n",
        "🔄 <b>Gruptan Gruba Doğrudan Aktarma:</b>\n",
        "👉 <code>.grupaktar [Kaynak No] [Hedef No] [Adet]</code>\n",
        "<i>Örnek: <code>.grupaktar 1 2 100</code> (1. gruptan 100 kişiyi 2. gruba aktarır)</i>\n\n",
        "⚙️ <b>Diğer Hızlı Komutlar:</b>\n",
        "• <code>.rehber [sayfa]</code> : Diğer sayfaları listeler\n",
        "• <code>.rehber yenile</code> : Grup listesini sıfırdan günceller\n",
        "• <code>.rehbersayi</code> : Rehberinizdeki kişi sayısını gösterir\n",
        "• <code>.rehbersil</code> : Yanıtlanan kişiyi rehberden siler\n",
        "• <code>.rehbertemizle onayla</code> : Rehberdeki kişileri temizler\n\n",
        "⚠️ <b>Sorumluluk Reddi:</b> <i>Toplu üye aktarımı ve otonom işlemlerde hesabınızın Telegram tarafından spam yemesi, kısıtlanması veya kapanması durumunda sorumluluk tamamen kullanıcıya aittir.</i>\n",
    ])
    return "".join(metin_parcalari)


@ggr.cmd(
    ["rehbermenu", "rehber", "rehberpanel", "contacts"],
    info="Grup ve rehber yönetim panelini açar. Butonlarla üye aktarımı ve yönetimi sağlar.",
    usage=".rehbermenu (veya .rehber | .rehber [sayfa] | .rehber yenile)",
    category="Grup & İletim"
)
async def cmd_rehber_panel(client: Client, message: Message):
    """
    Kullanıcının gruplarını ve rehberini yönetebileceği interaktif paneli açar.
    """
    try:
        args = message.text.split()[1:] if message.text else []
        cmd_name = message.text.split()[0].lstrip(".").lower() if message.text else "rehbermenu"
        sayfa = 1
        force_refresh = False

        if args:
            if args[0].lower() in ["yenile", "refresh", "guncelle"]:
                force_refresh = True
                if len(args) > 1 and args[1].isdigit():
                    sayfa = max(1, int(args[1]))
            elif args[0].isdigit():
                sayfa = max(1, int(args[0]))

        # 1. Eğer argümansız çağrıldıysa veya .rehbermenu ise ve Yardımcı Bot aktifse interaktif inline menüyü aç
        if (not args or cmd_name == "rehbermenu") and not force_refresh and utils.YARDIMCI_BOT_USERNAME:
            try:
                results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, "rehbermenu")
                if results and results.results:
                    await utils.send_inline_result_in_context(
                        client,
                        message,
                        results.query_id,
                        results.results[0].id
                    )
                    await message.delete()
                    return
            except Exception as e:
                logging.warning("[Rehber Plugin] Inline menü uyarısı (%s), metin paneline geçiliyor...", e)

        durum = await message.edit_text("🔄 <i>Gruplar taranıyor ve üye sayılarına göre sıralanıyor...</i>")

        gruplar = await get_sorted_user_groups(client, force_refresh=force_refresh)
        if not gruplar:
            await durum.edit_text("ℹ️ Üye olduğunuz herhangi bir grup bulunamadı.")
            return

        try:
            rehber_sayisi = await client.get_contacts_count()
        except Exception:
            rehber_sayisi = "Bilinmeyen"

        sayfa_basi = 10
        toplam_sayfa = max(1, (len(gruplar) + sayfa_basi - 1) // sayfa_basi)
        sayfa = min(sayfa, toplam_sayfa)

        panel_metni = _format_rehber_panel_text(gruplar, sayfa, toplam_sayfa, rehber_sayisi)
        await durum.edit_text(panel_metni)
    except Exception as e:
        logging.error("[Rehber Plugin] Panel hatası: %s", e)
        try:
            await message.edit_text(f"❌ <b>Panel açılırken bir hata oluştu:</b>\n<code>{ggr.safe_html(str(e))}</code>")
        except Exception as _exc:
            logging.debug("Suppressed: %s", _exc)


@ggr.cmd(
    ["grupaktar", "g2g", "grubagrup"],
    info="Bir gruptaki üyeleri doğrudan diğer gruba aktarır.",
    usage=".grupaktar [kaynak_grup_no] [hedef_grup_no] [adet (30/50/100/200)]",
    category=None
)
async def cmd_grup_aktar(client: Client, message: Message):
    """
    Belirtilen kaynak gruptan üyeleri toplayıp hedef gruba ekler.
    Kullanım: .grupaktar 1 2 100
    """
    args = message.text.split()[1:] if message.text else []
    if len(args) < 2:
        await message.edit_text(
            "❌ <b>Eksik parametre!</b>\n\n"
            "Kullanım: <code>.grupaktar [Kaynak No] [Hedef No] [Adet]</code>\n"
            "<i>Örnek: <code>.grupaktar 1 2 100</code> (1. gruptan 100 kişiyi 2. gruba aktarır)</i>\n"
            "💡 Veya butonlarla yönetmek için: <code>.rehbermenu</code>"
        )
        return

    gruplar = await get_sorted_user_groups(client)
    src_group = find_target_group(args[0], gruplar, message.chat.id)
    tgt_group = find_target_group(args[1], gruplar, message.chat.id)
    limit = 50
    if len(args) >= 3 and args[2].isdigit():
        limit = max(1, min(500, int(args[2])))

    if not src_group or not tgt_group:
        await message.edit_text("❌ <b>Kaynak veya hedef grup bulunamadı. Lütfen <code>.rehber</code> yazarak numaraları kontrol edin.</b>")
        return

    src_id = src_group["id"]
    tgt_id = tgt_group["id"]

    durum = await message.edit_text(
        f"⏳ <b>{ggr.safe_html(src_group['title'])}</b> grubundan üyeler toplanıp "
        f"<b>{ggr.safe_html(tgt_group['title'])}</b> grubuna aktarılmaya başlanıyor...\n"
        f"Hedef: <b>{limit}</b> kişi."
    )

    basarili = 0
    gizlilik = 0
    zaten = 0
    hatali = 0
    son_guncelleme = time.time()

    try:
        async for member in client.get_chat_members(src_id):
            u = member.user
            if not is_active_user(u):
                continue
            EntityCache.set_user(u.id, u)

            try:
                await client.add_chat_members(tgt_id, u.id)
                basarili += 1
                await asyncio.sleep(1.5)
            except UserAlreadyParticipant:
                zaten += 1
            except (UserPrivacyRestricted, UserNotMutualContact):
                gizlilik += 1
            except UserChannelsTooMuch:
                hatali += 1
            except ChatAdminRequired:
                await durum.edit_text("❌ <b>Hata:</b> Hedef gruba üye ekleme yetkiniz yok.")
                return
            except PeerFlood:
                await durum.edit_text(
                    "⚠️ <b>Telegram Sınırı (PeerFlood):</b> Hesabınız geçici grup davet sınırına ulaştı.\n"
                    f"Şu ana kadar eklenen: <code>{basarili}</code> kişi."
                )
                return
            except FloodWait as fw:
                await asyncio.sleep(fw.value + 1)
            except Exception:
                hatali += 1

            if basarili >= limit:
                break

            if time.time() - son_guncelleme > 3:
                yuzde = int((basarili / limit) * 100)
                await durum.edit_text(
                    f"🔄 <b>Gruptan Gruba Aktarım Sürüyor...</b>\n"
                    f"───────────────────────────\n"
                    f"📥 <b>Kaynak:</b> <b>{ggr.safe_html(src_group['title'])}</b>\n"
                    f"📤 <b>Hedef:</b> <b>{ggr.safe_html(tgt_group['title'])}</b>\n"
                    f"📊 <b>İlerleme:</b> <code>{basarili}/{limit}</code> (%{yuzde})\n"
                    f"✅ <b>Eklenen:</b> <code>{basarili}</code>\n"
                    f"🔒 <b>Gizlilik Engeli:</b> <code>{gizlilik}</code>\n"
                    f"⏭️ <b>Zaten Grupta:</b> <code>{zaten}</code>\n"
                    f"❌ <b>Diğer Hatalar:</b> <code>{hatali}</code>\n"
                    f"⏳ <i>Lütfen bekleyin...</i>"
                )
                son_guncelleme = time.time()

        await durum.edit_text(
            "🎉 <b>Aktarım Başarıyla Tamamlandı!</b>\n"
            "───────────────────────────\n"
            f"📥 <b>Kaynak:</b> <b>{ggr.safe_html(src_group['title'])}</b>\n"
            f"📤 <b>Hedef:</b> <b>{ggr.safe_html(tgt_group['title'])}</b>\n"
            f"🎯 <b>Hedef:</b> <code>{limit}</code> kişi\n\n"
            f"✅ <b>Başarıyla Eklenen:</b> <code>{basarili}</code> kişi\n"
            f"🔒 <b>Gizlilik Nedeniyle Eklenemeyen:</b> <code>{gizlilik}</code>\n"
            f"⏭️ <b>Zaten Üye Olan:</b> <code>{zaten}</code>\n"
            f"❌ <b>Diğer Hatalar:</b> <code>{hatali}</code>\n"
            f"───────────────────────────\n"
            f"💡 <i>Tüm işlemler güvenli aralıklarla tamamlandı!</i>"
        )
    except Exception as e:
        await durum.edit_text(f"❌ <b>Hata:</b> <code>{ggr.safe_html(str(e))}</code>")


@ggr.cmd(
    ["rehberekle", "cekrehbere"],
    info="Seçilen gruptaki üyeleri Telegram rehberinize kaydeder.",
    usage=".rehberekle [grup_no] [adet (30/50/100/200)]",
    category=None
)
async def cmd_rehberekle(client: Client, message: Message):
    """
    Belirtilen gruptan kişileri çeker ve Telegram rehberine kaydeder.
    Kullanım:
      .rehberekle [Grup No] [Adet (30/50/100/200)]
      .rehberekle 50  (Bulunulan gruptan 50 kişi ekler)
      .rehberekle 1 100 (1. gruptan 100 kişi ekler)
    """
    args = message.text.split()[1:] if message.text else []

    gruplar = await get_sorted_user_groups(client)
    hedef_grup = None
    limit = 50

    if len(args) == 0:
        hedef_grup = find_target_group("", gruplar, message.chat.id)
    elif len(args) == 1:
        if args[0].isdigit() and int(args[0]) in [10, 20, 30, 50, 100, 150, 200, 300, 500]:
            limit = int(args[0])
            hedef_grup = find_target_group("", gruplar, message.chat.id)
        else:
            hedef_grup = find_target_group(args[0], gruplar, message.chat.id)
    else:
        hedef_grup = find_target_group(args[0], gruplar, message.chat.id)
        if args[1].isdigit():
            limit = max(1, min(1000, int(args[1])))

    if not hedef_grup:
        await message.edit_text(
            "❌ <b>Grup bulunamadı!</b>\n\n"
            "Önce <code>.rehber</code> yazarak grup numarasını öğrenin.\n"
            "Kullanım: <code>.rehberekle [Grup No] [Adet]</code>\n"
            "<i>Örnek: <code>.rehberekle 1 50</code></i>"
        )
        return

    durum = await message.edit_text(
        f"⏳ <b>{ggr.safe_html(hedef_grup['title'])}</b> grubundan üyeler toplanıyor...\n"
        f"Hedef: <b>{limit}</b> kişi."
    )

    basarili = 0
    hatali = 0
    zaten_ekli = 0
    taranan = 0
    son_guncelleme = time.time()

    try:
        async for member in client.get_chat_members(hedef_grup["id"]):
            user = member.user
            if not is_active_user(user):
                continue
            EntityCache.set_user(user.id, user)

            if user.is_contact:
                zaten_ekli += 1
                continue

            taranan += 1
            ad = user.first_name or "Telegram"
            soyad = user.last_name or f"Kullanıcısı {user.id % 1000}"
            telefon = user.phone_number or ""

            try:
                await client.add_contact(
                    user_id=user.id,
                    first_name=ad,
                    last_name=soyad,
                    phone_number=telefon,
                    share_phone_number=False,
                )
                basarili += 1
                await asyncio.sleep(1.0)
            except FloodWait as fw:
                await durum.edit_text(
                    f"⚠️ <b>FloodWait Sınırı:</b> Telegram {fw.value} saniye beklemenizi istedi.\n"
                    f"İşlem duraklatıldı."
                )
                await asyncio.sleep(fw.value + 1)
            except Exception:
                hatali += 1

            if basarili >= limit:
                break

            if time.time() - son_guncelleme > 3:
                yuzde = int((basarili / limit) * 100)
                await durum.edit_text(
                    f"📥 <b>Gruptan Rehbere Ekleme Sürüyor...</b>\n"
                    f"───────────────────────────\n"
                    f"👥 <b>Grup:</b> <b>{ggr.safe_html(hedef_grup['title'])}</b>\n"
                    f"📊 <b>İlerleme:</b> <code>{basarili}/{limit}</code> (%{yuzde})\n"
                    f"✅ <b>Eklenen:</b> <code>{basarili}</code>\n"
                    f"⏭️ <b>Zaten Rehberde:</b> <code>{zaten_ekli}</code>\n"
                    f"❌ <b>Hata:</b> <code>{hatali}</code>\n"
                    f"⏳ <i>Lütfen bekleyin...</i>"
                )
                son_guncelleme = time.time()

        await durum.edit_text(
            "✅ <b>Rehbere Ekleme İşlemi Başarıyla Tamamlandı!</b>\n"
            "───────────────────────────\n"
            f"👥 <b>Kaynak Grup:</b> <b>{ggr.safe_html(hedef_grup['title'])}</b>\n"
            f"🎯 <b>Hedef:</b> <code>{limit}</code> kişi\n"
            f"✅ <b>Başarıyla Eklenen:</b> <code>{basarili}</code> kişi\n"
            f"⏭️ <b>Zaten Rehberde Olan:</b> <code>{zaten_ekli}</code>\n"
            f"❌ <b>Eklenemeyen / Hata:</b> <code>{hatali}</code>\n"
            "───────────────────────────\n"
            "💡 <i>Kişileri başka gruba eklemek için: <code>.grubaekle [Grup No] {limit}</code></i>"
        )

    except Exception as e:
        await durum.edit_text(
            f"❌ <b>İşlem sırasında hata oluştu:</b>\n<code>{ggr.safe_html(str(e))}</code>"
        )


def _resolve_grubaekle_target(args: List[str], current_chat_id: int, gruplar: List[Dict]):
    limit = 50
    if len(args) == 0:
        return find_target_group("", gruplar, current_chat_id), limit
    if len(args) == 1:
        if args[0].isdigit() and int(args[0]) in [10, 20, 30, 50, 100, 150, 200, 300, 500]:
            return find_target_group("", gruplar, current_chat_id), int(args[0])
        return find_target_group(args[0], gruplar, current_chat_id), limit
    hedef_grup = find_target_group(args[0], gruplar, current_chat_id)
    if args[1].isdigit():
        limit = max(1, min(1000, int(args[1])))
    return hedef_grup, limit


async def _execute_contact_addition(client: Client, chat_id: int, contact):
    try:
        await client.add_chat_members(chat_id, contact.id)
        await asyncio.sleep(1.5)
        return "success"
    except UserAlreadyParticipant:
        return "already"
    except (UserPrivacyRestricted, UserNotMutualContact):
        return "privacy"
    except UserChannelsTooMuch:
        return "other"
    except ChatAdminRequired:
        return "admin_required"
    except PeerFlood:
        return "peer_flood"
    except FloodWait as fw:
        await asyncio.sleep(fw.value + 1)
        return "flood_wait"
    except (RPCError, Exception):
        return "other"


@ggr.cmd(
    ["grubaekle", "davetet"],
    info="Rehberinizdeki kişileri seçilen gruba toplu olarak davet eder.",
    usage=".grubaekle [grup_no] [adet (30/50/100/200)]",
    category=None
)
async def cmd_grubaekle(client: Client, message: Message):
    """
    Telegram rehberinizdeki kişileri seçilen gruba ekler / davet eder.
    Kullanım:
      .grubaekle [Grup No] [Adet (30/50/100/200)]
      .grubaekle 50  (Bulunulan gruba rehberden 50 kişi ekler)
      .grubaekle 2 100 (2. gruba rehberden 100 kişi ekler)
    """
    args = message.text.split()[1:] if message.text else []
    gruplar = await get_sorted_user_groups(client)
    hedef_grup, limit = _resolve_grubaekle_target(args, message.chat.id, gruplar)

    if not hedef_grup:
        await message.edit_text(
            "❌ <b>Hedef grup bulunamadı!</b>\n\n"
            "Önce <code>.rehber</code> yazarak grup numarasını öğrenin.\n"
            "Kullanım: <code>.grubaekle [Grup No] [Adet]</code>\n"
            "<i>Örnek: <code>.grubaekle 2 50</code></i>"
        )
        return

    durum = await message.edit_text(
        f"⏳ Rehber taranıyor ve <b>{ggr.safe_html(hedef_grup['title'])}</b> grubuna davet hazırlanıyor..."
    )

    try:
        contacts = await client.get_contacts()
    except Exception as e:
        await durum.edit_text(f"❌ Rehber alınamadı: <code>{ggr.safe_html(str(e))}</code>")
        return

    if not contacts:
        await durum.edit_text("ℹ️ Rehberinizde eklenebilecek hiç kişi bulunmuyor.")
        return

    basarili = 0
    gizlilik_engeli = 0
    zaten_grupta = 0
    diger_hatalar = 0
    son_guncelleme = time.time()
    chat_id = hedef_grup["id"]

    for contact in contacts:
        if basarili >= limit:
            break
        if contact.is_bot or contact.is_deleted or contact.is_self:
            continue

        res = await _execute_contact_addition(client, chat_id, contact)
        if res == "success":
            basarili += 1
        elif res == "already":
            zaten_grupta += 1
        elif res == "privacy":
            gizlilik_engeli += 1
        elif res == "admin_required":
            await durum.edit_text("❌ <b>Hata:</b> Bu gruba üye ekleme yetkiniz yok veya grup kapalı.")
            return
        elif res == "peer_flood":
            await durum.edit_text(
                "⚠️ <b>PeerFlood (Spam Sınırı):</b> Telegram hesabınız geçici olarak grup davet kısıtlamasına girdi.\n"
                f"Şu ana kadar başarıyla eklenen: <code>{basarili}</code> kişi."
            )
            return
        else:
            diger_hatalar += 1

        if time.time() - son_guncelleme > 3:
            yuzde = int((basarili / limit) * 100)
            await durum.edit_text(
                f"📤 <b>Rehberden Gruba Ekleme Sürüyor...</b>\n"
                f"───────────────────────────\n"
                f"👥 <b>Hedef Grup:</b> <b>{ggr.safe_html(hedef_grup['title'])}</b>\n"
                f"📊 <b>İlerleme:</b> <code>{basarili}/{limit}</code> (%{yuzde})\n"
                f"✅ <b>Eklenen:</b> <code>{basarili}</code>\n"
                f"🔒 <b>Gizlilik Engeli:</b> <code>{gizlilik_engeli}</code>\n"
                f"⏭️ <b>Zaten Grupta:</b> <code>{zaten_grupta}</code>\n"
                f"❌ <b>Diğer Hatalar:</b> <code>{diger_hatalar}</code>\n"
                f"⏳ <i>Lütfen bekleyin...</i>"
            )
            son_guncelleme = time.time()

    await durum.edit_text(
        "✅ <b>Gruba Ekleme İşlemi Başarıyla Tamamlandı!</b>\n"
        "───────────────────────────\n"
        f"👥 <b>Hedef Grup:</b> <b>{ggr.safe_html(hedef_grup['title'])}</b>\n"
        f"🎯 <b>Hedef:</b> <code>{limit}</code> kişi\n"
        f"✅ <b>Başarıyla Eklenen:</b> <code>{basarili}</code> kişi\n"
        f"🔒 <b>Gizlilik Engeli Olan:</b> <code>{gizlilik_engeli}</code> kişi\n"
        f"⏭️ <b>Zaten Üye Olan:</b> <code>{zaten_grupta}</code> kişi\n"
        f"❌ <b>Diğer Nedenlerle Eklenemeyen:</b> <code>{diger_hatalar}</code>\n"
        "───────────────────────────\n"
        "🎉 <i>Tüm işlemler güvenli aralıklarla tamamlandı!</i>"
    )


@ggr.cmd(
    ["rehbersayi", "rehberkac"],
    info="Rehberinizdeki toplam kayıtlı kişi sayısını gösterir.",
    usage=".rehbersayi",
    category=None
)
async def cmd_rehbersayi(client: Client, message: Message):
    """
    Kullanıcının rehberindeki toplam kayıtlı kişi sayısını gösterir.
    """
    durum = await message.edit_text("🔄 <i>Rehber sayılıyor...</i>")
    try:
        count = await client.get_contacts_count()
        await durum.edit_text(
            f"📇 <b>Telegram Rehber Durumu</b>\n"
            f"───────────────────────────\n"
            f"👤 <b>Toplam Kayıtlı Kişi:</b> <code>{count}</code>\n\n"
            f"💡 <i>Grup ve rehber yönetimi için <code>.rehber</code> yazabilirsiniz.</i>"
        )
    except Exception as e:
        await durum.edit_text(f"❌ <b>Hata:</b> <code>{ggr.safe_html(str(e))}</code>")


@ggr.cmd(
    ["rehbersil"],
    info="Bir kullanıcının mesajını yanıtlayarak veya kullanıcı adı/ID belirterek rehberden siler.",
    usage=".rehbersil (yanıtlayarak)",
    category=None
)
async def cmd_rehbersil(client: Client, message: Message):
    """
    Yanıtlanan kullanıcıyı veya belirtilen kullanıcıyı rehberden siler.
    Kullanım: .rehbersil (mesajı yanıtlayarak veya kullanıcı adı/ID ile)
    """
    args = message.text.split()[1:] if message.text else []
    target_user = None

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
    elif args:
        try:
            target_user = await client.get_users(args[0])
        except Exception:
            target_user = None

    if not target_user:
        await message.edit_text(
            "❌ <b>Kullanıcı belirlenemedi!</b>\n"
            "Bir kullanıcının mesajını yanıtlayarak <code>.rehbersil</code> yazın veya kullanıcı adı/ID girin."
        )
        return

    durum = await message.edit_text("⏳ <i>Kişi rehberden siliniyor...</i>")
    try:
        await client.delete_contacts([target_user.id])
        await durum.edit_text(
            f"🗑️ <b>{ggr.safe_html(target_user.first_name)}</b> rehberinizden başarıyla silindi."
        )
    except Exception as e:
        await durum.edit_text(f"❌ <b>Hata:</b> <code>{ggr.safe_html(str(e))}</code>")


@ggr.cmd(
    ["rehbertemizle"],
    info="Rehberdeki kişileri toplu olarak temizler (Onay gerektirir).",
    usage=".rehbertemizle onayla",
    category=None
)
async def cmd_rehbertemizle(client: Client, message: Message):
    """
    Rehberdeki tüm kişileri siler (Güvenlik onayı gerektirir).
    Kullanım: .rehbertemizle onayla
    """
    args = message.text.split()[1:] if message.text else []
    if not args or args[0].lower() != "onayla":
        await message.edit_text(
            "⚠️ <b>DİKKAT: Rehber Temizleme İşlemi!</b>\n\n"
            "Bu işlem Telegram rehberinizdeki <b>TÜM</b> kişileri silecektir.\n"
            "Onaylamak için tam olarak şu komutu yazın:\n"
            "👉 <code>.rehbertemizle onayla</code>"
        )
        return

    durum = await message.edit_text("🔄 <i>Rehber taranıyor...</i>")
    try:
        contacts = await client.get_contacts()
        if not contacts:
            await durum.edit_text("ℹ️ Rehberiniz zaten boş.")
            return

        toplam = len(contacts)
        await durum.edit_text(f"🗑️ <b>{toplam}</b> kişi rehberden temizleniyor, lütfen bekleyin...")

        contact_ids = [c.id for c in contacts]
        silinen = 0
        for i in range(0, len(contact_ids), 50):
            parca = contact_ids[i:i + 50]
            await client.delete_contacts(parca)
            silinen += len(parca)
            await asyncio.sleep(0.5)

        await durum.edit_text(
            f"✅ <b>Rehber Temizlendi!</b>\n"
            f"Toplam <code>{silinen}</code> kişi başarıyla rehberden kaldırıldı."
        )
    except Exception as e:
        await durum.edit_text(f"❌ <b>Hata:</b> <code>{ggr.safe_html(str(e))}</code>")
