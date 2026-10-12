"""python -m cf.research notes: Notes from the Author to the Editor on a temp database."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from cf.research import cli


class NotesCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "f.db")

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*argv, "--db", self.db])
        return code, out.getvalue(), err.getvalue()

    def json_of(self, *argv):
        code, out, err = self.run_cli(*argv, "--json")
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_added_note_is_listed_open(self):
        added = self.json_of("notes", "add", "skill", "write-script", "Hook must be under 1.5 s")
        self.assertEqual((added["kind"], added["key"], added["text"], added["resolved_at"]),
                         ("skill", "write-script", "Hook must be under 1.5 s", None))
        [listed] = self.json_of("notes", "list")
        self.assertEqual(listed, added)

    def test_list_filters_by_kind_and_key(self):
        self.json_of("notes", "add", "skill", "write-script", "a")
        doc = self.json_of("notes", "add", "document", "CLAUDE.md", "b")
        self.json_of("notes", "add", "document", "style.json", "c")
        self.assertEqual([n["text"] for n in self.json_of("notes", "list", "--kind", "document")], ["b", "c"])
        self.assertEqual(self.json_of("notes", "list", "--kind", "document", "--key", "CLAUDE.md"), [doc])

    def test_resolved_note_leaves_the_open_list_but_stays_in_all(self):
        n = self.json_of("notes", "add", "idea", "12", "Too close to the last reel")
        resolved = self.json_of("notes", "resolve", str(n["id"]))
        self.assertIsNotNone(resolved["resolved_at"])
        self.assertEqual(self.json_of("notes", "list"), [])
        self.assertEqual(self.json_of("notes", "list", "--all"), [resolved])

    def test_deleted_note_is_gone(self):
        n = self.json_of("notes", "add", "card", "dQw4w9WgXcQ", "x")
        self.json_of("notes", "delete", str(n["id"]))
        self.assertEqual(self.json_of("notes", "list", "--all"), [])

    def test_general_note_has_an_empty_key(self):
        n = self.json_of("notes", "add", "general", "", "Never use the word vibe")
        self.assertEqual((n["kind"], n["key"]), ("general", ""))

    def test_errors_exit_1_with_one_line(self):
        for argv in (("notes", "resolve", "99"), ("notes", "delete", "99"),
                     ("notes", "add", "skill", "", "text"), ("notes", "add", "skill", "x", "  "),
                     ("notes", "add", "general", "x", "text")):
            with self.subTest(argv=argv):
                code, out, err = self.run_cli(*argv)
                self.assertEqual((code, out), (1, ""))
                self.assertTrue(err.startswith("error: "), err)
                self.assertEqual(err.count("\n"), 1)

    def test_human_list_is_a_table(self):
        self.json_of("notes", "add", "skill", "reel", "Shorter hook")
        code, out, _ = self.run_cli("notes", "list")
        self.assertEqual(code, 0)
        self.assertIn("| 1 | skill | reel | Shorter hook |", out)
