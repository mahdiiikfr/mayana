import logging
from typing import Callable
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from db.connection import DatabaseManager
from keyboards.common import get_language_keyboard, get_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, db: DatabaseManager, _: Callable[[str], str]) -> None:
    """
    Handles /start command.
    Checks if user is registered, creates record if new, and requests language preference.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"User {user_id} triggered command /start")

    # Register/retrieve user
    user = await db.users.create_user(
        user_id=user_id,
        username=username,
        full_name=full_name,
        language_code="fa"  # initial default, can be changed
    )

    # Prompt language selection
    await message.answer(
        text=_("select_language"),
        reply_markup=get_language_keyboard()
    )


@router.callback_query(F.data.startswith("lang:"))
async def process_lang_selection(callback: CallbackQuery, db: DatabaseManager, _: Callable[[str], str]) -> None:
    """
    Handles inline callback for language selection (e.g., lang:fa, lang:en).
    Saves language choice, deletes selection keyboard, and shows main menu.
    """
    selected_lang = callback.data.split(":")[1]
    user_id = callback.from_user.id

    logger.info(f"User {user_id} selected language: {selected_lang}")

    # Update database
    await db.users.update_language(user_id, selected_lang)

    # Clean up inline message
    await callback.message.delete()

    # Re-evaluate translator context with new language (for welcome message)
    # Since our i18n middleware loaded the previous language for this update instance,
    # we can temporarily define a local translation helper or use the updated language explicitly
    # To keep code simple, we fetch the welcome translation directly from translation files,
    # but we can also just call callback.message.answer with localized text.

    # Get localized welcome message based on selected language
    if selected_lang == "fa":
        welcome_text = (
            "سلام! به ربات تجاری مدیریت سرورهای ابری HostVDS خوش آمدید.\n"
            "لطفاً یکی از گزینه‌های زیر را برای مدیریت سرورها یا شارژ کیف پول خود انتخاب کنید."
        )
    else:
        welcome_text = (
            "Hello! Welcome to the HostVDS Cloud VPS Management Bot.\n"
            "Please select one of the options below to manage your servers or top up your wallet."
        )

    await callback.message.answer(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(selected_lang)
    )
    await callback.answer()
