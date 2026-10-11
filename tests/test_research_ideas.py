"""Ideas: field validation, sources, the status machine, notes, candidates. Temp store, no network."""

import json
import tempfile
import unittest
from pathlib import Path

from cf.research import ideas
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import NOW, add_member, add_videos, ago, video_item

from test_research_card_analysis import analysis

A = "UCaaaaaaaaaaaaaaaaaaaaaa"
V1, V2, V3 = "alfamaDusk1", "portoStair2", "sintraFog03"


def fields(**over) -> dict:
    f = {
        "title": "Lisbon's oldest district at golden hour, no narration",
        "summary": "A silent descent through Alfama that ends on the river at sunset.",
        "content_positioning": "The empty side of a district everyone calls a tourist trap",
        "storytelling_format": {"category": "pov", "why": "The descent is the arc; the river is the payoff"},
        "contrast_mechanism": {"common_belief": "Alfama is a tourist trap",
                               "contrarian_reality": "Ten minutes off the tram line it is empty"},
        "hook_alignment": "Open on the best view and name the place; the stairs keep the promise",
        "personalizations": ["Do it in Tbilisi's old town", "Shoot at dawn instead of dusk",
                             "Say the hook in Russian over the first view"],
    }
    f.update(over)
    return f


def add_card(store, external_id: str, a: dict | None = None) -> None:
    vid = store.one("SELECT id FROM video WHERE external_id = ?", (external_id,))["id"]
    with store.transaction() as c:
        c.execute("INSERT INTO card (video_id, schema, measured, analysis, written_at) "
                  "VALUES (?, 'cf-reference-card/1', '{}', ?, ?)",
                  (vid, None if a is None else json.dumps(a), ago(hours=1)))


class IdeasCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        s = self.store = st.open_store(Path(self.tmp.name) / "f.db")
        self.addCleanup(s.close)
        wl.create(s, "lisbon", format_id="walk_reel", author_channel="travelwalks")
        wl.create(s, "other", format_id="travel_long")
        add_member(s, "lisbon", A, "@alpha")
        add_videos(s, [video_item(f"base{i:07d}", A, ago(days=10 + i), 40, 1000) for i in range(5)]
                   + [video_item(V1, A, ago(days=2), 40, 9000, title="Alfama at dusk"),
                      video_item(V2, A, ago(days=3), 40, 5000, title="Porto stairs"),
                      video_item(V3, A, ago(days=4), 40, 3000, title="Sintra fog")])

    def add(self, sources=(V1,), wlname="lisbon", **over):
        return ideas.add(self.store, wlname, list(sources), fields(**over))


class ValidationTest(IdeasCase):
    def problems(self, f: dict) -> list[str]:
        return ideas.validate(f, self.store)

    def test_valid_fields(self):
        self.assertEqual(self.problems(fields()), [])

    def test_contrast_mechanism_may_be_null(self):
        self.assertEqual(self.problems(fields(contrast_mechanism=None)), [])

    def test_missing_empty_and_unknown_fields(self):
        f = fields(summary="  ", extra="x")
        del f["hook_alignment"]
        got = self.problems(f)
        self.assertIn("summary: must be a non-empty string", got)
        self.assertIn("hook_alignment: missing", got)
        self.assertIn("extra: unknown field", got)

    def test_personalizations_are_exactly_three_strings(self):
        self.assertIn("personalizations: must be a list of exactly 3 non-empty strings",
                      self.problems(fields(personalizations=["a", "b"])))
        self.assertIn("personalizations: must be a list of exactly 3 non-empty strings",
                      self.problems(fields(personalizations=["a", "b", ""])))
        self.assertIn("personalizations: must be a list of exactly 3 non-empty strings",
                      self.problems(fields(personalizations="a, b, c")))

    def test_storytelling_format_needs_a_taxonomy_category_and_why(self):
        self.assertIn("storytelling_format.why: missing",
                      self.problems(fields(storytelling_format={"category": "pov"})))
        got = self.problems(fields(storytelling_format={"category": "nonsense", "why": "x"}))
        self.assertTrue(any(p.startswith("storytelling_format.category: 'nonsense' is not an approved")
                            for p in got), got)
        self.assertEqual(self.problems(fields(storytelling_format={"category": "proposed:slow_reveal",
                                                                   "why": "x"})), [])

    def test_contrast_mechanism_needs_both_sides(self):
        got = self.problems(fields(contrast_mechanism={"common_belief": "x"}))
        self.assertIn("contrast_mechanism.contrarian_reality: missing", got)
        self.assertIn("contrast_mechanism: must be an object {common_belief, contrarian_reality} or null",
                      self.problems(fields(contrast_mechanism="x")))


