<p align="center">
  <img src="frontend/public/logo.svg" alt="ReelPilot Logo" width="110" height="110" style="border-radius: 20px; box-shadow: 0 10px 30px rgba(255, 94, 58, 0.3);" />
</p>

<h1 align="center">ReelPilot</h1>

<p align="center">
  <strong>“From raw clips to ready-to-publish content.”</strong>
</p>

<p align="center">
  <em>High-performance, local-first macOS desktop studio to download authorized Kuaishou (快手) / Kwai videos, replace Chinese audio with English voice-overs, burn subtitles, generate AI captions, and publish directly to Instagram Reels and YouTube Shorts.</em>
</p>

<p align="center">
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/Backend-FastAPI_0.115+-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://react.dev"><img src="https://img.shields.io/badge/Frontend-React_19_+_TypeScript-61DAFB?style=flat&logo=react&logoColor=black" alt="React" /></a>
  <a href="https://vitejs.dev"><img src="https://img.shields.io/badge/Build-Vite_8-646CFF?style=flat&logo=vite&logoColor=white" alt="Vite" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://ffmpeg.org"><img src="https://img.shields.io/badge/Engine-FFmpeg_&_FFprobe-007808?style=flat&logo=ffmpeg&logoColor=white" alt="FFmpeg" /></a>
  <a href="https://ai.google.dev"><img src="https://img.shields.io/badge/AI-Google_Gemini_3.8_Flash-4285F4?style=flat&logo=google&logoColor=white" alt="Gemini" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License" /></a>
</p>

---

## Table of Contents

