---
name: ingest-walk
description: Turn a folder of raw Clips into a Walk — clip_manifest.json with device, fps, rotation and color profile per clip, plus 540p SDR proxies. Use when the user points at new footage or names a folder of clips.
---

# Ingest a Walk

Color detection table and its evidence: `docs/research/03-color-iphone-osmo/result-a.md` Table A; confirmed on real files in `docs/research/samples-first-walk.md`.

## Steps

1. Resolve the source folder the user named. Create `~/Movies/content-factory/<walk-id>/` with `raw/`, `proxy/`, `shotlog/`, `reels/`. `<walk-id>` is `<place>-<YYYY-MM-DD>` from the clips' creation date; ask only if the place is unknown.
2. Copy clips into `raw/` (never move the originals).
3. Run `.venv/bin/python -m cf.probe raw/` → `clip_manifest.json`. Per clip: device make/model, width/height, rotation, fps (`r_frame_rate`), VFR flag (`avg_frame_rate` differs), duration, pixel format and range, `color_profile` with `confidence` and `source_field`, creation time with timezone, GPS if present.
4. Any clip with `confidence < high` (Osmo without a profile tag, Apple Log guess): list them to the user with the evidence and ask for the profile. Record the answer in the manifest as `source_field: user`.
5. Run `.venv/bin/python -m cf.proxy raw/ proxy/` sequentially: 540×960, SDR Rec.709 (tone-mapped for HLG, LUT for log), no audio, videotoolbox encode.
6. Print the manifest as a table: clip, device, fps, duration, profile.

Done when every clip in `raw/` has a manifest entry with a `high` or `user` confidence profile and a proxy file of the same stem.
