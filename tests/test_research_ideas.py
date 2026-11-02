"""Ideas: field validation, sources, the status machine, notes, candidates. Temp store, no network."""

import unittest

from cf.research import ideas
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import NOW, V1, V2, V3, IdeasCase, add_card, analysis, fields

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

    def test_a_source_that_is_neither_a_store_id_nor_a_youtube_ref_is_a_violation(self):
        for bad in (True, {"id": V1}, 1.5, None, [V1]):
            with self.subTest(bad=bad):
                problems = ideas.check(self.store, [bad], fields())
                self.assertEqual(len(problems), 1, problems)
                self.assertIn("store id, YouTube id or URL", problems[0])
                with self.assertRaises(ideas.IdeaError):
                    self.add(sources=(bad,))
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


class VideoLinkTest(IdeasCase):
    def test_link_video_is_idempotent_and_listed_on_the_idea(self):
        idea = self.add()
        self.assertEqual(idea.videos, [])
        ideas.link_video(self.store, idea.id, "boat-day")
        ideas.link_video(self.store, idea.id, "alfama")
        got = ideas.link_video(self.store, idea.id, "boat-day")
        me = st.person()
        want = [{"slug": "boat-day", "owner": me}, {"slug": "alfama", "owner": me}]
        self.assertEqual(got.videos, want)
        self.assertEqual(ideas.get(self.store, idea.id).to_dict()["videos"], want)
        got = ideas.link_video(self.store, idea.id, "boat-day", owner="someone-else")
        self.assertEqual(got.videos[-1], {"slug": "boat-day", "owner": "someone-else"})
        self.assertEqual(self.add(sources=(V2,)).videos, [])
        with self.assertRaises(ideas.IdeaError):
            ideas.link_video(self.store, 9999, "x")


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



class WatchlistRemoveTest(IdeasCase):
    def test_removing_a_watchlist_deletes_its_ideas(self):
        self.add()
        self.add(sources=(V3,), wlname="other")
        wl.remove(self.store, "lisbon")
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM idea")["n"], 1)

    def test_a_watchlist_with_a_briefed_idea_is_kept_unless_forced(self):
        i = self.add().id
        ideas.shortlist(self.store, i)
        ideas.mark_brief(self.store, i, "/footage/b.md")
        with self.assertRaises(wl.WatchlistError) as cm:
            wl.remove(self.store, "lisbon")
        self.assertIn("Brief", str(cm.exception))
        self.assertIn("force", str(cm.exception))
        self.assertEqual(ideas.get(self.store, i).status, "brief")
        wl.remove(self.store, "lisbon", force=True)
        self.assertEqual([w.name for w in wl.list_watchlists(self.store)], ["other"])

if __name__ == "__main__":
    unittest.main()
