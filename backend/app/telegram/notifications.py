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
    stage_emojis = {
        "awaiting_input": "[Awaiting Settings]",
        "queued": "[Queued]",
        "downloading": "[1/5 Downloading Source]",
        "transcribing": "[2/5 Transcribing Audio]",
        "burning_subtitles": "[3/5 Burning Subtitles]",
        "analyzing": "[4/5 Generating AI Metadata]",
        "exporting": "[5/5 Exporting Final MP4]",
        "ready": "[Ready]",
        "publishing": "[Publishing to Platforms]",
        "completed": "[Completed]",
        "failed": "[Failed]",
        "cancelled": "[Cancelled]",
    }
    
    header = stage_emojis.get(job.status, f"[{job.status.upper()}]")
    progress_bar = f"{int(job.progress)}%" if job.progress else "0%"
    
    text = (
        f"ReelPilot Job: {job.id[:8]}\n"
        f"Status: {header}\n"
        f"Progress: {progress_bar}\n"
        f"Stage: {job.stage or 'Processing'}\n"
    )
    if job.error_message:
        text += f"\nError: {job.error_message}\n"
    return text
