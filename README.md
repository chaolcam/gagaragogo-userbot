# GagaraGogo Userbot

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pyrogram v2](https://img.shields.io/badge/Pyrogram-v2.0-orange?style=flat-square)](https://docs.pyrogram.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Kurulum Botu](https://img.shields.io/badge/Telegram-Kurulum%20Botu-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://t.me/GagaragogoKurulumBot)
[![Deploy to Render](https://img.shields.io/badge/Deploy-Render-black?style=flat-square&logo=render)](https://render.com/deploy?repo=https://github.com/chaolcam/gagaragogo-userbot)

Pyrogram v2 tabanlı; otomatik forum özellikli arşiv grubu yönetimi, çoklu platform medya indiricisi, TikTok canlı yayın/gönderi kaydedicisi, Instagram içerik yöneticisi, özel eklenti motoru, otomesaj zamanlayıcısı, özel sohbetler için anti-delete ve reklamlı kısa linkleri çözen evrensel bypass motoruna sahip açık kaynaklı yeni nesil Telegram kullanıcı botu.

---

## ⚠️ Sorumluluk Reddi Beyanı (Disclaimer)

> **Önemli Bilgilendirme:**
> - Userbot kullanımından dolayı Telegram hesabınız sınırlandırılabilir veya yasaklanabilir.
> - Bu bir açık kaynaklı projedir; yaptığınız her işlemden, paylaştığınız içeriklerden ve hesabınızdan **bizzat kendiniz sorumlusunuz**.
> - Kesinlikle **GagaraGogo geliştiricileri ve yöneticileri hiçbir sorumluluk kabul etmemektedir**.
> - GagaraGogo Userbot'u kurarak, kullanarak veya çalıştırarak bu sorumlulukları ve kullanım şartlarını peşinen kabul etmiş sayılırsınız.

---

## 🚀 Hızlı Kurulum Seçenekleri

### 1. Otomatik Telegram Kurulum Asistanı (En Kolay & Önerilen)
Hiçbir kodlama yapmadan, konsol açmadan botunuzu saniyeler içinde kurmak için resmi Telegram asistanımızı başlatabilirsiniz:
👉 **[@GagaragogoKurulumBot](https://t.me/GagaragogoKurulumBot)**

*Bu asistan; Render API anahtarınızı bağlar, API ID & Hash alır, String Session üretir, @BotFather üzerinden yardımcı botunuzu açar ve servisinizi tek tıkla canlıya alır.*  
*(Kurulum botunun açık kaynak kodlarına [gagaragogo-kurulum-bot](https://github.com/chaolcam/gagaragogo-kurulum-bot) adresinden ulaşabilirsiniz).*

### 2. Render ile Tek Tıkla Deploy
Aşağıdaki butona basarak doğrudan Render Dashboard üzerinden yapılandırabilirsiniz:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/chaolcam/gagaragogo-userbot)

### 3. Yerel / Sunucu (VPS) Manuel Kurulum
```bash
# Depoyu klonlayın
git clone https://github.com/chaolcam/gagaragogo-userbot.git
cd gagaragogo-userbot

# Gerekli bağımlılıkları yükleyin
pip install -r requirements.txt

# Çevre değişkenlerini ayarlayın
cp example.env .env
# .env dosyasını kendi API_ID, API_HASH ve STRING_SESSION değerlerinizle düzenleyin

# Botu başlatın
python3 main.py
```

---

## ✨ Öne Çıkan Özellikler

* **Otomatik Admin & Arşiv Grubu:** Kurulumda grup ya da konu ID'si tanımlamanıza gerek kalmaz. Bot ilk çalıştığında forum özellikli bir süper grup açar, yardımcı botu yönetici olarak ekler ve tüm alt konuları (`Sistem Logları`, `Silinen Mesajlar`, `Süreli Medyalar`, `TikTok Konuları`) otomatik oluşturur.
* **Kalıcı Tek Bulut Veritabanı:** Tüm ayarlar, grup eşleşmeleri, otomesajlar ve özel eklentiler Telegram *Kayıtlı Mesajlar* kutunuzdaki TEK bir güvenli mesajda saklanır. Güncellemeler mevcut mesaj düzenlenerek (`edit`) yapılır; sunucu kapansa veya yeniden kurulsa bile bot verilerini hatırlar ve mükerrer grup açmaz.
* **Instagram Medya & Profil Yöneticisi:** Hikayeler (`.igstory`), gönderiler (`.igpost`), profil bilgileri (`.igprofile`) ve öne çıkanlar (`.ighighlights`) doğrudan sohbete indirilir.
* **TikTok Canlı Yayın & Gönderi Takibi:** Canlı yayınları otomatik kaydeder, profildeki yeni videoları filigransız HD ve kaydırmalı albüm formatında arşive yükler (`.tt`, `.tt_ekle`).
* **Dinamik Eklenti Sistemi (`.eklenti`):** Botu yeniden başlatmadan `.eklenti yukle` ile Telegram'dan Python dosyası yükleyebilir, silebilir ve yönetebilirsiniz. Yüklenen eklentiler otomatik bulut yedeğe alınır.
* **Otomesaj Zamanlayıcı (`.otomesaj`):** Belirlediğiniz aralıklarla istediğiniz sohbetlere otomatik mesaj gönderimi sağlar.
* **Evrensel Link Bypasser (`.bypass`):** Ouo.io, Ouo.press, TinyURL, CleanURI, Bitly ve clck.ru gibi reklamlı ya da kısaltılmış linkleri tekli veya çoklu olarak anında asıl hedef adresine çözer.
* **Anti-Delete (Yalnızca Özel Sohbetler):** Karşı taraf özel mesajı sildiği anda içeriği gönderen profiliyle birlikte arşiv konusuna iletir.
* **Süreli Medya Yakalayıcı:** Tek gösterimlik veya süreli fotoğraf/videoları yakalayarak kalıcı kopyasını yönetici grubuna arşivler.
* **Gelişmiş Araçlar:** `.afk`, `.delme`, `.lock/.unlock`, `.whois`, `.ocr`, `.type`, `.tts`, `.cevir`, `.lyrics` ve çok daha fazlası.
* **Düşük Kaynak Tüketimi & Bellek Temizleyici:** Render ücretsiz planındaki 512 MB RAM ve 5 GB disk sınırlarına uygun periyodik bellek temizleyicisi (`gc.collect`) ve geçici dosya temizleme mekanizması içerir.

---

## 🔑 Çevre Değişkenleri (Environment Variables)

| Değişken | Açıklama | Durum |
| :--- | :--- | :--- |
| `API_ID` | Telegram API ID ([my.telegram.org](https://my.telegram.org)) | Zorunlu (Varsayılan fallback: `2040`) |
| `API_HASH` | Telegram API Hash ([my.telegram.org](https://my.telegram.org)) | Zorunlu |
| `STRING_SESSION` | Pyrogram v2 oturum dizesi (String Session) | Zorunlu |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) üzerinden alınan yardımcı bot tokeni | Opsiyonel (Önerilir) |
| `RAPIDAPI_KEYS` | Instagram araçları için RapidAPI anahtarı (virgülle çoklu eklenebilir) | Opsiyonel |
| `YEDEK_GRUP_ID` | Önceden var olan bir grubu bağlamak için grup ID'si (Boş bırakılırsa otomatik açılır) | Opsiyonel |
| `PORT` | Web sağlık kontrolü sunucu portu (Varsayılan: `8080`) | Otomatik |

Detaylı örnek yapılandırma için [example.env](example.env) dosyasını inceleyebilirsiniz.

---

## ⚡ Render 7/24 Kesintisiz Çalışma (UptimeRobot)

Render ücretsiz web servisleri 15 dakika boyunca HTTP isteği almadığında uyku moduna geçer. Botun kapanmadan sürekli aktif kalması için dahili port dinleyicisi bulunmaktadır:

1. [UptimeRobot](https://uptimerobot.com) üzerinde ücretsiz bir hesap oluşturun.
2. **+ Add New Monitor** seçeneğini açın:
   * **Monitor Type:** `HTTP(s)`
   * **Friendly Name:** `GagaraGogo Userbot`
   * **URL (or IP):** Size özel canlı Render web linkiniz (örn: `https://gagaragogo-userbot.onrender.com`)
   * **Monitoring Interval:** `5 minutes`
3. Monitörü kaydedin. Botunuz periyodik sağlık sinyalleri alarak 7/24 kesintisiz çalışır.

---

## 📖 Komut Rehberi

Tüm komutların parametreleri ve detaylı kullanım senaryoları için **[KOMUTLAR_VE_OZELLIKLER.md](KOMUTLAR_VE_OZELLIKLER.md)** kılavuzuna göz atabilirsiniz.

Hızlı bir özet:
* `.yardim` — Butonlu interaktif menüyü açar.
* `.ayarlar` — Modülleri açıp kapatabileceğiniz paneli gösterir.
* `.durum` — CPU, RAM, Disk ve uptime durumunu listeler.
* `.bypass [link1] [link2]...` — Kısa ve reklamlı linkleri çözer.
* `.tt`, `.yt`, `.x`, `.rd` — Sosyal medya medyalarını doğrudan sohbete indirir.
* `.igstory`, `.igpost`, `.igprofile` — Instagram içeriklerini yönetir.
* `.antidelete on / off` — Özel sohbetlerde silinen mesaj takibini yönetir.
* `.sureli on / off` — Süreli medya korumasını açar / kapatır.
* `.eklenti` — Özel eklentileri yükler, siler veya listeler.
* `.otomesaj` — Otomatik mesaj zamanlayıcısını yönetir.

---

## 📜 Lisans

Bu proje **MIT Lisansı** kapsamında yayınlanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakabilirsiniz.