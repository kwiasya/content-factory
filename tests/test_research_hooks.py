"""The Hook library: hooks saved from cards per Format, listed and exported to Markdown."""

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from cf.research import card
from cf.research import hooks
from cf.research import watchlist as wl
from research_synth import NOW, add_member, add_videos, ago, video_item
from test_research_summary import SummaryCase, hook, put_card

LIBRARY = """\
# Hook library: walk-reel

Сгенерировано командой `python -m cf.research hooks export walk-reel` из базы исследования. Не правьте руками: следующий экспорт перезапишет файл. Сохранить хук из карточки: `python -m cf.research hooks save walk-reel <video_id>`.

Хуков: 3, категорий: 2. Внутри категории сначала больший Outlier score (на момент экспорта).

## question: Question

- **«Why is Lisbon so steep»**
  - Формула: Why is <place> <adjective>?
  - Источник: «Why is Lisbon so steep?» · 9,0x · https://www.youtube.com/watch?v=steepLisbn3
  - Сохранён: 2026-10-11

## visual_payoff: Visual payoff

- **«So this is Alfama»**
  - Формула: Place name + superlative
  - Источник: «Alfama at dawn» · 5,0x · https://www.youtube.com/watch?v=alfamaDawn1
  - Сохранён: 2026-10-10
- **«Two hundred steps»**
  - Формула: Stairs + count
  - Источник: «Graça stairs» · 3,0x · https://www.youtube.com/watch?v=gracaStair2
  - Сохранён: 2026-10-11
"""


class HookLibraryTest(SummaryCase):
    def setUp(self):
        super().setUp()
        wl.create(self.store, "porto", format_id="walk-reel")
        self.out = Path(self.tmp.name) / "formats" / "walk-reel" / "hook-library.md"

    def test_save_takes_category_formula_and_spoken_hook_from_the_card(self):
        h = hooks.save(self.store, "walk-reel", "alfamaDawn1", now=NOW)
        self.assertEqual((h.format_id, h.category, h.formula, h.text, h.source, h.source_title, h.proposed),
                         ("walk-reel", "visual_payoff", "Place name + superlative", "So this is Alfama", "alfamaDawn1",
                          "Alfama at dawn", False))
        self.assertEqual(h.saved_at[:10], "2026-10-11")

    def test_a_proposed_category_is_saved_bare_and_flagged(self):
        h = hooks.save(self.store, "walk-reel", "sunsetSoon4", now=NOW)
        self.assertEqual((h.category, h.proposed), ("sunset_tease", True))

    def test_a_card_without_a_spoken_hook_saves_the_measured_opening(self):
        self.assertEqual(hooks.save(self.store, "walk-reel", "waitForSun5", now=NOW).text, "measured words")

    def test_hooks_belong_to_the_format_not_the_watchlist(self):
        hooks.save(self.store, "walk-reel", "alfamaDawn1", now=NOW)
        hooks.save(self.store, "tech-explainer", "steepLisbn3", now=NOW)
        self.assertEqual([h.source for h in hooks.list_hooks(self.store, "walk-reel", now=NOW)], ["alfamaDawn1"])
        self.assertEqual([h.source for h in hooks.list_hooks(self.store, "tech-explainer", now=NOW)], ["steepLisbn3"])
        # porto shares lisbon's Format, so it reads the same library
        fmt = wl.get(self.store, "porto").format_id
        self.assertEqual([h.source for h in hooks.list_hooks(self.store, fmt, now=NOW)], ["alfamaDawn1"])

    def test_saving_the_same_reference_again_updates_its_entry(self):
        hooks.save(self.store, "walk-reel", "alfamaDawn1", now=NOW - timedelta(days=1))
        put_card(self.store, "alfamaDawn1", hook("question", "New formula", "So this is Alfama"))
        h = hooks.save(self.store, "walk-reel", "alfamaDawn1", now=NOW)
        listed = hooks.list_hooks(self.store, "walk-reel", now=NOW)
        self.assertEqual([(x.source, x.category, x.formula) for x in listed], [("alfamaDawn1", "question", "New formula")])
        self.assertEqual(h.saved_at[:10], "2026-10-10")  # first saved

    def test_a_reference_without_an_analysis_cannot_be_saved(self):
        with self.assertRaises(hooks.HookError):
            hooks.save(self.store, "walk-reel", "measuredOn3", now=NOW)
        with self.assertRaises(card.CardError):
            hooks.save(self.store, "walk-reel", "zzzzzzzzzzz", now=NOW)

    def test_a_format_id_must_be_folder_safe(self):
        with self.assertRaises(hooks.HookError):
            hooks.save(self.store, "../walk", "alfamaDawn1", now=NOW)

    def test_remove_takes_a_reference_out_of_the_library(self):
        hooks.save(self.store, "walk-reel", "alfamaDawn1", now=NOW)
        hooks.save(self.store, "walk-reel", "gracaStair2", now=NOW)
        hooks.remove(self.store, "walk-reel", "alfamaDawn1")
        self.assertEqual([h.source for h in hooks.list_hooks(self.store, "walk-reel", now=NOW)], ["gracaStair2"])
        with self.assertRaises(hooks.HookError):
            hooks.remove(self.store, "walk-reel", "alfamaDawn1")

    def save_three(self):
        hooks.save(self.store, "walk-reel", "gracaStair2", now=NOW)
        hooks.save(self.store, "walk-reel", "alfamaDawn1", now=NOW - timedelta(days=1))
        hooks.save(self.store, "walk-reel", "steepLisbn3", now=NOW)

    def test_export_groups_by_category_with_formula_source_outlier_link_and_date(self):
        self.save_three()
        path = hooks.export(self.store, "walk-reel", self.out, now=NOW)
        self.assertEqual(path, self.out)
        self.assertEqual(self.out.read_text(), LIBRARY)

    def test_export_is_deterministic_and_overwrites_the_file(self):
        self.out.parent.mkdir(parents=True)
        self.out.write_text("hand edits\n")
        self.save_three()
        hooks.export(self.store, "walk-reel", self.out, now=NOW)
        first = self.out.read_bytes()
        hooks.export(self.store, "walk-reel", self.out, now=NOW)
        self.assertEqual(self.out.read_bytes(), first)
        self.assertNotIn(b"hand edits", first)

    def test_export_marks_proposed_categories_and_a_missing_source(self):
        hooks.save(self.store, "walk-reel", "sunsetSoon4", now=NOW)
        self.store.conn.execute("DELETE FROM video WHERE external_id = 'sunsetSoon4'")
        self.store.conn.commit()
        text = hooks.export(self.store, "walk-reel", self.out, now=NOW).read_text()
        self.assertIn("## sunset_tease (предложено)\n", text)
        self.assertIn("  - Источник: удалён из базы\n", text)

    def test_an_empty_library_exports_a_header_only(self):
        text = hooks.export(self.store, "walk-reel", self.out, now=NOW).read_text()
        self.assertTrue(text.startswith("# Hook library: walk-reel\n"))
        self.assertTrue(text.endswith("Хуков пока нет.\n"))

    def test_the_default_path_is_the_formats_folder_of_the_repo(self):
        self.assertEqual(hooks.library_path("walk-reel"),
                         hooks.REPO_ROOT / "formats" / "walk-reel" / "hook-library.md")
