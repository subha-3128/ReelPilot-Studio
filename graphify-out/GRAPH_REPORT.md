# Graph Report - kasu pro  (2026-10-11)

## Corpus Check
- Corpus is ~25,391 words - fits in a single context window. You may not need a graph.

## Summary
- 400 nodes · 885 edges · 28 communities (14 shown, 14 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 65 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- asyncio / assets.py
- ApiClient (Typed Backend Client) / DownloaderService (yt-dlp SSRF-Guarded Ingestion)
- security.py / Strip dangerous directory separators and non-alphanumeric characters.
- delete_asset() / delete_derivative()
- drafts.py / generate_drafts()
- package.json / dependencies
- cancel_publication() / create_publication()
- transcription.py / AnyTranscribeNoticeProvider
- endpoints/media.py / get_thumbnail()
- tsconfig.app.json / compilerOptions
- tsconfig.node.json / compilerOptions
- MediaService / .burn_subtitles()
- .oxlintrc.json / plugins
- BackgroundScheduler (Local Persistent Task Worker) / API /publications (Post, Schedule, Retry)
- API /studio (Voiceover, Sync, Subtitles, Export) / MediaDerivative (Synced & Captioned Exports)
- tsconfig.json / files
- App.tsx (Main Workbench Router)
- ContentDraft (Platform Copy & Hashtags)
- index.css (UI UX Pro Max OLED Dark Tokens)
- API /settings (Storage, Timezone, Accounts)
- Transcript (Timestamped Subtitle Segments)
- VoiceoverAsset (Extracted English Audio Track)

## God Nodes (most connected - your core abstractions)
1. `VideoAsset` - 29 edges
2. `Publication` - 20 edges
3. `compilerOptions` - 18 edges
4. `StudioPage (6-Step Voiceover & Caption Wizard)` - 16 edges
5. `MediaDerivative` - 15 edges
6. `compilerOptions` - 15 edges
7. `validate_and_normalize_url()` - 11 edges
8. `react` - 11 edges
9. `DashboardPage (Kuaishou URL Downloader)` - 11 edges
10. `get_db()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `ApiClient (Typed Backend Client)` --calls--> `API /publications (Post, Schedule, Retry)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/publishing.py
- `ApiClient (Typed Backend Client)` --calls--> `API /assets (CRUD, Inspect, Download)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/assets.py
- `ApiClient (Typed Backend Client)` --calls--> `API /drafts (AI Metadata & User Edits)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/drafts.py
- `ApiClient (Typed Backend Client)` --streams_from--> `API /media (HTTP Range Video & Thumbnails)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/media.py
- `ApiClient (Typed Backend Client)` --calls--> `API /studio (Voiceover, Sync, Subtitles, Export)`  [EXTRACTED]
  frontend/src/api/client.ts → backend/app/api/endpoints/studio.py

## Import Cycles
- None detected.

## Communities (28 total, 14 thin omitted)

### Community 0 - "asyncio / assets.py"
Cohesion: 0.08
Nodes (13): connect_account(), get_accounts(), get_app_settings(), update_app_settings(), Settings, get_db(), init_db(), health_check() (+5 more)

### Community 1 - "ApiClient (Typed Backend Client) / DownloaderService (yt-dlp SSRF-Guarded Ingestion)"
Cohesion: 0.11
Nodes (41): ApiClient (Typed Backend Client), DownloaderService (yt-dlp SSRF-Guarded Ingestion), API /assets (CRUD, Inspect, Download), API /drafts (AI Metadata & User Edits), API /media (HTTP Range Video & Thumbnails), MetadataAssistantService (AI Instagram/YouTube Copy), VideoAsset (Original Source Video Record), api (+33 more)

### Community 2 - "security.py / Strip dangerous directory separators and non-alphanumeric characters."
Cohesion: 0.07
Nodes (13): sanitize_filename(), validate_and_normalize_url(), DownloaderService, format_timestamp_srt(), format_timestamp_vtt(), test_asset_crud_flow(), test_path_traversal_guard(), test_publication_creation_and_independent_status() (+5 more)

### Community 3 - "delete_asset() / delete_derivative()"
Cohesion: 0.10
Nodes (29): delete_asset(), delete_derivative(), download_asset(), get_asset(), inspect_url(), list_assets(), AppSettingsResponse, AppSettingsUpdateRequest (+21 more)

### Community 4 - "drafts.py / generate_drafts()"
Cohesion: 0.17
Nodes (17): generate_drafts(), get_drafts(), update_draft(), burn_subtitles(), export_derivative(), get_or_create_transcript(), sync_voiceover(), update_transcript() (+9 more)

### Community 5 - "package.json / dependencies"
Cohesion: 0.07
Nodes (28): dependencies, lucide-react, react, react-dom, devDependencies, oxlint, @types/node, @types/react (+20 more)

### Community 6 - "cancel_publication() / create_publication()"
Cohesion: 0.15
Nodes (10): cancel_publication(), create_publication(), list_publications(), retry_publication(), Publication, SocialAccount, InstagramPublisher, PlatformPublisher (+2 more)

### Community 7 - "transcription.py / AnyTranscribeNoticeProvider"
Cohesion: 0.13
Nodes (4): AnyTranscribeNoticeProvider, LocalSpeechTranscriptionProvider, TranscriptionProvider, TranscriptionService

### Community 8 - "endpoints/media.py / get_thumbnail()"
Cohesion: 0.15
Nodes (8): get_thumbnail(), send_file_range(), file_iterator(), stream_audio(), stream_derivative_video(), stream_original_video(), safe_resolve_path(), BackgroundScheduler

### Community 9 - "tsconfig.app.json / compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+11 more)

### Community 10 - "tsconfig.node.json / compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 12 - ".oxlintrc.json / plugins"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 13 - "BackgroundScheduler (Local Persistent Task Worker) / API /publications (Post, Schedule, Retry)"
Cohesion: 0.50
Nodes (4): BackgroundScheduler (Local Persistent Task Worker), API /publications (Post, Schedule, Retry), Publication (Independent Social Outcomes), SocialPublishingService (Instagram & YouTube Adapters)

### Community 14 - "API /studio (Voiceover, Sync, Subtitles, Export) / MediaDerivative (Synced & Captioned Exports)"
Cohesion: 0.50
Nodes (4): API /studio (Voiceover, Sync, Subtitles, Export), MediaDerivative (Synced & Captioned Exports), MediaService (FFmpeg 9.0.2 Audio Sync & Burn), TranscriptionService (Local Speech & SRT Engine)

## Knowledge Gaps
- **18 isolated node(s):** `@types/node`, `@types/react`, `@types/react-dom`, `oxlint`, `typescript` (+13 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 157 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VideoAsset` connect `drafts.py / generate_drafts()` to `asyncio / assets.py`, `security.py / Strip dangerous directory separators and non-alphanumeric characters.`, `delete_asset() / delete_derivative()`, `cancel_publication() / create_publication()`, `endpoints/media.py / get_thumbnail()`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `VideoAsset` (e.g. with `delete_asset()` and `get_asset()`) actually correct?**
  _`VideoAsset` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `@types/node`, `@types/react`, `@types/react-dom` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `asyncio / assets.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07864488808227466 - nodes in this community are weakly interconnected._
- **Why does `Publication` connect `cancel_publication() / create_publication()` to `asyncio / assets.py`, `endpoints/media.py / get_thumbnail()`, `security.py / Strip dangerous directory separators and non-alphanumeric characters.`, `drafts.py / generate_drafts()`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `Publication` (e.g. with `cancel_publication()` and `create_publication()`) actually correct?**
  _`Publication` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `ApiClient (Typed Backend Client) / DownloaderService (yt-dlp SSRF-Guarded Ingestion)` be split into smaller, more focused modules?**
  _Cohesion score 0.1096938775510204 - nodes in this community are weakly interconnected._