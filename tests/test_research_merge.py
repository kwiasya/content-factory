"""db merge: two stores into a new file, the base in the pre-merge numbering, the other at the current version."""

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import cli, merge
from cf.research import store as st
from old_numbering import make_old_store

OTHER_SQL = """
INSERT INTO watchlist (name, format_id, author_channel, language, queries, created_at)
    VALUES ('walks', 'walk-reel', 'me', 'en', '[]', 'x'),
           ('city', 'walk-reel', 'me', 'en', '["old town", "new town"]', 'x');
INSERT INTO channel (platform, external_id, handle, own, backfilled_at) VALUES
    ('instagram', '17841400000000001', '@kwi', 1, NULL),
    ('youtube', 'UCaaaaaaaaaaaaaaaaaaaaaa', '@alpha', 1, '2026-10-05T00:00:00Z');
INSERT INTO video (platform, external_id, channel_id, title, published_at, tags, marks, own) VALUES
    ('instagram', 'DAbc', 1, 'reel one', '2026-10-01T00:00:00Z', '[]', '["closeup_emotion"]', 1),
    ('youtube', 'vid00000001', 2, 'other title', '2026-09-01T00:00:00Z', '["walk"]', '[]', 0),
    ('instagram', 'DPick', NULL, 'picked', '2026-10-02T00:00:00Z', '[]', '[]', 0);
INSERT INTO snapshot (video_id, taken_at, views) VALUES
    (2, '2026-10-01T00:00:00Z', 99), (2, '2026-10-03T00:00:00Z', 20), (1, '2026-10-03T00:00:00Z', 5);
INSERT INTO insight (video_id, taken_at, views, reach) VALUES (1, '2026-10-03T00:00:00Z', 5, 4);
INSERT INTO card (video_id, schema, measured, analysis, written_at)
    VALUES (1, 'reference-card/1', '{"cuts_per_min":3}', '{"summary":"ig ünïcode"}', '2026-10-04T00:00:00Z');
INSERT INTO watchlist_channel (watchlist_id, channel_id, added_at) VALUES (1, 1, 'x'), (2, 2, 'x');
INSERT INTO watchlist_pick (watchlist_id, video_id, added_at) VALUES (1, 3, 'x');
INSERT INTO taxonomy (kind, value, status, source, created_at) VALUES
    ('hook', 'old_proposal', 'approved', 'card:DAbc', 'x'),
    ('hook', 'ig_only', 'approved', 'card:DAbc', 'x');
INSERT INTO idea (watchlist_id, source_video_ids, title, status, brief_path, created_at, updated_at)
    VALUES (1, '[1, 3]', 'an idea', 'brief', '/Users/nastya/Movies/content-factory/channels/me/briefs/1-x.md',
            'x', 'x');
INSERT INTO idea_video (idea_id, owner, video_slug, linked_at) VALUES (1, '', 'reel-a', 'x');
INSERT INTO hook (format_id, category, text, source_video_id, saved_at) VALUES ('walk-reel', 'c', 't', 1, 'x');
INSERT INTO note (kind, key, text, created_at) VALUES
    ('video', 'reel-a', 'tighter cut', 'x'), ('card', 'DAbc', 'nice', 'x'), ('channel', 'instagram:@kwi', 'mine', 'x');
INSERT INTO quota (day, bucket, method, calls, units) VALUES ('2026-10-01', 'youtube', 'videos.list', 3, 3),
    ('2026-10-02', 'youtube', 'search.list', 1, 100);
INSERT INTO rate (minute, bucket, method, calls) VALUES ('2026-10-01T10:00', 'instagram', 'media', 4);
INSERT INTO rate_pressure (bucket, seen_at, pct) VALUES ('instagram', '2026-10-01T10:00:00Z', 12);
INSERT INTO pack (id, root, config, created_at) VALUES
    ('memes', '/nonexistent/memes', '{}', 'x'), ('tpl', '/x/tpl', '{}', 'x');
INSERT INTO asset_author (asset_id, pack_id, rights, updated_at) VALUES ('m1', 'memes', 'free', 'x'),
    ('t9', 'tpl', 'free', 'x');
INSERT INTO asset_alias (ref, asset_id, source, created_at) VALUES ('@meme/one', 'm1', 'catalog', 'x');
"""


