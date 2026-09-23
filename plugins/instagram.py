# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: Instagram Media & Story Downloader
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import os
import random
import asyncio
import logging
import requests
from cachetools import cached, TTLCache
from utils import ggr

API_KALAN_LIMIT = "RapidAPI Rotasyonu"

RAPIDAPI_YARDIM_METNI = (
    "🔑 <b>Instagram Araçları İçin RapidAPI Anahtarı Gerekli!</b>\n\n"
    "Instagram hikaye, gönderi ve profil özelliklerini (<code>.ig</code>) "
    "kullanabilmek için RapidAPI anahtarınızı bota kaydetmeniz gerekmektedir.\n\n"
    "💡 <b>Nasıl Ücretsiz Alınır?</b>\n"
    "1️⃣ <a href='https://rapidapi.com/auth/sign-up'>rapidapi.com</a> adresine gidip ücretsiz üye olun.\n"
    "2️⃣ Arama kısmından aşağıdaki iki API'ye gidip <b>Subscribe (Free Plan)</b> ile ücretsiz abone olun:\n"
    "   • <a href='https://rapidapi.com/mranyx/api/instagram-looter2'>Instagram Looter</a>\n"
    "   • <a href='https://rapidapi.com/social-api1-social-api1-default/api/instagram-best-experience'>Instagram Best Experience</a>\n"
    "3️⃣ Sayfada yer alan <code>X-RapidAPI-Key</code> değerinizi kopyalayın.\n\n"
    "👉 <b>Bota Kaydetmek İçin:</b>\n"
    "<code>.rapidapi [anahtarınız]</code>\n"
    "<i>(Birden fazla anahtar eklemek için virgülle ayırabilirsiniz: <code>.rapidapi key1, key2</code>)</i>\n\n"
    "🔒 <i>Eklediğiniz anahtarlar Telegram Bulut Veritabanı'na kalıcı olarak yedeklenir. Sunucu kapansa bile asla silinmez!</i>"
)

def get_rapidapi_keys_list():
    """Veritabanından (ggr) veya ortam değişkenlerinden RapidAPI anahtarlarını liste olarak döner."""
    keys_db = ggr.get("rapidapi_keys")
    keys_env = os.getenv("RAPIDAPI_KEYS")
    keys_kaynak = keys_db if keys_db else (keys_env if keys_env and str(keys_env).strip() != "0" else "")
    if isinstance(keys_kaynak, list):
        return [str(k).strip() for k in keys_kaynak if str(k).strip() and str(k).strip() != "0"]
    return [k.strip() for k in str(keys_kaynak).split(",") if k.strip() and k.strip() != "0"]

def get_rapidapi_headers():
    """Çoklu RapidAPI anahtarları arasından rastgele bir anahtar seçerek rotasyon sağlar."""
    keys = get_rapidapi_keys_list()
    if not keys:
        raise Exception("RAPIDAPI_KEYS tanımlanmamış. Instagram özelliklerini kullanmak için geçerli bir RapidAPI anahtarı gereklidir.")
    return random.choice(keys)

@ggr.cmd(["rapidapi", "rapidkey", "igkey"], info="Instagram özellikleri için RapidAPI anahtarlarını yönetir.", usage=".rapidapi [anahtar1, anahtar2 | sil]", category="Araçlar")
async def rapidapi_yonet(client, message):
    args = message.text.split()[1:] if message.text else []
    
    # 1. Silme İşlemi (.rapidapi sil / reset / clear)
    if args and args[0].lower() in ["sil", "reset", "clear", "kaldir"]:
        ggr.set("rapidapi_keys", "")
        await ggr.sync_cloud(client)
        await message.edit_text(ggr.t("rapidapi_cleared"))
        return
        
    # 2. Anahtar Ekleme / Güncelleme
    if len(message.command) > 1:
        girilen = message.text.split(maxsplit=1)[1].strip()
        anahtarlar = [k.strip() for k in girilen.replace("\n", ",").split(",") if k.strip() and k.strip() != "0"]
        if not anahtarlar:
            await message.edit_text(ggr.t("rapidapi_invalid"))
            return
            
        kaydedilecek = ", ".join(anahtarlar)
        ggr.set("rapidapi_keys", kaydedilecek)
        await ggr.sync_cloud(client)
        
        await message.edit_text(ggr.t("rapidapi_saved", count=len(anahtarlar)))
        return

    # 3. Argümansız Kullanım: Durum Göster veya Rehber
    mevcut_anahtarlar = get_rapidapi_keys_list()
    if mevcut_anahtarlar:
        maskeli_list = []
        for k in mevcut_anahtarlar:
            if len(k) > 8:
                maskeli_list.append(f"<code>{k[:4]}...{k[-4:]}</code>")
            else:
                maskeli_list.append(f"<code>{k[:2]}...</code>")
        maskeli_metin = "\n• ".join(maskeli_list)
        
        await message.edit_text(
            f"✅ <b>RapidAPI Anahtarınız Aktif!</b>\n\n"
            f"🔑 <b>Kayıtlı Anahtarlar ({len(mevcut_anahtarlar)} Adet):</b>\n• {maskeli_metin}\n\n"
            f"🔒 <b>Telegram Bulut Veritabanı</b>'na kayıtlıdır. Sunucu yeniden başlasa bile otomatik korunur.\n\n"
            f"• <i>Yeni anahtar eklemek/güncellemek:</i> <code>.rapidapi [yeni_anahtar]</code>\n"
            f"• <i>Anahtarları silmek:</i> <code>.rapidapi sil</code>"
        )
    else:
        await message.edit_text(RAPIDAPI_YARDIM_METNI, disable_web_page_preview=True)

