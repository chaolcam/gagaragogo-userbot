# GagaraGogo Userbot - Commands & Architecture Reference

Technical reference manual documenting background event listeners, interactive bot components, media resolvers, and command structures for GagaraGogo Userbot.

[🇹🇷 Türkçe Komutlar ve Özellikler Kılavuzu için tıklayın (COMMANDS_AND_FEATURES_TR.md)](COMMANDS_AND_FEATURES_TR.md)

---

## 1. Automated Supergroup & Forum Architecture

When `YEDEK_GRUP_ID` is omitted in your environment configuration, the userbot automatically creates and provisions a designated management and archive center:

- **Supergroup Initialization:** Creates a private supergroup named `GagaraGogo Admin & Arşiv` with Telegram Forum/Topics enabled.
- **BotFather Assistant Privilege:** Adds your assistant bot (`BOT_TOKEN`) and assigns complete administrator rights.
- **General Topic Announcement:** Posts and pins a status card listing topics and key controls.
- **Standard Forum Topics:**
  - `Sistem Logları`: Unhandled runtime exceptions and health notices.
  - `Silinen Mesajlar`: Captures deleted direct messages with sender profile information.
  - `Süreli Medyalar`: Preserves view-once photos and self-destructing videos.
  - `TT: [username]`: Dedicated forum topic generated per tracked TikTok creator.

---

## 2. Background Event Listeners

Autonomous workers executing without manual user triggers:

### Anti-Delete (Direct Messages Only)
- Retains up to 500 recent private messages per chat using an in-memory `LRUCache`.
- When an incoming message is revoked by the other participant, copies content and sender metadata directly to the `Silinen Mesajlar` forum topic.
- Group messages are ignored to guarantee performance and privacy.

### View-Once Media Grabber
- Listens for media messages with `ttl_seconds` or `view_once` parameters in direct messages.
- Downloads the media stream in memory and stores a permanent copy in the `Süreli Medyalar` topic.

### TikTok Live & Media Watcher
- Polls tracked TikTok creators every 20 seconds.
- Detects live broadcasts, resolves the direct HLS stream, records in chunks via `yt-dlp` / `ffmpeg`, and uploads videos to the dedicated forum topic.
- Scrapes newly posted videos and image sliders watermark-free.

### Unified Cloud Storage (Telegram Saved Messages)
- Group configurations, active settings, TikTok creators, automessages, and dynamic plugins are preserved inside `gagaragogo_bulut_db.json` pinned under `#GAGARAGOGO_TEK_BULUT_DB` in Telegram *Saved Messages*.
- Rebuilt instances seamlessly synchronize state without creating duplicate groups.

---

## 3. Command Reference

All commands require the `.` (dot) prefix and are restricted to the bot owner (`filters.me`).

### Moderation & Administration

| Command | Usage | Description |
| :--- | :--- | :--- |
| `.ban` | `.ban 1d Reason` or reply `.ban` | Bans a user temporarily (`10s`, `15m`, `2h`, `1d`) or permanently. |
| `.unban` | `.unban @user` or `.unban [id]` | Unbans a user from the chat. |
| `.mute` | `.mute 2h Spam` or reply `.mute` | Mutes a user temporarily or permanently. |
| `.unmute` | `.unmute @user` or `.unmute [id]` | Restores message-sending permissions. |
| `.purge` | Reply to target message with `.purge` | Bulk-deletes all messages from the target up to the command. |
| `.delme` | `.delme [count]` (e.g. `.delme 20`) | Deletes your last N sent messages in the current chat. |
| `.lock` | `.lock [msg/media/sticker/link/poll/all]` | Restricts specified chat permissions. |
| `.unlock` | `.unlock [msg/media/sticker/link/poll/all]` | Unlocks chat permissions. |
| `.tag` | `.tag all [msg]` / `.tag admin [msg]` | Mentions chat members or admins in batches (Admin groups only). |

### Privacy & Presence

| Command | Usage | Description |
| :--- | :--- | :--- |
| `.afk` | `.afk [reason]` | Activates Away From Keyboard status. Auto-responds to mentions/DMs. Disables on your next message. |
| `.antidelete` | `.antidelete on` / `off` | Enables or disables deleted message archiving. |
| `.sureli` | `.sureli on` / `off` | Enables or disables view-once media interception. |

### Resolvers & Media Tools

| Command | Usage | Description |
| :--- | :--- | :--- |
| `.whois` | `.whois [username/id]` or reply | Analyzes user profile, DC location, common chats, and ID details. |
| `.ocr` | Reply to image with `.ocr [lang]` | Extracts text from images using optical character recognition. |
| `.yuvarlak` | Reply to video with `.yuvarlak` | Crops video into a 1:1 round video note (Telescope). |
| `.ses` | Reply to audio/video with `.ses` | Converts file into a native Telegram voice note. |
| `.sticker` | Reply to image with `.sticker` | Converts photo into a WebP Telegram sticker. |
| `.tts` | `.tts [text]` or reply with `.tts` | Converts text to speech and sends as a voice message. |
| `.stt` | Reply to voice note with `.stt [lang]` | Transcribes audio message to text via Google Speech API. |
| `.bypass` | `.bypass [url]` or reply | Bypasses shorteners and ad-protected links (ouo, bitly, tinyurl, etc.). |
| `.tt` | `.tt [url]` | Downloads TikTok videos or photo albums without watermarks. |
| `.yt` | `.yt [url]` | Downloads YouTube videos, Shorts, and audio. |
| `.x` | `.x [url]` | Downloads Twitter / X videos and photos. |
| `.rd` | `.rd [url]` | Downloads Reddit media posts. |
| `.tg` | `.tg [url]` or reply with `.tg` | Downloads Telegram media (including restricted/protected channels). |
| `.ig` | `.ig [username]` | Opens interactive gallery menu for Instagram stories, posts, and highlights. |
| `.rapidapi` | `.rapidapi [key1, key2 | reset]` | Manages RapidAPI keys for Instagram extraction with rotation. |
| `.dil` | `.dil [code]` (e.g. `.dil en`) | Configures default target language for message translation. |
| `.cevir` | Reply to message with `.cevir` | Translates replied message into default target language. |

