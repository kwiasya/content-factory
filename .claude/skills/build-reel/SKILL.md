---
name: build-reel
description: Build the Reel in DaVinci Resolve from script.json and cuts.json — project, 1080×1920 timeline, per-clip color tags, overlays from Remotion on V2/V3, Look, audio levels, markers. Use when a Script is ready to assemble, or to rebuild after Script edits.
---

# Build the Reel in Resolve

API rules: `docs/resolve-rules.md`. Color pipeline: `docs/research/03-color-iphone-osmo/result-a.md` Section B. Overlay path: `docs/research/02-overlays-and-motion-graphics/result-a.md` Section C. Style and safe zone: `style.json`.

## Steps

1. Preconditions: Resolve open; `script.json` validates; `cuts.json` exists (without a Track, derive `cuts.json` from the Script's `in_s`/`out_s` directly and say so).
2. Overlays first, while Resolve is idle: for each shot with an overlay run `npx remotion render` in `overlays/` → `reels/<reel>/overlays/<shot>.mov` (ProRes 4444, alpha, 1080×1920, timeline fps, concurrency 2). Skip when the overlay file is newer than `script.json`.
3. Run `.venv/bin/python -m cf.build reels/<reel>/` which, through `resolve_driver`: creates or reuses project `cf-<walk>-<reel>` from the project settings preset (color managed v2, DWG/Intermediate, HDR 1000 working luminance with inverse DRT, Rec.709 Gamma 2.4 out, 1080×1920, 30 fps); imports `raw/` clips and overlays; forces each clip's `Input Color Space` to the manifest value; deletes any existing timeline of this name and appends V1 shots, V2/V3 overlays, A1 track, A2 ambience by `record_frame`; applies speed, transitions, fades; `AudioVolume` −20 dB on ambience; then the HLG exposure CDL on node 1 of every HLG item (`docs/research/color-hlg-experiment.md`); then the Look LUT from `style.json` `look.lut` (or `--look <file.cube>`) on node 1 of the `cf-look` color group's post-clip graph, with every V1 item in the group (`docs/research/look-experiment.md`; `--stills-only` re-exports stills with a different Look without rebuilding); beat and shot markers with the shot id as `customData`.
4. Read-back report: the driver prints each shot's expected vs actual start/end, every property it set, every mismatch. A mismatch is a failure; fix the driver or the plan, then rebuild.
5. Export one still per shot (`ExportCurrentFrameAsStill`) into `reels/<reel>/stills/` and look at them: overlay inside the safe zone, no clipped HDR, Look applied.
6. Tell the user the timeline is ready for review in Resolve and which shots to check first.

Done when the read-back report has zero mismatches and the stills have been checked.
