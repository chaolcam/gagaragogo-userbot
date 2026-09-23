# GagaraGogo Userbot

A modular, high-performance open-source Telegram userbot built with Pyrogram v2 and MTProto architecture.

[🇹🇷 Türkçe Dokümantasyon için tıklayın (README_TR.md)](README_TR.md)

[![CodeFactor](https://www.codefactor.io/repository/github/chaolcam/gagaragogo-userbot/badge)](https://www.codefactor.io/repository/github/chaolcam/gagaragogo-userbot)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pyrogram v2](https://img.shields.io/badge/Framework-Pyrogram%20v2-orange?style=flat-square&logo=telegram)](https://docs.pyrogram.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3.0-blue.svg?style=flat-square)](LICENSE)
[![Deploy on Render](https://img.shields.io/badge/Deploy-Render-black?style=flat-square&logo=render)](https://render.com/deploy?repo=https://github.com/chaolcam/gagaragogo-userbot)

---

## Architectural Highlights

- **Hybrid Client Architecture:** Synchronizes MTProto client with an assistant bot (`@BotFather`) to deliver inline keyboards, interactive menus, and alerts.
- **Serverless / Persistent Cloud Storage:** Requires zero external database dependencies (Redis, MongoDB, etc.). Settings and configurations are saved as JSON files directly in Telegram *Saved Messages*.
- **Autonomous Archive & Forum Organization:** Automatically creates and configures a forum supergroup for system logs, view-once media, and deleted messages.
- **Memory & Resource Efficiency:** Built with LRU caching, automated GC cycles, and temporary file sweepers optimized for low-resource cloud tiers (512MB RAM).
- **Dynamic Plugin Loader:** Install, unload, and manage custom python plugins at runtime without restarting the userbot using `.install`.
- **Bilingual & Localization (i18n):** Native support for English and Turkish (`.lang tr` / `.lang en`), with Turkish enabled as default.

---

## Quick Start

### 1. Easy Deployment (Telegram Assistant)

Generate session strings and deploy to Render without console access:  
👉 **[@GagaragogoKurulumBot](https://t.me/GagaragogoKurulumBot)**

### 2. One-Click Deploy (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/chaolcam/gagaragogo-userbot)

### 3. Manual Setup (Linux / VPS)

```bash
# Clone the repository
git clone https://github.com/chaolcam/gagaragogo-userbot.git
cd gagaragogo-userbot

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp example.env .env
nano .env

# Run the userbot
python3 main.py
```

*Run with Docker:*
```bash
docker build -t gagaragogo-userbot .
docker run --env-file .env -d gagaragogo-userbot
```

---

## Environment Variables

| Variable | Description | Status |
| :--- | :--- | :---: |
| `API_ID` | Telegram API ID ([my.telegram.org](https://my.telegram.org)) | **Required** |
| `API_HASH` | Telegram API Hash ([my.telegram.org](https://my.telegram.org)) | **Required** |
| `STRING_SESSION` | Pyrogram v2 Session String | **Required** |
| `BOT_TOKEN` | Assistant bot token from [@BotFather](https://t.me/BotFather) | Recommended |
| `DEFAULT_LANG` | Default language (`tr` or `en`, default: `tr`) | Optional |
| `RAPIDAPI_KEYS` | RapidAPI keys for Instagram tools (comma-separated) | Optional |
| `YEDEK_GRUP_ID` | Existing admin group ID (auto-created if empty) | Optional |
| `PORT` | Health-check HTTP port (default: `8080`) | Optional |

---

## Key Commands & Modules

| Category | Commands | Description |
| :--- | :--- | :--- |
| **Control Center** | `.help`, `.settings`, `.lang` | Interactive inline assistance, settings, and language picker (`tr`/`en`). |
| **Broadcasting & Groups** | `.broadcast`, `.automessage`, `.contacts` | Manage contacts, filter active members, and broadcast instant or scheduled messages. |
| **Media Resolution** | `.tt`, `.ig`, `.yt` | TikTok (live recording + HD video), Instagram media/stories, and YouTube downloads. |
| **Privacy & Security** | `.antidelete`, `.viewonce` | Capture deleted DM messages and preserve view-once media directly into forum topics. |
| **URL Tools** | `.bypass <url>` | Bypass short links and ad-gateways (ouo, bitly, tinyurl, etc.). |
| **System** | `.update`, `.restart`, `.alive` | Live system statistics, auto-updating via git, and restart utilities. |

Detailed guide & usage documentation:  
📄 **[COMMANDS_AND_FEATURES.md](COMMANDS_AND_FEATURES.md)**

---

## Disclaimer & License

This project is open-source and intended for personal automation. Using userbots is subject to Telegram Terms of Service. The developers take no responsibility for account limitations.

Licensed under [GNU General Public License v3.0](LICENSE).