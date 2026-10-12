import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from telegram import Update, User, Chat, Message, CallbackQuery

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import ProcessingJob, TelegramUserPreference, VideoAsset, MediaDerivative
from app.telegram.security import is_user_authorized, require_auth
from app.telegram.conversations import (
    get_or_create_user_pref,
    handle_video_url_submission,
    handle_callback_query,
)
from app.telegram.pipeline import execute_job_pipeline
from app.telegram.bot import telegram_bot_manager

def test_telegram_config_validation(monkeypatch):
    """Test parsing and validation of allowed Telegram user IDs and bot token settings."""
    monkeypatch.setattr(settings, "TELEGRAM_ALLOWED_USER_IDS", "12345, 67890, invalid_id")
    ids = settings.get_allowed_telegram_user_ids()
    assert ids == {12345, 67890}

    monkeypatch.setattr(settings, "TELEGRAM_ALLOWED_USER_IDS", "")
    assert settings.get_allowed_telegram_user_ids() == set()

    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setattr(settings, "TELEGRAM_MODE", "polling")
    assert telegram_bot_manager.is_configured() is True

    monkeypatch.setattr(settings, "TELEGRAM_MODE", "disabled")
    assert telegram_bot_manager.is_configured() is False

def test_telegram_user_authorization(monkeypatch):
    """Ensure authorized users pass while unauthorized users are blocked."""
    monkeypatch.setattr(settings, "TELEGRAM_ALLOWED_USER_IDS", "999888")
    assert is_user_authorized(999888) is True
    assert is_user_authorized(111222) is False

    # Test @require_auth decorator on mock handler
    called = False

    @require_auth
    async def sample_handler(update, context):
        nonlocal called
        called = True

    mock_unauth_user = MagicMock()
    mock_unauth_user.id = 111222
    mock_unauth_user.username = "intruder"

    mock_msg = AsyncMock()
    mock_update = MagicMock()
    mock_update.effective_user = mock_unauth_user
    mock_update.message = mock_msg
    mock_update.callback_query = None

    asyncio.run(sample_handler(mock_update, MagicMock()))
    assert called is False
    assert mock_msg.reply_text.called
    assert "Unauthorized" in mock_msg.reply_text.call_args[0][0]

def test_telegram_user_preferences_crud():
    """Verify storing, retrieving, and updating user preferences in database."""
    db = SessionLocal()
    try:
        user_id = str(uuid.uuid4())[:12]
        pref = get_or_create_user_pref(db, user_id)
        assert pref.workflow_mode == "interactive"
        assert pref.default_sync_policy == "keep_original"
        assert pref.default_burn_subtitles is False
        assert pref.default_mute_original is False

        pref.workflow_mode = "automatic"
        pref.default_publish_target = "both"
        db.commit()

        # Re-fetch
        fetched = get_or_create_user_pref(db, user_id)
        assert fetched.workflow_mode == "automatic"
        assert fetched.default_publish_target == "both"
    finally:
        db.close()

@pytest.mark.asyncio
async def test_video_url_submission_interactive():
    """Submitting a valid video link in interactive mode should create job with original audio and no burn, prompting Step 1 of 2."""
    db = SessionLocal()
    try:
        user_id = 555111
        chat_id = 999111

        mock_user = MagicMock(spec=User)
        mock_user.id = user_id

        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = chat_id

        mock_msg = AsyncMock(spec=Message)
        mock_msg.message_id = 42

        mock_reply = AsyncMock()
        mock_reply.message_id = 101
        mock_msg.reply_text.return_value = mock_reply

        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = mock_user
        mock_update.effective_chat = mock_chat
        mock_update.message = mock_msg

        # Set user pref to interactive
        pref = get_or_create_user_pref(db, str(user_id))
        pref.workflow_mode = "interactive"
        db.commit()

        valid_url = "https://v.kuaishou.com/KXUHq2X9"
        await handle_video_url_submission(mock_update, MagicMock(), valid_url)

        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.telegram_user_id == str(user_id))
            .order_by(ProcessingJob.created_at.desc())
            .first()
        )
        assert job is not None
        assert job.status == "awaiting_input"
        assert job.source_url == valid_url
        assert job.collected_settings.get("sync_policy") == "keep_original"
        assert job.collected_settings.get("burn_subtitles") is False
        assert mock_msg.reply_text.called
        assert "Step 1 of 2" in mock_msg.reply_text.call_args[0][0]
    finally:
        db.close()

@pytest.mark.asyncio
async def test_video_url_submission_invalid_url():
    """Submitting an invalid or private URL should be rejected without job creation."""
    db = SessionLocal()
    try:
        mock_user = MagicMock(spec=User)
        mock_user.id = 777111

        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = 777222

        mock_msg = AsyncMock(spec=Message)
        mock_update = MagicMock(spec=Update)
        mock_update.effective_user = mock_user
        mock_update.effective_chat = mock_chat
        mock_update.message = mock_msg

        invalid_url = "http://127.0.0.1/malicious.mp4"
        await handle_video_url_submission(mock_update, MagicMock(), invalid_url)

        job = db.query(ProcessingJob).filter(ProcessingJob.source_url == invalid_url).first()
        assert job is None
        assert mock_msg.reply_text.called
        assert "Invalid or Unsupported" in mock_msg.reply_text.call_args[0][0]
    finally:
        db.close()

