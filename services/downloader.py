import asyncio
import yt_dlp
import logging
from pathlib import Path
from config import DOWNLOAD_DIR, COOKIES_YT_PATH, COOKIES_INST_PATH

class DownloadError(Exception):
    pass

async def download_video(url: str) -> dict:
    """
    Downloads video from the given URL using yt-dlp.
    Returns a dictionary with 'path', 'title', 'duration', 'author'.
    """
    
    # Base options
    ydl_opts = {
        'outtmpl': str(DOWNLOAD_DIR / '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        'socket_timeout': 30,
        'extract_flat': False,
        'ignoreerrors': False,
    }

    # Platform-specific overrides
    cookie_file = None
    
    if "youtube.com" in url or "youtu.be" in url:
        cookie_file = COOKIES_YT_PATH
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'external_downloader': 'aria2c',
            'external_downloader_args': ['-x16', '-k1M'],
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'],
                    'player_skip': ['webpage']
                }
            },
            'retries': 3,
        })
    elif "instagram.com" in url:
        cookie_file = COOKIES_INST_PATH
        ydl_opts.update({
            'format': 'best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.instagram.com/',
            },
        })
    elif "tiktok.com" in url:
        ydl_opts.update({
            'format': 'best',
        })
        
    # Apply cookie file if exists
    if cookie_file and Path(cookie_file).exists():
        ydl_opts['cookiefile'] = cookie_file
        logging.info(f"Using cookie file: {cookie_file}")
    else:
        if cookie_file:
            logging.warning(f"Cookie file not found: {cookie_file}, attempting without cookies")

    # Run blocking yt-dlp code in a separate thread
    loop = asyncio.get_event_loop()
    
    try:
        return await loop.run_in_executor(None, _download_sync, url, ydl_opts)
    except Exception as e:
        logging.error(f"Download error for {url}: {e}")
        raise DownloadError(f"{str(e)}")

def _download_sync(url: str, opts: dict) -> dict:
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            
            # If 'entries' is present it's a playlist, but we set noplaylist=True,
            # so it should be a single video. Just in case:
            if 'entries' in info:
                info = info['entries'][0]

            filepath = ydl.prepare_filename(info)
            
            return {
                'path': filepath,
                'title': info.get('title', 'Video'),
                'duration': info.get('duration'),
                'author': info.get('uploader') or info.get('channel') or 'Unknown'
            }
        except yt_dlp.utils.DownloadError as e:
            raise Exception(str(e))