### TikTok Live & Watcher

| Command | Usage | Description |
| :--- | :--- | :--- |
| `.tttakip` | `.tttakip [username]` | Adds a TikTok creator to automatic live stream recording watch. |
| `.tttakiptencikar` | `.tttakiptencikar [username]` | Removes user from watch list and terminates ongoing live recording. |
| `.ttcookie` | `.ttcookie [sessionid | file | reset]` | Manages TikTok cookies required for age-restricted live streams. |

### Broadcasting & Contact Manager

| Command | Usage | Description |
| :--- | :--- | :--- |
| `.ilet` | `.ilet` (reply / text / caption) | Broadcasts message or media to all active target groups. |
| `.iletmenu` | `.iletmenu` | Interactive paginated menu to toggle destination groups on/off. |
| `.otomesaj` | `.otomesaj` | Scheduled broadcasting dashboard to manage intervals and tasks. |
| `.otomesaj ekle` | `.otomesaj ekle [title]` (or reply) | Creates a recurring broadcast task from replied message. |
| `.otomesaj sure` | `.otomesaj sure [id] 2.5h` / `45m` | Sets transmission interval for specified broadcast task. |
| `.otomesaj sil` | `.otomesaj sil [id]` | Deletes a scheduled message task. |
| `.rehbermenu` | `.rehbermenu` | Full interactive inline control center for group members and contacts. |
| `.rehber` | `.rehber` (or `.rehber [page]`, `.rehber yenile`) | Lists groups sorted by member count via bulk MTProto RPC query. |
| `.grupaktar` | `.grupaktar [src_no] [dest_no] [count]` | Transfers members directly from source group to destination group. |
| `.rehberekle` | `.rehberekle [group_no] [count]` | Saves active members from chosen group into Telegram contacts. |
| `.grubaekle` | `.grubaekle [group_no] [count]` | Bulk invites phonebook contacts into destination group. |
| `.rehbersayi` | `.rehbersayi` | Returns total number of registered Telegram contacts. |
| `.rehbersil` | `.rehbersil` (reply or username) | Deletes target user from contacts. |
| `.rehbertemizle` | `.rehbertemizle onayla` | Wipes registered contacts with required confirmation flag. |

### System & Maintenance

| Command | Usage | Description |
| :--- | :--- | :--- |
| `.alive` / `.yardim` | `.alive` | Opens interactive categories, status metrics, and system dashboard. |
| `.ayarlar` | `.ayarlar` | Opens settings panel with one-click toggles. |
| `.botlang` | `.botlang [tr/en]` | Changes bot interface language (Default: `tr`). |
| `.durum` | `.durum` | Comprehensive diagnostic metrics (CPU, RAM, Disk, Uptime). |
| `.ping` | `.ping` | Measures round-trip latency to Telegram MTProto data centers. |
| `.update` | `.update` | Checks upstream repository for new commits. |
| `.update now` | `.update now` | Pulls upstream updates, installs dependencies, and restarts. |
| `.restart` | `.restart` | Gracefully restarts userbot process. |
| `.setalive` | `.setalive [url]` / `.setalive reset` | Sets or clears custom banner image for alive card. |
| `.setyedekgrup` | `.setyedekgrup [group_id]` | Binds an existing supergroup as the central administration forum. |

### Dynamic Plugin Manager

| Command | Usage | Description |
| :--- | :--- | :--- |
| `.install` | Reply to `.py` file with `.install` | Validates syntax, backs up file to Saved Messages, and **loads plugin at runtime without restart**. |
| `.install [id]` | `.install 4` | Downloads and installs plugin by ID directly from official store channel (`@gagaragogoplugin`). |
| `.uninstall` | `.uninstall [plugin_name]` | Safely unregisters handlers and deletes custom plugin from memory and disk. |
| `.plugins` | `.plugins` | Lists built-in and active custom plugins with metadata. |

---

## 4. Environment Variables Reference

```env
API_ID=1234567                     # Telegram API ID (my.telegram.org)
API_HASH=abcdef123456...           # Telegram API Hash
STRING_SESSION=1BVts...            # Pyrogram v2 Session String
BOT_TOKEN=123456:ABC...            # @BotFather Assistant Bot Token (Recommended)
DEFAULT_LANG=tr                    # Default interface language (tr / en, default: tr)
YEDEK_GRUP_ID=                     # Admin supergroup ID (Auto-created if empty)
RAPIDAPI_KEYS=key1,key2            # RapidAPI keys for Instagram resolution (Optional)
PORT=8080                          # Healthcheck HTTP server port (Default: 8080)
```
