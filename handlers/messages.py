import html
import logging
import os

from aiogram import Router, F, types
from aiogram.types import FSInputFile, InputMediaPhoto

from services import carousel
from services.carousel import CarouselError
from services.downloader import cleanup, download_video, DownloadError
from utils.validators import extract_url, is_supported_url

router = Router()

# Telegram Bot API rejects uploads above 50 MB via sendVideo.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _is_no_video_error(err: DownloadError) -> bool:
    """True when yt-dlp found no video stream (i.e. a photo post)."""
    return "no video formats found" in (err.raw or "").lower()


@router.message(F.text)
async def handle_message(message: types.Message):
    text = message.text
    if not is_supported_url(text):
        # Ignore non-link messages, or hint the user in a private chat.
        if message.chat.type == "private":
            await message.reply(
                "⚠️ Ссылка не найдена или не поддерживается.\n"
                "Пришлите ссылку на YouTube, Instagram или TikTok."
            )
        return

    url = extract_url(text)
    if not url:
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
    status_msg = await message.reply("⏳ Скачиваю видео...")

    result = None
    try:
        result = await download_video(url)

        size = os.path.getsize(result["path"])
        if size > MAX_UPLOAD_BYTES:
            await status_msg.edit_text(
                f"📦 Файл слишком большой: {size / 1024 / 1024:.1f} МБ\n"
                "Telegram принимает не больше 50 МБ. Попробуй другое видео."
            )
            return

        caption = (
            f"🎬 <b>{html.escape(result['title'])}</b>\n"
            f"👤 {html.escape(result['author'])}\n\n@loader_mdbot"
        )

        await message.answer_video(
            video=FSInputFile(result["path"]),
            caption=caption,
            supports_streaming=True,
        )
        await status_msg.delete()

    except DownloadError as e:
        # A post with no video is usually an Instagram photo carousel, which
        # yt-dlp cannot see. Retry those with gallery-dl before giving up.
        if _is_no_video_error(e) and "instagram.com" in url:
            carousel_result = None
            try:
                await status_msg.edit_text("📷 Похоже на карусель — качаю фото...")
                carousel_result = await carousel.download_carousel(url)

                media = [InputMediaPhoto(media=FSInputFile(p)) for p in carousel_result["paths"]]
                text = f"📷 <b>{html.escape(carousel_result['author'])}</b>"
                if carousel_result.get("skipped"):
                    text += f"\n⚠️ Ещё {carousel_result['skipped']} фото не вместилось"

                # Telegram only accepts a caption on the first media item.
                media[0] = InputMediaPhoto(media=FSInputFile(carousel_result["paths"][0]), caption=text)
                await message.answer_media_group(media=media)
                await status_msg.delete()
                return
            except CarouselError as ce:
                logging.warning("Carousel fallback failed for %s: %s", url, ce)
                await status_msg.edit_text(e.user_message)
            except Exception as ce:
                logging.error("Carousel fallback crashed for %s: %s", url, ce, exc_info=True)
                await status_msg.edit_text(e.user_message)
            finally:
                carousel.cleanup(carousel_result)
        else:
            # e.user_message is already a short, human-readable Russian string.
            await status_msg.edit_text(e.user_message)

    except Exception as e:
        logging.error("Unexpected error handling message: %s", e, exc_info=True)
        try:
            await status_msg.edit_text(
                "❌ Внутренняя ошибка. Попробуй ещё раз или сообщи администратору."
            )
        except Exception:
            # Status message may be too old to edit; never crash the handler here.
            pass
    finally:
        cleanup(result)
