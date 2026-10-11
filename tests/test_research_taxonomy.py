"""Taxonomy seed: the repo's vocabulary lands in the store as approved, once."""

import json
import tempfile
import unittest
from pathlib import Path

from cf import script_schema
from cf.research import store as st
from cf.research import taxonomy as tx


class TaxonomySeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "f.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_store_has_the_seed_as_approved(self):
        with st.open_store(self.db) as s:
            vals = tx.values(s)
        self.assertTrue(vals)
        self.assertEqual({v.status for v in vals}, {"approved"})
        self.assertEqual({v.kind for v in vals}, set(tx.KINDS))

    def test_seed_holds_the_script_schema_vocabulary(self):
        with st.open_store(self.db) as s:
            hooks = {v.value for v in tx.values(s, kind="hook_category")}
            formats = {v.value for v in tx.values(s, kind="storytelling_format")}
        self.assertLessEqual(set(script_schema.HOOK_TYPES), hooks)
        self.assertLessEqual(set(script_schema.FORMATS), formats)
        self.assertIn("diagnosis", hooks)          # hook-playbook
        self.assertIn("tutorial", formats)         # format-finder

    def test_layouts_and_editing_styles(self):
        with st.open_store(self.db) as s:
            layouts = {v.value for v in tx.values(s, kind="visual_layout")}
            styles = {v.value for v in tx.values(s, kind="editing_style")}
        self.assertEqual(layouts, {"talking_head", "screencast", "broll_voiceover", "pov_walk",
                                   "text_on_footage", "split"})
        self.assertLessEqual({"vlog_pov", "vlog_music", "vlog_timelapse", "faceless"}, styles)
        self.assertLessEqual({"office_room_yap", "full_screen_hybrid", "faceless_visual_explainer",
                              "skit_solo", "stop_motion"}, styles)  # format-finder editing styles
        self.assertEqual(len(styles), 4 + 30 - 3)  # vlog_pov, vlog_music, vlog_timelapse in both

    def test_reopening_does_not_duplicate(self):
        with st.open_store(self.db) as s:
            first = len(tx.values(s))
        with st.open_store(self.db) as s:
            self.assertEqual(tx.load_seed(s), 0)
            self.assertEqual(len(tx.values(s)), first)

    def test_new_seed_values_are_added_on_the_next_load(self):
        seed = Path(self.tmp.name) / "seed.json"
        seed.write_text(json.dumps({"schema": tx.SEED_SCHEMA, "kinds": {
            "visual_layout": [{"source": "test", "values": [
                {"value": "talking_head"}, {"value": "puppet_show", "note": "new"}]}]}}))
        with st.open_store(self.db) as s:
            self.assertEqual(tx.load_seed(s, seed), 1)
            self.assertIn("puppet_show", {v.value for v in tx.values(s, kind="visual_layout")})

    def test_a_bad_seed_file_is_refused(self):
        seed = Path(self.tmp.name) / "seed.json"
        seed.write_text(json.dumps({"schema": tx.SEED_SCHEMA, "kinds": {"colour": []}}))
        with st.open_store(self.db) as s, self.assertRaises(tx.TaxonomyError) as cm:
            tx.load_seed(s, seed)
        self.assertIn("colour", str(cm.exception))


class TaxonomyValueTest(unittest.TestCase):
    def test_a_value_with_a_trailing_newline_is_not_snake_case(self):
        with tempfile.TemporaryDirectory() as tmp, st.open_store(Path(tmp) / "f.db") as s:
            with self.assertRaises(tx.TaxonomyError):
                tx.propose(s, "hook_category", "shock_value\n", source="test")
            self.assertIsNone(tx.get(s, "hook_category", "shock_value\n"))

if __name__ == "__main__":
    unittest.main()
