<!--
-----------------------------------------------------------------------------
Project: GagaraGogo Userbot
Component: Documentation: Commands & Architecture Reference
Author: chaolcam (https://github.com/chaolcam/gagaragogo-userbot)
License: GNU GPL v3.0
Copyright (c) 2026 chaolcam
-----------------------------------------------------------------------------
-->

# GagaraGogo Userbot - Komutlar ve Özellikler Kılavuzu

Bu belge; GagaraGogo Userbot bünyesindeki otomatik arka plan servislerini, olay (event) dinleyicilerini, yönetim komutlarını, medya indirme araçlarını ve yapılandırma seçeneklerini açıklar.

[🇬🇧 Click here for English Documentation (COMMANDS_AND_FEATURES.md)](COMMANDS_AND_FEATURES.md)

---

## İçindekiler
1. [Otomatik Admin Grubu ve Forum Mimarisi](#1-otomatik-admin-grubu-ve-forum-mimarisi)
2. [Olay Dinleyicileri (Arka Plan Servisleri)](#2-olay-dinleyicileri-arka-plan-servisleri)
3. [Komut Listesi](#3-komut-listesi)
   - [Yönetim Komutları](#yönetim-komutları)
   - [Gizlilik ve Koruma](#gizlilik-ve-koruma)
   - [İndirme ve Medya Araçları](#indirme-ve-medya-araçları)
   - [TikTok Takip ve Canlı Kayıt](#tiktok-takip-ve-canlı-kayıt)
   - [Sistem ve Bakım](#sistem-ve-bakım)
   - [Yapılandırma](#yapılandırma)
4. [Yardımcı Bot ve İnteraktif Arayüz](#4-yardımcı-bot-ve-interaktif-arayüz)
5. [Ortam Değişkenleri ve Veri Saklama](#5-ortam-değişkenleri-ve-veri-saklama)

---

## 1. Otomatik Admin Grubu ve Forum Mimarisi

Bot, herhangi bir manuel grup veya konu ID'si girilmesine gerek kalmadan kendi yönetim ve arşiv merkezini kurabilir:

* **Sıfırdan Kurulum:** `.env` dosyasında `YEDEK_GRUP_ID` belirtilmemişse, bot ilk açılışında `GagaraGogo Admin & Arşiv` adında Forum özellikli bir süper grup oluşturur.
* **Yardımcı Bot Yetkilendirmesi:** `BOT_TOKEN` ile tanımlanan yardımcı bot gruba eklenir ve tüm yönetim izinleriyle yönetici yapılır.
* **Genel Konu Karşılama Mesajı:** Grup açıldığında General (Genel) konusuna sistemin hazır olduğunu belirten, konuları ve hızlı komutları listeleyen bir mesaj gönderilir ve sabitlenir (`pin`).
* **Alt Konuların Açılması:**
  * `Sistem Logları`: Beklenmeyen hatalar ve sistem raporları bu konuya iletilir.
  * `Silinen Mesajlar`: Özel sohbetlerde silinen metin ve medyalar gönderen bilgisiyle buraya arşivlenir.
  * `Süreli Medyalar`: Tek gösterimlik fotoğraf ve videolar kalıcı olarak buraya kaydedilir.
  * `TT: [kullanici_adi]`: Canlı yayın veya gönderi takibine alınan her TikTok profili için özel bir konu oluşturulur.

---

## 2. Olay Dinleyicileri (Arka Plan Servisleri)

Kullanıcının manuel komut vermesine gerek kalmadan, Telegram olaylarını izleyerek otonom çalışan mekanizmalar:

### Anti-Delete (Yalnızca Özel Sohbetler)
* Yalnızca birebir özel sohbetlerde (DM) gelen son 500 mesajı RAM önbelleğinde (`LRUCache`) saklar.
* Karşı taraf bir mesajı sildiği anda içeriği yakalayarak gönderenin profiliyle birlikte admin grubundaki `Silinen Mesajlar` konusuna iletir.
* Gruplardaki mesajlar gizlilik ve performans nedeniyle dinlenmez.

### Süreli Medya Yakalayıcı
* Özel sohbetlerde gönderilen tek gösterimlik veya süreli (`ttl_seconds`, `view_once`) medyaları yakalar.
* Medyayı yerel bellekte işleyerek admin grubundaki `Süreli Medyalar` konusuna kalıcı kopya olarak yükler.

### TikTok Canlı Yayın ve Gönderi Takibi
* Takip listesindeki kullanıcıları 20 saniyelik aralıklarla kontrol eder.
* Yayın başladığında doğrudan stream adresini çözerek `yt-dlp` ve `ffmpeg` ile parçalar halinde kaydeder; admin grubundaki ilgili forum konusuna gönderir.
* Yeni paylaşılan video ve kaydırmalı fotoğraf albümlerini periyodik olarak sorgular, filigransız biçimde konuya aktarır.

### Kalıcı Tek Bulut Veritabanı (JSON Belgesi)
* Admin grup ID'si, aktif ayarlar, TikTok takipleri, otomesajlar ve eklentiler Telegram Kayıtlı Mesajlar (`Saved Messages`) içinde `#GAGARAGOGO_TEK_BULUT_DB` etiketli **`gagaragogo_bulut_db.json`** dosyasında saklanır.
* Karakter sınırı yoktur; güncellemeler dosya düzenlenerek (`edit_message_media`) yapılır.
* Eski metin formatındaki kullanıcı verileri otomatik olarak okunup tek bir bayt kayıp olmadan yeni JSON dosyasına dönüştürülür.
* Sunucu yeniden kurulsa ya da geçici disk sıfırlansa bile bot mevcut grubu bu dosyadan okur ve yeni grup açmaz.

---

## 3. Komut Listesi

Tüm komutlar varsayılan olarak `.` (nokta) önekiyle çalışır ve bot sahibine (`filters.me`) kısıtlıdır.

### Yönetim Komutları

| Komut | Kullanım | Açıklama |
| :--- | :--- | :--- |
| `.ban` | `.ban 1d Reklam` veya yanıtlarken `.ban` | Kullanıcıyı gruptan süreli (`10s`, `15m`, `2h`, `1d`) veya kalıcı yasaklar. |
| `.unban` | `.unban @kullanici` ya da `.unban [id]` | Kullanıcının gruptaki yasağını kaldırır. |
| `.mute` | `.mute 2h Spam` veya yanıtlarken `.mute` | Kullanıcının grupta mesaj göndermesini süreli veya kalıcı susturur. |
| `.unmute` | `.unmute @kullanici` ya da `.unmute [id]` | Kullanıcının susturmasını kaldırır. |
| `.purge` | Bir mesaja yanıt vererek `.purge` | Yanıtlanan mesajdan mevcut komuta kadar olan tüm iletileri topluca siler. |
| `.delme` | `.delme [sayı]` (Örn: `.delme 20`) | Mevcut sohbette gönderdiğiniz son N adet kendi mesajınızı topluca siler. |
| `.lock` | `.lock [msg/media/sticker/link/poll/invite/all]` | Grupta mesaj, medya, çıkartma, bağlantı veya tüm yetkileri kilitler. |
| `.unlock` | `.unlock [msg/media/sticker/link/poll/invite/all]` | Grupta kilitlenen belirli veya tüm yetkileri tekrar açar. |
| `.tag` | `.tag herkes [mesaj]` / `.tag admin [mesaj]` / `.tag dur` | **(Sadece Yönetici Gruplarında)** Üyeleri veya adminleri 5'erli paketlerle etiketler. |

### Gizlilik ve Koruma

| Komut | Kullanım | Açıklama |
| :--- | :--- | :--- |
| `.afk` | `.afk [sebep]` (Örn: `.afk Toplantıdayım`) | AFK modunu açar; özel mesaj ve etiketleri otomatik yanıtlayıp kaydeder. İlk mesajınızla kapanır. |
| `.antidelete` | `.antidelete on` / `.antidelete off` | Özel sohbetlerde silinen mesajların arşivlenmesini açar veya kapatır. |
| `.sureli` | `.sureli on` / `.sureli off` | Tek gösterimlik süreli medyaların yakalanmasını açar veya kapatır. |

### İndirme ve Medya Araçları

| Komut | Kullanım | Açıklama |
| :--- | :--- | :--- |
| `.whois` | `.whois [kullanici_adi/id]` veya yanıtlarken | Kullanıcının DC, ID, bio, ortak grup ve güvenlik durumunu raporlar. |
| `.ocr` | Görsele yanıt vererek `.ocr [dil]` | Fotoğraftaki veya belgedeki metinleri optik karakter tanıma ile yazıya döker. |
| `.yuvarlak` | Bir videoya yanıt vererek `.yuvarlak` | Videoyu 1:1 kare kırparak Telegram yuvarlak video mesajına (Telescope) dönüştürür. |
| `.ses` | Bir videoya veya sese yanıt vererek `.ses` | Medyayı yerel Telegram sesli mesajına (Voice Note) dönüştürür. |
| `.sticker` | Bir fotoğrafa yanıt vererek `.sticker` | Fotoğrafı Telegram standart çıkartmasına (512x512 WebP) dönüştürür. |
| `.tts` | `.tts [metin]` veya yanıtlarken `.tts` | Metni Türkçe seslendirip sesli mesaj olarak iletir. |
| `.stt` | Bir sesli mesaja yanıt vererek `.stt [dil]` | Sesli mesajı veya ses kaydını dinleyip yazıya döker (Örn: `.stt tr`, `.stt en`). |
| `.bypass` | `.bypass [link1] [link2]...` veya yanıtlayarak | Ouo.io, Ouo.press, TinyURL, Bitly, CleanURI, clck.ru gibi linkleri çözer. |
| `.tt` | `.tt https://vt.tiktok.com/...` | TikTok videolarını veya fotoğraf albümlerini filigransız indirir. |
| `.yt` | `.yt https://youtube.com/...` | YouTube videolarını ve Shorts içeriklerini indirir. |
| `.x` | `.x https://x.com/...` | Twitter / X gönderisindeki video ve fotoğrafları indirir. |
| `.rd` | `.rd https://reddit.com/...` | Reddit gönderilerindeki videoları indirir. |
| `.tg` | `.tg https://t.me/...` veya yanıtlarken `.tg` | Telegram mesajındaki medyayı (gizli kanal olsa bile) indirip sohbete atar. |
| `.ig` | `.ig kullanici_adi` | Instagram profili için butonlu interaktif hikaye, gönderi ve öne çıkanlar menüsü açar. |
| `.rapidapi` | `.rapidapi [key1, key2 | sil]` | Instagram araçları için RapidAPI anahtarını bulut veritabanına kaydeder/yönetir. |
| `.dil` | `.dil [kod]` (örn: `.dil tr`) | Çeviri modülü için varsayılan hedef dili belirler. |
| `.cevir` | Bir mesaja yanıt vererek `.cevir` | Yanıtlanan metni ayarlanan varsayılan dile çevirir. |

### TikTok Takip ve Canlı Kayıt

| Komut | Kullanım | Açıklama |
| :--- | :--- | :--- |
| `.tttakip` | `.tttakip kullanici_adi [yayin/post/both]` | Kullanıcıyı otomatik canlı yayın ve gönderi takibine ekler. |
| `.tttakiptencikar` | `.tttakiptencikar kullanici_adi` | Kullanıcıyı takip listesinden çıkarır, süren kaydı durdurur. |
| `.ttcookie` | `.ttcookie [sessionid | dosya | sil]` | Yaş kısıtlamalı yayınlar için çerezleri bulut veritabanına kaydeder. |

### Grup & İletim (Anlık İletim, Otomatik Mesaj & Rehber Yönetimi)

| Komut | Kullanım | Açıklama |
| :--- | :--- | :--- |
| `.ilet` | `.ilet` (yanıtla / doğrudan metin / medya altyazısı) | Yanıtlanan mesajı, yazılan metni veya gönderilen medyayı (altyazısına `.ilet [yazı]` yazılarak) seçili tüm gruplara iletir. |
| `.iletmenu` | `.iletmenu` (veya `.iletmenu [no]`) | Grupları numaralandırarak listeler ve altındaki numara butonlarıyla tek tıkla açık/kapalı durumunu değiştirir. |
| `.otomesaj` | `.otomesaj` | Otomatik zamanlanmış mesaj yönetim panelini açar (Başlıklı butonlar, detay kartı, süre ve grup yönetimi). |
| `.otomesaj ekle` | `.otomesaj ekle [başlık]` (veya yanıtlayarak) | Yanıtlanan mesajı/metni otomatik başlık veya özel başlıkla zamanlanmış görev olarak kaydeder. |
| `.otomesaj sure` | `.otomesaj sure [id] 2.5 saat` / `45 dk` | Görevin iletim periyodunu serbestçe belirler (ondalıklı saat, dakika, gün destekler). |
| `.otomesaj sil` | `.otomesaj sil [id]` | Belirtilen otomatik mesaj görevini siler. |
| `.rehbermenu` | `.rehbermenu` (veya `.rehber`) | `.iletmenu` tarzında tamamen butonlu yönetim merkezini açar; gruptan gruba aktarım, rehbere çekme veya gruba ekleme işlemlerini butonlarla canlı yönetir. |
| `.rehber` | `.rehber` (veya `.rehber [sayfa]`, `.rehber yenile`) | Gruplarınızı üye sayılarına göre (en çok üyeden en aza) sıralayan interaktif kontrol panelini açar. |
| `.grupaktar` | `.grupaktar [kaynak_no] [hedef_no] [adet]` | Seçilen bir gruptaki üyeleri doğrudan diğer bir gruba aktarır (Örn: `.grupaktar 1 2 100`). |
| `.rehberekle` | `.rehberekle [grup_no] [adet]` | Seçilen gruptaki üyeleri güvenli aralıklarla Telegram rehberinize kaydeder (Örn: `.rehberekle 1 50`). |
| `.grubaekle` | `.grubaekle [grup_no] [adet]` | Rehberinizdeki kişileri seçilen gruba toplu olarak davet eder (Örn: `.grubaekle 2 50`). |
| `.rehbersayi` | `.rehbersayi` | Telegram rehberinizdeki toplam kayıtlı kişi sayısını anında gösterir. |
| `.rehbersil` | `.rehbersil` (yanıtlayarak veya kullanıcı adı/ID) | Belirtilen kişiyi rehberden siler. |
| `.rehbertemizle` | `.rehbertemizle onayla` | Rehberdeki tüm kişileri toplu olarak temizler (Güvenlik onayı gerektirir). |

### Sistem ve Bakım

| Komut | Kullanım | Açıklama |
| :--- | :--- | :--- |
| `.yardim` | `.yardim` | Yardımcı bot üzerinden kategorilere ayrılmış interaktif menüyü açar. |
| `.ayarlar` | `.ayarlar` | Botun dinamik aç/kapa ayarlarını butonlu panel olarak sunar. |
| `.durum` | `.durum` | CPU, RAM, Disk, Uptime ve işletim sistemi bilgilerini raporlar. |
| `.ping` | `.ping` | Telegram sunucuları ile gecikme süresini (ms) ölçer. |
| `.update` | `.update` | GitHub reposundaki yeni commitleri denetler. |
| `.update now` | `.update now` | Kodları GitHub'dan çeker (`git pull`), gereksinimleri günceller ve botu yeniden başlatır. |
| `.restart` | `.restart` | Bot sürecini sunucuya dokunmadan yeniden başlatır. |

### Eklenti Yönetimi ve Canlı Mağaza (Plugins & Store)

| Komut | Kullanım | Açıklama |
| :--- | :--- | :--- |
| `.install` | Bir `.py` dosyasına yanıt vererek `.install` | Gönderilen eklenti dosyasını syntax denetiminden geçirir, Kayıtlı Mesajlar'a yedekler ve **yeniden başlatma gerekmeden canlı aktif eder**. |
| `.install [sayı]` | `.install 4` | Resmi mağaza kanalındaki (`@gagaragogoplugin`) 4 numaralı eklentiyi otomatik indirip bota kurar. |
| `.uninstall` | `.uninstall [eklenti_adı]` | Yalnızca sonradan yüklenmiş özel bir eklentiyi canlı hafızadan ve diskten tamamen siler. *(Çekirdek sistem eklentileri korumalıdır, asla silinemez)*. |
| `.plugins` | `.plugins` | Dahili sistem eklentilerini ve sonradan yüklenmiş özel eklentileri dosya boyutu, yüklenme tarihi ve durumlarıyla listeler. |

### Yapılandırma

| Komut | Kullanım | Açıklama |
| :--- | :--- | :--- |
| `.setyedekgrup` | `.setyedekgrup [grup_id]` | Önceden var olan başka bir süper grubu ana admin grubu olarak tanımlar. |

---

## 4. Yardımcı Bot ve İnteraktif Arayüz

`bot_plugins/inline_yardim.py` tarafından yönetilen ve `@BotFather` yardımcı botu (`BOT_TOKEN`) ile sunulan etkileşimli özellikler:

* **Kategori Butonları:** `.yardim` çalıştırıldığında Admin, Koruma, Araçlar, Sistem ve Ayarlar seçeneklerini inline klavye olarak listeler.
* **Sayfalandırma:** Her kategorideki komutlar sayfalı olarak gezilebilir; komut butonuna basıldığında kullanım örneği ve açıklaması aynı mesajda gösterilir.
* **Hızlı Aç/Kapa (Toggle):** Kontrol panelinde (`.ayarlar`) Anti-Delete ve Süreli Medya modları tek tıkla açılıp kapatılabilir.
* **Inline Instagram Tarayıcısı:** `.ig [kullanici_adi]` çalıştırıldığında hikaye ve gönderileri Telegram üzerinden galeri gibi inceleme imkanı verir.

---

## 5. Ortam Değişkenleri ve Veri Saklama

### Çevre Değişkenleri (.env)

```env
API_ID=1234567                     # Telegram API ID (my.telegram.org)
API_HASH=abcdef123456...           # Telegram API Hash
STRING_SESSION=1BVts...            # Pyrogram v2 String Session
BOT_TOKEN=123456:ABC...            # @BotFather Yardımcı Bot Tokeni (Opsiyonel / Önerilir)
YEDEK_GRUP_ID=                     # Ana Admin Grubu ID (Opsiyonel - Boşsa otomatik açılır)
RAPIDAPI_KEYS=key1,key2            # Instagram araçları için API anahtarları (Opsiyonel)
PORT=8080                          # Sağlık kontrolü HTTP portu (Varsayılan: 8080)
```

### Veritabanı ve Çalışma Dosyaları
* **`ayarlar.json`**: Dinamik mod ve konu ID eşleşmelerini yerel diskte tutar.
* **`tiktok_takip.json`**: Takipteki TikTok profillerini ve konu ID'lerini saklar.
* **`Saved Messages / Bulut DB`**: Yerel dosyaların kaybolmasına karşı her iki dosyanın içeriğini Telegram bulutunda tek bir mesajda yedekler.
