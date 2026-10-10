# 06 · Scripts for travel Reels and the 2026 AI short-form landscape

Скопировать всё, что между линиями, в ChatGPT Deep Research и в Claude Research. Ответы положить в `docs/research/06-reels-scripts-and-ai-landscape/chatgpt.md` и `claude.md`.

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

RESEARCH TASK 6 of 6: how to write Scripts for travel "walk with me" Reels, and the 2026 landscape of AI tools for short-form video

Goal, part 1: before building a Reel, my agent writes a text "Script": the order of
clips, the hook in the first 1–2 seconds, the on-screen overlay texts (place names,
short facts, lines), and the post caption with hashtags. I need evidence-based
guidance on what makes travel/walk Reels perform in 2025–2026 so the agent can follow
real formulas rather than guesses.

Goal, part 2: a broad sweep of every AI / automation tool relevant to short-form
vertical video in 2026, so nothing important is missed before I design my own
pipeline. Breadth matters here; one line per tool is fine.

Part 1 — find and document:
1. Structure of a high-performing 15–60 second travel / walk / "POV: you are in X" Reel:
   hook types (text hook, visual hook, question, contrast), pacing (average shot
   length in 2025–2026 trending travel Reels), ending/loop tricks, how overlays are
   used (one line per shot vs one title), text amount. Prefer analyses with data
   (creator reports, platform statements, studies), not generic marketing posts.
2. Instagram algorithm signals in 2026 that matter for Reels (watch time, replays,
   shares, sends, saves, original audio), with sources from Instagram/Meta or credible
   analyses. What changed in 2025–2026.
3. Captions and hashtags: current best practice (length, number of hashtags, alt text,
   location tags, posting time), with sources.
4. Prompt patterns and frameworks people use to get LLMs to write short-form scripts
   and hooks (hook libraries, "script templates" for travel niche), and how to feed
   clip descriptions into the script generation.
5. Examples: 10–20 well-performing travel/walk Reels or accounts from 2025–2026 that
   use text overlays well, with a one-line note on what they do (for a style-reference
   list; links required).

Part 2 — find and list (one line each, grouped):
6. AI video editors and auto-Reel generators (Opus Clip, Captions, Submagic, Descript,
   CapCut AI, InVideo, Pictory, Runway, Veed, Vizard, Klap, Munch, others as of 2026):
   what they automate, API availability, price, relevance to travel footage.
7. Agent-oriented video tooling: MCP servers for video (ffmpeg MCP, video editing MCPs,
   Remotion agent skills, Resolve MCPs), Claude Code / Cursor "skills" or plugins for
   video, open-source agentic editors on GitHub (2025–2026), notable papers on
   LLM-driven video editing.
8. AI tools for related steps: thumbnail/cover generation, image-to-video b-roll
   (Kling, Runway, Veo, Sora, Luma, Pika, Seedance, Higgsfield), upscaling and
   stabilization (Topaz, Gyroflow), auto-reframing to 9:16, background removal.
9. Scheduling/analytics tools with APIs that could later close the loop (Meta Graph
   API for Reels publishing and insights, Later, Buffer, Metricool).

Exclude: generic "best AI tools" listicles without links, TikTok-only features unless
they also apply to Instagram, paid-course content.

Output format:
- Section A: Script template for a travel Reel (fields, rules, examples) derived from
  findings, with citations.
- Table B: hook types and pacing numbers with sources.
- Table C: style-reference Reels/accounts (link, why it works).
- Table D: tool landscape (name, link, category, API?, price, one-line verdict),
  grouped by category.
- Section E: top 5 things from this sweep that I would be foolish to ignore.

---
