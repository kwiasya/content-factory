---
name: ingest-footage
description: Turn a folder of raw Clips into Footage — clip_manifest.json with device, fps, rotation and color profile per clip, plus 540p SDR proxies. Use when the user points at new footage or names a folder of clips.
---

# Ingest Footage

Color detection table and its evidence: `docs/research/03-color-iphone-osmo/result-a.md` Table A; confirmed on real files in `docs/research/samples-first-walk.md`.

## Steps

1. Footage id: `<place>-<YYYY-MM-DD>` from the first shooting day; a trip of several days in one place is one Footage. Ask only if the place is unknown.
2. Run `.venv/bin/python -m cf.footage init <footage-id> --from <source>`. It creates `~/Movies/content-factory/<footage-id>/` with `raw/`, `proxy/`, `shotlog/`, `stills/` and links the Clips in place (ADR 0008, `docs/adr/0008-external-material-linked-footage-copied-documents.md`): `raw/` holds absolute symlinks, the originals are never moved or modified. Add `--copy` only when the source is a card or an external drive that will be unplugged. Stills (`.jpg`, `.jpeg`, `.png`, `.heic`) land in `stills/` and are not probed. Re-running is a no-op; an entry that points elsewhere stops it with exit 2.
3. Run `.venv/bin/python -m cf.probe raw/` → `clip_manifest.json`. Per clip: device make/model, width/height, rotation, fps (`r_frame_rate`), VFR flag (`avg_frame_rate` differs), duration, pixel format and range, `color_profile` with `confidence` and `source_field`, creation time with timezone, GPS if present. Each clip's `path` is the real file behind the link.
4. Any clip with `confidence < high` (Osmo without a profile tag, Apple Log guess): list them to the user with the evidence and ask for the profile. Record the answer in the manifest as `source_field: user`.
5. Run `.venv/bin/python -m cf.proxy raw/ proxy/` sequentially: 540 px short side, so 960×540 for landscape and 540×960 for portrait Clips, SDR Rec.709 (tone-mapped for HLG, LUT for log), no audio, videotoolbox encode. On a large Footage run it in the background.
6. Print the manifest as a table: clip, device, fps, duration, profile.

Vertical phone Clips in a landscape Footage are ingested like any other; how they sit on a 16:9 canvas is the build's decision.

Live Photo `.MOV` companions of `.HEIC` stills land in `raw/` as Clips of 2–3 s; leave them out of the source selection (or remove their links from `raw/`) before probing.

Subfolders of the source (a card's `DCIM/…`) are not scanned and are listed as "folders not scanned"; point `--from` at the folder that holds the files. With nothing found, `cf.footage` exits 2 and creates nothing. A link in `raw/` whose target is gone (files moved, drive unplugged) makes `cf.probe` exit 2 without touching `clip_manifest.json`: re-point the link, then probe again.

Done when every Clip in `raw/` (file or link) has a manifest entry with a `high` or `user` confidence profile and a proxy file of the same stem.