@cached(cache=TTLCache(maxsize=100, ttl=7200))
def get_user_id(username):
    """Instagram kullanıcı ID'sini ve profil bilgilerini bellekte 2 saat önbelleğe alarak API kotasını korur."""
    headers = {
        "x-rapidapi-key": get_rapidapi_headers(),
        "x-rapidapi-host": "instagram-looter2.p.rapidapi.com",
    }
    res = requests.get("https://instagram-looter2.p.rapidapi.com/profile", headers=headers, params={"username": username})
    if res.status_code != 200:
        if res.status_code in (401, 403):
            raise Exception("RapidAPI anahtarı yetkisiz veya geçersiz! Lütfen 'instagram-looter2' API'sine abone olduğunuzdan emin olun.")
        elif res.status_code == 429:
            raise Exception("RapidAPI aylık istek kotanız doldu! Yeni bir anahtar eklemek için: .rapidapi [yeni_anahtar]")
        raise Exception(f"Profil çekilemedi (Kod {res.status_code}): {res.text[:120]}")
    return res.json()

def _check_rapidapi_response(res, api_name, label):
    """RapidAPI yanıt durum kodlarını denetler."""
    if res.status_code != 200:
        if res.status_code in (401, 403):
            raise Exception(f"RapidAPI anahtarı yetkisiz! Lütfen '{api_name}' API'sine abone olduğunuzdan emin olun.")
        elif res.status_code == 429:
            raise Exception("RapidAPI istek kotanız doldu! Yeni anahtar eklemek için: .rapidapi [yeni_anahtar]")
        raise Exception(f"{label} çekilemedi (Kod {res.status_code}): {res.text[:120]}")


def _fetch_ig_posts(user_id):
    """Kullanıcının gönderilerini çeker."""
    headers = {
        "x-rapidapi-key": get_rapidapi_headers(),
        "x-rapidapi-host": "instagram-looter2.p.rapidapi.com",
    }
    res = requests.get("https://instagram-looter2.p.rapidapi.com/user-feeds", headers=headers, params={"id": user_id, "count": "12"})
    _check_rapidapi_response(res, "instagram-looter2", "Gönderiler")
    
    data = res.json()
    posts_result = []
    for post in data.get("items", []):
        obj = {"pk": post.get("id")}
        if post.get("media_type") == 2:
            obj["video_versions"] = post.get("video_versions", [])
        else:
            obj["image_versions2"] = post.get("image_versions2", {})
        posts_result.append({"node": obj})
    posts_result.reverse()
    return {"result": {"edges": posts_result}}


def _fetch_ig_stories_or_highlights(user_id, endpoint):
    """Kullanıcının hikayelerini veya öne çıkanlarını çeker."""
    headers = {
        "x-rapidapi-key": get_rapidapi_headers(),
        "x-rapidapi-host": "instagram-best-experience.p.rapidapi.com",
    }
    url = f"https://instagram-best-experience.p.rapidapi.com/{endpoint}"
    params = {"user_id": user_id}
    res = requests.get(url, headers=headers, params=params)
    label = "Hikayeler" if endpoint == "stories" else "Öne çıkanlar"
    _check_rapidapi_response(res, "instagram-best-experience", label)

    data = res.json()
    result = []
    for item in data:
        obj = {"pk": item.get("id")}
        if item.get("media_type") == 2:
            obj["video_versions"] = item.get("video_versions", [])
        else:
            obj["image_versions2"] = item.get("image_versions2", {})
        result.append(obj)
    return {"result": result}


# Instagram sonuçlarını bellekte 15 dakika (900 saniye) boyunca saklar
@cached(cache=TTLCache(maxsize=50, ttl=900))
def fetch_instagram_data(endpoint, username):
    profile_data = get_user_id(username)
    user_id = profile_data.get("id")
    if not user_id:
        raise Exception("Kullanıcı ID'si bulunamadı!")
        
    if endpoint == "profile":
        return {"result": {"profile_pic_url": profile_data.get("profile_pic_url"), "full_name": profile_data.get("full_name")}}
    if endpoint == "posts":
        return _fetch_ig_posts(user_id)
    if endpoint in ("stories", "highlights"):
        return _fetch_ig_stories_or_highlights(user_id, endpoint)
    return {}

def extract_media_url(item):
    if "video_versions" in item and item["video_versions"]:
        return item["video_versions"][0]["url"], "mp4"
    elif "image_versions2" in item and item["image_versions2"] and "candidates" in item["image_versions2"]:
        return item["image_versions2"]["candidates"][0]["url"], "jpg"
    return None, None

@ggr.cmd(["ig", "igstory", "igpost"], info="Instagram profili için butonlu hikaye, gönderi ve öne çıkanlar menüsü açar.", usage=".ig [kullanıcı_adı]", category="Araçlar")
async def ig_interactive(client, message):
    if len(message.command) < 2:
        await message.edit_text(ggr.t("err_missing_args"))
        return
        
    username = message.command[1].strip("@")
    
    if not get_rapidapi_keys_list():
        await message.edit_text(RAPIDAPI_YARDIM_METNI, disable_web_page_preview=True)
        return
    
    # Yardımcı botu sorgula
    import utils
    if not hasattr(utils, "YARDIMCI_BOT_USERNAME") or not utils.YARDIMCI_BOT_USERNAME:
        await message.edit_text(ggr.t("err_bot_not_active_inline"))
        return
        
    try:
        results = await client.get_inline_bot_results(utils.YARDIMCI_BOT_USERNAME, f"ig {username}")
        if results and results.results:
            await utils.send_inline_result_in_context(
                client,
                message,
                results.query_id,
                results.results[0].id
            )
            await message.delete()
        else:
            await message.edit_text(ggr.t("err_general", error="No inline results"))
    except Exception as e:
        await message.edit_text(ggr.t("err_general", error=str(e)))
