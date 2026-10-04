# 🎬 Telegram Video Downloader Bot

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Aiogram](https://img.shields.io/badge/Library-Aiogram_3.x-blue?logo=telegram)](https://github.com/aiogram/aiogram)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A high-performance Telegram bot for downloading media from **YouTube (Shorts)**, **Instagram (Reels and photo carousels)**, **TikTok** (watermark-free), and **X (Twitter)**. Built with a hybrid multi-stream engine to bypass modern server-side restrictions.

---

## ✨ Key Features

- 🔴 **YouTube**: Full videos and Shorts up to 4K (via FFmpeg merge), using a 16-connection `aria2c`.
- 🟣 **Instagram**: Reels and videos, downloaded anonymously from the public page and upgraded to a session when cookies are usable, plus **photo carousels** sent as a Telegram album.
- ⚫ **TikTok**: Watermark-free downloads with browser TLS impersonation.
- ⚪ **X (Twitter)**: Fast native video downloads from public posts without requiring cookies.
- 🩺 **Health monitoring**: Cookie sessions are probed on a timer; the admin is alerted the moment a session dies, instead of finding out from user complaints.
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
# Where health alerts go; get the value from the bot's /id command
ADMIN_CHAT_ID=
# How often cookies are probed, hours
HEALTH_CHECK_INTERVAL_HOURS=6
```
> [!IMPORTANT]
> **Instagram videos do not need cookies.** Public posts are scraped from the web page,
> so the bot works with no session at all. Cookies are still required for **photo
> carousels** (gallery-dl gets redirected to the login page without them) and they
> additionally unlock private posts. Export cookies in **Netscape** format (not JSON)
> and save as `cookies_yt.txt` / `cookies_inst.txt`. At minimum Instagram needs
> `sessionid`, `ds_user_id` and `csrftoken`. See `walkthrough.md` for the full recipe.
>
> Cookies that are present but *unusable* are worse than none: if Instagram puts the
> session under review, every authenticated call answers HTTP 400
> `checkpoint_required` and downloads fail until the cookies are re-uploaded. The bot
> detects this and falls back to anonymous extraction, so videos keep working — see
> [Instagram checkpoints](#instagram-checkpoints).
>
> Cookie files contain a live account session: keep them at `chmod 600`.
>
> Set `ADMIN_CHAT_ID` or the health monitor has nowhere to send alerts. You can
> always run `/status` in the bot to check on demand.

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
- `services/downloader.py`: Video download via yt-dlp, with per-platform options, an anonymous retry when Instagram refuses the session, and guaranteed temp cleanup.
- `services/carousel.py`: Instagram photo posts via gallery-dl, WebP → JPEG conversion, size-capped.
- `services/health.py`: Cookie liveness checks — a live Instagram session returns `200`, a dead one `302`, and `400` + `checkpoint_required` means the session is under review and must be re-uploaded.
- `services/monitor.py`: Background poller that alerts the admin only on a state *change*, so a dead session produces one message instead of four a day.
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

### Why health monitoring exists
Expired cookies are silent: every Instagram download starts hitting the login
wall and nothing surfaces until users complain. The monitor probes the session
and alerts on transition. Note that checking cookie *expiry* on disk is not
enough — a session revoked before its expiry looks perfectly valid, and only
the live probe catches that.

### Instagram checkpoints
Instagram sometimes decides an account must be re-verified and answers every
authenticated call with HTTP 400 and `{"message": "checkpoint_required"}`. The
cookies look perfectly valid — `sessionid` was still good for another 361 days
in the observed case — so nothing on disk reveals the problem.

Two things break, and both are handled:

1. **Downloads.** yt-dlp only reports the bare `HTTP Error 400`, which used to
   reach users as the generic "could not download" message. The downloader now
   recognises a session-level refusal, retries once **without cookies**, and
   remembers that state for 15 minutes so it does not pay a doomed attempt on
   every request. Public posts extract fine anonymously — measured on the reel
   that triggered this: 12 formats and a 963 917 byte download logged out, 400
   with cookies.
2. **Monitoring.** The probe treated `400` as "unexpected, assume alive", so
   `/status` stayed green while Instagram was unusable. It now parses the body
   and reports the checkpoint as broken, which sends exactly one admin alert.

Only **photo carousels** truly need a working session, since gallery-dl is
redirected to the login page when logged out.

---

## 📈 Scaling

Only Instagram needs an account, and only for photo carousels. TikTok, YouTube, and
X (Twitter) work with no session at all, and Instagram videos do too — verified, not
assumed. See [SCALING.md](SCALING.md) for the measured numbers, the account/IP cost
model, and where the real ceiling is (it is not CPU, and it is not automatable).

---

## 🛡 License
This project is licensed under the MIT License - see the LICENSE file for details.

---

