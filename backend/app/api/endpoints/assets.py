import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.models import VideoAsset, MediaDerivative, ProcessingJob
from app.schemas.schemas import (
    VideoAssetResponse,
    VideoAssetDetailResponse,
    DownloadRequest,
    DownloadInspectResponse,
    MessageResponse,
)
from app.services.downloader import downloader_service

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.get("", response_model=List[VideoAssetResponse])
def list_assets(
    query: Optional[str] = Query(None, description="Search term in filename or URL"),
    filter_status: Optional[str] = Query(None, description="Filter: all, has_voiceover, has_derivatives"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(VideoAsset)
    if query:
        q = q.filter(
            (VideoAsset.filename.ilike(f"%{query}%")) |
            (VideoAsset.original_source_url.ilike(f"%{query}%"))
        )
    if filter_status == "has_voiceover":
        q = q.filter(VideoAsset.voiceovers.any())
    elif filter_status == "has_derivatives":
        q = q.filter(VideoAsset.derivatives.any())

    return q.order_by(desc(VideoAsset.created_at)).offset(skip).limit(limit).all()

@router.get("/{asset_id}", response_model=VideoAssetDetailResponse)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset not found")
    return asset

@router.post("/inspect", response_model=DownloadInspectResponse)
def inspect_url(req: DownloadRequest, db: Session = Depends(get_db)):
    return downloader_service.inspect_url(db, req.url)

@router.post("/download", response_model=VideoAssetResponse)
def download_asset(req: DownloadRequest, db: Session = Depends(get_db)):
    return downloader_service.download_video(
        db=db,
        url=req.url,
        rights_acknowledged=req.rights_acknowledged,
    )

@router.delete("/{asset_id}", response_model=MessageResponse)
def delete_asset(
    asset_id: str,
    delete_files: bool = Query(True, description="Delete files from disk"),
    db: Session = Depends(get_db),
):
    asset = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset not found")

    if delete_files:
        # Remove original file
        if Path(asset.original_local_path).exists():
            Path(asset.original_local_path).unlink(missing_ok=True)
        if asset.thumbnail_path and Path(asset.thumbnail_path).exists():
            Path(asset.thumbnail_path).unlink(missing_ok=True)
        # Remove derivative files
        for deriv in asset.derivatives:
            if Path(deriv.local_path).exists():
                Path(deriv.local_path).unlink(missing_ok=True)
        # Remove voiceover files
        for vo in asset.voiceovers:
            if Path(vo.source_upload_path).exists():
                Path(vo.source_upload_path).unlink(missing_ok=True)
            if Path(vo.extracted_audio_path).exists():
                Path(vo.extracted_audio_path).unlink(missing_ok=True)

    db.delete(asset)
    db.commit()
    return MessageResponse(message="Video asset and associated records removed successfully.")

@router.delete("/{asset_id}/derivatives/{derivative_id}", response_model=MessageResponse)
def delete_derivative(
    asset_id: str,
    derivative_id: str,
    db: Session = Depends(get_db),
):
    deriv = db.query(MediaDerivative).filter(
        MediaDerivative.id == derivative_id,
        MediaDerivative.video_asset_id == asset_id,
    ).first()
    if not deriv:
        raise HTTPException(status_code=404, detail="Media derivative not found")

    # Delete derivative file, keeping original intact
    if Path(deriv.local_path).exists():
        Path(deriv.local_path).unlink(missing_ok=True)
    if deriv.thumbnail_path and Path(deriv.thumbnail_path).exists():
        Path(deriv.thumbnail_path).unlink(missing_ok=True)

    db.delete(deriv)
    db.commit()
    return MessageResponse(message="Derivative deleted. Original video remains untouched.")
