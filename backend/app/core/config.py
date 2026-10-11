import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ReelPilot"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False

    # Base workspace and media storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'storage' / 'studio.db'}"

    # Media subdirectories
    ORIGINALS_DIR: Path = STORAGE_DIR / "originals"
    VOICEOVERS_DIR: Path = STORAGE_DIR / "voiceovers"
    DERIVATIVES_DIR: Path = STORAGE_DIR / "derivatives"
    THUMBNAILS_DIR: Path = STORAGE_DIR / "thumbnails"
    TEMP_DIR: Path = STORAGE_DIR / "temp"

    # Default Preferences
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_SYNC_POLICY: str = "keep_natural_speed"  # keep_natural_speed | fit_to_video | manual_adjustment
    DEFAULT_SUBTITLE_FONT_SIZE: int = 24
    DEFAULT_SUBTITLE_FONT_COLOR: str = "&H00FFFFFF"

    # AI & Platform Keys
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Instagram Reels
    INSTAGRAM_ACCOUNT_ID: str = ""
    INSTAGRAM_BUSINESS_ACCOUNT_ID: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""
    PUBLIC_BASE_URL: str = ""  # Optional external URL / tunnel for Meta Reels ingestion

    # YouTube Direct Upload (OAuth 2.0)
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REFRESH_TOKEN: str = ""
    YOUTUBE_CLIENT_SECRETS_FILE: str = ""

    # Telegram Bot Automation
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_USER_IDS: str = ""  # Comma-separated list of Telegram user IDs (e.g. "12345678,87654321")
    TELEGRAM_MODE: str = "polling"  # polling | disabled
    TELEGRAM_DEFAULT_WORKFLOW_MODE: str = "interactive"  # interactive | automatic
    REELPILOT_MAX_CONCURRENT_JOBS: int = 1
    REELPILOT_MAX_VIDEO_SIZE_MB: int = 100
    REELPILOT_AUTO_PUBLISH: bool = False
    REELPILOT_CLOUD_MODE: bool = False

    def get_allowed_telegram_user_ids(self) -> set:
        if not self.TELEGRAM_ALLOWED_USER_IDS:
            return set()
        ids = set()
        for piece in self.TELEGRAM_ALLOWED_USER_IDS.split(","):
            piece = piece.strip()
            if piece.isdigit():
                ids.add(int(piece))
        return ids

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "extra": "ignore",
    }

    @property
    def RESOLVED_DATABASE_URL(self) -> str:
        if self.DATABASE_URL.startswith("sqlite:///./"):
            rel_path = self.DATABASE_URL.replace("sqlite:///./", "")
            return f"sqlite:///{self.BASE_DIR / rel_path}"
        return self.DATABASE_URL

    def set_storage_dir(self, new_dir: Path):
        self.STORAGE_DIR = new_dir.resolve()
        self.ORIGINALS_DIR = self.STORAGE_DIR / "originals"
        self.VOICEOVERS_DIR = self.STORAGE_DIR / "voiceovers"
        self.DERIVATIVES_DIR = self.STORAGE_DIR / "derivatives"
        self.THUMBNAILS_DIR = self.STORAGE_DIR / "thumbnails"
        self.TEMP_DIR = self.STORAGE_DIR / "temp"
        for folder in [
            self.STORAGE_DIR,
            self.ORIGINALS_DIR,
            self.VOICEOVERS_DIR,
            self.DERIVATIVES_DIR,
            self.THUMBNAILS_DIR,
            self.TEMP_DIR,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

settings = Settings()

# Ensure required storage directories exist
for folder in [
    settings.STORAGE_DIR,
    settings.ORIGINALS_DIR,
    settings.VOICEOVERS_DIR,
    settings.DERIVATIVES_DIR,
    settings.THUMBNAILS_DIR,
    settings.TEMP_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)
