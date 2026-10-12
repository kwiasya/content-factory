"""cf.research.env: .env loading and the YouTube key lookup."""

import os
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


if __name__ == "__main__":
    unittest.main()
