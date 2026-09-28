import logging

from aiogram import Router, types
from aiogram.filters import Command

from config import ADMIN_CHAT_ID
from services import health

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для скачивания видео.\n\n"
        "Я умею скачивать видео с:\n"
        "🔴 <b>YouTube</b> (Shorts)\n"
        "🟣 <b>Instagram</b> (Reels и карусели из фото)\n"
        "⚫ <b>TikTok</b> (без водяных знаков)\n\n"
        "Просто пришли мне ссылку на видео, и я отправлю его тебе файлом!"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "ℹ️ <b>Справка</b>\n\n"
        "Просто отправь ссылку на поддерживаемый ресурс.\n"
        "Если видео слишком большое (>50МБ), я предупрежу об этом.\n\n"
        "Поддерживаемые форматы ссылок:\n"
        "- youtube.com/..., youtu.be/...\n"
        "- instagram.com/reel/..., instagram.com/p/...\n"
        "- tiktok.com/..., vm.tiktok.com/..."
    )


@router.message(Command("id"))
async def cmd_id(message: types.Message):
    """Show the chat id needed for ADMIN_CHAT_ID in .env."""
    await message.answer(
        f"<code>{message.chat.id}</code>\n\n"
        "Это значение впиши в <code>ADMIN_CHAT_ID</code> в .env, чтобы бот "
        "присылал уведомления о протухших куках сюда."
    )


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    """Manual health check on demand."""
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        results = await health.full_report()
        await message.answer(health.format_report(results))
    except Exception as e:
        logging.error("/status failed: %s", e, exc_info=True)
        await message.answer("❌ Проверка не удалась, детали в логах.")