@pytest.mark.asyncio
async def test_telegram_question_callback_flow():
    """Verify complete streamlined 2-step interactive question and callback progression."""
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        job = ProcessingJob(
            id=job_id,
            job_type="full_pipeline",
            status="awaiting_input",
            telegram_chat_id="123",
            telegram_user_id="456",
            source_url="https://v.kuaishou.com/test",
            collected_settings={
                "sync_policy": "keep_original",
                "mute_original": False,
                "burn_subtitles": False,
                "font_size": 24,
            },
        )
        db.add(job)
        db.commit()

        mock_query = AsyncMock(spec=CallbackQuery)
        mock_update = MagicMock(spec=Update)
        mock_update.callback_query = mock_query
        mock_update.effective_user = MagicMock(id=456)
        mock_update.effective_chat = MagicMock(id=123)

        # Step 1 of 2: Answer Tone
        mock_query.data = f"q:tone:{job_id}:engaging"
        await handle_callback_query(mock_update, MagicMock())
        db.refresh(job)
        assert job.collected_settings.get("ai_tone") == "engaging"
        assert job.collected_settings.get("sync_policy") == "keep_original"
        assert job.collected_settings.get("burn_subtitles") is False

        # Step 2 of 2: Answer Publish Target -> Immediately Queues & Launches
        with patch("app.telegram.conversations.execute_job_pipeline", new_callable=AsyncMock) as mock_pipe:
            mock_query.data = f"q:pub:{job_id}:instagram"
            await handle_callback_query(mock_update, MagicMock())
            db.refresh(job)
            assert job.collected_settings.get("publish_target") == "instagram"
            assert job.status == "queued"
    finally:
        db.close()

@pytest.mark.asyncio
async def test_telegram_job_cancellation():
    """Verify that user can cancel a pending job."""
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        job = ProcessingJob(
            id=job_id,
            job_type="full_pipeline",
            status="awaiting_input",
            telegram_chat_id="123",
            telegram_user_id="456",
        )
        db.add(job)
        db.commit()

        mock_query = AsyncMock(spec=CallbackQuery)
        mock_update = MagicMock(spec=Update)
        mock_update.callback_query = mock_query
        mock_update.effective_user = MagicMock(id=456)
        mock_update.effective_chat = MagicMock(id=123)
        mock_query.data = f"q:confirm:{job_id}:cancel"

        await handle_callback_query(mock_update, MagicMock())
        db.refresh(job)
        assert job.status == "cancelled"
    finally:
        db.close()

@pytest.mark.asyncio
async def test_telegram_pipeline_execution():
    """Test full background pipeline execution with mocked external services."""
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        job = ProcessingJob(
            id=job_id,
            job_type="full_pipeline",
            status="queued",
            telegram_chat_id="1001",
            telegram_message_id=2001,
            source_url="https://v.kuaishou.com/test",
            collected_settings={
                "sync_policy": "keep_natural_speed",
                "mute_original": True,
                "burn_subtitles": False,
                "ai_tone": "engaging",
                "publish_target": "none",
            },
        )
        db.add(job)
        db.commit()

        # Mock mock video asset & output derivative
        dummy_source = settings.ORIGINALS_DIR / "dummy_test.mp4"
        dummy_source.write_bytes(b"dummy_video_stream_binary")

        mock_asset = VideoAsset(
            id=str(uuid.uuid4()),
            original_source_url="https://v.kuaishou.com/test",
            original_local_path=str(dummy_source),
            filename="dummy_test.mp4",
        )
        db.add(mock_asset)
        db.commit()

        mock_bot = AsyncMock()
        mock_bot.edit_message_text = AsyncMock()
        mock_bot.send_video = AsyncMock()
        mock_bot.send_message = AsyncMock()

        with patch("app.telegram.pipeline.downloader_service.download_video", return_value=mock_asset), \
             patch("app.telegram.pipeline.media_service.generate_thumbnail", return_value=True), \
             patch("app.telegram.pipeline.media_service.probe", return_value={"duration": 15.0, "width": 720, "height": 1280}):

            await execute_job_pipeline(job_id, mock_bot)

            db.refresh(job)
            assert job.status == "completed"
            assert job.progress == 100.0
            assert mock_bot.send_video.called

        dummy_source.unlink(missing_ok=True)
    finally:
        db.close()

def test_telegram_startup_recovery():
    """Verify recovery marks interrupted in-flight jobs as failed on restart."""
    db = SessionLocal()
    try:
        interrupted_job = ProcessingJob(
            id=str(uuid.uuid4()),
            job_type="full_pipeline",
            status="exporting",
            stage="Rendering derivative",
        )
        db.add(interrupted_job)
        db.commit()

        telegram_bot_manager._recover_interrupted_jobs()

        db.refresh(interrupted_job)
        assert interrupted_job.status == "failed"
        assert "Server restarted" in interrupted_job.error_message
    finally:
        db.close()
