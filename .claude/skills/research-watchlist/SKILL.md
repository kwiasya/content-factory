---
name: research-watchlist
description: Create a Watchlist for one niche (Format, Channel, language, seed Reference channels on YouTube and Instagram, search queries, the author's own reel links with her notes) in the research store. Use when the author names a niche to research, pastes Reference channels or Instagram accounts and reels, or asks to set up research for a Format.
---

# Create a Watchlist

A Watchlist scopes all research for one niche and one Format (`GLOSSARY.md`, section Исследование) and may hold channels of both Platforms. CLI: `.venv/bin/python -m cf.research watchlist --help`. Adding a YouTube channel calls the YouTube Data API (1 unit of 10 000 a day) and needs `YOUTUBE_API_KEY`. Adding an Instagram account calls Business Discovery (1 call of the hourly `instagram` bucket, 100 in any 60 minutes) and needs `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID` (ADR 0007); it sees public business and creator accounts only. Keys live in `.env` (see `.env.example`); never print them.

## Steps

1. Read `author/how-you-work.md`, then `author/who-i-am.md` for the author's Channels and priorities. If `author/` is missing or a heading this step needs is empty (the Channel in `who-i-am.md`, the rules in `how-you-work.md`), `/author-setup` has not run yet: run it for that part, then continue.
2. Collect what the author has not already said, in one batch:
   - **name**: short, folder-safe (`claude-jobs`, `vienna-long`), not starting with `_` (reserved: `references/_adhoc/` holds References fetched without a Watchlist); it becomes `references/<name>/`.
   - **Format** id (`walk-reel`, `tech-explainer`, `travel-long`: the folder name under `formats/`, where the Format's Hook library lands) and the author's **Channel** it serves (the Author's Channel, stored as `author_channel`: a short folder name such as `travelwalks`, where its Briefs land under `channels/<channel>/briefs/`; not a Reference channel).
   - **language** (ISO 639-1, default `en`) and **region** (ISO 3166-1, e.g. `US`), when it matters.
   - **seed Reference channels**: YouTube handles or URLs, Instagram accounts as `ig:<username>` or `instagram.com/<username>` links, aiming at 15–20 for the niche; 5 is enough to start. The author's own picks come first, ahead of any research list.
   - **search queries**: 3–5 phrases a viewer of this niche would type. They run on YouTube only: Instagram has no search API.
   - **single reels** the author wants studied (Instagram reel or post links) and her note on each, word for word.
   - which of the channels are the author's own (added with `--own`).
3. Create it: `.venv/bin/python -m cf.research watchlist add <name> --format <format> --channel <author-channel> --language <lang> [--region <XX>] [--query "<q>" ...]`.
4. Add every channel: `.venv/bin/python -m cf.research watchlist add-channel <name> <handle-or-url> [--own]` (Instagram: `ig:<username>`). A channel that is not found, a video link, or an Instagram account Business Discovery cannot see (personal or private) is reported in one line; collect those, keep going, and tell the author at the end. A quota refusal stops the step: report what was added and when the quota resets (YouTube: midnight Pacific; Instagram: calls leave the window an hour after they were made). Keep the author's note on an account verbatim as a Note: `.venv/bin/python -m cf.research notes add channel instagram:@<username> "<note>"`.
5. Add the author's single reels: `.venv/bin/python -m cf.research watchlist add-reference <name> <link> --note "<her note, verbatim>"` (one link per call when it has a note; several links without notes in one call). Run `/scout-references` first when the Watchlist has Instagram accounts: a reel the scout already read needs no yt-dlp call. The owner comes from yt-dlp metadata (no login, no cookies, a pause between calls, stops after two refusals in a row), then Business Discovery of the owner; otherwise the link is kept unresolved with its note. Tracking parameters are dropped. Links to other sites (X, TikTok) are out of scope: leave them where the author put them.
6. Add queries given after creation with `watchlist add-query <name> "<q>"`.
7. Show the author `.venv/bin/python -m cf.research watchlist show <name>` (the channel table with subscribers and the own flag) and apply their corrections with `add-channel`, `remove-channel`, `add-query`.

Done when `watchlist show <name>` lists the Format, every seed channel the author gave (or a stated reason it is missing) and the queries, every reel link she gave is picked (resolved or with the reason it is not), and the author has seen that table.
