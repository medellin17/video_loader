import asyncio
import logging
import shutil
import tempfile
import time
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


# Instagram's authenticated endpoint (/api/v1/media/<id>/info/) answers
# `{"message": "checkpoint_required"}` with HTTP 400 once it decides the session
# must be re-verified. yt-dlp surfaces that as a bare "HTTP Error 400", which
# used to reach the user as the generic "не получилось скачать видео" message.
# The public web page keeps working, so we retry logged out.
# The flag is process-wide with a short TTL: the admin only has to re-log in
# once, and meanwhile we do not pay a doomed attempt on every request.
_checkpoint_until: float = 0.0
CHECKPOINT_TTL_SECONDS = 900

# Substrings that mean "Instagram refused the session", not "this link is
# broken". Deliberately excludes per-post failures (private, deleted, photo
# carousel) so those still produce their own specific message.
_SESSION_BLOCK_MARKERS = (
    "video info extraction failed",
    "checkpoint",
    "login required",
    "cookies are no longer valid",
    "rate-limit reached",
    "empty media response",
    "unable to extract shared data",
    "http error 400",
    "http error 401",
    "http error 403",
    "http error 429",
)


def session_is_blocked() -> bool:
    return time.monotonic() < _checkpoint_until


def _mark_session_blocked() -> None:
    global _checkpoint_until
    _checkpoint_until = time.monotonic() + CHECKPOINT_TTL_SECONDS
    logging.warning(
        "Instagram refused the bot session (checkpoint). Working logged out for %s s. "
        "The admin must re-login and re-upload cookies_inst.txt.",
        CHECKPOINT_TTL_SECONDS,
    )


def _looks_like_session_block(raw: str) -> bool:
    lowered = raw.lower()
    return any(marker in lowered for marker in _SESSION_BLOCK_MARKERS)


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

    ydl_opts = _build_opts(platform, tmpdir)
    # A known-blocked session is skipped outright instead of failing first.
    if platform == "Instagram" and session_is_blocked() and "cookiefile" in ydl_opts:
        logging.info("Instagram session known to be blocked, extracting logged out")
        ydl_opts.pop("cookiefile")

    loop = asyncio.get_event_loop()

    try:
        return await loop.run_in_executor(None, _download_sync, url, ydl_opts, tmpdir)
    except Exception as e:
        raw = getattr(e, "raw", "") or str(e)

        if (platform == "Instagram" and "cookiefile" in ydl_opts
                and _looks_like_session_block(raw)):
            _mark_session_blocked()
            shutil.rmtree(tmpdir, ignore_errors=True)
            tmpdir = Path(tempfile.mkdtemp(dir=DOWNLOAD_DIR, prefix="dl_"))
            retry_opts = _build_opts(platform, tmpdir)
            retry_opts.pop("cookiefile", None)
            logging.info("Retrying %s without Instagram cookies", url)
            try:
                return await loop.run_in_executor(
                    None, _download_sync, url, retry_opts, tmpdir
                )
            except Exception as e2:
                raw = getattr(e2, "raw", "") or str(e2)
                shutil.rmtree(tmpdir, ignore_errors=True)
                logging.error("Logged-out retry failed for %s: %s", url, raw)
                raise DownloadError(humanize(raw, platform), raw) from None

        # Never let a partial file survive a failure.
        shutil.rmtree(tmpdir, ignore_errors=True)
        logging.error("Download error for %s: %s", url, raw)
        raise DownloadError(humanize(raw, platform), raw) from None


def _build_opts(platform: str, tmpdir: Path) -> dict:
    """yt-dlp options for one attempt: shared base plus per-platform tweaks."""
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

    return ydl_opts


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
