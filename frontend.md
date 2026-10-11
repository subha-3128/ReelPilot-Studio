# Antigravity Task Prompt --- Frontend (`frontend.md`)

## Role and mission

You are the frontend lead working inside the existing repository for a
local-first **Kuaishou Video Studio**. Build a polished,
production-minded web UI for a Mac-hosted application that downloads
user-authorized Kuaishou/Kwai videos, optionally replaces Chinese source
audio with a user-provided English voice-over MP4, creates subtitles,
prepares platform metadata, and publishes or schedules approved videos
to Instagram and YouTube.

**Use the `UI UX Pro Max` skill for all UI/UX decisions.** First
discover the exact installed skill and read its instructions; do not
merely claim to have used it. Follow its design system, accessibility,
responsive layout, and implementation guidance. Reuse the repository's
existing stack and conventions unless there is a clear reason not to.

This file is the frontend task specification. Coordinate API contracts
with the backend implementation described in `backend.md`. Do not build
fake backend behavior into production UI. If an endpoint is not ready,
use a clearly labeled development mock behind a mock flag and document
it.

## Product requirements

The app is primarily used in a browser on the user's Mac, with video
files stored locally by the backend. The main workflow is:

1.  Paste a Kuaishou/Kwai URL and fetch/download the supported video.
2.  View its metadata, thumbnail, duration, and processing status.
3.  Optionally enable **Replace audio with my voice-over**.
4.  When enabled, reveal an **Upload voice-over MP4** area. The uploaded
    MP4 is an audio source container; extract/use its audio, not its
    video visuals.
5.  Mute original audio by default in voice-over mode. Keep the original
    file unchanged.
6.  Configure synchronization, generate English subtitles from the final
    voice-over, preview, and export.
7.  Generate editable Instagram caption and YouTube
    title/description/hashtags using available transcript/metadata and
    optional AI services.
8.  Select Instagram, YouTube, or both, then publish immediately or
    schedule.
9.  Track per-platform outcomes independently, and retry only failed
    platform actions.

The user expects an explicit toggle for the translation/voice-over
workflow. Do **not** imply the app automatically translates or generates
spoken English: in the first version, the user supplies the English
voice-over MP4. Chinese transcription/translation can be a later
optional workflow.

## Step-by-step frontend tasks

### Step 1 --- Inspect repository and skills

-   Inspect the current app structure, package manager, framework,
    existing routes/components, styling system, API client, tests, and
    conventions before editing.
-   Find and read the installed `UI UX Pro Max` skill instructions. If
    the named skill is unavailable, search available skills and report
    the closest actual option before proceeding; do not silently invent
    skill content.
-   Inspect `backend.md`, existing API schemas, and any Graphify
    instructions/configuration in the repo.
-   Preserve existing working functionality. Avoid replacing the stack
    just to match this prompt.

### Step 2 --- Establish design system

-   Apply the UI UX Pro Max skill recommendations.
-   Build a coherent design system: typography, spacing, colors,
    borders, elevation, interaction states, focus rings, and responsive
    breakpoints.
-   Aim for a modern, premium media-workbench UI: clear hierarchy,
    readable contrast, calm surfaces, compact but comfortable
    information density, and prominent video previews.
-   Avoid generic gradient-heavy AI dashboards, excessive glassmorphism,
    tiny text, and decorative UI that harms usability.
-   Support keyboard navigation, semantic HTML, accessible labels,
    screen-reader announcements for progress/status, reduced motion, and
    visible focus states.
-   Use consistent design tokens rather than one-off styles.

### Step 3 --- App shell and navigation

Implement the main shell with navigation for: - **Dashboard / Add
Video** - **Video Library** - **Video Studio** - **Publishing
Calendar** - **Publishing History** - **Settings / Connections**

Show service/connection state and a clear local-processing indicator. Do
not show secrets, access tokens, or API keys in the UI.

