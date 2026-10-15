"""references relativize: absolute paths in Reference JSON files become relative or canonical."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from cf.research import cli, refpaths

OLD = "/Users/anastasiiahlushchenko/Movies/content-factory/references"


class RelativizeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ref = self.root / "references" / "me-walks" / "DAbc"
        self.ref.mkdir(parents=True)
        (self.ref / "shotlog.json").write_text(json.dumps(
            {"clip": {"id": "DAbc", "path": f"{OLD}/me-walks/DAbc/DAbc.mp4"}, "shots": [1, 2]}))
        (self.ref / "info.json").write_text(json.dumps(
            {"title": "x", "_filename": f"{OLD}/me-walks/DAbc/DAbc.mp4",
             "related": [f"{OLD}/_adhoc/Other/proxy.mp4", "https://example.com/references/x"]}))
        (self.ref / "card.json").write_text(json.dumps({"analysis": {"summary": "no paths"}}))
        self.untouched = (self.ref / "card.json").read_bytes()

    def test_own_files_become_relative_and_others_canonical(self):
        r = refpaths.relativize(self.root).to_dict()
        self.assertEqual((r["files"], r["absolute_paths_before"], r["foreign_paths_after"]), (3, 3, 0))
        self.assertEqual(sorted(r["changed_files"]), ["references/me-walks/DAbc/info.json",
                                                      "references/me-walks/DAbc/shotlog.json"])
        shotlog = json.loads((self.ref / "shotlog.json").read_text())
        self.assertEqual(shotlog, {"clip": {"id": "DAbc", "path": "DAbc.mp4"}, "shots": [1, 2]})
        info = json.loads((self.ref / "info.json").read_text())
        self.assertEqual(info["_filename"], "DAbc.mp4")
        self.assertEqual(info["related"], [f"{self.root}/references/_adhoc/Other/proxy.mp4",
                                           "https://example.com/references/x"])
        self.assertEqual((self.ref / "card.json").read_bytes(), self.untouched)
        again = refpaths.relativize(self.root).to_dict()
        self.assertEqual((again["changed_files"], again["foreign_paths_after"]), ([], 0))

    def test_dry_run_writes_nothing_and_the_cli_reports(self):
        before = (self.ref / "shotlog.json").read_bytes()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["references", "relativize", "--root", str(self.root), "--dry-run", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["absolute_paths_before"], 3)
        self.assertEqual((self.ref / "shotlog.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
