import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import VideoAsset, VoiceoverAsset, MediaDerivative, Transcript
from app.schemas.schemas import (
    VoiceoverAssetResponse,
    MediaDerivativeResponse,
    VoiceoverSyncRequest,
    TranscriptResponse,
    TranscriptUpdateRequest,
    BurnSubtitlesRequest,
    ExportRequest,
)
from app.services.media import media_service
from app.services.transcription import transcription_service

router = APIRouter(prefix="/studio", tags=["Studio"])

@router.post("/upload-voiceover", response_model=VoiceoverAssetResponse)
async def upload_voiceover(
    video_asset_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    video = db.query(VideoAsset).filter(VideoAsset.id == video_asset_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video asset not found")

    vo_id = str(uuid.uuid4())
    upload_ext = Path(file.filename or "voiceover.mp4").suffix or ".mp4"
    saved_upload_path = settings.VOICEOVERS_DIR / f"{vo_id}_raw{upload_ext}"

    # Stream file to disk
    with open(saved_upload_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Validate container and audio stream with FFprobe
    meta = media_service.probe(saved_upload_path)
    if not meta.get("has_audio"):
        saved_upload_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="The uploaded file does not contain an audio track. Please upload an MP4 or audio file with valid audio.",
        )

    # Extract audio stream to high-quality M4A/AAC
    extracted_audio_path = settings.VOICEOVERS_DIR / f"{vo_id}_extracted.m4a"
    media_service.extract_audio_from_mp4(saved_upload_path, extracted_audio_path)

    audio_meta = media_service.probe(extracted_audio_path)

    vo_asset = VoiceoverAsset(
        id=vo_id,
        video_asset_id=video_asset_id,
        source_upload_path=str(saved_upload_path),
        extracted_audio_path=str(extracted_audio_path),
        filename=file.filename or f"voiceover_{vo_id[:8]}.mp4",
        duration=audio_meta.get("duration", meta.get("duration", 0.0)),
        file_size=saved_upload_path.stat().st_size,
    )
    db.add(vo_asset)
    db.commit()
    db.refresh(vo_asset)

    return vo_asset

@router.post("/sync-voiceover", response_model=MediaDerivativeResponse)
def sync_voiceover(req: VoiceoverSyncRequest, db: Session = Depends(get_db)):
    video = db.query(VideoAsset).filter(VideoAsset.id == req.video_asset_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video asset not found")

    vo = db.query(VoiceoverAsset).filter(VoiceoverAsset.id == req.voiceover_asset_id).first()
    if not vo:
        raise HTTPException(status_code=404, detail="Voice-over asset not found")

    derivative_id = str(uuid.uuid4())
    out_video_path = settings.DERIVATIVES_DIR / f"{derivative_id}_synced.mp4"
    thumb_path = settings.THUMBNAILS_DIR / f"{derivative_id}.jpg"

    sync_result = media_service.process_voiceover_sync(
        source_video_path=Path(video.original_local_path),
        extracted_audio_path=Path(vo.extracted_audio_path),
        output_derivative_path=out_video_path,
        sync_policy=req.sync_policy,
        mute_original_audio=req.mute_original_audio,
        start_offset=req.start_offset_seconds,
        audio_trim=req.audio_trim_seconds,
        background_ambience_volume=req.background_ambience_volume,
    )

    media_service.generate_thumbnail(out_video_path, thumb_path)

    derivative = MediaDerivative(
        id=derivative_id,
        video_asset_id=video.id,
        derivative_type="voiceover_synced",
        local_path=str(out_video_path),
        thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
        duration=sync_result["duration"],
        width=sync_result["width"],
        height=sync_result["height"],
        file_size=sync_result["file_size"],
        settings={
            "sync_policy": req.sync_policy,
            "mute_original_audio": req.mute_original_audio,
            "start_offset": req.start_offset_seconds,
            "warning": sync_result.get("warning"),
        },
    )
    db.add(derivative)
    db.commit()
    db.refresh(derivative)

    return derivative

@router.get("/{asset_id}/transcript", response_model=TranscriptResponse)
def get_or_create_transcript(
    asset_id: str,
    voiceover_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    video = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video asset not found")

    # Check existing transcript
    trans = db.query(Transcript).filter(Transcript.video_asset_id == asset_id).first()
    if trans:
        return trans

    # If no transcript exists, transcribe from voiceover if available, or generate initial template
    audio_path = None
    if voiceover_id:
        vo = db.query(VoiceoverAsset).filter(VoiceoverAsset.id == voiceover_id).first()
        if vo and Path(vo.extracted_audio_path).exists():
            audio_path = Path(vo.extracted_audio_path)
    elif video.voiceovers:
        audio_path = Path(video.voiceovers[0].extracted_audio_path)

    if not audio_path or not audio_path.exists():
        # Fall back to video's own path if no voiceover
        audio_path = Path(video.original_local_path)

    segments = transcription_service.transcribe_audio(audio_path, language="en")
    full_text = " ".join(seg.get("text", "") for seg in segments)

    trans = Transcript(
        id=str(uuid.uuid4()),
        video_asset_id=asset_id,
        provider=transcription_service.provider.provider_name(),
        source_lang="en",
        target_lang="en",
        full_text=full_text,
        segments=segments,
    )
    db.add(trans)
    db.commit()
    db.refresh(trans)
    return trans

@router.put("/{asset_id}/transcript", response_model=TranscriptResponse)
def update_transcript(
    asset_id: str,
    req: TranscriptUpdateRequest,
    db: Session = Depends(get_db),
):
    trans = db.query(Transcript).filter(Transcript.video_asset_id == asset_id).first()
    if not trans:
        raise HTTPException(status_code=404, detail="Transcript not found")

    trans.segments = [seg.model_dump() for seg in req.segments]
    trans.full_text = " ".join(seg.text for seg in req.segments)
    db.commit()
    db.refresh(trans)
    return trans

@router.post("/burn-subtitles", response_model=MediaDerivativeResponse)
def burn_subtitles(req: BurnSubtitlesRequest, db: Session = Depends(get_db)):
    video = db.query(VideoAsset).filter(VideoAsset.id == req.video_asset_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video asset not found")

    # Pick input video: requested derivative, or latest synced derivative, or original
    source_video_path = Path(video.original_local_path)
    if req.derivative_id:
        deriv = db.query(MediaDerivative).filter(MediaDerivative.id == req.derivative_id).first()
        if deriv and Path(deriv.local_path).exists():
            source_video_path = Path(deriv.local_path)
    elif video.derivatives:
        source_video_path = Path(video.derivatives[-1].local_path)

    # Fetch transcript
    trans = db.query(Transcript).filter(Transcript.video_asset_id == req.video_asset_id).first()
    if not trans or not trans.segments:
        raise HTTPException(status_code=400, detail="No transcript available to burn subtitles from.")

    # Write temporary SRT file
    sub_id = str(uuid.uuid4())
    srt_path = settings.TEMP_DIR / f"{sub_id}.srt"
    transcription_service.write_srt_file(trans.segments, srt_path)

    out_path = settings.DERIVATIVES_DIR / f"{sub_id}_captioned.mp4"
    thumb_path = settings.THUMBNAILS_DIR / f"{sub_id}.jpg"

    media_service.burn_subtitles(
        video_path=source_video_path,
        srt_path=srt_path,
        output_path=out_path,
        font_size=req.font_size,
        font_color=req.font_color,
        outline_color=req.outline_color,
        outline_width=req.outline_width,
    )
    media_service.generate_thumbnail(out_path, thumb_path)

    meta = media_service.probe(out_path)
    derivative = MediaDerivative(
        id=sub_id,
        video_asset_id=video.id,
        derivative_type="captioned",
        local_path=str(out_path),
        thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
        duration=meta["duration"],
        width=meta["width"],
        height=meta["height"],
        file_size=meta["file_size"],
        settings={
            "font_size": req.font_size,
            "font_color": req.font_color,
        },
    )
    db.add(derivative)
    db.commit()
    db.refresh(derivative)

    return derivative

@router.post("/export", response_model=MediaDerivativeResponse)
def export_derivative(req: ExportRequest, db: Session = Depends(get_db)):
    video = db.query(VideoAsset).filter(VideoAsset.id == req.video_asset_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video asset not found")

    target_deriv = None
    if req.derivative_id:
        target_deriv = db.query(MediaDerivative).filter(MediaDerivative.id == req.derivative_id).first()
    elif video.derivatives:
        target_deriv = video.derivatives[-1]

    if not target_deriv or not Path(target_deriv.local_path).exists():
        raise HTTPException(status_code=400, detail="No processed derivative found to export.")

    # Create export entry
    export_id = str(uuid.uuid4())
    export_filename = f"export_{export_id[:8]}_{video.filename}"
    export_path = settings.DERIVATIVES_DIR / export_filename

    # Copy to designated export location
    import shutil
    shutil.copy2(target_deriv.local_path, export_path)

    meta = media_service.probe(export_path)
    thumb_path = settings.THUMBNAILS_DIR / f"{export_id}.jpg"
    media_service.generate_thumbnail(export_path, thumb_path)

    derivative = MediaDerivative(
        id=export_id,
        video_asset_id=video.id,
        derivative_type="final_export",
        local_path=str(export_path),
        thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
        duration=meta["duration"],
        width=meta["width"],
        height=meta["height"],
        file_size=meta["file_size"],
        settings={"source_derivative_id": target_deriv.id},
    )
    db.add(derivative)
    db.commit()
    db.refresh(derivative)

    return derivative
