import json
import logging
import re
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings

logger = logging.getLogger("studio.metadata_ai")

class MetadataAssistantService:
    def clean_title(self, filename: str) -> str:
        """Strip internal UUID prefix and extension, returning a clean, human-readable title."""
        if not filename:
            return "Viral Highlights"
        # Strip UUID or hex prefixes (e.g. 12345678-1234-1234-1234-123456789012_ or 8 to 36-char hex prefix)
        raw = re.sub(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}_?", "", filename)
        raw = re.sub(r"^[0-9a-fA-F\-]{8,36}_", "", raw)
        base = raw.rsplit(".", 1)[0]
        cleaned = base.replace("_", " ").replace("-", " ").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        # Check if too short, generic, or just a hex/id hash
        if not cleaned or len(cleaned) <= 2 or re.match(r"^[0-9a-fA-F]+$", cleaned):
            return "Viral Highlights"
        return cleaned.title()

    def clean_transcript(self, transcript_text: str) -> str:
        """Filter out synthetic placeholder segments or dummy commentary markers."""
        if not transcript_text:
            return ""
        low = transcript_text.lower()
        if "voice-over commentary segment" in low or "commentary segment" in low or "[cue" in low or "[segment" in low:
            return ""
        cleaned = transcript_text.strip()
        return cleaned if len(cleaned) >= 6 else ""

    def generate_drafts(
        self,
        filename: str,
        transcript_text: str = "",
        tone: str = "engaging",
        include_hashtags: bool = True,
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate platform-specific drafts for Instagram Reels and YouTube Shorts.
        Uses Google Gemini AI if configured with automatic model fallbacks,
        otherwise uses an executive smart copywriting engine.
        """
        title = self.clean_title(filename)
        cleaned_transcript = self.clean_transcript(transcript_text)
        tone_normalized = tone.lower().strip() if tone else "engaging"

        # 1. Attempt live Google Gemini AI generation if key is provided
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 5:
            try:
                gemini_drafts = self._generate_with_gemini(
                    title=title,
                    transcript=cleaned_transcript,
                    tone=tone_normalized,
                    include_hashtags=include_hashtags,
                )
                if gemini_drafts:
                    return gemini_drafts
            except Exception as e:
                logger.warning("Gemini AI generation failed, falling back to smart copy engine: %s", e)

        # 2. Smart Copywriting Engine fallback
        return self._generate_smart_fallback(
            title=title,
            transcript=cleaned_transcript,
            tone=tone_normalized,
            include_hashtags=include_hashtags,
        )

    def _generate_with_gemini(
        self,
        title: str,
        transcript: str,
        tone: str,
        include_hashtags: bool,
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """Call Gemini API across candidate models with automatic failover."""
        candidate_models: List[str] = []
        if settings.GEMINI_MODEL:
            candidate_models.append(settings.GEMINI_MODEL.strip())
        for m in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"):
            if m not in candidate_models:
                candidate_models.append(m)

        prompt = (
            f"You are a world-class viral copywriter and creative director for short-form video (Instagram Reels and YouTube Shorts).\n\n"
            f"Topic / Title: '{title}'.\n"
            f"Context / Speech: '{transcript or 'High-energy, compelling creator video with captivating visual moments.'}'.\n"
            f"Tone: '{tone}'.\n\n"
            f"Task: Generate viral, scroll-stopping social media copy.\n"
            f"Rules:\n"
            f"1. Generate a punchy, click-worthy Title (3 to 6 words).\n"
            f"2. Write an engaging Instagram caption: hook line that stops the scroll, 2 concise descriptive storytelling sentences, and a natural call to action.\n"
            f"3. Do NOT output generic filler like 'Check out this moment' or 'voice-over commentary'.\n"
            f"4. Provide 6 to 10 trending, high-reach hashtags relevant to this content.\n\n"
            f"Respond ONLY with a valid JSON object matching this schema with no markdown code blocks:\n"
            f"{{\n"
            f'  "instagram": {{\n'
            f'    "title": "Punchy Title Here",\n'
            f'    "caption": "Scroll-stopping hook line.\\n\\nEngaging description of the moment.\\n\\nCall to action.",\n'
            f'    "hashtags": "#reels #trending #viral #fyp #explorepage #creator"\n'
            f'  }},\n'
            f'  "youtube": {{\n'
            f'    "title": "High CTR Title Under 85 Chars #Shorts",\n'
            f'    "description": "Engaging description with context and subscribe CTA.",\n'
            f'    "hashtags": "shorts, trending, viral, creator"\n'
            f'  }}\n'
            f"}}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.75, "maxOutputTokens": 1000},
        }

        with httpx.Client(timeout=20.0) as client:
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY.strip()}"
                try:
                    res = client.post(url, json=payload)
                    if res.status_code != 200:
                        logger.warning("Gemini model %s returned status %d: %s", model, res.status_code, res.text[:200])
                        continue

                    data = res.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        continue

                    raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    # Strip code blocks
                    if raw_text.startswith("```"):
                        raw_text = raw_text.split("\n", 1)[-1]
                        if raw_text.endswith("```"):
                            raw_text = raw_text.rsplit("```", 1)[0]
                        raw_text = raw_text.strip()

                    parsed = json.loads(raw_text)
                    ig = parsed.get("instagram", {})
                    yt = parsed.get("youtube", {})

                    ig_title = (ig.get("title") or title).strip()
                    ig_caption = (ig.get("caption") or "").strip()
                    ig_tags = (ig.get("hashtags") or "").strip() if include_hashtags else ""

                    yt_title = (yt.get("title") or f"{ig_title} #Shorts").strip()
                    yt_desc = (yt.get("description") or f"{ig_caption}\n\n#Shorts").strip()
                    yt_tags = (yt.get("hashtags") or "shorts, viral, trending").strip()

                    if ig_caption:
                        return {
                            "instagram": {
                                "title": ig_title,
                                "caption": ig_caption,
                                "description": "",
                                "hashtags": ig_tags,
                            },
                            "youtube": {
                                "title": yt_title,
                                "caption": "",
                                "description": yt_desc,
                                "hashtags": yt_tags,
                            },
                        }
                except Exception as model_err:
                    logger.warning("Error with Gemini model %s: %s", model, model_err)
                    continue

        return None

    def _generate_smart_fallback(
        self,
        title: str,
        transcript: str,
        tone: str,
        include_hashtags: bool,
    ) -> Dict[str, Dict[str, str]]:
        """
        Executive-grade copywriting engine providing dynamic, captivating titles,
        hooks, storytelling body, and call-to-actions tailored to the chosen tone.
        """
        # Clean title base
        is_generic = title.lower() in ("viral highlights", "kuaishou video", "instagram reel", "video", "")
        clean_subject = title if not is_generic else "This Creator Moment"

        if tone == "professional":
            ig_title = f"Mastery in Focus: {clean_subject}" if not is_generic else "Mastery in Motion: Precision & Craft"
            hook = "Precision, timing, and disciplined execution. 🎯"
            if transcript:
                body = (
                    f"\"{transcript[:200]}...\"\n\n"
                    f"Observing the subtle mechanics behind this sequence demonstrates what true consistency looks like."
                )
            else:
                body = (
                    f"The attention to detail and flow across this sequence demonstrates what true craftsmanship looks like in practice. "
                    f"Notice how seamless the rhythm remains from start to finish."
                )
            cta = "Save this reference for your next creative project. What key takeaway stood out to you? Let's discuss."
            hashtags = "#craftsmanship #mastery #creator #professional #process #innovation #focus #excellence #reels"

        elif tone == "humorous":
            ig_title = f"Nobody Expected This 😂" if is_generic else f"When {clean_subject} Goes Off Script 😂"
            hook = "Tell me I'm not the only one who didn't see that ending coming... 💀😭"
            if transcript:
                body = (
                    f"\"{transcript[:180]}...\"\n\n"
                    f"Just when you think you know exactly how this is going to turn out, reality takes a completely unexpected left turn."
                )
            else:
                body = (
                    f"The confidence going into this versus the actual outcome is unmatched. "
                    f"Watching this on repeat and it only gets funnier every single time."
                )
            cta = "Tag that one friend who would definitely do this! Drop your reaction below 👇😂"
            hashtags = "#comedy #funny #humor #relatable #viral #trending #reels #lol #funnymoments #hilarious"

        else:
            # Engaging (default)
            ig_title = f"{clean_subject}: Pure Energy" if not is_generic else "The Moment Everyone Is Talking About 🔥"
            hook = "Wait until you see how this sequence unfolds... 👀✨"
            if transcript:
                body = (
                    f"\"{transcript[:220]}...\"\n\n"
                    f"From the creative rhythm to the final delivery, every second of this was dialed in perfectly."
                )
            else:
                body = (
                    f"From the creative rhythm to the flawless execution, every second of this moment was dialed in with unmatched energy. "
                    f"Proof that consistency and passion hit completely differently."
                )
            cta = "Double tap if this inspired you! Share this with someone who needs to see it today 🚀"
            hashtags = "#reels #trending #viral #explorepage #creator #viralvideos #reelsinstagram #inspiration #fyp"

        ig_caption = f"{hook}\n\n{body}\n\n{cta}"
        ig_hashtags = hashtags if include_hashtags else ""

        yt_title = f"{ig_title} #Shorts"
        if len(yt_title) > 90:
            yt_title = yt_title[:82] + "... #Shorts"

        yt_description = (
            f"{ig_caption}\n\n"
            f"Subscribe for daily curated viral creator highlights and master editions!\n\n"
            f"#Shorts #Viral #Trending"
        )
        yt_tags = "shorts, viral, trending, creator, highlights, reels, inspiration"

        return {
            "instagram": {
                "title": ig_title,
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

metadata_service = MetadataAssistantService()
