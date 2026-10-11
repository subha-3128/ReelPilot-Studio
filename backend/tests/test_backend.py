import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import validate_and_normalize_url, sanitize_filename, safe_resolve_path
from app.services.transcription import transcription_service, format_timestamp_srt, format_timestamp_vtt
from app.services.metadata_ai import metadata_service
from app.models.models import VideoAsset, MediaDerivative, Publication, SocialAccount
from fastapi import HTTPException

from tests.conftest import TestingSessionLocal, client

# 1. Security & URL Validation Tests
def test_valid_kuaishou_urls():
    valid_urls = [
        "https://v.kuaishou.com/abc123",
        "https://www.kuaishou.com/short-video/3x7a8b",
        "https://kwai.com/v/example",
        "https://m.kwai.com/photo/12345",
    ]
    for url in valid_urls:
        normalized = validate_and_normalize_url(url)
        assert normalized == url

def test_reject_unsupported_domains():
    with pytest.raises(HTTPException) as exc:
        validate_and_normalize_url("https://malicious-site.com/video")
    assert exc.value.status_code == 400
    assert "not supported" in exc.value.detail

def test_reject_invalid_schemes():
    with pytest.raises(HTTPException):
        validate_and_normalize_url("file:///etc/passwd")
    with pytest.raises(HTTPException):
        validate_and_normalize_url("ftp://kuaishou.com/video")

def test_sanitize_filename():
    assert sanitize_filename("my_video!@#$.mp4") == "my_video____.mp4"
    assert sanitize_filename("../../etc/passwd") == "passwd"

def test_path_traversal_guard(tmp_path):
    safe_base = tmp_path / "storage"
    safe_base.mkdir()
    child_file = safe_base / "video.mp4"
    child_file.touch()

    # Allowed path
    resolved = safe_resolve_path(safe_base, str(child_file))
    assert resolved == child_file

    # Traversal attempt
    with pytest.raises(HTTPException) as exc:
        safe_resolve_path(safe_base, str(tmp_path / "outside.txt"))
    assert exc.value.status_code == 403

# 2. Transcription SRT & VTT Formatter Tests
def test_timestamp_formatting():
    assert format_timestamp_srt(0.0) == "00:00:00,000"
    assert format_timestamp_srt(65.5) == "00:01:05,500"
    assert format_timestamp_vtt(65.5) == "00:01:05.500"

def test_srt_generation():
    segments = [
        {"id": 1, "start": 0.0, "end": 2.5, "text": "Welcome to the show."},
        {"id": 2, "start": 2.5, "end": 5.0, "text": "Let us get started."},
    ]
    srt = transcription_service.generate_srt(segments)
    assert "00:00:00,000 --> 00:00:02,500" in srt
    assert "Welcome to the show." in srt
    assert "00:00:02,500 --> 00:00:05,000" in srt
    assert "Let us get started." in srt

# 3. AI Metadata Draft Generation Tests
def test_metadata_generation():
    drafts = metadata_service.generate_drafts(
        filename="cooking_dumplings_viral.mp4",
        transcript_text="Today we make delicious homemade dumplings with crispy bottoms.",
    )
    assert "instagram" in drafts
    assert "youtube" in drafts
    assert len(drafts["youtube"]["title"]) > 0
    assert len(drafts["instagram"]["caption"]) > 0
    assert len(drafts["instagram"]["hashtags"]) > 0

# 4. API Health Check & Settings
def test_health_check_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_settings_endpoints():
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "storage_dir" in data
    assert "timezone" in data
    assert "ffmpeg_available" in data

    # Update settings
    update_res = client.put("/api/settings", json={"timezone": "UTC", "subtitle_font_size": 28})
    assert update_res.status_code == 200

# 5. Asset CRUD Flow
def test_asset_crud_flow():
    db = TestingSessionLocal()
    dummy_asset = VideoAsset(
        id="test-asset-1",
        original_source_url="https://v.kuaishou.com/test1",
        source_platform="kuaishou",
        original_local_path="/tmp/test1.mp4",
        filename="test1.mp4",
        duration=15.0,
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        file_size=1024000,
        has_audio=True,
    )
    db.add(dummy_asset)
    db.commit()
    db.close()

    res = client.get("/api/assets")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["id"] == "test-asset-1"

    detail_res = client.get("/api/assets/test-asset-1")
    assert detail_res.status_code == 200
    assert detail_res.json()["filename"] == "test1.mp4"

# 6. Publication and Independent Retry
def test_publication_creation_and_independent_status():
    db = TestingSessionLocal()
    dummy_asset = VideoAsset(
        id="pub-asset-1",
        original_source_url="https://v.kuaishou.com/pub1",
        source_platform="kuaishou",
        original_local_path="/tmp/pub1.mp4",
        filename="pub1.mp4",
        duration=10.0,
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        file_size=500000,
        has_audio=True,
    )
    db.add(dummy_asset)
    db.commit()
    db.close()

    # Publish to both Instagram and YouTube
    res = client.post(
        "/api/publications",
        json={"video_asset_id": "pub-asset-1", "platforms": ["instagram", "youtube"]},
    )
    assert res.status_code == 200
    pubs = res.json()
    assert len(pubs) == 2
    platforms = {p["platform"] for p in pubs}
    assert platforms == {"instagram", "youtube"}

    # Each has independent status (fails due to unconnected account or unhosted local file, as expected by specification)
    for p in pubs:
        assert p["status"] in ("failed", "publishing")

    # Retry single platform publication
    ig_pub = next(p for p in pubs if p["platform"] == "instagram")
    retry_res = client.post(f"/api/publications/{ig_pub['id']}/retry")
    assert retry_res.status_code == 200
