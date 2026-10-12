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


class ReadTest(DeskTestCase):
    def test_read_returns_text_hash_and_entry(self):
        doc = self.doc("CLAUDE.md")
        self.assertEqual(doc["text"], "# Project\n")
        self.assertEqual(doc["hash"], "sha256:aef277fb6a70a89681a85e1b6d23f44ee2a6cc58490f9f5c95fc99db6d2d3542")
        self.assertEqual(doc["group"], "content")
        self.assertEqual(doc["git"], "clean")
        self.assertTrue(doc["editable"])

    def test_hidden_vendored_doc_reads_but_is_not_editable(self):
        doc = self.doc(".claude/skills/remotion-foo/SKILL.md")
        self.assertEqual(doc["text"], "# Remotion foo\n")
        self.assertFalse(doc["editable"])

    def test_uncatalogued_and_traversal_paths_are_404(self):
        outside = Path(self.tmp.name) / "outside.md"
        outside.write_text("outside\n")
        for path in ["secret.txt", "docs/adr/0001-x.md", "../outside.md", "docs/../secret.txt",
                     "/etc/passwd", str(outside), ".claude/skills/alpha/../../../CLAUDE.md", "nope.md"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get("/api/doc", params={"path": path}).status_code, 404)

    def test_symlink_out_of_the_repo_is_404(self):
        outside = Path(self.tmp.name) / "outside.md"
        outside.write_text("outside\n")
        (self.repo / "docs" / "agents" / "link.md").symlink_to(outside)
        self.assertEqual(self.client.get("/api/doc", params={"path": "docs/agents/link.md"}).status_code, 404)


class WriteTest(DeskTestCase):
    def put(self, path: str, text: str, hash: str):
        return self.client.put("/api/doc", json={"path": path, "text": text, "hash": hash})

    def test_write_with_the_read_hash_lands_in_the_same_file(self):
        read = self.doc(".claude/skills/alpha/SKILL.md")
        r = self.put(read["path"], "# Alpha v2\n", read["hash"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((self.repo / ".claude/skills/alpha/SKILL.md").read_text(), "# Alpha v2\n")
        self.assertEqual(r.json()["hash"], self.doc(read["path"])["hash"])
        self.assertEqual(r.json()["git"], "modified")
        self.assertEqual(sorted(p.name for p in (self.repo / ".claude/skills/alpha").iterdir()), ["SKILL.md"])

    def test_write_after_the_file_changed_on_disk_is_409_with_the_fresh_text(self):
        read = self.doc("CLAUDE.md")
        (self.repo / "CLAUDE.md").write_text("# Editor wrote this\n")
        r = self.put("CLAUDE.md", "# Author's edit\n", read["hash"])
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["text"], "# Editor wrote this\n")
        self.assertEqual(r.json()["hash"], self.doc("CLAUDE.md")["hash"])
        self.assertEqual((self.repo / "CLAUDE.md").read_text(), "# Editor wrote this\n")

    def test_read_only_doc_is_refused(self):
        read = self.doc("formats/walk-reel/hook-library.md")
        r = self.put(read["path"], "# edited\n", read["hash"])
        self.assertEqual(r.status_code, 403)
        self.assertEqual((self.repo / "formats/walk-reel/hook-library.md").read_text(), "# Hooks\n")

    def test_uncatalogued_or_traversal_write_is_404_and_writes_nothing(self):
        for path in ["secret.txt", "../outside.md", "docs/agents/new.md"]:
            with self.subTest(path=path):
                self.assertEqual(self.put(path, "x\n", "sha256:0").status_code, 404)
        self.assertEqual((self.repo / "secret.txt").read_text(), "not catalogued\n")
        self.assertFalse((Path(self.tmp.name) / "outside.md").exists())
        self.assertFalse((self.repo / "docs/agents/new.md").exists())

    def test_invalid_json_is_refused_for_a_json_doc(self):
        read = self.doc("style.json")
        r = self.put("style.json", '{"schema": ', read["hash"])
        self.assertEqual(r.status_code, 422)
        self.assertEqual((self.repo / "style.json").read_text(), '{"schema": "style/1"}\n')


if __name__ == "__main__":
    unittest.main()
