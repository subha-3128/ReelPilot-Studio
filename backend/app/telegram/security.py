import functools
import logging
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import settings

logger = logging.getLogger("studio.telegram.security")

def is_user_authorized(user_id: int) -> bool:
    """Check if the given Telegram user ID is present in the allowed users list."""
    allowed = settings.get_allowed_telegram_user_ids()
    if not allowed:
        # If no user IDs are configured, default to False to fail closed.
        return False
    return user_id in allowed

def require_auth(func: Callable) -> Callable:
    """Decorator to enforce Telegram user authorization before executing handler logic."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        user = update.effective_user
        if not user:
            return None

        user_id = user.id
        if not is_user_authorized(user_id):
            logger.warning("Unauthorized access attempt by Telegram user %s (@%s)", user_id, user.username)
            if update.message:
                await update.message.reply_text(
                    f"⛔ Unauthorized Access\n\n"
                    f"Your Telegram User ID is: `{user_id}`\n\n"
                    f"To use ReelPilot, add your ID to your backend configuration:\n"
                    f"TELEGRAM_ALLOWED_USER_IDS={user_id}",
                    parse_mode="Markdown",
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    f"Unauthorized (Your ID: {user_id})", show_alert=True
                )
            return None

        return await func(update, context, *args, **kwargs)

    return wrapper
