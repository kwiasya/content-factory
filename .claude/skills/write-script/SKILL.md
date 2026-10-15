---
name: write-script
description: Write the Script for one Reel from the Footage's Shot logs — clip order, hook, overlays, caption, hashtags — and validate it. Use when the author asks for a script, a plan, or a hook for a Reel.
---

# Write a Script

Schema, enums and the writing rules: `docs/script-schema.md`. Voice: `author/how-i-talk.md` (language, tone, example captions, `Never` rules) and the viewer in `author/who-i-am.md`; empty headings there mean `/author-setup` has not run, ask the two questions below and go on. Style: `style.json` (audience, fonts, safe zone, pacing). Hook evidence: `docs/research/06-reels-scripts-and-ai-landscape/result-a.md` Table B, and the Hook library of this Format, `formats/walk-reel/hook-library.md` (a Walk Reel's Format id is `walk-reel`), when it exists: proven hooks from the niche's outliers with formula and Outlier score (`/mine-hooks` regenerates it).

## Steps

1. Read every `shotlog/*.json` and `clip_manifest.json`. Build a one-line card per clip: id, duration, best segments with tags, light, motion, people flags. Reason over the cards, never over frames; open a contact sheet (`.venv/bin/python -m cf.sheet <clip> <in> <out>`) only to settle a choice between two candidates.
2. Ask the author two things if not already known: the place (for `location_tag` and overlays) and whether a Track is already chosen (its tempo shapes shot lengths).
3. Draft 3–5 hooks of different `hook.type`, each paired with the clip that proves it. Every hook clip opens on her figure or outfit in a beautiful place, or on her full body in the location under a situational text hook; this is what reached men on her account in 2026 (see `docs/script-schema.md`, `hook.clip`). Search the Shot logs for a full-body person box in a striking setting, with no speech. Critique them against the writing rules and the `Never` section of `author/how-i-talk.md`; keep one.
4. Write `reels/<reel>/script.json`: order shots for impact (reorder freely), one overlay per scene, a one-line caption in the author's voice (place in `location_tag`), ≤5 hashtags. The default ending is `loop_seamless`: pick the hook from a clip whose preceding seconds are usable, so the last shot can be the run-up into the hook's first frame (see `docs/script-schema.md`, Seamless loop).
   For a landscape clip (DJI, landscape iPhone) leave `reframe` out (default `follow`: a static 9:16 window placed on the person by the build) or set `center` / `pan` with `x` (−1 left … 1 right); never `smart` (black bands). A static window holds only 31.6 % of the frame width, so pick ranges where she stays in one place or moves toward/away from the lens, not across the frame; a 1080p landscape clip is upscaled ×3.56 and looks soft, so prefer 4K sources.
   For a horizontal (16:9, YouTube / feed) video set top-level `"canvas": "landscape"`: 16:9 clips then fill the frame with no reframe, portrait clips are rejected (they would pillarbox), and overlays use the landscape safe zone and positions from `style.json` `canvases.landscape`.
5. Assets (Library cues, `docs/script-schema.md` Assets; skip when the Library has no indexed Pack):
   1. Run `.venv/bin/python -m cf.assets refs <the Video folder or script.json> --json`: every ref the Author wrote in the Video's md files (`brief.md`, `notes.md`, …), resolved, with broken ones and their nearest refs. Place every resolved one first, where its md text says (or at the moment it fits); name every broken one to the Author.
   2. Then candidates by tags: `.venv/bin/python -m cf.library query --category sfx --tag переход --json` (and `face` / `emoji` for reactions; `meme` only when the Author's notes ask for memes). Assets the Author tagged come first and agent tags the Author hid never match; prefer the top of the list: a whoosh or hit on a cut (on the incoming shot at `at_s` 0, or the outgoing one ~0.1 s before its end), a reaction sticker or emoji right after a payoff beat, a sound on the hook frame only when it carries the hook. At most one cue per ~2.5 s of Reel unless the notes ask for more; no picture over the loop seam (it must end 0.5 s before the end); keep `pos` clear of the overlay's anchor.
   3. Never invent a ref. Never write refs into the Video's md files yourself (only the Author does, or you on the Author's dictation in this session): a ref there is what unlocks an Asset of unknown rights.
6. Run `.venv/bin/python -m cf.script_schema validate reels/<reel>/script.json` (it loads the Library itself; `--shared-root` / `--db` for another root); fix every reported rule until it passes. `- WARN` lines (unknown rights allowed, a sticker placed as a still) do not fail; keep them for step 7.
7. Show the author the Script as a shot list table (with an "Assets" column: `@ref at_s`, `pos` / `db`) plus the caption, and list every `WARN` line in the summary. Apply their edits in the JSON, re-validate.

Done when `script.json` validates and the author has seen the shot list.
