import logging
import re
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import SessionLocal
from app.models.models import ProcessingJob
from app.telegram.security import require_auth
from app.telegram.conversations import (
    get_or_create_user_pref,
    handle_video_url_submission,
    handle_callback_query,
)
from app.telegram.keyboards import build_mode_keyboard
from app.telegram.pipeline import execute_job_pipeline
import asyncio

logger = logging.getLogger("studio.telegram.handlers")

URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)

@require_auth
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    db: Session = SessionLocal()
    try:
        pref = get_or_create_user_pref(db, str(user.id))
        mode = pref.workflow_mode
    finally:
        db.close()

    await update.message.reply_text(
        f"🎬 *Welcome to ReelPilot Studio Bot!*\n\n"
        f"I automate your short-video production pipeline:\n"
        f"1. Send me any authorized Instagram Reel, Kuaishou, or Kwai video link.\n"
        f"2. I'll ask you for preferences (or run automatically).\n"
        f"3. I'll download, sync voice-over, burn subtitles, generate AI copy with Gemini, and return the finished 9:16 video!\n\n"
        f"Current Mode: *{mode.capitalize()}*\n"
        f"Your Telegram ID: `{user.id}`\n\n"
        f"Commands:\n"
        f"• `/mode` — Switch between Interactive and Automatic mode\n"
        f"• `/settings` — View your default preferences\n"
        f"• `/status` — View active processing jobs\n"
        f"• `/jobs` — View recent jobs history\n"
        f"• `/cancel` — Cancel an in-progress workflow\n"
        f"• `/help` — Show help and supported links",
        parse_mode="Markdown",
    )

@require_auth
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        f"📖 *ReelPilot Bot Guide*\n\n"
        f"• *How to produce a video:*\n"
        f"Simply paste any mobile or web Instagram Reel, Kuaishou, or Kwai link, e.g.:\n"
        f"`https://www.instagram.com/reel/Cxxxxxx/`\n"
        f"`https://v.kuaishou.com/KXUHq2X9`\n\n"
        f"• *Workflow Modes:*\n"
        f"- *Interactive*: Asks you audio policy, subtitle style, AI tone, and social publishing targets via buttons.\n"
        f"- *Automatic*: Instantly runs using your default saved preferences.\n\n"
        f"• *Voice-over Dubbing:*\n"
        f"You can also send or forward an audio clip / voice note right after a video link to attach it as the English voiceover track!\n\n"
        f"• *Zero-Budget Cloud:*\n"
        f"This bot runs directly on your local Mac or zero-budget cloud server (Oracle Cloud Always Free).",
        parse_mode="Markdown",
    )

@require_auth
async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mode command."""
    user = update.effective_user
    db: Session = SessionLocal()
    try:
        pref = get_or_create_user_pref(db, str(user.id))
        mode = pref.workflow_mode
    finally:
        db.close()

    await update.message.reply_text(
        f"⚙️ *ReelPilot Workflow Mode*\n\n"
        f"Current mode: *{mode.capitalize()}*\n\n"
        f"Tap an option below to switch:",
        reply_markup=build_mode_keyboard(mode),
        parse_mode="Markdown",
    )

@require_auth
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command."""
    user = update.effective_user
    db: Session = SessionLocal()
    try:
        pref = get_or_create_user_pref(db, str(user.id))
        text = (
            f"⚙️ *Your ReelPilot Studio Preferences*\n\n"
            f"• *Mode:* `{pref.workflow_mode}`\n"
            f"• *Default Sync Policy:* `{pref.default_sync_policy}`\n"
            f"• *Mute Original Audio:* `{'Yes' if pref.default_mute_original else 'No'}`\n"
            f"• *Burn Subtitles:* `{'Yes' if pref.default_burn_subtitles else 'No'}`\n"
            f"• *Subtitle Font Size:* `{pref.default_subtitle_font_size}pt`\n"
            f"• *AI Tone:* `{pref.default_ai_tone}`\n"
            f"• *Publish Target:* `{pref.default_publish_target}`\n"
            f"• *Auto Publish:* `{'Enabled' if pref.auto_publish else 'Disabled'}`\n\n"
            f"To toggle mode, use `/mode`."
        )
    finally:
        db.close()

    await update.message.reply_text(text, parse_mode="Markdown")

