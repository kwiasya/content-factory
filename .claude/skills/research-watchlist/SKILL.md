---
name: research-watchlist
description: Create a Watchlist for one niche (Format, Channel, language, seed Reference channels, search queries) in the research store. Use when the author names a niche to research, pastes Reference channels, or asks to set up research for a Format.
---

# Create a Watchlist

A Watchlist scopes all research for one niche and one Format (`GLOSSARY.md`, section Исследование). CLI: `.venv/bin/python -m cf.research watchlist --help`. Adding a channel calls the YouTube Data API (1 unit of 10 000 a day) and needs `YOUTUBE_API_KEY` in the environment.

## Steps

1. Read `author/how-you-work.md`, then `author/who-i-am.md` for the author's Channels and priorities. If `author/` is missing or a heading this step needs is empty (the Channel in `who-i-am.md`, the rules in `how-you-work.md`), `/author-setup` has not run yet: run it for that part, then continue.
2. Collect what the author has not already said, in one batch:
   - **name**: short, folder-safe (`claude-jobs`, `vienna-long`); it becomes `references/<name>/`.
   - **Format** id (`walk-reel`, `tech-explainer`, `travel-long`: the folder name under `formats/`, where the Format's Hook library lands) and the author's **Channel** it serves (the Author's Channel, stored as `author_channel`: a short folder name such as `travelwalks`, where its Briefs land under `channels/<channel>/briefs/`; not a Reference channel).
   - **language** (ISO 639-1, default `en`) and **region** (ISO 3166-1, e.g. `US`), when it matters.
   - **seed Reference channels**: handles or URLs, aiming at 15–20 for the niche; 5 is enough to start.
   - **search queries**: 3–5 phrases a viewer of this niche would type.
   - which of the channels are the author's own (added with `--own`).
3. Create it: `.venv/bin/python -m cf.research watchlist add <name> --format <format> --channel <author-channel> --language <lang> [--region <XX>] [--query "<q>" ...]`.
4. Add every channel: `.venv/bin/python -m cf.research watchlist add-channel <name> <handle-or-url> [--own]`. A channel that is not found or a video link is reported in one line; collect those, keep going, and ask the author for the right channel URL at the end. A quota refusal stops the step: report what was added and when the quota resets.
5. Add queries given after creation with `watchlist add-query <name> "<q>"`.
6. Show the author `.venv/bin/python -m cf.research watchlist show <name>` (the channel table with subscribers and the own flag) and apply their corrections with `add-channel`, `remove-channel`, `add-query`.

Done when `watchlist show <name>` lists the Format, every seed channel the author gave (or a stated reason it is missing) and the queries, and the author has seen that table.
