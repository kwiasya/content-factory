# Shared setup: one store, References and Library for two Macs

Two people share the research store, the References and the Library over SMB; each keeps their own Footage and Videos (ADR 0013, `GLOSSARY.md`: Shared root, Local root). This page is the setup on both Macs, the one-off move and merge of the two stores, the `db` commands, and recovery. Steps marked **[author]** need sudo, System Settings or credentials and are done by the author; **[Nastya]** likewise on her Mac; the agent runs the rest, one step at a time, and stops at every checkpoint.

## Layout

```
/Users/madvil2/Shared/                         SMB share "Shared" on the author's Mac
  content-factory/                             the real shared folder (inherited ACLs for madvil2 and nastaglusenko)
    factory.db                                 the research store (+ factory.db-journal during writes)
    secrets.env                                API keys for both people, mode 600
    backups/                                   factory-<YYYYMMDD-HHMM>-<label>.db
    references/<watchlist|_adhoc>/<id>/        References of both people
    library/<pack>/                            the Library cache
    packs/<name>/                              Packs both people use ("davinci templates", memes, memes-inbox)
/Users/Shared/content-factory                  the canonical path, a symlink on BOTH Macs; what the code and the store use
  author's Mac:  -> /Users/madvil2/Shared/content-factory
  Nastya's Mac:  -> /Volumes/Shared/content-factory      (smb://<author-mac>.local/Shared mounted as nastaglusenko)
~/Movies/content-factory/                      each person's local root: Footage, videos/, channels/ (Briefs), _models/
```

Stored paths are absolute and use `/Users/Shared/content-factory/...`. With the share not mounted the symlink dangles and every command that needs the store or a shared file stops with the mount hint; nothing is created locally. Desk still starts and serves Videos, Formats and documents.

## Settings: `.env` and `secrets.env`

| File | Holds | Who |
|---|---|---|
| `<repo>/.env` (gitignored) | `CF_PERSON` (default: the macOS user name), optional `CF_LOCAL_ROOT`, `CF_SHARED_ROOT`, `CF_FACTORY_DB` | each person, never secrets |
| `<shared root>/secrets.env` | `YOUTUBE_API_KEY`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, `INSTAGRAM_USER_ID` | one file for both, mode 600 |

Order: the shell wins over `.env`, which wins over `secrets.env`. `CF_ENV_FILE` and `CF_SECRETS_FILE` point at other files (the tests point both at missing ones). `ig token-refresh` rewrites the token line in the file it came from; if the atomic write fails over SMB, the author runs it on his Mac. Both people share one YouTube quota and one Instagram rate bucket.

## `db` commands

| Command | Does |
|---|---|
| `python -m cf.research db check [--db P]` | read-only: path and resolved path, schema version, `journal_mode` (must be `delete`), `quick_check`, size, newest backup per label, whether the shared root is mounted; exit 1 on any problem |
| `db init [--db P]` | creates the store; the only command that does |
| `db backup [--label L]` | copies the store into `backups/` (label `manual` by default) |
| `db migrate` | migrates to this checkout's schema version after a `git pull` (any CLI command does it too, with a `pre-v<N>` backup first; Desk never migrates) |
| `db renumber [--db P]` | repairs a store migrated by the pre-merge checkout (Library as V6, idea_video as V7; every command on it fails with this hint), backup `pre-renumber` first, then migrates; idempotent |
| `db merge --base A --other N --out OUT --other-person NAME [--packs skip\|import] [--dry-run]` | merges two stores into a new file; inputs are only read; prints and saves `<OUT>.merge-report.json`; deletes `OUT` on any FAIL and on `--dry-run` |

Backups: `daily` at the first CLI command of the day (after a passing `quick_check`; a failing one stops the command and never overwrites good backups), `pre-scout`, `pre-snapshot`, `pre-fetch`, `pre-own`, `pre-index`, `pre-pack-remove` before those commands (the newest 10 kept), the newest 14 `daily`; `pre-v<N>`, `pre-renumber`, `manual` and any other label are kept until removed by hand.

## Move and merge, author's Mac (A)

A0. The code is on the branch the author runs and the tests are green. Add `CF_SHARED_ROOT=/Users/madvil2/Movies/content-factory` to `.env` (until A6). Repair the author's store: `python -m cf.research db renumber`, then `db check`. This alone unblocks the author's research CLI.