def run(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(argv)
    return code, out.getvalue()


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.base, self.other = self.dir / "author.db", self.dir / "other.db"
        self.out = self.dir / "merged" / "factory.db"
        make_old_store(self.base)
        with sqlite3.connect(self.base) as conn:
            conn.executescript("""
                INSERT INTO note (kind, key, text, created_at) VALUES ('card', 'DAbc', 'nice', 'x');
                INSERT INTO idea (watchlist_id, source_video_ids, title, status, brief_path, created_at, updated_at)
                    VALUES (1, '[1]', 'base idea', 'brief', '/Users/author/briefs/1.md', 'x', 'x');
                INSERT INTO idea_video (idea_id, video_slug, linked_at) VALUES (1, 'base-walk', 'x');
                INSERT INTO note (kind, key, text, created_at) VALUES ('video', 'base-walk', 'louder', 'y');
            """)
        st.open_store(self.other, seed=False, create=True).close()
        with sqlite3.connect(self.other) as conn:
            conn.executescript(OTHER_SQL)
        self.sums = (merge.sha256(self.base), merge.sha256(self.other))

    def merged(self, **kw) -> dict:
        return merge.merge(self.base, self.other, self.out, base_person="author", other_person="nastya", **kw)

    def q(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = st.connect(self.out, readonly=True)
        try:
            return [dict(r) for r in conn.execute(sql, params)]
        finally:
            conn.close()

    def test_a_full_merge_passes_and_maps_every_row(self):
        r = self.merged()
        self.assertTrue(r["ok"], json.dumps(r, indent=1))
        self.assertTrue(r["out_kept"])
        self.assertEqual((merge.sha256(self.base), merge.sha256(self.other)), self.sums)
        self.assertTrue(Path(r["report_file"]).is_file())
        counts = {t["table"]: t["merged"] for t in r["tables"]}
        self.assertEqual((counts["watchlist"], counts["channel"], counts["video"], counts["card"]), (2, 2, 3, 2))
        self.assertEqual(self.q("PRAGMA user_version")[0]["user_version"], st.SCHEMA_VERSION)

        alpha = self.q("SELECT * FROM channel WHERE external_id = 'UCaaaaaaaaaaaaaaaaaaaaaa'")[0]
        self.assertEqual((alpha["id"], alpha["own"], alpha["backfilled_at"]), (1, 1, "2026-10-05T00:00:00Z"))
        shared = self.q("SELECT * FROM video WHERE external_id = 'vid00000001'")[0]
        self.assertEqual((shared["id"], shared["title"], shared["tags"]), (1, "first", '["walk"]'))
        self.assertEqual(self.q("SELECT taken_at, views FROM snapshot WHERE video_id = 1 ORDER BY taken_at"),
                         [{"taken_at": "2026-10-01T00:00:00Z", "views": 10},
                          {"taken_at": "2026-10-03T00:00:00Z", "views": 20}])
        self.assertEqual(self.q("SELECT queries FROM watchlist WHERE name = 'city'")[0]["queries"],
                         '["old town","new town"]')

        reel = self.q("SELECT id, channel_id FROM video WHERE external_id = 'DAbc'")[0]
        ig = self.q("SELECT id FROM channel WHERE external_id = '17841400000000001'")[0]["id"]
        self.assertEqual(reel["channel_id"], ig)
        self.assertIsNone(self.q("SELECT channel_id FROM video WHERE external_id = 'DPick'")[0]["channel_id"])
        cards = self.q("SELECT id, video_id, analysis FROM card ORDER BY id")
        self.assertEqual(cards[0]["video_id"], 1)
        self.assertEqual((cards[1]["id"], cards[1]["video_id"], cards[1]["analysis"]),
                         (2, reel["id"], '{"summary":"ig ünïcode"}'))
        self.assertEqual(self.q("SELECT video_id FROM insight"), [{"video_id": reel["id"]}])
        walks = self.q("SELECT id FROM watchlist WHERE name = 'walks'")[0]["id"]
        pick = self.q("SELECT id FROM video WHERE external_id = 'DPick'")[0]["id"]
        self.assertEqual(self.q("SELECT watchlist_id, video_id FROM watchlist_pick"),
                         [{"watchlist_id": walks, "video_id": pick}])

        base_idea, idea = self.q("SELECT * FROM idea ORDER BY id")
        self.assertEqual(base_idea["brief_owner"], "author")
        self.assertEqual((idea["watchlist_id"], json.loads(idea["source_video_ids"]), idea["brief_owner"]),
                         (walks, [reel["id"], pick], "nastya"))
        self.assertEqual(self.q("SELECT idea_id, owner, video_slug FROM idea_video ORDER BY idea_id"),
                         [{"idea_id": base_idea["id"], "owner": "author", "video_slug": "base-walk"},
                          {"idea_id": idea["id"], "owner": "nastya", "video_slug": "reel-a"}])
        self.assertEqual(self.q("SELECT source_video_id FROM hook"), [{"source_video_id": reel["id"]}])

        self.assertEqual(self.q("SELECT kind, key, owner FROM note ORDER BY id"),
                         [{"kind": "card", "key": "DAbc", "owner": ""}, {"kind": "video", "key": "base-walk", "owner": "author"},
                          {"kind": "video", "key": "reel-a", "owner": "nastya"},
                          {"kind": "channel", "key": "instagram:@kwi", "owner": ""}])
        self.assertEqual(self.q("SELECT day, calls, units FROM quota ORDER BY day"),
                         [{"day": "2026-10-01", "calls": 5, "units": 5}, {"day": "2026-10-02", "calls": 1, "units": 100}])
        self.assertEqual(len(self.q("SELECT * FROM rate")), 1)

    def test_taxonomy_a_verdict_wins_over_a_proposal(self):
        r = self.merged()
        self.assertEqual(self.q("SELECT status, source FROM taxonomy WHERE value = 'old_proposal'"),
                         [{"status": "approved", "source": "card:DAbc"}])
        self.assertEqual(len(self.q("SELECT 1 FROM taxonomy WHERE value = 'ig_only'")), 1)
        diffs = [e for e in r["events"] if e["event"] == "taxonomy_differs"]
        self.assertEqual([(e["value"], e["kept"]) for e in diffs], [("old_proposal", "other's verdict")])

    def test_packs_skipped_by_root_keep_their_author_rows_and_a_clashing_id_is_skipped_whole(self):
        r = self.merged()
        skipped = {e["id"]: e for e in r["events"] if e["event"] == "pack_skipped"}
        self.assertEqual(set(skipped), {"memes", "tpl"})
        self.assertTrue(skipped["memes"]["author_rows_kept"])
        self.assertIn("pack add", skipped["memes"]["command"])
        self.assertFalse(skipped["tpl"]["author_rows_kept"])
        self.assertEqual([p["id"] for p in self.q("SELECT id FROM pack")], ["tpl"])
        self.assertEqual(self.q("SELECT root FROM pack")[0]["root"], "/x/tpl")
        self.assertEqual({a["asset_id"] for a in self.q("SELECT asset_id FROM asset_author")}, {"a1", "m1"})
        self.assertEqual({a["ref"] for a in self.q("SELECT ref FROM asset_alias")}, {"@face/one", "@meme/one"})

    def test_a_pack_whose_root_exists_here_is_imported(self):
        self.merged(is_dir=lambda p: p == "/nonexistent/memes")
        self.assertEqual({p["id"] for p in self.q("SELECT id FROM pack")}, {"tpl", "memes"})

    def test_the_two_people_must_be_named_and_differ(self):
        for base_person, other_person in (("", "nastya"), ("author", " "), ("same", "same")):
            with self.assertRaises(merge.MergeError):
                merge.merge(self.base, self.other, self.out, base_person=base_person, other_person=other_person)
        self.assertFalse(self.out.exists())

    def test_a_dry_run_leaves_no_file(self):
        r = self.merged(dry_run=True)
        self.assertTrue(r["ok"])
        self.assertFalse(r["out_kept"])
        self.assertFalse(self.out.parent.exists())
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["author.db", "other.db"])

    def test_an_existing_out_is_refused(self):
        self.out.parent.mkdir()
        self.out.write_bytes(b"x")
        with self.assertRaises(merge.MergeError):
            self.merged()
        self.assertEqual(self.out.read_bytes(), b"x")

    def test_a_failed_check_deletes_the_out_file_and_exits_1(self):
        bad = [{"check": "forced", "ok": False, "detail": None}]
        with mock.patch.object(merge, "_spot_checks", return_value=bad):
            code, out = run(["db", "merge", "--base", str(self.base), "--other", str(self.other), "--out",
                             str(self.out), "--base-person", "author", "--other-person", "nastya", "--json"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out)["ok"])
        self.assertFalse(self.out.exists())
        self.assertFalse(Path(str(self.out) + ".other.tmp").exists())

    def test_cli_merge_prints_the_report(self):
        code, out = run(["db", "merge", "--base", str(self.base), "--other", str(self.other), "--out",
                         str(self.out), "--base-person", "author", "--other-person", "nastya", "--dry-run"])
        self.assertEqual(code, 0, out)
        self.assertIn("PASS", out)
        self.assertIn("memes", out)

    def test_the_merged_store_merges_again_as_a_no_op_other(self):
        self.merged()
        again = merge.merge(self.out, self.other, self.dir / "twice.db", base_person="author", other_person="nastya", dry_run=True)
        self.assertTrue(again["ok"], json.dumps(again, indent=1))
        counts = {t["table"]: (t["merged"], t["base"]) for t in again["tables"]}
        for table in ("channel", "video", "snapshot", "card", "note", "watchlist_pick"):
            self.assertEqual(counts[table][0], counts[table][1], table)


if __name__ == "__main__":
    unittest.main()
