import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class VideoAsset(Base):
    __tablename__ = "video_assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    original_source_url = Column(String(1024), nullable=False)
    source_platform = Column(String(64), default="kuaishou")
    original_local_path = Column(String(1024), nullable=False)
    filename = Column(String(256), nullable=False)
    thumbnail_path = Column(String(1024), nullable=True)

    duration = Column(Float, default=0.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    aspect_ratio = Column(String(32), default="9:16")
    file_size = Column(Integer, default=0)
    checksum = Column(String(64), nullable=True, index=True)
    has_audio = Column(Boolean, default=True)

    rights_notes = Column(Text, default="User confirmed usage rights")
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    derivatives = relationship("MediaDerivative", back_populates="video_asset", cascade="all, delete-orphan")
    voiceovers = relationship("VoiceoverAsset", back_populates="video_asset", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="video_asset", cascade="all, delete-orphan")
    drafts = relationship("ContentDraft", back_populates="video_asset", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="video_asset", cascade="all, delete-orphan")


class VoiceoverAsset(Base):
    __tablename__ = "voiceover_assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_asset_id = Column(String(36), ForeignKey("video_assets.id"), nullable=False)
    source_upload_path = Column(String(1024), nullable=False)
    extracted_audio_path = Column(String(1024), nullable=False)
    filename = Column(String(256), nullable=False)
    duration = Column(Float, default=0.0)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

    video_asset = relationship("VideoAsset", back_populates="voiceovers")


class MediaDerivative(Base):
    __tablename__ = "media_derivatives"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_asset_id = Column(String(36), ForeignKey("video_assets.id"), nullable=False)
    derivative_type = Column(String(64), nullable=False)  # voiceover_synced, captioned, final_export
    local_path = Column(String(1024), nullable=False)
    thumbnail_path = Column(String(1024), nullable=True)
    duration = Column(Float, default=0.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    checksum = Column(String(64), nullable=True)

    # Stored processing settings (sync policy, mute mode, speed ratio, offset, subtitle style)
    settings = Column(JSON, default=dict)
    media_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    video_asset = relationship("VideoAsset", back_populates="derivatives")
    publications = relationship("Publication", back_populates="derivative")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_asset_id = Column(String(36), ForeignKey("video_assets.id"), nullable=False)
    derivative_id = Column(String(36), ForeignKey("media_derivatives.id"), nullable=True)
    provider = Column(String(64), default="local_whisper")
    source_lang = Column(String(16), default="en")
    target_lang = Column(String(16), default="en")
    full_text = Column(Text, default="")
    # List of segments: [{"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world"}]
    segments = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)

    video_asset = relationship("VideoAsset", back_populates="transcripts")


class ContentDraft(Base):
    __tablename__ = "content_drafts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_asset_id = Column(String(36), ForeignKey("video_assets.id"), nullable=False)
    platform = Column(String(32), nullable=False)  # instagram, youtube
    title = Column(String(256), default="")
    caption = Column(Text, default="")
    description = Column(Text, default="")
    hashtags = Column(Text, default="")
    language = Column(String(16), default="en")
    generation_source = Column(String(64), default="user_edit")  # ai_suggested, user_edit
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    video_asset = relationship("VideoAsset", back_populates="drafts")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_type = Column(String(64), nullable=False)  # download, extract_audio, sync_voiceover, transcribe, burn_subtitles, export, publish
    asset_id = Column(String(36), nullable=True)
    status = Column(String(32), default="queued")  # queued, processing, completed, failed, cancelled
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    stage = Column(String(128), default="Initializing")
    retry_count = Column(Integer, default=0)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    platform = Column(String(32), nullable=False, unique=True)  # instagram, youtube
    account_identifier = Column(String(256), default="")
    account_name = Column(String(256), default="")
    connection_status = Column(String(32), default="disconnected")  # connected, disconnected, expired
    scopes = Column(String(512), default="")
    token_expiry = Column(DateTime, nullable=True)
    # Stored credentials metadata (redacted/server-side only)
    credentials_meta = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class Publication(Base):
    __tablename__ = "publications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_asset_id = Column(String(36), ForeignKey("video_assets.id"), nullable=False)
    derivative_id = Column(String(36), ForeignKey("media_derivatives.id"), nullable=True)
    platform = Column(String(32), nullable=False)  # instagram, youtube
    scheduled_time = Column(DateTime, nullable=True)
    status = Column(String(32), default="draft")  # draft, scheduled, publishing, published, failed
    remote_post_id = Column(String(256), nullable=True)
    remote_post_url = Column(String(1024), nullable=True)
    attempts = Column(Integer, default=0)
    error_details = Column(Text, nullable=True)
    idempotency_key = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    video_asset = relationship("VideoAsset", back_populates="publications")
    derivative = relationship("MediaDerivative", back_populates="publications")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
