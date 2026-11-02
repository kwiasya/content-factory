"""cf.research.env: the personal .env, the shared secrets.env and the YouTube key lookup."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import env


class LoadEnvTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / ".env"
        self.addCleanup(self.dir.cleanup)

    def test_reads_pairs_and_skips_noise(self):
        self.path.write_text('# comment\n\nexport A=1\nB = "two words"\nC=\'x\'\nbroken line\n', encoding="utf-8")
        with mock.patch.dict(os.environ, {}, clear=True):
            found = env.load_env(self.path)
            self.assertEqual(found, {"A": "1", "B": "two words", "C": "x"})
            self.assertEqual((os.environ["A"], os.environ["B"], os.environ["C"]), ("1", "two words", "x"))

    def test_shell_value_wins_over_file(self):
        self.path.write_text("YOUTUBE_API_KEY=from-file\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": "from-shell"}, clear=True):
            self.assertEqual(env.api_key(self.path), "from-shell")

    def test_key_from_file_when_shell_has_none(self):
        self.path.write_text("YOUTUBE_API_KEY=from-file\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(env.api_key(self.path), "from-file")

    def test_cf_env_file_points_elsewhere(self):
        other = Path(self.dir.name) / "elsewhere.env"
        other.write_text("YOUTUBE_API_KEY=from-other\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"CF_ENV_FILE": str(other)}, clear=True):
            self.assertEqual(env.env_path(), other)
            self.assertEqual(env.api_key(), "from-other")

    def test_missing_file_means_no_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(env.load_env(self.path), {})
            self.assertIsNone(env.api_key(self.path))


class SecretsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        base = Path(self.dir.name)
        self.personal, self.secrets = base / ".env", base / "secrets.env"
        patch = mock.patch.dict(os.environ, {"CF_ENV_FILE": str(self.personal),
                                             "CF_SECRETS_FILE": str(self.secrets)}, clear=True)
        patch.start()
        self.addCleanup(patch.stop)

    def test_personal_env_wins_over_secrets_and_the_shell_over_both(self):
        self.personal.write_text("YOUTUBE_API_KEY=personal\n")
        self.secrets.write_text("YOUTUBE_API_KEY=shared\nINSTAGRAM_USER_ID=42\n")
        self.assertEqual((env.api_key(), env.ig_user_id()), ("personal", "42"))
        os.environ["INSTAGRAM_USER_ID"] = "shell"
        self.assertEqual(env.ig_user_id(), "shell")

    def test_secrets_file_defaults_to_the_shared_root(self):
        os.environ.pop("CF_SECRETS_FILE")
        os.environ["CF_SHARED_ROOT"] = self.dir.name
        self.assertEqual(env.secrets_path(), self.secrets)
        self.secrets.write_text("YOUTUBE_API_KEY=shared\n")
        self.assertEqual(env.api_key(), "shared")

    def test_set_value_rewrites_the_file_the_variable_came_from(self):
        self.secrets.write_text("# shared\nINSTAGRAM_ACCESS_TOKEN=old\nYOUTUBE_API_KEY=k\n")
        self.assertEqual(env.set_value(env.IG_TOKEN_VAR, "new"), self.secrets)
        self.assertEqual(self.secrets.read_text(), "# shared\nINSTAGRAM_ACCESS_TOKEN=new\nYOUTUBE_API_KEY=k\n")
        self.assertEqual(stat.S_IMODE(self.secrets.stat().st_mode), 0o600)
        self.assertFalse(self.personal.exists())
        self.personal.write_text("INSTAGRAM_ACCESS_TOKEN=mine\n")
        self.assertEqual(env.set_value(env.IG_TOKEN_VAR, "newer"), self.personal)
        self.assertEqual(self.personal.read_text(), "INSTAGRAM_ACCESS_TOKEN=newer\n")
        self.assertIn("INSTAGRAM_ACCESS_TOKEN=new\n", self.secrets.read_text())

    def test_a_new_variable_goes_to_secrets(self):
        self.assertEqual(env.set_value(env.IG_TOKEN_VAR, "t"), self.secrets)
        self.assertEqual(self.secrets.read_text(), "INSTAGRAM_ACCESS_TOKEN=t\n")

    def test_a_failing_chmod_is_tolerated(self):
        self.secrets.write_text("INSTAGRAM_ACCESS_TOKEN=old\n")
        with mock.patch.object(env.os, "chmod", side_effect=PermissionError(1, "Operation not permitted")), \
                self.assertLogs("cf.research.env", "WARNING"):
            env.set_value(env.IG_TOKEN_VAR, "new")
        self.assertEqual(self.secrets.read_text(), "INSTAGRAM_ACCESS_TOKEN=new\n")

    def test_an_unmounted_share_is_refused_and_nothing_created(self):
        os.environ["CF_SECRETS_FILE"] = str(Path(self.dir.name) / "gone" / "secrets.env")
        with self.assertRaises(Exception) as cm:
            env.set_value(env.IG_TOKEN_VAR, "t")
        self.assertIn("smb://", str(cm.exception))
        self.assertFalse((Path(self.dir.name) / "gone").exists())


if __name__ == "__main__":
    unittest.main()
