from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_wallet_keyboard() -> InlineKeyboardMarkup:
    """
    Builds localized inline keyboard for primary wallet management actions.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 شارژ حساب / Deposit", callback_data="wallet_deposit")
    builder.button(text="📜 تاریخچه تراکنش‌ها / History", callback_data="wallet_history")
    builder.adjust(1)
    return builder.as_markup()


def get_deposit_presets_keyboard() -> InlineKeyboardMarkup:
    """
    Builds preset amount options for fast deposit selections.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 $1.00", callback_data="deposit_preset:1.0")
    builder.button(text="💵 $5.00", callback_data="deposit_preset:5.0")
    builder.button(text="💵 $10.00", callback_data="deposit_preset:10.0")
    builder.button(text="💵 $20.00", callback_data="deposit_preset:20.0")
    builder.button(text="✏️ مبلغ دلخواه / Custom", callback_data="deposit_custom")
    builder.button(text="❌ انصراف / Cancel", callback_data="deposit_cancel")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()
