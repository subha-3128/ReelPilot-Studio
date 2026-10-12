from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    """Toggle between interactive and automatic modes."""
    interactive_label = "Interactive (Active)" if current_mode == "interactive" else "Switch to Interactive"
    automatic_label = "Automatic (Active)" if current_mode == "automatic" else "Switch to Automatic"
    
    keyboard = [
        [
            InlineKeyboardButton(interactive_label, callback_data="set:mode:interactive"),
            InlineKeyboardButton(automatic_label, callback_data="set:mode:automatic"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_audio_policy_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Ask voice-over and audio replacement policy."""
    keyboard = [
        [
            InlineKeyboardButton(
                "Natural Speed (Mute Chinese)",
                callback_data=f"q:audio:{job_id}:keep_natural_speed",
            )
        ],
        [
            InlineKeyboardButton(
                "Fit Video Duration (Rubberband)",
                callback_data=f"q:audio:{job_id}:fit_to_video",
            )
        ],
        [
            InlineKeyboardButton(
                "Keep Original Audio (No Mute)",
                callback_data=f"q:audio:{job_id}:keep_original",
            )
        ],
        [
            InlineKeyboardButton("Cancel", callback_data=f"q:confirm:{job_id}:cancel")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_subtitles_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Ask subtitle burn-in preference."""
    keyboard = [
        [
            InlineKeyboardButton(
                "Burn Subtitles (White 24pt)",
                callback_data=f"q:sub:{job_id}:burn_yes",
            ),
            InlineKeyboardButton(
                "No Subtitle Burn",
                callback_data=f"q:sub:{job_id}:burn_no",
            ),
        ],
        [
            InlineKeyboardButton("Cancel", callback_data=f"q:confirm:{job_id}:cancel")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_tone_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Ask AI copy tone preference."""
    keyboard = [
        [
            InlineKeyboardButton("Engaging", callback_data=f"q:tone:{job_id}:engaging"),
            InlineKeyboardButton("Professional", callback_data=f"q:tone:{job_id}:professional"),
            InlineKeyboardButton("Humorous", callback_data=f"q:tone:{job_id}:humorous"),
        ],
        [
            InlineKeyboardButton("Cancel Production", callback_data=f"q:confirm:{job_id}:cancel")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_publish_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Ask target social publishing destination."""
    keyboard = [
        [
            InlineKeyboardButton("Direct Delivery Only", callback_data=f"q:pub:{job_id}:none"),
        ],
        [
            InlineKeyboardButton("Instagram Reels", callback_data=f"q:pub:{job_id}:instagram"),
            InlineKeyboardButton("YouTube Shorts", callback_data=f"q:pub:{job_id}:youtube"),
        ],
        [
            InlineKeyboardButton("Both (Instagram + YouTube)", callback_data=f"q:pub:{job_id}:both"),
        ],
        [
            InlineKeyboardButton("Cancel Production", callback_data=f"q:confirm:{job_id}:cancel")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_confirm_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Final preflight confirmation before starting background render."""
    keyboard = [
        [
            InlineKeyboardButton("Start Production", callback_data=f"q:confirm:{job_id}:start"),
            InlineKeyboardButton("Cancel Production", callback_data=f"q:confirm:{job_id}:cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_retry_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Retry action button on failed job."""
    keyboard = [
        [
            InlineKeyboardButton("Retry Production", callback_data=f"q:retry:{job_id}:run"),
            InlineKeyboardButton("Dismiss", callback_data=f"q:confirm:{job_id}:cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
