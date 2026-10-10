---
name: beat-grid
description: Turn the user's Track into beats, downbeats, sections and an energy curve, then place the Script's cuts on the grid as cuts.json. Use when a Track file is given for a Reel, or when the user asks to cut to the music.
---

# Beat grid and cuts

Cutting rules and tool choice: `docs/research/05-music-and-sound/result-a.md`, Table B and "How to express the cuts". The Track is always a file the user supplies; log its origin in `reels/<reel>/music_license.json`.

## Steps

1. Put the Track at `reels/<reel>/track/source.wav` (convert to 48 kHz WAV with ffmpeg if needed) and record `source_url`, `title`, `uploader`, `date`, `license` in `reels/<reel>/music_license.json` from what the user tells you. A rip with unknown rights is a local cutting reference only: say so in `license`.
2. Run `.venv/bin/python -m cf.beats reels/<reel>/track/source.wav -o reels/<reel>/track/beats.json --window 0:60 --click reels/<reel>/track/beats_check.wav` → `beats.json`: `bpm`, `beats`, `downbeats` (Beat This!, MPS then CPU), `energy` (RMS per 0.5 s, normalized to the file max), `sections` (all-in-one-infer; falls back to energy levels on the downbeat grid, `sections_source` says which), `drop`, `intro_end` (first downbeat after the energy passes 35 % of the max) and `sanity` (beat-interval CV must be < 3 %, BPM 60–180; exit code 1 otherwise). all-in-one-infer runs Demucs: about 45 s and 1.8 GB for a 60 s window, so keep `--window` short. Compressed modern tracks have flat RMS; check `intro_end` against the onsets before trusting it.
3. Set the Script's `track` (`track/source.wav`) and `track_in_s` (a whole timeline frame; default `intro_end`). Choose the cut grid from energy: low sections cut every 2 bars, mid every bar, drop every 2 beats. With shots of 1.2–2.5 s and overlays that hold ≥ 2 s, a 120–130 BPM grid gives 3-beat shots and 5-beat overlay shots; put place changes on downbeats. The hook may start one beat before a downbeat so the first cut lands on the next one.
4. Write `cuts.json` (`{"fps", "track_in_s", "shots": [{"id", "record_frame_offset", "duration_frames", "src_in_s", "src_out_s", "beat_index"}], "beat_markers": [{"frame", "t", "beat_index", "downbeat"}]}`), each cut 1 frame (`style.pacing.cut_lead_frames`) before its beat, the end on a downbeat, and copy each shot's `in_s`/`out_s`/`beat_index` into the Script. cf.build takes record frames from `cuts.json` and turns `beat_markers` into timeline markers. Validate the Script and check every shot against `speech_on_camera` and `rejects`; re-render overlays whose shot length changed.
5. Where a shot's `in_s`/`out_s` cannot fill its slot, shorten or extend inside the Clip's candidate segment and note the change; where it cannot, report the shot to the user.

Done when every shot in `script.json` has a frame-accurate entry in `cuts.json` and the total matches `target_length_s`.
