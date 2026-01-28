import os
import asyncio
from aiogram import Router, types, F
from aiogram.types import FSInputFile
from utils.validators import is_supported_url, extract_url
from services.downloader import download_video, DownloadError

router = Router()

@router.message(F.text)
async def handle_message(message: types.Message):
    text = message.text
    if not is_supported_url(text):
        if message.chat.type == 'private':
            await message.reply("⚠️ Ссылка не найдена или не поддерживается.\nПришлите ссылку на YouTube, Instagram или TikTok.")
        return

    url = extract_url(text)
    if not url:
        return

    # User feedback: Uploading action
    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
    status_msg = await message.reply("⏳ Скачиваю видео...")

    file_path = None
    try:
        # Download
        result = await download_video(url)
        file_path = result['path']
        video_title = result['title']
        author = result['author']

        # Caption
        import html
        safe_title = html.escape(video_title)
        safe_author = html.escape(author)
        caption = f"🎬 <b>{safe_title}</b>\n👤 {safe_author}\n\n@loader_mdbot"

        # Send video
        video_file = FSInputFile(file_path)
        await message.answer_video(
            video=video_file, 
            caption=caption,
            supports_streaming=True
        )
        
        # Delete processing message
        await status_msg.delete()

    except DownloadError as e:
        await status_msg.edit_text(f"❌ Ошибка при скачивании: {str(e)}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Произошла ошибка: {str(e)}")
        # Print error to console/log for debug (in real app use logging)
        logging.error(f"Unexpected error handling message: {e}", exc_info=True)
    finally:
        # Cleanup
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to remove file {file_path}: {e}")
