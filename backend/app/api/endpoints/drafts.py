import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import VideoAsset, ContentDraft, Transcript
from app.schemas.schemas import (
    ContentDraftResponse,
    DraftUpdateRequest,
    GenerateMetadataRequest,
)
from app.services.metadata_ai import metadata_service

router = APIRouter(prefix="/drafts", tags=["Drafts"])

@router.get("/{asset_id}", response_model=List[ContentDraftResponse])
def get_drafts(asset_id: str, db: Session = Depends(get_db)):
    video = db.query(VideoAsset).filter(VideoAsset.id == asset_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video asset not found")

    drafts = db.query(ContentDraft).filter(ContentDraft.video_asset_id == asset_id).all()
    if not drafts:
        # Generate initial defaults
        draft_dict = metadata_service.generate_drafts(filename=video.filename)
        for platform, data in draft_dict.items():
            new_draft = ContentDraft(
                id=str(uuid.uuid4()),
                video_asset_id=asset_id,
                platform=platform,
                title=data.get("title", ""),
                caption=data.get("caption", ""),
                description=data.get("description", ""),
                hashtags=data.get("hashtags", ""),
                generation_source="default_template",
            )
            db.add(new_draft)
        db.commit()
        drafts = db.query(ContentDraft).filter(ContentDraft.video_asset_id == asset_id).all()

    return drafts

@router.put("/{asset_id}", response_model=ContentDraftResponse)
def update_draft(asset_id: str, req: DraftUpdateRequest, db: Session = Depends(get_db)):
    draft = (
        db.query(ContentDraft)
        .filter(ContentDraft.video_asset_id == asset_id, ContentDraft.platform == req.platform)
        .first()
    )
    if not draft:
        draft = ContentDraft(
            id=str(uuid.uuid4()),
            video_asset_id=asset_id,
            platform=req.platform,
        )
        db.add(draft)

    if req.title is not None:
        draft.title = req.title
    if req.caption is not None:
        draft.caption = req.caption
    if req.description is not None:
        draft.description = req.description
    if req.hashtags is not None:
        draft.hashtags = req.hashtags

    draft.generation_source = "user_edit"
    db.commit()
    db.refresh(draft)
    return draft

@router.post("/generate", response_model=List[ContentDraftResponse])
def generate_drafts(req: GenerateMetadataRequest, db: Session = Depends(get_db)):
    video = db.query(VideoAsset).filter(VideoAsset.id == req.video_asset_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video asset not found")

    trans = db.query(Transcript).filter(Transcript.video_asset_id == req.video_asset_id).first()
    transcript_text = trans.full_text if trans else ""

    generated = metadata_service.generate_drafts(
        filename=video.filename,
        transcript_text=transcript_text,
        tone=req.tone or "engaging",
        include_hashtags=req.include_hashtags,
    )

    results = []
    for platform in req.platforms:
        if platform not in generated:
            continue
        data = generated[platform]
        draft = (
            db.query(ContentDraft)
            .filter(ContentDraft.video_asset_id == req.video_asset_id, ContentDraft.platform == platform)
            .first()
        )
        if not draft:
            draft = ContentDraft(
                id=str(uuid.uuid4()),
                video_asset_id=req.video_asset_id,
                platform=platform,
            )
            db.add(draft)

        draft.title = data.get("title", draft.title)
        draft.caption = data.get("caption", draft.caption)
        draft.description = data.get("description", draft.description)
        draft.hashtags = data.get("hashtags", draft.hashtags)
        draft.generation_source = "ai_suggested"
        db.commit()
        db.refresh(draft)
        results.append(draft)

    return results
