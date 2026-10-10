# 04 · Video understanding: letting the agent see and judge clips

Скопировать всё, что между линиями, в ChatGPT Deep Research и в Claude Research. Ответы положить в `docs/research/04-video-understanding-shot-quality/chatgpt.md` и `claude.md`.

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

RESEARCH TASK 4 of 6: video understanding tools so an AI agent can "see" clips, judge quality and pick moments

Goal: give my agent eyes. Clips are already pre-selected by me, but each clip is often
longer than what ends up in the Reel. The agent needs to: understand what is in each
clip, find the best 2–5 second moments, detect shaky/blurry/overexposed parts, detect
people walking into frame, estimate motion direction and pace (for matching cuts), and
describe the clip in text so it can write the Script (overlay texts, hook, caption).

Note: do NOT research landmark/location recognition or geocoding; that is handled
separately. Focus on visual quality, moment selection and description.

Find and document:

1. Multimodal LLM APIs that accept video directly (Gemini, GPT-4o/5 family, Claude,
   Qwen-VL, others as of 2026): max video length, fps sampling, cost per minute of
   video, whether they return timestamps, quality of "describe this clip" and "find
   the best moment" tasks. Any benchmarks or write-ups comparing them for short-form
   editing.
2. Frame-sampling approach: extract frames with ffmpeg, send to a vision model.
   Best practices for sampling rate, contact sheets / grids to save tokens, cost math
   for a 60-clip walk.
3. Local, lightweight analysis that runs on M2 8 GB without a vision LLM:
   - shake / camera-motion estimation (OpenCV optical flow, vidstab, gyroflow data),
   - blur / sharpness scoring, exposure clipping, over/under-exposure stats,
   - scene cut / shot boundary detection (PySceneDetect, TransNetV2, ffmpeg scdet),
   - aesthetic scoring models (NIMA, LAION aesthetic predictor, CLIP-based scorers),
   - person / face detection to flag strangers in frame,
   - highlight / "best moment" detection models for short-form video.
4. Existing open-source "auto editor" projects for short-form or travel video that do
   selection + cutting (e.g. auto-editor, Jumpcutter, LosslessCut automation,
   ShortGPT, Vidio, Clipper, others). What they do well, what they do badly,
   whether they are maintained in 2026.
5. Clip-level metadata the agent can get for free without ML: duration, fps,
   stabilization flags, iPhone "Cinematic mode", Osmo gimbal data, slow-motion
   (120/240 fps) detection, creation time ordering.
6. How to represent the analysis so an agent can reason over it: a JSON "shot log"
   schema per clip (segments with scores and tags). Any existing standard
   (OTIO metadata, EBU, Frame.io) worth adopting.

Exclude: live streaming, surveillance analytics, training custom models from scratch.

Output format:
- Table A: tool/model × task (describe / best-moment / shake / blur / exposure /
  people / scene cut) × runs locally on M2 8 GB? × cost × latency × how an agent calls it × verdict.
- Section B: recommended two-tier pipeline (cheap local metrics first, vision LLM
  second) with concrete cost estimate for one walk of 60 clips × 20 seconds.
- Section C: proposed JSON shot-log schema.
- Section D: what is still unsolved / unreliable in 2026.

---
