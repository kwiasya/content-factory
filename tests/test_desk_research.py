"""Desk research documents, search and skill link map through the TestClient on a temporary git repo."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from cf.desk.app import create_app
from test_desk_api import git

README = """# Research

| # | Файл | Тема | Статус |
|---|------|------|--------|
| 01 | `prompts/01-resolve-api.md` | Что агент может делать в Resolve | 1 ответ получен |
| 09 | `prompts/09-storytelling.md` | Структуры сторителлинга | готово |
"""

TREE = {
    "docs/research/README.md": README,
    "docs/research/SYNTHESIS.md": "# Synthesis\nPipeline plan.\n",
    "docs/research/SYNTHESIS-content.md": "# Content synthesis\n",
    "docs/research/01-resolve-api/result-a.md": "# Resolve answer\n",
    "docs/research/01-resolve-api/verification.md": "# Verified\n",
    "docs/research/09-storytelling/chatgpt.md": "# ChatGPT answer\nThe Hook Ladder works.\n",
    "docs/research/09-storytelling/result-a.md": "# Opus answer\n## Hooks\nA hook opens a loop.\n",
    "docs/research/09-storytelling/rules.md": "# 09 rules\n|id|rule|\n|---|---|\n|R09-01|Stakes first|\n",
    "docs/research/09-storytelling/notes/stakes.md": "# Stakes notes\n",
    "docs/research/prompts/09-storytelling.md": "# Prompt, hidden\n",
    "docs/research/prompts/_context.md": "# Context, hidden\n",
    "docs/research/loose-note.md": "# not catalogued\n",
    ".claude/skills/alpha/SKILL.md": "# Alpha\n",
    ".claude/skills/remotion-foo/SKILL.md": "# Remotion foo\n",
    "CLAUDE.md": "# Project\n",
    "src/cf/research/store.py": "V1 = \"\"\"\nCREATE TABLE watchlist (\n  id INTEGER\n);\nCREATE TABLE idea (\n  id INTEGER\n);\n\"\"\"\n",
}


class ResearchTestCase(unittest.TestCase):
    tree = TREE

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        for rel, text in self.tree.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "Initial tree")
        footage = base / "footage"
        footage.mkdir()
        env = mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(footage)})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(create_app(self.repo, footage_root=footage, db_path=footage / "factory.db",
                                            web_dist=base / "dist"))

    def get(self, url: str, **params) -> dict:
        r = self.client.get(url, params=params)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()


class ResearchCatalogTest(ResearchTestCase):
    def docs(self) -> dict:
        groups = {g["id"]: g for g in self.get("/api/catalog")["groups"]}
        return {d["path"]: d for d in groups["research"]["docs"]}

    def test_research_group_lists_answers_notes_rules_synthesis_and_readme_without_prompts(self):
        self.assertEqual(sorted(self.docs()), [
            "docs/research/01-resolve-api/result-a.md",
            "docs/research/01-resolve-api/verification.md",
            "docs/research/09-storytelling/chatgpt.md",
            "docs/research/09-storytelling/notes/stakes.md",
            "docs/research/09-storytelling/result-a.md",
            "docs/research/09-storytelling/rules.md",
            "docs/research/README.md",
            "docs/research/SYNTHESIS-content.md",
            "docs/research/SYNTHESIS.md",
        ])

    def test_only_rules_and_synthesis_are_editable(self):
        editable = sorted(p for p, d in self.docs().items() if d["editable"])
        self.assertEqual(editable, [
            "docs/research/09-storytelling/rules.md",
            "docs/research/SYNTHESIS-content.md",
            "docs/research/SYNTHESIS.md",
        ])

    def test_prompts_are_not_readable_even_with_all(self):
        r = self.client.get("/api/doc", params={"path": "docs/research/prompts/_context.md"})
        self.assertEqual(r.status_code, 404)
        groups = self.get("/api/catalog", all=1)["groups"]
        paths = [d["path"] for g in groups for d in g["docs"]]
        self.assertFalse([p for p in paths if "/prompts/" in p])

    def test_rules_save_and_answer_is_refused(self):
        rules = self.get("/api/doc", path="docs/research/09-storytelling/rules.md")
        r = self.client.put("/api/doc", json={"path": rules["path"], "text": "# edited\n", "hash": rules["hash"]})
        self.assertEqual(r.status_code, 200, r.text)
        answer = self.get("/api/doc", path="docs/research/09-storytelling/result-a.md")
        r = self.client.put("/api/doc", json={"path": answer["path"], "text": "# edited\n", "hash": answer["hash"]})
        self.assertEqual(r.status_code, 403)


class ResearchTopicsTest(ResearchTestCase):
    def test_topics_come_from_numbered_folders_with_file_flags_and_readme_titles(self):
        body = self.get("/api/research")
        self.assertEqual(body["topics"], [
            {"id": "01-resolve-api", "number": "01", "slug": "resolve-api",
             "title": "Что агент может делать в Resolve", "status": "1 ответ получен",
             "chatgpt": False, "result_a": True, "rules": False, "verification": True, "notes": [],
             "docs": ["docs/research/01-resolve-api/result-a.md", "docs/research/01-resolve-api/verification.md"]},
            {"id": "09-storytelling", "number": "09", "slug": "storytelling",
             "title": "Структуры сторителлинга", "status": "готово",
             "chatgpt": True, "result_a": True, "rules": True, "verification": False,
             "notes": ["docs/research/09-storytelling/notes/stakes.md"],
             "docs": ["docs/research/09-storytelling/chatgpt.md", "docs/research/09-storytelling/result-a.md",
                      "docs/research/09-storytelling/rules.md"]},
        ])
        self.assertEqual(body["synthesis"], ["docs/research/SYNTHESIS-content.md", "docs/research/SYNTHESIS.md"])
        self.assertEqual(body["readme"], "docs/research/README.md")

    def test_no_research_folder_is_an_empty_list(self):
        git(self.repo, "rm", "-rq", "docs/research")
        self.assertEqual(self.get("/api/research"), {"topics": [], "synthesis": [], "readme": None})


if __name__ == "__main__":
    unittest.main()
