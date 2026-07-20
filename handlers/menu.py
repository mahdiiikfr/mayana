import logging
from typing import Callable
from aiogram import Router, F
from aiogram.types import Message
from db.connection import DatabaseManager
from keyboards.common import get_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="menu")


@router.message(F.text.in_({"👤 حساب کاربری", "👤 My Account"}))
async def cmd_my_account(message: Message, db: DatabaseManager, _: Callable[[str], str], locale: str) -> None:
    """
    Displays current user account profile details including registration date,
    verification status, and net balance.
    """
    user_id = message.from_user.id
    user_data = await db.users.get_user(user_id)
    balance = await db.wallet.get_balance(user_id)

    if not user_data:
        return

    is_verified_str = "✅ تأیید شده" if user_data["is_verified"] else "❌ تأیید نشده"
    if locale != "fa":
        is_verified_str = "✅ Verified" if user_data["is_verified"] else "❌ Unverified"

    if locale == "fa":
        profile_text = (
            f"👤 **پروفایل کاربری شما**\n\n"
            f"🆔 شناسه کاربر: `{user_data['user_id']}`\n"
            f"👤 نام کاربری: @{user_data['username'] or 'ندارد'}\n"
            f"📱 وضعیت تأیید همراه: {is_verified_str}\n"
            f"💳 موجودی کیف پول: `{balance:.2f} دلار`\n"
            f"📅 تاریخ عضویت: `{user_data['created_at']}`"
        )
    else:
        profile_text = (
            f"👤 **Your Profile**\n\n"
            f"🆔 User ID: `{user_data['user_id']}`\n"
            f"👤 Username: @{user_data['username'] or 'None'}\n"
            f"📱 Phone Verification: {is_verified_str}\n"
            f"💳 Wallet Balance: `${balance:.2f}`\n"
            f"📅 Date Joined: `{user_data['created_at']}`"
        )

    await message.answer(text=profile_text, parse_mode="Markdown")


@router.message(F.text.in_({"📞 پشتیبانی", "📞 Support"}))
async def cmd_support(message: Message, locale: str) -> None:
    """
    Displays localized support and channel information.
    """
    if locale == "fa":
        support_text = (
            "📞 **بخش پشتیبانی**\n\n"
            "برای ارتباط با پشتیبانی، پیگیری پرداخت‌ها و یا گزارش هرگونه مشکل فنی از لینک‌های زیر استفاده کنید:\n\n"
            "📢 کانال اطلاع‌رسانی: @NexNode\n"
            "💬 پشتیبان رسمی: @NexNode_Support"
        )
    else:
        support_text = (
            "📞 **Support Desk**\n\n"
            "To contact support, track payments, or report technical issues, use the links below:\n\n"
            "📢 News Channel: @NexNode\n"
            "💬 Official Support: @NexNode_Support"
        )

    await message.answer(text=support_text, parse_mode="Markdown")


@router.message(F.text.in_({"🔙 بازگشت", "🔙 Back"}))
async def cmd_back_to_menu(message: Message, locale: str) -> None:
    """
    Navigates the user back to the main menu, resetting state keyboards.
    """
    if locale == "fa":
        msg = "به منوی اصلی بازگشتید."
    else:
        msg = "Returned to the main menu."

    await message.answer(text=msg, reply_markup=get_main_menu_keyboard(locale))
