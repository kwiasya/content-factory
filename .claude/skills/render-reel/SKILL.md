---
name: render-reel
description: Render the reviewed Reel from Resolve as 1080×1920 SDR and verify the file — color tags, pixel format, loudness. Use after the user has finished edits in Resolve, or to re-render.
---

# Render and verify

Export settings and their reasons: `docs/research/03-color-iphone-osmo/result-a.md` Section D. Loudness: `docs/research/05-music-and-sound/result-a.md` Table C.

## Steps

1. Ask the user to confirm edits in Resolve are done; the render reads the timeline as it is now, including their changes.
2. Run `.venv/bin/python -m cf.render <walk>/reels/<reel>/` (`--walk`, `--out`, `--preset` optional). It opens project `cf-<walk>-<reel>` (it never creates one) and timeline `<reel>`. It creates or updates render preset `cf-instagram-1080x1920` (mp4 / H.264 High, 1080×1920, 30 fps, about 22 Mbit/s, AAC 48 kHz, `ColorSpaceTag` Rec.709, `GammaTag` Rec.709-A), deletes this timeline's old jobs, queues one job and polls `GetRenderJobStatus` until done → `out/<reel>.mp4`. Then it restores the UI page and writes `out/render-report.json`.
3. The same command then runs `python -m cf.render_check out/<reel>.mp4`. It checks with ffprobe: `bt709/bt709/bt709`, `color_range=tv`, `yuv420p`, 1080×1920, 30 fps, no DOVI side data, AAC 48 kHz, and duration = timeline length. It measures loudness with ffmpeg `loudnorm` print mode (target −14 LUFS ±1, true peak ≤ −1 dBTP), prints a PASS/FAIL table, writes `out/render-check.json`, and exits non-zero on FAIL.
4. If only loudness fails, re-run with `--fix-loudness` (on `cf.render`, or on `cf.render_check <file>` to skip the re-render). It writes `out/<reel>.normalized.mp4`: two-pass `loudnorm` with the video stream copied, repeated on its own output (at most 3 rounds) when loudnorm falls back to dynamic mode. Then it re-checks that file. Upload the `.normalized.mp4` when it exists.
5. Report the file path, duration, size, render time and the verification table.

Done when the verification table passes on the file in `out/` that will be uploaded.
