import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Publication, SocialAccount, VideoAsset, MediaDerivative

logger = logging.getLogger("studio.publisher")

class PlatformPublisher(ABC):
    @abstractmethod
    def publish(
        self,
        db: Session,
        publication: Publication,
        video_path: Path,
        title: str,
        caption: str,
        description: str,
        tags: str,
    ) -> Dict[str, Any]:
        """
        Publish to the target social platform.
        Returns dict with status, remote_post_id, remote_post_url, error.
        """
        pass


class InstagramPublisher(PlatformPublisher):
    """
    Instagram Reels publisher via official Meta Graph API (graph.instagram.com / graph.facebook.com).
    Uses account-authorized token and temporary hosting/tunnel for local media ingestion.
    """
    def _get_public_video_url(self, video_path: Path, derivative_id: Optional[str]) -> str:
        """
        Obtain a publicly reachable direct HTTPS download URL for Meta ingestion servers.
        Uses Catbox as primary direct CDN hosting, Uguu as secondary fallback, and
        PUBLIC_BASE_URL if explicitly configured by the user.
        """
        # 1. User-configured explicit CDN / external base URL (e.g. custom domain, S3, Cloudflare R2)
        if settings.PUBLIC_BASE_URL:
            clean_base = settings.PUBLIC_BASE_URL.rstrip("/")
            return f"{clean_base}/api/media/stream/{video_path.name}"

        logger.info("Uploading media to high-speed CDN hosting for Meta Reels ingestion: %s", video_path.name)
        safe_name = f"reel_{int(time.time())}.mp4"

        # 2. Primary Direct CDN Hosting: Catbox (proven 100% reliable with Meta Reels API)
        try:
            with open(video_path, "rb") as f:
                res = httpx.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": (safe_name, f, "video/mp4")},
                    timeout=90.0,
                )
                if res.status_code == 200 and res.text.strip().startswith("http"):
                    direct_url = res.text.strip()
                    logger.info("Catbox CDN ingestion URL ready: %s", direct_url)
                    return direct_url
        except Exception as e:
            logger.warning("Catbox upload failed: %s", e)

        # 3. Secondary Direct Hosting: Uguu
        try:
            with open(video_path, "rb") as f:
                res = httpx.post(
                    "https://uguu.se/upload.php",
                    files={"files[]": (safe_name, f, "video/mp4")},
                    timeout=90.0,
                )
                if res.status_code == 200:
                    data = res.json()
                    files_list = data.get("files", [])
                    if files_list and files_list[0].get("url"):
                        direct_url = files_list[0]["url"]
                        logger.info("Uguu ingestion URL ready: %s", direct_url)
                        return direct_url
        except Exception as e:
            logger.warning("Uguu upload failed: %s", e)

        # 4. Fallback to server external URL if available
        if os.environ.get("RENDER_EXTERNAL_URL"):
            clean_base = os.environ.get("RENDER_EXTERNAL_URL").rstrip("/")
            return f"{clean_base}/api/media/stream/{video_path.name}"

        raise ValueError("Could not upload video to direct media hosting for Meta Reels ingestion.")

    def publish(
        self,
        db: Session,
        publication: Publication,
        video_path: Path,
        title: str,
        caption: str,
        description: str,
        tags: str,
    ) -> Dict[str, Any]:
        token = settings.INSTAGRAM_ACCESS_TOKEN
        ig_user_id = settings.INSTAGRAM_ACCOUNT_ID or settings.INSTAGRAM_BUSINESS_ACCOUNT_ID

        # Also check db overrides if stored in Settings
        account = db.query(SocialAccount).filter(SocialAccount.platform == "instagram").first()
        if account and account.credentials_meta.get("access_token"):
            token = account.credentials_meta["access_token"]
        if account and account.account_identifier and account.account_identifier.isdigit():
            ig_user_id = account.account_identifier

        if not token or not ig_user_id:
            return {
                "success": False,
                "error": "Instagram credentials missing. Configure INSTAGRAM_ACCOUNT_ID and INSTAGRAM_ACCESS_TOKEN in .env or Settings.",
            }

        full_caption = caption.strip()
        if tags and tags.strip():
            full_caption += f"\n\n{tags.strip()}"

        try:
            # 1. Obtain public video URL
            video_url = self._get_public_video_url(video_path, publication.derivative_id)
            logger.info("Meta Reels ingestion video URL ready: %s", video_url)

            # 2. Create Reels container (with share_to_feed=true for feed + reels placement)
            container_payload = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": full_caption,
                "share_to_feed": "true",
                "access_token": token,
            }

            api_base = "https://graph.instagram.com/v21.0"
            with httpx.Client(timeout=45.0) as client:
                res = client.post(f"{api_base}/{ig_user_id}/media", data=container_payload)
                if res.status_code != 200:
                    # Fallback to graph.facebook.com endpoint
                    fb_base = "https://graph.facebook.com/v21.0"
                    res_fb = client.post(f"{fb_base}/{ig_user_id}/media", data=container_payload)
                    if res_fb.status_code == 200:
                        res = res_fb
                        api_base = fb_base

                if res.status_code != 200:
                    err_msg = res.json().get("error", {}).get("message", res.text)
                    return {"success": False, "error": f"Instagram container creation error: {err_msg}"}

                creation_id = res.json().get("id")
                if not creation_id:
                    return {"success": False, "error": "Instagram API did not return a media creation container ID."}

                logger.info("Instagram container created: %s. Polling processing status via %s...", creation_id, api_base)

                # 3. Poll container status (Meta processes the video asynchronously)
                status_url = f"{api_base}/{creation_id}?fields=status_code,status&access_token={token}"
                status_code = "IN_PROGRESS"
                max_attempts = 45  # Wait up to 90s
                for attempt in range(max_attempts):
                    time.sleep(2)
                    s_res = client.get(status_url)
                    if s_res.status_code == 200:
                        status_code = s_res.json().get("status_code", "")
                        logger.info("Instagram container %s status: %s (attempt %d/%d)", creation_id, status_code, attempt + 1, max_attempts)
                        if status_code in ("FINISHED", "READY"):
                            break
                        elif status_code == "ERROR":
                            err_info = s_res.json().get("status", "Meta processing error")
                            return {"success": False, "error": f"Instagram failed to process video stream: {err_info}"}

                if status_code not in ("FINISHED", "READY"):
                    return {"success": False, "error": f"Instagram video processing timed out (status: {status_code})."}

                # 4. Publish Reels container (with replication retry if Meta replication is propagating)
                publish_url = f"{api_base}/{ig_user_id}/media_publish"
                pub_res = None
                for pub_attempt in range(5):
                    pub_res = client.post(publish_url, data={"creation_id": creation_id, "access_token": token})
                    if pub_res.status_code == 200:
                        break
                    err_text = pub_res.text.lower()
                    if "not ready" in err_text or "please wait" in err_text:
                        logger.info("Meta media replication propagating, waiting 3s (attempt %d/5)...", pub_attempt + 1)
                        time.sleep(3)
                        continue
                    break

                if not pub_res or pub_res.status_code != 200:
                    err_msg = pub_res.json().get("error", {}).get("message", pub_res.text) if pub_res else "Unknown publish error"
                    return {"success": False, "error": f"Instagram media_publish error: {err_msg}"}

                media_id = pub_res.json().get("id", creation_id)

                # 5. Retrieve real public Instagram permalink & shortcode
                # (Instagram media IDs are numeric; the browser URL requires permalink or shortcode to avoid 404)
                post_url = None
                for _ in range(3):
                    try:
                        meta_query_url = f"{api_base}/{media_id}?fields=permalink,shortcode&access_token={token}"
                        m_res = client.get(meta_query_url, timeout=15.0)
                        if m_res.status_code == 200:
                            m_data = m_res.json()
                            if m_data.get("permalink"):
                                post_url = m_data["permalink"]
                                break
                            elif m_data.get("shortcode"):
                                post_url = f"https://www.instagram.com/reel/{m_data['shortcode']}/"
                                break
                    except Exception as p_err:
                        logger.warning("Could not fetch permalink for IG media %s: %s", media_id, p_err)
                    time.sleep(1)

                if not post_url:
                    post_url = f"https://www.instagram.com/reel/{media_id}/"

                logger.info("Instagram Reel published successfully! Media ID: %s, URL: %s", media_id, post_url)

                return {
                    "success": True,
                    "remote_post_id": media_id,
                    "remote_post_url": post_url,
                }

        except Exception as e:
            logger.error("Instagram Reels publishing exception: %s", e)
            return {"success": False, "error": str(e)}


