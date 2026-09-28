"""
Health checks for the cookie-backed sources.

The bot fails quietly when cookies expire: every Instagram download starts
returning a login-wall error and nobody notices until users complain. These
checks turn that into an explicit, verifiable state change.

Instagram liveness probe
------------------------
GET /api/v1/accounts/edit/web_form_data/ answers:
  200 + JSON  -> session is valid
  302          -> session is dead (redirect to the login page)

This was verified against four cookie states: real session, a structurally
valid but revoked sessionid, csrftoken-only, and an empty jar. Only the real
session produced 200, so there are no false "alive" results.
"""

import asyncio
import logging
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from config import COOKIES_INST_PATH, COOKIES_YT_PATH

IG_PROBE_URL = "https://www.instagram.com/api/v1/accounts/edit/web_form_data/"
IG_APP_ID = "936619743392459"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
PROBE_TIMEOUT = 20


@dataclass
class CheckResult:
    ok: bool
    label: str
    detail: str = ""
    fatal: bool = True
    data: dict = field(default_factory=dict)


def parse_cookie_file(path: str | None) -> tuple[dict, dict]:
    """
    Read a Netscape cookie file.

    Returns (values, expiries) where expiries maps name -> unix timestamp
    (0 means session cookie with no expiry).
    """
    values, expiries = {}, {}
    if not path or not Path(path).exists():
        return values, expiries

    for line in Path(path).read_text(errors="replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        name, value, expires = parts[5], parts[6], parts[4]
        values[name] = urllib.parse.unquote(value)
        try:
            expiries[name] = int(expires)
        except ValueError:
            expiries[name] = 0
    return values, expiries


def _expiry_state(expires: int) -> tuple[bool, str]:
    """Return (is_valid, human text) for a cookie expiry timestamp."""
    if not expires:
        return True, "бессрочная"
    days = (expires - time.time()) / 86400
    if days < 0:
        return False, f"истекла {abs(days):.0f} дн. назад"
    if days < 3:
        return False, f"истекает через {days:.1f} дн."
    return True, f"действительна ещё {days:.0f} дн."


def check_instagram_file() -> CheckResult:
    """Static check: does the cookie file exist and is it internally sane?"""
    values, expiries = parse_cookie_file(COOKIES_INST_PATH)

    if not values:
        return CheckResult(
            False, "Instagram куки",
            f"файл не найден или пуст: {COOKIES_INST_PATH}",
        )
    if "sessionid" not in values:
        return CheckResult(
            False, "Instagram куки",
            "в файле нет sessionid — Instagram ничего не отдаст",
        )

    ok, text = _expiry_state(expiries.get("sessionid", 0))
    if not ok:
        return CheckResult(
            False, "Instagram куки",
            f"sessionid {text}. Файл: {COOKIES_INST_PATH}",
            data={"cookies": len(values)},
        )

    return CheckResult(
        True, "Instagram куки",
        f"файл в порядке ({len(values)} кук), sessionid {text}",
        data={"cookies": len(values)},
    )


def check_youtube_file() -> CheckResult:
    """YouTube works without cookies, so a missing file is not an error."""
    values, expiries = parse_cookie_file(COOKIES_YT_PATH)

    if not values:
        return CheckResult(
            True, "YouTube куки",
            "файла нет — это не критично, публичные видео качаются без кук",
            fatal=False,
        )

    ok, text = _expiry_state(expiries.get("__Secure-3PSID", 0))
    if not ok:
        return CheckResult(
            True, "YouTube куки",
            f"сессия протухла ({text}), но публичные видео качаются без неё",
            fatal=False,
        )

    return CheckResult(
        True, "YouTube куки", f"{len(values)} кук, {text}", fatal=False
    )


async def check_instagram_live() -> CheckResult:
    """Live probe: is the Instagram session actually accepted right now?"""
    static = check_instagram_file()
    if not static.ok:
        return static

    values, _ = parse_cookie_file(COOKIES_INST_PATH)
    headers = {
        "User-Agent": UA,
        "X-IG-App-ID": IG_APP_ID,
    }

    try:
        async with httpx.AsyncClient(
            timeout=PROBE_TIMEOUT, follow_redirects=False
        ) as client:
            resp = await client.get(
                IG_PROBE_URL, cookies=values, headers=headers
            )
    except Exception as e:
        # A network hiccup is not a dead session; do not raise a false alarm.
        return CheckResult(
            True, "Instagram сессия",
            f"не удалось проверить ({type(e).__name__}), считаю живой",
            fatal=False,
        )

    if resp.status_code == 200:
        username = None
        try:
            username = resp.json().get("username")
        except Exception:
            pass
        who = f" ({username})" if username else ""
        return CheckResult(
            True, "Instagram сессия", f"живая{who}, Instagram подтвердил вход"
        )

    if resp.status_code in (301, 302, 303, 307, 308):
        return CheckResult(
            False, "Instagram сессия",
            "МЁТРВАЯ — Instagram перенаправляет на логин.\n"
            f"Обнови куки: {COOKIES_INST_PATH}",
        )

    if resp.status_code == 429:
        return CheckResult(
            True, "Instagram сессия",
            "ответ 429 (лимит запросов), не считаю сессию мёртвой",
            fatal=False,
        )

    return CheckResult(
        True, "Instagram сессия",
        f"неожиданный ответ {resp.status_code}, не считаю сессию мёртвой",
        fatal=False,
    )


async def full_report() -> list[CheckResult]:
    """Run every check. Network check last so file errors surface first."""
    return [
        check_instagram_file(),
        check_youtube_file(),
        await check_instagram_live(),
    ]


def format_report(results: list[CheckResult]) -> str:
    """Render results as the admin-facing message body."""
    lines = []
    for r in results:
        mark = "✅" if r.ok else ("⚠️" if not r.fatal else "❌")
        lines.append(f"{mark} <b>{r.label}</b>\n   {r.detail}")
    broken = [r for r in results if not r.ok and r.fatal]
    lines.append("")
    if broken:
        lines.append(f"🔴 Проблем: {len(broken)}. Бот работает частично.")
    else:
        lines.append("🟢 Всё в порядке.")
    return "\n".join(lines)
