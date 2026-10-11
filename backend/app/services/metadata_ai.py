import json
import logging
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("studio.metadata_ai")

class MetadataAssistantService:
    def generate_drafts(
        self,
        filename: str,
        transcript_text: str = "",
        tone: str = "engaging",
        include_hashtags: bool = True,
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate platform-specific drafts for Instagram Reels and YouTube Shorts/Videos.
        Uses Google Gemini AI (gemini-3.8-flash) if key configured, otherwise smart template fallback.
        """
        clean_name = filename.rsplit(".", 1)[0].replace("_", " ").title()
        snippet = transcript_text[:1000].strip() if transcript_text else ""

        # Attempt live Gemini AI generation
        if settings.GEMINI_API_KEY:
            try:
                gemini_drafts = self._generate_with_gemini(clean_name, snippet, tone, include_hashtags)
                if gemini_drafts:
                    return gemini_drafts
            except Exception as e:
                logger.warning("Gemini AI generation failed, falling back to local templates: %s", e)

        # Smart fallback template
        theme = snippet if snippet else f"Exciting moments from {clean_name}"
        ig_caption = f"Check out this moment! 🎬✨\n\n{theme}\n\nWhat are your thoughts on this? Drop a comment below! 👇"
        ig_hashtags = "#reels #trending #viralvideo #videooftheday #creator #kuaishou" if include_hashtags else ""

        yt_title = f"{clean_name} — English Voice-Over Edition"
        if len(yt_title) > 95:
            yt_title = yt_title[:92] + "..."

        yt_description = (
            f"{theme}\n\n"
            "Official English Voice-Over Edition.\n"
            "Subscribe for more translated and dubbed creator content!\n\n"
            "#Shorts #YouTubeVideo #CreatorHighlights"
        )
        yt_tags = "trending, video, shorts, creator, voiceover, highlights"

        return {
            "instagram": {
                "title": "",
                "caption": ig_caption,
                "description": "",
                "hashtags": ig_hashtags,
            },
            "youtube": {
                "title": yt_title,
                "caption": "",
                "description": yt_description,
                "hashtags": yt_tags,
            },
        }

    def _generate_with_gemini(
        self,
        title: str,
        transcript: str,
        tone: str,
        include_hashtags: bool,
    ) -> Optional[Dict[str, Dict[str, str]]]:
        model = settings.GEMINI_MODEL or "gemini-3.8-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"

        prompt = (
            f"You are a professional social media manager for short-form viral videos. "
            f"Video Title/Subject: '{title}'.\n"
            f"English Voice-Over Transcript: '{transcript or 'A captivating creator short video.'}'\n"
            f"Desired Tone: '{tone}'.\n\n"
            f"Generate publishing copy tailored for Instagram Reels and YouTube Shorts.\n"
            f"Return ONLY valid JSON with no markdown formatting or backticks, with this exact structure:\n"
            f"{{\n"
            f'  "instagram": {{\n'
            f'    "caption": "engaging Instagram caption with hook and call to action",\n'
            f'    "hashtags": "#reels #trending #relevant_tags"\n'
            f"  }},\n"
            f'  "youtube": {{\n'
            f'    "title": "catchy YouTube title under 90 chars",\n'
            f'    "description": "engaging description with hashtags at the bottom",\n'
            f'    "hashtags": "tag1, tag2, tag3"\n'
            f"  }}\n"
            f"}}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000},
        }

        with httpx.Client(timeout=20.0) as client:
            res = client.post(url, json=payload)
            if res.status_code != 200:
                logger.error("Gemini returned %d: %s", res.status_code, res.text)
                return None

            data = res.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None

            raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
            # Clean possible markdown block wrappers
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
                if raw_text.endswith("```"):
                    raw_text = raw_text.rsplit("```", 1)[0]
                raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            return {
                "instagram": {
                    "title": "",
                    "caption": parsed.get("instagram", {}).get("caption", ""),
                    "description": "",
                    "hashtags": parsed.get("instagram", {}).get("hashtags", "") if include_hashtags else "",
                },
                "youtube": {
                    "title": parsed.get("youtube", {}).get("title", f"{title} | English Edition"),
                    "caption": "",
                    "description": parsed.get("youtube", {}).get("description", ""),
                    "hashtags": parsed.get("youtube", {}).get("hashtags", ""),
                },
            }

metadata_service = MetadataAssistantService()
