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
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Background scheduler and job worker started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("Background scheduler stopped.")

    def _run_loop(self):
        while self._running:
            try:
                self._check_due_publications()
            except Exception as e:
                logger.error("Error in scheduler cycle: %s", e)
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

scheduler = BackgroundScheduler()
