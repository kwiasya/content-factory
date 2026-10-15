---
name: index-pack
description: Index the Author's editing Pack (sounds, memes, emoji, face stickers, backgrounds, footage, fonts, Resolve templates) into the Library — register it, build the index and derived files, import the old catalog's tags, then run the agent tag pass. Use when the Author asks to index, refresh or add a Pack, when Library in Desk says a Pack is not indexed, or after new files land in the Pack.
---

# Index a Pack

A Pack is read in place and never written (`GLOSSARY.md`: Library, Pack, Asset, Asset ref; `docs/adr/0007-packs-read-in-place-cache-derived-author-in-store.md`). Everything derived goes to `<shared root>/library/<pack>/` (`--shared-root`, default `/Users/Shared/content-factory`); the Author's fields live in `factory.db`. A Pack both people use lives under `<shared root>/packs/<name>/` and its config `root` names that canonical path (ADR 0013). CLI: `.venv/bin/python -m cf.library --help`. Every rule (categories, refs, keying, loudness, import) lives in the CLI; this skill only runs it in order. The first Pack's config is `.claude/skills/index-pack/packs/davinci-templates.json` (folder → category mapping; the Author edits it in Desk).

## Steps

0. **One-time unpack** (only when `<root>/montage/Davinci Shrine Pack/` is missing and `<root>/montage/Davinci Shrine Pack (1).rar` exists). Ask the Author first: "Распаковать Davinci Shrine Pack (1.7 ГБ) рядом с архивом? Архив останется." Only on a yes run:
   `mkdir "<root>/montage/Davinci Shrine Pack" && /usr/bin/bsdtar -xf "<root>/montage/Davinci Shrine Pack (1).rar" -C "<root>/montage/Davinci Shrine Pack"`
   (`<root>` is the config's `root`). This is the only write under a Pack root, ever. On a no, go on: the Shrine folders are simply absent from the index.
1. Register (idempotent; re-run after editing the config): `.venv/bin/python -m cf.library pack add --config .claude/skills/index-pack/packs/davinci-templates.json`.
2. Index: `.venv/bin/python -m cf.library index davinci-templates`. The first run hashes ~7 GB, keys 150 emoji and the green-screen footage to ProRes 4444 (≈ 6 GB of cache) and makes previews: 10–15 minutes; progress goes to stderr. Stage it with `--only "<folder>"` (repeatable) or `--no-key` / `--no-previews` / `--no-loudness` when the Author wants it faster; a later run without the flags fills the gaps. A second run on an unchanged Pack probes and derives nothing.
3. Import the old catalog (idempotent):
   `.venv/bin/python -m cf.library import-tags davinci-templates "<root>/montage/1 pack/_каталог/tags.json" --base "montage/1 pack"` and
   `.venv/bin/python -m cf.library import-tags davinci-templates "<root>/montage/1 pack/_каталог/face-stickers/tags.json" --base "montage/1 pack" --names`
   (`--names` makes each face sticker's label its ref, `@face/крик-в-камеру`; the numeric `@face/1750765-sticker` keeps resolving). Report unmatched ids.
4. **Tag pass** (long; may run in its own session). `.venv/bin/python -m cf.library tags todo davinci-templates --sheets` writes `library/davinci-templates/sheets/NN.jpg` with `NN.json` (tile number → Asset id, ref, folder, file name, kind, duration). For each sheet: Read the jpg and its json, write a proposals file in the scratchpad `{"<asset id>": {"caption": "…", "tags": ["…"], "basis": "sheet"}}` — `caption` in Russian, ≤ 60 characters, what is shown or heard; `tags` 3–6 lowercase Russian words: emotion, object, use (`переход`, `удар`, `шок`, `реакция`). Audio tiles are a speaker glyph: caption them from the file name and the function table in `<root>/montage/1 pack/PACK.md`, with `"basis": "name"`. Apply after every sheet (checkpoint): `.venv/bin/python -m cf.library tags apply davinci-templates <proposals.json>`. The tag pass writes agent fields only; never touch the Author's caption, tags, rights or name.
5. Print the index report (`index` output), the fallback folders (media under no mapped folder; propose mapping lines for the config), the import's unmatched ids, and how many Assets still have no agent tags.

Done when `index` reports no errors (or each one is explained), both imports ran, and the Author has seen the report and the fallback folders.
