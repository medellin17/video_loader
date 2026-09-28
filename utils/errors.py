"""
Translates raw yt-dlp / download errors into short human-readable Russian messages.

The bot talks to end users, so the raw yt-dlp traceback (which is English, long,
and full of GitHub issue links) must never reach the chat. Details still go to the log.
"""

import logging

# (substring to look for in the raw error, human message for the user)
# Checked in order, so put specific patterns before generic ones.
_RULES: list[tuple[str, str]] = [
    # --- Instagram: the login wall / expired cookies ---
    (
        "rate-limit reached or login required",
        "🔐 Instagram требует вход — сессия бота протухла.\n"
        "Администратору нужно обновить куки. Попробуй другой источник.",
    ),
    (
        "empty media response",
        "🔐 Instagram не отдал видео — нужна авторизация.\n"
        "Администратору нужно обновить куки. Попробуй другой источник.",
    ),
    (
        "login required",
        "🔐 Instagram требует вход. Попробуй другой источник.",
    ),

    # --- TikTok / Instagram: extractor breakage (usually stale yt-dlp) ---
    (
        "unexpected response from webpage request",
        "🌐 TikTok отдал блок-страницу вместо видео — сервис подозревает бота.\n"
        "Попробуй позже или другой источник.",
    ),
    (
        "unable to extract webpage video data",
        "⚠️ TikTok изменил разметку, экстрактор не справился.\n"
        "Нужно обновление yt-dlp. Попробуй позже.",
    ),
    (
        "unable to extract shared data",
        "⚠️ Не удалось разобрать страницу — возможно, нужна авторизация.\n"
        "Попробуй другой источник.",
    ),
    # NOTE: "No video formats found" is also what yt-dlp reports for a
    # photo-only Instagram carousel. That is NOT an auth failure, so do not
    # blame the session/cookies here - the post simply has no video.
    (
        "no video formats found",
        "📷 В этом посте нет видео — похоже, это карусель из фотографий.\n"
        "Бот качает только видео. Попробуй Reel или ролик.",
    ),
    (
        "requested format is not available",
        "⚠️ Нужный формат недоступен для этого видео.",
    ),

    # --- Content state ---
    (
        "private video",
        "🔒 Это видео приватное — скачать его нельзя.",
    ),
    (
        "this video is private",
        "🔒 Это видео приватное — скачать его нельзя.",
    ),
    (
        "video unavailable",
        "🚫 Видео недоступно или удалено автором.",
    ),
    (
        "account is private",
        "🔒 Аккаунт приватный — контент недоступен.",
    ),
    (
        "confirm you're not a bot",
        "🤖 YouTube думает, что я бот. Нужно обновить сессию. Попробуй позже.",
    ),
    (
        "sign in to confirm your age",
        "🔞 YouTube требует подтверждения возраста. Попробуй другое видео.",
    ),

    # --- Network / rate limits ---
    (
        "http error 429",
        "🚦 Слишком много запросов к сервису. Подожди немного и попробуй снова.",
    ),
    (
        "too many requests",
        "🚦 Слишком много запросов к сервису. Подожди немного и попробуй снова.",
    ),
    (
        "unable to download",
        "🌐 Не удалось скачать файл — проблема с сетью. Попробуй ещё раз.",
    ),
    (
        "timed out",
        "⏱️ Сервис не ответил вовремя. Попробуй ещё раз.",
    ),
    (
        "connection reset",
        "🌐 Соединение оборвалось. Попробуй ещё раз.",
    ),
]

_FALLBACK = (
    "❌ Не получилось скачать видео.\n"
    "Попробуй другую ссылку или сообщи об этом администратору."
)


def humanize(error: str | BaseException, platform: str | None = None) -> str:
    """
    Return a short Russian message for the chat, and log the original error in full.

    `platform` is used only to add a hint when no rule matched, so the user at
    least knows which service misbehaved.
    """
    raw = str(error)
    lowered = raw.lower()

    for needle, message in _RULES:
        if needle in lowered:
            logging.warning("Download failed [%s]: %s -> %s", platform or "?", raw, message)
            return message

    logging.error("Unhandled download error [%s]: %s", platform or "?", raw, exc_info=error)
    if platform:
        return f"{_FALLBACK}\n\n({platform})"
    return _FALLBACK


def detect_platform(url: str) -> str:
    """Best-effort platform label for error hints."""
    lowered = (url or "").lower()
    if "instagram.com" in lowered:
        return "Instagram"
    if "tiktok.com" in lowered:
        return "TikTok"
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return "YouTube"
    return "unknown"
