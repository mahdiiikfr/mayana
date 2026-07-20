import time
from typing import Any, Callable, Dict, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery


class ThrottlingMiddleware(BaseMiddleware):
    """
    ThrottlingMiddleware prevents update flooding (Anti-Spam).
    Enforces a default 2-second rate limit between consecutive user messages/clicks.
    Unpacks general Update objects for aiogram 3 compatibility.
    """
    def __init__(self, limit: float = 2.0) -> None:
        self.limit = limit
        # Maps user_id -> last update timestamp
        self.last_timestamps: Dict[int, float] = {}
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id: Optional[int] = None

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
        elif isinstance(target_event, CallbackQuery):
            if target_event.from_user:
                user_id = target_event.from_user.id

        if user_id:
            now = time.time()
            last_time = self.last_timestamps.get(user_id, 0.0)

            # Check elapsed time since last request
            if now - last_time < self.limit:
                # If message, alert user about the flood warning
                if isinstance(target_event, Message):
                    await target_event.answer("⚠️ لطفاً از اسپم کردن خودداری کنید. مجدداً چند لحظه دیگر تلاش کنید.")
                elif isinstance(target_event, CallbackQuery):
                    await target_event.answer("⚠️ Please do not spam!", show_alert=True)
                return  # Skip invoking the handler (throttled)

            # Update timestamp
            self.last_timestamps[user_id] = now

        return await handler(event, data)
