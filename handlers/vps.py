import logging
from typing import Callable, Any, Dict
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup

from db.connection import DatabaseManager
from states.vps import BuyVPSState
from services.openstack import OpenStackService, OpenStackAPIError
from keyboards.vps import (
    get_networks_keyboard,
    get_flavors_keyboard,
    get_images_keyboard,
    get_confirm_purchase_keyboard,
    get_server_control_keyboard
)

logger = logging.getLogger(__name__)
router = Router(name="vps")
openstack = OpenStackService()


# --- MY VPS / LISTING ACTIVE INSTANCES ---

@router.message(F.text.in_({"🖥 مدیریت سرورها (VPS)", "🖥 Manage Servers (VPS)"}))
async def cmd_my_vps(message: Message, db: DatabaseManager, locale: str) -> None:
    """
    Lists all VPS instances belonging to the user.
    """
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested their VPS list.")

    # Get local registered servers
    vps_list = await db.vps.get_user_vps_list(user_id)

    if not vps_list:
        if locale == "fa":
            msg = (
                "❌ شما هیچ سرور مجازی فعالی ندارید!\n\n"
                "برای تهیه یک سرور مجازی ابری با کیفیت، دستور /buy_vps را ارسال کنید "
                "یا روی منوهای زیر کلیک کنید."
            )
        else:
            msg = (
                "❌ You do not have any active virtual servers!\n\n"
                "To buy a new cloud server, send the /buy_vps command "
                "or use the options below."
            )
        await message.answer(text=msg)
        return

    # Display each registered server with its live status queried from OpenStack
    for vps in vps_list:
        uuid = vps["openstack_uuid"]
        live_status = vps["status"]
        ip = vps["ip_address"] or "Under Provisioning..."

        try:
            # Query live OpenStack status
            details = await openstack.get_server_details(uuid)
            if details:
                # Extract actual status
                live_status = details.get("status", details.get("Status", vps["status"]))
                # Save status update locally in database for synchronization
                await db.vps.update_vps_status(uuid, live_status)
        except Exception:
            logger.warning(f"Failed to fetch live OpenStack status for UUID {uuid}")

        if locale == "fa":
            info_text = (
                f"🖥 **نام سرور: {vps['server_name']}**\n\n"
                f"🆔 شناسه مرجع: `{vps['vps_id']}`\n"
                f"🌐 آدرس آی‌پی (IP): `{ip}`\n"
                f"📊 مشخصات پلن: `{vps['flavor']}`\n"
                f"⚡ وضعیت لایو سرور: **{live_status}**\n"
                f"📅 تاریخ انقضا: `{vps['expires_at']}`"
            )
        else:
            info_text = (
                f"🖥 **Server Name: {vps['server_name']}**\n\n"
                f"🆔 Internal ID: `{vps['vps_id']}`\n"
                f"🌐 IP Address: `{ip}`\n"
                f"📊 Plan / Flavor: `{vps['flavor']}`\n"
                f"⚡ Live Status: **{live_status}**\n"
                f"📅 Expiry Date: `{vps['expires_at']}`"
            )

        await message.answer(
            text=info_text,
            parse_mode="Markdown",
            reply_markup=get_server_control_keyboard(uuid)
        )


# --- VPS CONTROLS (START / STOP / DELETE / REFRESH) ---

