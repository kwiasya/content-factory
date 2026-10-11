---
name: suggest-ideas
description: Turn the analyzed top outliers of a Watchlist into 3–7 Ideas for the author's Channel, put them in the inbox, and let the author triage them (shortlist, discard, note) and turn chosen ones into Briefs. Use when the author asks what to make next, for video ideas from a niche, to fill or review the Idea inbox, or for a Brief.
---

# Suggest Ideas

Turns what worked in a Watchlist's Reference into Idea rows for the author's Channel (`GLOSSARY.md`, section Исследование: Idea, Brief). The fields are those of the Sandcastles Idea Detail page (`docs/research/sandcastles-map.md`, "Поля Idea"). CLI: `.venv/bin/python -m cf.research ideas --help`. Statuses: `inbox` → `shortlisted` | `discarded`; `discarded` → `inbox` (restore); `shortlisted` → `brief` (only through `ideas brief`). Any other move exits 1 and names the current status.

## Steps

1. Read `author/who-i-am.md` and `author/how-you-work.md`. If `author/` is missing or their headings are empty, stop and tell the author to run `/author-setup` first. The Channel, its audience and the viewer described there are who every personalization is for.
2. Pick the Watchlist: the one the author named, else `.venv/bin/python -m cf.research watchlist list` and ask.
3. Get the input: `.venv/bin/python -m cf.research ideas candidates <name> --json` (analyzed Reference of the last 30 days that no Idea uses yet, best Outlier score first; `--days`, `--min-outlier 2` for a strict pick, `--limit`, default 10). If it is empty, stop: say so and point to `/scout-references` for fresh outliers and `/analyze-reference` for the ones marked `без разбора` in the feed.
4. Read the evidence: `.venv/bin/python -m cf.research card show <id> --json` for every candidate (summary, idea analysis, hook, storytelling format, measured numbers), and `.venv/bin/python -m cf.research ideas list <name> --json` so no new Idea repeats one already in the inbox, shortlist or a Brief.
5. Write 3–7 Ideas into one JSON file, a list of objects, in the scratchpad (not the repo). An Idea may draw on several candidates that share an idea seed. Each object:
   - `sources`: the candidates' YouTube ids it comes from.
   - `title`: the video the author would make, not the Reference's title.
   - `summary`: what the video is and why it should work, 1–2 sentences, citing the Outlier score or the measured evidence that backs it.
   - `content_positioning`: the unique angle, moved to the author's Channel.
   - `storytelling_format`: `{"category", "why"}`; the category is an approved `storytelling_format` value (`.venv/bin/python -m cf.research taxonomy list --kind storytelling_format`), or `proposed:<snake_case>` when none fits; `why` says why the format carries this idea.
   - `contrast_mechanism`: `{"common_belief", "contrarian_reality"}` taken from or sharpened beyond the cards, or `null` when the idea challenges nothing.
   - `hook_alignment`: which source hook formula opens the author's video and how the rest keeps its promise.
   - `personalizations`: exactly three different ways to adapt the idea for the author's Channel and its viewer from `who-i-am.md` (place, Clips the author can actually film, angle, language), each one concrete enough to shoot.
6. Save: `.venv/bin/python -m cf.research ideas add <name> <file>`. It checks every Idea first and writes none on `INVALID`; fix each listed violation (`[n]` is the Idea's index in the list) and run it again until it saves.
7. Show the inbox: `.venv/bin/python -m cf.research ideas list <name> --status inbox`, then one line per new Idea with its summary, in the voice of `how-you-work.md`. Offer `ideas show <id>` for the full card.
8. Apply only what the author says: `ideas shortlist <id>`, `ideas discard <id>`, `ideas restore <id>` (a discarded Idea back to the inbox), `ideas note <id> "<text>"` (appends with a timestamp, any status). For each Idea the author wants as a Brief, shortlist it first, then `ideas brief <id>` (`--channel` and `--format` when it is not for the Watchlist's Author's Channel or Format); report the file path. A second `brief` for the same Idea refuses and names the existing file: point the author there. Filling the Brief's shot list is the author's next step, not this skill's.

Done when `ideas add` saved the new Ideas, the author has seen the inbox table, and every triage decision or Brief the author asked for is applied.
