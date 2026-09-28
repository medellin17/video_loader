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


    results = [
        InlineQueryResultArticle(
            id=result_id,
            title="🎥 Скачать видео",
            description="Нажмите, чтобы отправить ссылку в чат. Если я есть в чате, я скачаю видео.",
            input_message_content=InputTextMessageContent(
                message_text=url
            ),
            thumbnail_url="https://cdn-icons-png.flaticon.com/512/726/726993.png"
        )
    ]
    
    await query.answer(results, cache_time=1, is_personal=True)