class AddTest(IdeasCase):
    def test_add_stores_an_inbox_idea_with_its_sources(self):
        idea = self.add(sources=(V1, f"https://www.youtube.com/shorts/{V2}"))
        self.assertEqual(idea.status, "inbox")
        self.assertEqual(idea.watchlist, "lisbon")
        self.assertEqual(idea.title, fields()["title"])
        self.assertEqual([s["external_id"] for s in idea.sources], [V1, V2])
        self.assertEqual(idea.fields["personalizations"], fields()["personalizations"])
        self.assertNotIn("title", idea.fields)
        self.assertEqual(idea.notes, [])
        self.assertIsNone(idea.brief_path)
        self.assertEqual(ideas.get(self.store, idea.id), idea)

    def test_sources_by_store_id(self):
        sid = self.store.one("SELECT id FROM video WHERE external_id = ?", (V3,))["id"]
        self.assertEqual([s["external_id"] for s in self.add(sources=(sid,)).sources], [V3])

    def test_unknown_source_refuses_and_writes_nothing(self):
        with self.assertRaises(ideas.IdeaError) as cm:
            self.add(sources=(V1, "zzzzzzzzzzz"))
        self.assertIn("zzzzzzzzzzz", str(cm.exception))
        self.assertEqual(ideas.list(self.store, "lisbon"), [])

    def test_needs_at_least_one_source(self):
        with self.assertRaises(ideas.IdeaError):
            self.add(sources=())

    def test_invalid_fields_refuse_with_violations(self):
        with self.assertRaises(ideas.IdeaError) as cm:
            self.add(personalizations=["one"])
        self.assertIn("personalizations: must be a list of exactly 3 non-empty strings", cm.exception.violations)
        self.assertEqual(ideas.list(self.store, "lisbon"), [])

    def test_unknown_watchlist(self):
        with self.assertRaises(Exception) as cm:
            self.add(wlname="nowhere")
        self.assertIn("nowhere", str(cm.exception))

    def test_list_by_watchlist_and_status(self):
        a = self.add()
        b = self.add(sources=(V2,))
        self.add(sources=(V3,), wlname="other")
        self.assertEqual([i.id for i in ideas.list(self.store, "lisbon")], [a.id, b.id])
        ideas.shortlist(self.store, b.id)
        self.assertEqual([i.id for i in ideas.list(self.store, "lisbon", status="shortlisted")], [b.id])
        self.assertEqual([i.id for i in ideas.list(self.store, "lisbon", status="inbox")], [a.id])
        with self.assertRaises(ideas.IdeaError):
            ideas.list(self.store, "lisbon", status="maybe")

    def test_get_unknown_id(self):
        with self.assertRaises(ideas.IdeaError) as cm:
            ideas.get(self.store, 999)
        self.assertIn("999", str(cm.exception))


