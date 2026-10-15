"""Merge two research stores into a new file (``db merge``, ADR 0013): a one-off tool kept in the repo.

The inputs are copied with SQLite's backup API from ``mode=ro`` connections and never written. The copy
of ``base`` becomes ``out`` (renumbered when it is in the pre-merge numbering, then migrated); the copy of
``other`` (``<out>.other.tmp``, migrated too, deleted at the end) is read row by row and imported into
``out`` in dependency order inside one transaction, with maps other id → out id for Watchlists,
channels, videos and Ideas:

- ``taxonomy`` by (kind, value): new values are added; a base ``proposed`` value takes the other's
  verdict (``approved``/``rejected``); every other difference keeps base and is reported;
- ``watchlist`` by name (queries united), ``channel`` and ``video`` by (platform, external_id) (flags
  ORed, tags and marks united, the later scout marks kept), ``snapshot``/``insight`` by (video, taken_at),
  ``card`` by video (the newer ``written_at`` wins, reported), the link tables by their keys;
- ``hook`` and ``idea`` are added with remapped ids (``source_video_ids`` too); the other's Briefs,
  Video links and video Notes get ``other_person`` as owner where they have none;
- ``note`` is added unless the same (kind, key, text, created_at) is there;
- ``quota`` sums calls and units per (day, method), ``rate`` keeps base per (minute, method),
  ``rate_pressure`` keeps the later reading per bucket;
- Packs: a Pack whose id is already in base is skipped with its Author rows and aliases. ``skip`` imports
  a Pack row only when its root is a folder on this Mac; for any other Pack it keeps the Author rows and
  aliases (keyed by content id and Pack id, they attach again when the Pack is re-added under the same id)
  and reports the command that re-adds it. ``import`` copies every Pack row whose id is free as it is.

Verification: per table ``merged == base + other - matched - skipped``, ``foreign_key_check`` empty,
``integrity_check`` ok, the schema version, every other video present (with its title and publish time when it was new),
every other card's analysis byte for byte under its new video id (unless a newer base card won), every
other Note present, base Library rows unchanged, inputs unchanged (sha256). Any failure, and every dry run,
deletes ``out``.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Callable

from cf.research import renumber
from cf.research import store as st

PACK_MODES = ("skip", "import")
TABLES = ("taxonomy", "watchlist", "channel", "video", "snapshot", "insight", "card", "watchlist_channel",
          "watchlist_pick", "search_hit", "hook", "idea", "idea_video", "note", "quota", "rate", "rate_pressure",
          "pack", "asset_author", "asset_alias")
VERDICTS = ("approved", "rejected")


class MergeError(st.StoreError):
    """The merge cannot start (inputs, output path) or an import step met data it cannot place."""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy(src: Path, dest: Path) -> None:
    source = st.connect(src, readonly=True)
    try:
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def _prepare(path: Path) -> sqlite3.Connection:
    conn = st.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    if st.old_numbering(conn):
        renumber.apply(conn)
    st.Store(conn, None).migrate()
    return conn


def _rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    return [dict(r) for r in conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid')]


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])


def _union(a: str | None, b: str | None) -> str:
    out = list(json.loads(a or "[]"))
    out += [x for x in json.loads(b or "[]") if x not in out]
    return st.dumps(out)


def _later(a: str | None, b: str | None) -> str | None:
    return max((x for x in (a, b) if x), default=None)


class _Import:
    def __init__(self, out: sqlite3.Connection, other: sqlite3.Connection, person: str, packs: str,
                 is_dir: Callable[[str], bool]):
        self.out, self.other, self.person, self.packs, self.is_dir = out, other, person, packs, is_dir
        self.maps: dict[str, dict[int, int]] = {t: {} for t in ("watchlist", "channel", "video", "idea")}
        self.matched = {t: 0 for t in TABLES}
        self.skipped = {t: 0 for t in TABLES}
        self.events: list[dict] = []
        self.failures: list[str] = []
        self.in_base: set[int] = set()

    def one(self, sql: str, params: tuple) -> dict | None:
        row = self.out.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def insert(self, table: str, row: dict, *, keep_id: bool = False) -> int:
        data = {k: v for k, v in row.items() if keep_id or k != "id"}
        cols = ", ".join(f'"{k}"' for k in data)
        marks = ", ".join("?" for _ in data)
        return int(self.out.execute(f'INSERT INTO "{table}" ({cols}) VALUES ({marks})', tuple(data.values())).lastrowid)

    def update(self, table: str, where: str, params: tuple, values: dict) -> None:
        sets = ", ".join(f'"{k}" = ?' for k in values)
        self.out.execute(f'UPDATE "{table}" SET {sets} WHERE {where}', (*values.values(), *params))

    def mapped(self, table: str, other_id: int | None, where: str) -> int | None:
        if other_id is None:
            return None
        got = self.maps[table].get(other_id)
        if got is None:
            self.failures.append(f"{where}: {table} id {other_id} of the other store has no row to map to")
        return got

    def run(self) -> None:
        for step in (self.taxonomy, self.watchlists, self.channels, self.videos, self.measures, self.cards,
                     self.links, self.hooks, self.ideas, self.idea_videos, self.notes, self.quota, self.rate,
                     self.library):
            step()

    def taxonomy(self) -> None:
        for r in _rows(self.other, "taxonomy"):
            b = self.one("SELECT * FROM taxonomy WHERE kind = ? AND value = ?", (r["kind"], r["value"]))
            if b is None:
                self.insert("taxonomy", r)
                continue
            self.matched["taxonomy"] += 1
            diff = {f: [b[f], r[f]] for f in ("status", "label", "note", "source") if b[f] != r[f]}
            if not diff:
                continue
            verdict = b["status"] == "proposed" and r["status"] in VERDICTS
            if verdict:
                self.update("taxonomy", "id = ?", (b["id"],), {"status": r["status"], "source": r["source"]})
            self.events.append({"event": "taxonomy_differs", "kind": r["kind"], "value": r["value"], "diff": diff,
                                "kept": "other's verdict" if verdict else "base"})

    def watchlists(self) -> None:
        for r in _rows(self.other, "watchlist"):
            b = self.one("SELECT id, queries FROM watchlist WHERE name = ?", (r["name"],))
            if b is None:
                self.maps["watchlist"][r["id"]] = self.insert("watchlist", r)
                continue
            self.matched["watchlist"] += 1
            self.update("watchlist", "id = ?", (b["id"],), {"queries": _union(b["queries"], r["queries"])})
            self.maps["watchlist"][r["id"]] = b["id"]
            self.events.append({"event": "watchlist_merged", "name": r["name"]})

    def channels(self) -> None:
        for r in _rows(self.other, "channel"):
            b = self.one("SELECT * FROM channel WHERE platform = ? AND external_id = ?",
                         (r["platform"], r["external_id"]))
            if b is None:
                self.maps["channel"][r["id"]] = self.insert("channel", r)
                continue
            self.matched["channel"] += 1
            self.update("channel", "id = ?", (b["id"],), {
                "own": max(b["own"], r["own"]),
                "backfilled_at": _later(b["backfilled_at"], r["backfilled_at"]),
                "uploads_through": _later(b["uploads_through"], r["uploads_through"])})
            self.maps["channel"][r["id"]] = b["id"]

    def videos(self) -> None:
        for r in _rows(self.other, "video"):
            channel = self.mapped("channel", r["channel_id"], f"video {r['external_id']}")
            b = self.one("SELECT * FROM video WHERE platform = ? AND external_id = ?",
                         (r["platform"], r["external_id"]))
            if b is None:
                self.maps["video"][r["id"]] = self.insert("video", {**r, "channel_id": channel})
                continue
            self.matched["video"] += 1
            self.in_base.add(r["id"])
            diff = {f: [b[f], r[f]] for f in ("title", "published_at") if b[f] != r[f]}
            if diff:
                self.events.append({"event": "video_differs", "external_id": r["external_id"], "diff": diff,
                                    "kept": "base"})
            self.update("video", "id = ?", (b["id"],), {
                "tags": _union(b["tags"], r["tags"]), "marks": _union(b["marks"], r["marks"]),
                "own": max(b["own"], r["own"]), "has_media": max(b["has_media"], r["has_media"]),
                "has_transcript": max(b["has_transcript"], r["has_transcript"])})
            self.maps["video"][r["id"]] = b["id"]

    def measures(self) -> None:
        for table in ("snapshot", "insight"):
            for r in _rows(self.other, table):
                vid = self.mapped("video", r["video_id"], table)
                if self.one(f"SELECT 1 AS x FROM {table} WHERE video_id = ? AND taken_at = ?", (vid, r["taken_at"])):
                    self.matched[table] += 1
                else:
                    self.insert(table, {**r, "video_id": vid})

    def cards(self) -> None:
        for r in _rows(self.other, "card"):
            vid = self.mapped("video", r["video_id"], "card")
            b = self.one("SELECT * FROM card WHERE video_id = ?", (vid,))
            if b is None:
                self.insert("card", {**r, "video_id": vid})
                continue
            self.matched["card"] += 1
            newer = r["written_at"] > b["written_at"]
            if newer:
                self.update("card", "id = ?", (b["id"],), {k: r[k] for k in ("schema", "measured", "analysis",
                                                                              "written_at")})
            self.events.append({"event": "card_in_both", "video_id": vid, "kept": "other" if newer else "base"})

    def links(self) -> None:
        for table, keys in (("watchlist_channel", ("watchlist_id", "channel_id")),
                            ("watchlist_pick", ("watchlist_id", "video_id")),
                            ("search_hit", ("watchlist_id", "video_id", "query"))):
            for r in _rows(self.other, table):
                row = dict(r)
                row["watchlist_id"] = self.mapped("watchlist", r["watchlist_id"], table)
                if "channel_id" in row:
                    row["channel_id"] = self.mapped("channel", r["channel_id"], table)
                if "video_id" in row:
                    row["video_id"] = self.mapped("video", r["video_id"], table)
                where = " AND ".join(f"{k} = ?" for k in keys)
                if self.one(f"SELECT 1 AS x FROM {table} WHERE {where}", tuple(row[k] for k in keys)):
                    self.matched[table] += 1
                else:
                    self.insert(table, row)

    def hooks(self) -> None:
        for r in _rows(self.other, "hook"):
            self.insert("hook", {**r, "source_video_id": self.mapped("video", r["source_video_id"], "hook")})

    def ideas(self) -> None:
        for r in _rows(self.other, "idea"):
            sources = [self.mapped("video", v, f"idea {r['id']} source") for v in json.loads(r["source_video_ids"])]
            owner = r["brief_owner"] or (self.person if r["brief_path"] else None)
            self.maps["idea"][r["id"]] = self.insert("idea", {
                **r, "watchlist_id": self.mapped("watchlist", r["watchlist_id"], "idea"),
                "source_video_ids": st.dumps(sources), "brief_owner": owner})

    def idea_videos(self) -> None:
        for r in _rows(self.other, "idea_video"):
            row = {**r, "idea_id": self.mapped("idea", r["idea_id"], "idea_video"), "owner": r["owner"] or self.person}
            if self.one("SELECT 1 AS x FROM idea_video WHERE idea_id = ? AND owner = ? AND video_slug = ?",
                        (row["idea_id"], row["owner"], row["video_slug"])):
                self.matched["idea_video"] += 1
            else:
                self.insert("idea_video", row)

    def notes(self) -> None:
        for r in _rows(self.other, "note"):
            if self.one("SELECT 1 AS x FROM note WHERE kind = ? AND key = ? AND text = ? AND created_at = ?",
                        (r["kind"], r["key"], r["text"], r["created_at"])):
                self.matched["note"] += 1
                continue
            owner = (r["owner"] or self.person) if r["kind"] == "video" else r["owner"]
            self.insert("note", {**r, "owner": owner})

    def quota(self) -> None:
        for r in _rows(self.other, "quota"):
            b = self.one("SELECT * FROM quota WHERE day = ? AND method = ?", (r["day"], r["method"]))
            if b is None:
                self.insert("quota", r)
                continue
            self.matched["quota"] += 1
            self.update("quota", "day = ? AND method = ?", (r["day"], r["method"]),
                        {"calls": b["calls"] + r["calls"], "units": b["units"] + r["units"]})

    def rate(self) -> None:
        for r in _rows(self.other, "rate"):
            if self.one("SELECT 1 AS x FROM rate WHERE minute = ? AND method = ?", (r["minute"], r["method"])):
                self.matched["rate"] += 1
            else:
                self.insert("rate", r)
        for r in _rows(self.other, "rate_pressure"):
            b = self.one("SELECT * FROM rate_pressure WHERE bucket = ?", (r["bucket"],))
            if b is None:
                self.insert("rate_pressure", r)
                continue
            self.matched["rate_pressure"] += 1
            if r["seen_at"] > b["seen_at"]:
                self.update("rate_pressure", "bucket = ?", (r["bucket"],),
                            {k: r[k] for k in ("seen_at", "pct", "regain_minutes")})

    def library(self) -> None:
        authors = _rows(self.other, "asset_author")
        aliases = _rows(self.other, "asset_alias")
        taken: set[str] = set()
        for p in _rows(self.other, "pack"):
            mine = [a for a in authors if a["pack_id"] == p["id"]]
            ids = {a["asset_id"] for a in mine}
            refs = [a for a in aliases if a["asset_id"] in ids]
            event = {"event": "pack_skipped", "id": p["id"], "root": p["root"], "author_rows": len(mine),
                     "aliases": len(refs),
                     "command": f"python -m cf.library pack add --config <config of {p['id']}> "
                                f"--root /Users/Shared/content-factory/packs/<folder>"}
            taken |= ids
            if self.one("SELECT 1 AS x FROM pack WHERE id = ?", (p["id"],)):
                self.skipped["pack"] += 1
                self.skipped["asset_author"] += len(mine)
                self.skipped["asset_alias"] += len(refs)
                self.events.append({**event, "reason": "a Pack with this id is already in the base store",
                                    "author_rows_kept": False})
                continue
            if self.packs == "skip" and not self.is_dir(p["root"]):
                self.skipped["pack"] += 1
                self.events.append({**event, "reason": "its root is not a folder on this Mac",
                                    "author_rows_kept": True})
            else:
                self.insert("pack", p, keep_id=True)
            for a in mine:
                if self.one("SELECT 1 AS x FROM asset_author WHERE asset_id = ?", (a["asset_id"],)):
                    self.matched["asset_author"] += 1
                else:
                    self.insert("asset_author", a)
            taken |= ids
            for a in refs:
                self._alias(a)
        for a in aliases:
            if a["asset_id"] in taken:
                continue
            if self.packs == "import":
                self._alias(a)
            else:
                self.skipped["asset_alias"] += 1
                self.events.append({"event": "alias_skipped", "ref": a["ref"], "reason": "no imported Pack has it"})

    def _alias(self, a: dict) -> None:
        b = self.one("SELECT asset_id FROM asset_alias WHERE ref = ?", (a["ref"],))
        if b is None:
            self.insert("asset_alias", a)
            return
        self.matched["asset_alias"] += 1
        if b["asset_id"] != a["asset_id"]:
            self.events.append({"event": "alias_differs", "ref": a["ref"], "kept": "base"})


def _changed(conn: sqlite3.Connection, table: str, before: list[dict]) -> bool:
    after = {json.dumps(r, sort_keys=True, ensure_ascii=False) for r in _rows(conn, table)}
    return any(json.dumps(r, sort_keys=True, ensure_ascii=False) not in after for r in before)


def _check(name: str, ok: bool, detail: Any = None) -> dict:
    return {"check": name, "ok": bool(ok), "detail": detail}


def _spot_checks(out: sqlite3.Connection, other: sqlite3.Connection, imp: _Import) -> list[dict]:
    checks = []
    missing = []
    for r in other.execute("SELECT id, platform, external_id, title, published_at FROM video"):
        if r["id"] in imp.in_base:
            continue
        got = out.execute("SELECT title, published_at FROM video WHERE platform = ? AND external_id = ?",
                          (r["platform"], r["external_id"])).fetchone()
        if got is None or (got["title"], got["published_at"]) != (r["title"], r["published_at"]):
            missing.append(r["external_id"])
    checks.append(_check("every other new video present with its title and published_at", not missing,
                         missing[:20]))
    kept_base = {e["video_id"] for e in imp.events if e["event"] == "card_in_both" and e["kept"] == "base"}
    bad = []
    for r in other.execute("SELECT video_id, analysis, measured FROM card"):
        vid = imp.maps["video"].get(r["video_id"])
        if vid in kept_base:
            continue
        got = out.execute("SELECT analysis, measured FROM card WHERE video_id = ?", (vid,)).fetchone()
        if got is None or got["analysis"] != r["analysis"] or got["measured"] != r["measured"]:
            bad.append(r["video_id"])
    checks.append(_check("every other card byte for byte under its new video id", not bad, bad[:20]))
    lost = [r["id"] for r in other.execute("SELECT id, kind, key, text, created_at FROM note")
            if out.execute("SELECT 1 FROM note WHERE kind = ? AND key = ? AND text = ? AND created_at = ?",
                           (r["kind"], r["key"], r["text"], r["created_at"])).fetchone() is None]
    checks.append(_check("every other Note present", not lost, lost[:20]))
    return checks


def merge(base: str | Path, other: str | Path, out: str | Path, *, other_person: str, packs: str = "skip",
          dry_run: bool = False, is_dir: Callable[[str], bool] = lambda p: Path(p).is_dir()) -> dict:
    """Merge ``base`` and ``other`` into the new file ``out``; return the report (see the module docstring)."""
    base, other, out = Path(base).expanduser(), Path(other).expanduser(), Path(out).expanduser()
    if packs not in PACK_MODES:
        raise MergeError(f"--packs must be one of {', '.join(PACK_MODES)}")
    if not other_person.strip():
        raise MergeError("--other-person names whose local rows the other store holds; it cannot be empty")
    for p in (base, other):
        if not p.is_file():
            raise MergeError(f"no store at {p}")
    tmp = out.with_name(out.name + ".other.tmp")
    for p in (out, tmp):
        if p.exists():
            raise MergeError(f"{p} already exists; the merge writes a new file only")
    made_dir = not out.parent.exists()
    out.parent.mkdir(parents=True, exist_ok=True)
    sums = {"base": [sha256(base)], "other": [sha256(other)]}
    report: dict[str, Any] = {"base": str(base), "other": str(other), "out": str(out), "dry_run": dry_run,
                              "other_person": other_person, "packs": packs}
    conn = oconn = None
    try:
        _copy(base, out)
        _copy(other, tmp)
        conn, oconn = _prepare(out), _prepare(tmp)
        base_counts = {t: _count(conn, t) for t in TABLES}
        other_counts = {t: _count(oconn, t) for t in TABLES}
        library_before = {t: _rows(conn, t) for t in ("asset_author", "asset_alias")}
        imp = _Import(conn, oconn, other_person, packs, is_dir)
        conn.execute("BEGIN IMMEDIATE")
        try:
            imp.run()
        except BaseException:
            conn.rollback()
            raise
        conn.commit()
        tables = []
        for t in TABLES:
            merged = _count(conn, t)
            expected = base_counts[t] + other_counts[t] - imp.matched[t] - imp.skipped[t]
            tables.append({"table": t, "base": base_counts[t], "other": other_counts[t], "matched": imp.matched[t],
                           "skipped": imp.skipped[t], "merged": merged, "expected": expected,
                           "ok": merged == expected})
        fk = [list(r) for r in conn.execute("PRAGMA foreign_key_check")]
        integrity = "\n".join(str(r[0]) for r in conn.execute("PRAGMA integrity_check"))
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        changed_library = [t for t, rows in library_before.items() if _changed(conn, t, rows)]
        checks = [_check("import met only mappable rows", not imp.failures, imp.failures[:20]),
                  _check("foreign_key_check empty", not fk, fk[:20]),
                  _check("integrity_check ok", integrity == "ok", integrity.splitlines()[:5]),
                  _check(f"schema version {st.SCHEMA_VERSION}", version == st.SCHEMA_VERSION, version),
                  *_spot_checks(conn, oconn, imp)]
        checks.append(_check("base Library rows unchanged", not changed_library, changed_library))
        report.update(tables=tables, checks=checks, events=imp.events, version=version)
    except BaseException:
        for c in (conn, oconn):
            if c is not None:
                c.close()
        conn = oconn = None
        _remove(out, made_dir)
        raise
    finally:
        for c in (conn, oconn):
            if c is not None:
                c.close()
        for p in (tmp, tmp.with_name(tmp.name + "-journal")):
            p.unlink(missing_ok=True)
    sums["base"].append(sha256(base))
    sums["other"].append(sha256(other))
    report["inputs_sha256"] = sums
    checks.append(_check("inputs unchanged", all(a == b for a, b in sums.values()), sums))
    report["ok"] = all(t["ok"] for t in tables) and all(c["ok"] for c in checks)
    report["out_kept"] = report["ok"] and not dry_run
    if not report["out_kept"]:
        _remove(out, made_dir and dry_run)
    if not dry_run:
        report_path = out.with_name(out.name + ".merge-report.json")
        report["report_file"] = str(report_path)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def _remove(out: Path, folder: bool) -> None:
    for p in (out, out.with_name(out.name + "-journal")):
        p.unlink(missing_ok=True)
    if folder:
        try:
            out.parent.rmdir()
        except OSError:
            pass
