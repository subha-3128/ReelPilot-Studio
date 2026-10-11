import asyncio
import logging
from typing import Optional
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import ProcessingJob
from app.telegram.handlers import (
    start_command,
    help_command,
    mode_command,
    settings_command,
    status_command,
    jobs_command,
    cancel_command,
    retry_command,
    text_message_handler,
    callback_query_handler,
)

logger = logging.getLogger("studio.telegram.bot")

class TelegramBotManager:
    """
    Manages the lifecycle of the ReelPilot Telegram Bot.
    Runs async long-polling without blocking the FastAPI event loop.
    """
    def __init__(self):
        self.application: Optional[Application] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._is_running = False

    def is_configured(self) -> bool:
        return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_MODE != "disabled")

    async def start(self):
        if not self.is_configured():
            logger.info("Telegram Bot Token not configured or mode is disabled. Bot polling skipped.")
            return

        if self._is_running:
            return

        try:
            logger.info("Initializing ReelPilot Telegram Bot...")
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

            # Register Command Handlers
            self.application.add_handler(CommandHandler("start", start_command))
            self.application.add_handler(CommandHandler("help", help_command))
            self.application.add_handler(CommandHandler("mode", mode_command))
            self.application.add_handler(CommandHandler("settings", settings_command))
            self.application.add_handler(CommandHandler("status", status_command))
            self.application.add_handler(CommandHandler("jobs", jobs_command))
            self.application.add_handler(CommandHandler("cancel", cancel_command))
            self.application.add_handler(CommandHandler("retry", retry_command))

            # Register Callback Query & Text Message Handlers
            self.application.add_handler(CallbackQueryHandler(callback_query_handler))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

            await self.application.initialize()
            await self.application.start()
            
            # Start polling updater
            await self.application.updater.start_polling(drop_pending_updates=True)
            self._is_running = True
            logger.info("ReelPilot Telegram Bot started polling successfully.")

            # Run startup job recovery
            self._recover_interrupted_jobs()

        except Exception as e:
            logger.error("Failed to start Telegram Bot: %s", e)
            self._is_running = False

    def _recover_interrupted_jobs(self):
        """Identify jobs that were interrupted in flight before server restart."""
        db: Session = SessionLocal()
        try:
            interrupted = (
                db.query(ProcessingJob)
                .filter(
                    ProcessingJob.status.in_([
                        "downloading",
                        "transcribing",
                        "burning_subtitles",
                        "analyzing",
                        "exporting",
                        "publishing",
                    ])
                )
                .all()
            )
            for j in interrupted:
                logger.warning("Recovering interrupted job %s (was in %s state)", j.id, j.status)
                j.status = "failed"
                j.error_message = "Server restarted during processing. Safe recovery: tap /retry to restart job."
            db.commit()
        except Exception as e:
            logger.error("Error during job startup recovery: %s", e)
        finally:
            db.close()

    async def stop(self):
        if not self._is_running or not self.application:
            return

        logger.info("Stopping ReelPilot Telegram Bot...")
        try:
            if self.application.updater and self.application.updater.running:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self._is_running = False
            logger.info("ReelPilot Telegram Bot stopped cleanly.")
        except Exception as e:
            logger.warning("Error stopping Telegram Bot: %s", e)

telegram_bot_manager = TelegramBotManager()
