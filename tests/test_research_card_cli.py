"""python -m cf.research card validate|save|show and taxonomy approve|reject|list on a temp store and footage root."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import card, cli
from cf.research import store as st
from research_synth import MEASURED, TRANSCRIPT, analysis

VID = "dQw4w9WgXcQ"


class CardCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "f.db")
        root = Path(self.tmp.name) / "footage"
        env = mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(root)})
        env.start()
        self.addCleanup(env.stop)
        self.dir = root / "references" / "lisbon" / VID
        self.dir.mkdir(parents=True)
        (self.dir / "transcript.json").write_text(json.dumps({"segments": [{"words": [
            {"word": f" {w}", "start": float(i)} for i, w in enumerate(TRANSCRIPT.split())]}]}))
        with st.open_store(self.db) as s:
            with s.transaction() as c:
                vid = c.execute("INSERT INTO video (external_id, title) VALUES (?, 'Alfama at dusk')",
                                (VID,)).lastrowid
            card.save(s, vid, MEASURED, path=self.dir / "card.json")

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*argv, "--db", self.db])
        return code, out.getvalue(), err.getvalue()

    def json_of(self, *argv):
        code, out, err = self.run_cli(*argv, "--json")
        self.assertEqual(code, 0, out + err)
        return json.loads(out)

    def write(self, name: str, data: dict) -> str:
        path = Path(self.tmp.name) / name
        path.write_text(json.dumps(data))
        return str(path)

    def test_save_then_show_and_validate_the_stored_card(self):
        saved = self.json_of("card", "save", VID, self.write("a.json", analysis()))
        self.assertEqual(saved["card"]["analysis"], analysis())
        self.assertEqual(saved["proposed"], [])
        self.assertEqual(self.json_of("card", "show", VID)["analysis"], analysis())
        code, out, _ = self.run_cli("card", "validate", VID)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith(f"OK {VID}"), out)
        code, out, _ = self.run_cli("card", "show", VID)
        self.assertEqual(code, 0)
        self.assertIn("So this is Alfama, the oldest part of Lisbon", out)

    def test_an_invalid_analysis_prints_one_violation_per_line_and_exits_1(self):
        bad = analysis(hook__category="shock_value", hook__spoken_hook="Welcome to Porto")
        path = self.write("a.json", bad)
        code, out, _ = self.run_cli("card", "save", VID, path)
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(lines[0], f"INVALID {path} (2 violations)")
        self.assertTrue(lines[1].startswith("- hook.category: 'shock_value' is not an approved hook_category"))
        self.assertTrue(lines[2].startswith("- hook.spoken_hook: not found in the transcript"))
        code, out, _ = self.run_cli("card", "validate", path, "--video", VID)
        self.assertEqual((code, out.splitlines()[0]), (1, f"INVALID {path} (2 violations)"))

    def test_validate_takes_a_whole_card_file_and_its_folder_transcript(self):
        full = {"schema": card.SCHEMA, "measured": MEASURED,
                "analysis": analysis(hook__spoken_hook="Okay, sunset time")}
        (self.dir / "card.json").write_text(json.dumps(full))
        code, out, _ = self.run_cli("card", "validate", str(self.dir / "card.json"))
        self.assertEqual(code, 0, out)

    def test_an_analysis_file_without_a_video_is_refused(self):
        code, out, _ = self.run_cli("card", "validate", self.write("a.json", analysis()))
        self.assertEqual(code, 1)
        self.assertIn("--video", out)

    def test_proposed_values_go_through_taxonomy_approve_and_reject(self):
        saved = self.json_of("card", "save", VID,
                             self.write("a.json", analysis(hook__category="proposed:shock_value")))
        self.assertEqual(saved["proposed"], [{"kind": "hook_category", "value": "shock_value"}])
        [p] = self.json_of("taxonomy", "list", "--status", "proposed")
        self.assertEqual((p["kind"], p["value"]), ("hook_category", "shock_value"))
        ok = self.json_of("taxonomy", "approve", "hook_category", "shock_value")
        self.assertEqual((ok["status"], ok["cards"]), ("approved", [VID]))
        self.assertEqual(self.json_of("card", "show", VID)["analysis"]["hook"]["category"], "shock_value")
        no = self.json_of("taxonomy", "reject", "hook_category", "shock_value")
        self.assertEqual((no["status"], no["cards"]), ("rejected", [VID]))
        code, out, _ = self.run_cli("card", "validate", VID)
        self.assertEqual(code, 1)
        self.assertIn("- hook.category: 'shock_value' was rejected", out)

    def test_an_unknown_reference_is_one_error_line(self):
        code, _, err = self.run_cli("card", "show", "aaaaaaaaaaa")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("error: "), err)


if __name__ == "__main__":
    unittest.main()
