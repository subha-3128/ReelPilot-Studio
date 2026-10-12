import asyncio
import logging
from typing import Optional
from telegram import Update, Bot
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import ProcessingJob, TelegramUserPreference
from app.core.security import validate_and_normalize_url
from app.telegram.keyboards import (
    build_audio_policy_keyboard,
    build_subtitles_keyboard,
    build_tone_keyboard,
    build_publish_keyboard,
    build_confirm_keyboard,
    build_mode_keyboard,
)
from app.telegram.notifications import safe_edit_message
from app.telegram.pipeline import execute_job_pipeline

logger = logging.getLogger("studio.telegram.conversations")

def get_or_create_user_pref(db: Session, user_id: str) -> TelegramUserPreference:
    """Retrieve saved preferences or initialize with default ReelPilot studio settings."""
    pref = db.query(TelegramUserPreference).filter(TelegramUserPreference.telegram_user_id == user_id).first()
    if not pref:
        pref = TelegramUserPreference(
            telegram_user_id=user_id,
            workflow_mode="interactive",
            default_sync_policy="keep_original",
            default_mute_original=False,
            default_burn_subtitles=False,
            default_subtitle_font_size=24,
            default_ai_tone="engaging",
            default_publish_target="none",
            auto_publish=False,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref

async def handle_video_url_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Called when an authorized user submits a video link to the bot."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    # Validate URL against allowlist & SSRF guards
    try:
        normalized_url = validate_and_normalize_url(url)
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ *Invalid or Unsupported Video URL*\n\n"
            f"{e}\n\n"
            f"Please provide an authorized Instagram Reel, Kuaishou, or Kwai link:\n"
            f"• `https://www.instagram.com/reel/Cxxxxxx/`\n"
            f"• `https://v.kuaishou.com/xxxxxx`\n"
            f"• `https://kwai.com/xxxxxx`",
            parse_mode="Markdown",
        )
        return

    db: Session = SessionLocal()
    try:
        pref = get_or_create_user_pref(db, str(user.id))
        workflow_mode = pref.workflow_mode

        # Default settings: Always preserve original audio, no subtitle burn
        initial_settings = {
            "sync_policy": "keep_original",
            "mute_original": False,
            "burn_subtitles": False,
            "font_size": 24,
        }

        # Create persistent job in database
        job = ProcessingJob(
            job_type="full_pipeline",
            status="awaiting_input" if workflow_mode == "interactive" else "queued",
            progress=0.0,
            stage="Job initialized via Telegram",
            telegram_chat_id=str(chat.id),
            telegram_user_id=str(user.id),
            workflow_mode=workflow_mode,
            source_url=normalized_url,
            collected_settings=initial_settings,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if workflow_mode == "automatic":
            # Apply saved user preferences directly
            job.collected_settings = {
                "sync_policy": "keep_original",
                "mute_original": False,
                "burn_subtitles": False,
                "font_size": 24,
                "ai_tone": pref.default_ai_tone or "engaging",
                "publish_target": pref.default_publish_target or "none",
            }
            job.status = "queued"
            db.commit()

            target_label = {
                "none": "Direct Delivery Only",
                "instagram": "Instagram Reels",
                "youtube": "YouTube Shorts",
                "both": "Instagram Reels + YouTube Shorts",
            }.get(pref.default_publish_target, pref.default_publish_target or "Direct Delivery Only")

            status_msg = await update.message.reply_text(
                f"🎬 *ReelPilot Studio — Production Initiated*\n\n"
                f"• *Job ID:* `{job.id[:8]}`\n"
                f"• *Mode:* Automatic\n"
                f"• *Audio Policy:* Original Audio Preserved\n"
                f"• *Subtitles:* Unburned\n"
                f"• *AI Tone:* {str(pref.default_ai_tone or 'engaging').capitalize()}\n"
                f"• *Target Channel:* {target_label}\n\n"
                f"⏳ Initializing background processing pipeline...",
                parse_mode="Markdown",
            )
            job.telegram_message_id = status_msg.message_id
            db.commit()

            # Launch background worker task
            asyncio.create_task(execute_job_pipeline(job.id, context.bot))

        else:
            # Interactive Mode: Start directly with Tone (Step 1 of 2)
            msg = await update.message.reply_text(
                f"🎬 *ReelPilot Studio — New Video Job*\n\n"
                f"• *Job ID:* `{job.id[:8]}`\n"
                f"• *Audio Policy:* Original Audio Preserved\n"
                f"• *Subtitles:* None (Clean Video)\n\n"
                f"*Step 1 of 2:* Select AI Metadata & Caption Tone:",
                reply_markup=build_tone_keyboard(job.id),
                parse_mode="Markdown",
            )
            job.telegram_message_id = msg.message_id
            db.commit()

    finally:
        db.close()

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button presses from inline keyboards."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    data = query.data
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    db: Session = SessionLocal()
    try:
        # 1. Mode selection: set:mode:<interactive|automatic>
        if data.startswith("set:mode:"):
            new_mode = data.split(":")[2]
            pref = get_or_create_user_pref(db, str(user.id))
            pref.workflow_mode = new_mode
            db.commit()
            await query.edit_message_text(
                f"⚙️ *Workflow Mode Updated*\n\n"
                f"Active Mode: *{new_mode.capitalize()}*\n\n"
                f"• *Interactive:* Prompts for metadata tone and distribution channel for each video.\n"
                f"• *Automatic:* Processes incoming videos immediately using default studio preferences.",
                reply_markup=build_mode_keyboard(new_mode),
                parse_mode="Markdown",
            )
            return

        # 2. Interactive Questions: q:<step>:<job_id>:<value>
        parts = data.split(":")
        if len(parts) >= 4 and parts[0] == "q":
            step = parts[1]
            job_id = parts[2]
            value = parts[3]

            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if not job:
                await query.edit_message_text("⚠️ Job not found or expired from record.")
                return

            settings_dict = dict(job.collected_settings or {})

            # Step 1 (Legacy / Direct): Audio Policy
            if step == "audio":
                if value == "keep_original":
                    settings_dict["sync_policy"] = "keep_original"
                    settings_dict["mute_original"] = False
                else:
                    settings_dict["sync_policy"] = value
                    settings_dict["mute_original"] = True

                job.collected_settings = settings_dict
                db.commit()

                await query.edit_message_text(
                    f"🎬 *ReelPilot Studio — Job `{job.id[:8]}`*\n\n"
                    f"• *Audio Policy:* {value}\n\n"
                    f"Select AI Metadata & Caption Tone:",
                    reply_markup=build_tone_keyboard(job.id),
                    parse_mode="Markdown",
                )
                return

            # Step 2 (Legacy / Direct): Subtitle Burn
            if step == "sub":
                settings_dict["burn_subtitles"] = (value == "burn_yes")
                settings_dict["font_size"] = 24
                job.collected_settings = settings_dict
                db.commit()

                await query.edit_message_text(
                    f"🎬 *ReelPilot Studio — Job `{job.id[:8]}`*\n\n"
                    f"• *Subtitles:* {'Burned' if value == 'burn_yes' else 'Unburned'}\n\n"
                    f"Select AI Metadata & Caption Tone:",
                    reply_markup=build_tone_keyboard(job.id),
                    parse_mode="Markdown",
                )
                return

            # Step 1 of 2: AI Tone
            if step == "tone":
                settings_dict["ai_tone"] = value
                settings_dict["sync_policy"] = "keep_original"
                settings_dict["mute_original"] = False
                settings_dict["burn_subtitles"] = False
                settings_dict["font_size"] = 24
                job.collected_settings = settings_dict
                db.commit()

                await query.edit_message_text(
                    f"🎬 *ReelPilot Studio — Job `{job.id[:8]}`*\n\n"
                    f"• *Selected Tone:* {value.capitalize()}\n\n"
                    f"*Step 2 of 2:* Select Target Distribution Channel:",
                    reply_markup=build_publish_keyboard(job.id),
                    parse_mode="Markdown",
                )
                return

            # Step 2 of 2: Publish Target -> Immediately Launch Production
            if step == "pub":
                settings_dict["publish_target"] = value
                settings_dict["sync_policy"] = "keep_original"
                settings_dict["mute_original"] = False
                settings_dict["burn_subtitles"] = False
                settings_dict["font_size"] = 24

                job.collected_settings = settings_dict
                job.status = "queued"
                job.stage = "Queued for pipeline execution"
                job.progress = 5.0
                db.commit()

                pub_label = {
                    "none": "Direct Delivery Only",
                    "instagram": "Instagram Reels",
                    "youtube": "YouTube Shorts",
                    "both": "Instagram Reels & YouTube Shorts",
                }.get(value, value)

                tone_clean = str(settings_dict.get("ai_tone", "engaging")).capitalize()

                status_text = (
                    f"🚀 *ReelPilot Studio — Production Launched*\n\n"
                    f"• *Job ID:* `{job.id[:8]}`\n"
                    f"• *Audio:* Original Audio Preserved\n"
                    f"• *Subtitles:* Unburned\n"
                    f"• *AI Tone:* {tone_clean}\n"
                    f"• *Destination:* {pub_label}\n\n"
                    f"⏳ Ingesting source media, synthesizing AI captions, and rendering video in the background..."
                )

                try:
                    await query.edit_message_text(status_text, parse_mode="Markdown")
                except Exception:
                    plain_text = status_text.replace("*", "").replace("`", "")
                    await query.edit_message_text(plain_text)

                asyncio.create_task(execute_job_pipeline(job.id, context.bot))
                return

            # Step 5: Final Confirmation / Cancel (for backwards compatibility)
            if step == "confirm":
                if value == "start":
                    if job.status == "awaiting_input":
                        job.status = "queued"
                        job.stage = "Queued for pipeline execution"
                        job.progress = 5.0
                        db.commit()

                        await query.edit_message_text(
                            f"🚀 *ReelPilot Studio — Job `{job.id[:8]}` Queued*\n\n"
                            f"Pipeline execution initiated in background. Real-time updates and output will be delivered here.",
                            parse_mode="Markdown",
                        )
                        asyncio.create_task(execute_job_pipeline(job.id, context.bot))
                else:
                    job.status = "cancelled"
                    job.stage = "Cancelled by user"
                    db.commit()
                    await query.edit_message_text(
                        f"🛑 *ReelPilot Studio — Job Cancelled*\n\n"
                        f"Job `{job.id[:8]}` has been cancelled.",
                        parse_mode="Markdown",
                    )
                return

            # Retry handler
            if step == "retry":
                job.status = "queued"
                job.error_message = None
                job.retry_count = (job.retry_count or 0) + 1
                db.commit()

                await query.edit_message_text(
                    f"🔄 *ReelPilot Studio — Retrying Job `{job.id[:8]}`*\n\n"
                    f"Attempt {job.retry_count} queued for background execution.",
                    parse_mode="Markdown",
                )
                asyncio.create_task(execute_job_pipeline(job.id, context.bot))
                return

    finally:
        db.close()
