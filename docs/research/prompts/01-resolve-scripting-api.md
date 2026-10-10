# 01 · DaVinci Resolve Studio scripting: what an agent can and cannot do

Скопировать всё, что между линиями, в ChatGPT Deep Research и в Claude Research. Ответы положить в `docs/research/01-resolve-scripting-api/chatgpt.md` и `claude.md`.

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

RESEARCH TASK 1 of 6: DaVinci Resolve Studio scripting API, as a tool for an AI agent

Goal: a complete, honest map of what an external Python script (and therefore my agent)
can do inside DaVinci Resolve Studio 21.x on macOS, what it cannot do, and what the
existing ecosystem (libraries, MCP servers, wrappers, community scripts) already provides.

Find and document:

1. Official API coverage, per Resolve page, for version 20/21:
   - Media Pool: import, folders, metadata read/write, proxies, clip attributes (LUT, color space per clip).
   - Edit page: create timeline, append clips with in/out, set clip position/duration,
     transitions, speed changes, retiming, crop/transform/zoom (Inspector properties),
     markers, compound clips, adjustment clips, subtitles/text+ titles.
   - Fusion page: can a script create/modify Fusion compositions, insert a Fusion
     template (.setting / macro), set its text and parameters programmatically?
   - Color page: apply LUT, apply node grade, color space transform, copy grades,
     stills/powergrades, per-clip vs timeline-level.
   - Fairlight: volume, normalization, fades, effects. What is NOT scriptable?
   - Deliver: render presets, custom resolution 1080x1920, H.264/H.265 settings,
     render job queue, progress monitoring.
   - Project settings: timeline resolution/fps/vertical, color management (DaVinci YRGB
     Color Managed), HDR/SDR handling.
2. Known hard limits of the API (things only possible through the GUI) and known
   workarounds: FCPXML/AAF/EDL/OTIO import, DRT timeline import, Fusion macros,
   UI automation (keyboard scripting, AppleScript, pyautogui), DaVinci "Resolve FX".
3. Existing open-source projects that wrap or extend the API, specifically:
   - Python wrappers / typed stubs (e.g. pydavinci, davinci-resolve-api-helpers, others).
   - MCP servers for DaVinci Resolve (there are several on GitHub; compare them:
     coverage, maintenance, Resolve version tested, macOS support).
   - OpenTimelineIO adapters for Resolve, and tools that generate FCPXML timelines
     from code (for vertical 9:16 timelines in particular).
   - Agent/LLM projects that already drive Resolve (any "AI editor" built on Resolve).
4. Practical setup facts: env vars on macOS (RESOLVE_SCRIPT_API, RESOLVE_SCRIPT_LIB,
   PYTHONPATH), supported Python versions for Resolve 21 (does 3.12 work?), external
   scripting preference, running headless or with Resolve open, stability issues,
   how long operations take, whether multiple scripts can connect at once.
5. Resolve 20/21 built-in AI features that could replace custom tooling: IntelliScript,
   AI Music Editor, Magic Mask, Voice Isolation, Smart Reframe, Scene Cut Detection,
   Auto subtitles, "IntelliCut". For each: is it scriptable or GUI-only?

Exclude: Resolve Free version limitations (I have Studio), Windows/Linux specifics,
basic "how to use Resolve" tutorials.

Output format:
- Table A: feature × scriptable (yes / partial / no) × API call or workaround × source link.
- Table B: ecosystem projects (name, link, what it adds, last commit, Resolve version, verdict).
- Section C: "Do not try this" list with reasons.
- Section D: recommended architecture for an agent driving Resolve 21 Studio on macOS,
  with the top 3 risks.

---
