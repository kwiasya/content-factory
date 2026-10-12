"""Desk Videos API and media streaming through the FastAPI TestClient on a temporary footage root."""

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from cf.desk.app import create_app

ROOT = Path(__file__).resolve().parents[1]

VIDEO = {
    "schema": "cf-video/1",
    "slug": "long-one",
    "title_working": "The long one",
    "format": "tech-explainer",
    "channel": "tech-en",
    "language": "en",
    "walks": ["w1"],
    "status": "script",
    "history": [{"status": "brief", "at": "2026-10-01", "note": "first"},
                {"status": "script", "at": "2026-10-02", "note": "draft"}],
    "references": [],
    "ideas": [],
    "published_url": None,
}

SRT = "1\n00:00:00,000 --> 00:00:02,000\nHello\n"
MP4 = bytes(range(256)) * 4
OLD = 1_700_000_000

MANIFEST = {
    "walk": "w1",
    "clips": [
        {"file": "A.MOV", "fps": 60.0, "duration_s": 13.0},
        {"file": "B.MOV", "fps": 24.0, "duration_s": 29.0},
        {"file": "C.mov", "fps": 30.0, "duration_s": 33.0},
    ],
}


def good_script() -> dict:
    return {
        "schema": "cf-script/1",
        "walk": "w1",
        "concept": "A slow afternoon by the lake.",
        "format": "pov",
        "target_length_s": 9,
        "hook": {"type": "visual_payoff", "text": "This lake hides a whole palace", "clip": "A.MOV"},
        "shots": [
            {"clip": "A.MOV", "in_s": 1.0, "out_s": 4.0, "role": "hook", "overlay": None, "transition": "cut"},
            {"clip": "B.MOV", "in_s": 2.0, "out_s": 5.0, "role": "build",
             "overlay": {"text": "Sanssouci, Potsdam", "type": "place"}, "transition": "dissolve"},
            {"clip": "C.mov", "in_s": 0.0, "out_s": 3.0, "role": "payoff", "transition": "cut"},
        ],
        "ending": "reveal_last",
        "cta": "Send this to your travel buddy",
        "caption": "Potsdam in October\nQuiet paths.\nSend this to your travel buddy",
        "hashtags": ["#potsdam", "#citybreak"],
        "location_tag": "Potsdam, Germany",
        "alt_text": "A lake and a palace.",
        "track": None,
        "metrics": None,
    }


def write(path: Path, data: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data)
    return path


class VideosTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        shutil.copy(ROOT / "style.json", self.repo / "style.json")
        self.footage = base / "footage"
        self.video = self.footage / "videos" / "long-one"
        write(self.video / "video.json", json.dumps(VIDEO, indent=2))
        write(self.video / "script.md", "# Script\n\nHook line.\n")
        write(self.video / "references.md", "# References\n")
        write(self.video / "subtitles" / "en.srt", SRT)
        write(self.video / "renders" / "v1.mp4", MP4)
        write(self.video / "overlays" / "o1.mov", MP4)
        for p in self.video.rglob("*"):
            os.utime(p, (OLD, OLD))
        self.walk = self.footage / "w1"
        write(self.walk / "clip_manifest.json", json.dumps(MANIFEST))
        write(self.walk / "raw" / "x.mp4", MP4)
        write(self.walk / "proxy" / "A.mp4", MP4)
        self.reel = self.walk / "reels" / "short-01"
        write(self.reel / "script.draft.json", json.dumps(good_script(), indent=2))
        env = mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(self.footage)})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(create_app(self.repo, footage_root=self.footage,
                                            db_path=self.footage / "factory.db", web_dist=base / "dist"))

    def ok(self, response) -> dict:
        self.assertLess(response.status_code, 300, response.text)
        return response.json()


