import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
COOKIES_YT_PATH = os.getenv("COOKIES_YT_PATH")
COOKIES_INST_PATH = os.getenv("COOKIES_INST_PATH")

# Chat that receives health alerts. Empty disables the alert channel, but
# /status still works for anyone. Set it with the /id command in the bot.
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

# How often the background health check runs.
HEALTH_CHECK_INTERVAL_HOURS = int(os.getenv("HEALTH_CHECK_INTERVAL_HOURS", "6"))

BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"

# Ensure download directory exists
DOWNLOAD_DIR.mkdir(exist_ok=True)
