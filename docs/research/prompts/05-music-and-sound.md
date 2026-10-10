# 05 · Music, beat sync and sound for Reels

Скопировать всё, что между линиями, в ChatGPT Deep Research и в Claude Research. Ответы положить в `docs/research/05-music-and-sound/chatgpt.md` и `claude.md`.

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

RESEARCH TASK 5 of 6: music sourcing, beat-synced cutting and sound cleanup for Reels

Goal: music will definitely be in every Reel, but I have not decided where it comes
from or who adds it (me in Instagram, or the agent in the edit). I need the full map
of options and the tools that let an agent cut clips to the beat and keep the natural
walk sound clean underneath.

Find and document:

1. Where music comes from, with legal and practical consequences for Instagram Reels:
   a) Instagram trending audio added at publish time (what the agent then needs:
      the same track as a file to cut against; is there a legal way to get it; how
      creators do this in practice; does the cut survive Instagram replacing audio),
   b) licensed libraries (Epidemic Sound, Artlist, Musicbed, Uppbeat, others):
      price, Instagram clearance, API access, "stems" availability, 2026 state,
   c) AI-generated music (Suno, Udio, ElevenLabs Music, Stable Audio, Google Lyria,
      MusicGen, others): licensing for commercial Instagram use, API availability,
      quality for travel/lo-fi/cinematic moods, cost,
   d) Resolve Studio 20/21 built-in AI Music Editor and Fairlight music tools:
      what they do, scriptable or not.
2. Beat and structure detection tools an agent can run: librosa, madmom, Essentia,
   aubio, BeatNet, allin1 (All-In-One music structure), Spotify Basic Pitch, Demucs
   for stems. Accuracy, speed on M2 8 GB, Python 3.12 support, maintenance in 2026.
   Also: detecting "drops", phrases, energy curves, not just beats.
3. Beat-synced auto-cutting: existing tools and projects (open source or paid, GUI or
   API) that place cuts on beats and choose clip durations from music energy
   (e.g. tools similar to CapCut auto-beat, Resolve "beat markers" via script, Premiere
   Remix style). What algorithms they use; any papers on music-driven video editing.
   How to express the result as cut points for a Resolve timeline.
4. Sound design for walk Reels: keeping ambient sound (footsteps, street, sea) under
   music, ducking, crossfades between clips without clicks, wind noise removal, loudness
   normalization targets for Instagram (LUFS, true peak), tools: ffmpeg filters
   (loudnorm, afftdn, highpass), Resolve Fairlight (scriptable?), AI denoisers
   (Resolve Voice Isolation, Adobe Enhance, Krisp, DeepFilterNet, others).
5. How Instagram processes uploaded audio in 2026: re-encoding, loudness, copyright
   detection (what triggers mutes), stereo vs mono, AAC bitrate.

Exclude: voiceover/TTS, podcast audio, full music production.

Output format:
- Table A: music source × legal status for Instagram × cost × agent-automatable ×
  pros/cons × verdict.
- Table B: beat/structure detection and beat-sync tools (name, link, license, runs on
  M2 8 GB, accuracy notes, how to call, last release).
- Table C: sound cleanup/normalization tools (same columns).
- Section D: two recommended end-to-end flows: (1) music chosen in the edit, (2) music
  added in Instagram, each with the exact steps an agent would perform.
- Section E: open legal/practical risks.

---