- [Key Highlights](#key-highlights)
- [System Architecture](#system-architecture)
- [The 6-Step Studio Workflow](#the-6-step-studio-workflow)
- [Project Directory Layout](#project-directory-layout)
- [Prerequisites & System Requirements](#prerequisites--system-requirements)
- [Quick Start Guide](#quick-start-guide)
- [Configuration & Credentials](#configuration--credentials)
- [Telegram Automation & Bot Setup](#telegram-automation--bot-setup)
- [Zero-Budget Cloud Deployment (Render.com & Oracle)](#zero-budget-cloud-deployment-rendercom--oracle)
- [Automated Testing & Verification](#automated-testing--verification)
- [REST API Specifications](#rest-api-specifications)
- [Security & Privacy Model](#security-privacy-model)
- [Graphify Architecture Knowledge Graph](#graphify-architecture-knowledge-graph)
- [License & Credits](#license--credits)

---

## Key Highlights

- **100% Local-First & Private:** All media files, SQLite databases, and API secrets remain strictly on your local Mac. Servers bind only to loopback (`127.0.0.1`).
- **Preserve Original Video Frames:** The source video stream is never cropped, distorted, or re-framed. The original 9:16 vertical video framing is strictly maintained, and original files are kept completely untouched in `storage/originals/`.
- **Dual-Engine Ingestion Pipeline:** 
  - **Primary:** High-speed native Kuaishou CDN stream parser (`window.INIT_STATE`) that follows mobile share links (`v.kuaishou.com`), pulls exact Chinese captions & author handles, and downloads high-definition `.mp4` video directly.
  - **Fallback:** Automatic failover to `yt-dlp` array execution.
- **Voice-Over Engine:** 
  - Upload user-supplied English voice-over MP4s.
  - Automatically extracts the audio track via FFmpeg, discarding unnecessary video tracks.
  - Completely mutes original Chinese audio by default.
  - Three synchronization policies: `keep_natural_speed` (recommended), `fit_to_video` (atempo/rubberband), or `manual_adjustment`.
- **Subtitle & Caption Generation:**
  - Automatic timestamped subtitle generation with local phrase segmentation.
  - In-browser interactive subtitle editor.
  - Subtitle burn-in with customizable font sizes, colors (`&H00FFFFFF`), and outline styles.
  - One-click `.srt` export.
- **AI Content Assistant:**
  - Integrated with **Google Gemini 3.8 Flash** (`gemini-3.8-flash`) to generate platform-tailored, viral Instagram captions/hashtags and YouTube Shorts titles, descriptions, and tags.
  - Smart local heuristic fallbacks when offline or unconfigured.
- **Multi-Platform Direct Publishing:**
  - **Instagram Reels:** Official Meta Graph API publishing with direct streaming ingestion.
  - **YouTube Shorts:** Google Cloud OAuth 2.0 resumable direct upload API (`youtube.upload` scope).
  - **Independent Platform Tracking:** Real-time statuses (`draft`, `scheduled`, `publishing`, `published`, `failed`).
  - **Single-Platform Retry:** Retry failed uploads on one platform without creating duplicate posts on successful ones.
- **Configurable Storage Directory:** Select custom media destination directories (e.g., `~/Movies/KuaishouStudio` or external SSD) directly from the Settings page with automatic directory creation and disk space meters.

---

## System Architecture

```mermaid
graph TD
    User([User / Creator]) -->|Browser UI| Frontend[React 19 + TypeScript + Vite<br>OLED Dark Theme]
    Frontend -->|REST API & Streaming| Backend[FastAPI Backend Engine<br>127.0.0.1:8000]

    subgraph "Backend Engine"
        Backend --> Router[FastAPI APIRouter]
        Router --> AssetsAPI[Assets & Download]
        Router --> StudioAPI[Studio Wizard]
        Router --> DraftsAPI[AI Content Drafts]
        Router --> PubsAPI[Publishing & Retry]
        Router --> SettingsAPI[Settings & Storage]
        Router --> MediaAPI[Safe Range Video Streaming]

        AssetsAPI --> Downloader[Downloader Engine<br>Native CDN Parser + yt-dlp]
        StudioAPI --> MediaService[FFmpeg / FFprobe Engine]
        StudioAPI --> Transcription[Transcription Service]
        DraftsAPI --> GeminiAI[Google Gemini 3.8 Flash]
        PubsAPI --> SocialService[Social Publishing Service]
        PubsAPI --> Scheduler[SQLite Background Worker & Poller]

        SocialService -->|Meta Graph API| Instagram[Instagram Reels API]
        SocialService -->|Google OAuth2 Resumable| YouTube[YouTube Shorts API]

        Downloader --> Storage[(Local Media Storage<br>storage/originals)]
        MediaService --> StorageDeriv[(storage/derivatives<br>storage/voiceovers)]
        Router --> SQLite[(SQLite Database<br>studio.db)]
    end
```

---

## The 6-Step Studio Workflow

The core studio wizard at `/studio` provides an intuitive 6-step guided experience:

| Step | Name | Description | Key Actions |
| :---: | :--- | :--- | :--- |
| **1** | **Select Source** | Choose an ingested Kuaishou/Kwai video asset from your local library. | Preview video, inspect duration, resolution (720×1280), and audio status. |
| **2** | **Voice-Over Sync** | Upload an English voice-over MP4 or toggle voice-over replacement on/off. | Mute original audio, extract audio from voice-over MP4, select sync policy (`keep_natural_speed`). |
| **3** | **Captions & Subtitles** | Review, edit, and burn English timestamped subtitles. | Edit caption text, adjust start/end timestamps, customize font size & color, export `.srt`. |
| **4** | **Preview & Export** | Inspect synchronized video with burned subtitles before exporting. | Real-time HTML5 video player with range-request streaming, render derivative MP4. |
| **5** | **AI Metadata** | Generate viral copy for target platforms using Gemini 3.8 Flash. | Customize tone (engaging, professional, humorous), generate Instagram captions/hashtags & YouTube titles/tags. |
| **6** | **Publish & Schedule** | Publish immediately or schedule to Instagram Reels, YouTube Shorts, or both. | Choose platforms, set local timezone-aware publication time, execute upload with real-time audit log. |

---

## Project Directory Layout

```
kasu pro/
├── run.sh                     # Convenience single-command launcher (Backend + Frontend)
├── backend.md                 # Backend engineering specification
├── frontend.md                # Frontend engineering specification
├── README.md                  # Comprehensive project documentation
├── .gitignore                 # Secure exclusion of .env, media files, and caches
│
├── backend/                   # Python FastAPI Backend
│   ├── .env                   # Local environment variables & API tokens (gitignored)
│   ├── .env.example           # Environment template with credential placeholders
│   ├── pyproject.toml         # Backend project configuration & dependencies
│   ├── app/
│   │   ├── main.py            # FastAPI lifespan, CORS, and loopback bindings
│   │   ├── api/
│   │   │   ├── router.py      # Unified API router
│   │   │   └── endpoints/     # assets, studio, drafts, publishing, settings, media
│   │   ├── core/
│   │   │   ├── config.py      # Dynamic storage & Pydantic application settings
│   │   │   ├── database.py    # SQLite engine and session factory
│   │   │   └── security.py    # SSRF guard, hostname allowlist, path traversal protection
│   │   ├── models/            # SQLAlchemy database models (VideoAsset, MediaDerivative, etc.)
│   │   ├── schemas/           # Pydantic v2 validation models & request/response contracts
│   │   └── services/          # Media (FFmpeg), Downloader, Transcription, AI, Publisher, Scheduler
│   └── tests/
│       ├── conftest.py        # Pytest database fixtures & social publisher quota mocking
│       ├── test_backend.py    # Unit tests for URL security, formatting, CRUD
│       └── test_full_workflow.py # End-to-end integration test (ingest -> sync -> captions -> publish)
│
├── frontend/                  # React 19 + TypeScript + Vite Frontend
│   ├── package.json           # Frontend dependencies & scripts
│   ├── vite.config.ts         # Vite server configuration & API proxy
│   ├── index.html             # App entry, dynamic title, & logo favicon
│   ├── public/                # Static studio assets
│   │   ├── logo.svg           # High-resolution vector brand mark
│   │   └── favicon.svg        # Browser tab favicon badge
│   ├── src/
│   │   ├── App.tsx            # Application routing shell
│   │   ├── index.css          # UI UX Pro Max OLED Dark theme tokens
│   │   ├── api/client.ts      # Strictly typed HTTP API client
│   │   ├── components/        # Sidebar navigation, Header, Logo, disk space badge
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx  # Ingestion dashboard & URL download queue
│   │   │   ├── LibraryPage.tsx    # Media asset management, filters, playback modal
│   │   │   ├── StudioPage.tsx     # 6-step guided video production wizard
│   │   │   ├── CalendarPage.tsx   # Timezone-aware scheduled post calendar
│   │   │   ├── HistoryPage.tsx    # Audit trail with single-platform retry
│   │   │   └── SettingsPage.tsx   # Storage directory selection, policies, OAuth status
│   │   └── types/             # TypeScript interfaces and domain types
│
├── storage/                   # Default local media workspace (gitignored)
│   ├── studio.db              # SQLite persistent database
│   ├── originals/             # Raw untouched downloaded source videos
│   ├── voiceovers/            # Uploaded voice-over MP4s & extracted audio tracks
│   ├── derivatives/           # Synchronized, captioned, and final exported MP4s
│   ├── thumbnails/            # Extracted high-resolution video covers
│   └── temp/                  # Temporary subtitle files (.srt, .vtt)
│
└── graphify-out/              # Architecture Knowledge Graph
    ├── graph.json             # 432 Nodes, 913 Edges graph data
    └── graph.html             # Interactive D3 visualization (open in browser)
```

---

## Prerequisites & System Requirements

- **Operating System:** macOS (Apple Silicon or Intel)
- **Python:** 3.12 or newer (Tested on Python 3.14)
- **Node.js:** 18 or newer (Tested on Node.js v22)
- **FFmpeg & FFprobe:** Installed and available in PATH:
  ```bash
  brew install ffmpeg
  ```
- **yt-dlp:** Installed and available in PATH:
  ```bash
  brew install yt-dlp
  ```

---

## Quick Start Guide

### Option 1: One-Click Startup (Recommended)

Run the included executable script from the project root:

```bash
./run.sh
```

This automatically:
1. Validates that `ffmpeg` and `yt-dlp` are installed.
2. Creates any missing storage subdirectories.
3. Launches the FastAPI backend at `http://127.0.0.1:8000`.
4. Waits for the `/api/health` check to pass.
5. Launches the Vite development frontend at `http://localhost:5173`.

### Option 2: Manual Terminal Execution

#### 1. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # or pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings httpx yt-dlp pytest pytest-asyncio
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

- **Frontend Application:** [http://localhost:5173](http://localhost:5173)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Configuration & Credentials

Create a `backend/.env` file based on `backend/.env.example`:

```env
# Storage & Database
DATABASE_URL=sqlite:///./storage/studio.db

# Server Bindings
HOST=127.0.0.1
PORT=8000
DEBUG=false

# Default Timezone & Preferences
DEFAULT_TIMEZONE=Asia/Kolkata
DEFAULT_SYNC_POLICY=keep_natural_speed
DEFAULT_SUBTITLE_FONT_SIZE=24
DEFAULT_SUBTITLE_FONT_COLOR=&H00FFFFFF

# Google Gemini AI Integration (Viral Metadata Copy)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash

# Instagram Reels Publishing (Meta Graph API)
INSTAGRAM_ACCOUNT_ID=your_instagram_user_or_business_id
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_user_or_business_id
INSTAGRAM_ACCESS_TOKEN=your_meta_user_or_page_access_token

# YouTube Shorts Direct Upload (Google Cloud OAuth 2.0 Data API v3)
YOUTUBE_CLIENT_ID=your_oauth_client_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your_oauth_client_secret
YOUTUBE_REFRESH_TOKEN=your_oauth_refresh_token

# Telegram Bot Automation (Zero-Budget Cloud Pipeline)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_from_botfather
TELEGRAM_ALLOWED_USER_IDS=your_telegram_user_id
TELEGRAM_MODE=polling
TELEGRAM_DEFAULT_WORKFLOW_MODE=interactive
REELPILOT_MAX_CONCURRENT_JOBS=1
REELPILOT_MAX_VIDEO_SIZE_MB=100
REELPILOT_AUTO_PUBLISH=false
REELPILOT_CLOUD_MODE=false
```

> [!NOTE]
> All credentials can also be connected and inspected dynamically from the **Settings** page in the user interface.

---

## Telegram Automation & Bot Setup

ReelPilot Studio can be fully controlled via Telegram, enabling hands-free automated video production from your mobile phone or laptop.

### 1. Create a Bot with BotFather
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow instructions to choose a name and username (e.g., `MyReelPilotBot`).
3. Copy the HTTP API token provided by BotFather and set it in `backend/.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ```

### 2. Determine Your Authorized Telegram User ID
For personal security, the bot only responds to user IDs listed in `TELEGRAM_ALLOWED_USER_IDS`:
1. Start a chat with `@userinfobot` on Telegram to view your numeric ID, or simply message your new bot.
2. If unauthorized, the bot will reply with your exact numeric ID (e.g., `123456789`).
3. Add this ID to `backend/.env`:
   ```env
   TELEGRAM_ALLOWED_USER_IDS=123456789
   ```

### 3. Workflow Operating Modes
- **Interactive Mode (Default):**
  When you send a video link, the bot guides you through inline keyboard buttons:
  - Step 1: Audio Policy (Natural Speed / Fit Duration / Keep Original Audio).
  - Step 2: Subtitles (Burn 24pt White Subtitles / No Burn).
  - Step 3: AI Tone (Engaging / Professional / Humorous).
  - Step 4: Social Destination (Export Only / Instagram Reels / YouTube Shorts / Both).
  - Step 5: Confirmation and background job queueing.
- **Automatic Mode:**
  Reuses your saved preferences from `/settings` and immediately begins downloading, dubbing, burning subtitles, generating AI copy, and exporting without asking intermediate questions.
  Switch modes anytime using `/mode`.

### 4. Bot Commands
- `/start` - Initialize bot and display operating status.
- `/help` - Usage instructions and supported link formats.
- `/mode` - Switch between Interactive and Automatic mode.
- `/settings` - View your default saved preferences.
- `/status` - View active in-flight processing jobs and progress bars.
- `/jobs` - View history of recent processing jobs.
- `/cancel` - Cancel a pending or queued workflow.
- `/retry <job_id>` - Safely retry a failed job without duplicating completed parts.

### 5. Delivery & Output Limits
- Output videos under 50 MB (Telegram Bot API limit) are streamed directly into your Telegram chat alongside AI-generated titles, captions, and hashtags.
- Videos exceeding 50 MB are preserved on persistent storage, and the bot provides a local/cloud streaming link.

---

## Zero-Budget Cloud Deployment (Render.com & Oracle)

ReelPilot Studio is engineered to run 24/7 in the cloud on persistent infrastructure with zero ongoing costs (0 INR / 0 USD per month). Once deployed, your video pipeline runs independently of your personal Mac.

### Method 1: Render.com (100% Free, No Credit/Debit Card Required)

Render provides a free Docker Web Service tier without requiring any credit or debit card for registration (only GitHub or email authentication).

1. Sign up at https://render.com using your GitHub account.
2. In your Render Dashboard, click **New +** and select **Blueprint** (or **Web Service**).
3. Connect your `ReelPilot-Studio` GitHub repository. Render automatically reads `render.yaml` and configures the service.
4. Specify your environment variables in the Render Dashboard under **Environment**:
   - `TELEGRAM_BOT_TOKEN`: Your token from BotFather (`8768413756:AAFp645DgMWGlcyYyj4lOo5-EO-N3sv3bfs`)
   - `TELEGRAM_ALLOWED_USER_IDS`: Your numeric Telegram User ID
   - `GEMINI_API_KEY`: Your Google AI Studio API key
5. Deploy the service. Render will build the container using the provided `Dockerfile` (installing FFmpeg, Python 3.12, and all dependencies).
6. **24/7 Keep-Alive Setup (Prevent Auto-Sleep):**
   Render free web services spin down after 15 minutes of web inactivity. To keep Telegram long-polling active 24/7, add your service health URL (`https://your-service-name.onrender.com/api/health`) to a free uptime pinger such as:
   - [cron-job.org](https://cron-job.org) (Schedule an HTTP GET request every 10 minutes, completely free, no card needed)
   - [uptimerobot.com](https://uptimerobot.com) (HTTP monitor every 5 or 10 minutes, free tier, no card needed)
   Since Render gives 750 free instance hours per month, one web service running 24/7 uses 744 hours in a 31-day month, remaining 100% free forever.

---

### Method 2: Oracle Cloud Always Free (Requires Credit Card Verification)

### 2. Server Provisioning & Dependencies
Connect to your Ubuntu instance via SSH:
```bash
ssh -i ~/.ssh/id_rsa ubuntu@<YOUR_INSTANCE_PUBLIC_IP>
```

Install Docker and Docker Compose (or native system dependencies):
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ffmpeg

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
```

### 3. Clone Repository & Configure Environment
```bash
git clone https://github.com/subha-3128/ReelPilot-Studio.git
cd ReelPilot-Studio

# Copy environment template
cp backend/.env.example backend/.env
nano backend/.env
```
Fill in:
- `TELEGRAM_BOT_TOKEN`: Token from BotFather
- `TELEGRAM_ALLOWED_USER_IDS`: Your Telegram User ID
- `GEMINI_API_KEY`: Free-tier API key from Google AI Studio (https://aistudio.google.com/)
- Optional: `INSTAGRAM_ACCESS_TOKEN`, `YOUTUBE_REFRESH_TOKEN`

### 4. Deployment Option A: Docker Compose (Recommended)
Launch the unified background worker container:
```bash
docker compose up -d --build
```
Check operational logs:
```bash
docker compose logs -f
```
Verify health check:
```bash
docker compose ps
```

### 5. Deployment Option B: Native Systemd Service (Lightweight)
For minimal RAM usage on 1 GB instances, run directly without containerization:
```bash
# Setup Python venv
sudo apt install -y python3-venv python3-pip
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt

# Install systemd service
sudo cp reelpilot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now reelpilot.service

# Check status and logs
sudo systemctl status reelpilot.service
journalctl -u reelpilot.service -f
```

### 6. Persistence & Restart Resilience
- **Database:** SQLite database is stored at `storage/studio.db` on host disk.
- **Media Files:** `storage/originals/`, `storage/derivatives/`, `storage/voiceovers/` are mounted as persistent host volumes.
- **Auto-Recovery:** If the server restarts, interrupted in-flight jobs are safely marked as failed with instructions to retry, preventing corrupted partial files or duplicate social publishing.

---

## Automated Testing & Verification

The test suite validates URL security guards, path sanitization, subtitle formatting, Gemini AI generation, and a complete end-to-end video lifecycle with synthetic 9:16 media generated via FFmpeg.

Automated tests mock external social publishing endpoints to ensure runs are fast and never consume live Meta or Google API quotas:

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/ -v
```

**Verification Results:**
```
backend/tests/test_backend.py::test_valid_kuaishou_urls PASSED            [  7%]
backend/tests/test_backend.py::test_reject_unsupported_domains PASSED     [ 15%]
backend/tests/test_backend.py::test_reject_invalid_schemes PASSED         [ 23%]
backend/tests/test_backend.py::test_sanitize_filename PASSED              [ 30%]
backend/tests/test_backend.py::test_path_traversal_guard PASSED           [ 38%]
backend/tests/test_backend.py::test_timestamp_formatting PASSED           [ 46%]
backend/tests/test_backend.py::test_srt_generation PASSED                 [ 53%]
backend/tests/test_backend.py::test_metadata_generation PASSED            [ 61%]
backend/tests/test_backend.py::test_health_check_endpoint PASSED          [ 69%]
backend/tests/test_backend.py::test_settings_endpoints PASSED             [ 76%]
backend/tests/test_backend.py::test_asset_crud_flow PASSED                [ 84%]
backend/tests/test_backend.py::test_publication_creation_and_independent_status PASSED [ 92%]
backend/tests/test_full_workflow.py::test_complete_end_to_end_video_workflow PASSED [100%]

======================== 13 passed in 9.11s ========================
```

---

## REST API Specifications

### Ingestion & Library (`/api/assets`)
- `POST /api/assets/inspect` — Validate Kuaishou URL, follow redirects, check duplicates, extract Chinese title & duration.
- `POST /api/assets/download` — Download video via native CDN stream or yt-dlp, compute SHA256, probe media with FFprobe.
- `GET /api/assets` — List all ingested video assets with search and status filters.
- `GET /api/assets/{id}` — Retrieve detailed asset metadata, voice-overs, and generated derivatives.
- `DELETE /api/assets/{id}` — Safely delete an asset and all its derivative files from disk.

### Video Studio (`/api/studio`)
- `POST /api/studio/upload-voiceover` — Upload English voice-over MP4, extract audio stream, validate duration.
- `POST /api/studio/sync-voiceover` — Mute original audio, merge voice-over audio, create synced derivative.
- `GET /api/studio/{asset_id}/transcript` — Retrieve timestamped subtitle segments for the voice-over.
- `PUT /api/studio/{asset_id}/transcript` — Save updated subtitle segments.
- `POST /api/studio/burn-subtitles` — Burn subtitles into video derivative using FFmpeg with custom styling.
- `POST /api/studio/export` — Render and finalize production-ready vertical 9:16 derivative.

### AI Metadata Assistant (`/api/drafts`)
- `POST /api/drafts/generate` — Generate platform copy via Gemini 3.8 Flash (Instagram captions & YouTube titles/tags).
- `GET /api/drafts/{asset_id}` — Retrieve saved draft copy for an asset.
- `PUT /api/drafts/{draft_id}` — Update titles, captions, descriptions, or hashtags.

### Publishing & Scheduling (`/api/publications`)
- `POST /api/publications` — Publish immediately or schedule to Instagram Reels, YouTube Shorts, or both.
- `GET /api/publications` — List all publications with platform and status filters.
- `POST /api/publications/{id}/retry` — Retry a single failed publication without duplicating successful posts.
- `DELETE /api/publications/{id}/cancel` — Cancel a scheduled publication.

### Settings & Media Streaming (`/api/settings` & `/api/media`)
- `GET /api/settings` — Get active storage directory, available disk space, and tool statuses.
- `PUT /api/settings` — Update storage directory, timezone, sync policy, or subtitle appearance.
- `GET /api/settings/accounts` — Check connected Instagram and YouTube accounts.
- `GET /api/media/video/{id}` — Stream original video with HTTP 206 range-request support.
- `GET /api/media/derivative/{id}` — Stream finished derivative MP4.
- `GET /api/media/thumbnail/{id}` — Serve asset cover thumbnail image.

---

## Security & Privacy Model

1. **Loopback Server Binding:** The backend binds strictly to `127.0.0.1:8000`, preventing unauthorized network access from other devices on the local area network.
2. **SSRF Guard:** Ingestion URLs are strictly validated against an allowlist of official Kuaishou/Kwai domains (`v.kuaishou.com`, `kuaishou.com`, `kwai.com`, `chenzhongtech.com`). DNS resolution blocks private, loopback, and link-local IP addresses.
3. **Path Traversal Guards:** File streaming and storage lookups use `safe_resolve_path` to guarantee that all requested file paths are strictly contained within the allowed storage roots.
4. **Credential Isolation:** OAuth secrets, refresh tokens, and AI keys are never committed to version control and are never exposed in client browser JavaScript bundles.

---

## Graphify Architecture Knowledge Graph

The project codebase maintains a persistent architectural knowledge graph generated by **Graphify**:

- **Current Graph Metrics:** 432 Nodes · 913 Edges · 47 Communities
- **Interactive Visualization:** Open [graphify-out/graph.html](graphify-out/graph.html) directly in any browser for an interactive D3 graph of code relationships, dependencies, and data flows.

To refresh the graph after making changes:
```bash
graphify extract . --code-only && graphify export html
```

---

## License & Credits

This project is licensed under the [MIT License](LICENSE). Authorized for lawful video downloading, translation, and creator syndication.

<p align="center">
  Crafted by <a href="https://github.com/subha-3128" target="_blank" rel="noopener noreferrer">Nubru</a>
</p>

<p align="center">
  <small>© 2026 ReelPilot Studio. All rights reserved.</small>
</p>
