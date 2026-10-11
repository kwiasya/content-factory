"""Brief from a shortlisted Idea: file content from the template, path rules, refusals. Temp footage root."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import brief, ideas
from cf.research import watchlist as wl
from test_research_card_analysis import analysis
from test_research_ideas import V1, V2, IdeasCase, add_card

SLUG = "lisbons-oldest-district-at-golden-hour-no-narration"


class BriefCase(IdeasCase):
    def setUp(self):
        super().setUp()
        self.root = Path(self.tmp.name) / "footage"
        add_card(self.store, V1, analysis())
        add_card(self.store, V2, analysis(hook__formula="Question + the answer on screen",
                                          hook__category="question",
                                          storytelling_format__description="Three stairways, worst to best"))
        self.idea = self.add(sources=(V1, V2))
        ideas.note(self.store, self.idea.id, "Shoot it in Tbilisi in November")
        ideas.shortlist(self.store, self.idea.id)

    def create(self, idea_id=None, **kw):
        return brief.create(self.store, idea_id or self.idea.id, root=self.root, **kw)


class PathTest(BriefCase):
    def test_default_channel_is_the_watchlists(self):
        path = self.create()
        self.assertEqual(path, self.root / "channels" / "travelwalks" / "briefs" / f"{self.idea.id}-{SLUG}.md")
        self.assertTrue(path.is_file())

    def test_channel_argument_wins(self):
        self.assertEqual(self.create(channel="@second").parent, self.root / "channels" / "@second" / "briefs")

    def test_watchlist_without_channel_goes_to_unassigned(self):
        i = self.add(sources=(V1,), wlname="other", title="Порто: лестницы!")
        ideas.shortlist(self.store, i.id)
        path = self.create(i.id)
        self.assertEqual(path, self.root / "channels" / "_unassigned" / "briefs" / f"{i.id}-порто-лестницы.md")

    def test_default_root_is_the_footage_root(self):
        with mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(self.root)}):
            path = brief.create(self.store, self.idea.id)
        self.assertTrue(str(path).startswith(str(self.root / "channels" / "travelwalks")))

    def test_channel_must_be_a_folder_name(self):
        for bad in ("a/b", "..", ".hidden", " "):
            with self.subTest(channel=bad), self.assertRaises(ideas.IdeaError):
                self.create(channel=bad)
        self.assertEqual(ideas.get(self.store, self.idea.id).status, "shortlisted")


class ContentTest(BriefCase):
    def setUp(self):
        super().setUp()
        self.path = self.create()
        self.text = self.path.read_text()

    def test_marks_the_idea(self):
        idea = ideas.get(self.store, self.idea.id)
        self.assertEqual((idea.status, idea.brief_path), ("brief", str(self.path)))

    def test_channel_format_and_title(self):
        self.assertIn("# Brief: Lisbon's oldest district at golden hour, no narration", self.text)
        self.assertIn("- Channel: travelwalks", self.text)
        self.assertIn("- Format: walk_reel", self.text)
        self.assertIn(f"- Idea: #{self.idea.id} (Watchlist lisbon)", self.text)

    def test_working_hook_from_alignment_and_source_formulas(self):
        hook = self.section("Рабочий хук")
        self.assertIn("Open on the best view and name the place; the stairs keep the promise", hook)
        self.assertIn("Place name + superlative, said over the best view", hook)
        self.assertIn("Question + the answer on screen", hook)
        self.assertIn(V2, hook)

    def test_structure_from_storytelling_format(self):
        s = self.section("Структура")
        self.assertIn("pov", s)
        self.assertIn("The descent is the arc; the river is the payoff", s)
        self.assertIn("Three stairways, worst to best", s)

    def test_empty_checklist_for_the_author(self):
        self.assertRegex(self.section("Что снять или записать"), r"^- \[ \]")

    def test_references_with_outlier_and_url(self):
        refs = self.section("Reference")
        self.assertIn(f"https://www.youtube.com/watch?v={V1}", refs)
        self.assertIn("9,0x", refs)
        self.assertIn("5,0x", refs)
        self.assertIn("Alfama at dusk", refs)

    def test_personalizations_contrast_and_notes(self):
        self.assertIn("Do it in Tbilisi's old town", self.text)
        self.assertIn("Alfama is a tourist trap", self.text)
        self.assertIn("Shoot it in Tbilisi in November", self.section("Заметки"))

    def test_no_placeholder_left(self):
        self.assertNotIn("$", self.text)

    def section(self, heading: str) -> str:
        after = self.text.split(f"\n## {heading}\n", 1)[1]
        return after.split("\n## ", 1)[0].strip()


class FormatTest(BriefCase):
    def test_format_argument_wins(self):
        self.assertIn("- Format: travel_long", self.create(format_id="travel_long").read_text())


class RefusalTest(BriefCase):
    def test_second_call_refuses_and_points_to_the_file(self):
        path = self.create()
        before = path.read_text()
        with self.assertRaises(ideas.IdeaError) as cm:
            self.create()
        self.assertIn(str(path), str(cm.exception))
        self.assertEqual(path.read_text(), before)
        self.assertEqual(len(list(path.parent.iterdir())), 1)

    def test_only_shortlisted_ideas(self):
        i = self.add(sources=(V1,))
        with self.assertRaises(ideas.IdeaError) as cm:
            self.create(i.id)
        self.assertIn("is inbox", str(cm.exception))
        self.assertFalse((self.root / "channels").exists())

    def test_existing_file_is_never_overwritten(self):
        target = self.root / "channels" / "travelwalks" / "briefs" / f"{self.idea.id}-{SLUG}.md"
        target.parent.mkdir(parents=True)
        target.write_text("mine")
        with self.assertRaises(ideas.IdeaError) as cm:
            self.create()
        self.assertIn(str(target), str(cm.exception))
        self.assertEqual(target.read_text(), "mine")
        self.assertEqual(ideas.get(self.store, self.idea.id).status, "shortlisted")


if __name__ == "__main__":
    unittest.main()
