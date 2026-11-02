---
name: mine-hooks
description: Summarize which hooks, storytelling formats, visual layouts and topics work in a Watchlist from its Reference cards, and save the hooks the author picks into the Format's Hook library (formats/<format>/hook-library.md). Use when the author asks what hooks or formats land in a niche, what topics work now, to mine hooks, or to refresh the Hook library before writing a Script.
---

# Mine hooks

Turns the cards of a Watchlist into three summaries and an updated Hook library. A summary takes the Watchlist's Reference published in the window (default 14 days), groups the carded ones (card with an analysis) by one category, and ranks the groups by weight: the sum of their Outlier scores, a Reference without a score counting as 1. The hooks summary ranks hook categories, then, in a second section, hook formulas (grouped after folding case and spaces; only exact matches merge). Each group shows its best examples (Outlier score, views, title, link, spoken hook, formula). A value marked `(предложено)` still waits for `taxonomy approve`. Each summary ends with the outliers of the window without analysis (`без разбора`) (Outlier score ≥ 2 by default): until they are analyzed the summary does not see them. The Hook library belongs to a Format, not to a Watchlist: every Watchlist of a Format feeds the same `formats/<format_id>/hook-library.md`, which `write-script` reads. Vocabulary: `GLOSSARY.md` (section Исследование); card fields: `docs/research/reference-card.md`. CLI: `.venv/bin/python -m cf.research summary|hooks --help`.

## Steps

1. Read `author/how-you-work.md`. If `author/` is missing or that file's headings are empty, `/author-setup` has not run yet: run it for that part (Phase 3, how-you-work), then continue.
2. Pick the Watchlist: the one the author named, else `.venv/bin/python -m cf.research watchlist list` and ask. Note its Format id (`walk-reel` for Walk Reel).
3. Run the three summaries with the author's window (`--days`, default 14; `--min-outlier` for the list without analysis, default 2; `--limit` groups, default 10; `--examples` per group, default 3):
   `.venv/bin/python -m cf.research summary hooks <name>`, `... summary formats <name>`, `... summary topics <name>`.
4. If the list without analysis is not empty, show it once and offer to analyze those first with `/analyze-reference` (best Outlier score first; a few minutes each). If the author agrees, run it per Reference and then rerun step 3. If fewer than 3 cards fall in the window, say the summary is thin and suggest a wider `--days` or more cards before drawing conclusions.
5. Show the summaries in the voice of `author/how-you-work.md`: the tables as printed, then 3–5 lines on what stands out (which hook category and formula carry the outliers, which format and layout, which topics), each claim pointing at an example from the output.
6. Ask which hooks to keep: offer the examples of the top groups by YouTube id. For each pick run `.venv/bin/python -m cf.research hooks save <format_id> <video_id>`; saving the same Reference again updates its entry. Remove a mistaken one with `hooks remove <format_id> <video_id>`.
7. Export: `.venv/bin/python -m cf.research hooks export <format_id>`. It overwrites `formats/<format_id>/hook-library.md` (generated; never edit it by hand). Run it even when nothing new was saved, so the Outlier scores in the file are current.

The artifact is the summaries shown in the chat plus `formats/<format_id>/hook-library.md`; show the author the file's path and its hook count.

Done when the three summaries were shown, the outliers without analysis were offered for analysis, the hooks the author picked are saved, and `hooks export` rewrote the Format's Hook library.
