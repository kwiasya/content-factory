---
name: beat-grid
description: Turn the user's Track into beats, downbeats, sections and an energy curve, then place the Script's cuts on the grid as cuts.json. Use when a Track file is given for a Reel, or when the user asks to cut to the music.
---

# Beat grid and cuts

Cutting rules and tool choice: `docs/research/05-music-and-sound/result-a.md`, Table B and "How to express the cuts". The Track is always a file the user supplies; log its origin in `reels/<reel>/music_license.json`.

## Steps

1. Copy the Track to `reels/<reel>/track.wav` (convert to 48 kHz WAV with ffmpeg if needed) and record `source`, `license`, `date` in `music_license.json` from what the user tells you.
2. Run `.venv/bin/python -m cf.beats reels/<reel>/track.wav` → `beats.json`: beats, downbeats (Beat This!), sections with labels (all-in-one-infer), RMS energy per 0.5 s (librosa), detected drop.
3. Choose the cut grid from energy: low sections cut every 2 bars, mid every bar, drop every 2 beats. Assign the Script's shots to grid slots in order; the hook shot starts before the first downbeat so the first cut lands on it.
4. Write `cuts.json`: per shot `record_frame`, `duration_frames` at timeline fps, each cut 1–2 frames before its beat, plus `beat_markers` for review.
5. Where a shot's `in_s`/`out_s` cannot fill its slot, shorten or extend inside the Clip's candidate segment and note the change; where it cannot, report the shot to the user.

Done when every shot in `script.json` has a frame-accurate entry in `cuts.json` and the total matches `target_length_s`.
