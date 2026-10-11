"""Research store: where the database lives and what a fresh one holds. No network."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import store as st


class StoreLocationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_database_lives_at_the_footage_root(self):
        env = {"CF_FOOTAGE_ROOT": str(self.dir)}
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("CF_FACTORY_DB", None)
            self.assertEqual(st.default_db_path(), self.dir / "factory.db")

    def test_factory_db_variable_overrides_the_default(self):
        path = self.dir / "elsewhere" / "x.db"
        with mock.patch.dict(os.environ, {"CF_FACTORY_DB": str(path)}):
            self.assertEqual(st.default_db_path(), path)

    def test_open_creates_the_file_and_its_folder(self):
        path = self.dir / "nested" / "factory.db"
        with st.open_store(path) as s:
            self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)
        self.assertTrue(path.exists())

    def test_fresh_store_has_every_table_of_the_spec(self):
        with st.open_store(self.dir / "f.db") as s:
            self.assertLessEqual(
                {"watchlist", "channel", "watchlist_channel", "video", "snapshot", "card",
                 "idea", "hook", "taxonomy", "quota"},
                set(s.tables()))

    def test_reopening_keeps_the_schema_version(self):
        path = self.dir / "f.db"
        with st.open_store(path):
            pass
        with st.open_store(path) as s:
            self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)

    def test_a_newer_database_is_refused(self):
        path = self.dir / "f.db"
        with st.open_store(path) as s:
            s.conn.execute(f"PRAGMA user_version = {st.SCHEMA_VERSION + 1}")
        with self.assertRaises(st.StoreError) as cm:
            st.open_store(path)
        self.assertIn("newer", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
