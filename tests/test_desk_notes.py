"""Desk Notes API through the FastAPI TestClient on a temporary db, and the skill hook script."""

import json
import os
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
