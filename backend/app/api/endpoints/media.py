import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import safe_resolve_path
from app.models.models import VideoAsset, MediaDerivative, VoiceoverAsset

router = APIRouter(prefix="/media", tags=["Media"])

def send_file_range(file_path: Path, range_header: str):
    file_size = file_path.stat().st_size
    start, end = 0, file_size - 1

    try:
        parts = range_header.replace("bytes=", "").split("-")
        if parts[0]:
            start = int(parts[0])
        if len(parts) > 1 and parts[1]:
            end = int(parts[1])
    except ValueError:
        pass

    chunk_size = end - start + 1

    def file_iterator():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                read_bytes = min(remaining, 65536)
                data = f.read(read_bytes)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(file_iterator(), status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers)

@router.get("/video/{asset_id}")
def stream_original_video(asset_id: str, request: Request, db: Session = Depends(get_db)):
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset or not Path(asset.original_local_path).exists():
        raise HTTPException(status_code=404, detail="Original video file not found")

    file_path = safe_resolve_path(settings.STORAGE_DIR, asset.original_local_path)
    range_header = request.headers.get("range")
    if range_header:
        return send_file_range(file_path, range_header)
    return FileResponse(file_path, media_type="video/mp4")

@router.get("/derivative/{derivative_id}")
def stream_derivative_video(derivative_id: str, request: Request, db: Session = Depends(get_db)):
    deriv = db.query(MediaDerivative).filter(MediaDerivative.id == derivative_id).first()
    if not deriv or not Path(deriv.local_path).exists():
        raise HTTPException(status_code=404, detail="Derivative video file not found")

    file_path = safe_resolve_path(settings.STORAGE_DIR, deriv.local_path)
    range_header = request.headers.get("range")
    if range_header:
        return send_file_range(file_path, range_header)
    return FileResponse(file_path, media_type="video/mp4")

@router.get("/audio/{voiceover_id}")
def stream_audio(voiceover_id: str, db: Session = Depends(get_db)):
    vo = db.query(VoiceoverAsset).filter(VoiceoverAsset.id == voiceover_id).first()
    if not vo or not Path(vo.extracted_audio_path).exists():
        raise HTTPException(status_code=404, detail="Extracted audio file not found")

    file_path = safe_resolve_path(settings.STORAGE_DIR, vo.extracted_audio_path)
    return FileResponse(file_path, media_type="audio/mp4")

@router.get("/thumbnail/{asset_id}")
def get_thumbnail(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    thumb_path = None
    if asset and asset.thumbnail_path and Path(asset.thumbnail_path).exists():
        thumb_path = Path(asset.thumbnail_path)
    else:
        # Check derivative thumbnail
        deriv = db.query(MediaDerivative).filter(MediaDerivative.id == asset_id).first()
        if deriv and deriv.thumbnail_path and Path(deriv.thumbnail_path).exists():
            thumb_path = Path(deriv.thumbnail_path)

    if not thumb_path or not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    file_path = safe_resolve_path(settings.STORAGE_DIR, str(thumb_path))
    return FileResponse(file_path, media_type="image/jpeg")

@router.get("/stream/{filename}")
def stream_file_by_name(filename: str, request: Request):
    """
    Public streaming route for media files (derivatives, originals, exports).
    Supports HTTP 206 Partial Content for Meta Reels and media crawlers.
    """
    storage_root = Path(settings.STORAGE_DIR).resolve()
    for sub in ["derivatives", "originals", ""]:
        candidate = (storage_root / sub / filename).resolve()
        if candidate.exists() and candidate.is_file() and str(candidate).startswith(str(storage_root)):
            range_header = request.headers.get("range")
            if range_header:
                return send_file_range(candidate, range_header)
            return FileResponse(candidate, media_type="video/mp4")
    raise HTTPException(status_code=404, detail="Media file not found")
