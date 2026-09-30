import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

import yt_dlp

from config import DOWNLOAD_DIR, COOKIES_YT_PATH, COOKIES_INST_PATH
from utils.errors import humanize, detect_platform


class DownloadError(Exception):
    """Carries a message that is already safe to show in chat."""

    def __init__(self, user_message: str, raw: str = ""):
        super().__init__(user_message)
        self.user_message = user_message
        self.raw = raw


async def download_video(url: str) -> dict:
    """
    Downloads a video from the given URL using yt-dlp.

    Each call downloads into its own temp subdirectory, so a failed or
    interrupted download can never leave `.part`/temp files behind in
    DOWNLOAD_DIR. The caller is responsible for calling `cleanup(result)`.

    Returns a dict with 'path', 'tmpdir', 'title', 'duration', 'author'.
    """
    platform = detect_platform(url)

    # Per-request scratch directory: cleanup is then just rmtree of one folder.
    tmpdir = Path(tempfile.mkdtemp(dir=DOWNLOAD_DIR, prefix="dl_"))

    # NOTE: deliberately no custom User-Agent. yt-dlp ships realistic per-site
    # UAs; a hardcoded old Chrome UA is a bot fingerprint that gets blocked.
    ydl_opts = {
        "outtmpl": str(tmpdir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "format": "best",
        "external_downloader": None,
        "ignoreerrors": False,
        # YouTube/Instagram connections drop transiently; retry instead of
        # showing the user a failure on the first hiccup.
        "retries": 3,
    }

    cookie_file = None

    if platform == "YouTube":
        cookie_file = COOKIES_YT_PATH
        ydl_opts.update({
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "external_downloader": "aria2c",
            "external_downloader_args": ["-x16", "-k1M"],
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        })
    elif platform == "Instagram":
        cookie_file = COOKIES_INST_PATH
    # TikTok and X (Twitter) need no cookies and no special client args.

    if cookie_file and Path(cookie_file).exists():
        ydl_opts["cookiefile"] = cookie_file
    else:
        logging.info("No cookie file available for %s (expected %s)", platform, cookie_file)

    loop = asyncio.get_event_loop()

    try:
        return await loop.run_in_executor(None, _download_sync, url, ydl_opts, tmpdir)
    except Exception as e:
        # Never let a partial file survive a failure.
        shutil.rmtree(tmpdir, ignore_errors=True)
        raw = getattr(e, "raw", "") or str(e)
        logging.error("Download error for %s: %s", url, raw)
        raise DownloadError(humanize(raw, platform), raw) from None


def cleanup(result: dict | None) -> None:
    """Remove the download directory for a finished (or failed) request."""
    if not result:
        return
    tmpdir = result.get("tmpdir")
    if tmpdir:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _download_sync(url: str, opts: dict, tmpdir: Path) -> dict:
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

        if info.get("entries"):
            info = info["entries"][0]

        filepath = ydl.prepare_filename(info)
        path = Path(filepath)

        # `prepare_filename` returns the pre-merge path; prefer the real file
        # on disk so we never hand aiogram a path that does not exist.
        if not path.exists():
            candidates = [
                p for p in tmpdir.iterdir()
                if p.is_file() and not p.name.endswith((".part", ".ytdl", ".temp"))
            ]
            if not candidates:
                raise FileNotFoundError(f"No downloaded file in {tmpdir}")
            # Largest file wins (video stream, not a stray audio-only leftover).
            path = max(candidates, key=lambda p: p.stat().st_size)

        return {
            "path": str(path),
            "tmpdir": str(tmpdir),
            "title": info.get("title") or "Video",
            "duration": info.get("duration"),
            "author": info.get("uploader") or info.get("channel") or "Unknown",
        }
