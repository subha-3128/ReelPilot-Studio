import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from telegram import Bot
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import (
    ProcessingJob,
    VideoAsset,
    VoiceoverAsset,
    MediaDerivative,
    Transcript,
    ContentDraft,
    Publication,
)
from app.services.downloader import DownloaderService
from app.services.media import media_service
from app.services.transcription import transcription_service
from app.services.metadata_ai import metadata_service
from app.services.publisher import social_service
from app.telegram.notifications import safe_edit_message, format_job_status_text
from app.telegram.keyboards import build_retry_keyboard

logger = logging.getLogger("studio.telegram.pipeline")

# Concurrency semaphore to prevent OOM/resource exhaustion on free-tier cloud instances
_pipeline_semaphore = asyncio.Semaphore(settings.REELPILOT_MAX_CONCURRENT_JOBS)
downloader_service = DownloaderService()

async def execute_job_pipeline(job_id: str, bot: Bot):
    """
    Asynchronous worker that drives the 6-step ReelPilot production workflow
    for a persistent ProcessingJob in the background.
    """
    async with _pipeline_semaphore:
        db: Session = SessionLocal()
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if not job or job.status in ("completed", "cancelled"):
                return

            chat_id = job.telegram_chat_id
            msg_id = job.telegram_message_id
            user_settings: Dict[str, Any] = job.collected_settings or {}

            # --- STEP 1: Download Source Video ---
            job.status = "downloading"
            job.stage = "Downloading high-resolution source stream"
            job.progress = 15.0
            db.commit()

            if chat_id and msg_id:
                await safe_edit_message(bot, chat_id, msg_id, format_job_status_text(job))

            # Run download (CPU/network bound in thread executor)
            loop = asyncio.get_running_loop()
            video_asset: Optional[VideoAsset] = await loop.run_in_executor(
                None, lambda: downloader_service.download_video(db, job.source_url)
            )

            if not video_asset:
                raise RuntimeError("Failed to download source video. Link may be private or unavailable.")

            job.asset_id = video_asset.id
            db.commit()

            # --- STEP 2: Audio & Voice-over Processing ---
            job.status = "transcribing"
            job.stage = "Transcribing audio and analyzing speech"
            job.progress = 35.0
            db.commit()

            if chat_id and msg_id:
                await safe_edit_message(bot, chat_id, msg_id, format_job_status_text(job))

            # Determine audio source & sync policy
            sync_policy = user_settings.get("sync_policy", "keep_original")
            mute_original = user_settings.get("mute_original", False)
            burn_subtitles = user_settings.get("burn_subtitles", False)
            font_size = user_settings.get("font_size", 24)
            ai_tone = user_settings.get("ai_tone", "engaging")
            publish_target = user_settings.get("publish_target", "none")

            current_video_path = Path(video_asset.original_local_path)
            synced_derivative_id = None

            # If user provided a voiceover file (attached to asset)
            if video_asset.voiceovers:
                vo = video_asset.voiceovers[-1]
                deriv_id = str(uuid.uuid4())
                out_path = settings.DERIVATIVES_DIR / f"{deriv_id}_synced.mp4"
                thumb_path = settings.THUMBNAILS_DIR / f"{deriv_id}.jpg"

                sync_res = await loop.run_in_executor(
                    None,
                    lambda: media_service.process_voiceover_sync(
                        source_video_path=current_video_path,
                        extracted_audio_path=Path(vo.extracted_audio_path),
                        output_derivative_path=out_path,
                        sync_policy=sync_policy,
                        mute_original_audio=mute_original,
                    ),
                )
                media_service.generate_thumbnail(out_path, thumb_path)

                deriv = MediaDerivative(
                    id=deriv_id,
                    video_asset_id=video_asset.id,
                    derivative_type="voiceover_synced",
                    local_path=str(out_path),
                    thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
                    duration=sync_res["duration"],
                    width=sync_res["width"],
                    height=sync_res["height"],
                    file_size=sync_res["file_size"],
                    settings={"sync_policy": sync_policy, "mute_original": mute_original},
                )
                db.add(deriv)
                db.commit()
                current_video_path = out_path
                synced_derivative_id = deriv_id

            # --- STEP 3: Subtitles Transcription & Optional Burn ---
            trans = db.query(Transcript).filter(Transcript.video_asset_id == video_asset.id).first()
            if not trans:
                # Transcribe from current audio
                audio_to_transcribe = current_video_path
                if video_asset.voiceovers:
                    audio_to_transcribe = Path(video_asset.voiceovers[-1].extracted_audio_path)

                segments = await loop.run_in_executor(
                    None,
                    lambda: transcription_service.transcribe_audio(audio_to_transcribe, language="en"),
                )
                full_text = " ".join(
                    s.get("text", "") for s in segments 
                    if not s.get("text", "").startswith("[Cue") and "commentary segment" not in s.get("text", "").lower()
                ).strip()
                trans = Transcript(
                    id=str(uuid.uuid4()),
                    video_asset_id=video_asset.id,
                    derivative_id=synced_derivative_id,
                    provider="local_speech",
                    source_lang="en",
                    target_lang="en",
                    full_text=full_text,
                    segments=segments,
                )
                db.add(trans)
                db.commit()

            if burn_subtitles and trans and trans.segments:
                job.status = "burning_subtitles"
                job.stage = "Burning styled subtitles into video"
                job.progress = 55.0
                db.commit()

                if chat_id and msg_id:
                    await safe_edit_message(bot, chat_id, msg_id, format_job_status_text(job))

                sub_id = str(uuid.uuid4())
                srt_path = settings.TEMP_DIR / f"{sub_id}.srt"
                transcription_service.write_srt_file(trans.segments, srt_path)

                captioned_path = settings.DERIVATIVES_DIR / f"{sub_id}_captioned.mp4"
                thumb_path = settings.THUMBNAILS_DIR / f"{sub_id}.jpg"

                await loop.run_in_executor(
                    None,
                    lambda: media_service.burn_subtitles(
                        video_path=current_video_path,
                        srt_path=srt_path,
                        output_path=captioned_path,
                        font_size=font_size,
                        font_color="&H00FFFFFF",
                        outline_color="&H00000000",
                        outline_width=2,
                    ),
                )
                media_service.generate_thumbnail(captioned_path, thumb_path)

                meta = media_service.probe(captioned_path)
                captioned_deriv = MediaDerivative(
                    id=sub_id,
                    video_asset_id=video_asset.id,
                    derivative_type="captioned",
                    local_path=str(captioned_path),
                    thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
                    duration=meta.get("duration", 0.0),
                    width=meta.get("width", 720),
                    height=meta.get("height", 1280),
                    file_size=captioned_path.stat().st_size,
                    settings={"font_size": font_size, "burned": True},
                )
                db.add(captioned_deriv)
                db.commit()
                current_video_path = captioned_path

            # --- STEP 4: AI Metadata Generation ---
            job.status = "analyzing"
            job.stage = "Synthesizing AI headlines and metadata via Gemini"
            job.progress = 75.0
            db.commit()

            if chat_id and msg_id:
                await safe_edit_message(bot, chat_id, msg_id, format_job_status_text(job))

            transcript_text = trans.full_text if trans else ""
            ai_drafts = await loop.run_in_executor(
                None,
                lambda: metadata_service.generate_drafts(
                    filename=video_asset.filename,
                    transcript_text=transcript_text,
                    tone=ai_tone,
                    include_hashtags=True,
                ),
            )

            # Persist drafts
            for plat in ("instagram", "youtube"):
                if plat in ai_drafts:
                    data = ai_drafts[plat]
                    d_record = ContentDraft(
                        id=str(uuid.uuid4()),
                        video_asset_id=video_asset.id,
                        platform=plat,
                        title=data.get("title", ""),
                        caption=data.get("caption", ""),
                        description=data.get("description", ""),
                        hashtags=data.get("hashtags", ""),
                        generation_source="ai_suggested",
                    )
                    db.add(d_record)
            db.commit()

            # --- STEP 5: Export Final Derivative ---
            job.status = "exporting"
            job.stage = "Rendering production 9:16 export derivative"
            job.progress = 90.0
            db.commit()

            if chat_id and msg_id:
                await safe_edit_message(bot, chat_id, msg_id, format_job_status_text(job))

            final_id = str(uuid.uuid4())
            export_filename = f"export_{final_id[:8]}_{video_asset.filename}"
            export_path = settings.DERIVATIVES_DIR / export_filename
            thumb_path = settings.THUMBNAILS_DIR / f"{final_id}.jpg"

            import shutil
            await loop.run_in_executor(
                None,
                lambda: shutil.copy2(current_video_path, export_path),
            )
            media_service.generate_thumbnail(export_path, thumb_path)

            meta = media_service.probe(export_path)
            final_deriv = MediaDerivative(
                id=final_id,
                video_asset_id=video_asset.id,
                derivative_type="final_export",
                local_path=str(export_path),
                thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
                duration=meta.get("duration", 0.0),
                width=meta.get("width", 720),
                height=meta.get("height", 1280),
                file_size=export_path.stat().st_size,
            )
            db.add(final_deriv)
            job.output_derivative_id = final_id
            db.commit()

            # --- STEP 6: Social Media Publishing (If selected) ---
            published_urls = []
            if publish_target in ("instagram", "youtube", "both"):
                job.status = "publishing"
                job.stage = f"Publishing to {publish_target.title()}"
                job.progress = 95.0
                db.commit()

                if chat_id and msg_id:
                    await safe_edit_message(bot, chat_id, msg_id, format_job_status_text(job))

                targets = ["instagram", "youtube"] if publish_target == "both" else [publish_target]
                for p_target in targets:
                    idempotency_key = f"{video_asset.id}_{p_target}_{int(datetime.now(timezone.utc).timestamp())}"
                    pub = Publication(
                        id=str(uuid.uuid4()),
                        video_asset_id=video_asset.id,
                        derivative_id=final_id,
                        platform=p_target,
                        status="publishing",
                        idempotency_key=idempotency_key,
                    )
                    db.add(pub)
                    db.commit()
                    db.refresh(pub)

                    # Execute publishing
                    await loop.run_in_executor(
                        None,
                        lambda: social_service.execute_publication(db, pub.id),
                    )
                    db.refresh(pub)
                    if pub.remote_post_url:
                        published_urls.append(f"{p_target.capitalize()}: {pub.remote_post_url}")
                    else:
                        reason = pub.error_details or "Credentials not configured in environment"
                        published_urls.append(f"{p_target.capitalize()}: ⚠️ {reason}")

            # --- STEP 7: Completion & Telegram Delivery ---
            job.status = "completed"
            job.stage = "Production completed and delivered"
            job.progress = 100.0
            job.published_platforms = published_urls
            db.commit()

            # Prepare Telegram Caption
            ig_draft = ai_drafts.get("instagram", {})
            yt_draft = ai_drafts.get("youtube", {})

            clean_fallback_title = metadata_service.clean_title(video_asset.filename)
            raw_title = (
                ig_draft.get("title")
                or yt_draft.get("title")
                or clean_fallback_title
            )
            title = raw_title.replace("#Shorts", "").replace("#shorts", "").strip(" -|")

            caption = (ig_draft.get("caption") or yt_draft.get("description", "")).strip()
            hashtags = (ig_draft.get("hashtags") or yt_draft.get("hashtags", "")).strip()

            caption_text = (
                f"🎬 *ReelPilot Studio — Production Complete*\n\n"
                f"📌 *Title:* {title}\n\n"
                f"📝 *Caption:*\n{caption}\n\n"
                f"🏷️ {hashtags}\n"
            )
            if published_urls:
                caption_text += "\n🚀 *Distribution Status:*\n" + "\n".join(published_urls)

            # Keep message strictly under Telegram 1024-char limit
            if len(caption_text) > 1000:
                caption_text = caption_text[:990] + "..."

            file_size_mb = export_path.stat().st_size / (1024 * 1024)

            # Telegram Bot API allows up to 50MB for send_video
            if chat_id:
                if file_size_mb <= 50.0:
                    try:
                        with open(export_path, "rb") as video_file:
                            await bot.send_video(
                                chat_id=chat_id,
                                video=video_file,
                                caption=caption_text,
                                parse_mode="Markdown",
                                supports_streaming=True,
                            )
                    except Exception as delivery_err:
                        logger.error("Failed to stream video to Telegram: %s", delivery_err)
                        await bot.send_message(
                            chat_id=chat_id,
                            text=(
                                f"✅ *ReelPilot Studio — Media Generated*\n\n"
                                f"File rendered ({file_size_mb:.1f} MB), but Telegram stream encountered an error:\n"
                                f"{delivery_err}\n\n"
                                f"Local file saved at: `{export_path.name}`"
                            ),
                            parse_mode="Markdown",
                        )
                else:
                    # File exceeds Telegram Bot 50MB limit
                    await bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"✅ *ReelPilot Studio — Video Generated*\n\n"
                            f"File size is *{file_size_mb:.1f} MB* (exceeds Telegram Bot API 50MB direct delivery limit).\n"
                            f"Video stored at: `{export_path.name}`\n\n"
                            f"{caption_text}"
                        ),
                        parse_mode="Markdown",
                    )

                if msg_id:
                    await safe_edit_message(
                        bot,
                        chat_id,
                        msg_id,
                        f"✅ *ReelPilot Studio — Job Completed*\n\n"
                        f"• Job ID: `{job.id[:8]}`\n"
                        f"• Media Asset: `{export_path.name}` ({file_size_mb:.1f} MB)\n"
                        f"• Status: Delivered to chat.",
                        parse_mode="Markdown",
                    )

        except Exception as e:
            logger.exception("Error executing ReelPilot processing job %s: %s", job_id, e)
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                db.commit()

                if job.telegram_chat_id and job.telegram_message_id:
                    await safe_edit_message(
                        bot,
                        job.telegram_chat_id,
                        job.telegram_message_id,
                        f"⚠️ *ReelPilot Studio — Pipeline Exception*\n\n"
                        f"• Job ID: `{job.id[:8]}`\n"
                        f"• Stage: {job.stage}\n"
                        f"• Details: {e}\n\n"
                        f"Select below to retry this workflow:",
                        reply_markup=build_retry_keyboard(job.id),
                        parse_mode="Markdown",
                    )
        finally:
            db.close()
