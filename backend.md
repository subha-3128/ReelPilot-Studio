# Antigravity Task Prompt --- Backend (`backend.md`)

## Role and mission

You are the backend lead for the existing local-first **Kuaishou Video
Studio**. Implement a reliable Mac-hosted service that manages supported
video downloads, local assets, user-supplied English voice-over audio,
video processing, subtitles/transcription integration, metadata drafts,
and Instagram/YouTube publishing and scheduling.

**Use the installed `Ponytail` skill for backend work.** First discover
the exact skill and read its instructions. Follow the skill's
conventions for architecture, code quality, testing, security, and
implementation. Do not claim to use it if it is not available. Inspect
the repository and preserve its existing framework/conventions unless a
migration is necessary and justified.

Coordinate the frontend API contract with `frontend.md`. Maintain
project knowledge in the repository's actual **Graphify** knowledge
graph throughout implementation.

## Product workflow

1.  Accept a Kuaishou/Kwai URL.
2.  Validate the URL and download only through a supported, permitted
    extraction method.
3.  Store the original video on the Mac and register it in the database.
4.  Optionally accept a user-uploaded English voice-over MP4.
5.  Extract the audio track from that uploaded MP4; do not use its
    visual frames.
6.  Mute original video audio by default in voice-over mode.
7.  Synchronize the supplied audio with the source video using a
    selected policy.
8.  Generate English captions from the final voice-over, using a
    verified transcription integration or a supported fallback.
9.  Export a derivative while preserving the original.
10. Generate editable platform metadata drafts using configured AI
    capability, or gracefully disable that feature if no provider is
    configured.
11. Publish to Instagram, YouTube, or both using official APIs and
    authorized OAuth.
12. Schedule publication and track independent per-platform outcomes.
13. Keep accurate history and update Graphify after each major phase.

The first version uses a **user-provided English voice-over**. Do not
silently add machine translation or synthetic voice generation as a
required step. Chinese transcription/translation may be a future
optional feature.

## Step-by-step backend tasks

### Step 1 --- Inspect repository and skill instructions

-   Inspect the repository structure, runtime, dependency manager,
    database, migrations, environment/config patterns, existing API
    routes, background jobs, tests, and deployment setup.
-   Find and read the installed `Ponytail` skill instructions. If not
    available, inspect actual available skills and report the
    limitation; do not invent its rules.
-   Inspect `frontend.md`, any existing API schemas, and the Graphify
    configuration/knowledge graph.
-   Establish a short implementation plan and execute it incrementally.
    Do not rewrite a functioning project wholesale.

### Step 2 --- Architecture and configuration

-   Reuse the current backend stack where possible; if the repo is new,
    prefer Python FastAPI, SQLite, and FFmpeg for a Mac-local service.
-   Separate download, asset management, media processing,
    transcription, metadata generation, publishing, scheduling, and
    integration configuration into clear modules.
-   Use environment variables or a local secrets store for secrets.
    Provide a safe `.env.example` with placeholders only; ensure `.env`,
    tokens, cookies, and credentials are gitignored.
-   Add startup validation for required dependencies and clear
    diagnostics for missing FFmpeg or configuration.
-   Bind local-only services to loopback by default. Do not expose the
    service to the public internet without an explicit secure deployment
    design.

### Step 3 --- Data model and migrations

Create or adapt models for: - `VideoAsset`: id, original source URL,
source platform, original local path, filename, duration, width/height,
aspect ratio, size, checksum, created time, rights/permission notes. -
`MediaDerivative`: parent asset, type (voice-over, captioned, platform
export), local path, media metadata, processing settings, checksum. -
`VoiceoverAsset`: source upload path, extracted audio path, duration,
metadata, linked video. - `Transcript` and `SubtitleSegment`:
provider/source language, target language, text, timestamps, status, and
version. - `ContentDraft`: platform, title, caption, description,
hashtags/tags, language, generation source, edit state. -
`ProcessingJob`: job type, status, progress, stage, timestamps, retry
count, error code/message, cancellation where safe. - `SocialAccount`:
platform, account identifier/label, connection status, scopes/expiry
metadata; never persist secrets in plaintext unless the existing secure
secret mechanism explicitly requires it. - `Publication`:
video/derivative, platform, scheduled time, status, remote id/URL,
attempts, error details, idempotency key. - `AppSettings`: non-secret
preferences such as output folder, timezone, subtitle style, and default
behavior. Use migrations and foreign keys where supported. Store
filesystem paths and relative/managed asset references safely; do not
store media blobs in SQLite.

