"""The analysis section of a Reference card: validation against the taxonomy and the transcript,
saving, and the proposed → approved / rejected flow. Temp store, no network, no models."""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import card
from cf.research import store as st
from cf.research import taxonomy as tx

TRANSCRIPT = ("So this is Alfama, the oldest part of Lisbon. Watch the stairs. "
              "Okay, sunset time.")
MEASURED = {"duration_s": 95.0, "spoken_hook": "So this is Alfama, the oldest part of Lisbon."}


def analysis(**over) -> dict:
    a = {
        "summary": "A slow evening walk through Alfama that ends on the river at sunset.",
        "idea_analysis": {
            "topic": "Walking Lisbon's oldest district",
            "idea_seed": "The old town is best seen on foot at golden hour",
            "unique_angle": "No narration after the first line; the stairs carry the story",
            "common_belief": "Alfama is a tourist trap",
            "contrarian_reality": "Ten minutes off the tram line it is empty",
            "supporting_evidence": "Empty alleys from 0:40 on; the sunset viewpoint at 1:30",
        },
        "hook": {
            "category": "visual_payoff",
            "formula": "Place name + superlative, said over the best view",
            "spoken_hook": "So this is Alfama, the oldest part of Lisbon",
            "alignment": "The promise of the oldest part pays off in the stairs and alleys",
        },
        "storytelling_format": {
            "category": "pov",
            "description": "First-person walk from the top of the hill to the river",
            "analysis": "The descent gives a natural arc that ends at the payoff",
        },
        "visual_layout": {"category": "pov_walk", "sub_category": "vlog_pov"},
    }
    for path, value in over.items():
        node = a
        *head, last = path.split("__")
        for k in head:
            node = node[k]
        node[last] = value
    return a


def full_card(a: dict | None = None) -> dict:
    return {"schema": card.SCHEMA, "measured": copy.deepcopy(MEASURED), "analysis": a or analysis()}


class AnalysisCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = st.open_store(Path(self.tmp.name) / "f.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def problems(self, c: dict, transcript=TRANSCRIPT) -> list[str]:
        return card.validate(c, self.store, transcript=transcript)

    def assertViolation(self, c: dict, needle: str, transcript=TRANSCRIPT):
        found = self.problems(c, transcript)
        self.assertTrue(any(needle in p for p in found), f"{needle!r} not in {found}")


class ValidateTest(AnalysisCase):
    def test_a_complete_card_with_approved_categories_and_a_quoted_hook_is_valid(self):
        self.assertEqual(self.problems(full_card()), [])

    def test_a_missing_or_empty_required_field_is_a_violation(self):
        a = analysis()
        del a["idea_analysis"]["topic"]
        self.assertViolation(full_card(a), "idea_analysis.topic: missing")
        self.assertViolation(full_card(analysis(summary="  ")), "summary: empty")
        self.assertViolation(full_card(analysis(hook__formula=7)), "hook.formula: must be a string")
        a = analysis()
        del a["visual_layout"]
        self.assertViolation(full_card(a), "visual_layout: missing")

    def test_a_card_without_analysis_or_with_another_schema_is_a_violation(self):
        c = full_card()
        c["analysis"] = None
        self.assertViolation(c, "analysis: missing")
        c = full_card()
        c["schema"] = "cf-reference-card/0"
        self.assertViolation(c, "schema: 'cf-reference-card/0', expected 'cf-reference-card/1'")

    def test_an_unknown_field_is_a_violation(self):
        self.assertViolation(full_card(analysis(hook__formla="x")), "hook.formla: unknown field")

    def test_belief_and_reality_may_both_be_null_but_not_one_alone(self):
        both = analysis(idea_analysis__common_belief=None, idea_analysis__contrarian_reality=None)
        self.assertEqual(self.problems(full_card(both)), [])
        self.assertViolation(full_card(analysis(idea_analysis__contrarian_reality=None)),
                             "idea_analysis.contrarian_reality: null while common_belief is set")

    def test_a_category_outside_the_approved_taxonomy_is_a_violation(self):
        self.assertViolation(full_card(analysis(hook__category="shock_value")),
                             "hook.category: 'shock_value' is not an approved hook_category")
        self.assertViolation(full_card(analysis(storytelling_format__category="vlog_pov")),
                             "storytelling_format.category: 'vlog_pov' is not an approved storytelling_format")
        self.assertViolation(full_card(analysis(visual_layout__category="tutorial")),
                             "visual_layout.category: 'tutorial' is not an approved visual_layout")
        self.assertViolation(full_card(analysis(visual_layout__sub_category="pov_walk")),
                             "visual_layout.sub_category: 'pov_walk' is not an approved editing_style")

    def test_a_proposed_category_is_accepted(self):
        c = full_card(analysis(hook__category="proposed:shock_value",
                               visual_layout__sub_category="proposed:drone_flyover"))
        self.assertEqual(self.problems(c), [])

    def test_a_proposed_value_must_be_snake_case(self):
        self.assertViolation(full_card(analysis(hook__category="proposed:Shock Value")),
                             "hook.category: proposed value 'Shock Value' must be snake_case")
        self.assertViolation(full_card(analysis(hook__category="proposed:")),
                             "hook.category: proposed value '' must be snake_case")


class SpokenHookTest(AnalysisCase):
    def test_a_spoken_hook_not_in_the_transcript_is_a_violation(self):
        self.assertViolation(full_card(analysis(hook__spoken_hook="This is the oldest street in Europe")),
                             "hook.spoken_hook: not found in the transcript")

    def test_case_punctuation_and_whitespace_do_not_matter(self):
        c = full_card(analysis(hook__spoken_hook="so  this is ALFAMA -- the oldest part of lisbon!"))
        self.assertEqual(self.problems(c), [])

    def test_the_hook_may_run_past_the_first_three_seconds(self):
        c = full_card(analysis(hook__spoken_hook="the oldest part of Lisbon. Watch the stairs"))
        self.assertEqual(self.problems(c), [])

    def test_words_must_match_whole_not_as_fragments(self):
        self.assertViolation(full_card(analysis(hook__spoken_hook="his is Alfama")),
                             "hook.spoken_hook: not found in the transcript")

    def test_a_stable_ts_result_works_as_the_transcript(self):
        tr = {"segments": [{"words": [{"word": " So", "start": 0.6}, {"word": " this", "start": 0.8},
                                      {"word": " is", "start": 1.0}, {"word": " Alfama,", "start": 1.1},
                                      {"word": " the", "start": 1.9}, {"word": " oldest", "start": 2.0},
                                      {"word": " part", "start": 2.4}, {"word": " of", "start": 2.7},
                                      {"word": " Lisbon.", "start": 2.8}]}]}
        self.assertEqual(self.problems(full_card(), transcript=tr), [])

    def test_without_a_transcript_the_measured_spoken_hook_is_the_reference(self):
        self.assertEqual(self.problems(full_card(), transcript=None), [])
        self.assertViolation(full_card(analysis(hook__spoken_hook="Watch the stairs")),
                             "hook.spoken_hook: not found in the transcript", transcript=None)

    def test_with_nothing_to_quote_from_a_spoken_hook_cannot_be_checked(self):
        c = full_card()
        c["measured"]["spoken_hook"] = None
        self.assertViolation(c, "hook.spoken_hook: no transcript to check against", transcript=None)

    def test_a_null_spoken_hook_is_fine_only_for_a_reference_without_speech(self):
        c = full_card(analysis(hook__spoken_hook=None))
        self.assertViolation(c, "hook.spoken_hook: null, but the Reference has speech")
        c["measured"]["spoken_hook"] = None
        self.assertEqual(self.problems(c, transcript=""), [])


class StoredCardCase(AnalysisCase):
    """A measured card in the store and its Reference folder with transcript.json and card.json."""

    def setUp(self):
        super().setUp()
        self.root = Path(self.tmp.name) / "footage"
        env = mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.dir = self.root / "references" / "lisbon" / "dQw4w9WgXcQ"
        self.dir.mkdir(parents=True)
        (self.dir / "transcript.json").write_text(json.dumps({"segments": [{"words": [
            {"word": f" {w}", "start": float(i)} for i, w in enumerate(TRANSCRIPT.split())]}]}))
        with self.store.transaction() as c:
            self.vid = c.execute("INSERT INTO video (external_id, title) VALUES ('dQw4w9WgXcQ', 't')").lastrowid
        card.save(self.store, self.vid, MEASURED, path=self.dir / "card.json")

    def save(self, a: dict) -> dict:
        return card.save_analysis(self.store, self.vid, a)


class SaveTest(StoredCardCase):
    def test_a_valid_analysis_lands_in_the_store_and_in_card_json_next_to_measured(self):
        saved = self.save(analysis())
        self.assertEqual(saved, {"schema": card.SCHEMA, "measured": MEASURED, "analysis": analysis()})
        self.assertEqual(card.load(self.store, self.vid), saved)
        self.assertEqual(json.loads((self.dir / "card.json").read_text()), saved)

    def test_the_transcript_is_read_from_the_reference_folder(self):
        with self.assertRaises(card.CardError) as cm:
            self.save(analysis(hook__spoken_hook="Okay, sunset time and more"))
        self.assertEqual(cm.exception.violations,
                         ["hook.spoken_hook: not found in the transcript: 'Okay, sunset time and more'"])
        self.save(analysis(hook__spoken_hook="Okay, sunset time"))  # past measured.spoken_hook

    def test_an_invalid_analysis_is_refused_and_nothing_is_written(self):
        with self.assertRaises(card.CardError):
            self.save(analysis(hook__category="shock_value", visual_layout__category="proposed:drone"))
        self.assertIsNone(card.load(self.store, self.vid)["analysis"])
        self.assertNotIn("drone", {v.value for v in tx.values(self.store, status="proposed")})

    def test_a_video_without_a_measured_card_is_refused(self):
        with self.store.transaction() as c:
            other = c.execute("INSERT INTO video (external_id) VALUES ('aaaaaaaaaaa')").lastrowid
        with self.assertRaises(card.CardError) as cm:
            card.save_analysis(self.store, other, analysis(), transcript=TRANSCRIPT, root=self.root)
        self.assertIn("fetch", str(cm.exception))

    def test_the_youtube_id_works_as_the_video(self):
        card.save_analysis(self.store, "dQw4w9WgXcQ", analysis())
        self.assertEqual(card.load(self.store, self.vid)["analysis"], analysis())


class ProposedFlowTest(StoredCardCase):
    def stored_category(self) -> str:
        return card.load(self.store, self.vid)["analysis"]["hook"]["category"]

    def test_save_proposes_approve_admits_reject_takes_back(self):
        self.save(analysis(hook__category="proposed:shock_value"))
        [row] = [v for v in tx.values(self.store, status="proposed")]
        self.assertEqual((row.kind, row.value, row.source), ("hook_category", "shock_value", "card:dQw4w9WgXcQ"))
        self.assertEqual(self.stored_category(), "proposed:shock_value")
        plain = full_card(analysis(hook__category="shock_value"))
        self.assertViolation(plain, "'shock_value' is a proposed hook_category awaiting approval")

        change = tx.approve(self.store, "hook_category", "shock_value")
        self.assertEqual((change.value.status, change.cards), ("approved", ["dQw4w9WgXcQ"]))
        self.assertEqual(self.problems(plain), [])
        self.assertEqual(self.stored_category(), "shock_value")  # the card no longer carries the prefix
        self.assertEqual(json.loads((self.dir / "card.json").read_text())["analysis"]["hook"]["category"],
                         "shock_value")

        change = tx.reject(self.store, "hook_category", "shock_value")
        self.assertEqual((change.value.status, change.cards), ("rejected", ["dQw4w9WgXcQ"]))
        self.assertViolation(plain, "'shock_value' was rejected as hook_category")
        self.assertViolation(full_card(analysis(hook__category="proposed:shock_value")),
                             "'shock_value' was rejected as hook_category")

    def test_a_rejected_seed_value_stays_rejected_when_the_seed_loads_again(self):
        tx.reject(self.store, "visual_layout", "split")
        tx.load_seed(self.store)
        self.assertEqual([v.status for v in tx.values(self.store, kind="visual_layout") if v.value == "split"],
                         ["rejected"])
        self.assertViolation(full_card(analysis(visual_layout__category="split")), "was rejected")

    def test_proposals_list_what_awaits_the_author(self):
        self.save(analysis(hook__category="proposed:shock_value", visual_layout__sub_category="proposed:drone"))
        self.assertEqual([(v.kind, v.value) for v in tx.proposals(self.store)],
                         [("editing_style", "drone"), ("hook_category", "shock_value")])

    def test_proposing_an_approved_value_saves_it_plain(self):
        self.save(analysis(hook__category="proposed:pov"))
        self.assertEqual(self.stored_category(), "pov")
        self.assertEqual(tx.proposals(self.store), [])

    def test_approving_or_rejecting_an_unknown_value_adds_it_with_the_author_as_source(self):
        change = tx.approve(self.store, "hook_category", "cold_open")
        self.assertEqual((change.value.status, change.value.source, change.cards), ("approved", "author", []))
        with self.assertRaises(tx.TaxonomyError):
            tx.approve(self.store, "colour", "red")
        with self.assertRaises(tx.TaxonomyError):
            tx.reject(self.store, "hook_category", "Cold Open")


if __name__ == "__main__":
    unittest.main()
