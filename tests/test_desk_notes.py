"""Desk Notes API through the FastAPI TestClient on a temporary db, and the skill hook script."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cf.desk.app import create_app
from cf.research import notes
from cf.research import store as st

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "skill_notes.py"


class NotesApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        (base / "repo").mkdir()
        self.db = base / "footage" / "factory.db"
        self.client = TestClient(create_app(base / "repo", footage_root=base / "footage", db_path=self.db,
                                            web_dist=base / "dist"))

    def add(self, kind: str, key: str, text: str) -> dict:
        r = self.client.post("/api/notes", json={"kind": kind, "key": key, "text": text})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def listed(self, **params) -> list[dict]:
        r = self.client.get("/api/notes", params=params)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["notes"]

    def test_added_note_is_listed_open_and_lands_in_the_store(self):
        n = self.add("document", ".claude/skills/reel/SKILL.md", "Mention the loop rule")
        self.assertEqual((n["kind"], n["key"], n["text"], n["resolved_at"]),
                         ("document", ".claude/skills/reel/SKILL.md", "Mention the loop rule", None))
        self.assertEqual(self.listed(), [n])
        with st.open_store(self.db) as s:
            self.assertEqual([x.to_dict() for x in notes.list(s)], [n])

    def test_list_filters_by_kind_and_key(self):
        self.add("skill", "reel", "a")
        b = self.add("document", "CLAUDE.md", "b")
        self.add("document", "style.json", "c")
        self.assertEqual([x["text"] for x in self.listed(kind="document")], ["b", "c"])
        self.assertEqual(self.listed(kind="document", key="CLAUDE.md"), [b])

    def test_resolve_hides_from_open_list_but_all_keeps_it(self):
        n = self.add("idea", "3", "x")
        r = self.client.post(f"/api/notes/{n['id']}/resolve")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNotNone(r.json()["resolved_at"])
        self.assertEqual(self.listed(), [])
        self.assertEqual(self.listed(all=1), [r.json()])

    def test_delete_removes_the_note(self):
        n = self.add("card", "abc", "x")
        r = self.client.delete(f"/api/notes/{n['id']}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.listed(all=1), [])

    def test_missing_note_is_404_and_bad_note_is_422(self):
        self.assertEqual(self.client.post("/api/notes/99/resolve").status_code, 404)
        self.assertEqual(self.client.delete("/api/notes/99").status_code, 404)
        for body in ({"kind": "nope", "key": "x", "text": "t"}, {"kind": "skill", "key": "", "text": "t"},
                     {"kind": "skill", "key": "x", "text": " "}):
            with self.subTest(body=body):
                r = self.client.post("/api/notes", json=body)
                self.assertEqual(r.status_code, 422, r.text)
                self.assertIsInstance(r.json()["detail"], str)


class SkillHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "factory.db"

    def run_hook(self, stdin: str) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k not in ("CF_FACTORY_DB", "CF_FOOTAGE_ROOT")}
        env["CF_FACTORY_DB"] = str(self.db)
        return subprocess.run([sys.executable, str(HOOK)], input=stdin, env=env,
                              capture_output=True, text=True, timeout=30)

    def skill_call(self, name: str) -> str:
        return json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": name}})

    def assert_silent(self, stdin: str):
        p = self.run_hook(stdin)
        self.assertEqual((p.returncode, p.stdout, p.stderr), (0, "", ""))

    def context_of(self, event: dict) -> str:
        p = self.run_hook(json.dumps(event))
        self.assertEqual((p.returncode, p.stderr), (0, ""))
        out = json.loads(p.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], event["hook_event_name"])
        return out["additionalContext"]

    def seed(self):
        with st.open_store(self.db) as s:
            notes.add(s, "skill", "reel", "Shorter hook")
            notes.add(s, "document", ".claude/skills/reel/SKILL.md", "Fix step 3")
            notes.add(s, "general", "", "No word vibe")
            notes.add(s, "skill", "write-script", "Other skill")
            notes.add(s, "document", ".claude/skills/reel-old/SKILL.md", "Other folder")
            done = notes.add(s, "skill", "reel", "Already done")
            notes.resolve(s, done.id)

    def test_prints_open_notes_of_the_skill_its_documents_and_general_ones(self):
        self.seed()
        text = self.context_of(json.loads(self.skill_call("reel")))
        for wanted in ("Shorter hook", "Fix step 3", "No word vibe", "notes resolve"):
            self.assertIn(wanted, text)
        for unwanted in ("Other skill", "Other folder", "Already done"):
            self.assertNotIn(unwanted, text)

    def test_typed_slash_command_gets_the_same_notes(self):
        self.seed()
        text = self.context_of({"hook_event_name": "UserPromptExpansion", "command_name": "reel"})
        self.assertIn("Shorter hook", text)

    def test_silent_and_creates_nothing_when_the_db_is_missing(self):
        self.assert_silent(self.skill_call("reel"))
        self.assertFalse(self.db.exists())

    def test_silent_when_the_db_has_no_note_table(self):
        sqlite3.connect(self.db).close()
        self.assert_silent(self.skill_call("reel"))

    def test_silent_when_no_note_concerns_the_skill(self):
        with st.open_store(self.db) as s:
            notes.add(s, "skill", "write-script", "Other skill")
        self.assert_silent(self.skill_call("reel"))

    def test_silent_on_unexpected_input(self):
        self.seed()
        for stdin in ("", "not json", json.dumps({"hook_event_name": "PreToolUse", "tool_input": {}})):
            with self.subTest(stdin=stdin):
                self.assert_silent(stdin)
