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
        f"🎬 *ReelPilot Studio — Production Engine*\n\n"
        f"ReelPilot streamlines video ingestion, AI caption synthesis, and social distribution.\n\n"
        f"• *Current Mode:* {mode.capitalize()}\n"
        f"• *Telegram User ID:* `{user.id}`\n\n"
        f"*Quick Workflow:*\n"
        f"1. Submit any authorized Instagram Reel, Kuaishou, or Kwai link.\n"
        f"2. Select AI metadata tone and target distribution platform.\n"
        f"3. Receive the completed video with preserved original audio directly in chat.\n\n"
        f"*Available Commands:*\n"
        f"• `/mode` — Switch between Interactive and Automatic operation\n"
        f"• `/settings` — Inspect default production parameters\n"
        f"• `/status` — View active processing pipelines\n"
        f"• `/jobs` — View recent production logs\n"
        f"• `/cancel` — Cancel a pending or queued job\n"
        f"• `/retry` — Rerun a failed job\n"
        f"• `/help` — Documentation and input specifications",
        parse_mode="Markdown",
    )

@require_auth
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        f"📖 *ReelPilot Studio — Operations Manual*\n\n"
        f"*Supported Ingestion Formats:*\n"
        f"Submit standard video links from:\n"
        f"• Instagram Reels: `https://www.instagram.com/reel/Cxxxxxx/`\n"
        f"• Kuaishou: `https://v.kuaishou.com/xxxxxx`\n"
        f"• Kwai: `https://kwai.com/xxxxxx`\n\n"
        f"*Production Policies:*\n"
        f"• *Audio Policy:* Preserves original audio at original mix and fidelity.\n"
        f"• *Subtitles:* Clean derivative format (no subtitle burn-in).\n"
        f"• *AI Synthesis:* Gemini-powered headlines, captions, and hashtags.\n\n"
        f"*Operating Modes:*\n"
        f"• *Interactive:* Quick 2-step prompt (Metadata Tone & Distribution Channel).\n"
        f"• *Automatic:* Direct pipeline execution using saved studio preferences.\n\n"
        f"*Custom Audio Track (Optional):*\n"
        f"Send or forward an audio file or voice note immediately following a video link to attach it as an alternative voiceover track.",
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
        f"⚙️ *ReelPilot Studio — Workflow Configuration*\n\n"
        f"Current Mode: *{mode.capitalize()}*\n\n"
        f"Select an operational mode below:",
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
            f"⚙️ *ReelPilot Studio — Default Parameters*\n\n"
            f"• *Workflow Mode:* `{pref.workflow_mode.capitalize()}`\n"
            f"• *Audio Policy:* `Original Audio Preserved`\n"
            f"• *Subtitle Burn:* `Disabled (Clean Video)`\n"
            f"• *AI Metadata Tone:* `{str(pref.default_ai_tone or 'engaging').capitalize()}`\n"
            f"• *Distribution Target:* `{str(pref.default_publish_target or 'none').capitalize()}`\n"
            f"• *Automated Publishing:* `{'Enabled' if pref.auto_publish else 'Disabled'}`\n\n"
            f"Use `/mode` to switch between Interactive and Automatic workflow."
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
            await update.message.reply_text("✅ No active jobs currently running. Submit a video link to begin.")
            return

        lines = ["📊 *ReelPilot Studio — Active Operations:*\n"]
        for j in active_jobs:
            lines.append(
                f"• Job `{j.id[:8]}` — *{j.status.capitalize()}* ({int(j.progress)}%)\n"
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
            await update.message.reply_text("No recent production jobs found.")
            return

        lines = ["📋 *ReelPilot Studio — Recent Production History:*\n"]
        for j in jobs:
            status_icon = "✅" if j.status == "completed" else "❌" if j.status == "failed" else "⏳"
            lines.append(
                f"{status_icon} Job `{j.id[:8]}` — *{j.status.capitalize()}*\n"
                f"   Timestamp: {j.created_at.strftime('%Y-%m-%d %H:%M UTC') if j.created_at else 'N/A'}\n"
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
            await update.message.reply_text("No active or queued jobs available to cancel.")
            return

        active.status = "cancelled"
        active.stage = "Cancelled by user"
        db.commit()
        await update.message.reply_text(f"🛑 Cancelled Job `{active.id[:8]}`.")
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
            await update.message.reply_text("No failed jobs found to retry.")
            return

        job.status = "queued"
        job.error_message = None
        job.retry_count = (job.retry_count or 0) + 1
        db.commit()

        await update.message.reply_text(f"🔄 Re-initiating Job `{job.id[:8]}` (Attempt {job.retry_count})...")
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
            "Please provide a valid Instagram Reel, Kuaishou, or Kwai URL (e.g., `https://www.instagram.com/reel/...`) to initialize production, or type `/help` for commands.",
            parse_mode="Markdown",
        )

@require_auth
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to conversation dispatcher."""
    await handle_callback_query(update, context)
