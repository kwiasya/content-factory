"""python -m cf.research summary hooks|formats|topics and hooks save|list|export|remove: JSON and Russian text."""

import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cf.research import cli
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import add_member, add_videos, iso, video_item
from test_research_summary import hook, put_card

A = "UCaaaaaaaaaaaaaaaaaaaaaa"


def real_ago(days=0):
    return iso(datetime.now(timezone.utc) - timedelta(days=days))


class SummaryCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "f.db")
        with st.open_store(self.db) as s:
            wl.create(s, "lisbon", format_id="walk-reel")
            add_member(s, "lisbon", A, "@alpha")
            add_videos(s, [video_item(f"baseline0{i:02d}", A, real_ago(days=20 + i), 40, 1000) for i in range(6)]
                       + [video_item("alfamaDawn1", A, real_ago(days=1), 40, 5000, title="Alfama | at dawn"),
                          video_item("steepLisbn3", A, real_ago(days=1), 40, 3000, title="Why so steep?"),
                          video_item("uncardHit01", A, real_ago(days=1), 40, 4000, title="Uncarded hit")])
            put_card(s, "alfamaDawn1", hook("visual_payoff", "Place name + superlative", "So this is Alfama"))
            put_card(s, "steepLisbn3", hook("proposed:steep_question", "Why is <place> steep?", "Why so steep"))

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

    def test_summary_hooks_json_has_groups_weights_examples_and_uncarded(self):
        data = self.json_of("summary", "hooks", "lisbon")
        groups = data["sections"][0]["groups"]
        self.assertEqual([(g["value"], g["proposed"], g["weight"]) for g in groups],
                         [("visual_payoff", False, 5.0), ("steep_question", True, 3.0)])
        self.assertEqual(groups[0]["examples"][0]["spoken_hook"], "So this is Alfama")
        self.assertEqual([u["external_id"] for u in data["uncarded"]], ["uncardHit01"])
        self.assertEqual((data["days"], data["min_outlier"], data["format_id"]), (14, 2.0, "walk-reel"))

    def test_summary_flags_change_threshold_window_and_limit(self):
        data = self.json_of("summary", "hooks", "lisbon", "--min-outlier", "4.5", "--limit", "1")
        self.assertEqual(data["uncarded"], [])
        self.assertEqual(len(data["sections"][0]["groups"]), 1)
        formats = self.json_of("summary", "formats", "lisbon", "--days", "0.5")
        self.assertEqual([s["groups"] for s in formats["sections"]], [[], []])

    def test_summary_human_output_is_a_russian_table_with_examples_and_uncarded(self):
        code, out, _ = self.run_cli("summary", "topics", "lisbon")
        self.assertEqual(code, 0)
        self.assertIn("Сводка тем lisbon (Format walk-reel) за 14 дн.: 3 Reference, с карточкой 2.", out)
        self.assertIn("| # | Значение | Название | Карточек | Вес | Лучший outlier |", out)
        self.assertIn("«Alfama | at dawn»", out)
        self.assertIn("### Выбросы без карточки (outlier ≥ 2x)", out)
        self.assertIn("1. **4,0x**", out)

    def test_hooks_save_list_export_remove(self):
        saved = self.json_of("hooks", "save", "walk-reel", "https://www.youtube.com/watch?v=alfamaDawn1")
        self.assertEqual((saved["category"], saved["text"], saved["outlier"]),
                         ("visual_payoff", "So this is Alfama", 5.0))
        self.json_of("hooks", "save", "walk-reel", "steepLisbn3")
        listed = self.json_of("hooks", "list", "walk-reel")
        self.assertEqual([(h["source"], h["proposed"]) for h in listed],
                         [("steepLisbn3", True), ("alfamaDawn1", False)])
        path = Path(self.tmp.name) / "lib.md"
        exported = self.json_of("hooks", "export", "walk-reel", "--out", str(path))
        self.assertEqual((exported["path"], exported["hooks"]), (str(path), 2))
        self.assertIn("## visual_payoff: Visual payoff", path.read_text())
        self.json_of("hooks", "remove", "walk-reel", "steepLisbn3")
        self.assertEqual(len(self.json_of("hooks", "list", "walk-reel")), 1)

    def test_saving_an_uncarded_reference_is_one_error_line(self):
        code, out, err = self.run_cli("hooks", "save", "walk-reel", "uncardHit01")
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(err.count("\n"), 1)
        self.assertTrue(err.startswith("error: Reference uncardHit01 has no analysis yet"))
