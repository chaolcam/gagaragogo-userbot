# -----------------------------------------------------------------------------
# Project: GagaraGogo Userbot
# Component: URL Shortener & Link Bypasser Tool
# Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
# License: GNU GPL v3.0
# Copyright (c) 2026 chaolcam
# -----------------------------------------------------------------------------
import re
import logging
import urllib.parse
from urllib.parse import urlparse
import requests as std_requests
from curl_cffi import requests
from bs4 import BeautifulSoup
from utils import ggr


def RecaptchaV3():
    """Google reCAPTCHA v3 token üretici."""
    ANCHOR_URL = 'https://www.google.com/recaptcha/api2/anchor?ar=1&k=6Lcr1ncUAAAAAH3cghg6cOTPGARa8adOf-y9zv2x&co=aHR0cHM6Ly9vdW8ucHJlc3M6NDQz&hl=en&v=pCoGBhjs9s8EhFOHJFe8cqis&size=invisible&cb=ahgyd1gkfkhe'
    url_base = 'https://www.google.com/recaptcha/'
    post_data = "v={}&reason=q&c={}&k={}&co={}"
    client = std_requests.Session()
    client.headers.update({'content-type': 'application/x-www-form-urlencoded'})
    
    matches = re.findall(r'([api2|enterprise]+)\/anchor\?(.*)', ANCHOR_URL)[0]
    url_base += matches[0]+'/'
    params_str = matches[1]
    params_dict = dict(pair.split('=') for pair in params_str.split('&'))
    res = client.get(url_base+'anchor', params=params_dict, timeout=15)
    token = re.findall(r'recaptcha-token.*?value=[\'"]([^\'"]+)', res.text)[0]
    post_data = post_data.format(params_dict["v"], token, params_dict["k"], params_dict["co"])
    res = client.post(url_base+'reload', params={'k': params_dict["k"]}, data=post_data, timeout=15)
    answer = re.findall(r'"rresp","(.*?)"', res.text)[0]
    return answer

def bypass_ouo(url):
    """Ouo.io ve Ouo.press reklamlı reCAPTCHA korumasını aşar."""
    url_str = str(url).strip()
    parsed = urlparse(url_str)
    original_host = parsed.hostname or "ouo.press"
    alt_host = "ouo.io" if "press" in original_host else "ouo.press"
    link_id = str(parsed.path).strip("/").split("/")[-1]
    
    for host in [original_host, alt_host]:
        for _ in range(2):
            try:
                client = requests.Session(impersonate="safari15_5")
                client.headers.update({
                    'authority': host,
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'accept-language': 'en-US,en;q=0.9',
                    'referer': 'https://www.google.com/',
                    'upgrade-insecure-requests': '1'
                })
                
                target_url = f"https://{host}/{link_id}"
                res = client.get(target_url, timeout=20)
                next_url = f"https://{host}/go/{link_id}"
                
                for _ in range(2):
                    if res.headers.get('Location'):
                        return res.headers.get('Location')
                        
                    bs4 = BeautifulSoup(res.content, 'html.parser')
                    if bs4.form is None:
                        break
                        
                    inputs = bs4.form.find_all("input", {"name": re.compile(r"token$")})
                    data = {input.get('name'): input.get('value') for input in inputs}
                    data['x-token'] = RecaptchaV3()
                    
                    h = {'content-type': 'application/x-www-form-urlencoded'}
                    
                    res = client.post(
                        next_url,
                        data=data,
                        headers=h,
                        allow_redirects=False,
                        timeout=20
                    )
                    next_url = f"https://{host}/xreallcygo/{link_id}"
                    
                if res.headers.get('Location'):
                    return res.headers.get('Location')
            except Exception as _byp_err:
                logging.debug("Droplink bypass denemesi hatası: %s", _byp_err)
                continue
                
    return None

