import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Callable
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import ProcessingJob, Publication
from app.services.publisher import social_service

logger = logging.getLogger("studio.scheduler")

class BackgroundScheduler:
    """
    Persistent, restart-safe local scheduler and background task runner.
    Polls database for due scheduled posts and queued background processing jobs.
    """
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        # Immediate cleanup sweep on reboot to free disk and RAM cache
        try:
            self._clean_expired_media(max_age_seconds=300)
        except Exception as e:
            logger.debug("Initial cleanup sweep on startup: %s", e)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Background scheduler and job worker started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("Background scheduler stopped.")

    def _run_loop(self):
        last_clean_time = 0.0
        while self._running:
            try:
                self._check_due_publications()
            except Exception as e:
                logger.error("Error in scheduler cycle: %s", e)

            # Run 5-minute media cleanup check every 60 seconds
            now = time.time()
            if now - last_clean_time >= 60.0:
                try:
                    self._clean_expired_media(max_age_seconds=300)
                    last_clean_time = now
                except Exception as e:
                    logger.error("Error in media cleanup cycle: %s", e)

            time.sleep(5)  # Poll every 5 seconds

    def _check_due_publications(self):
        now_utc = datetime.now(timezone.utc)
        db: Session = SessionLocal()
        try:
            due_pubs = (
                db.query(Publication)
                .filter(Publication.status == "scheduled")
                .filter(Publication.scheduled_time <= now_utc)
                .all()
            )
            for pub in due_pubs:
                logger.info("Executing due scheduled publication %s for platform %s", pub.id, pub.platform)
                social_service.execute_publication(db, pub.id)
        finally:
            db.close()

    def _clean_expired_media(self, max_age_seconds: int = 300):
        """
        Automatically delete all reels, exports, original downloads, and temporary media
        older than 5 minutes (300s) from Render storage to strictly enforce low memory
        and disk footprint within free-tier limits.
        """
        from app.core.config import settings
        now = time.time()
        directories = [
            settings.DERIVATIVES_DIR,
            settings.ORIGINALS_DIR,
            settings.TEMP_DIR,
            settings.VOICEOVERS_DIR,
            settings.THUMBNAILS_DIR,
        ]
        deleted_count = 0
        freed_bytes = 0

        for directory in directories:
            if not directory or not directory.exists():
                continue
            for item in directory.glob("*"):
                if item.name.startswith(".") or not item.is_file():
                    continue
                if item.suffix.lower() in (".db", ".sqlite", ".sqlite3"):
                    continue
                try:
                    file_stat = item.stat()
                    file_age = now - file_stat.st_mtime
                    if file_age >= max_age_seconds:
                        size = file_stat.st_size
                        item.unlink(missing_ok=True)
                        deleted_count += 1
                        freed_bytes += size
                except Exception as file_err:
                    logger.debug("Could not delete file %s during cleanup: %s", item, file_err)

        if deleted_count > 0:
            freed_mb = freed_bytes / (1024 * 1024)
            logger.info(
                "Automated 5-min cleanup freed %.2f MB across %d files from Render storage.",
                freed_mb,
                deleted_count,
            )
            import gc
            gc.collect()

scheduler = BackgroundScheduler()