@router.callback_query(F.data.startswith("vps_"))
async def process_server_control(callback: CallbackQuery, db: DatabaseManager, locale: str) -> None:
    """
    Handles inline callback actions for active server power management.
    """
    parts = callback.data.split(":")
    action = parts[0]
    uuid = parts[1]

    # Retrieve local server meta
    vps = await db.vps.get_vps_by_uuid(uuid)
    if not vps:
        await callback.answer("Server not found in database.", show_alert=True)
        return

    try:
        if action == "vps_start":
            await openstack.start_server(uuid)
            await db.vps.update_vps_status(uuid, "ACTIVE")
            msg = "درخواست روشن کردن سرور با موفقیت ارسال شد." if locale == "fa" else "Start request sent successfully."
            await callback.answer(msg, show_alert=True)

        elif action == "vps_stop":
            await openstack.stop_server(uuid)
            await db.vps.update_vps_status(uuid, "SHUTOFF")
            msg = "درخواست خاموش کردن سرور با موفقیت ارسال شد." if locale == "fa" else "Stop request sent successfully."
            await callback.answer(msg, show_alert=True)

        elif action == "vps_delete":
            await openstack.delete_server(uuid)
            # Remove from local database record on delete
            # Alternatively, keep record as status 'DELETED'
            await db.vps.update_vps_status(uuid, "DELETED")
            msg = "سرور با موفقیت حذف شد." if locale == "fa" else "Server deleted successfully."
            await callback.message.delete()
            await callback.answer(msg, show_alert=True)

        elif action == "vps_refresh":
            details = await openstack.get_server_details(uuid)
            live_status = details.get("status", details.get("Status", "ACTIVE"))
            await db.vps.update_vps_status(uuid, live_status)

            # Edit text to reflect updated status
            msg = "وضعیت سرور به‌روزرسانی شد." if locale == "fa" else "Server status refreshed."
            await callback.answer(msg)

            # Re-fetch local data to reconstruct message
            vps = await db.vps.get_vps_by_uuid(uuid)
            ip = vps["ip_address"] or "Provisioning..."
            if locale == "fa":
                updated_text = (
                    f"🖥 **نام سرور: {vps['server_name']}**\n\n"
                    f"🆔 شناسه مرجع: `{vps['vps_id']}`\n"
                    f"🌐 آدرس آی‌پی (IP): `{ip}`\n"
                    f"📊 مشخصات پلن: `{vps['flavor']}`\n"
                    f"⚡ وضعیت لایو سرور: **{live_status}**\n"
                    f"📅 تاریخ انقضا: `{vps['expires_at']}`"
                )
            else:
                updated_text = (
                    f"🖥 **Server Name: {vps['server_name']}**\n\n"
                    f"🆔 Internal ID: `{vps['vps_id']}`\n"
                    f"🌐 IP Address: `{ip}`\n"
                    f"📊 Plan / Flavor: `{vps['flavor']}`\n"
                    f"⚡ Live Status: **{live_status}**\n"
                    f"📅 Expiry Date: `{vps['expires_at']}`"
                )
            await callback.message.edit_text(text=updated_text, parse_mode="Markdown", reply_markup=callback.message.reply_markup)

    except OpenStackAPIError as e:
        logger.error(f"OpenStack CLI execution failure: {e.stderr}")
        err_msg = "خطا در برقراری ارتباط با پنل ابری." if locale == "fa" else "Error communicating with cloud panel."
        await callback.answer(f"{err_msg} ({e})", show_alert=True)


# --- STEP-BY-STEP FSM VPS DEPLOYMENT PROCESS ---

@router.message(F.text == "/buy_vps")
async def start_buy_vps(message: Message, db: DatabaseManager, state: FSMContext, _: Callable[[str], str], locale: str) -> None:
    """
    Kicks off the VPS selection workflow.
    Validates user wallet balance before querying cloud locations.
    """
    user_id = message.from_user.id
    balance = await db.wallet.get_balance(user_id)

    # Validate minimum limit (0.5 USD)
    if balance < 0.5:
        await message.answer(text=_("insufficient_balance"))
        return

    await message.answer("دریافت لوکیشن‌ها و شبکه‌های فعال ابری..." if locale == "fa" else "Querying active cloud network locations...")

    try:
        # Fetch active networks from OpenStack
        networks = await openstack.get_networks()
        if not networks:
            raise OpenStackAPIError("No networks found.")

        await state.set_state(BuyVPSState.select_location)
        msg_text = "لطفاً لوکیشن/شبکه مورد نظر برای سرور جدید را انتخاب کنید:" if locale == "fa" else "Please select the desired network location for your server:"
        await message.answer(text=msg_text, reply_markup=get_networks_keyboard(networks))
    except Exception as e:
        logger.exception(f"Failed to query networks: {e}")
        await message.answer("خطا در واکشی لوکیشن‌های ابری. لطفاً دوباره تلاش کنید." if locale == "fa" else "Error fetching cloud locations. Please try again.")
        await state.clear()


@router.callback_query(BuyVPSState.select_location, F.data.startswith("buy_net:"))
async def process_location(callback: CallbackQuery, state: FSMContext, locale: str) -> None:
    """
    Stores selected network location in FSM and queries available Flavors/Plans.
    """
    net_id = callback.data.split(":")[1]
    await state.update_data(network_id=net_id)

    await callback.message.edit_text("دریافت پلن‌های سخت‌افزاری فعال..." if locale == "fa" else "Querying active cloud hardware plans...")

    try:
        flavors = await openstack.get_flavors()
        await state.set_state(BuyVPSState.select_flavor)
        msg_text = "لطفاً پلن سخت‌افزاری (Flavor) سرور را انتخاب کنید:" if locale == "fa" else "Please select server plan/flavor size:"
        await callback.message.edit_text(text=msg_text, reply_markup=get_flavors_keyboard(flavors))
    except Exception as e:
        logger.exception(f"Failed to fetch flavors: {e}")
        await callback.message.answer("خطا در بارگذاری پلن‌های ابری. مراحل لغو شد." if locale == "fa" else "Error loading cloud plans. Workflow canceled.")
        await state.clear()


