import os
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db

# Create a temporary file database for tests
temp_dir = tempfile.mkdtemp()
TEST_DB_PATH = Path(temp_dir) / "test_studio.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=test_engine)

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_social_publishers(monkeypatch):
    """Ensure automated tests never call external Meta or Google endpoints."""
    from app.services.publisher import social_service

    def mock_ig_publish(db, pub, video_path, title, caption, description, tags):
        if pub.attempts == 1:
            return {"success": False, "error": "Simulated temporary network timeout"}
        return {
            "success": True,
            "remote_post_id": "mock_ig_123456789",
            "remote_post_url": "https://instagram.com/reel/mock123",
        }

    def mock_yt_publish(db, pub, video_path, title, caption, description, tags):
        return {
            "success": True,
            "remote_post_id": "mock_yt_987654321",
            "remote_post_url": "https://youtube.com/shorts/mock987",
        }

    monkeypatch.setattr(social_service.instagram, "publish", mock_ig_publish)
    monkeypatch.setattr(social_service.youtube, "publish", mock_yt_publish)
