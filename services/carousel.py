"""
Instagram photo-carousel support.

yt-dlp only extracts video/audio streams, so a post made of photos fails with
"No video formats found". gallery-dl understands Instagram posts properly, so
it is used to enumerate the media of a post instead.

Design notes:
- gallery-dl is invoked as a subprocess with `-j` (JSON), so nothing but
  stdout parsing depends on its internals.
- Instagram serves WebP, which Telegram renders poorly, so images are
  converted to JPEG with Pillow.
- Every file lands in a per-request temp dir so cleanup is a single rmtree,
  exactly like services/downloader.py does for video.
"""

import asyncio
import json
import logging
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image

from config import COOKIES_INST_PATH, DOWNLOAD_DIR

# Telegram refuses media groups larger than this.
MAX_MEDIA = 10
MAX_IMAGE_BYTES = 10 * 1024 * 1024
# WebP sources can be huge; shrink instead of failing the whole carousel.
MAX_DIMENSION = 2048
# Cap what we download: a malicious/huge post should not eat the disk.
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
# A post that stalls this long is treated as a timeout instead of hanging
# the bot forever.
GALLERY_TIMEOUT = 45


class CarouselError(Exception):
    pass


def _build_args() -> list[str]:
    """
    gallery-dl arguments.

    Deliberately command-line flags rather than a YAML config on stdin: with
    `-j` plus a stdin config, gallery-dl blocks indefinitely on this host.
    """
    args = [
        "-m", "gallery_dl",
        "-j",
        "--no-download",
        # Be gentle: Instagram throttles bursts aggressively.
        "--sleep", "1-2",
        "--sleep-request", "1-2",
        "--no-input",
    ]
    if COOKIES_INST_PATH and Path(COOKIES_INST_PATH).exists():
        args += ["--cookies", str(COOKIES_INST_PATH)]
    return args


def _media_urls_from_stream(raw: str) -> list[str]:
    """
    Parse gallery-dl's `-j` output.

    Code 2 is the post metadata dict; codes >2 are the individual media URLs.
    We only want the media items, in post order.
    """
    try:
        events = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CarouselError(f"gallery-dl returned invalid JSON: {e}") from e

    urls: list[str] = []
    for event in events:
        if not (isinstance(event, list) and len(event) >= 2):
            continue
        code, payload = event[0], event[1]
        if code > 2 and isinstance(payload, str) and payload.startswith(("http://", "https://")):
            urls.append(payload)
    return urls


def _meta_from_stream(raw: str) -> dict:
    """Pull a few useful fields out of the code-2 metadata record."""
    meta: dict = {}
    try:
        events = json.loads(raw)
    except json.JSONDecodeError:
        return meta

    for event in events:
        if (isinstance(event, list) and len(event) >= 2
                and event[0] == 2 and isinstance(event[1], dict)):
            m = event[1]
            username = m.get("username")
            fullname = m.get("fullname")
            meta = {
                "author": fullname or username or "Unknown",
                "caption": (m.get("description") or "").strip(),
                "count": m.get("count"),
            }
            break
    return meta


def _download(url: str, dest: Path) -> int:
    """Fetch one image with a size cap, return bytes written."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/140.0.0.0 Safari/537.36"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        declared = resp.headers.get("Content-Length")
        if declared and int(declared) > MAX_DOWNLOAD_BYTES:
            raise CarouselError("image too large")
        data = resp.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise CarouselError("image too large")
    dest.write_bytes(data)
    return len(data)


def _to_jpeg(src: Path, dest: Path) -> int:
    """Normalise to JPEG within Telegram's limits. Returns file size."""
    with Image.open(src) as im:
        im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")

        if max(im.size) > MAX_DIMENSION:
            im.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

        quality = 92
        while True:
            im.save(dest, "JPEG", quality=quality, optimize=True)
            size = dest.stat().st_size
            if size <= MAX_IMAGE_BYTES or quality <= 55:
                break
            quality -= 12

    if dest.stat().st_size > MAX_IMAGE_BYTES:
        raise CarouselError("converted image exceeds Telegram limit")
    return dest.stat().st_size


async def download_carousel(url: str) -> dict:
    """
    Download an Instagram photo post.

    Returns a dict with 'paths' (list of jpg paths), 'tmpdir', 'author',
    'caption'. Raises CarouselError on any failure.
    """
    # Use this venv's own interpreter: a bare "python3" may point at a
    # different version without gallery-dl/Pillow installed.
    proc = await asyncio.create_subprocess_exec(
        sys.executable, *_build_args(), url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(Path(__file__).parent.parent),
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=GALLERY_TIMEOUT
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise CarouselError("Instagram did not respond in time") from None

    raw = stdout.decode(errors="replace")

    if proc.returncode != 0:
        raise CarouselError(
            f"gallery-dl failed: {stderr.decode(errors='replace').strip()[:200]}"
        )

    media_urls = _media_urls_from_stream(raw)
    if not media_urls:
        raise CarouselError("no media found in post")

    meta = _meta_from_stream(raw)
    tmpdir = Path(tempfile.mkdtemp(dir=DOWNLOAD_DIR, prefix="car_"))
    loop = asyncio.get_event_loop()

    def _work() -> list[Path]:
        paths: list[Path] = []
        for idx, media_url in enumerate(media_urls[:MAX_MEDIA]):
            raw_path = tmpdir / f"raw_{idx}"
            jpg_path = tmpdir / f"{idx:02d}.jpg"
            try:
                _download(media_url, raw_path)
                _to_jpeg(raw_path, jpg_path)
            except Exception as e:
                logging.warning("Skipping carousel item %d: %s", idx, e)
                raw_path.unlink(missing_ok=True)
                jpg_path.unlink(missing_ok=True)
                continue
            raw_path.unlink(missing_ok=True)
            paths.append(jpg_path)
        return paths

    try:
        paths = await loop.run_in_executor(None, _work)
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise

    if not paths:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise CarouselError("all media items failed to download")

    return {
        "paths": [str(p) for p in paths],
        "tmpdir": str(tmpdir),
        "author": meta.get("author", "Unknown"),
        "caption": meta.get("caption", ""),
        "skipped": max(0, len(media_urls) - MAX_MEDIA),
    }


def cleanup(result: dict | None) -> None:
    if result and result.get("tmpdir"):
        shutil.rmtree(result["tmpdir"], ignore_errors=True)