class YouTubePublisher(PlatformPublisher):
    """
    YouTube Shorts direct uploader via official YouTube Data API v3 with OAuth 2.0.
    Ensures strict YouTube Shorts qualification:
    - #Shorts enforced in Title (<= 100 chars)
    - #Shorts prepended to Description
    - Shorts / YouTube Shorts tags included
    - Privacy status public with direct https://youtube.com/shorts/{id} permalink
    """
    def _get_access_token(self) -> str:
        client_id = settings.YOUTUBE_CLIENT_ID
        client_secret = settings.YOUTUBE_CLIENT_SECRET
        refresh_token = settings.YOUTUBE_REFRESH_TOKEN

        if not client_id or not client_secret or not refresh_token:
            raise ValueError("YouTube OAuth credentials missing in .env (YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN).")

        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        with httpx.Client(timeout=15.0) as client:
            res = client.post(token_url, data=payload)
            if res.status_code != 200:
                raise ValueError(f"Failed to refresh YouTube access token ({res.status_code}): {res.text}")
            token = res.json().get("access_token")
            if not token:
                raise ValueError("No access token returned from Google OAuth token endpoint.")
            return token

    def publish(
        self,
        db: Session,
        publication: Publication,
        video_path: Path,
        title: str,
        caption: str,
        description: str,
        tags: str,
    ) -> Dict[str, Any]:
        try:
            access_token = self._get_access_token()
            file_size = video_path.stat().st_size

            # Parse and normalize tags: enforce Shorts tags
            tag_list = [t.strip().lstrip("#") for t in tags.split(",") if t.strip()]
            for st in ["Shorts", "YouTube Shorts"]:
                if st.lower() not in [t.lower() for t in tag_list]:
                    tag_list.insert(0, st)

            # Enforce #Shorts in Title (max 100 characters in YouTube)
            clean_title = (title.strip() or video_path.name.rsplit(".", 1)[0])
            clean_title = clean_title.replace("\n", " ").strip()
            if "#shorts" not in clean_title.lower():
                if len(clean_title) > 85:
                    clean_title = clean_title[:85].rstrip()
                clean_title = f"{clean_title} #Shorts"
            clean_title = clean_title[:100]

            # Enforce #Shorts in Description
            base_desc = (description.strip() or caption.strip() or clean_title)
            if "#shorts" not in base_desc.lower():
                clean_desc = f"#Shorts\n\n{base_desc}\n\n#YouTubeShorts #Trending"
            else:
                clean_desc = base_desc

            metadata = {
                "snippet": {
                    "title": clean_title,
                    "description": clean_desc,
                    "tags": tag_list,
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }

            # 1. Initiate Resumable Upload
            init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(file_size),
            }

            with httpx.Client(timeout=120.0) as client:
                init_res = client.post(init_url, json=metadata, headers=headers)
                if init_res.status_code not in (200, 201):
                    err_msg = init_res.json().get("error", {}).get("message", init_res.text)
                    return {"success": False, "error": f"YouTube upload init failed: {err_msg}"}

                upload_url = init_res.headers.get("Location")
                if not upload_url:
                    return {"success": False, "error": "Google API did not return upload Location header."}

                logger.info("YouTube resumable upload initiated for %s (%d bytes). Streaming...", clean_title, file_size)

                # 2. Upload video payload
                with open(video_path, "rb") as video_file:
                    upload_res = client.put(
                        upload_url,
                        content=video_file.read(),
                        headers={"Content-Type": "video/mp4"},
                    )

                if upload_res.status_code not in (200, 201):
                    err_msg = upload_res.json().get("error", {}).get("message", upload_res.text)
                    return {"success": False, "error": f"YouTube video stream upload failed: {err_msg}"}

                video_id = upload_res.json().get("id")
                if not video_id:
                    return {"success": False, "error": "YouTube upload completed but no video ID returned."}

                post_url = f"https://youtube.com/shorts/{video_id}"
                logger.info("YouTube Short successfully uploaded! ID: %s, URL: %s", video_id, post_url)

                return {
                    "success": True,
                    "remote_post_id": video_id,
                    "remote_post_url": post_url,
                }

        except Exception as e:
            logger.error("YouTube publish exception: %s", e)
            return {"success": False, "error": str(e)}