### Step 4 --- API contract for frontend

Implement documented, typed endpoints consistent with frontend needs.
Adapt naming to repository conventions and publish OpenAPI schemas if
using FastAPI. At minimum support equivalents of: - Health/status and
capability checks. - Create/inspect a source URL and start a download
job. - List/get/cancel/retry supported jobs. - List/search/filter/get
assets and derivatives. - Upload a voice-over MP4 with size/type
validation. - Start voice-over processing with mode/settings. -
Get/update transcript and subtitle segments; start transcription if
supported. - Export or fetch generated media through a safe local
endpoint, not a raw arbitrary filesystem path. - Create/update content
drafts and request metadata suggestions. - Connect/disconnect/check
Instagram and YouTube accounts via OAuth flows. - Validate publishing
readiness, publish now, schedule, list/update/cancel scheduled jobs
where safe. - Get publication history, retry a failed platform
publication, and return remote post URLs. - Read/update non-secret
settings and integration status. Add request/response schemas,
pagination, validation, consistent error responses, and API versioning
if appropriate. Document the final contract for the frontend in the
repo.

### Step 5 --- Secure supported downloading

-   Inspect whether a maintained downloader such as yt-dlp supports the
    specific Kuaishou/Kwai URLs that the user is authorized to access.
-   Do not assume the reference website provides a public API; do not
    depend on its undocumented internal endpoints.
-   Do not bypass login, paywalls, DRM, anti-bot/access controls, or
    platform restrictions. Do not embed user cookies or credentials
    without explicit secure handling and authorization.
-   Validate URL schemes and allowed hosts; protect against SSRF,
    redirects to private networks, local-file URLs, and arbitrary
    protocols.
-   Sanitize filenames, constrain output paths to the configured media
    root, enforce size/time limits, and use subprocess argument arrays
    (never shell string interpolation).
-   Support job progress, timeouts, cancellation where safe, retries
    with backoff, and duplicate detection via cryptographic checksum.
    Optional perceptual duplicate detection may be added later.
-   Store original downloads unchanged and keep source URL/rights notes.
    Return clear unsupported-link errors rather than pretending success.

### Step 6 --- Asset storage and media validation

-   Use a configurable media directory on the Mac with safe path
    handling and adequate disk-space checks.
-   Validate uploads by inspecting actual file content/metadata, not
    only the supplied extension or MIME type.
-   Set file-size/duration limits, reject malformed or unsupported
    files, and prevent path traversal.
-   Generate thumbnails and probe media using FFprobe/FFmpeg with safe
    argument handling.
-   Keep original source, voice-over upload, extracted audio, and final
    derivative as distinct assets.
-   Implement safe deletion with explicit confirmation semantics and
    clear dependency checks.
-   Do not expose arbitrary local paths through HTTP endpoints.

### Step 7 --- Voice-over processing

Implement a deterministic FFmpeg-based pipeline: 1. Validate the source
video and voice-over MP4. 2. Probe duration, dimensions, frame rate,
codecs, and audio stream availability. 3. Extract the uploaded MP4's
audio stream; ignore its video stream. 4. Keep source video frames and
9:16 framing unless the user explicitly chooses an edit. 5. In
voice-over mode, remove/mute all original audio by default. 6. Apply the
selected synchronization policy: - `keep_natural_speed`: default;
preserve natural speech speed, support a configurable start offset, and
handle shorter/longer durations explicitly. - `fit_to_video`: only apply
bounded, quality-aware speed adjustment and warn if adjustment exceeds
safe thresholds. - `manual_adjustment`: accept validated trim/offset
settings. 7. Do not silently cut off narration. If voice-over duration
exceeds the video, return a warning and require an explicit policy
(trim, approved video extension/freeze frame, or cancel). 8. If
narration is shorter, support a configurable ending policy such as
silence or optional licensed background audio; silence is the safe
default. 9. Export to a new derivative with compatible codecs/container,
preserve the original, and record the settings and output metadata. 10.
Verify output integrity and ensure the exported video duration,
dimensions, audio track, and file size are reasonable. Use subprocess
argument arrays, resource/time limits, and safe temporary directories.
Add unit/integration tests for duration mismatch, no-audio input,
malformed input, and processing failure.

