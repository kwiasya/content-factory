---
name: render-reel
description: Render the reviewed Reel from Resolve as 1080×1920 SDR and verify the file — color tags, pixel format, loudness. Use after the user has finished edits in Resolve, or to re-render.
---

# Render and verify

Export settings and their reasons: `docs/research/03-color-iphone-osmo/result-a.md` Section D. Loudness: `docs/research/05-music-and-sound/result-a.md` Table C.

## Steps

1. Ask the user to confirm edits in Resolve are done; the render reads the timeline as it is now, including their changes.
2. Run `.venv/bin/python -m cf.render reels/<reel>/`: loads render preset `cf-instagram-1080x1920` (H.264 High, 8-bit 4:2:0, 20–25 Mbps, AAC 48 kHz, `ColorSpaceTag` Rec.709, `GammaTag` Rec.709-A), queues the job, polls `GetRenderJobStatus` until done → `out/<reel>.mp4`.
3. Verify with ffprobe: `bt709/bt709/bt709`, `color_range=tv`, `yuv420p`, 1080×1920, 30 fps, no DOVI side data. Measure loudness with ffmpeg `loudnorm` print mode; target −14 LUFS integrated, −1 dBTP.
4. If loudness is off, normalize the audio with two-pass `loudnorm` into `out/<reel>.mp4` (video stream copied) and re-verify.
5. Report the file path, duration, size and the verification table.

Done when the verification table passes on the file in `out/`.
