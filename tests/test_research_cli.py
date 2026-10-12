"""python -m cf.research: JSON output of every command on a temp database. No network."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import cli
from cf.research import store as st
from cf.research import watchlist as wl

FIX = Path(__file__).parent / "fixtures" / "research"


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "f.db")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*argv, "--db", self.db])
        return code, out.getvalue(), err.getvalue()

    def json_of(self, *argv):
        code, out, err = self.run_cli(*argv, "--json")
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_watchlist_lifecycle(self):
        w = self.json_of("watchlist", "add", "claude-jobs", "--format", "tech_explainer",
                         "--channel", "yt-main", "--language", "en", "--region", "US",
                         "--query", "claude code agents")
        self.assertEqual((w["name"], w["format_id"], w["author_channel"], w["queries"]),
                         ("claude-jobs", "tech_explainer", "yt-main", ["claude code agents"]))
        self.json_of("watchlist", "add-query", "claude-jobs", "job search automation")
        [listed] = self.json_of("watchlist", "list")
        self.assertEqual(listed["queries"], ["claude code agents", "job search automation"])
        self.assertEqual(listed["channel_count"], 0)
        self.json_of("watchlist", "remove", "claude-jobs")
        self.assertEqual(self.json_of("watchlist", "list"), [])

    def test_show_lists_channels_and_queries(self):
        with st.open_store(self.db) as s:
            wl.create(s, "claude-jobs", format_id="tech_explainer")
            payload = json.loads((FIX / "channels_list_handle.json").read_text())
            wl.add_channel(s, "claude-jobs", "@slowwalks", own=True, transport=lambda m, p: payload)
        shown = self.json_of("watchlist", "show", "claude-jobs")
        self.assertEqual(shown["watchlist"]["name"], "claude-jobs")
        [ch] = shown["channels"]
        self.assertEqual((ch["handle"], ch["subscriber_count"], ch["own"]), ("@slowwalks", 312_000, True))
        removed = self.json_of("watchlist", "remove-channel", "claude-jobs", "@slowwalks")
        self.assertEqual(removed["removed"]["handle"], "@slowwalks")

    def test_human_output_is_a_markdown_table(self):
        self.run_cli("watchlist", "add", "claude-jobs", "--format", "tech_explainer")
        code, out, _ = self.run_cli("watchlist", "list")
        self.assertEqual(code, 0)
        self.assertIn("| claude-jobs |", out)

    def test_errors_exit_1_with_one_line(self):
        code, out, err = self.run_cli("watchlist", "remove", "nope", "--json")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("nope", err)

    def test_add_channel_without_an_api_key_says_so_and_costs_nothing(self):
        self.run_cli("watchlist", "add", "claude-jobs", "--format", "tech_explainer")
        env = {k: v for k, v in os.environ.items() if k != "YOUTUBE_API_KEY"}
        env["CF_ENV_FILE"] = os.path.join(self.dir.name, "no-such.env") if hasattr(self, "dir") else "/nonexistent/.env"
        with mock.patch.dict(os.environ, env, clear=True):
            code, _, err = self.run_cli("watchlist", "add-channel", "claude-jobs", "@slowwalks")
        self.assertEqual(code, 1)
        self.assertIn("YOUTUBE_API_KEY", err)
        q = self.json_of("quota")
        self.assertEqual(sum(b["used"] for b in q["buckets"]), 0)

    def test_bad_channel_reference_is_refused_before_any_call(self):
        self.run_cli("watchlist", "add", "claude-jobs", "--format", "tech_explainer")
        code, _, err = self.run_cli("watchlist", "add-channel", "claude-jobs", "https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(code, 1)
        self.assertIn("video", err)

    def test_taxonomy_list(self):
        rows = self.json_of("taxonomy", "list", "--kind", "visual_layout")
        self.assertEqual(len(rows), 6)
        self.assertEqual({r["status"] for r in rows}, {"approved"})
        self.assertIn("diagnosis", {r["value"] for r in self.json_of("taxonomy", "list")})

    def test_quota(self):
        q = self.json_of("quota")
        self.assertEqual({b["bucket"]: (b["limit"], b["used"]) for b in q["buckets"]},
                         {"default": (10_000, 0), "search": (100, 0)})

    def test_runs_as_a_module(self):
        r = subprocess.run([sys.executable, "-m", "cf.research", "quota", "--json", "--db", self.db],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("buckets", json.loads(r.stdout))


if __name__ == "__main__":
    unittest.main()