A1. Dry runs. `du -sh ~/Movies/content-factory/{factory.db,references,library} "/Users/madvil2/Movies/Videos/davinci templates"`; `python -m cf.library pack list`; `pgrep -fl "cf\.|uvicorn|DaVinci"` is empty here and Nastya confirms nothing of hers runs. **[Nastya]** copies her LIVE `~/Movies/content-factory/factory.db` to `/Users/madvil2/Shared/content-factory/factory.db` and stops using her local store from now on. Merge dry run:

```sh
python -m cf.research db merge --base ~/Movies/content-factory/factory.db \
  --other /Users/madvil2/Shared/content-factory/factory.db \
  --out /Users/madvil2/Shared/content-factory/merge/factory.db --other-person anastasiiahlushchenko --dry-run
```

Expected on the 2026-10-15 copies: 3 watchlists, 495 channels, 8 110 videos, 16 cards, 15 335 snapshots, 100 insights, 21 picks, 37 watchlist_channel, 701 search_hit, 80 taxonomy (2 proposed kept, 3 approved from Nastya), 20 notes, 8 quota, 13 rate, 1 pack, 97 asset_author (the author's 93 untouched, and 4 of Nastya's `memes` Pack kept for its re-add in N7), 85 aliases; Packs `memes` and `memes-inbox` reported as skipped with the re-add command; every check PASS.

**Checkpoint: the author confirms the move and the merge.**

A2. Backups: `python -m cf.research db backup --label pre-shared`; copy Nastya's file to `/Users/madvil2/Shared/content-factory/backups/factory-<ts>-nastya-pre-merge.db`.

A3. The merge for real (A1 without `--dry-run`); the report says PASS; `python -m cf.research db check --db /Users/madvil2/Shared/content-factory/merge/factory.db`.

A4. Move the shared parts and place the merged store (renames on one volume):

```sh
S=/Users/madvil2/Shared/content-factory
mkdir -p $S/packs $S/backups
mv ~/Movies/content-factory/references $S/references
mv ~/Movies/content-factory/library    $S/library
mv ~/Movies/content-factory/backups/*  $S/backups/
mv ~/Movies/content-factory/factory.db $S/backups/factory-<ts>-author-pre-merge.db
mv ~/Movies/content-factory/factory.db.bak-pre-v7-20261014-2355 $S/backups/factory-20261014-2355-pre-v7.db
mv $S/factory.db $S/backups/factory-<ts>-nastya-copy.db
mv $S/merge/factory.db $S/factory.db && mv $S/merge/factory.db.merge-report.json $S/backups/ && rmdir $S/merge
mv "/Users/madvil2/Movies/Videos/davinci templates" "$S/packs/davinci templates"
ln -s /Users/madvil2/Shared/content-factory /Users/Shared/content-factory
ln -s /Users/Shared/content-factory/factory.db  ~/Movies/content-factory/factory.db
ln -s /Users/Shared/content-factory/references  ~/Movies/content-factory/references
ln -s /Users/Shared/content-factory/library     ~/Movies/content-factory/library
ln -s "/Users/Shared/content-factory/packs/davinci templates" "/Users/madvil2/Movies/Videos/davinci templates"
```

The symlinks under `~/Movies` are for habits only; `cf.*` never uses them.

A5. Inherited ACLs on the real folder for both users:

```sh
for u in madvil2 nastaglusenko; do chmod -R +a "$u allow read,write,append,delete,delete_child,add_file,add_subdirectory,readattr,writeattr,readextattr,writeextattr,readsecurity,list,search,file_inherit,directory_inherit" /Users/madvil2/Shared/content-factory; done
```

A6. Point the code at the share: delete the `CF_SHARED_ROOT` line from `.env`. **[author]** creates `/Users/Shared/content-factory/secrets.env` (mode 600) with `YOUTUBE_API_KEY` from his `.env`; Nastya adds the four `INSTAGRAM_*` lines (N3); the secrets leave both personal `.env` files. Pack: set `root` in `.claude/skills/index-pack/packs/davinci-templates.json` to `/Users/Shared/content-factory/packs/davinci templates`; `python -m cf.library pack add --config .claude/skills/index-pack/packs/davinci-templates.json` (same id, Author fields kept); `python -m cf.library index davinci-templates` (incremental; a full ~10-minute rebuild is acceptable).