class ListTest(VideosTestCase):
    def test_list_merges_videos_and_legacy_reels_newest_first(self):
        videos = self.ok(self.client.get("/api/videos"))["videos"]
        self.assertEqual([v["slug"] for v in videos], ["w1~short-01", "long-one"])
        legacy, long_one = videos
        self.assertEqual((long_one["title"], long_one["format"], long_one["channel"], long_one["status"],
                          long_one["legacy"]), ("The long one", "tech-explainer", "tech-en", "script", False))
        self.assertEqual((legacy["format"], legacy["status"], legacy["legacy"]), ("walk-reel", "script", True))
        self.assertTrue(long_one["updated"].startswith("2023-11-14"))

    def test_legacy_status_follows_what_the_reel_folder_holds(self):
        def status() -> str:
            return self.ok(self.client.get("/api/videos/w1~short-01"))["video"]["status"]

        self.assertEqual(status(), "script")
        write(self.reel / "cuts.json", "{}")
        self.assertEqual(status(), "edit")
        write(self.reel / "out" / "short-01.mp4", MP4)
        self.assertEqual(status(), "review")

    def test_unreadable_video_json_stays_in_the_list_with_an_error(self):
        write(self.footage / "videos" / "broken" / "video.json", "{oops")
        videos = {v["slug"]: v for v in self.ok(self.client.get("/api/videos"))["videos"]}
        self.assertIn("video.json", videos["broken"]["error"])
        self.assertIsNone(videos["broken"]["status"])
        self.assertEqual(self.client.get("/api/videos/broken").status_code, 422)

    def test_unknown_video_is_404(self):
        self.assertEqual(self.client.get("/api/videos/nope").status_code, 404)
        self.assertEqual(self.client.get("/api/videos/videos~x").status_code, 404)


class MediaTest(VideosTestCase):
    def media(self, path: str, **headers):
        return self.client.get("/api/media", params={"path": path}, headers=headers)

    def test_range_request_returns_206_with_the_slice(self):
        r = self.media("videos/long-one/renders/v1.mp4", range="bytes=10-19")
        self.assertEqual(r.status_code, 206)
        self.assertEqual(r.content, MP4[10:20])
        self.assertEqual(r.headers["content-range"], f"bytes 10-19/{len(MP4)}")

    def test_allowlisted_files_stream_whole(self):
        write(self.footage / "references" / "wl" / "abc" / "proxy.mp4", MP4)
        write(self.reel / "out" / "short-01.mp4", MP4)
        for path in ("videos/long-one/overlays/o1.mov", "w1/proxy/A.mp4", "references/wl/abc/proxy.mp4",
                     "w1/reels/short-01/out/short-01.mp4"):
            with self.subTest(path):
                r = self.media(path)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.content, MP4)
                self.assertEqual(r.headers["accept-ranges"], "bytes")

    def test_raw_and_everything_outside_the_allowlist_is_404(self):
        write(self.footage / "references" / "wl" / "abc" / "abc.mp4", MP4)
        (self.video / "renders" / "link.mp4").symlink_to(self.walk / "raw" / "x.mp4")
        for path in ("w1/raw/x.mp4", "w1/clip_manifest.json", "videos/long-one/video.json",
                     "videos/long-one/script.md", "videos/long-one/renders", "videos/long-one/renders/",
                     "videos/long-one/renders/../../../w1/raw/x.mp4", "/etc/hosts", "",
                     "references/wl/abc/abc.mp4", "videos/long-one/renders/link.mp4", "w1/proxy/missing.mp4"):
            with self.subTest(path):
                self.assertEqual(self.media(path).status_code, 404)


class DetailTest(VideosTestCase):
    def test_video_detail_has_video_json_hash_and_file_tree_with_kinds(self):
        detail = self.ok(self.client.get("/api/videos/long-one"))
        self.assertEqual(detail["video"]["history"], VIDEO["history"])
        self.assertTrue(detail["hash"].startswith("sha256:"))
        files = {f["path"]: f for f in detail["files"]}
        self.assertEqual({p: f["kind"] for p, f in files.items()}, {
            "video.json": "video", "script.md": "script", "references.md": "references",
            "subtitles/en.srt": "subtitle", "renders/v1.mp4": "render", "overlays/o1.mov": "overlay"})
        self.assertEqual(files["renders/v1.mp4"]["media"], "videos/long-one/renders/v1.mp4")
        self.assertIsNone(files["script.md"]["media"])
        self.assertEqual(files["renders/v1.mp4"]["size"], len(MP4))
        self.assertTrue(files["script.md"]["editable"])
        self.assertFalse(files["video.json"]["editable"])
        self.assertEqual([p["media"] for p in detail["proxies"]], ["w1/proxy/A.mp4"])

    def test_legacy_detail_lists_reel_files_and_walk_proxies_without_raw(self):
        write(self.reel / "out" / "short-01.mp4", MP4)
        write(self.reel / "overlays" / "s01.mov", MP4)
        detail = self.ok(self.client.get("/api/videos/w1~short-01"))
        self.assertTrue(detail["video"]["legacy"])
        self.assertIsNone(detail["hash"])
        kinds = {f["path"]: f["kind"] for f in detail["files"]}
        self.assertEqual(kinds, {"script.draft.json": "script", "out/short-01.mp4": "render",
                                 "overlays/s01.mov": "overlay"})
        media = [f["media"] for f in detail["files"]] + [p["media"] for p in detail["proxies"]]
        self.assertNotIn("w1/raw/x.mp4", media)
        self.assertIn("w1/reels/short-01/out/short-01.mp4", media)
        self.assertEqual([p["media"] for p in detail["proxies"]], ["w1/proxy/A.mp4"])


