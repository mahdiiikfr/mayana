from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from db.connection import DatabaseManager


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware to inject the central DatabaseManager into each handler's data context.
    Allows accessing db operations in handlers as an argument (e.g., db: DatabaseManager).
    """
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Inject DatabaseManager instance
        data["db"] = self.db_manager
        return await handler(event, data)