### Step 4 --- Add video / downloader page

Build: - Kuaishou/Kwai URL field with validation and clear error
messages. - Fetch/inspect and download actions, depending on backend
capabilities. - Progress display with percentage or stage text when
available. - Queue of downloads with
queued/downloading/completed/failed/cancelled states. - Retry/cancel
controls only when supported by the backend. - Duplicate detection
warning and a link to the existing library item where available. -
Explain unsupported links/access restrictions without suggesting
bypasses. - Make clear that users must have rights/permission to
download and reuse source material.

### Step 5 --- Video library

Create a searchable, filterable library with: - Thumbnail, filename,
duration, aspect ratio, source, date added, tags/category. - Transcript
and voice-over availability indicators. - Processing and publication
status badges. - Filters: all, downloaded, needs review, ready,
scheduled, published, failed. - Sorting and pagination/virtualization
appropriate to the actual library size. - Video detail drawer/page with
original asset, processed variants, transcript, source/rights notes, and
platform publication records. - Confirm destructive actions such as
delete. Deletion must never silently remove the original while deleting
a derivative.

### Step 6 --- Video Studio and conditional voice-over flow

Create a step-by-step studio workflow with a clear progress tracker: 1.
Source video 2. Voice-over 3. Captions 4. Preview/export 5. Metadata 6.
Publish/schedule

When **Replace audio with my voice-over** is OFF: - Keep original audio
and offer the ordinary review/export flow.

When it is ON: - Reveal an accessible upload section labeled **Upload
English voice-over MP4**. - Accept only formats supported by backend
validation; explain limits from the actual backend contract. - Show
upload progress, selected filename, duration if known, replace/remove
controls, and errors. - State that the audio track is extracted from the
uploaded MP4; its picture is not inserted into the source video. -
Default to muting all original audio, with an optional
background-ambience control only if backend processing supports it. -
Provide synchronization modes: `fit_to_video`, `keep_natural_speed`
(recommended default), and `manual_adjustment`. - Show duration mismatch
warnings before export. Never imply that narration will be perfectly
aligned automatically without review. - Provide a preview and adjustable
start offset / trim only if the backend supports those operations. -
Preserve the original source and voice-over upload; create a separate
output derivative.

### Step 7 --- Subtitles and transcript UI

-   Show transcript text and timestamped subtitle segments when
    available.
-   Provide editable caption segments, preview, and subtitle styling
    controls if supported.
-   Distinguish subtitles generated from the **final English
    voice-over** from any Chinese source transcript.
-   Offer burned-in subtitles and downloadable SRT only when those
    export options are supported.
-   Use an honest AnyTranscribe integration state. Do not assume
    AnyTranscribe has a public API or automate its website without a
    verified, permitted integration. Show connection/configuration
    status and actionable errors.
-   If transcription is unavailable, allow the user to continue without
    subtitles where possible.

### Step 8 --- AI content assistant / metadata editor

Create editable fields for: - Instagram caption and hashtags. - YouTube
title, description, and hashtags/tags where supported. - Optional
language and tone choices. - Regenerate and copy controls only if backed
by real endpoints. - Source transcript/context used for suggestions and
a warning that generated content needs human review. - Keep
platform-specific drafts separate. Do not fabricate video facts or
promise reach/virality. - Preserve user edits when regenerating unless
the user explicitly confirms replacement.

### Step 9 --- Publishing and scheduling

-   Platform selectors: Instagram, YouTube, both.
-   Separate status per platform, not one misleading overall status.
-   **Post now** and **Schedule** actions with timezone-aware date/time
    input.
-   Preflight checklist: video exported, metadata complete, account
    connected, rights confirmation, and platform requirements satisfied.
-   Confirmation modal before publishing.
-   Publishing progress and result URLs where returned by APIs.
-   If one platform succeeds and the other fails, show the successful
    result and retry only the failed platform.
