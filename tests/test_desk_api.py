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
        self.assertEqual(list(groups), ["skills", "content", "formats", "research"])
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
        self.assertEqual(list(groups), ["skills", "skills-vendored", "content", "formats", "research"])
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


class GitTest(DeskTestCase):
    def test_diff_against_head_shows_the_edit(self):
        (self.repo / "CLAUDE.md").write_text("# Project\nNew rule\n")
        r = self.client.get("/api/doc/diff", params={"path": "CLAUDE.md"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["git"], "modified")
        self.assertIn("+New rule", r.json()["diff"])
        self.assertIn("--- a/CLAUDE.md", r.json()["diff"])

    def test_clean_file_has_an_empty_diff(self):
        r = self.client.get("/api/doc/diff", params={"path": "CLAUDE.md"})
        self.assertEqual(r.json(), {"path": "CLAUDE.md", "git": "clean", "diff": ""})

    def test_untracked_file_diffs_as_all_added(self):
        (self.repo / "docs/agents/new.md").write_text("fresh\n")
        r = self.client.get("/api/doc/diff", params={"path": "docs/agents/new.md"}).json()
        self.assertEqual(r["git"], "untracked")
        self.assertIn("+fresh", r["diff"])

    def test_log_lists_commits_touching_the_file(self):
        (self.repo / "CLAUDE.md").write_text("# Project v2\n")
        git(self.repo, "commit", "-q", "-am", "Reword the project rule")
        (self.repo / "style.json").write_text("{}\n")
        git(self.repo, "commit", "-q", "-am", "Unrelated style change")
        entries = self.client.get("/api/doc/log", params={"path": "CLAUDE.md"}).json()["entries"]
        self.assertEqual([e["subject"] for e in entries], ["Reword the project rule", "Initial tree"])
        self.assertEqual(entries[0]["author"], "t")
        self.assertEqual(len(entries[0]["hash"]), 40)

    def test_diff_and_log_refuse_uncatalogued_paths(self):
        for endpoint in ["/api/doc/diff", "/api/doc/log"]:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint, params={"path": "secret.txt"}).status_code, 404)

    def test_desk_never_commits(self):
        read = self.doc("CLAUDE.md")
        self.client.put("/api/doc", json={"path": "CLAUDE.md", "text": "# edit\n", "hash": read["hash"]})
        self.assertEqual(git(self.repo, "rev-list", "--count", "HEAD").strip(), "1")


class MetaTest(DeskTestCase):
    def test_meta_names_the_checkout_and_the_data_roots(self):
        r = self.client.get("/api/meta")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"repo": str(self.repo.resolve()), "branch": "main",
                                    "footage_root": str(self.footage), "db_path": str(self.db)})

    def test_desk_does_not_create_the_db(self):
        self.client.get("/api/meta")
        self.client.get("/api/catalog")
        self.assertFalse(self.db.exists())


class FrontendTest(DeskTestCase):
    def test_without_a_build_the_root_tells_how_to_build_the_frontend(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("npm --prefix web run build", r.text)

    def test_built_frontend_is_served_with_index_fallback(self):
        (self.dist / "assets").mkdir(parents=True)
        (self.dist / "index.html").write_text("<!doctype html><title>Desk</title>")
        (self.dist / "assets" / "app.js").write_text("console.log(1)")
        self.assertIn("<title>Desk</title>", self.client.get("/").text)
        self.assertEqual(self.client.get("/assets/app.js").text, "console.log(1)")
        self.assertIn("<title>Desk</title>", self.client.get("/doc/CLAUDE.md").text)
        self.assertEqual(self.client.get("/api/nothing").status_code, 404)

    def test_built_frontend_does_not_serve_files_outside_dist(self):
        self.dist.mkdir()
        (self.dist / "index.html").write_text("<!doctype html><title>Desk</title>")
        r = self.client.get("/..%2Fstyle.json")
        self.assertNotIn("schema", r.text)


class TokenTest(DeskTestCase):
    token = "s3cret"

    def test_requests_without_the_token_are_401(self):
        for path in ["/api/catalog", "/api/meta", "/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get("/api/meta", headers={"Authorization": "Bearer wrong"}).status_code, 401)

    def test_bearer_header_is_accepted(self):
        r = self.client.get("/api/meta", headers={"Authorization": "Bearer s3cret"})
        self.assertEqual(r.status_code, 200)

    def test_token_in_the_url_sets_a_cookie_for_the_browser(self):
        self.assertEqual(self.client.get("/", params={"token": "s3cret"}).status_code, 200)
        self.assertEqual(self.client.get("/api/catalog").status_code, 200)


if __name__ == "__main__":
    unittest.main()
