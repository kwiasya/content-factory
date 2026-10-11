---
name: scout-references
description: Refresh a Watchlist from YouTube (new uploads of its Reference channels, its search queries, today's snapshots of views, likes and comments) and show its feed ordered by Outlier score. Use when the author asks what is working in a niche, for the latest outliers, to refresh or scout a Watchlist, or before analyzing a Reference.
---

# Scout References

Turns a Watchlist into a fresh feed of Reference ranked by Outlier score (`GLOSSARY.md`, section Исследование): views from the latest snapshot ÷ the median of the same channel's last 30 videos of the same kind (short ≤ 180 s, long otherwise) that are at least 3 days old. No score (`—`) means the channel has fewer than 5 such videos yet. CLI: `.venv/bin/python -m cf.research scout|snapshot|feed --help`. Calls need `YOUTUBE_API_KEY` in the environment. Quota: uploads and snapshots cost 1 unit of 10 000 a day per call (50 videos per call); every search page costs 1 of 100 search calls a day. Check with `.venv/bin/python -m cf.research quota`.

## Steps

1. Read `author/how-you-work.md`. If `author/` is missing or that file's headings are empty, `/author-setup` has not run yet: run it for that part (Phase 3, how-you-work), then continue.
2. Pick the Watchlist: the one the author named, else `.venv/bin/python -m cf.research watchlist list` and ask. If none exists, stop and point to `/research-watchlist`.
3. Scout: `.venv/bin/python -m cf.research scout <name> --json`. The first run per channel pages its uploads until 30 videos of each kind are known (or the history ends); later runs read only new uploads. Search reads one page of 50 per query from the last 30 days (`--search-days`, `--search-pages`, `--duration short` for Reels-length searches, `--no-search` when the search bucket is short). A refusal before the start (exit 1, `quota:` line) means nothing was spent: report it with the reset time (midnight Pacific) and stop. A non-null `stopped` means the quota ran out midway: what was read is kept, a later run resumes; say so and go on to the feed.
4. Snapshot: `.venv/bin/python -m cf.research snapshot <name> --json`. One row per Reference per run; history is kept, so running it daily builds velocity data. Mention `missing` videos (deleted or private) in one line.
5. Show the feed: `.venv/bin/python -m cf.research feed <name>` with the author's filters (`--days`, default 30; `--min-outlier`; `--min-views`; `--kind short|long`; `--max-duration 60` for Walk Reel work; `--limit`, default 20). Paste its report lines as they are: number, Outlier score, views, date, title, handle, link, `без разбора` when the card has no analysis yet (not fetched, or fetched and only measured), `кандидат` when the video came from a search on a channel outside the Watchlist.
6. Next step, in a short list after the feed: the outliers marked `без разбора` (score ≥ 2, or the top 5 if fewer qualify), each with its link, for `/analyze-reference`; and the candidate channels from the scout output with the most hits, for `.venv/bin/python -m cf.research watchlist add-channel <name> <handle>` if the author wants them as Reference channels.

Done when the scout and snapshot ran (or the quota stop is reported), and the author has seen the feed and the list of outliers without analysis.