-   Prevent accidental duplicate posts by using backend
    idempotency/status checks.
-   Show the local scheduler limitation: Mac/app must be awake and
    running for local scheduled jobs. Display the configured timezone.
-   Do not promise Instagram upload will work with a local-only file
    URL; explain that the backend may need temporary media hosting.

### Step 10 --- Publishing calendar and history

-   Calendar/list views for drafts, scheduled, publishing, published,
    and failed posts.
-   Filter by platform and status.
-   Show planned time, actual publish time, post URL, error summary, and
    retry eligibility.
-   Allow reschedule/cancel only where the backend and platform state
    permit it.
-   Make partial success obvious.

### Step 11 --- Settings and integrations

-   Instagram and YouTube connection status, connect/disconnect flows,
    required permissions, token-expiry status if provided by backend.
-   AnyTranscribe integration status based only on a verified supported
    mechanism.
-   Download folder and storage usage.
-   Default subtitle style, voice-over behavior, export settings, and
    timezone.
-   Never collect API secrets in client-side storage or display tokens.
    OAuth should use backend-controlled flows.

### Step 12 --- API integration and state handling

-   Use the existing typed API client if present; otherwise create a
    centralized typed client from the backend contract.
-   Add loading, empty, success, partial-success, offline, and error
    states to every relevant screen.
-   Use polling, server-sent events, or WebSockets only if backend
    support exists; document the chosen approach.
-   Do not hard-code local filesystem paths into browser code.
-   Do not make direct browser-to-platform API calls with secret
    credentials.
-   Keep UI state consistent after retries and navigation.

### Step 13 --- Testing and polish

-   Add unit/component tests for key controls, conditional voice-over
    UI, metadata forms, status rendering, and errors.
-   Add end-to-end coverage for the main flow using mocked network
    responses: add URL → download result → enable voice-over → upload
    file → edit captions → schedule/publish.
-   Test narrow and wide browser sizes, keyboard-only navigation, focus
    management, and accessible labels.
-   Run lint, typecheck, tests, and production build. Fix failures
    rather than merely listing them.
-   Remove accidental placeholder text, broken links, console errors,
    and misleading success states.

### Step 14 --- Graphify project knowledge

Use the repository's installed **Graphify** workflow to maintain a
durable knowledge graph for the whole project: - First discover the
actual Graphify instructions, commands, configuration, and graph storage
location in the repo/environment. Do not invent CLI commands or create a
competing graph format. - Read the existing graph before editing and
preserve its conventions. - Record the frontend architecture,
route/page/component map, shared UI tokens, state transitions, API
endpoints/types, and cross-module dependencies. - Link frontend
components to backend endpoints and data models, including
video/job/publication status entities. - Update the graph after each
major implementation phase and after API contract changes, not just at
the end. - Include links to relevant source files and decisions. Keep it
concise, accurate, and synchronized with the actual code. - If Graphify
is unavailable, document the blocker and the exact graph update that
remains; do not claim the graph was updated.

## Quality gates / definition of done

-   The frontend works with the actual backend API contract.
-   The conditional voice-over upload section appears only when the
    toggle is enabled.
-   Original video and uploaded voice-over are represented as separate
    assets.
-   Platform statuses are independent and partial success is clear.
-   The UI has robust loading, empty, validation, error, and retry
    states.
-   Responsive/accessibility requirements are met.
-   Lint, typecheck, tests, and build pass.
-   Graphify knowledge is updated and points to the real implementation.
-   Provide a concise final report: files changed, implemented
    workflows, checks run/results, known blockers, and graph update
    location.

## Working rules

-   Work step by step. Inspect first, implement in small coherent
    phases, and verify each phase before moving on.
-   Ask before making destructive changes or introducing a paid service.
-   Do not expose secrets, bypass platform protections, scrape
    unsupported services, or claim unsupported integration capability.
-   Prefer reliable, understandable functionality over a large number of
    superficial UI features.