### Step 8 --- Transcription and subtitles

-   Investigate AnyTranscribe's official site/docs to determine whether
    it provides an official API, SDK, or other supported
    automation/integration method. Do not assume an API exists and do
    not automate/scrape its website or bypass access controls.
-   If a supported integration exists, isolate it behind a
    `TranscriptionProvider` interface, keep credentials server-side,
    honor provider terms/limits, and document setup.
-   If no suitable integration exists, implement a provider interface
    with a local or authorized alternative (for example, a local
    speech-to-text engine) only after checking repository/environment
    capabilities and clearly documenting dependencies.
-   Transcribe the **final English voice-over audio** to create English
    subtitles. Keep any Chinese-source transcript separate and label
    language/provenance clearly.
-   Store timestamped segments, allow corrections, and export SRT/VTT
    where supported.
-   Support optional burned-in subtitles via FFmpeg with safe font/path
    handling and configurable style.
-   Treat transcription as optional: if unavailable/fails, allow the
    user to continue without captions when feasible.
-   Do not invent transcript text or timestamps; reflect provider
    uncertainty/errors honestly.

### Step 9 --- AI metadata assistant

-   Use a provider interface for caption/title/description/hashtag
    suggestions.
-   Generate drafts only from available video metadata, user input, and
    transcript; do not claim visual understanding unless a configured
    visual-analysis provider actually supplies it.
-   Keep suggestions editable and preserve user changes unless
    replacement is explicitly requested.
-   Do not store provider keys in frontend code or commit them to the
    repo.
-   If no provider is configured, return a clear disabled/unconfigured
    state and allow manual metadata entry.
-   Add tests for empty transcript, provider failure, and user-edited
    draft preservation.

### Step 10 --- Instagram OAuth and publishing

-   Use the current official Instagram publishing API and supported
    OAuth flow. Verify current account eligibility, permissions, token
    handling, media specifications, and publishing constraints against
    official documentation.
-   Do not assume a local filesystem path is fetchable by Meta. If
    remote media access is required, design a configurable
    temporary-media-hosting adapter with expiring, least-privilege URLs
    and cleanup after the provider has fetched the media, where
    feasible.
-   Do not expose local files through a public directory or create an
    unrestricted upload endpoint.
-   Keep credentials and refresh tokens server-side, protected by the
    platform's supported storage mechanism; redact them from logs.
-   Implement readiness checks, upload/container status polling where
    required, publish confirmation, rate-limit handling, and structured
    errors.
-   Record remote IDs/URLs and per-platform state. Make retries
    idempotent and avoid duplicate publishing.
-   If hosting or API access is not configured, fail with an actionable
    status; do not simulate a successful post.

### Step 11 --- YouTube OAuth and upload

-   Use official YouTube Data API v3 with OAuth 2.0 for
    account-authorized uploads. An API key alone is not sufficient for
    uploading to a user's channel.
-   Support resumable upload if practical, progress reporting, retries,
    quota/rate-limit handling, and upload status.
-   Apply title, description, tags where supported, privacy setting, and
    category only when valid for the current API.
-   Handle API project verification/restrictions honestly and document
    setup steps.
-   Save returned video ID/URL and final state.
-   Keep YouTube and Instagram publication records independent so a
    retry targets only the failed platform.

### Step 12 --- Scheduler and background jobs

-   Use a persistent, restart-safe local job queue/scheduler appropriate
    to the existing stack.
-   Store schedule timestamps in UTC and retain the user's IANA timezone
    for display and daylight-saving correctness.
-   Clearly document that local scheduled publishing requires the Mac,
    application, and internet connection to be active at the scheduled
    time.
-   Implement job locking to prevent two workers from processing the
    same job.
-   Add bounded retries with exponential backoff for transient errors;
    don't retry permanent validation/auth failures indefinitely.
-   Support pause/cancel only at safe stages and expose job
    state/progress to the frontend.
-   For "publish to both," create separate publication jobs and maintain
    an aggregate state without hiding partial success.

### Step 13 --- Security, privacy, and reliability

-   Add authentication/CSRF protections if the app is ever exposed
    beyond loopback; by default, bind locally and reject unexpected
    origins.
