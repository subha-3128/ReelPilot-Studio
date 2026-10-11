from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Base & Response Enums/Primitives ---
class MessageResponse(BaseModel):
    message: str
    success: bool = True

# --- Asset Schemas ---
class MediaDerivativeResponse(BaseModel):
    id: str
    video_asset_id: str
    derivative_type: str
    local_path: str
    thumbnail_path: Optional[str] = None
    duration: float
    width: int
    height: int
    file_size: int
    checksum: Optional[str] = None
    settings: Dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}

class VoiceoverAssetResponse(BaseModel):
    id: str
    video_asset_id: str
    filename: str
    duration: float
    file_size: int
    extracted_audio_path: str
    created_at: datetime

    model_config = {"from_attributes": True}

class VideoAssetResponse(BaseModel):
    id: str
    original_source_url: str
    source_platform: str
    filename: str
    thumbnail_path: Optional[str] = None
    duration: float
    width: int
    height: int
    aspect_ratio: str
    file_size: int
    checksum: Optional[str] = None
    has_audio: bool
    rights_notes: str
    created_at: datetime
    derivatives: List[MediaDerivativeResponse] = []
    voiceovers: List[VoiceoverAssetResponse] = []

    model_config = {"from_attributes": True}

class VideoAssetDetailResponse(VideoAssetResponse):
    pass

# --- Downloader Schemas ---
class DownloadRequest(BaseModel):
    url: str = Field(..., description="Kuaishou or Kwai video URL")
    rights_acknowledged: bool = Field(True, description="Confirmation that user has rights/permission to process video")

class DownloadInspectResponse(BaseModel):
    url: str
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[float] = None
    is_supported: bool = True
    duplicate_asset_id: Optional[str] = None
    message: Optional[str] = None

# --- Studio & Voiceover Schemas ---
class VoiceoverSyncRequest(BaseModel):
    video_asset_id: str
    voiceover_asset_id: str
    sync_policy: str = Field("keep_natural_speed", description="keep_natural_speed | fit_to_video | manual_adjustment")
    mute_original_audio: bool = Field(True, description="Mute all original video audio")
    start_offset_seconds: float = Field(0.0, description="Start offset for voiceover in seconds")
    audio_trim_seconds: Optional[float] = Field(None, description="Optional trim length for audio")
    background_ambience_volume: float = Field(0.0, description="Original audio volume if ambience retained (0.0 = muted)")

class SubtitleSegmentItem(BaseModel):
    id: int
    start: float
    end: float
    text: str

class TranscriptResponse(BaseModel):
    id: str
    video_asset_id: str
    derivative_id: Optional[str] = None
    provider: str
    source_lang: str
    target_lang: str
    full_text: str
    segments: List[SubtitleSegmentItem] = []
    created_at: datetime

    model_config = {"from_attributes": True}

class TranscriptUpdateRequest(BaseModel):
    segments: List[SubtitleSegmentItem]

class BurnSubtitlesRequest(BaseModel):
    video_asset_id: str
    derivative_id: Optional[str] = None
    font_size: int = 24
    font_color: str = "&H00FFFFFF"
    outline_color: str = "&H00000000"
    outline_width: int = 2
    alignment: int = 2  # Bottom centered

class ExportRequest(BaseModel):
    video_asset_id: str
    derivative_id: Optional[str] = None
    target_format: str = "mp4"

# --- AI Metadata & Content Drafts ---
class ContentDraftResponse(BaseModel):
    id: str
    video_asset_id: str
    platform: str
    title: str
    caption: str
    description: str
    hashtags: str
    language: str
    generation_source: str
    updated_at: datetime

    model_config = {"from_attributes": True}

class DraftUpdateRequest(BaseModel):
    platform: str
    title: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None

class GenerateMetadataRequest(BaseModel):
    video_asset_id: str
    tone: Optional[str] = "engaging"
    include_hashtags: bool = True
    platforms: List[str] = ["instagram", "youtube"]

# --- Background Jobs ---
class JobResponse(BaseModel):
    id: str
    job_type: str
    asset_id: Optional[str] = None
    status: str
    progress: float
    stage: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

# --- Publishing & Scheduling ---
class PublishRequest(BaseModel):
    video_asset_id: str
    derivative_id: Optional[str] = None
    platforms: List[str] = Field(..., description="List of platforms: ['instagram'], ['youtube'], or both")
    schedule_time: Optional[datetime] = Field(None, description="UTC time to schedule, or None to post immediately")

class PublicationResponse(BaseModel):
    id: str
    video_asset_id: str
    derivative_id: Optional[str] = None
    platform: str
    scheduled_time: Optional[datetime] = None
    status: str
    remote_post_id: Optional[str] = None
    remote_post_url: Optional[str] = None
    attempts: int
    error_details: Optional[str] = None
    idempotency_key: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

# --- Settings & Social Accounts ---
class SocialAccountResponse(BaseModel):
    id: str
    platform: str
    account_identifier: str
    account_name: str
    connection_status: str
    scopes: str
    token_expiry: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}

class ConnectAccountRequest(BaseModel):
    platform: str
    auth_code: Optional[str] = None
    access_token: Optional[str] = None
    account_identifier: Optional[str] = None
    account_name: Optional[str] = None

class AppSettingsResponse(BaseModel):
    storage_dir: str
    free_disk_space_gb: float
    timezone: str
    default_sync_policy: str
    subtitle_font_size: int
    subtitle_font_color: str
    ffmpeg_available: bool
    ytdlp_available: bool

class AppSettingsUpdateRequest(BaseModel):
    storage_dir: Optional[str] = None
    timezone: Optional[str] = None
    default_sync_policy: Optional[str] = None
    subtitle_font_size: Optional[int] = None
    subtitle_font_color: Optional[str] = None
