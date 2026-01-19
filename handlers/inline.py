from aiogram import Router, types
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultVideo
from utils.validators import is_supported_url, extract_url
from services.downloader import download_video
import hashlib

router = Router()

@router.inline_query()
async def inline_handler(query: types.InlineQuery):
    text = query.query.strip()
    
    if not is_supported_url(text):
        # We can offer a help article or empty result
        return
        
    url = extract_url(text)
    if not url:
        return
        
    # Unique ID for the result
    result_id = hashlib.md5(text.encode()).hexdigest()

    # For MVP we will return an Article that sends the link.
    # The bot must be in the chat to download it if it sees the link.
    # However, a better UX is "Article" that says "Send to Bot to Download".
    # But the user wants usage in other chats.
    # If the bot is added to the group, it will catch the message sent by the user via inline.
    
    results = [
        InlineQueryResultArticle(
            id=result_id,
            title="🎥 Скачать видео",
            description="Нажмите, чтобы отправить ссылку в чат. Если я есть в чате, я скачаю видео.",
            input_message_content=InputTextMessageContent(
                message_text=url
            ),
            thumbnail_url="https://cdn-icons-png.flaticon.com/512/726/726993.png" # Generic download icon
        )
    ]
    
    # Advanced: Try to fetch direct URL for Video Result (Slow, might timeout)
    # Ideally we would need a cache or a fast way. For now, stick to Article.
    
    await query.answer(results, cache_time=1, is_personal=True)
