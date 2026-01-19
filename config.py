import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
COOKIES_YT_PATH = os.getenv("COOKIES_YT_PATH")
COOKIES_INST_PATH = os.getenv("COOKIES_INST_PATH")
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"

# Ensure download directory exists
DOWNLOAD_DIR.mkdir(exist_ok=True)
