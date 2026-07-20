import logging
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

logger = logging.getLogger("bot.middlewares.logging")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware that records incoming updates, logging the Sender's ID
    and their actions (sent message text or callback data button).
    Unpacks general Update objects for aiogram 3 compatibility.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = "Unknown"
        action = "Update"

        # aiogram 3 root update middlewares receive Update object
        target_event = event
        if isinstance(event, Update):
            if event.message:
                target_event = event.message
            elif event.callback_query:
                target_event = event.callback_query

        if isinstance(target_event, Message):
            if target_event.from_user:
                user_id = target_event.from_user.id
            action = f"Sent Message: '{target_event.text}'"
        elif isinstance(target_event, CallbackQuery):
            if target_event.from_user:
                user_id = target_event.from_user.id
            action = f"Clicked Button (CallbackData): '{target_event.data}'"

        logger.info(f"User ID {user_id} -> {action}")

        return await handler(event, data)
