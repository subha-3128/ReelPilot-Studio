import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import validate_and_normalize_url, sanitize_filename
from app.models.models import VideoAsset
from app.services.media import media_service

logger = logging.getLogger("studio.downloader")

class DownloaderService:
    def __init__(self):
        self.ytdlp_bin = shutil.which("yt-dlp") or "/opt/homebrew/bin/yt-dlp"

    def is_available(self) -> bool:
        return bool(shutil.which("yt-dlp") or Path(self.ytdlp_bin).exists())

    def calculate_sha256(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def extract_kuaishou_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Directly parse Kuaishou/Kwai video stream and metadata from web share page."""
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        try:
            with httpx.Client(follow_redirects=True, timeout=20.0, headers=headers) as client:
                res = client.get(url)
                if res.status_code != 200:
                    return None

                caption = "Kuaishou Video"
                author = ""
                duration = 0.0
                thumb_url = None
                video_url = None

                # 1. Parse window.INIT_STATE
                m = re.search(r"window\.INIT_STATE\s*=\s*(\{.+?\});?</script>", res.text)
                if m:
                    try:
                        state_data = json.loads(m.group(1))
                        for k, v in state_data.items():
                            if isinstance(v, dict) and "photo" in v:
                                photo = v["photo"]
                                caption = photo.get("caption") or caption
                                author = photo.get("userName") or author
                                if photo.get("duration"):
                                    duration = float(photo.get("duration")) / 1000.0

                                covers = photo.get("coverUrls") or []
                                if covers and isinstance(covers[0], dict):
                                    thumb_url = covers[0].get("url")

                                reps = photo.get("manifest", {}).get("adaptationSet", [{}])[0].get("representation", [])
                                for rep in reps:
                                    if rep.get("url"):
                                        video_url = rep["url"]

                                if not video_url:
                                    mv_urls = photo.get("mainMvUrls") or []
                                    if mv_urls and isinstance(mv_urls[0], dict):
                                        video_url = mv_urls[0].get("url")
                    except Exception as e:
                        logger.warning("Error parsing INIT_STATE: %s", e)

                # 2. Fallback regex for MP4 streams
                if not video_url:
                    mp4s = re.findall(r'https?://[^\s"\'<>\\]+?\.mp4[^\s"\'<>\\]*', res.text)
                    for candidate in mp4s:
                        if "kwaicdn.com" in candidate or "kwimgs.com" in candidate:
                            video_url = candidate
                            break
                    if not video_url and mp4s:
                        video_url = mp4s[0]

                if not video_url:
                    return None

                title = f"{caption} - {author}".strip(" -") if author else caption
                return {
                    "title": title,
                    "author": author,
                    "duration": duration,
                    "thumb_url": thumb_url,
                    "video_url": video_url,
                }
        except Exception as e:
            logger.warning("Native Kuaishou info extraction error for %s: %s", url, e)
            return None

    def _download_direct_stream(self, video_url: str, target_path: Path) -> bool:
        """Stream direct MP4 video from CDN to local storage file."""
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://www.kuaishou.com/",
        }
        try:
            with httpx.stream("GET", video_url, headers=headers, follow_redirects=True, timeout=60.0) as resp:
                if resp.status_code not in (200, 206):
                    logger.error("Direct stream failed with status %d", resp.status_code)
                    return False
                with open(target_path, "wb") as f:
                    for chunk in resp.iter_bytes(65536):
                        f.write(chunk)
            return target_path.exists() and target_path.stat().st_size > 0
        except Exception as e:
            logger.error("Direct stream download exception: %s", e)
            return False

    def inspect_url(self, db: Session, url: str) -> Dict[str, Any]:
        """Validate URL and check if already downloaded in local library."""
        normalized_url = validate_and_normalize_url(url)

        # Check existing database entries for exact URL duplicate
        existing = db.query(VideoAsset).filter(VideoAsset.original_source_url == normalized_url).first()
        if existing:
            return {
                "url": normalized_url,
                "title": existing.filename,
                "thumbnail": f"/api/media/thumbnail/{existing.id}",
                "duration": existing.duration,
                "is_supported": True,
                "duplicate_asset_id": existing.id,
                "message": "Video with this exact URL already exists in your library.",
            }

        # 1. First probe via native Kuaishou extractor
        ks_info = self.extract_kuaishou_info(normalized_url)
        if ks_info:
            return {
                "url": normalized_url,
                "title": ks_info["title"],
                "thumbnail": ks_info.get("thumb_url"),
                "duration": ks_info.get("duration"),
                "is_supported": True,
                "duplicate_asset_id": None,
                "message": "Valid Kuaishou video link ready for download.",
            }

        # 2. Probe with yt-dlp --dump-json without downloading
        cmd = [
            self.ytdlp_bin,
            "--no-warnings",
            "--dump-json",
            "--no-playlist",
            normalized_url,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=25)
            info = json.loads(res.stdout)
            return {
                "url": normalized_url,
                "title": info.get("title", "Kuaishou Video"),
                "thumbnail": info.get("thumbnail"),
                "duration": float(info.get("duration", 0.0)),
                "is_supported": True,
                "duplicate_asset_id": None,
                "message": "Valid supported video link.",
            }
        except subprocess.SubprocessError as e:
            logger.warning("URL inspection fallback for %s: %s", normalized_url, e)
            return {
                "url": normalized_url,
                "title": "Kuaishou / Kwai Video",
                "thumbnail": None,
                "duration": None,
                "is_supported": True,
                "duplicate_asset_id": None,
                "message": "Link ready for download.",
            }

    def download_video(
        self,
        db: Session,
        url: str,
        rights_acknowledged: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> VideoAsset:
        """Download video to local storage safely using native stream or yt-dlp."""
        if not rights_acknowledged:
            raise HTTPException(
                status_code=400,
                detail="You must acknowledge having rights or authorization to process this video.",
            )

        normalized_url = validate_and_normalize_url(url)

        # Check existing duplicate by URL
        existing_url_match = db.query(VideoAsset).filter(VideoAsset.original_source_url == normalized_url).first()
        if existing_url_match and Path(existing_url_match.original_local_path).exists():
            return existing_url_match

        file_id = str(uuid.uuid4())
        download_success = False
        target_file = None

        # --- Method A: Native Kuaishou CDN Direct Stream ---
        if progress_callback:
            progress_callback(10.0, "Resolving Kuaishou video stream...")

        ks_info = self.extract_kuaishou_info(normalized_url)
        if ks_info and ks_info.get("video_url"):
            clean_title = sanitize_filename(ks_info["title"])[:50]
            candidate_file = settings.ORIGINALS_DIR / f"{file_id}_{clean_title}.mp4"
            if progress_callback:
                progress_callback(25.0, f"Downloading video directly from Kuaishou CDN...")
            if self._download_direct_stream(ks_info["video_url"], candidate_file):
                target_file = candidate_file
                download_success = True
                logger.info("Direct native Kuaishou download succeeded: %s", candidate_file.name)

        # --- Method B: Fallback to yt-dlp ---
        if not download_success:
            if progress_callback:
                progress_callback(30.0, "Starting video download via yt-dlp engine...")

            out_template = str(settings.ORIGINALS_DIR / f"{file_id}_%(title).50s.%(ext)s")
            cmd = [
                self.ytdlp_bin,
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "--no-playlist",
                "-o", out_template,
                normalized_url,
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=180)
                logger.info("yt-dlp download completed for %s", normalized_url)
                matched_files = list(settings.ORIGINALS_DIR.glob(f"{file_id}_*"))
                if matched_files:
                    target_file = matched_files[0]
                    download_success = True
            except subprocess.SubprocessError as e:
                logger.error("yt-dlp download failed for %s: %s", normalized_url, e)

        if not download_success or not target_file or not target_file.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download video from {normalized_url}. The video link may be private, expired, or unavailable.",
            )

        if progress_callback:
            progress_callback(60.0, "Probing video metadata and computing checksum")

        checksum = self.calculate_sha256(target_file)

        # Check duplicate by checksum
        existing_checksum = db.query(VideoAsset).filter(VideoAsset.checksum == checksum).first()
        if existing_checksum and Path(existing_checksum.original_local_path).exists():
            # Clean up duplicate download
            target_file.unlink(missing_ok=True)
            return existing_checksum

        # Probe video using FFprobe
        meta = media_service.probe(target_file)

        # Generate thumbnail
        thumb_path = settings.THUMBNAILS_DIR / f"{file_id}.jpg"
        media_service.generate_thumbnail(target_file, thumb_path)

        if progress_callback:
            progress_callback(90.0, "Registering video in library database")

        asset = VideoAsset(
            id=file_id,
            original_source_url=normalized_url,
            source_platform="kuaishou" if "kuaishou" in normalized_url else "kwai",
            original_local_path=str(target_file),
            filename=target_file.name,
            thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
            duration=meta["duration"],
            width=meta["width"],
            height=meta["height"],
            aspect_ratio=meta["aspect_ratio"],
            file_size=meta["file_size"],
            checksum=checksum,
            has_audio=meta["has_audio"],
            rights_notes="User confirmed authorization",
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        if progress_callback:
            progress_callback(100.0, "Download and ingestion completed")

        return asset

downloader_service = DownloaderService()