class StatusTest(VideosTestCase):
    def post(self, **body):
        return self.client.post("/api/videos/long-one/status", json=body)

    def current_hash(self) -> str:
        return self.ok(self.client.get("/api/videos/long-one"))["hash"]

    def test_status_change_appends_history_with_todays_utc_date_and_rewrites_video_json(self):
        today = datetime.now(timezone.utc).date().isoformat()
        detail = self.ok(self.post(status="recording", note="camera day", hash=self.current_hash()))
        on_disk = json.loads((self.video / "video.json").read_text())
        self.assertEqual(on_disk["status"], "recording")
        self.assertEqual(on_disk["history"], VIDEO["history"] + [
            {"status": "recording", "at": today, "note": "camera day"}])
        self.assertEqual({k: on_disk[k] for k in VIDEO if k not in ("status", "history")},
                         {k: VIDEO[k] for k in VIDEO if k not in ("status", "history")})
        self.assertEqual(detail["video"]["status"], "recording")
        self.assertNotEqual(detail["hash"], None)

    def test_unknown_status_is_422_and_stale_hash_is_409_and_nothing_is_written(self):
        before = (self.video / "video.json").read_bytes()
        self.assertEqual(self.post(status="done", hash=self.current_hash()).status_code, 422)
        self.assertEqual(self.post(status="edit", hash="sha256:stale").status_code, 409)
        self.assertEqual((self.video / "video.json").read_bytes(), before)

    def test_legacy_reel_status_cannot_be_set(self):
        r = self.client.post("/api/videos/w1~short-01/status", json={"status": "edit", "hash": ""})
        self.assertEqual(r.status_code, 409)


