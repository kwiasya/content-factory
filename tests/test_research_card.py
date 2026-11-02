"""Saving the measured part of a Reference card (cf-reference-card/1) on a temp store."""

import json
import tempfile
import unittest
from pathlib import Path

from cf.research import card
from cf.research import store as st


class CardSaveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = st.open_store(Path(self.tmp.name) / "f.db", seed=False, create=True)
        with self.store.transaction() as c:
            self.vid = c.execute("INSERT INTO video (external_id, title) VALUES ('dQw4w9WgXcQ', 't')").lastrowid

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_a_new_card_has_the_measured_section_and_an_empty_analysis_in_the_store_and_on_disk(self):
        path = Path(self.tmp.name) / "ref" / "card.json"
        saved = card.save(self.store, self.vid, {"cut_count": 4}, path=path)
        self.assertEqual(saved, {"schema": "cf-reference-card/1", "measured": {"cut_count": 4}, "analysis": None})
        self.assertEqual(card.load(self.store, self.vid), saved)
        self.assertEqual(json.loads(path.read_text()), saved)

    def test_measuring_again_keeps_the_analysis_the_editor_wrote(self):
        card.save(self.store, self.vid, {"cut_count": 4})
        with self.store.transaction() as c:
            c.execute("UPDATE card SET analysis = ? WHERE video_id = ?", ('{"summary": "x"}', self.vid))
        saved = card.save(self.store, self.vid, {"cut_count": 5})
        self.assertEqual(saved["measured"], {"cut_count": 5})
        self.assertEqual(saved["analysis"], {"summary": "x"})

    def test_a_video_without_a_card_loads_as_none(self):
        self.assertIsNone(card.load(self.store, self.vid))


if __name__ == "__main__":
    unittest.main()
