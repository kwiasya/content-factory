"""Desk opens factory.db without seeding, and reads never create or migrate it."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cf.desk.app import create_app
from cf.research import store as st


class StoreUseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        (base / "repo").mkdir()
        self.db = base / "footage" / "factory.db"
        self.client = TestClient(create_app(base / "repo", footage_root=base / "footage", db_path=self.db,
                                            web_dist=base / "dist"))

    def test_listing_notes_without_a_store_is_empty_and_creates_nothing(self):
        r = self.client.get("/api/notes")
        self.assertEqual((r.status_code, r.json()), (200, {"notes": []}))
        self.assertFalse(self.db.exists())

    def test_contour_reads_without_a_store_are_404_naming_the_store_and_create_nothing(self):
        for url in ("/api/contour/watchlists", "/api/contour/ideas", "/api/contour/taxonomy",
                    "/api/contour/quota"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 404, url)
            self.assertIn("factory.db", r.json()["detail"])
        self.assertFalse(self.db.exists())

    def test_a_read_does_not_seed_the_taxonomy(self):
        with st.open_store(self.db, seed=False):
            pass
        r = self.client.get("/api/contour/taxonomy")
        self.assertEqual((r.status_code, r.json()["values"]), (200, []))

    def test_a_read_does_not_migrate_an_older_store(self):
        self.db.parent.mkdir(parents=True)
        sqlite3.connect(self.db).close()
        r = self.client.get("/api/contour/watchlists")
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("schema version 0", r.json()["detail"])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)

    def test_a_note_written_without_a_store_creates_it_unseeded(self):
        r = self.client.post("/api/notes", json={"kind": "general", "key": "", "text": "x"})
        self.assertEqual(r.status_code, 201, r.text)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM taxonomy").fetchone()[0], 0)
