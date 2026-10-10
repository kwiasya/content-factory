# 02 · Text overlays, transitions and motion graphics for Reels

Скопировать всё, что между линиями, в ChatGPT Deep Research и в Claude Research. Ответы положить в `docs/research/02-overlays-and-motion-graphics/chatgpt.md` и `claude.md`.

---

CONTEXT (same for every research task in this series)

I am a solo creator building an AI "video editor" agent for my own Instagram Reels.
The content: vertical 9:16 Reels up to 60 seconds, travel walks, scenic strolls, landmarks,
"walk with me" style. No speech on camera right now (may come later). Music will be used,
plus text overlays (place names, short facts) and transitions.

Setup:
- macOS, MacBook Air M2, 8 GB RAM (this is a hard constraint: heavy local ML models and
  parallel rendering are problematic; cloud APIs are acceptable).
- DaVinci Resolve Studio 21.1.1 (paid version, external scripting enabled, Python API available).
- The agent is Claude Code (Anthropic's CLI agent) running in a git repo. It can run shell
  commands, Python 3.12 (venv), Node 24, ffmpeg, and can call MCP servers and "skills"
  (markdown instruction files). It can drive Resolve through the official Python scripting API.
- Source footage: iPhone (settings vary: sometimes HDR / Dolby Vision, 4K 30 or 60 fps) and
  DJI Osmo Pocket (settings vary: sometimes D-Log M 10-bit). The agent must handle each
  clip based on its metadata.
- Workflow: clips are already pre-selected by me. The agent writes a text "script" (clip
  order, hook, overlay texts, caption), builds a Resolve timeline, adds overlays, color,
  sound, then I review and tweak in Resolve, then render 1080x1920.

Research rules:
- Prefer sources from 2025–2026; flag anything older than 2024 as possibly outdated.
- Prefer primary sources: official docs, GitHub repos, changelogs, maintainer posts.
- For every tool: name, link, license, price, last release date, maturity (actively
  maintained / stale / abandoned), platform support (macOS Apple Silicon), and HOW an
  agent would call it (CLI, Python lib, HTTP API, MCP server, Resolve script).
- Be explicit about what is NOT possible or NOT worth it. Negative findings are valuable.
- Do not pad. Tables over prose. Cite links for every claim about a tool.

RESEARCH TASK 2 of 6: programmatic text overlays, transitions and motion graphics for travel Reels

Goal: decide how my agent should produce animated text overlays (place names, short
facts, hooks), transitions and small motion-graphics elements for 9:16 Reels, with
consistent personal style, without me doing it by hand each time.

Compare these rendering paths head to head, with evidence:

1. Inside Resolve: Fusion Text+ templates, Fusion macros (.setting), Resolve title
   templates, programmatic parameter changes via the scripting API. How far can an
   agent go: create a title from a template, set text, font, position, animation
   in/out, duration? Any libraries of free/paid vertical-video Fusion templates?
2. Remotion (React-based video renderer): render overlays with alpha (ProRes 4444 /
   PNG sequence) and import into Resolve as a layer. Maturity in 2026, licensing
   (company vs individual license), render time on M2 8 GB, best practices for
   transparent overlays, existing Remotion template packs for captions/titles,
   Remotion + AI agent integrations (there is official "Remotion skills" / agent docs,
   check them).
3. Other code-driven renderers: Motion Canvas, Manim, Lottie (via LottieFiles, Bodymovin,
   lottie-to-video), HTML/CSS → video (Puppeteer/Playwright capture), ffmpeg drawtext/
   ASS subtitles (libass) for simple animated text, Python MoviePy, Rust/Go tools.
4. AI motion-graphics generators and caption-styling tools (e.g. Captions app,
   Submagic, Opus Clip, CapCut templates, Canva video, Adobe Express) — only if they
   have an API or can be scripted; otherwise list them in one line as "GUI-only".
5. Transitions: how to do whip pans, zoom punches, match cuts, speed ramps, luma fades
   programmatically in Resolve (API or FCPXML) vs pre-rendered transition overlays.
6. Style consistency: how to store a "style profile" (fonts, colors, safe zones for
   Instagram UI, animation presets) so every render looks the same. Instagram Reels
   safe zones in pixels for 1080x1920 (where the UI covers the video).
7. What is trending in 2025–2026 travel / "walk with me" Reels in terms of text style
   and motion: minimal serif captions, location tags, kinetic text, etc. Cite examples
   or analyses, not opinions.

Exclude: 3D animation, character animation, long-form YouTube intro packs, After Effects
workflows (I do not have AE).

Output format:
- Table A: rendering path × can agent fully automate it × output format × render time
  estimate × license/cost × maintenance status × verdict for my case.
- Table B: tools/templates found (name, link, type, cost, how to call from an agent).
- Section C: recommended primary path and fallback, with reasoning and the top 3 risks.
- Section D: Instagram safe-zone numbers with source.

---