class TextFileTest(VideosTestCase):
    def read(self, slug: str, path: str):
        return self.client.get(f"/api/videos/{slug}/file", params={"path": path})

    def save(self, slug: str, path: str, text: str, hash: str):
        return self.client.put(f"/api/videos/{slug}/file", json={"path": path, "text": text, "hash": hash})

    def test_script_markdown_reads_and_writes_through_the_hash(self):
        doc = self.ok(self.read("long-one", "script.md"))
        self.assertEqual((doc["kind"], doc["format"], doc["text"]), ("script", "markdown", "# Script\n\nHook line.\n"))
        saved = self.ok(self.save("long-one", "script.md", "# Script v2\n", doc["hash"]))
        self.assertEqual((self.video / "script.md").read_text(), "# Script v2\n")
        stale = self.save("long-one", "script.md", "# lost\n", doc["hash"])
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["hash"], saved["hash"])
        self.assertEqual((self.video / "script.md").read_text(), "# Script v2\n")

    def test_subtitle_is_text_and_writable(self):
        doc = self.ok(self.read("long-one", "subtitles/en.srt"))
        self.assertEqual((doc["kind"], doc["format"], doc["text"]), ("subtitle", "text", SRT))
        self.ok(self.save("long-one", "subtitles/en.srt", SRT.replace("Hello", "Hi"), doc["hash"]))
        self.assertIn("Hi", (self.video / "subtitles" / "en.srt").read_text())

    def test_invalid_cf_script_returns_violations_and_leaves_the_file(self):
        path = self.reel / "script.draft.json"
        before = path.read_bytes()
        doc = self.ok(self.read("w1~short-01", "script.draft.json"))
        self.assertEqual(doc["format"], "json")
        bad = json.loads(doc["text"])
        bad["hook"]["clip"] = "NOPE.MOV"
        bad["hashtags"] = ["#a", "#b", "#c", "#d", "#e", "#f"]
        r = self.save("w1~short-01", "script.draft.json", json.dumps(bad), doc["hash"])
        self.assertEqual(r.status_code, 422)
        violations = r.json()["violations"]
        self.assertTrue(any("NOPE.MOV" in v for v in violations), violations)
        self.assertTrue(any("hashtag" in v for v in violations), violations)
        self.assertEqual(path.read_bytes(), before)
        broken = self.save("w1~short-01", "script.draft.json", "{not json", doc["hash"])
        self.assertEqual(broken.status_code, 422)
        self.assertEqual(path.read_bytes(), before)

    def test_valid_cf_script_is_written(self):
        doc = self.ok(self.read("w1~short-01", "script.draft.json"))
        script = json.loads(doc["text"])
        script["concept"] = "A quieter afternoon by the lake."
        self.ok(self.save("w1~short-01", "script.draft.json", json.dumps(script, indent=2), doc["hash"]))
        self.assertEqual(json.loads((self.reel / "script.draft.json").read_text())["concept"],
                         "A quieter afternoon by the lake.")

    def test_a_script_json_that_is_not_cf_script_1_is_a_violation(self):
        path = self.reel / "script.draft.json"
        before = path.read_bytes()
        doc = self.ok(self.read("w1~short-01", "script.draft.json"))
        for schema in ("cf-script/0", None):
            with self.subTest(schema=schema):
                script = json.loads(doc["text"])
                if schema is None:
                    del script["schema"]
                else:
                    script["schema"] = schema
                r = self.save("w1~short-01", "script.draft.json", json.dumps(script), doc["hash"])
                self.assertEqual(r.status_code, 422, r.text)
                self.assertTrue(any("cf-script/1" in v for v in r.json()["violations"]), r.text)
                self.assertEqual(path.read_bytes(), before)

    def test_a_stale_hash_is_409_before_the_json_is_checked(self):
        doc = self.ok(self.read("w1~short-01", "script.draft.json"))
        self.ok(self.save("w1~short-01", "script.draft.json", doc["text"], doc["hash"]))
        (self.reel / "script.draft.json").write_text(doc["text"] + "\n")
        r = self.save("w1~short-01", "script.draft.json", "{not json", doc["hash"])
        self.assertEqual(r.status_code, 409, r.text)

    def test_cf_script_of_a_walk_without_manifest_is_still_validated(self):
        (self.walk / "clip_manifest.json").unlink()
        (self.repo / "style.json").unlink()
        doc = self.ok(self.read("w1~short-01", "script.draft.json"))
        bad = json.loads(doc["text"])
        bad["target_length_s"] = 555
        r = self.save("w1~short-01", "script.draft.json", json.dumps(bad), doc["hash"])
        self.assertEqual(r.status_code, 422, r.text)
        self.assertTrue(r.json()["violations"])

    def test_brief_and_notes_can_be_created_other_missing_files_cannot(self):
        self.assertEqual(self.read("long-one", "brief.md").status_code, 404)
        self.ok(self.save("long-one", "brief.md", "# Brief\n", ""))
        self.assertEqual((self.video / "brief.md").read_text(), "# Brief\n")
        self.assertEqual(self.save("long-one", "brief.md", "# again\n", "").status_code, 409)
        self.assertEqual(self.save("long-one", "other.md", "x", "").status_code, 404)
        self.assertEqual(self.save("long-one", "subtitles/new.srt", "x", "").status_code, 404)

    def test_voiceover_text_can_be_created_edited_and_is_listed(self):
        self.assertEqual(self.read("long-one", "voiceover.md").status_code, 404)
        self.ok(self.save("long-one", "voiceover.md", "This is the report.\n", ""))
        self.assertEqual((self.video / "voiceover.md").read_text(), "This is the report.\n")
        doc = self.read("long-one", "voiceover.md").json()
        self.assertEqual(doc["kind"], "voiceover")
        self.ok(self.save("long-one", "voiceover.md", "Take two.\n", doc["hash"]))
        files = {f["path"]: f for f in self.client.get("/api/videos/long-one").json()["files"]}
        self.assertEqual(files["voiceover.md"]["kind"], "voiceover")
        self.assertTrue(files["voiceover.md"]["editable"])

    def test_only_editable_texts_inside_the_folder_are_served(self):
        for path in ("video.json", "renders/v1.mp4", "../../w1/clip_manifest.json", "/etc/hosts",
                     "subtitles/../video.json", "missing.md"):
            with self.subTest(path):
                self.assertEqual(self.read("long-one", path).status_code, 404)
                self.assertEqual(self.save("long-one", path, "x", "").status_code, 404)
