---
name: reel
description: Map of the Editor's skills for a Reel, in order.
disable-model-invocation: true
---

# Reel skills

One Walk becomes one or more Reels through these skills, in order. Each produces one artifact and stops.

| Step | Skill | Artifact |
|---|---|---|
| 00 | `author-setup` | `author/*.md` — once per clone, again when the author's voice or rules change |
| 0 | `resolve-smoke` | `docs/research/smoke-results.md` — run once per Resolve update |
| 1 | `ingest-walk` | `<walk>/clip_manifest.json` + 540p proxies |
| 2 | `analyze-clips` | `<walk>/shotlog/<clip>.json` |
| 3 | `write-script` | `<walk>/reels/<reel>/script.json` |
| 4 | `beat-grid` | `<walk>/reels/<reel>/cuts.json` (needs a Track from the author) |
| 5 | `build-reel` | Resolve project + timeline, overlays on V2/V3 |
| 6 | `render-reel` | `<walk>/reels/<reel>/out/<reel>.mp4`, verified |

`<walk>` is `~/Movies/content-factory/<walk-id>/`. Vocabulary: `GLOSSARY.md`. Plan and evidence: `docs/research/SYNTHESIS.md`.

Shortest path to a first Reel: 0 → 1 → 5 with a hand-written `script.json` and no overlays → 6.
