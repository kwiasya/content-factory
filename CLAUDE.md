## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels are used as-is (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Notes

Before working on a skill or an entity, check its open Notes (`python -m cf.research notes list --kind K --key PATH|ID`; the skill hook prints the skill's own); resolve each one after acting on it (`notes resolve <id>`). See `docs/desk.md`.

## Project

Content Factory: an Editor agent that assembles the user's own Instagram Reels (vertical, 45–60 s, travel walks) in DaVinci Resolve Studio 21.1.1 on a MacBook Pro M5 Max, 36 GB. Terms: `GLOSSARY.md`. Plan and decisions: `docs/research/SYNTHESIS.md`, `docs/adr/`. Pipeline skills in order: `/reel` (Walk Reel; other Formats are described in `formats/<id>/FORMAT.md`); research contour (Watchlist → Reference → Hook library → Idea): skills map `/research-map`, CLI `python -m cf.research`, store `~/Movies/content-factory/factory.db`; editing material (Library of Packs, Asset refs `@<category>/<name>`): skill `/index-pack`, CLI `python -m cf.library`, cache `~/Movies/content-factory/library/` (ADR 0007). Resolve API rules: `docs/resolve-rules.md`. Script format: `docs/script-schema.md`. Python runs from `.venv` (3.12); footage and working files live in `~/Movies/content-factory/<walk>/`, and each Video in `~/Movies/content-factory/videos/<slug>/` (ADR 0006), never in the repo. The author only looks at `~/Movies/Готовые ролики/` (filled by `cf.publish`): refer to finished videos by their names there, not by internal paths. The author views and edits everything in Desk (`python -m cf.desk`, `docs/desk.md`).

## Author

Before writing any text the author will post (hook, overlay, caption) or acting on their behalf, read `author/who-i-am.md`, `author/how-i-talk.md`, `author/how-you-work.md`. Rules in `how-you-work.md` hold in every session. `author/` is gitignored and personal to this Mac; if it is missing or a heading is empty, `/author-setup` has not run yet; run it when a task needs that answer.

## Git

Commits carry no Co-Authored-By or other AI attribution lines. Author is the configured git identity; never set or override it.
