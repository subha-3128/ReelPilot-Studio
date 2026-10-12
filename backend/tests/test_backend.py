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
from app.core.config import settings
from fastapi import HTTPException

from tests.conftest import TestingSessionLocal, client

# 1. Security & URL Validation Tests
def test_valid_kuaishou_urls():
    valid_urls = [
        "https://v.kuaishou.com/abc123",
        "https://www.kuaishou.com/short-video/3x7a8b",
        "https://kwai.com/v/example",
        "https://m.kwai.com/photo/12345",
        "https://www.instagram.com/reel/Cxxxxxx/",
        "https://instagram.com/p/Cxxxxxx/",
        "https://instagr.am/reel/12345",
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
    assert len(drafts["instagram"]["title"]) > 0
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

# 7. Media Streaming & Social Ingestion Tests
def test_media_stream_by_filename():
    test_file = settings.DERIVATIVES_DIR / "test_stream_video.mp4"
    test_file.write_bytes(b"A" * 1024)
    try:
        # Full content
        res = client.get("/api/media/stream/test_stream_video.mp4")
        assert res.status_code == 200
        assert len(res.content) == 1024

        # Partial content Range request
        res_range = client.get(
            "/api/media/stream/test_stream_video.mp4",
            headers={"Range": "bytes=0-499"},
        )
        assert res_range.status_code == 206
        assert "Content-Range" in res_range.headers
        assert res_range.headers["Content-Range"] == "bytes 0-499/1024"
        assert len(res_range.content) == 500
    finally:
        test_file.unlink(missing_ok=True)

def test_instagram_publisher_share_to_feed_and_permalink(monkeypatch):
    from unittest.mock import patch, MagicMock
    from app.services.publisher import InstagramPublisher

    ig = InstagramPublisher()
    dummy_path = settings.ORIGINALS_DIR / "dummy_ig.mp4"
    dummy_path.write_bytes(b"dummy")

    # Test user-configured explicit public base URL
    with patch("app.core.config.settings.PUBLIC_BASE_URL", "https://reelpilot-test.onrender.com"):
        url = ig._get_public_video_url(dummy_path, None)
        assert url == "https://reelpilot-test.onrender.com/api/media/stream/dummy_ig.mp4"

    # Test publish container payload and permalink lookup
    captured_payloads = []
    def mock_post(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "media_publish" in url:
            mock_resp.json.return_value = {"id": "18114804401518384"}
        else:
            payload = kwargs.get("data", {})
            captured_payloads.append(payload)
            mock_resp.json.return_value = {"id": "container_123"}
        return mock_resp

    def mock_get(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "fields=status_code" in url:
            mock_resp.json.return_value = {"status_code": "FINISHED"}
        elif "permalink" in url:
            mock_resp.json.return_value = {
                "permalink": "https://www.instagram.com/reel/DeXRBHigPKE/",
                "shortcode": "DeXRBHigPKE",
                "id": "18114804401518384",
            }
        return mock_resp

    db = TestingSessionLocal()
    mock_pub = MagicMock()
    mock_pub.derivative_id = "deriv_1"

    with patch("httpx.Client.post", side_effect=mock_post), \
         patch("httpx.Client.get", side_effect=mock_get), \
         patch("app.core.config.settings.INSTAGRAM_ACCESS_TOKEN", "mock_token"), \
         patch("app.core.config.settings.INSTAGRAM_ACCOUNT_ID", "17841400000000000"):

        result = ig.publish(
            db=db,
            publication=mock_pub,
            video_path=dummy_path,
            title="Epic Reel",
            caption="Check out this epic moment!",
            description="",
            tags="#reels, #viral",
        )

        assert result["success"] is True
        assert result["remote_post_id"] == "18114804401518384"
        assert result["remote_post_url"] == "https://www.instagram.com/reel/DeXRBHigPKE/"
        assert len(captured_payloads) > 0
        assert captured_payloads[0]["share_to_feed"] == "true"
        assert captured_payloads[0]["media_type"] == "REELS"

    db.close()
    dummy_path.unlink(missing_ok=True)

def test_youtube_shorts_metadata_enforcement():
    from unittest.mock import patch, MagicMock
    from app.services.publisher import YouTubePublisher

    yt = YouTubePublisher()
    dummy_path = settings.ORIGINALS_DIR / "dummy_yt.mp4"
    dummy_path.write_bytes(b"dummy")

    captured_metadata = []
    def mock_post(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "uploadType=resumable" in url:
            captured_metadata.append(kwargs.get("json"))
            mock_resp.headers = {"Location": "https://upload.youtube.com/resumable/test"}
        return mock_resp

    def mock_put(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "short_vid_999"}
        return mock_resp

    db = TestingSessionLocal()
    mock_pub = MagicMock()

    with patch.object(yt, "_get_access_token", return_value="mock_yt_token"), \
         patch("httpx.Client.post", side_effect=mock_post), \
         patch("httpx.Client.put", side_effect=mock_put):

        res = yt.publish(
            db=db,
            publication=mock_pub,
            video_path=dummy_path,
            title="Unbelievable Action Scene",
            caption="",
            description="Detailed commentary",
            tags="action, skills",
        )

        assert res["success"] is True
        assert res["remote_post_id"] == "short_vid_999"
        assert res["remote_post_url"] == "https://youtube.com/shorts/short_vid_999"

        assert len(captured_metadata) == 1
        meta = captured_metadata[0]["snippet"]
        # Must enforce #Shorts in title
        assert "#Shorts" in meta["title"]
        # Must enforce #Shorts in description
        assert "#Shorts" in meta["description"]
        # Must enforce Shorts tags
        assert "Shorts" in meta["tags"]
        assert "YouTube Shorts" in meta["tags"]

    db.close()
    dummy_path.unlink(missing_ok=True)

def test_clean_expired_media_after_5_minutes():
    import time
    import os
    from app.services.scheduler import scheduler

    old_file = settings.DERIVATIVES_DIR / "old_test_reel.mp4"
    old_file.write_bytes(b"old reel content")
    past_time = time.time() - 350
    os.utime(old_file, (past_time, past_time))

    fresh_file = settings.DERIVATIVES_DIR / "fresh_test_reel.mp4"
    fresh_file.write_bytes(b"fresh reel content")

    db_file = settings.DERIVATIVES_DIR / "test_backup.db"
    db_file.write_bytes(b"sqlite content")
    os.utime(db_file, (past_time, past_time))

    try:
        scheduler._clean_expired_media(max_age_seconds=300)

        assert not old_file.exists(), "Old reel should be deleted after 5 minutes"
        assert fresh_file.exists(), "Fresh reel under 5 minutes must be preserved"
        assert db_file.exists(), "Database files must not be deleted by media cleaner"
    finally:
        old_file.unlink(missing_ok=True)
        fresh_file.unlink(missing_ok=True)
        db_file.unlink(missing_ok=True)

@pytest.mark.asyncio
async def test_delayed_reel_cleanup():
    from app.telegram.pipeline import _delayed_reel_cleanup

    temp_reel = settings.TEMP_DIR / "test_delayed_reel.mp4"
    temp_reel.write_bytes(b"temp reel data")
    assert temp_reel.exists()

    await _delayed_reel_cleanup([temp_reel], delay_seconds=0)

    assert not temp_reel.exists(), "Delayed cleanup should delete reel from Render storage"