class TransitionTest(IdeasCase):
    MOVES = {"shortlist": ideas.shortlist, "discard": ideas.discard, "restore": ideas.restore}

    def at(self, status: str) -> int:
        """An Idea brought to ``status`` through the public moves (``brief`` by marking it)."""
        i = self.add().id
        if status in ("shortlisted", "brief"):
            ideas.shortlist(self.store, i)
        if status == "discarded":
            ideas.discard(self.store, i)
        if status == "brief":
            ideas.mark_brief(self.store, i, "/tmp/x.md")
        return i

    def test_allowed_moves(self):
        for start, move, end in [("inbox", "shortlist", "shortlisted"), ("inbox", "discard", "discarded"),
                                 ("discarded", "restore", "inbox")]:
            with self.subTest(start=start, move=move):
                i = self.at(start)
                self.assertEqual(self.MOVES[move](self.store, i).status, end)
                self.assertEqual(ideas.get(self.store, i).status, end)

    def test_shortlisted_to_brief_by_marking(self):
        i = self.at("shortlisted")
        idea = ideas.mark_brief(self.store, i, "/footage/b.md")
        self.assertEqual((idea.status, idea.brief_path), ("brief", "/footage/b.md"))

    def test_forbidden_moves_name_the_current_status(self):
        forbidden = [("shortlisted", "shortlist"), ("shortlisted", "discard"), ("shortlisted", "restore"),
                     ("discarded", "shortlist"), ("discarded", "discard"),
                     ("inbox", "restore"),
                     ("brief", "shortlist"), ("brief", "discard"), ("brief", "restore")]
        for start, move in forbidden:
            with self.subTest(start=start, move=move):
                i = self.at(start)
                with self.assertRaises(ideas.IdeaError) as cm:
                    self.MOVES[move](self.store, i)
                self.assertIn(f"is {start}", str(cm.exception))
                self.assertEqual(ideas.get(self.store, i).status, start)

    def test_only_shortlisted_can_be_marked_brief(self):
        for start in ("inbox", "discarded", "brief"):
            with self.subTest(start=start):
                i = self.at(start)
                with self.assertRaises(ideas.IdeaError) as cm:
                    ideas.mark_brief(self.store, i, "/tmp/y.md")
                self.assertIn(f"is {start}", str(cm.exception))

    def test_unknown_idea(self):
        with self.assertRaises(ideas.IdeaError):
            ideas.shortlist(self.store, 4242)


class NoteTest(IdeasCase):
    def test_notes_append_with_timestamps_in_order(self):
        i = self.add().id
        ideas.note(self.store, i, "Try it in Tbilisi")
        ideas.discard(self.store, i)
        idea = ideas.note(self.store, i, "  Not this month  ")
        self.assertEqual([n["text"] for n in idea.notes], ["Try it in Tbilisi", "Not this month"])
        for n in idea.notes:
            self.assertRegex(n["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(ideas.get(self.store, i).notes, idea.notes)

    def test_empty_note_refused(self):
        with self.assertRaises(ideas.IdeaError):
            ideas.note(self.store, self.add().id, "   ")


class CandidatesTest(IdeasCase):
    """V1 (outlier 9), V2 (5), V3 (3) are analyzed; V2 is a source already; the baseline is uncarded."""

    def setUp(self):
        super().setUp()
        for v in (V1, V2, V3):
            add_card(self.store, v, analysis())
        add_card(self.store, "base0000000")  # measured only: no analysis
        self.add(sources=(V2,), wlname="other")

    def ids(self, **kw):
        return [r.external_id for r in ideas.candidates(self.store, "lisbon", now=NOW, **kw)]

    def test_analyzed_top_outliers_not_yet_a_source(self):
        self.assertEqual(self.ids(days=30), [V1, V3])

    def test_a_discarded_idea_still_uses_its_source(self):
        ideas.discard(self.store, self.add(sources=(V1,)).id)
        self.assertEqual(self.ids(days=30), [V3])

    def test_window_min_outlier_and_limit(self):
        self.assertEqual(self.ids(days=3.5), [V1])
        self.assertEqual(self.ids(days=30, min_outlier=5), [V1])
        self.assertEqual(self.ids(days=30, limit=1), [V1])

    def test_rows_carry_outlier_and_url(self):
        row = ideas.candidates(self.store, "lisbon", days=30, now=NOW)[0]
        self.assertAlmostEqual(row.outlier, 9.0)
        self.assertEqual(row.url, f"https://www.youtube.com/watch?v={V1}")


if __name__ == "__main__":
    unittest.main()
