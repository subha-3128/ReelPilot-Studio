import logging
from typing import Optional
from telegram import Bot, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest

logger = logging.getLogger("studio.telegram.notifications")

async def safe_edit_message(
    bot: Bot,
    chat_id: str | int,
    message_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> bool:
    """Safely edit a message, suppressing BadRequest if message content is unmodified."""
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return True
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return True
        logger.warning("BadRequest editing Telegram message: %s", e)
        return False
    except TelegramError as e:
        logger.warning("TelegramError editing message: %s", e)
        return False

async def safe_send_message(
    bot: Bot,
    chat_id: str | int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> Optional[int]:
    """Safely send a new message and return its message_id."""
    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return msg.message_id
    except TelegramError as e:
        logger.error("Failed to send Telegram message to %s: %s", chat_id, e)
        return None

def format_job_status_text(job) -> str:
    """Produce clean, formatted status text for a given processing job."""
    stage_labels = {
        "awaiting_input": "Awaiting Parameters",
        "queued": "Queued in Pipeline",
        "downloading": "1/4 Downloading Source Stream",
        "transcribing": "2/4 Audio Analysis & Speech Recognition",
        "burning_subtitles": "Processing Video Stream",
        "analyzing": "3/4 Synthesizing AI Captions & Metadata",
        "exporting": "4/4 Rendering Production Export",
        "ready": "Production Complete",
        "publishing": "Publishing to Target Channels",
        "completed": "Delivered",
        "failed": "Execution Failed",
        "cancelled": "Cancelled",
    }
    
    header = stage_labels.get(job.status, job.status.capitalize())
    progress_bar = f"{int(job.progress)}%" if job.progress else "0%"
    
    text = (
        f"ReelPilot Studio — Production Status\n\n"
        f"Job ID: {job.id[:8]}\n"
        f"Status: {header}\n"
        f"Progress: {progress_bar}\n"
        f"Stage: {job.stage or 'Processing'}\n"
    )
    if job.error_message:
        text += f"\nError Details: {job.error_message}\n"
    return text
