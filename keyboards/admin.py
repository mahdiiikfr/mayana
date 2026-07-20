from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    """
    Builds the inline keyboard for the administrator control panel.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 آمار کلی سیستم / System Stats", callback_data="admin_stats")
    builder.button(text="📢 ارسال پیام همگانی / Broadcast", callback_data="admin_broadcast")
    builder.button(text="💳 شارژ دستی کاربر / Manual Charge", callback_data="admin_charge_user")
    builder.button(text="🖥 لیست کل سرورها / All Servers", callback_data="admin_servers_list")
    builder.adjust(1)
    return builder.as_markup()
