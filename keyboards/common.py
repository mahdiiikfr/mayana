from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_language_keyboard() -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard to choose the preferred language: Farsi or English.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🇮🇷 فارسی", callback_data="lang:fa")
    builder.button(text="🇬🇧 English", callback_data="lang:en")
    builder.adjust(2)
    return builder.as_markup()


def get_main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """
    Creates a localized reply keyboard for the main menu options.
    """
    builder = ReplyKeyboardBuilder()

    if lang == "fa":
        builder.button(text="🖥 مدیریت سرورها (VPS)")
        builder.button(text="💳 کیف پول و اعتبار")
        builder.button(text="👤 حساب کاربری")
        builder.button(text="📞 پشتیبانی")
    else:
        # English language
        builder.button(text="🖥 Manage Servers (VPS)")
        builder.button(text="💳 Wallet & Credit")
        builder.button(text="👤 My Account")
        builder.button(text="📞 Support")

    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Select an option...")
