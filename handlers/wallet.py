import logging
from typing import Callable
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from db.connection import DatabaseManager
from states.wallet import DepositState
from keyboards.wallet import get_wallet_keyboard, get_deposit_presets_keyboard

logger = logging.getLogger(__name__)
router = Router(name="wallet")


# --- DISPLAY WALLET & HISTORY ---

@router.message(F.text.in_({"💳 کیف پول و اعتبار", "💳 Wallet & Credit"}))
async def cmd_wallet_menu(message: Message, db: DatabaseManager, locale: str) -> None:
    """
    Displays the user's current wallet balance and action options.
    """
    user_id = message.from_user.id
    balance = await db.wallet.get_balance(user_id)

    if locale == "fa":
        text = (
            f"💳 **کیف پول دیجیتال شما**\n\n"
            f"💰 موجودی فعلی شما: `{balance:.2f} دلار`\n\n"
            f"توضیحات: جهت ساخت سرور جدید، حداقل موجودی شما باید 0.5 دلار باشد. "
            f"هزینه استفاده از سرورها به صورت ساعتی محاسبه و از موجودی کسر خواهد شد."
        )
    else:
        text = (
            f"💳 **Your Digital Wallet**\n\n"
            f"💰 Current Balance: `${balance:.2f}`\n\n"
            f"Note: To deploy a new server, you need at least $0.50. "
            f"Runtime costs are calculated and deducted hourly from your balance."
        )

    await message.answer(text=text, parse_mode="Markdown", reply_markup=get_wallet_keyboard())


@router.callback_query(F.data == "wallet_history")
async def process_wallet_history(callback: CallbackQuery, db: DatabaseManager, locale: str) -> None:
    """
    Fetches and lists the last 10 transaction history records for the user.
    """
    user_id = callback.from_user.id
    transactions = await db.wallet.get_user_transactions(user_id, limit=10)

    if not transactions:
        msg = "تراکنشی یافت نشد." if locale == "fa" else "No transactions found."
        await callback.answer(msg, show_alert=True)
        return

    if locale == "fa":
        history_text = "📜 **تاریخچه تراکنش‌های اخیر شما**\n\n"
        for tx in transactions:
            type_symbol = "🟢 شارژ" if tx["transaction_type"] == "charge" else "🔴 کسر"
            history_text += (
                f"{type_symbol}: `{tx['amount']:.2f}$`\n"
                f"🔖 بابت: {tx['description'] or 'سیستمی'}\n"
                f"📅 تاریخ: `{tx['created_at']}`\n"
                f"───────────────────\n"
            )
    else:
        history_text = "📜 **Your Recent Transactions**\n\n"
        for tx in transactions:
            type_symbol = "🟢 Deposit" if tx["transaction_type"] == "charge" else "🔴 Charge"
            history_text += (
                f"{type_symbol}: `${tx['amount']:.2f}`\n"
                f"🔖 Description: {tx['description'] or 'System'}\n"
                f"📅 Date: `{tx['created_at']}`\n"
                f"───────────────────\n"
            )

    await callback.message.answer(text=history_text, parse_mode="Markdown")
    await callback.answer()


# --- DEPOSIT FLOW ---

@router.callback_query(F.data == "wallet_deposit")
async def process_wallet_deposit(callback: CallbackQuery, locale: str) -> None:
    """
    Shows deposit presets or prompts for a custom amount.
    """
    if locale == "fa":
        text = (
            "💵 **شارژ حساب کاربری**\n\n"
            "لطفاً مبلغ مورد نظر برای افزایش اعتبار خود را انتخاب کنید "
            "یا دکمه 'مبلغ دلخواه' را بفشارید:"
        )
    else:
        text = (
            "💵 **Top up Wallet**\n\n"
            "Please select the desired amount to charge your account "
            "or choose 'Custom amount':"
        )
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=get_deposit_presets_keyboard())


@router.callback_query(F.data.startswith("deposit_preset:"))
async def process_deposit_preset(callback: CallbackQuery, db: DatabaseManager, locale: str) -> None:
    """
    Processes deposit using a quick preset amount, updating user wallet ledger.
    """
    amount = float(callback.data.split(":")[1])
    user_id = callback.from_user.id

    logger.info(f"User {user_id} deposited via preset: {amount}")

    # Record completed deposit transaction in database
    await db.wallet.add_transaction(
        user_id=user_id,
        amount=amount,
        transaction_type="charge",
        description="Deposit preset top-up"
    )

    new_balance = await db.wallet.get_balance(user_id)

    if locale == "fa":
        msg = (
            f"✅ **افزایش اعتبار با موفقیت انجام شد!**\n\n"
            f"💵 مبلغ واریزی: `{amount:.2f} دلار`\n"
            f"💰 موجودی جدید شما: `{new_balance:.2f} دلار`"
        )
    else:
        msg = (
            f"✅ **Deposit successful!**\n\n"
            f"💵 Amount added: `${amount:.2f}`\n"
            f"💰 New balance: `${new_balance:.2f}`"
        )

    await callback.message.edit_text(text=msg, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "deposit_custom")
async def process_deposit_custom(callback: CallbackQuery, state: FSMContext, locale: str) -> None:
    """
    Prompts the user to write their custom deposit amount in text.
    """
    await state.set_state(DepositState.enter_amount)

    if locale == "fa":
        text = "✍️ لطفاً مبلغ دلخواه خود را به عدد (مثلاً 2.5) ارسال کنید:"
    else:
        text = "✍️ Please enter your custom deposit amount as a decimal number (e.g. 2.5):"

    await callback.message.edit_text(text=text)
    await callback.answer()


@router.message(DepositState.enter_amount)
async def process_custom_amount_text(message: Message, db: DatabaseManager, state: FSMContext, locale: str) -> None:
    """
    Handles text inputs for custom wallet top up, validating the entry.
    """
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        msg = "❌ عدد وارد شده نامعتبر است. لطفاً یک عدد مثبت ارسال کنید:" if locale == "fa" else "❌ Invalid amount. Please enter a valid positive number:"
        await message.answer(text=msg)
        return

    user_id = message.from_user.id
    await state.clear()

    # Record completed custom deposit
    await db.wallet.add_transaction(
        user_id=user_id,
        amount=amount,
        transaction_type="charge",
        description="Custom deposit top-up"
    )

    new_balance = await db.wallet.get_balance(user_id)

    if locale == "fa":
        msg = (
            f"✅ **افزایش اعتبار با موفقیت انجام شد!**\n\n"
            f"💵 مبلغ واریزی: `{amount:.2f} دلار`\n"
            f"💰 موجودی جدید شما: `{new_balance:.2f} دلار`"
        )
    else:
        msg = (
            f"✅ **Deposit successful!**\n\n"
            f"💵 Amount added: `${amount:.2f}`\n"
            f"💰 New balance: `${new_balance:.2f}`"
        )

    await message.answer(text=msg, parse_mode="Markdown")


@router.callback_query(F.data == "deposit_cancel")
async def process_deposit_cancel(callback: CallbackQuery, locale: str) -> None:
    """
    Cancels custom/preset deposit wizard, resetting state.
    """
    msg = "عملیات افزایش اعتبار لغو شد." if locale == "fa" else "Deposit operation canceled."
    await callback.message.edit_text(text=msg)
    await callback.answer()
