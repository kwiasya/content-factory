"""Desk opens factory.db without seeding and never creates nor migrates it; a held lock is 503 db_busy."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        self.db.parent.mkdir()
        self.client = TestClient(create_app(base / "repo", local_root=base / "footage", db_path=self.db,
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
            self.assertEqual(r.json()["code"], "db_missing", url)
            self.assertEqual(r.json()["params"],
                             {"path": str(self.db), "command": "python -m cf.research db init"})
        self.assertFalse(self.db.exists())

    def test_a_read_does_not_seed_the_taxonomy(self):
        with st.open_store(self.db, seed=False):
            pass
        r = self.client.get("/api/contour/taxonomy")
        self.assertEqual((r.status_code, r.json()["values"]), (200, []))

    def test_a_read_does_not_migrate_an_older_store(self):
        sqlite3.connect(self.db).close()
        r = self.client.get("/api/contour/watchlists")
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("schema version 0", r.json()["detail"])
        self.assertEqual(r.json()["code"], "db_schema")
        self.assertEqual(r.json()["params"], {"path": str(self.db), "version": 0, "expected": st.SCHEMA_VERSION,
                                              "command": "python -m cf.research db migrate"})
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)

    def test_a_store_newer_than_the_code_asks_for_a_restart(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(f"PRAGMA user_version = {st.SCHEMA_VERSION + 1}")
        r = self.client.get("/api/contour/watchlists")
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(r.json()["code"], "db_schema_newer")
        self.assertIn("restart Desk", r.json()["detail"])

    def test_a_note_written_without_a_store_is_404_and_creates_nothing(self):
        r = self.client.post("/api/notes", json={"kind": "general", "key": "", "text": "x"})
        self.assertEqual((r.status_code, r.json()["code"]), (404, "db_missing"), r.text)
        self.assertFalse(self.db.exists())

    def test_without_the_shared_root_a_store_use_names_it_and_creates_nothing(self):
        self.db.parent.rmdir()
        for r in (self.client.get("/api/contour/watchlists"),
                  self.client.post("/api/notes", json={"kind": "general", "key": "", "text": "x"})):
            self.assertEqual((r.status_code, r.json()["code"]), (404, "shared_unavailable"), r.text)
            self.assertEqual(r.json()["params"]["root"], str(self.db.parent))
            self.assertIn("smb://", r.json()["detail"])
        self.assertFalse(self.db.parent.exists())

    def test_a_note_written_to_an_older_store_is_409_and_does_not_migrate_it(self):
        sqlite3.connect(self.db).close()
        r = self.client.post("/api/notes", json={"kind": "general", "key": "", "text": "x"})
        self.assertEqual((r.status_code, r.json()["code"]), (409, "db_schema"), r.text)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)

    def test_a_note_written_to_an_existing_store_does_not_seed_it(self):
        st.open_store(self.db, seed=False).close()
        r = self.client.post("/api/notes", json={"kind": "general", "key": "", "text": "x"})
        self.assertEqual(r.status_code, 201, r.text)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM taxonomy").fetchone()[0], 0)

    def test_a_write_while_another_connection_holds_the_lock_is_503_db_busy(self):
        st.open_store(self.db, seed=False).close()
        holder = sqlite3.connect(self.db)
        self.addCleanup(holder.close)
        holder.execute("BEGIN EXCLUSIVE")
        with mock.patch.object(st, "BUSY_TIMEOUT_S", 0.1):
            r = self.client.post("/api/notes", json={"kind": "general", "key": "", "text": "x"})
        holder.rollback()
        self.assertEqual((r.status_code, r.json()["code"]), (503, "db_busy"), r.text)
