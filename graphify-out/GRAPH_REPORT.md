# Graph Report - kasu pro  (2026-10-12)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 537 nodes · 1241 edges · 49 communities (15 shown, 34 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 81 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2ef760f2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models.py
- client.ts
- test_backend.py
- schemas.py
- .download_video
- handlers.py
- package.json
- test_telegram_automation.py
- conversations.py
- safe_resolve_path
- compilerOptions
- compilerOptions
- MediaService
- execute_job_pipeline
- .start
- is_user_authorized
- .oxlintrc.json
- mock_social_publishers
- MetadataAssistantService
- tsconfig.json
- run.sh
- App.tsx (Main Workbench Router)
- ContentDraft (Platform Copy & Hashtags)
- index.css (UI UX Pro Max OLED Dark Tokens)
- API /settings (Storage, Timezone, Accounts)
- Transcript (Timestamped Subtitle Segments)
- VoiceoverAsset (Extracted English Audio Track)

## God Nodes (most connected - your core abstractions)
1. `VideoAsset` - 32 edges
2. `ProcessingJob` - 23 edges
3. `execute_job_pipeline()` - 20 edges
4. `MediaDerivative` - 18 edges
5. `compilerOptions` - 18 edges
6. `handle_callback_query()` - 17 edges
7. `require_auth()` - 16 edges
8. `compilerOptions` - 15 edges
9. `Publication` - 14 edges
10. `handle_video_url_submission()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `ApiClient (Typed Backend Client)` --calls--> `API /assets (CRUD, Inspect, Download)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/assets.py
- `ApiClient (Typed Backend Client)` --calls--> `API /drafts (AI Metadata & User Edits)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/drafts.py
- `ApiClient (Typed Backend Client)` --streams_from--> `API /media (HTTP Range Video & Thumbnails)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/media.py
- `ApiClient (Typed Backend Client)` --calls--> `API /publications (Post, Schedule, Retry)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/publishing.py
- `get_thumbnail()` --uses--> `MediaDerivative`  [INFERRED]
  backend/app/api/endpoints/media.py → backend/app/models/models.py

## Import Cycles
- None detected.

## Communities (49 total, 34 thin omitted)

### Community 0 - "models.py"
Cohesion: 0.08
Nodes (24): delete_asset(), delete_derivative(), download_asset(), get_asset(), inspect_url(), list_assets(), cancel_publication(), create_publication() (+16 more)

### Community 1 - "client.ts"
Cohesion: 0.09
Nodes (42): ApiClient (Typed Backend Client), BackgroundScheduler (Local Persistent Task Worker), DownloaderService (yt-dlp SSRF-Guarded Ingestion), API /assets (CRUD, Inspect, Download), API /drafts (AI Metadata & User Edits), API /media (HTTP Range Video & Thumbnails), API /publications (Post, Schedule, Retry), API /studio (Voiceover, Sync, Subtitles, Export) (+34 more)

### Community 2 - "test_backend.py"
Cohesion: 0.06
Nodes (16): sanitize_filename(), validate_and_normalize_url(), AnyTranscribeNoticeProvider, format_timestamp_srt(), format_timestamp_vtt(), LocalSpeechTranscriptionProvider, TranscriptionProvider, TranscriptionService (+8 more)

### Community 3 - "schemas.py"
Cohesion: 0.09
Nodes (35): generate_drafts(), get_drafts(), update_draft(), connect_account(), burn_subtitles(), export_derivative(), get_or_create_transcript(), sync_voiceover() (+27 more)

### Community 4 - ".download_video"
Cohesion: 0.07
Nodes (9): get_accounts(), get_app_settings(), Settings, health_check(), DownloaderService, InstagramPublisher, PlatformPublisher, SocialPublishingService (+1 more)

### Community 5 - "handlers.py"
Cohesion: 0.15
Nodes (11): callback_query_handler(), cancel_command(), help_command(), jobs_command(), mode_command(), retry_command(), settings_command(), start_command() (+3 more)

### Community 6 - "package.json"
Cohesion: 0.07
Nodes (29): dependencies, lucide-react, react, react-dom, devDependencies, oxlint, @types/node, @types/react (+21 more)

### Community 7 - "test_telegram_automation.py"
Cohesion: 0.13
Nodes (12): ProcessingJob, TelegramUserPreference, get_or_create_user_pref(), handle_video_url_submission(), test_telegram_config_validation(), test_telegram_job_cancellation(), test_telegram_pipeline_execution(), test_telegram_question_callback_flow() (+4 more)

### Community 8 - "conversations.py"
Cohesion: 0.17
Nodes (8): handle_callback_query(), build_audio_policy_keyboard(), build_confirm_keyboard(), build_mode_keyboard(), build_publish_keyboard(), build_retry_keyboard(), build_subtitles_keyboard(), build_tone_keyboard()

### Community 9 - "safe_resolve_path"
Cohesion: 0.15
Nodes (8): get_thumbnail(), send_file_range(), file_iterator(), stream_audio(), stream_derivative_video(), stream_original_video(), safe_resolve_path(), BackgroundScheduler

### Community 10 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+11 more)

### Community 11 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 13 - "execute_job_pipeline"
Cohesion: 0.20
Nodes (4): format_job_status_text(), safe_edit_message(), safe_send_message(), execute_job_pipeline()

### Community 15 - "is_user_authorized"
Cohesion: 0.33
Nodes (3): is_user_authorized(), wrapper(), test_telegram_user_authorization()

### Community 16 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

## Knowledge Gaps
- **18 isolated node(s):** `oxlint`, `@types/node`, `@types/react`, `@types/react-dom`, `typescript` (+13 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 224 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VideoAsset` connect `models.py` to `test_backend.py`, `schemas.py`, `.download_video`, `test_telegram_automation.py`, `safe_resolve_path`, `execute_job_pipeline`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `VideoAsset` (e.g. with `delete_asset()` and `get_asset()`) actually correct?**
  _`VideoAsset` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `oxlint`, `@types/node`, `@types/react` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `models.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08339029391660971 - nodes in this community are weakly interconnected._
- **Why does `MediaService` connect `MediaService` to `models.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `ProcessingJob` (e.g. with `TelegramBotManager` and `handle_callback_query()`) actually correct?**
  _`ProcessingJob` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Should `client.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.08831168831168831 - nodes in this community are weakly interconnected._