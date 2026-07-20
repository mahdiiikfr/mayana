import json
from pathlib import Path
from typing import Any, Callable, Dict, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from db.connection import DatabaseManager
from config import settings


class I18nMiddleware(BaseMiddleware):
    """
    Middleware that manages multi-language localization (i18n).
    - Checks the user's language selection from SQLite database.
    - Falls back to config.DEFAULT_LOCALE if user is new or selection is missing.
    - Injects a helper translate function '_' into the handler's parameters.
    """
    def __init__(self, locales_dir: str = "locales", default_locale: str = settings.DEFAULT_LOCALE) -> None:
        self.locales_dir = Path(locales_dir)
        self.default_locale = default_locale
        self.translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()
        super().__init__()

    def _load_translations(self) -> None:
        """Pre-loads all JSON localization files into memory."""
        if not self.locales_dir.exists():
            return

        for file in self.locales_dir.glob("*.json"):
            locale_name = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.translations[locale_name] = json.load(f)
            except Exception as e:
                import sys
                print(f"Error loading locale file {file}: {e}", file=sys.stderr)

    def translate(self, key: str, locale: str) -> str:
        """Translates a key into the given locale, falling back to English or key name."""
        locale_translations = self.translations.get(locale, {})
        # If key is missing, fall back to default locale
        if key not in locale_translations:
            locale_translations = self.translations.get(self.default_locale, {})

        return locale_translations.get(key, key)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Resolve Telegram user
        user: Optional[User] = data.get("event_from_user")

        # Default language
        locale = self.default_locale

        # Check database if DatabaseMiddleware successfully injected 'db'
        db: Optional[DatabaseManager] = data.get("db")
        if user and db and db.connection:
            user_data = await db.users.get_user(user.id)
            if user_data and user_data.get("language_code"):
                locale = user_data["language_code"]

        # Define the translator helper function (_)
        def translate_helper(key: str) -> str:
            return self.translate(key, locale)

        # Inject into data so handlers can accept '_' as parameter
        data["_"] = translate_helper
        data["locale"] = locale

        return await handler(event, data)
