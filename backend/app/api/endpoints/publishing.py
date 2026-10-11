import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.models import VideoAsset, MediaDerivative, Publication
from app.schemas.schemas import (
    PublishRequest,
    PublicationResponse,
    MessageResponse,
)
from app.services.publisher import social_service

router = APIRouter(prefix="/publications", tags=["Publishing"])

@router.post("", response_model=List[PublicationResponse])
def create_publication(req: PublishRequest, db: Session = Depends(get_db)):
    video = db.query(VideoAsset).filter(VideoAsset.id == req.video_asset_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video asset not found")

    if not req.platforms:
        raise HTTPException(status_code=400, detail="At least one platform (instagram, youtube) must be selected.")

    created_publications = []
    is_scheduled = req.schedule_time is not None

    for platform in req.platforms:
        if platform not in ("instagram", "youtube"):
            continue

        # Generate idempotency key
        key = f"{req.video_asset_id}_{platform}_{int(datetime.now(timezone.utc).timestamp())}"

        pub = Publication(
            id=str(uuid.uuid4()),
            video_asset_id=req.video_asset_id,
            derivative_id=req.derivative_id,
            platform=platform,
            scheduled_time=req.schedule_time,
            status="scheduled" if is_scheduled else "publishing",
            idempotency_key=key,
        )
        db.add(pub)
        db.commit()
        db.refresh(pub)

        if not is_scheduled:
            # Immediate execution
            pub = social_service.execute_publication(db, pub.id)

        created_publications.append(pub)

    return created_publications

@router.get("", response_model=List[PublicationResponse])
def list_publications(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: Optional[str] = Query(None, description="Filter by status: draft, scheduled, publishing, published, failed"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Publication)
    if platform:
        q = q.filter(Publication.platform == platform)
    if status:
        q = q.filter(Publication.status == status)

    return q.order_by(desc(Publication.created_at)).offset(skip).limit(limit).all()

@router.post("/{pub_id}/retry", response_model=PublicationResponse)
def retry_publication(pub_id: str, db: Session = Depends(get_db)):
    pub = db.query(Publication).filter(Publication.id == pub_id).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication record not found")

    if pub.status == "published":
        raise HTTPException(status_code=400, detail="This publication has already been successfully published.")

    updated_pub = social_service.execute_publication(db, pub.id)
    return updated_pub

@router.delete("/{pub_id}/cancel", response_model=MessageResponse)
def cancel_publication(pub_id: str, db: Session = Depends(get_db)):
    pub = db.query(Publication).filter(Publication.id == pub_id).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication record not found")

    if pub.status == "published":
        raise HTTPException(status_code=400, detail="Cannot cancel an already published post.")

    pub.status = "draft"
    pub.scheduled_time = None
    db.commit()
    return MessageResponse(message="Scheduled post cancelled.")
