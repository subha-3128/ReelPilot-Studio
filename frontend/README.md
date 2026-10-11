# 🎬 ReelPilot — Frontend

<p align="center">
  <img src="public/logo.svg" alt="ReelPilot Logo" width="96" height="96" />
</p>

<p align="center">
  <strong>“From raw clips to ready-to-publish content.”</strong>
</p>

---

## 🚀 Overview

The **ReelPilot** frontend is a high-performance, dark-themed (OLED dark palette) desktop web interface built with **React 19**, **TypeScript**, and **Vite 8**. It interfaces directly with the local FastAPI backend to provide an end-to-end video pipeline:

1. **Add Video / URL**: Direct Kuaishou ingestion with metadata preview.
2. **Video Library**: Media catalog with range-request HTML5 video playback.
3. **Video Studio**: 6-step guided wizard (Voice-over synchronization, subtitle editing, burn-in preview, AI copy, direct publishing).
4. **Publishing Calendar**: Timezone-aware scheduled publication calendar.
5. **Publishing History**: Real-time audit log with single-platform retries.
6. **Settings & Integrations**: Local storage management, disk usage meter, and OAuth credential management.

## 🛠️ Development

```bash
# Install dependencies
npm install

# Start Vite development server
npm run dev

# Typecheck and build for production
npm run build
```

---

<p align="center">
  Crafted with ❤️ By <a href="https://github.com/subha-3128" target="_blank" rel="noopener noreferrer">Nubru</a>
</p>

<p align="center">
  <small>© 2026 ReelPilot Studio. All rights reserved.</small>
</p>
