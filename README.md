# 🎬 Telegram Video Downloader Bot

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Aiogram](https://img.shields.io/badge/Library-Aiogram_3.x-blue?logo=telegram)](https://github.com/aiogram/aiogram)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A high-performance Telegram bot for downloading media from **YouTube (Shorts)**, **Instagram (Reels and photo carousels)**, and **TikTok** (watermark-free). Built with a hybrid multi-stream engine to bypass modern server-side restrictions.

---

## ✨ Key Features

- 🔴 **YouTube**: Full videos and Shorts up to 4K (via FFmpeg merge), using a 16-connection `aria2c`.
- 🟣 **Instagram**: Reels and videos via session cookies, plus **photo carousels** sent as a Telegram album.
- ⚫ **TikTok**: Watermark-free downloads with browser TLS impersonation.
- 🧹 **Self-cleaning**: Every download goes into its own temp directory, so partial `.part` files can never pile up.
- 🇷🇺 **Readable errors**: Users get short Russian messages instead of raw yt-dlp tracebacks; full details go to the log.
- 👤 **Clean UX**: Clear captions with author metadata.

---

## 🛠 Tech Stack

- **Core**: [Aiogram 3](https://aiogram.dev/) (Asynchronous Bot API)
- **Engine**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) for video, [gallery-dl](https://github.com/mikf/gallery-dl) for photo posts
- **Downloader**: [aria2c](https://aria2.github.io/) (16-thread multi-connection)
- **Processor**: [FFmpeg](https://ffmpeg.org/) (DASH stream merging) + Pillow (WebP → JPEG)

> ⚠️ **`curl_cffi` is not optional.** Since yt-dlp 2026.x the TikTok extractor relies on browser TLS impersonation. Without it TikTok serves a ~537 byte block page and every download fails with `Unexpected response from webpage request`.

---

## 🐍 Requirements

- **Python 3.11+** — yt-dlp has dropped 3.10.
- `ffmpeg` and `aria2` for full quality and fast YouTube downloads.

```bash
sudo apt update
sudo apt install -y ffmpeg aria2 python3.11-venv
```

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/medellin17/video_loader.git
cd video_loader
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the root directory:
```env
BOT_TOKEN=your_telegram_bot_token
COOKIES_YT_PATH=cookies_yt.txt
COOKIES_INST_PATH=cookies_inst.txt
```
> [!IMPORTANT]
> Instagram requires cookies from a logged-in session. Export them in **Netscape** format
> (not JSON) and save as `cookies_yt.txt` / `cookies_inst.txt`. At minimum Instagram needs
> `sessionid`, `ds_user_id` and `csrftoken`. See `walkthrough.md` for the full recipe.
>
> Cookie files contain a live account session: keep them at `chmod 600`.

### 3. Running as a Daemon
```bash
# /etc/systemd/system/videoloader.service
[Unit]
Description=Telegram Media Downloader Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/video_loader
ExecStart=/root/video_loader/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload
systemctl enable --now videoloader
```

---

## 🏗 Architecture

The project follows a modular structure:

- `handlers/`: Command, message and inline-query logic. `messages.py` orchestrates a request: try yt-dlp for video, and fall back to a gallery-dl carousel when a post has no video stream.
- `services/downloader.py`: Video download via yt-dlp, with per-platform options and guaranteed temp cleanup.
- `services/carousel.py`: Instagram photo posts via gallery-dl, WebP → JPEG conversion, size-capped.
- `utils/errors.py`: Maps raw yt-dlp errors to short Russian messages for chat.
- `utils/validators.py`: URL detection and extraction.
- `tools/cookie_upload.py`: One-shot, token-protected uploader for refreshing Instagram cookies without scp.
- `config.py`: Environment and path configuration.

### How a photo post is handled
1. `download_video()` runs yt-dlp, which reports `No video formats found` for a photo-only post.
2. The handler recognises that specific error and retries with `download_carousel()`.
3. gallery-dl enumerates the post's media, images are converted to JPEG within Telegram's limits.
4. The bot sends an album (max 10 items) and deletes the temp directory.

If the carousel also fails, the user gets the plain yt-dlp error message — no crash.

---

## 🛡 License
This project is licensed under the MIT License - see the LICENSE file for details.

---

