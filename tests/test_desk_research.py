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

ALPHA = """---
name: alpha
---
# Alpha
Run `.venv/bin/python -m cf.research watchlist add <name>` then `python -m cf.research quota --json`.
Writes one Watchlist row and reads the `idea` table. Then hand over to `/beta`.
See docs/research/SYNTHESIS.md, `CLAUDE.md` and docs/research/09-storytelling/, not docs/missing.md.
Hook first.
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
    "docs/research/prompts/09-storytelling.md": "# Prompt about a hook, hidden\n",
    "docs/research/prompts/_context.md": "# Context, hidden\n",
    "docs/research/loose-note.md": "# not catalogued\n",
    ".claude/skills/alpha/SKILL.md": ALPHA,
    ".claude/skills/beta/SKILL.md": "# Beta\nBuilds on the `remotion-foo` skill.\n",
    ".claude/skills/beta/templates/x.md": "Template for `alpha` output.\n",
    ".claude/skills/remotion-foo/SKILL.md": "# Remotion foo\nA HOOK in a vendored skill.\n",
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


class SearchTest(ResearchTestCase):
    def search(self, q: str, **params) -> dict:
        return self.get("/api/search", q=q, **params)

    def hits(self, body: dict) -> dict:
        return {h["path"]: h for g in body["groups"] for h in g["hits"]}

    def test_case_insensitive_hits_are_grouped_by_group_and_path_with_line_snippets(self):
        body = self.search("hook")
        self.assertEqual([g["id"] for g in body["groups"]], ["skills", "research"])
        self.assertEqual([h["path"] for h in body["groups"][1]["hits"]], [
            "docs/research/09-storytelling/chatgpt.md", "docs/research/09-storytelling/result-a.md"])
        result = self.hits(body)["docs/research/09-storytelling/result-a.md"]
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["snippets"], [{"line": 2, "text": "## Hooks"}, {"line": 3, "text": "A hook opens a loop."}])
        self.assertEqual(result["title"], "09-storytelling · result-a.md")
        self.assertEqual(body["total"], 3)
        self.assertFalse(body["truncated"])

    def test_hidden_groups_are_searched_only_with_all_and_prompts_never(self):
        self.assertNotIn(".claude/skills/remotion-foo/SKILL.md", self.hits(self.search("hook")))
        hits = self.hits(self.search("HOOK", all=1))
        self.assertIn(".claude/skills/remotion-foo/SKILL.md", hits)
        self.assertFalse([p for p in hits if "/prompts/" in p])

    def test_snippets_stop_at_three_and_long_lines_are_cut_around_the_match(self):
        line = "x" * 300 + " stakes " + "y" * 300
        (self.repo / "docs/research/09-storytelling/notes/stakes.md").write_text("\n".join([line] * 5) + "\n")
        hit = self.hits(self.search("Stakes"))["docs/research/09-storytelling/notes/stakes.md"]
        self.assertEqual(hit["count"], 5)
        self.assertEqual([s["line"] for s in hit["snippets"]], [1, 2, 3])
        self.assertIn("stakes", hit["snippets"][0]["text"])
        self.assertLess(len(hit["snippets"][0]["text"]), 200)

    def test_hits_are_capped_at_200(self):
        notes = self.repo / "docs/research/09-storytelling/notes"
        for i in range(210):
            (notes / f"n{i:03}.md").write_text("needle\n")
        body = self.search("needle")
        self.assertEqual(body["total"], 200)
        self.assertTrue(body["truncated"])

    def test_blank_query_is_refused(self):
        self.assertEqual(self.client.get("/api/search", params={"q": "  "}).status_code, 422)
        self.assertEqual(self.client.get("/api/search").status_code, 422)


class SkillLinksTest(ResearchTestCase):
    def test_map_lists_paths_commands_tables_and_skills_each_own_skill_mentions(self):
        skills = {s["name"]: s for s in self.get("/api/skills/links")["skills"]}
        self.assertEqual(list(skills), ["alpha", "beta"])
        self.assertEqual(skills["alpha"], {
            "name": "alpha", "path": ".claude/skills/alpha/SKILL.md",
            "paths": ["CLAUDE.md", "docs/research/09-storytelling", "docs/research/SYNTHESIS.md"],
            "catalogued": ["CLAUDE.md", "docs/research/SYNTHESIS.md"],
            "commands": ["cf.research quota", "cf.research watchlist add"],
            "tables": ["idea", "watchlist"],
            "skills": ["beta"],
            "mentioned_by": ["beta"],
        })

    def test_inbound_links_come_from_any_file_of_the_mentioning_skill(self):
        beta = self.get("/api/skills/beta/links")
        self.assertEqual(beta["skills"], ["alpha", "remotion-foo"])
        self.assertEqual(beta["mentioned_by"], ["alpha"])
        self.assertEqual(beta["paths"], [])
        self.assertEqual(beta["tables"], [])

    def test_a_folder_without_skill_md_is_not_an_own_skill(self):
        stray = self.repo / ".claude/skills/delta/notes.md"
        stray.parent.mkdir(parents=True)
        stray.write_text("Hand over to /alpha.\n")
        skills = {s["name"]: s for s in self.get("/api/skills/links")["skills"]}
        self.assertEqual(list(skills), ["alpha", "beta"])
        self.assertEqual(skills["alpha"]["mentioned_by"], ["beta"])
        self.assertEqual(self.client.get("/api/skills/delta/links").status_code, 404)

    def test_unknown_or_vendored_skill_is_404(self):
        for name in ["nope", "remotion-foo"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(f"/api/skills/{name}/links").status_code, 404)

    def test_without_the_store_module_no_tables_are_found(self):
        (self.repo / "src/cf/research/store.py").unlink()
        self.assertEqual(self.get("/api/skills/alpha/links")["tables"], [])


if __name__ == "__main__":
    unittest.main()