@require_auth
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command: list active/running jobs."""
    user = update.effective_user
    db: Session = SessionLocal()
    try:
        active_jobs = (
            db.query(ProcessingJob)
            .filter(
                ProcessingJob.telegram_user_id == str(user.id),
                ProcessingJob.status.in_(["awaiting_input", "queued", "downloading", "transcribing", "burning_subtitles", "analyzing", "exporting", "publishing"]),
            )
            .order_by(desc(ProcessingJob.created_at))
            .all()
        )

        if not active_jobs:
            await update.message.reply_text("✅ No active jobs currently running. Send a video link to start!")
            return

        lines = ["📊 *Active ReelPilot Jobs:*\n"]
        for j in active_jobs:
            lines.append(
                f"• Job `{j.id[:8]}` — *{j.status}* ({int(j.progress)}%)\n"
                f"  Stage: {j.stage}\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    finally:
        db.close()

@require_auth
async def jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /jobs command: list last 5 jobs."""
    user = update.effective_user
    db: Session = SessionLocal()
    try:
        jobs = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.telegram_user_id == str(user.id))
            .order_by(desc(ProcessingJob.created_at))
            .limit(5)
            .all()
        )

        if not jobs:
            await update.message.reply_text("No recent jobs found.")
            return

        lines = ["📋 *Recent Jobs History:*\n"]
        for j in jobs:
            status_icon = "✅" if j.status == "completed" else "❌" if j.status == "failed" else "⏳"
            lines.append(
                f"{status_icon} Job `{j.id[:8]}`: *{j.status}*\n"
                f"   Created: {j.created_at.strftime('%Y-%m-%d %H:%M UTC') if j.created_at else 'N/A'}\n"
                f"   Stage: {j.stage}\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    finally:
        db.close()

@require_auth
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel latest active job or conversation."""
    user = update.effective_user
    db: Session = SessionLocal()
    try:
        active = (
            db.query(ProcessingJob)
            .filter(
                ProcessingJob.telegram_user_id == str(user.id),
                ProcessingJob.status.in_(["awaiting_input", "queued"]),
            )
            .order_by(desc(ProcessingJob.created_at))
            .first()
        )
        if not active:
            await update.message.reply_text("No pending or queued job to cancel.")
            return

        active.status = "cancelled"
        active.stage = "Cancelled by user"
        db.commit()
        await update.message.reply_text(f"❌ Cancelled Job `{active.id[:8]}`.")
    finally:
        db.close()

@require_auth
async def retry_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retry a failed job: /retry <job_id> or latest failed."""
    user = update.effective_user
    db: Session = SessionLocal()
    try:
        target_id = None
        if context.args:
            target_id = context.args[0].strip()

        q = db.query(ProcessingJob).filter(ProcessingJob.telegram_user_id == str(user.id))
        if target_id:
            job = q.filter(ProcessingJob.id.startswith(target_id)).first()
        else:
            job = q.filter(ProcessingJob.status == "failed").order_by(desc(ProcessingJob.created_at)).first()

        if not job:
            await update.message.reply_text("No failed job found to retry.")
            return

        job.status = "queued"
        job.error_message = None
        job.retry_count = (job.retry_count or 0) + 1
        db.commit()

        await update.message.reply_text(f"🔄 Retrying Job `{job.id[:8]}` in the background...")
        asyncio.create_task(execute_job_pipeline(job.id, context.bot))
    finally:
        db.close()

@require_auth
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect and process video URLs in user messages."""
    text = update.message.text or ""
    urls = URL_REGEX.findall(text)
    if urls:
        first_url = urls[0]
        await handle_video_url_submission(update, context, first_url)
    else:
        await update.message.reply_text(
            "Please send a supported Instagram Reel, Kuaishou, or Kwai link (e.g., `https://www.instagram.com/reel/...` or `https://v.kuaishou.com/...`) to start processing, or type `/help` for commands.",
            parse_mode="Markdown",
        )

@require_auth
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to conversation dispatcher."""
    await handle_callback_query(update, context)
