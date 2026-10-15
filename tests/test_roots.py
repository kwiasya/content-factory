import getpass
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import store as st

VARS = ("CF_LOCAL_ROOT", "CF_SHARED_ROOT", "CF_FOOTAGE_ROOT", "CF_FACTORY_DB", "CF_PERSON")


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

    def test_with_nothing_set_the_roots_are_the_two_defaults(self):
        self.assertEqual((st.local_root(), st.shared_root()),
                         (Path.home() / "Movies" / "content-factory", Path("/Users/Shared/content-factory")))

    def test_each_new_variable_moves_only_its_root(self):
        os.environ["CF_LOCAL_ROOT"] = str(self.dir / "local")
        self.assertEqual((st.local_root(), st.shared_root()), (self.dir / "local", st.DEFAULT_SHARED_ROOT))
        os.environ.pop("CF_LOCAL_ROOT")
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "shared")
        self.assertEqual((st.local_root(), st.shared_root()), (st.DEFAULT_LOCAL_ROOT, self.dir / "shared"))

    def test_the_old_variable_moves_only_the_local_root(self):
        os.environ["CF_FOOTAGE_ROOT"] = str(self.dir / "old")
        self.assertEqual((st.local_root(), st.shared_root()), (self.dir / "old", st.DEFAULT_SHARED_ROOT))
        os.environ["CF_LOCAL_ROOT"] = str(self.dir / "local")
        self.assertEqual(st.local_root(), self.dir / "local")

    def test_person_is_cf_person_else_the_user_name(self):
        os.environ.pop("CF_PERSON", None)
        self.assertEqual(st.person(), getpass.getuser())
        os.environ["CF_PERSON"] = "someone"
        self.assertEqual(st.person(), "someone")

    def test_ensure_shared_root_refuses_a_missing_folder_with_the_mount_hint(self):
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "gone")
        with self.assertRaises(st.StoreError) as cm:
            st.ensure_shared_root()
        self.assertIn("smb://", str(cm.exception))
        self.assertFalse((self.dir / "gone").exists())
        os.environ["CF_SHARED_ROOT"] = str(self.dir)
        self.assertEqual(st.ensure_shared_root(), self.dir)

    def test_the_personal_env_file_sets_the_roots(self):
        envfile = self.dir / ".env"
        envfile.write_text(f"CF_SHARED_ROOT={self.dir / 'from-env'}\nCF_PERSON=envperson\n")
        os.environ["CF_ENV_FILE"] = str(envfile)
        with mock.patch.object(st, "_env_loaded", False):
            self.assertEqual((st.shared_root(), st.person()), (self.dir / "from-env", "envperson"))

    def test_default_db_is_under_the_shared_root_and_the_db_variable_wins(self):
        os.environ["CF_LOCAL_ROOT"] = str(self.dir / "local")
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "shared")
        self.assertEqual(st.default_db_path(), self.dir / "shared" / "factory.db")
        os.environ["CF_FACTORY_DB"] = str(self.dir / "x.db")
        self.assertEqual(st.default_db_path(), self.dir / "x.db")


if __name__ == "__main__":
    unittest.main()
