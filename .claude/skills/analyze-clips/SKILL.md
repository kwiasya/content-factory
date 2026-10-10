---
name: analyze-clips
description: Build a Shot log per Clip from the proxies — per-second exposure, sharpness, shake, motion direction, people, aesthetics, and candidate segments. Use after ingest-walk, before write-script.
---

# Analyze Clips into Shot logs

The Editor sees Clips only through Shot logs (`docs/adr/0002-agent-sees-shot-log-not-frames.md`). Schema: `docs/research/04-video-understanding-shot-quality/result-a.md` Section C, versioned `reel-shotlog/1.1`. All analysis runs on `proxy/`, one clip at a time; only speech reads the audio of `raw/` (proxies have no audio).

## Steps

1. Read `clip_manifest.json`. Skip clips that already have a shot log newer than their proxy.
2. For each clip run `.venv/bin/python -m cf.shotlog proxy/<clip>.mp4` → `shotlog/<clip>.json`. It chains: ffmpeg `signalstats`+`blurdetect`+`scdet` per second; OpenCV global motion (shake px, pan dx, divergence, pace); `tools/vision-score` (Apple Vision aesthetics, faces); YOLO person tracks; Whisper `small` speech on the raw clip's audio (`per_second.speech`, `speech_segments`, `speech_text`); then scores 1 s bins and slides 2–5 s windows into up to 3 candidate `segments` with `reason`, and lists `rejects` with `why`. `--all <walk>` loads Whisper once and gives 1.0 logs only the speech pass (`--speech-only` redoes it).
3. Tag each candidate with the shot vocabulary: `motion` ∈ locked · push_in · pull_back · drift · pan_left · pan_right · forward_walk · handheld; `light` ∈ golden_hour · overcast · blue_hour · night · interior. A second with speech is never usable (`why: speech`; no speech in a Reel until voiceover), so no candidate contains speech.
4. Print one line per clip: best candidate in/out, quality score, tags, flags.
5. Where no candidate survives the filters, say so: that clip is a reject for this Walk, with the reason.

Done when every clip in the manifest has a Shot log and the summary table has been shown to the user.
