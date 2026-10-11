---
name: research-map
description: Map of the research skills, in order: from a Watchlist to Ideas.
disable-model-invocation: true
---

# Research contour

A niche becomes evidence for hooks, formats and Ideas through these skills, in order. Each produces one artifact and stops.

| Step | Skill | Artifact |
|---|---|---|
| 00 | `author-setup` | `author/*.md`, once per clone |
| 1 | `research-watchlist` | one Watchlist row (Format, Channel, language, Reference channels, queries) |
| 2 | `scout-references` | refreshed Reference rows and today's snapshots for the Watchlist, and its feed of outliers |
| 3 | `analyze-reference` | one Reference card (`cf-reference-card/1`) in the store and under `references/<watchlist>/<video_id>/` |
| 4 | `mine-hooks` | hooks, formats and topics summaries for the Watchlist, and the Format's Hook library export in the repo |
| 5 | `suggest-ideas` | Idea rows in the inbox (status `inbox`) |

Store: `~/Movies/content-factory/factory.db` (override `CF_FACTORY_DB` or `--db`); raw payloads, media, transcripts and cards under `~/Movies/content-factory/references/`. CLI: `.venv/bin/python -m cf.research <group> <cmd> [--json]`; quota left today: `.venv/bin/python -m cf.research quota`. Vocabulary: `GLOSSARY.md` (section Исследование). Plan: GitHub issue #1; the product it reproduces: `docs/research/sandcastles-map.md`.

Shortest path to a first card: 1 → 2 → 3 on the top outlier of the feed.
