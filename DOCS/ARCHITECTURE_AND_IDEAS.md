# DeepTurtol — Architecture, Vision & Ideas

## Overview
**DeepTurtol** is a customized, beach-aesthetic fork of [HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor), an agent-native personalized tutoring platform. DeepTurtol merges DeepTutor's multi-agent reasoning, RAG framework, and knowledge graph engine with Turtol's organic coastal beach aesthetic (waves, sandcastles, pebbles, and warm sea tones).

## Git & Upstream Architecture
To ensure seamless updates from upstream DeepTutor without merge conflicts or lost history:
- **`origin`**: `https://github.com/PcRoGamer/DeepTurtol.git` (Your primary fork repo)
- **`upstream`**: `https://github.com/HKUDS/DeepTutor.git` (Authoritative source)
- **Development Workflow**:
  - All visual and functional customizations are developed on dedicated feature branches (`feature/beach-theme-sidebar`, etc.).
  - Periodic upstream syncs are performed via `git fetch upstream` -> `git rebase upstream/main`.

## Design Philosophy & Aesthetic Blueprint
1. **Beach & Coastal Color System**:
   - Primary Sand Base: `#E5D3B8` / `#F6EFE5` (Light sand) & `#3D342C` / `#4A3F35` (Dark warm sand)
   - Ocean & Wave Accents: `#00A896` / `#028090` / `#05668D` (Lagoon blue & foam green)
   - Coastal Pebble Accents: `#C3B095` border trims & smooth rounded pebble shapes
2. **Visual Components**:
   - **Wave Sidebar**: Curved wave SVG divider along the sidebar navigation panel.
   - **Sandcastle Input Bar**: Sculpted sand-styled chat input with carved text effect.
   - **Beach Micro-animations**: Subtle wave shimmer, ripple click effects, and warm sea-foam hover states.

## Roadmap & Progress Tracking
- [x] **Step 0**: Fork & clone repository, configure `upstream` remote, setup documentation hub.
- [ ] **Step 1**: Visual-only Next.js frontend update (Waves sidebar, sand color tokens, beach aesthetic — **0 functionality changes**).
- [ ] **Step 2**: Visual polish & component harmonization across chat, workspace, knowledge base, and settings pages.
- [ ] **Step 3**: Feature additions (custom tutoring agent personalities, enhanced interactive learning surfaces).
- [ ] **Step 4**: GUI-first setup migration — move first-run configuration, provider onboarding, diagnostics, and common runtime setup from terminal-guided flows into the Web UI. Preserve the CLI for automation, headless deployments, and advanced users; every GUI flow should expose clear status, recovery guidance, and safe links to provider setup.
- [ ] **Step 5**: Video library — store course videos with background transcription, searchable captions/subtitles, lecture summaries, and knowledge-base ingestion. Keep playback, caption generation, and indexing independently queued so video processing never blocks chat or live speech-to-text.

### Echo360 and library progress

- [x] Durable audio/video storage, playback, background transcription, summaries, and study notes.
- [x] UniMelb Echo360 course discovery/import through a GUI-managed, isolated Chromium profile without accepting or storing university passwords.
- [x] Always-available agent library search over transcripts and generated notes, independent of KB selection.
- [x] Time-aligned WebVTT subtitle generation during media processing + subtitle display in the video player.
- [ ] Subtitle editing/export and richer video-library organization.

The archived EchoTutor/Trinity implementations are reference material only.
The active integration in `deeptutor/services/echo360.py` targets the user's
current University of Melbourne enrolments on Echo360 Cloud. Do not restore
Trinity-specific login, course, path, or branding assumptions into the runtime.
