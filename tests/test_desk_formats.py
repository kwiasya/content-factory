"""Desk Format shelf and skill lint through the FastAPI TestClient on a temporary repo and footage root."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from cf.desk.app import create_app

RULES_07 = """# Rules 07

|id|rule|applies to|tag|source|confidence|
|---|---|---|---|---|---|
|R07-01|Confirm the promise in the first 5 s.|long|PRACTITIONER|[h1](https://example.com/a)|high|
|R07-02|Cut self-intros.|both|DATA|[h2](https://example.com/b)|medium|
"""

RULES_09 = """# Rules 09

| Metric | Meaning |
|---|---|
| Hold | not a rule |

| id | rule | tag | source | confidence |
|---|---|---|---|---|
| R09-01 | Write the viewer contract. | PRACTITIONER | [P](https://example.com/c) | high |
"""

TREE = {
    "formats/walk-reel/FORMAT.md": "# Format: Walk Reel\n\n- id: `walk-reel`\n"
                                   "- Research rules that apply: 07 (retention, the first 30 s), 09\n",
    "formats/walk-reel/hook-library.md": "# Hooks\n\n- one\n",
    "formats/tech-explainer/FORMAT.md": "# Format: Tech explainer\n\n"
                                        "- Research rules that apply: 09 (structure), 42\n",
    "docs/research/07-retention-long-form/rules.md": RULES_07,
    "docs/research/09-storytelling-structures/rules.md": RULES_09,
    "docs/script-schema.md": "# Schema\n",
    "style.json": "{}\n",
    ".claude/skills/alpha/SKILL.md": "# Alpha\n\nRead `docs/script-schema.md` and `docs/gone.md`, then run "
                                     "/beta and /ghost. Ignore `~/Movies/x/y.json`, `videos/<slug>/script.md`, "
                                     "https://example.com/a/b and `cuts.json`.\n",
    ".claude/skills/alpha/templates/t.md": "See `style.json` and `formats/nope/FORMAT.md`.\n",
    ".claude/skills/beta/SKILL.md": "# Beta\n\nUses `templates/x.md` and `docs/script-schema.md`.\n",
    ".claude/skills/beta/templates/x.md": "x\n",
    ".claude/skills/remotion-foo/SKILL.md": "# Vendored\n\n`docs/missing.md`\n",
}


def video(slug: str, fmt: str, status: str = "script") -> dict:
    return {"schema": "cf-video/1", "slug": slug, "title_working": f"Title {slug}", "format": fmt,
            "channel": "tech-en", "status": status}


class FormatsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        for rel, text in TREE.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.footage = base / "footage"
        self.footage.mkdir()
        env = mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(self.footage)})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(create_app(self.repo, footage_root=self.footage,
                                            db_path=self.footage / "factory.db", web_dist=base / "dist"))

    def get(self, url: str) -> dict:
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def write_video(self, slug: str, data) -> None:
        folder = self.footage / "videos" / slug
        folder.mkdir(parents=True)
        text = data if isinstance(data, str) else json.dumps(data)
        (folder / "video.json").write_text(text)


class FormatListTest(FormatsTestCase):
    def test_lists_every_format_folder_with_its_title(self):
        formats = self.get("/api/formats")["formats"]
        self.assertEqual([f["id"] for f in formats], ["tech-explainer", "walk-reel"])
        walk = formats[1]
        self.assertEqual(walk["title"], "Walk Reel")
        self.assertEqual(walk["path"], "formats/walk-reel/FORMAT.md")
        self.assertTrue(walk["has_hook_library"])
        self.assertFalse(formats[0]["has_hook_library"])


class FormatPageTest(FormatsTestCase):
    def test_format_carries_its_text_and_hook_library(self):
        fmt = self.get("/api/formats/walk-reel")
        self.assertEqual(fmt["id"], "walk-reel")
        self.assertEqual(fmt["title"], "Walk Reel")
        self.assertEqual(fmt["format"]["path"], "formats/walk-reel/FORMAT.md")
        self.assertIn("Research rules that apply", fmt["format"]["text"])
        self.assertEqual(fmt["hook_library"], {"path": "formats/walk-reel/hook-library.md",
                                               "text": "# Hooks\n\n- one\n"})

    def test_hook_library_is_null_until_exported(self):
        self.assertIsNone(self.get("/api/formats/tech-explainer")["hook_library"])

    def test_unknown_or_malformed_format_is_404(self):
        for fid in ("nope", "Walk-Reel", "%2e%2e", "walk-reel%2F..%2F..%2Fdocs"):
            self.assertEqual(self.client.get(f"/api/formats/{fid}").status_code, 404, fid)


class FormatRulesTest(FormatsTestCase):
    def test_topics_named_in_format_md_map_to_their_rules_files(self):
        topics = self.get("/api/formats/walk-reel")["topics"]
        self.assertEqual(topics, [
            {"topic": "07", "path": "docs/research/07-retention-long-form/rules.md"},
            {"topic": "09", "path": "docs/research/09-storytelling-structures/rules.md"},
        ])

    def test_a_topic_without_a_rules_file_is_listed_with_no_path(self):
        topics = self.get("/api/formats/tech-explainer")["topics"]
        self.assertEqual(topics[1], {"topic": "42", "path": None})

    def test_rule_rows_are_parsed_by_header_with_either_spacing(self):
        rules = self.get("/api/formats/walk-reel")["rules"]
        self.assertEqual([r["id"] for r in rules], ["R07-01", "R07-02", "R09-01"])
        self.assertEqual(rules[0], {
            "topic": "07", "id": "R07-01", "rule": "Confirm the promise in the first 5 s.", "scope": "long",
            "tag": "PRACTITIONER", "source": "[h1](https://example.com/a)", "confidence": "high"})
        self.assertEqual(rules[2], {
            "topic": "09", "id": "R09-01", "rule": "Write the viewer contract.", "scope": "",
            "tag": "PRACTITIONER", "source": "[P](https://example.com/c)", "confidence": "high"})


class FormatVideosTest(FormatsTestCase):
    def test_videos_of_the_format_come_from_video_json_under_the_footage_root(self):
        self.write_video("b-long", video("b-long", "tech-explainer", "brief"))
        self.write_video("a-long", video("a-long", "tech-explainer"))
        self.write_video("reel-1", video("reel-1", "walk-reel"))
        videos = self.get("/api/formats/tech-explainer")["videos"]
        self.assertEqual(videos, [
            {"slug": "a-long", "title": "Title a-long", "status": "script", "channel": "tech-en",
             "path": str(self.footage / "videos" / "a-long")},
            {"slug": "b-long", "title": "Title b-long", "status": "brief", "channel": "tech-en",
             "path": str(self.footage / "videos" / "b-long")},
        ])

    def test_no_videos_folder_and_broken_video_json_are_not_errors(self):
        self.assertEqual(self.get("/api/formats/walk-reel")["videos"], [])
        self.write_video("broken", "{not json")
        self.write_video("listy", "[1, 2]")
        self.write_video("ok", video("ok", "walk-reel"))
        self.assertEqual([v["slug"] for v in self.get("/api/formats/walk-reel")["videos"]], ["ok"])


class SkillLintTest(FormatsTestCase):
    def refs(self, items: list[dict]) -> list[str]:
        return [i["ref"] for i in items]

    def test_missing_repo_paths_are_reported_with_file_and_line(self):
        lint = self.get("/api/skills/alpha/lint")
        self.assertEqual(lint["missing_paths"], [
            {"ref": "docs/gone.md", "file": ".claude/skills/alpha/SKILL.md", "line": 3},
            {"ref": "formats/nope/FORMAT.md", "file": ".claude/skills/alpha/templates/t.md", "line": 1},
        ])

    def test_slash_mentions_of_skills_that_are_not_folders_are_reported(self):
        lint = self.get("/api/skills/alpha/lint")
        self.assertEqual(lint["missing_skills"], [
            {"ref": "/ghost", "file": ".claude/skills/alpha/SKILL.md", "line": 3}])

    def test_paths_relative_to_the_skill_folder_and_clean_skills_pass(self):
        self.assertEqual(self.get("/api/skills/beta/lint"), {
            "name": "beta", "missing_paths": [], "missing_skills": []})

    def test_vendored_unknown_and_malformed_skills_are_404(self):
        for name in ("remotion-foo", "nope", "Alpha"):
            self.assertEqual(self.client.get(f"/api/skills/{name}/lint").status_code, 404, name)

    def test_summary_counts_broken_references_per_own_skill(self):
        self.assertEqual(self.get("/api/skills/lint"), {"skills": {"alpha": 3, "beta": 0}})


if __name__ == "__main__":
    unittest.main()
