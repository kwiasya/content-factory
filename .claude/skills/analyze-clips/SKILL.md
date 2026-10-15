---
name: analyze-clips
description: Build a Shot log per Clip from the proxies — per-second exposure, sharpness, shake, motion direction, people, aesthetics, and candidate segments. Use after ingest-footage, before write-script.
---

# Analyze Clips into Shot logs

The Editor sees Clips only through Shot logs (`docs/adr/0002-agent-sees-shot-log-not-frames.md`). Schema: `docs/research/04-video-understanding-shot-quality/result-a.md` Section C, versioned `reel-shotlog/1.2` (1.0 and 1.1 logs stay readable). All analysis runs on `proxy/`, one clip at a time; only speech reads the audio of `raw/` (proxies have no audio).

## Steps

1. Read `clip_manifest.json`. Skip clips that already have a shot log newer than their proxy.
2. For each clip run `.venv/bin/python -m cf.shotlog proxy/<clip>.mp4` → `shotlog/<clip>.json`. It chains: ffmpeg `signalstats`+`blurdetect`+`scdet` per second; OpenCV global motion (shake px, pan dx, divergence, pace); `tools/vision-score` (Apple Vision aesthetics, faces); YOLO person tracks; Whisper `small` speech on the raw clip's audio (`per_second.speech`, `speech_segments`, `speech_text`), and per speech segment a `side`: `near` (the author behind the camera) or `far` (the person on camera), with `side_confidence`, `rms_dbfs` and `mouth_open_var` (loudness against the Footage's loudest voice and the clip's noise floor, plus face size and mouth movement from `tools/vision-score --landmarks`); then scores 1 s bins and slides 2–5 s windows into up to 3 candidate `segments` with `reason`, and lists `rejects` with `why`. `--all <footage>` loads Whisper once, gives 1.0/1.1 logs only the speech pass (`--speech-only` redoes it for every log), then classifies sides against the whole Footage and re-applies `overrides.json`.
3. Tag each candidate with the shot vocabulary: `motion` ∈ locked · push_in · pull_back · drift · pan_left · pan_right · forward_walk · handheld; `light` ∈ golden_hour · overcast · blue_hour · night · interior. Speech is a soft flag: the author talking behind the camera is fine, music covers it (candidates over it carry flag `speech`). Only on-camera speech is a reject: a second touched by a `far` segment with `side_confidence` ≥ 0.5 (padded 0.3 s) is unusable with `why: speech_on_camera`.
4. Print one line per clip: best candidate in/out, quality score, tags, flags.
5. Where no candidate survives the filters, say so: that clip is a reject for this Footage, with the reason.

**Overrides.** The author corrects the automatic rules in `<footage>/shotlog/overrides.json`: `{"<clip>": {"reject": [[in_s, out_s, "reason"]], "allow": [[in_s, out_s]]}}`, e.g. `{"IMG_0412": {"reject": [[0.6, 3.3, "speech_on_camera"]]}}`. Each range covers every second it touches. They are applied last: `allow` clears all automatic flags in its seconds, then `reject` adds its reason (default `override`), so a reject wins over an allow. Re-apply after editing with `.venv/bin/python -m cf.shotlog --all <footage>` (up-to-date logs are only re-scored, about a second) or `--speech-only` (also redoes Whisper, levels and faces). The applied entry is copied into the log as `overrides`.

Done when every clip in the manifest has a Shot log and the summary table has been shown to the user.