def unshorten_redirect(url):
    """TinyURL, Bitly, CleanURI, is.gd, clck.ru gibi standart yönlendirmeli linkleri çözer."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = std_requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        final_target = r.url
        if "preview" in final_target:
            r2 = std_requests.get(final_target, allow_redirects=True, timeout=15)
            final_target = r2.url
        if final_target and final_target != url:
            return final_target
    except Exception as _exc:
        logging.debug("Suppressed: %s", _exc)
    return None

def tek_adim_bypass(url):
    """Gelen linkin türüne göre uygun bypass motorunu çalıştırır."""
    url = url.strip()
    if "ouo.io" in url or "ouo.press" in url:
        return bypass_ouo(url)
    
    # Standart kısaltıcıları çözmeyi dene
    redirect_res = unshorten_redirect(url)
    if redirect_res:
        return redirect_res
        
    return None

async def zincirleme_bypass(url):
    """Tek bir linki iç içe yönlendirmeler bitene kadar (maksimum 5 aşama) çözer."""
    import asyncio
    current_url = url
    final_url = None
    for _ in range(5):
        result = await asyncio.to_thread(tek_adim_bypass, current_url)
        if not result or result == current_url:
            break
        final_url = result
        if any(k in result for k in ["ouo.io", "ouo.press", "tinyurl.com", "bit.ly", "cleanuri.com", "is.gd", "t.co", "cutt.ly"]):
            current_url = result
        else:
            break
    return final_url

@ggr.cmd(
    "bypass",
    info="Ouo.io, Ouo.press, TinyURL, Bitly, CleanURI ve tüm kısa/reklamlı linkleri aşarak asıl hedef URL'yi çıkarır.",
    usage=".bypass [link] ya da linke yanıt vererek .bypass",
    category="Araçlar"
)
async def bypass_cmd(client, message):
    target_text = ""
    if len(message.command) > 1:
        target_text = message.text.split(maxsplit=1)[1]
    elif message.reply_to_message:
        target_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        
    raw_links = re.findall(r'https?://[^\s<>"]+', target_text)
    if not raw_links:
        await message.edit_text("❌ Lütfen çözülecek link(ler) girin ya da link içeren bir mesajı yanıtlayarak `.bypass` yazın.\n\nÖrnekler:\n• Tek link: `.bypass https://ouo.press/xxxxx`\n• Çoklu link: `.bypass link1 link2 link3`\n• Mesaja yanıtla: Mesajı yanıtlayıp `.bypass`")
        return
        
    # Linklerin sonundaki noktalama işaretlerini temizle ve tekrarları kaldır
    links = []
    for lnk in raw_links:
        clean_lnk = lnk.rstrip(".,;)>]")
        if clean_lnk not in links:
            links.append(clean_lnk)
            
    toplam = len(links)
    
    # 1. TEK LİNK DURUMU
    if toplam == 1:
        url = links[0]
        await message.edit_text(f"⏳ <i>Link çözülüyor:</i> <code>{url}</code>\nLütfen bekleyin...")
        try:
            final_url = await zincirleme_bypass(url)
            if final_url:
                await message.edit_text(
                    "✅ <b>Bypass Başarılı!</b>\n\n"
                    f"🔗 <b>Orijinal:</b> <code>{url}</code>\n"
                    f"🎯 <b>Hedef:</b>\n<code>{final_url}</code>", 
                    disable_web_page_preview=True
                )
            else:
                await message.edit_text("❌ Link çözülemedi veya yönlendirme bulunamadı.")
        except Exception as e:
            await message.edit_text(f"❌ Hata: <code>{str(e)}</code>")
        return

    # 2. ÇOKLU LİNK DURUMU (Birden fazla link)
    await message.edit_text(f"⏳ <b>Toplu Bypass Başlatıldı:</b> Toplam <code>{toplam}</code> link tespit edildi...\n(0/{toplam} tamamlandı)")
    
    sonuclar = []
    basarili_sayisi = 0
    
    for idx, url in enumerate(links, start=1):
        try:
            await message.edit_text(f"⏳ <i>Linkler çözülüyor:</i> ({idx}/{toplam})\n<code>{url}</code>")
            final_url = await zincirleme_bypass(url)
            if final_url:
                sonuclar.append(f"<b>{idx}.</b> <code>{url}</code>\n➡️ <code>{final_url}</code>")
                basarili_sayisi += 1
            else:
                sonuclar.append(f"<b>{idx}.</b> <code>{url}</code>\n❌ <i>Çözülemedi</i>")
        except Exception:
            sonuclar.append(f"<b>{idx}.</b> <code>{url}</code>\n❌ <i>Hata oluştu</i>")
            
    rapor = (
        f"✅ <b>Toplu Bypass Tamamlandı!</b> ({basarili_sayisi}/{toplam} Başarılı)\n"
        "──────────────────────────────\n\n"
        + "\n\n".join(sonuclar)
    )
    
    await message.edit_text(rapor, disable_web_page_preview=True)
