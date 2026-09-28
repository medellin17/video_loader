"""
Background health monitoring.

Alerts the admin only when the overall state *changes*, so a broken session
produces one message instead of one every six hours. Recovers are announced
too, otherwise a silent fix would leave you unsure whether it worked.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from config import ADMIN_CHAT_ID, HEALTH_CHECK_INTERVAL_HOURS
from services import health


def _is_broken(results: list[health.CheckResult]) -> bool:
    return any(not r.ok and r.fatal for r in results)


async def _send(bot: Bot, text: str) -> None:
    if not ADMIN_CHAT_ID:
        logging.info("Health alert suppressed (ADMIN_CHAT_ID not set): %s",
                     text.replace("\n", " ")[:80])
        return
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode="HTML")
        logging.info("Health alert sent to admin")
    except TelegramForbiddenError:
        logging.error(
            "Cannot message admin chat %s - the bot was not started by that user. "
            "Send /start to the bot first.", ADMIN_CHAT_ID
        )
    except Exception as e:
        logging.error("Failed to send health alert: %s", e)


async def run_health_monitor(bot: Bot) -> None:
    """
    Poll cookie health forever, alerting on transitions.

    First run is delayed so it does not compete with bot startup.
    """
    interval = max(1, HEALTH_CHECK_INTERVAL_HOURS) * 3600

    # Give the bot time to come up and register handlers.
    await asyncio.sleep(60)

    last_state: bool | None = None

    while True:
        try:
            results = await health.full_report()
            broken = _is_broken(results)

            if last_state is None:
                # First run: report only if something is already wrong.
                if broken:
                    await _send(bot, "🚨 <b>Проблема при запуске бота</b>\n\n"
                                     + health.format_report(results))
                    logging.warning("Health check on startup: problems found")
                else:
                    logging.info("Health check on startup: all good")
            elif broken != last_state:
                if broken:
                    await _send(bot, "🚨 <b>Куки протухли</b>\n\n"
                                     + health.format_report(results))
                    logging.error("Health state changed to BROKEN")
                else:
                    await _send(bot, "✅ <b>Куки снова в порядке</b>\n\n"
                                     + health.format_report(results))
                    logging.info("Health state changed to OK")

            last_state = broken

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error("Health monitor iteration failed: %s", e, exc_info=True)

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
