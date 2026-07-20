import logging
from typing import Optional
from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db.connection import DatabaseManager
from services.openstack import OpenStackService

logger = logging.getLogger("bot.services.scheduler")


class BillingScheduler:
    """
    BillingScheduler manages background periodic tasks for virtual server billing.
    Uses AsyncIOScheduler to deduct hourly server runtime costs and gracefully suspend
    instances if the user wallet runs out of balance.
    """
    def __init__(self, db_manager: DatabaseManager, bot: Bot) -> None:
        self.db_manager = db_manager
        self.bot = bot
        self.openstack = OpenStackService()
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Starts the scheduler in the background."""
        logger.info("Starting APscheduler daemon...")

        # Add hourly billing checks (runs every 1 hour, or 60 minutes)
        self.scheduler.add_job(
            self.check_vps_billing_job,
            "interval",
            hours=1,
            next_run_time=datetime.now() # trigger immediately on startup
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        """Shuts down the scheduler safely."""
        logger.info("Shutting down APscheduler daemon...")
        self.scheduler.shutdown()

    async def check_vps_billing_job(self) -> None:
        """
        Billing cycle execution:
        - Retrieves all servers with 'ACTIVE' status in SQLite.
        - Deducts hourly runtime cost (e.g. $0.01/hour standard fee).
        - Suspends/turns off the server if user balance drops below $0.00.
        """
        logger.info("Executing recurring server billing check...")

        if not self.db_manager.connection:
            logger.warning("Scheduler skipped billing: Database connection not established.")
            return

        # Simple standard hourly fee, can be adjusted or calculated dynamically per flavor
        hourly_rate = 0.01

        # Query all active VPS servers from the DB
        # To maintain modularity, we query direct from SQLite or fetch all VPS
        # and filter ACTIVE ones.
        query = "SELECT vps_id, user_id, openstack_uuid, server_name, flavor FROM vps WHERE status = 'ACTIVE';"
        async with self.db_manager.connection.execute(query) as cursor:
            active_vps_list = await cursor.fetchall()

        for row in active_vps_list:
            vps_id, user_id, uuid, server_name, flavor = row

            # Get current wallet balance
            balance = await self.db_manager.wallet.get_balance(user_id)
            user_data = await self.db_manager.users.get_user(user_id)
            locale = user_data.get("language_code", "fa") if user_data else "fa"

            # 1. Deduct hourly runtime cost
            await self.db_manager.wallet.add_transaction(
                user_id=user_id,
                amount=hourly_rate,
                transaction_type="deduction",
                description=f"Hourly billing deduction for server {server_name}"
            )

            # Re-fetch balance after deduction
            updated_balance = await self.db_manager.wallet.get_balance(user_id)
            logger.info(f"Billed user {user_id} (${hourly_rate}) for VPS {server_name}. New balance: ${updated_balance:.2f}")

            # 2. Check if balance dropped below zero
            if updated_balance <= 0:
                logger.info(f"User {user_id} has insufficient funds (${updated_balance:.2f}). Powering off VPS {server_name}...")

                try:
                    # Turn off server via OpenStack
                    await self.openstack.stop_server(uuid)

                    # Update local database status
                    await self.db_manager.vps.update_vps_status(uuid, "SHUTOFF")

                    # Send warning notification message in user's selected language
                    if locale == "fa":
                        warning_msg = (
                            f"⚠️ **اخطار خاموشی موقت سرور!**\n\n"
                            f"سرور شما با نام `{server_name}` به دلیل اتمام موجودی کیف پول خاموش شد.\n"
                            f"موجودی فعلی شما: `{updated_balance:.2f} دلار`\n\n"
                            f"لطفاً جهت فعال‌سازی مجدد، کیف پول خود را شارژ کرده و سرور را روشن کنید."
                        )
                    else:
                        warning_msg = (
                            f"⚠️ **Server Suspension Notice!**\n\n"
                            f"Your virtual server `{server_name}` has been stopped due to insufficient funds.\n"
                            f"Current balance: `${updated_balance:.2f}`\n\n"
                            f"Please top up your wallet and restart the server to restore service."
                        )

                    await self.bot.send_message(chat_id=user_id, text=warning_msg, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Failed to gracefully stop server {server_name} on suspension: {e}")
