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
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    # Platform-specific overrides
    cookie_file = None
    
    ydl_opts.update({
        'format': 'best',
        'external_downloader': None, # Ensure we don't use aria2c here
        'socket_timeout': 30,
    })
    
    if "youtube.com" in url or "youtu.be" in url:
        cookie_file = COOKIES_YT_PATH
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'external_downloader': 'aria2c',
            'external_downloader_args': ['-x16', '-k1M'],
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
        })
    elif "instagram.com" in url:
        cookie_file = COOKIES_INST_PATH
    elif "tiktok.com" in url:
        pass
        
    # Apply cookie file if exists
    if cookie_file and Path(cookie_file).exists():
        ydl_opts['cookiefile'] = cookie_file

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
