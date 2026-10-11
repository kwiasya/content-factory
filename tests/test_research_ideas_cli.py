"""python -m cf.research ideas … on a temp store and footage root."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import cli
from cf.research import store as st
from cf.research import watchlist as wl
from datetime import datetime, timedelta, timezone

from research_synth import V1, V2, V3, add_card, add_member, add_videos, analysis, fields, iso, video_item
from research_synth import CHANNEL_A as A


def ago(days: float = 0, hours: float = 0) -> str:
    return iso(datetime.now(timezone.utc) - timedelta(days=days, hours=hours))


class IdeasCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "f.db")
        self.root = Path(self.tmp.name) / "footage"
        env = mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        with st.open_store(self.db) as s:
            wl.create(s, "lisbon", format_id="walk_reel", author_channel="travelwalks")
            add_member(s, "lisbon", A, "@alpha")
            add_videos(s, [video_item(f"base{i:07d}", A, ago(days=10 + i), 40, 1000) for i in range(5)]
                       + [video_item(V1, A, ago(days=2), 40, 9000, title="Alfama at dusk"),
                          video_item(V2, A, ago(days=3), 40, 5000, title="Porto stairs"),
                          video_item(V3, A, ago(days=4), 40, 3000, title="Sintra fog")])
            for v in (V1, V2, V3):
                add_card(s, v, analysis())

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*argv, "--db", self.db])
        return code, out.getvalue(), err.getvalue()

    def ok(self, *argv):
        code, out, err = self.run_cli(*argv)
        self.assertEqual(code, 0, out + err)
        return out

    def json_of(self, *argv):
        return json.loads(self.ok(*argv, "--json"))

    def write(self, data) -> str:
        path = Path(self.tmp.name) / "idea.json"
        path.write_text(json.dumps(data))
        return str(path)

    def add_one(self, sources=(V1,), **over) -> int:
        return self.json_of("ideas", "add", "lisbon", self.write({"sources": list(sources), **fields(**over)}))[0]["id"]

    def test_add_one_or_many_then_list(self):
        self.add_one()
        added = self.json_of("ideas", "add", "lisbon", self.write([
            {"sources": [V2], **fields(title="Porto stairs, worst to best")},
            {"sources": [f"https://youtu.be/{V3}"], **fields(title="Sintra in fog")}]))
        self.assertEqual([i["status"] for i in added], ["inbox", "inbox"])
        rows = self.json_of("ideas", "list", "lisbon")
        self.assertEqual([r["title"] for r in rows][1:], ["Porto stairs, worst to best", "Sintra in fog"])
        self.assertEqual(rows[2]["sources"][0]["external_id"], V3)
        table = self.ok("ideas", "list", "lisbon")
        self.assertIn("| ID | Статус |", table)
        self.assertIn("Sintra in fog", table)
        self.assertIn("inbox", table)

    def test_add_invalid_prints_violations_and_writes_nothing(self):
        path = self.write([{"sources": [V1], **fields()}, {"sources": [V2], **fields(personalizations=["x"])}])
        code, out, _ = self.run_cli("ideas", "add", "lisbon", path)
        self.assertEqual(code, 1)
        self.assertIn("INVALID", out)
        self.assertIn("[1] personalizations: must be a list of exactly 3 non-empty strings", out)
        self.assertEqual(self.json_of("ideas", "list", "lisbon"), [])

    def test_add_with_a_source_object_prints_the_violation(self):
        code, out, err = self.run_cli("ideas", "add", "lisbon", self.write({"sources": [{"url": V1}], **fields()}))
        self.assertEqual(code, 1)
        self.assertIn("store id, YouTube id or URL", out + err)
        self.assertNotIn("Traceback", out + err)

    def test_add_without_sources(self):
        code, out, err = self.run_cli("ideas", "add", "lisbon", self.write(fields()))
        self.assertEqual(code, 1)
        self.assertIn("sources", out + err)

    def test_triage_and_status_filter(self):
        a, b = self.add_one(), self.add_one(sources=(V2,))
        self.assertIn("inbox → shortlisted", self.ok("ideas", "shortlist", str(a)))
        self.assertEqual(self.json_of("ideas", "discard", str(b))["status"], "discarded")
        self.assertEqual(self.json_of("ideas", "restore", str(b))["status"], "inbox")
        self.assertEqual([r["id"] for r in self.json_of("ideas", "list", "lisbon", "--status", "shortlisted")], [a])

    def test_forbidden_move_is_one_error_line(self):
        a = self.add_one()
        code, out, err = self.run_cli("ideas", "restore", str(a))
        self.assertEqual(code, 1)
        self.assertEqual(err.strip(), f"error: Idea {a} is inbox; restore needs an Idea that is discarded")

    def test_note_and_show(self):
        a = self.add_one()
        self.ok("ideas", "note", str(a), "Shoot it in Tbilisi")
        shown = self.json_of("ideas", "show", str(a))
        self.assertEqual(shown["notes"][0]["text"], "Shoot it in Tbilisi")
        text = self.ok("ideas", "show", str(a))
        self.assertIn("Shoot it in Tbilisi", text)
        self.assertIn("Do it in Tbilisi's old town", text)
        self.assertIn(V1, text)

    def test_brief_then_refuse(self):
        a = self.add_one()
        self.ok("ideas", "shortlist", str(a))
        got = self.json_of("ideas", "brief", str(a), "--channel", "second", "--format", "travel_long")
        path = Path(got["brief_path"])
        self.assertEqual(path.parent, self.root / "channels" / "second" / "briefs")
        self.assertIn("- Format: travel_long", path.read_text())
        code, _, err = self.run_cli("ideas", "brief", str(a))
        self.assertEqual(code, 1)
        self.assertIn(str(path), err)

    def test_candidates(self):
        self.add_one(sources=(V2,))
        rows = self.json_of("ideas", "candidates", "lisbon", "--days", "30")
        self.assertEqual([r["external_id"] for r in rows], [V1, V3])
        self.assertEqual(rows[0]["outlier"], 9.0)
        table = self.ok("ideas", "candidates", "lisbon", "--min-outlier", "5")
        self.assertIn("Alfama at dusk", table)
        self.assertNotIn("Sintra fog", table)


if __name__ == "__main__":
    unittest.main()
