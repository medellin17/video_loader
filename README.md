# 🎬 Telegram Video Downloader Bot

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Aiogram](https://img.shields.io/badge/Library-Aiogram_3.x-blue?logo=telegram)](https://github.com/aiogram/aiogram)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A high-performance Telegram bot capable of downloading high-quality videos from **YouTube (Shorts)**, **Instagram (Reels)**, and **TikTok** (watermark-free). Built with a hybrid multi-stream engine to bypass modern server-side restrictions.

---

## ✨ Key Features

- 🔴 **YouTube**: Supports full videos and Shorts in 1080p/4K (via FFmpeg merge).
- 🟣 **Instagram**: Downloads Reels and videos using session-based authentication.
- ⚫ **TikTok**: Watermark-free downloads with high-speed extraction.
- 🚀 **Hybrid Engine**: Custom logic using `aria2c` for YouTube to bypass network throttling.
- 🛠 **HTML Mode**: Robust message parsing and automatic entity escaping.
- 👤 **Clean UX**: Minimalist interface with clear video captions and author metadata.

---

## 🛠 Tech Stack

- **Core**: [Aiogram 3](https://aiogram.dev/) (Asynchronous Bot API)
- **Engine**: [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Downloader**: [aria2c](https://aria2.github.io/) (16-thread multi-connection)
- **Processor**: [FFmpeg](https://ffmpeg.org/) (for DASH stream merging)

---

## 🚀 Quick Start

### 1. Requirements
Ensure you have the following installed on your Linux server:
```bash
sudo apt update
sudo apt install -y ffmpeg aria2 python3-pip
```

### 2. Installation
```bash
git clone https://github.com/your-repo/video-loader-bot.git
cd video-loader-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
BOT_TOKEN=your_telegram_bot_token
COOKIES_YT_PATH=cookies_yt.txt
COOKIES_INST_PATH=cookies_inst.txt
```
> [!IMPORTANT]
> To avoid YouTube/Instagram blocks, export your cookies in Netscape format and save them as `cookies_yt.txt` and `cookies_inst.txt`.

### 4. Running as a Daemon
Create a systemd service for 24/7 uptime:
```bash
# /etc/systemd/system/videoloader.service
[Unit]
Description=Telegram Video Loader Bot
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
systemctl enable --now videoloader
```

---

## 🏗 Architecture

The project follows a modular structure for easy maintenance:
- `handlers/`: Command and message logic.
- `services/`: Core download service with platform-specific optimizations.
- `utils/`: URL validation and regex utilities.
- `config.py`: Environment and path configuration.

---

## 🛡 License
This project is licensed under the MIT License - see the LICENSE file for details.

---
<p align="center">Made with ❤️ for the community</p>
