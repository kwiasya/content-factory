"""Desk HTTP API through the FastAPI TestClient on a temporary git repo, footage root and db."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from cf.desk.app import create_app

TREE = {
    ".claude/skills/alpha/SKILL.md": "---\nname: alpha\n---\n# Alpha\n",
    ".claude/skills/beta/SKILL.md": "# Beta\n",
    ".claude/skills/beta/templates/x.md": "template\n",
    ".claude/skills/remotion-foo/SKILL.md": "# Remotion foo\n",
    ".claude/skills/remotion-foo/rules/a.md": "rule\n",
    "CLAUDE.md": "# Project\n",
    "docs/agents/domain.md": "# Domain\n",
    "docs/adr/0001-x.md": "# not catalogued\n",
    "style.json": '{"schema": "style/1"}\n',
    "research/templates/brief.md": "# Brief\n",
    "research/taxonomy.json": '{"kinds": {}}\n',
    "formats/walk-reel/FORMAT.md": "# Walk reel\n",
    "formats/walk-reel/hook-library.md": "# Hooks\n",
    "secret.txt": "not catalogued\n",
}


def git(root: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    return subprocess.run(["git", *args], cwd=root, env=env, check=True,
                          capture_output=True, text=True).stdout


class DeskTestCase(unittest.TestCase):
    token = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        for rel, text in TREE.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        (self.repo / ".gitignore").write_text("author/\n")
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "Initial tree")
        self.footage = base / "footage"
        self.footage.mkdir()
        self.db = self.footage / "factory.db"
        env = mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(self.footage)})
        env.start()
        self.addCleanup(env.stop)
        self.dist = base / "dist"
        self.client = TestClient(create_app(self.repo, footage_root=self.footage, db_path=self.db,
                                            web_dist=self.dist, token=self.token))

    def catalog(self, **params) -> dict:
        r = self.client.get("/api/catalog", params=params)
        self.assertEqual(r.status_code, 200, r.text)
        return {g["id"]: g for g in r.json()["groups"]}

    def paths(self, group: dict) -> list[str]:
        return [d["path"] for d in group["docs"]]

    def doc(self, path: str) -> dict:
        r = self.client.get("/api/doc", params={"path": path})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()


class CatalogTest(DeskTestCase):
    def test_groups_list_own_skills_content_and_formats_with_vendored_hidden(self):
        groups = self.catalog()
        self.assertEqual(list(groups), ["skills", "content", "formats"])
        self.assertEqual(self.paths(groups["skills"]), [
            ".claude/skills/alpha/SKILL.md", ".claude/skills/beta/SKILL.md",
            ".claude/skills/beta/templates/x.md"])
        self.assertEqual(self.paths(groups["content"]), [
            "CLAUDE.md", "docs/agents/domain.md", "style.json", "research/templates/brief.md",
            "research/taxonomy.json"])
        self.assertEqual(self.paths(groups["formats"]), [
            "formats/walk-reel/FORMAT.md", "formats/walk-reel/hook-library.md"])

    def test_all_shows_the_vendored_skills(self):
        groups = self.catalog(all=1)
        self.assertEqual(list(groups), ["skills", "skills-vendored", "content", "formats"])
        self.assertTrue(groups["skills-vendored"]["hidden"])
        self.assertEqual(self.paths(groups["skills-vendored"]), [
            ".claude/skills/remotion-foo/SKILL.md", ".claude/skills/remotion-foo/rules/a.md"])

    def test_entries_carry_title_kind_editable_and_git_status(self):
        docs = {d["path"]: d for g in self.catalog().values() for d in g["docs"]}
        self.assertEqual(docs[".claude/skills/alpha/SKILL.md"]["title"], "alpha")
        self.assertEqual(docs[".claude/skills/beta/templates/x.md"]["title"], "beta · templates/x.md")
        self.assertEqual(docs["formats/walk-reel/FORMAT.md"]["title"], "walk-reel · FORMAT.md")
        self.assertEqual(docs["style.json"]["kind"], "json")
        self.assertEqual(docs["CLAUDE.md"]["kind"], "markdown")
        self.assertTrue(docs["formats/walk-reel/FORMAT.md"]["editable"])
        self.assertFalse(docs["formats/walk-reel/hook-library.md"]["editable"])
        self.assertEqual(docs["CLAUDE.md"]["git"], "clean")

    def test_missing_author_folder_is_an_empty_state_pointing_to_author_setup(self):
        content = self.catalog()["content"]
        self.assertEqual(content["empty"][0]["glob"], "author/*.md")
        self.assertIn("/author-setup", content["empty"][0]["hint"])

    def test_author_files_are_listed_when_present(self):
        (self.repo / "author").mkdir()
        (self.repo / "author" / "who-i-am.md").write_text("# Me\n")
        content = self.catalog()["content"]
        self.assertIn("author/who-i-am.md", self.paths(content))
        self.assertEqual(content["empty"], [])
        entry = next(d for d in content["docs"] if d["path"] == "author/who-i-am.md")
        self.assertEqual(entry["git"], "ignored")
        self.assertTrue(entry["editable"])


if __name__ == "__main__":
    unittest.main()
