import logging
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger("bot.middlewares.logging")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware that records incoming updates, logging the Sender's ID
    and their actions (sent message text or callback data button).
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = "Unknown"
        action = "Update"

        if isinstance(event, Message):
            if event.from_user:
                user_id = event.from_user.id
            action = f"Sent Message: '{event.text}'"
        elif isinstance(event, CallbackQuery):
            if event.from_user:
                user_id = event.from_user.id
            action = f"Clicked Button (CallbackData): '{event.data}'"

        logger.info(f"User ID {user_id} -> {action}")

        return await handler(event, data)
