## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels are used as-is (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Project

Content Factory: an Editor agent that assembles the user's own Instagram Reels (vertical, 45–60 s, travel walks) in DaVinci Resolve Studio 21.1.1 on a MacBook Air M2 8 GB. Terms: `GLOSSARY.md`. Plan and decisions: `docs/research/SYNTHESIS.md`, `docs/adr/`. Pipeline skills in order: `/reel`; research contour (Watchlist → Reference → Hook library → Idea): skills map `/research`, CLI `python -m cf.research`, store `~/Movies/content-factory/factory.db`. Resolve API rules: `docs/resolve-rules.md`. Script format: `docs/script-schema.md`. Python runs from `.venv` (3.12); footage and outputs live in `~/Movies/content-factory/<walk>/`, never in the repo.

## Author

Before writing any text the author will post (hook, overlay, caption) or acting on their behalf, read `author/who-i-am.md`, `author/how-i-talk.md`, `author/how-you-work.md`. Rules in `how-you-work.md` hold in every session. `author/` is gitignored and personal to this Mac; if it is missing or a heading is empty, `/author-setup` has not run yet; run it when a task needs that answer.

## Git

Commits carry no Co-Authored-By or other AI attribution lines. Author is the configured git identity (Anastasiia <kwiasya27@gmail.com>).
