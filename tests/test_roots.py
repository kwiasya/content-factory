import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import store as st

VARS = ("CF_LOCAL_ROOT", "CF_SHARED_ROOT", "CF_FOOTAGE_ROOT", "CF_FACTORY_DB")


class RootsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        env = mock.patch.dict(os.environ, {})
        env.start()
        self.addCleanup(env.stop)
        for var in VARS:
            os.environ.pop(var, None)

    def test_with_nothing_set_both_roots_are_the_default(self):
        default = Path.home() / "Movies" / "content-factory"
        self.assertEqual((st.local_root(), st.shared_root(), st.single_root()), (default, default, default))

    def test_each_new_variable_moves_only_its_root(self):
        default = Path.home() / "Movies" / "content-factory"
        os.environ["CF_LOCAL_ROOT"] = str(self.dir / "local")
        self.assertEqual((st.local_root(), st.shared_root()), (self.dir / "local", default))
        os.environ.pop("CF_LOCAL_ROOT")
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "shared")
        self.assertEqual((st.local_root(), st.shared_root()), (default, self.dir / "shared"))

    def test_the_old_variable_moves_both_and_a_new_one_wins(self):
        os.environ["CF_FOOTAGE_ROOT"] = str(self.dir / "old")
        self.assertEqual((st.local_root(), st.shared_root()), (self.dir / "old", self.dir / "old"))
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "shared")
        self.assertEqual((st.local_root(), st.shared_root()), (self.dir / "old", self.dir / "shared"))

    def test_single_root_refuses_two_different_roots(self):
        os.environ["CF_LOCAL_ROOT"] = str(self.dir / "a")
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "b")
        with self.assertRaises(st.RootsError) as cm:
            st.single_root()
        self.assertIn("separate roots are not supported yet", str(cm.exception))
        self.assertIsInstance(cm.exception, st.StoreError)

    def test_single_root_accepts_one_folder_spelled_two_ways(self):
        home = Path.home()
        os.environ["CF_LOCAL_ROOT"] = "~/x-cf-root"
        os.environ["CF_SHARED_ROOT"] = f"{home}/x-cf-root/"
        self.assertEqual(st.single_root(), home / "x-cf-root")

    def test_default_db_is_under_the_shared_root_and_the_db_variable_wins(self):
        os.environ["CF_LOCAL_ROOT"] = str(self.dir / "local")
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "shared")
        self.assertEqual(st.default_db_path(), self.dir / "shared" / "factory.db")
        os.environ["CF_FACTORY_DB"] = str(self.dir / "x.db")
        self.assertEqual(st.default_db_path(), self.dir / "x.db")


if __name__ == "__main__":
    unittest.main()
