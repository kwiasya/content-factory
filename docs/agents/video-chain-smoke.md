# Video chain routing smoke (dry-run)

No render. Checks that `/produce` routing language maps asks → Format → chain → first agents.

## Walk Reel

**Ask:** "Собери Walk Reel из footage `lisbon-2026-04-01`."

| Step | Expected |
|---|---|
| Format | `walk-reel` |
| Chain | Walk (material-first) |
| First launch | `video-planner` |
| Planner → makers | `video-footage` → `video-writer` → (`video-sound` if Track) → `video-picture` → `video-finish` → `video-checker` |
| Skills named | `/ingest-footage`, `/analyze-clips`, `/write-script`, `/beat-grid`, `/build-reel`, `/render-reel` |
| Not used | `video-motion`, HyperFrames, Anime/Pixi kit |

## Motion / Tech explainer

**Ask:** "Сделай Remotion explainer по brief в `videos/autopilot-intro/`."

| Step | Expected |
|---|---|
| Format | `tech-explainer` (or freeform motion) |
| Chain | Motion (script-first) |
| First launch | `video-planner` |
| Planner → makers | `video-writer` → `video-sound` (VO first) → `video-motion` → `video-finish` → `video-checker` |
| Skills / kit | author voice, Chatterbox or VO files, `overlays/CLAUDE.md`, `/remotion-best-practices` |
| Not used | `/build-reel` Resolve timeline as the primary picture path |

## Ambiguous

**Ask:** "Сделай видео про Лиссабон."

Expected: producer or planner stops with two routes (Walk from Footage vs motion explainer); `NEEDS_INPUT`; no silent pick.

## Pass

Routing tables in `/produce` and `docs/agents/video-chain.md` match the rows above; all nine agents exist under `.claude/agents/video-*.md`.