A7. Rewrite the old absolute prefix `/Users/madvil2/Movies/content-factory/references` to `/Users/Shared/content-factory/references` in the `shotlog.json` and `info.json` files under `references/`; print counts before and after. New fetches write the Shot log's clip path relative to the Reference folder.

A8. **[author]** File Sharing exports `Shared`; give `nastaglusenko` Read & Write; turn guest access off for `Shared` (System Settings, or `sudo sharing -e Shared -g 000`). The Mac's name for the URL: `scutil --get LocalHostName`.

A9. Verify: `db check` (path `/Users/Shared/content-factory/factory.db` resolved to `/Users/madvil2/Shared/...`, current version, `delete`, `ok`); `watchlist list` shows 3 Watchlists; `feed me-walks` shows Instagram rows; `card show <ig code>` and `card show <yt id>`; `notes list --all` shows the 20 Notes; `cf.library pack list` shows the new root; `cf.library query --category face` returns Assets; Desk: `#/agent` shows both roots and the person, `#/library` tiles and previews load, `#/contour` lists three Watchlists, `#/videos` unchanged. **[author]** Resolve opens a project that uses a template through the old path with media online.

A10. Commit the repo changes (the Pack config root) when the author asks. Nothing under the share is ever committed.

## Nastya's Mac (N)

N1. **[Nastya]** Finder → Connect to Server → `smb://<author-mac>.local/Shared` as `nastaglusenko` (not guest); it mounts at `/Volumes/Shared` (if `/Volumes/Shared-1` appears, eject the other volume first); add it to Login Items.

N2. `ln -s /Volumes/Shared/content-factory /Users/Shared/content-factory`.

N3. `git pull` (the checkout must have store V10), `uv pip install --python .venv/bin/python -e '.[desk,research]'`, `npm --prefix web install && npm --prefix web run build`; `.env` gets `CF_PERSON` only if she wants a name other than her macOS user; **[Nastya]** adds her four `INSTAGRAM_*` lines to `/Users/Shared/content-factory/secrets.env` and deletes them from her `.env`.

N4. Copy her References to the share once (no name clash with the author's Watchlists): `rsync -a ~/Movies/content-factory/references/ /Users/Shared/content-factory/references/`. Her `library/` cache is not copied; `index` rebuilds it after N7.

N5. `python -m cf.research db check`; `watchlist list` (3 rows); `feed me-walks` shows her picks; `card show <ig code>`; `notes list --all` shows her 20 Notes. ACLs both ways: she runs `touch /Users/Shared/content-factory/.nastya-test` and the author deletes it; she deletes a file the author made. One write: `notes add general "Nastya connected"`, the author resolves it. Then her local store is renamed `~/Movies/content-factory/factory.db.local-pre-shared` (kept, unused).

N6. `python -m cf.desk` → `#/agent` shows both roots, her name and no "not mounted" line; `#/contour` shows `me-walks`; `#/library` lists the author's Pack and plays a preview; `#/videos` lists her Videos.

N7. Her Packs: move `memes` into `/Users/Shared/content-factory/packs/memes/` and copy the iCloud `Мемы` folder to `packs/memes-inbox/` (iCloud cannot be shared in place); set each config's `root` to the canonical path in `.claude/skills/index-pack/packs/`, then `python -m cf.library pack add --config <config>` and `index <id>` for each. The 4 Author rows of `memes` kept by the merge attach again because the id stays `memes`. Until then the Library shows only `davinci-templates`.

N8. Unmount test: eject the volume; `python -m cf.research watchlist list` exits 1 with the mount hint; nothing appears under `/Volumes`, `/Users/Shared` or her local root; Desk `#/videos` still works; remount.

## Rollback and restore

Before A8, or later with everyone stopped: move the folders back, remove the five symlinks, put `backups/factory-<ts>-author-pre-merge.db` back as `~/Movies/content-factory/factory.db` (already renumbered; `backups/factory-*-pre-renumber.db` restores the old numbering if an old checkout must read it), restore the Pack `root` and `pack add`, put `CF_SHARED_ROOT` back in `.env`. Nastya keeps her local store until N5, so her side rolls back by pointing `CF_SHARED_ROOT` at her local root.

Restore a damaged store (`db check` reports a failing `quick_check`, or a command says so): stop Desk and every `cf.*` on both Macs; `cp` the newest good file from `backups/` over `factory.db` (remove a stale `factory.db-journal` only if no process runs); `db check`. Writes since that backup are lost; re-run `scout` or `snapshot` to refill measurements.