class SocialPublishingService:
    def __init__(self):
        self.instagram = InstagramPublisher()
        self.youtube = YouTubePublisher()

    def execute_publication(self, db: Session, publication_id: str) -> Publication:
        pub = db.query(Publication).filter(Publication.id == publication_id).first()
        if not pub:
            raise ValueError(f"Publication not found: {publication_id}")

        if pub.status == "published":
            # Idempotency: avoid duplicate posts
            return pub

        pub.status = "publishing"
        pub.attempts += 1
        db.commit()

        # Locate media file
        video_path = None
        if pub.derivative and Path(pub.derivative.local_path).exists():
            video_path = Path(pub.derivative.local_path)
        elif pub.video_asset and Path(pub.video_asset.original_local_path).exists():
            video_path = Path(pub.video_asset.original_local_path)

        if not video_path:
            pub.status = "failed"
            pub.error_details = "Media file for publication could not be found on local storage."
            db.commit()
            return pub

        # Retrieve draft copy
        draft = None
        for d in pub.video_asset.drafts:
            if d.platform == pub.platform:
                draft = d
                break

        title = draft.title if draft else pub.video_asset.filename
        caption = draft.caption if draft else ""
        description = draft.description if draft else ""
        tags = draft.hashtags if draft else ""

        publisher = self.instagram if pub.platform == "instagram" else self.youtube
        result = publisher.publish(db, pub, video_path, title, caption, description, tags)

        if result.get("success"):
            pub.status = "published"
            pub.remote_post_id = result.get("remote_post_id")
            pub.remote_post_url = result.get("remote_post_url")
            pub.error_details = None
        else:
            pub.status = "failed"
            pub.error_details = result.get("error", "Unknown publishing error")

        pub.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(pub)
        return pub

social_service = SocialPublishingService()
