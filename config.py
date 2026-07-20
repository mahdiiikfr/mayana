import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings configuration.
    Loads environmental variables from `.env` file or local environment.
    Provides strict typing, validation, and auto-casting of values.
    """
    # Telegram settings
    BOT_TOKEN: str
    ADMIN_ID: int

    # Database settings
    DB_PATH: str = "db/bot_database.db"

    # OpenStack settings
    OPENRC_PATH: str = "api/openrc.sh"

    # Localization
    DEFAULT_LOCALE: str = "fa"

    # Pydantic configuration to read .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # ignores extra environmental variables
    )


# Instantiate the settings object to be used globally
try:
    # Ensure a local .env exists or fallback gracefully if variables are in environment
    settings = Settings()
except Exception as e:
    # For initial steps or when .env is not present yet, we can log a warning or load defaults
    # For safety, if BOT_TOKEN is missing during active run, we raise a helpful error.
    # But during configuration phase we load dummy values or raise error.
    import sys
    print(f"Configuration Loading Warning/Error: {e}", file=sys.stderr)
    # We raise the exception so the user/developer gets immediate feedback on invalid/missing config
    raise e
