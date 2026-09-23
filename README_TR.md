# GagaraGogo Userbot

Pyrogram v2 ve MTProto altyapısıyla geliştirilmiş, Telegram için modüler ve yüksek performanslı açık kaynaklı kullanıcı botu.

[![CodeFactor](https://www.codefactor.io/repository/github/chaolcam/gagaragogo-userbot/badge)](https://www.codefactor.io/repository/github/chaolcam/gagaragogo-userbot)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pyrogram v2](https://img.shields.io/badge/Framework-Pyrogram%20v2-orange?style=flat-square&logo=telegram)](https://docs.pyrogram.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3.0-blue.svg?style=flat-square)](LICENSE)
[![Deploy on Render](https://img.shields.io/badge/Deploy-Render-black?style=flat-square&logo=render)](https://render.com/deploy?repo=https://github.com/chaolcam/gagaragogo-userbot)

---

## Mimari Özellikleri

- **Hibrit İstemci:** Kullanıcı oturumu (MTProto Client) ile yardımcı botu (`@BotFather`) senkronize ederek interaktif inline arayüzler ve bildirimler sunar.
- **Sunucusuz / Yerel Veri Katmanı:** Harici bir veritabanı (Redis, Mongo vb.) gerektirmez. Yapılandırma ve durum bilgileri Telegram *Kayıtlı Mesajlar* üzerinde JSON dokümanı olarak güvenle saklanır ve taşınabilir kalır.
- **Otonom Arşiv ve Forum Yapısı:** İlk çalıştırmada loglar, süreli medyalar ve silinen mesajlar için otomatik bir süper grup açarak forum başlıklarına ayrıştırır.
- **Bellek ve Kaynak Yönetimi:** LRU önbellekleri, otomatik çöp toplayıcı (GC) ve geçici dosya temizliği sayesinde 512 MB RAM kısıtlı ortamlarda (Render, mikro VPS) stabil çalışır.
- **Dinamik Modül Yükleme:** Bot oturumunu kesintiye uğratmadan Telegram üzerinden `.install` komutuyla yeni eklentiler yüklenebilir ve yönetilebilir.

---

## Hızlı Başlangıç

### 1. Kolay Kurulum (Telegram Asistanı)

Konsol erişimine gerek duymadan session üretimi ve Render dağıtımını otomatik yapan bot:
👉 **[@GagaragogoKurulumBot](https://t.me/GagaragogoKurulumBot)**

### 2. Tek Tıkla Deploy (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/chaolcam/gagaragogo-userbot)

### 3. Manuel Kurulum (Linux / VPS)

```bash
# Repoyu klonlayın
git clone https://github.com/chaolcam/gagaragogo-userbot.git
cd gagaragogo-userbot

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Çevre değişkenlerini yapılandırın
cp example.env .env
nano .env

# Başlatın
python3 main.py
```

*Docker ile çalıştırmak için:*
```bash
docker build -t gagaragogo-userbot .
docker run --env-file .env -d gagaragogo-userbot
```

---

## Ortam Değişkenleri

| Değişken | Açıklama | Durum |
| :--- | :--- | :---: |
| `API_ID` | Telegram API ID ([my.telegram.org](https://my.telegram.org)) | **Zorunlu** |
| `API_HASH` | Telegram API Hash ([my.telegram.org](https://my.telegram.org)) | **Zorunlu** |
| `STRING_SESSION` | Pyrogram v2 oturum dizesi | **Zorunlu** |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) yardımcı bot belirteci | Önerilen |
| `RAPIDAPI_KEYS` | Instagram/Medya API anahtarları (virgülle ayrılmış) | Opsiyonel |
| `YEDEK_GRUP_ID` | Mevcut yönetim grubu ID'si (boşsa otomatik açılır) | Opsiyonel |
| `PORT` | Health-check HTTP portu (varsayılan: `8080`) | Opsiyonel |

---

## Temel Yetenekler & Komutlar

| Kategori | Komut / İşlem | Açıklama |
| :--- | :--- | :--- |
| **Kontrol Paneli** | `.yardim` / `.ayarlar` | İnteraktif butonlu yardım ve modül konfigürasyonu. |
| **Grup & İletişim** | `.rehber`, `.ilet`, `.otomesaj` | Üye listeleme/aktarımı, seçili sohbetlere toplu ve zamanlanmış mesaj yayını. |
| **Medya Çözücü** | `.tt`, `.igstory`, `.igpost`, `.yt` | TikTok (canlı yayın kaydı + HD video), Instagram ve YouTube medya indirme. |
| **Gizlilik & Arşiv** | `.antidelete`, `.sureli` | Silinen özel mesajları ve süreli medyaları otomatik yakalayıp forumda arşivleme. |
| **Link Çözücü** | `.bypass <link>` | Reklamlı ve kısaltılmış linklerin (ouo, bitly vb.) asıl adresini çözer. |
| **Sistem** | `.update`, `.restart`, `.ping` | GitHub üzerinden canlı güncelleme ve çalışma durumu kontrolü. |

Detaylı kullanım senaryoları, parametreler ve mimari dokümantasyon için:  
📄 **[KOMUTLAR_VE_OZELLIKLER.md](KOMUTLAR_VE_OZELLIKLER.md)**

---

## Uyarı ve Lisans

Bu proje kişisel otomasyon ve geliştirme amacıyla sunulmuştur. Telegram Hizmet Şartları çerçevesinde hesap yönetimi kullanıcıya aittir; olası kısıtlamalardan geliştirici sorumlu tutulamaz.

Lisans: [GNU General Public License v3.0](LICENSE)