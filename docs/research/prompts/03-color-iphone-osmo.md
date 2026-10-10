# 03 · Color pipeline for mixed iPhone HDR and DJI Osmo Pocket footage

Скопировать всё, что между линиями, в ChatGPT Deep Research и в Claude Research. Ответы положить в `docs/research/03-color-iphone-osmo/chatgpt.md` и `claude.md`.

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

RESEARCH TASK 3 of 6: color pipeline for mixed iPhone and DJI Osmo Pocket footage in Resolve Studio

Goal: a reliable, automatable color workflow for Reels where clips come from an iPhone
(sometimes HDR / Dolby Vision HLG, sometimes SDR, sometimes Apple Log) and a DJI Osmo
Pocket (sometimes normal profile, sometimes D-Log M 10-bit), mixed in one timeline,
delivered as SDR Rec.709 1080x1920 for Instagram, with a consistent "travel" look.

Find and document:

1. Metadata detection: how to detect per clip, from the file itself (ffprobe, exiftool,
   mediainfo, Resolve clip attributes), whether it is HDR (HLG / PQ / Dolby Vision
   profile 8.4), Apple Log, D-Log M, or standard Rec.709. Exact fields and values.
2. The correct Resolve 20/21 setup for mixing these: DaVinci YRGB Color Managed vs
   manual CST nodes, input color space per clip, timeline color space, output color
   space, what to do with Dolby Vision metadata, known pitfalls (washed-out iPhone HDR,
   double-transform, gamma shift on export, QuickTime "gamma tag" issues on macOS).
   Can all of this be set by script (per-clip input color space via API)?
3. DJI official D-Log M to Rec.709 LUTs for Osmo Pocket 3/4, where to download, and
   whether they should be applied as input LUT or via CST.
4. Instagram delivery: does Instagram accept HDR Reels in 2026, what happens to SDR vs
   HDR uploads, recommended export (codec, bitrate, color tags: bt709 nclc 1-1-1), tools
   to verify tags before upload.
5. Automatic / assisted grading options an agent could use: Resolve Color Match, shot
   match, Auto Color, third-party AI grading tools (e.g. Colourlab Ai, fylm.ai,
   Dehancer, others) with APIs or scriptability; open-source auto color matching
   between clips (Python, OpenCV, color-matcher libs).
6. Look design: how creators build a consistent "travel film" look (LUT packs, film
   emulation, grain, halation) and where to get free/paid LUTs that work on Rec.709
   after CST. How to apply a LUT per timeline vs per clip by script.
7. Exposure/white-balance fixing at scale: tools to auto-detect clipped highlights,
   mixed white balance between clips, and fix them programmatically or in Resolve.

Exclude: cinema cameras, RAW workflows, HDR mastering for TV, color theory basics.

Output format:
- Table A: footage type × how to detect it (exact metadata) × Resolve input setting ×
  scriptable (yes/no, API call) × source link.
- Section B: step-by-step recommended pipeline for one mixed timeline, with the reasons.
- Table C: grading/LUT tools (name, link, cost, agent-callable?, verdict).
- Section D: export settings for Instagram with sources, and known gotchas on macOS.

---