-   Apply CORS allowlists, request size limits, rate limits for
    expensive endpoints, upload validation, path traversal protection,
    SSRF protections, and safe subprocess execution.
-   Redact access tokens, authorization headers, sensitive query
    parameters, and local secrets from logs.
-   Avoid telemetry or uploading user media unless required for a
    configured feature and disclosed.
-   Add structured logging and actionable error codes without leaking
    sensitive data.
-   Provide a clear rights/permission confirmation before publication.
    Do not assume a public Kuaishou video is free to reuse.
-   Respect platform terms and APIs; do not bypass DRM, private content
    restrictions, or access controls.
-   Use safe temporary-file cleanup and prevent orphaned job records
    where feasible.

### Step 14 --- Testing

Add automated tests for: - URL allowlisting and SSRF protection. -
Filename/path sanitization and upload validation. - Duplicate
detection. - Job state transitions, retries, cancellation, and
progress. - Voice-over extraction and original-audio muting. -
Shorter/longer narration policies and preservation of original assets. -
Subtitle timestamp storage and SRT/VTT output. - Transcription provider
success/failure and unconfigured state. - OAuth callback validation and
secret redaction (mock external APIs). - Instagram/YouTube partial
success and retry idempotency. - Scheduling timezone/DST and restart
recovery. - API schema compatibility with frontend. Never make live
social posts in automated tests. Use mocked API clients and test
credentials only.

### Step 15 --- Documentation and developer experience

-   Add/update setup instructions for macOS, Python/runtime
    dependencies, FFmpeg, environment variables, database migrations,
    and local startup.
-   Document Instagram/YouTube developer app configuration, OAuth
    redirect URLs, required permissions, quota/verification caveats, and
    secure secret setup.
-   Document AnyTranscribe integration findings with official evidence.
    If no official API is found, explicitly state that and explain the
    selected fallback.
-   Provide sample configuration with placeholders, not working
    credentials.
-   Document the API endpoints and job/status state machine for frontend
    integration.
-   Provide troubleshooting guidance and a clear distinction between
    implemented, configured, and not-yet-supported features.

### Step 16 --- Graphify project knowledge

Use the actual Graphify tool/workflow installed in this repository: -
Discover its instructions, commands, configuration, graph location, and
existing conventions before use. Do not invent commands or create a
parallel knowledge graph. - Read existing graph knowledge first and
preserve its format. - Record modules, files, data models, API routes,
job states, external integrations, environment variables by name (never
their values), and dependencies. - Represent relationships such as
`Frontend page -> API endpoint -> service -> model/job -> filesystem/external API`. -
Include important architectural decisions and integration limitations,
especially AnyTranscribe API verification and Instagram
temporary-hosting requirements. - Update after each major phase and
after contract/schema changes. Verify graph updates reflect actual
code. - If Graphify is not installed or unavailable, report the blocker
and the exact missing update; do not claim completion.

## Quality gates / definition of done

-   The application starts locally on macOS with documented setup.
-   Original video and voice-over files remain unchanged; processed
    exports are separate derivatives.
-   Voice-over mode mutes original audio and uses the uploaded MP4's
    audio track.
-   Duration mismatches are handled explicitly, with no silent narration
    truncation.
-   Subtitles are based on final English audio and are timestamped where
    provider support allows.
-   Platform integrations use official supported authorization/API flows
    and never fake success.
-   Publishing statuses are independent, retries are idempotent, and
    partial success is retained.
-   Scheduler survives restart and respects timezone semantics.
-   Security checks and tests pass; lint/typecheck/build/test commands
    are run and failures fixed or precisely documented.
-   Graphify knowledge is updated and consistent with the code.
-   Final report lists files changed, endpoints, setup/config
    requirements, tests and results, verified external integration
    capabilities, remaining blockers, and Graphify location.

## Working rules

-   Work step by step: inspect, plan, implement one phase, test, update
    Graphify, then continue.
-   Do not install paid services or introduce costs without asking.
-   Do not hard-code credentials, claim unsupported APIs, scrape
    undocumented services, bypass platform restrictions, or publish
    content without user action/authorization.
-   Prefer a robust end-to-end MVP over shallow placeholders. If a
    feature is blocked by credentials or external API approval, finish
    its interface, adapter, tests, and setup documentation without
    pretending the live integration works.
