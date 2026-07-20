import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramAPIError

from config import settings
from db.connection import DatabaseManager
from states.admin import BroadcastState, ChargeUserState
from keyboards.admin import get_admin_dashboard_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin")


# --- HELPER SECURITY CHECK ---

def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_ID


# --- ADMIN COMMAND PANEL ---

@router.message(Command("admin"))
async def cmd_admin_panel(message: Message) -> None:
    """
    Displays the administrator dashboard interface.
    """
    if not is_admin(message.from_user.id):
        return  # Silently ignore non-admin commands for security hardening

    text = (
        "👑 **پنل مدیریت ربات HostVDS**\n\n"
        "به بخش مدیریت خوش آمدید. لطفاً جهت مشاهده گزارشات یا انجام تراکنش‌های سیستمی یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await message.answer(text=text, parse_mode="Markdown", reply_markup=get_admin_dashboard_keyboard())


# --- SYSTEM STATS ---

@router.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: CallbackQuery, db: DatabaseManager) -> None:
    """
    Computes and prints system stats: total users, active servers count, and total holdings.
    """
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied.", show_alert=True)
        return

    # Compute stats using sqlite aggregation
    async with db.connection.execute("SELECT COUNT(*) FROM users;") as cursor:
        total_users = (await cursor.fetchone())[0]

    async with db.connection.execute("SELECT COUNT(*) FROM vps WHERE status = 'ACTIVE';") as cursor:
        active_vps = (await cursor.fetchone())[0]

    # Calculate net wallets sum (all charges minus deductions)
    async with db.connection.execute(
        "SELECT SUM(CASE WHEN transaction_type = 'charge' THEN amount ELSE -amount END) FROM wallet WHERE status = 'COMPLETED';"
    ) as cursor:
        total_wallet_holdings = (await cursor.fetchone())[0] or 0.0

    stats_text = (
        "📊 **آمار کلی ربات تجاری**\n\n"
        f"👥 کل کاربران ثبت‌شده: `{total_users}`\n"
        f"🖥 سرورهای مجازی فعال: `{active_vps}`\n"
        f"💰 مجموع اعتبار کیف پول‌ها: `{total_wallet_holdings:.2f} دلار`"
    )

    await callback.message.answer(text=stats_text, parse_mode="Markdown")
    await callback.answer()


# --- LIST ALL ACTIVE SERVERS ---

@router.callback_query(F.data == "admin_servers_list")
async def process_admin_servers_list(callback: CallbackQuery, db: DatabaseManager) -> None:
    """
    Lists all servers registered under the platform.
    """
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied.", show_alert=True)
        return

    async with db.connection.execute(
        "SELECT vps_id, user_id, server_name, ip_address, status FROM vps;"
    ) as cursor:
        servers = await cursor.fetchall()

    if not servers:
        await callback.message.answer("هیچ سروری در دیتابیس ثبت نشده است.")
        await callback.answer()
        return

    report = "🖥 **لیست تمامی سرورهای ثبت شده**\n\n"
    for srv in servers:
        vps_id, user_id, name, ip, status = srv
        report += (
            f"🆔 کد: `{vps_id}` | کاربر: `{user_id}`\n"
            f"🖥 نام: `{name}`\n"
            f"🌐 آی‌پی: `{ip or 'نامشخص'}`\n"
            f"⚡ وضعیت: **{status}**\n"
            f"───────────────────\n"
        )

    await callback.message.answer(text=report, parse_mode="Markdown")
    await callback.answer()


# --- ASYNC MASS BROADCAST ---

