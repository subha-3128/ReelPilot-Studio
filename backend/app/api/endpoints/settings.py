import shutil
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import AppSetting, SocialAccount
from app.schemas.schemas import (
    AppSettingsResponse,
    AppSettingsUpdateRequest,
    SocialAccountResponse,
    ConnectAccountRequest,
    MessageResponse,
)
from app.services.media import media_service
from app.services.downloader import downloader_service

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=AppSettingsResponse)
def get_app_settings(db: Session = Depends(get_db)):
    # Read storage directory override from db if configured
    storage_setting = db.query(AppSetting).filter(AppSetting.key == "storage_dir").first()
    if storage_setting and storage_setting.value:
        try:
            custom_dir = Path(storage_setting.value).expanduser().resolve()
            settings.set_storage_dir(custom_dir)
        except Exception:
            pass

    # Calculate free disk space in GB for active storage root
    total, used, free = shutil.disk_usage(settings.STORAGE_DIR)
    free_gb = round(free / (1024 ** 3), 2)

    tools = media_service.check_tools()

    # Read overrides from db
    tz_setting = db.query(AppSetting).filter(AppSetting.key == "timezone").first()
    tz_val = tz_setting.value if tz_setting else settings.DEFAULT_TIMEZONE

    policy_setting = db.query(AppSetting).filter(AppSetting.key == "default_sync_policy").first()
    policy_val = policy_setting.value if policy_setting else settings.DEFAULT_SYNC_POLICY

    font_size_setting = db.query(AppSetting).filter(AppSetting.key == "subtitle_font_size").first()
    font_size_val = int(font_size_setting.value) if font_size_setting else settings.DEFAULT_SUBTITLE_FONT_SIZE

    font_color_setting = db.query(AppSetting).filter(AppSetting.key == "subtitle_font_color").first()
    font_color_val = font_color_setting.value if font_color_setting else settings.DEFAULT_SUBTITLE_FONT_COLOR

    return AppSettingsResponse(
        storage_dir=str(settings.STORAGE_DIR),
        free_disk_space_gb=free_gb,
        timezone=tz_val,
        default_sync_policy=policy_val,
        subtitle_font_size=font_size_val,
        subtitle_font_color=font_color_val,
        ffmpeg_available=tools["ffmpeg"],
        ytdlp_available=downloader_service.is_available(),
    )

@router.put("", response_model=MessageResponse)
def update_app_settings(req: AppSettingsUpdateRequest, db: Session = Depends(get_db)):
    if req.storage_dir:
        clean_dir = req.storage_dir.strip()
        try:
            target_path = Path(clean_dir).expanduser().resolve()
            target_path.mkdir(parents=True, exist_ok=True)
            settings.set_storage_dir(target_path)

            setting = db.query(AppSetting).filter(AppSetting.key == "storage_dir").first()
            if not setting:
                setting = AppSetting(key="storage_dir", value=str(target_path))
                db.add(setting)
            else:
                setting.value = str(target_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid storage directory '{clean_dir}': {e}")

    if req.timezone:
        setting = db.query(AppSetting).filter(AppSetting.key == "timezone").first()
        if not setting:
            setting = AppSetting(key="timezone", value=req.timezone)
            db.add(setting)
        else:
            setting.value = req.timezone

    if req.default_sync_policy:
        setting = db.query(AppSetting).filter(AppSetting.key == "default_sync_policy").first()
        if not setting:
            setting = AppSetting(key="default_sync_policy", value=req.default_sync_policy)
            db.add(setting)
        else:
            setting.value = req.default_sync_policy

    if req.subtitle_font_size is not None:
        setting = db.query(AppSetting).filter(AppSetting.key == "subtitle_font_size").first()
        if not setting:
            setting = AppSetting(key="subtitle_font_size", value=str(req.subtitle_font_size))
            db.add(setting)
        else:
            setting.value = str(req.subtitle_font_size)

    if req.subtitle_font_color is not None:
        setting = db.query(AppSetting).filter(AppSetting.key == "subtitle_font_color").first()
        if not setting:
            setting = AppSetting(key="subtitle_font_color", value=str(req.subtitle_font_color))
            db.add(setting)
        else:
            setting.value = str(req.subtitle_font_color)

    db.commit()
    return MessageResponse(message="Settings saved successfully.")

@router.get("/accounts", response_model=List[SocialAccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(SocialAccount).all()
    existing_platforms = {a.platform for a in accounts}
    for plat in ["instagram", "youtube"]:
        if plat not in existing_platforms:
            is_env_connected = False
            acc_name = "Not connected"
            acc_id = ""
            if plat == "instagram" and settings.INSTAGRAM_ACCESS_TOKEN:
                is_env_connected = True
                acc_name = "liz_yarr (Env Configured)"
                acc_id = settings.INSTAGRAM_ACCOUNT_ID or settings.INSTAGRAM_BUSINESS_ACCOUNT_ID or ""
            elif plat == "youtube" and settings.YOUTUBE_REFRESH_TOKEN:
                is_env_connected = True
                acc_name = "YouTube Studio (Env Configured)"
                acc_id = settings.YOUTUBE_CLIENT_ID or ""

            new_acc = SocialAccount(
                id=str(uuid.uuid4()),
                platform=plat,
                account_identifier=acc_id,
                account_name=acc_name,
                connection_status="connected" if is_env_connected else "disconnected",
                scopes="publish_video" if is_env_connected else "",
                credentials_meta={},
            )
            db.add(new_acc)
            db.commit()
        else:
            acc = next(a for a in accounts if a.platform == plat)
            if plat == "instagram" and settings.INSTAGRAM_ACCESS_TOKEN and acc.connection_status != "connected":
                acc.connection_status = "connected"
                acc.account_name = "liz_yarr (Env Configured)" if acc.account_name == "Not connected" else acc.account_name
                acc.account_identifier = acc.account_identifier or settings.INSTAGRAM_ACCOUNT_ID or settings.INSTAGRAM_BUSINESS_ACCOUNT_ID or ""
                db.commit()
            elif plat == "youtube" and settings.YOUTUBE_REFRESH_TOKEN and acc.connection_status != "connected":
                acc.connection_status = "connected"
                acc.account_name = "YouTube Studio (Env Configured)" if acc.account_name == "Not connected" else acc.account_name
                acc.account_identifier = acc.account_identifier or settings.YOUTUBE_CLIENT_ID or ""
                db.commit()

    return db.query(SocialAccount).all()

@router.post("/accounts/connect", response_model=SocialAccountResponse)
def connect_account(req: ConnectAccountRequest, db: Session = Depends(get_db)):
    account = db.query(SocialAccount).filter(SocialAccount.platform == req.platform).first()
    if not account:
        account = SocialAccount(
            id=str(uuid.uuid4()),
            platform=req.platform,
        )
        db.add(account)

    account.account_identifier = req.account_identifier or f"{req.platform}_user"
    account.account_name = req.account_name or f"Connected {req.platform.title()}"
    account.connection_status = "connected"
    if req.access_token:
        account.credentials_meta = {"access_token": req.access_token}

    db.commit()
    db.refresh(account)
    return account
