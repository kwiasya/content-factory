---
name: analyze-reference
description: Write the analysis of one Reference (summary, idea, hook, storytelling format, visual layout) into its card, validated against the taxonomy and the transcript. Use when the author gives a YouTube link to break down, picks an outlier from the feed, or asks why a video worked.
---

# Analyze a Reference

Turns one Reference into a full card `cf-reference-card/1`: the `measured` section from `fetch`, plus the `analysis` section the Editor writes here. Field reference, the `proposed:` rule and an example: `docs/research/reference-card.md`. Vocabulary: `GLOSSARY.md` (section Исследование). CLI: `.venv/bin/python -m cf.research card|taxonomy|fetch --help`. The Reference folder is `~/Movies/content-factory/references/<watchlist or _adhoc>/<video_id>/` (`fetch --json` prints it as `dir`).

## Steps

1. Read `author/how-you-work.md`. If `author/` is missing or its headings are empty, stop and tell the author to run `/author-setup` first.
2. Pick the Reference: the URL or id the author gave, else the top uncarded outlier of `.venv/bin/python -m cf.research feed <watchlist>` (ask which Watchlist if it is not known, and confirm the pick).
3. Make sure a measured card exists: `.venv/bin/python -m cf.research card show <id> --json`. On an `error:` line ending in `run fetch first`, run `.venv/bin/python -m cf.research fetch <url> --watchlist <name> --json` (drop `--watchlist` for a one-off link); it downloads, transcribes and measures, a few minutes on this Mac. Report any `FAILED` step in one line and go on with what was measured.
4. Read the evidence: `measured` from the card (spoken hook of the first 3 s, cuts per minute, first shot, first on-screen text, first person and face, sections, chapters, heatmap peaks with quotes, `notes`), the full text of `<dir>/transcript.json`, and title and description from `<dir>/info.json`. Open a contact sheet (`.venv/bin/python -m cf.sheet <dir>/proxy.mp4 0 <duration_s> -o <dir>/sheet.png`) only when the visual layout is still in doubt after that.
5. Load the vocabulary: `.venv/bin/python -m cf.research taxonomy list --json`. Pick each category from the approved values of its kind: `hook.category` from `hook_category`, `storytelling_format.category` from `storytelling_format`, `visual_layout.category` from `visual_layout`, `visual_layout.sub_category` from `editing_style`. Write `proposed:<snake_case_value>` only when no approved value fits, and say why in the field's text.
6. Write `<dir>/analysis.json` with every field of the reference doc. `hook.spoken_hook` is copied word for word from the transcript (it may run past 3 s; null only for a video without speech). Every claim in `supporting_evidence` and `alignment` points at a moment, a quote or a measured number.
7. Save: `.venv/bin/python -m cf.research card save <id> <dir>/analysis.json`. It validates first; on `INVALID` fix every listed violation in the file and run it again until it saves.
8. Show the author the card (`.venv/bin/python -m cf.research card show <id>`) in the voice of `author/how-you-work.md`, and list the values awaiting approval at its end with the commands `taxonomy approve|reject <kind> <value>`. Apply the author's edits to `analysis.json` and save again.

Done when `card save` succeeded, and the author has seen the card and every proposed value it introduced.