@router.callback_query(F.data == "admin_broadcast")
async def process_admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Initiates the broadcast wizard.
    """
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied.", show_alert=True)
        return

    await state.set_state(BroadcastState.enter_message)
    await callback.message.edit_text("📢 لطفاً متن پیام همگانی خود را ارسال کنید:")
    await callback.answer()


@router.message(BroadcastState.enter_message)
async def process_broadcast_message_text(message: Message, db: DatabaseManager, state: FSMContext, bot: Bot) -> None:
    """
    Sends the broadcast message to all platform users. Handles and logs blocks gracefully.
    """
    if not is_admin(message.from_user.id):
        return

    broadcast_text = message.text.strip()
    await state.clear()

    await message.answer("🔄 در حال ارسال پیام همگانی به تمام کاربران...")

    # Fetch all user IDs
    async with db.connection.execute("SELECT user_id FROM users;") as cursor:
        rows = await cursor.fetchall()
        user_ids = [row[0] for row in rows]  # Fixed: correctly unpack single item tuples

    sent_count = 0
    fail_count = 0

    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.05) # Rate limiting to prevent telegram flood block
        except TelegramAPIError as e:
            logger.warning(f"Failed to send broadcast to user {uid}: {e}")
            fail_count += 1

    await message.answer(
        f"✅ **ارسال پیام همگانی به پایان رسید!**\n\n"
        f"🟢 با موفقیت ارسال شد: `{sent_count}`\n"
        f"🔴 ناموفق (دی اکتیو یا بلاک): `{fail_count}`"
    )


# --- MANUAL BALANCE CHARGING ---

@router.callback_query(F.data == "admin_charge_user")
async def process_admin_charge_user(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Initiates manual user balance adjustment wizard.
    """
    if not is_admin(callback.from_user.id):
        await callback.answer("Access Denied.", show_alert=True)
        return

    await state.set_state(ChargeUserState.enter_user_id)
    await callback.message.edit_text("💳 لطفاً شناسه عددی تلگرام (User ID) کاربر مورد نظر را ارسال کنید:")
    await callback.answer()


@router.message(ChargeUserState.enter_user_id)
async def process_charge_user_id(message: Message, db: DatabaseManager, state: FSMContext) -> None:
    """
    Validates the input User ID.
    """
    if not is_admin(message.from_user.id):
        return

    try:
        target_uid = int(message.text.strip())
        user_data = await db.users.get_user(target_uid)
        if not user_data:
            await message.answer("❌ کاربر مورد نظر در دیتابیس یافت نشد. لطفاً شناسه دیگری ارسال کنید:")
            return
    except ValueError:
        await message.answer("❌ شناسه نامعتبر است. یک عدد صحیح ارسال کنید:")
        return

    await state.update_data(target_user_id=target_uid)
    await state.set_state(ChargeUserState.enter_amount)
    await message.answer(f"💵 کاربر @{user_data['username'] or 'بدون یوزرنیم'} تایید شد.\nمبلغ شارژ را به عدد ارسال کنید (مثلاً 5.0 برای افزایش یا -3.0 برای کسر):")


@router.message(ChargeUserState.enter_amount)
async def process_charge_amount(message: Message, db: DatabaseManager, state: FSMContext, bot: Bot) -> None:
    """
    Executes the balance adjustment and records transaction memo logs.
    """
    if not is_admin(message.from_user.id):
        return

    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ مبلغ نامعتبر است. مجدداً ارسال کنید:")
        return

    data = await state.get_data()
    target_uid = data["target_user_id"]
    await state.clear()

    # Perform balance update
    new_balance = await db.wallet.update_balance(user_id=target_uid, amount=amount)

    # Inform Admin
    await message.answer(
        f"✅ **تغییر موجودی با موفقیت اعمال شد!**\n\n"
        f"👤 کاربر: `{target_uid}`\n"
        f"💵 مبلغ تغییر یافته: `{amount:.2f} دلار`\n"
        f"💰 موجودی نهایی کاربر: `{new_balance:.2f} دلار`"
    )

    # Inform User directly
    try:
        user_data = await db.users.get_user(target_uid)
        locale = user_data.get("language_code", "fa") if user_data else "fa"
        if locale == "fa":
            notif_msg = (
                f"💳 **اعتبار حساب شما تغییر یافت!**\n\n"
                f"مبلغ تغییر یافته: `{amount:.2f} دلار` (شارژ سیستمی)\n"
                f"💰 موجودی جدید شما: `{new_balance:.2f} دلار`"
            )
        else:
            notif_msg = (
                f"💳 **Your account balance has been updated!**\n\n"
                f"Amount changed: `${amount:.2f}` (System credit)\n"
                f"💰 New balance: `${new_balance:.2f}`"
            )
        await bot.send_message(chat_id=target_uid, text=notif_msg, parse_mode="Markdown")
    except TelegramAPIError as e:
        logger.warning(f"Could not notify user {target_uid} about manual credit: {e}")
