from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для скачивания видео.\n\n"
        "Я умею скачивать видео с:\n"
        "🔴 <b>YouTube</b> (+Shorts)\n"
        "🟣 <b>Instagram</b> (Reels)\n"
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
        "- instagram.com/reel/...\n"
        "- tiktok.com/..., vm.tiktok.com/..."
    )
