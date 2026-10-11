---
name: write-script
description: Write the Script for one Reel from the Walk's Shot logs — clip order, hook, overlays, caption, hashtags — and validate it. Use when the user asks for a script, a plan, or a hook for a Reel.
---

# Write a Script

Schema, enums and the writing rules: `docs/script-schema.md`. Style: `style.json` (audience, fonts, safe zone, pacing). Hook evidence: `docs/research/06-reels-scripts-and-ai-landscape/result-a.md` Table B.

## Steps

1. Read every `shotlog/*.json` and `clip_manifest.json`. Build a one-line card per clip: id, duration, best segments with tags, light, motion, people flags. Reason over the cards, never over frames; open a contact sheet (`.venv/bin/python -m cf.sheet <clip> <in> <out>`) only to settle a choice between two candidates.
2. Ask the user two things if not already known: the place (for `location_tag` and overlays) and whether a Track is already chosen (its tempo shapes shot lengths).
3. Draft 3–5 hooks of different `hook.type`, each paired with the clip that proves it. Critique them against the writing rules; keep one.
4. Write `reels/<reel>/script.json`: order shots for impact (reorder freely), one overlay per scene, caption led by the place name, ≤5 hashtags. The default ending is `loop_seamless`: pick the hook from a clip whose preceding seconds are usable, so the last shot can be the run-up into the hook's first frame (see `docs/script-schema.md`, Seamless loop).
   For a landscape clip (DJI, landscape iPhone) leave `reframe` out (default `follow`: a static 9:16 window placed on the person by the build) or set `center` / `pan` with `x` (−1 left … 1 right); never `smart` (black bands). A static window holds only 31.6 % of the frame width, so pick ranges where she stays in one place or moves toward/away from the lens, not across the frame; a 1080p landscape clip is upscaled ×3.56 and looks soft, so prefer 4K sources.
5. Run `.venv/bin/python -m cf.script_schema validate reels/<reel>/script.json`; fix every reported rule until it passes.
6. Show the user the Script as a shot list table plus the caption. Apply their edits in the JSON, re-validate.

Done when `script.json` validates and the user has seen the shot list.
