import os
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.models import VideoAsset, MediaDerivative, VoiceoverAsset, Transcript, ContentDraft, Publication
from app.services.media import media_service
from app.services.transcription import transcription_service

from tests.conftest import TestingSessionLocal, client

@pytest.fixture(scope="session")
def synthetic_media(tmp_path_factory):
    """Generate synthetic 9:16 source video and English voice-over MP4 using ffmpeg."""
    tmp_dir = tmp_path_factory.mktemp("media_test")
    source_video = tmp_dir / "kuaishou_source.mp4"
    voiceover_video = tmp_dir / "english_voiceover.mp4"

    ffmpeg = media_service.ffmpeg_bin

    # 1. Generate 3-second 720x1280 9:16 video with test audio tone
    subprocess.run([
        ffmpeg, "-y",
        "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", "3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(source_video)
    ], check=True, capture_output=True)

    # 2. Generate 3-second voice-over MP4 with different audio frequency
    subprocess.run([
        ffmpeg, "-y",
        "-f", "lavfi", "-i", "color=c=blue:size=640x480:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=44100",
        "-t", "3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(voiceover_video)
    ], check=True, capture_output=True)

    return source_video, voiceover_video

def test_complete_end_to_end_video_workflow(synthetic_media):
    source_video_path, voiceover_video_path = synthetic_media
    orig_stat_before = source_video_path.stat().st_size

    # --- 1. Register Source Video Asset ---
    db = TestingSessionLocal()
    source_meta = media_service.probe(source_video_path)
    asset_id = "test-e2e-video-001"
    asset = VideoAsset(
        id=asset_id,
        original_source_url="https://v.kuaishou.com/e2etest",
        source_platform="kuaishou",
        original_local_path=str(source_video_path),
        filename=source_video_path.name,
        duration=source_meta["duration"],
        width=source_meta["width"],
        height=source_meta["height"],
        aspect_ratio=source_meta["aspect_ratio"],
        file_size=source_meta["file_size"],
        has_audio=True,
    )
    db.add(asset)
    db.commit()
    db.close()

    assert source_meta["aspect_ratio"] == "9:16"

    # --- 2. Upload English Voice-over MP4 ---
    with open(voiceover_video_path, "rb") as f:
        upload_res = client.post(
            "/api/studio/upload-voiceover",
            data={"video_asset_id": asset_id},
            files={"file": ("voiceover.mp4", f, "video/mp4")},
        )
    assert upload_res.status_code == 200
    vo_data = upload_res.json()
    vo_id = vo_data["id"]
    extracted_audio_path = Path(vo_data["extracted_audio_path"])
    assert extracted_audio_path.exists()
    assert extracted_audio_path.stat().st_size > 0

    # Verify extracted audio contains audio and no video
    audio_meta = media_service.probe(extracted_audio_path)
    assert audio_meta["has_audio"] is True
    assert audio_meta["has_video"] is False

    # --- 3. Synchronize Voice-over & Mute Original Audio ---
    sync_res = client.post(
        "/api/studio/sync-voiceover",
        json={
            "video_asset_id": asset_id,
            "voiceover_asset_id": vo_id,
            "sync_policy": "keep_natural_speed",
            "mute_original_audio": True,
            "start_offset_seconds": 0.0,
            "background_ambience_volume": 0.0,
        },
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    synced_file = Path(sync_data["local_path"])
    assert synced_file.exists()
    assert synced_file.stat().st_size > 0

    # Ensure original source video is completely untouched
    assert source_video_path.stat().st_size == orig_stat_before

    # Verify synced derivative has valid video & audio
    synced_meta = media_service.probe(synced_file)
    assert synced_meta["has_video"] is True
    assert synced_meta["has_audio"] is True
    assert synced_meta["aspect_ratio"] == "9:16"

    # --- 4. Subtitles & Captions Generation ---
    trans_res = client.get(f"/api/studio/{asset_id}/transcript?voiceover_id={vo_id}")
    assert trans_res.status_code == 200
    trans_data = trans_res.json()
    assert len(trans_data["segments"]) > 0

    # Edit caption segments
    segments = trans_data["segments"]
    segments[0]["text"] = "Welcome to the English edition."
    update_trans_res = client.put(
        f"/api/studio/{asset_id}/transcript",
        json={"segments": segments},
    )
    assert update_trans_res.status_code == 200

    # --- 5. Burn Subtitles and Export Derivative ---
    burn_res = client.post(
        "/api/studio/burn-subtitles",
        json={
            "video_asset_id": asset_id,
            "derivative_id": sync_data["id"],
            "font_size": 26,
            "font_color": "&H00FFFFFF",
        },
    )
    assert burn_res.status_code == 200
    captioned_data = burn_res.json()
    captioned_file = Path(captioned_data["local_path"])
    assert captioned_file.exists()

    # Export final derivative
    export_res = client.post(
        "/api/studio/export",
        json={"video_asset_id": asset_id, "derivative_id": captioned_data["id"]},
    )
    assert export_res.status_code == 200
    export_data = export_res.json()
    export_file = Path(export_data["local_path"])
    assert export_file.exists()

    # --- 6. AI Metadata Assistant ---
    meta_gen_res = client.post(
        "/api/drafts/generate",
        json={"video_asset_id": asset_id, "tone": "engaging", "include_hashtags": True},
    )
    assert meta_gen_res.status_code == 200
    drafts = meta_gen_res.json()
    assert len(drafts) >= 2
    ig_draft = next(d for d in drafts if d["platform"] == "instagram")
    yt_draft = next(d for d in drafts if d["platform"] == "youtube")
    assert "#reels" in ig_draft["hashtags"].lower() or "reel" in ig_draft["hashtags"].lower()
    assert len(yt_draft["title"]) > 0

    # --- 7. Publish and Schedule to Both Platforms ---
    pub_res = client.post(
        "/api/publications",
        json={
            "video_asset_id": asset_id,
            "derivative_id": export_data["id"],
            "platforms": ["instagram", "youtube"],
        },
    )
    assert pub_res.status_code == 200
    pubs = pub_res.json()
    assert len(pubs) == 2

    # Verify independent platform tracking
    ig_pub = next(p for p in pubs if p["platform"] == "instagram")
    yt_pub = next(p for p in pubs if p["platform"] == "youtube")
    assert ig_pub["platform"] == "instagram"
    assert yt_pub["platform"] == "youtube"

    # Retry single platform without duplicating
    retry_res = client.post(f"/api/publications/{ig_pub['id']}/retry")
    assert retry_res.status_code == 200
    retried_data = retry_res.json()
    assert retried_data["attempts"] == ig_pub["attempts"] + 1

    # Original video still intact at the very end
    assert source_video_path.stat().st_size == orig_stat_before