@router.callback_query(BuyVPSState.select_flavor, F.data.startswith("buy_flv:"))
async def process_flavor(callback: CallbackQuery, state: FSMContext, locale: str) -> None:
    """
    Stores selected hardware plan in FSM and queries available Operating System Images.
    """
    flv_id = callback.data.split(":")[1]
    await state.update_data(flavor_id=flv_id)

    await callback.message.edit_text("دریافت سیستم‌عامل‌های در دسترس..." if locale == "fa" else "Querying available operating systems...")

    try:
        images = await openstack.get_images()
        await state.set_state(BuyVPSState.select_image)
        msg_text = "لطفاً سیستم‌عامل (Image) مورد نظر را انتخاب کنید:" if locale == "fa" else "Please select preferred Operating System:"
        await callback.message.edit_text(text=msg_text, reply_markup=get_images_keyboard(images))
    except Exception as e:
        logger.exception(f"Failed to fetch images: {e}")
        await callback.message.answer("خطا در بارگذاری سیستم‌عامل‌ها. مراحل لغو شد." if locale == "fa" else "Error loading operating system images. Workflow canceled.")
        await state.clear()


@router.callback_query(BuyVPSState.select_image, F.data.startswith("buy_img:"))
async def process_image(callback: CallbackQuery, state: FSMContext, locale: str) -> None:
    """
    Stores selected Image ID in FSM and presents final deployment verification details.
    """
    img_id = callback.data.split(":")[1]
    await state.update_data(image_id=img_id)

    data = await state.get_data()

    await state.set_state(BuyVPSState.confirm_purchase)

    if locale == "fa":
        summary = (
            "📋 **پیش‌نمایش و تایید نهایی سفارش سرور جدید**\n\n"
            f"🌐 شناسه لوکیشن/شبکه: `{data['network_id']}`\n"
            f"⚙️ شناسه پلن سخت‌افزاری: `{data['flavor_id']}`\n"
            f"💿 شناسه سیستم‌عامل انتخابی: `{data['image_id']}`\n\n"
            "⚠️ هزینه ساعتی استفاده از این سرور به صورت خودکار از کیف پول شما کسر خواهد شد.\n"
            "آیا مایل به تایید سفارش و راه‌اندازی سرور هستید؟"
        )
    else:
        summary = (
            "📋 **New Server Order Summary & Confirmation**\n\n"
            f"🌐 Network Location ID: `{data['network_id']}`\n"
            f"⚙️ Hardware Flavor ID: `{data['flavor_id']}`\n"
            f"💿 OS Image ID: `{data['image_id']}`\n\n"
            "⚠️ Hourly runtime costs will be automatically deducted from your wallet.\n"
            "Do you want to confirm your order and deploy the server?"
        )

    await callback.message.edit_text(text=summary, parse_mode="Markdown", reply_markup=get_confirm_purchase_keyboard())


