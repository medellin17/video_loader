from aiogram import Router
from .commands import router as commands_router
from .messages import router as messages_router
from .inline import router as inline_router

main_router = Router()

main_router.include_router(commands_router)
main_router.include_router(messages_router)
main_router.include_router(inline_router)
