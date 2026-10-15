"""python -m cf.desk flags: localhost by default, any other host only with --token."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from cf.desk import cli


class DeskCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        footage = Path(self.tmp.name) / "footage"
        env = mock.patch.dict(os.environ, {"CF_LOCAL_ROOT": str(footage), "CF_SHARED_ROOT": str(footage)})
        env.start()
        self.addCleanup(env.stop)
        self.footage = footage
        run = mock.patch.object(cli.uvicorn, "run")
        self.run = run.start()
        self.addCleanup(run.stop)

    def main(self, *argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            try:
                code = cli.main(["--repo", str(self.repo), *argv])
            except SystemExit as e:
                code = e.code
        return code, err.getvalue()

    def test_defaults_bind_localhost_on_8765(self):
        code, _ = self.main()
        self.assertEqual(code, 0)
        _, kwargs = self.run.call_args
        self.assertEqual((kwargs["host"], kwargs["port"]), ("127.0.0.1", 8765))
        meta = TestClient(self.run.call_args.args[0]).get("/api/meta").json()
        self.assertEqual(meta["repo"], str(self.repo.resolve()))
        self.assertEqual((meta["local_root"], meta["shared_root"]), (str(self.footage), str(self.footage)))
        self.assertNotIn("footage_root", meta)
        self.assertEqual(meta["db_path"], str(self.footage / "factory.db"))

    def test_two_different_roots_exit_2_with_the_roots_message(self):
        with mock.patch.dict(os.environ, {"CF_SHARED_ROOT": str(self.footage.parent / "shared")}):
            code, err = self.main()
        self.assertEqual(code, 2)
        self.assertIn("separate roots are not supported yet", err)
        self.run.assert_not_called()

    def test_the_old_root_variable_still_sets_both_roots(self):
        with mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(self.footage)}):
            os.environ.pop("CF_LOCAL_ROOT")
            os.environ.pop("CF_SHARED_ROOT")
            code, _ = self.main()
        self.assertEqual(code, 0)
        meta = TestClient(self.run.call_args.args[0]).get("/api/meta").json()
        self.assertEqual((meta["local_root"], meta["shared_root"]), (str(self.footage), str(self.footage)))

    def test_non_localhost_host_without_token_is_refused(self):
        code, err = self.main("--host", "0.0.0.0")
        self.assertNotEqual(code, 0)
        self.assertIn("--token", err)
        self.run.assert_not_called()

    def test_non_localhost_host_with_token_starts(self):
        code, _ = self.main("--host", "0.0.0.0", "--port", "9000", "--token", "t")
        self.assertEqual(code, 0)
        _, kwargs = self.run.call_args
        self.assertEqual((kwargs["host"], kwargs["port"]), ("0.0.0.0", 9000))

    def test_missing_repo_is_an_error(self):
        code, err = self.main("--repo", str(Path(self.tmp.name) / "nope"))
        self.assertNotEqual(code, 0)
        self.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