@router.callback_query(BuyVPSState.confirm_purchase, F.data == "buy_confirm_deploy")
async def process_confirm_purchase(callback: CallbackQuery, db: DatabaseManager, state: FSMContext, _: Callable[[str], str], locale: str) -> None:
    """
    Finalizes the purchase! Deploys the VPS instance asynchronously on HostVDS,
    deducts initial deploy setup fees (0.5 USD), updates transaction ledgers,
    saves server metadata locally, and issues access credentials.
    """
    user_id = callback.from_user.id
    data = await state.get_data()
    await state.clear()

    await callback.message.edit_text("⚙️ در حال راه‌اندازی و ایجاد سرور مجازی ابری شما در HostVDS..." if locale == "fa" else "⚙️ Initialising and creating your VPS instance in HostVDS...")

    # Double check wallet balance
    balance = await db.wallet.get_balance(user_id)
    if balance < 0.5:
        await callback.message.edit_text(text=_("insufficient_balance"))
        return

    try:
        # Create unique hostname
        server_name = f"user-{user_id}-vps"

        # Deploy instance asynchronously via OpenStack Client CLI
        result = await openstack.create_server(
            name=server_name,
            flavor_id=data["flavor_id"],
            image_id=data["image_id"],
            network_id=data["network_id"]
        )

        uuid = result.get("id", result.get("ID", ""))
        if not uuid:
            raise OpenStackAPIError("Server deployed successfully but no ID was returned.")

        # Deduct setup fee (0.5 USD) from the user ledger
        await db.wallet.add_transaction(
            user_id=user_id,
            amount=0.5,
            transaction_type="deduction",
            description=f"VPS deployment setup fee for server {server_name}"
        )

        # Register server locally
        expires = datetime.now() + timedelta(days=30)
        # Sometime CLI returns access addresses directly, else fetch via show details
        ip_addr = result.get("addresses", result.get("IP", "Retrieving IP..."))

        await db.vps.add_vps(
            user_id=user_id,
            openstack_uuid=uuid,
            server_name=server_name,
            ip_address=ip_addr,
            flavor=data["flavor_id"],
            status="ACTIVE",
            expires_at=expires
        )

        if locale == "fa":
            success_msg = (
                "✅ **سرور شما با موفقیت در هاست‌وی‌دی‌اس ایجاد شد!**\n\n"
                f"🖥 نام سرور: `{server_name}`\n"
                f"🆔 شناسه رفرنس: `{uuid}`\n"
                f"🌐 آدرس آی‌پی (IP): `{ip_addr}`\n"
                f"⚙️ پلن سخت‌افزاری: `{data['flavor_id']}`\n\n"
                "ℹ️ نصب و بالا آمدن کامل سیستم‌عامل ممکن است تا ۱۵ دقیقه طول بکشد. "
                "جهت چک کردن آخرین وضعیت زنده سرور به بخش مدیریت سرورهای من مراجعه کنید."
            )
        else:
            success_msg = (
                "✅ **Your Server has been successfully deployed in HostVDS!**\n\n"
                f"🖥 Server Name: `{server_name}`\n"
                f"🆔 Reference UUID: `{uuid}`\n"
                f"🌐 IP Address: `{ip_addr}`\n"
                f"⚙️ Hardware Plan: `{data['flavor_id']}`\n\n"
                "ℹ️ Complete OS installation and bootup may take up to 15 minutes. "
                "Go to 'Manage Servers' section to track updated live status."
            )

        await callback.message.edit_text(text=success_msg, parse_mode="Markdown")

    except OpenStackAPIError as e:
        logger.error(f"Failed to deploy VPS: {e.stderr}")
        err_msg = (
            "❌ **خطا در راه‌اندازی سرور ابری**\n\n"
            "متأسفانه اتصال یا اجرای دستور با خطا مواجه شد. لطفاً موضوع را به بخش پشتیبانی اطلاع دهید."
        ) if locale == "fa" else (
            "❌ **Error Deploying Cloud Server**\n\n"
            "Unfortunately, communicating with the cloud provider failed. Please report this to support."
        )
        await callback.message.edit_text(text=f"{err_msg}\n\n`{e}`", parse_mode="Markdown")


# --- GLOBAL CANCEL BUTTON HANDLERS ---

@router.callback_query(F.data == "buy_cancel")
async def process_cancel_purchase(callback: CallbackQuery, state: FSMContext, locale: str) -> None:
    """
    Cancels current active purchase wizard state and resets keyboards.
    """
    await state.clear()
    msg = "سفارش شما لغو شد." if locale == "fa" else "Your order has been canceled."
    await callback.message.edit_text(text=msg)
    await callback.answer()


@router.callback_query(F.data == "buy_back_net")
async def process_back_net(callback: CallbackQuery, state: FSMContext, locale: str) -> None:
    """
    Backs up one step to network location selection.
    """
    await state.set_state(BuyVPSState.select_location)
    try:
        networks = await openstack.get_networks()
        msg_text = "لطفاً لوکیشن/شبکه مورد نظر برای سرور جدید را انتخاب کنید:" if locale == "fa" else "Please select the desired network location for your server:"
        await callback.message.edit_text(text=msg_text, reply_markup=get_networks_keyboard(networks))
    except Exception:
        await callback.message.edit_text("خطا در بارگذاری مجدد لوکیشن‌ها.")
        await state.clear()


@router.callback_query(F.data == "buy_back_flv")
async def process_back_flv(callback: CallbackQuery, state: FSMContext, locale: str) -> None:
    """
    Backs up one step to hardware flavor plan selection.
    """
    await state.set_state(BuyVPSState.select_flavor)
    try:
        flavors = await openstack.get_flavors()
        msg_text = "لطفاً پلن سخت‌افزاری (Flavor) سرور را انتخاب کنید:" if locale == "fa" else "Please select server plan/flavor size:"
        await callback.message.edit_text(text=msg_text, reply_markup=get_flavors_keyboard(flavors))
    except Exception:
        await callback.message.edit_text("خطا در بارگذاری مجدد پلن‌ها.")
        await state.clear()
