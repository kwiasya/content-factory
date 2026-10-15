"""Desk Videos API and media streaming through the FastAPI TestClient on a temporary root."""

import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from cf.desk.app import create_app
from cf.research import brief, ideas
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import CHANNEL_A, V1, V2, add_member, add_videos, ago, fields, video_item

ROOT = Path(__file__).resolve().parents[1]

VIDEO = {
    "schema": "cf-video/1",
    "slug": "long-one",
    "title_working": "The long one",
    "format": "tech-explainer",
    "channel": "tech-en",
    "language": "en",
    "footage": ["w1"],
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
    "footage": "w1",
    "clips": [
        {"file": "A.MOV", "fps": 60.0, "duration_s": 13.0},
        {"file": "B.MOV", "fps": 24.0, "duration_s": 29.0},
        {"file": "C.mov", "fps": 30.0, "duration_s": 33.0},
    ],
}


def good_script() -> dict:
    return {
        "schema": "cf-script/1",
        "footage": "w1",
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
        self.footage_dir = self.footage / "w1"
        write(self.footage_dir / "clip_manifest.json", json.dumps(MANIFEST))
        write(self.footage_dir / "raw" / "x.mp4", MP4)
        write(self.footage_dir / "proxy" / "A.mp4", MP4)
        self.reel = self.footage_dir / "reels" / "short-01"
        write(self.reel / "script.draft.json", json.dumps(good_script(), indent=2))
        env = mock.patch.dict(os.environ, {"CF_LOCAL_ROOT": str(self.footage), "CF_SHARED_ROOT": str(self.footage)})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(create_app(self.repo, local_root=self.footage,
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
        self.assertEqual(videos["broken"]["error_code"], "video_json_unreadable")
        self.assertIsNone(videos["broken"]["status"])
        r = self.client.get("/api/videos/broken")
        self.assertEqual((r.status_code, r.json()["code"]), (422, "video_json_unreadable"))
        write(self.footage / "videos" / "broken" / "video.json", "[]")
        r = self.client.get("/api/videos/broken")
        self.assertEqual((r.status_code, r.json()["code"]), (422, "video_json_not_object"))

    def test_unknown_video_is_404(self):
        r = self.client.get("/api/videos/nope")
        self.assertEqual((r.status_code, r.json()["code"], r.json()["params"]),
                         (404, "video_not_found", {"slug": "nope"}))
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
        (self.video / "renders" / "link.mp4").symlink_to(self.footage_dir / "raw" / "x.mp4")
        for path in ("w1/raw/x.mp4", "w1/clip_manifest.json", "videos/long-one/video.json",
                     "videos/long-one/script.md", "videos/long-one/renders", "videos/long-one/renders/",
                     "videos/long-one/renders/../../../w1/raw/x.mp4", "/etc/hosts", "",
                     "references/wl/abc/abc.mp4", "videos/long-one/renders/link.mp4", "w1/proxy/missing.mp4"):
            with self.subTest(path):
                r = self.media(path)
                self.assertEqual((r.status_code, r.json()["code"]), (404, "media_not_found"))


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

    def test_legacy_detail_lists_reel_files_and_footage_proxies_without_raw(self):
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


class LegacyKeysTest(VideosTestCase):
    def write_legacy(self, slug: str = "legacy") -> Path:
        video = {k: ("walks" if k == "footage" else k, v) for k, v in VIDEO.items()}
        folder = self.footage / "videos" / slug
        write(folder / "video.json", json.dumps({**dict(video.values()), "slug": slug}, indent=2))
        return folder

    def test_detail_of_a_video_json_with_footage_names_it_and_its_proxies(self):
        detail = self.ok(self.client.get("/api/videos/long-one"))
        self.assertEqual(detail["video"]["footage"], ["w1"])
        self.assertNotIn("walks", detail["video"])
        self.assertEqual([(p["footage"], p["name"]) for p in detail["proxies"]], [("w1", "A.mp4")])
        self.assertNotIn('"walk', json.dumps(detail))

    def test_a_legacy_walks_key_reads_as_footage_and_its_proxies_are_found(self):
        self.write_legacy()
        detail = self.ok(self.client.get("/api/videos/legacy"))
        self.assertEqual(detail["video"]["footage"], ["w1"])
        self.assertNotIn("walks", detail["video"])
        self.assertEqual(list(detail["video"])[:7], ["schema", "slug", "title_working", "format", "channel",
                                                     "language", "footage"])
        self.assertEqual([p["media"] for p in detail["proxies"]], ["w1/proxy/A.mp4"])

    def test_a_legacy_reel_links_its_own_footage(self):
        detail = self.ok(self.client.get("/api/videos/w1~short-01"))
        self.assertEqual(detail["video"]["footage"], ["w1"])
        self.assertNotIn("walks", detail["video"])

    def test_a_status_change_rewrites_the_legacy_key(self):
        folder = self.write_legacy()
        digest = self.ok(self.client.get("/api/videos/legacy"))["hash"]
        self.ok(self.client.post("/api/videos/legacy/status", json={"status": "brief", "hash": digest}))
        on_disk = json.loads((folder / "video.json").read_text())
        self.assertEqual(on_disk["footage"], ["w1"])
        self.assertNotIn("walks", on_disk)
        self.assertEqual(list(on_disk).index("footage"), list(VIDEO).index("footage"))

    def test_a_script_with_legacy_walk_still_validates_against_its_manifest(self):
        doc = self.ok(self.client.get("/api/videos/w1~short-01/file", params={"path": "script.draft.json"}))
        script = json.loads(doc["text"])
        script["walk"] = script.pop("footage")
        script["hook"]["clip"] = "NOPE.MOV"
        r = self.client.put("/api/videos/w1~short-01/file",
                            json={"path": "script.draft.json", "text": json.dumps(script), "hash": doc["hash"]})
        self.assertEqual(r.status_code, 422, r.text)
        self.assertTrue(any("NOPE.MOV" in v for v in r.json()["violations"]), r.text)

    def test_media_under_a_footage_proxy_is_served_and_root_folders_are_not_footage(self):
        self.assertEqual(self.client.get("/api/media", params={"path": "w1/proxy/A.mp4"}).status_code, 200)
        for name in ("videos", "references", "channels", "library", "packs"):
            with self.subTest(name):
                write(self.footage / name / "proxy" / "A.mp4", MP4)
                r = self.client.get("/api/media", params={"path": f"{name}/proxy/A.mp4"})
                self.assertEqual(r.status_code, 404)


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
        unknown = self.post(status="done", hash=self.current_hash())
        self.assertEqual((unknown.status_code, unknown.json()["code"]), (422, "status_invalid"))
        self.assertEqual(unknown.json()["params"], {"status": "done", "statuses": [
            "idea", "brief", "script", "recording", "edit", "review", "published"]})
        stale = self.post(status="edit", hash="sha256:stale")
        self.assertEqual((stale.status_code, stale.json()["code"]), (409, "file_changed"))
        self.assertEqual((self.video / "video.json").read_bytes(), before)

    def test_legacy_reel_status_cannot_be_set(self):
        r = self.client.post("/api/videos/w1~short-01/status", json={"status": "edit", "hash": ""})
        self.assertEqual((r.status_code, r.json()["code"]), (409, "legacy_status"))


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
        self.assertEqual((r.status_code, r.json()["code"]), (422, "script_invalid"))
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

    def test_cf_script_of_a_footage_without_manifest_is_still_validated(self):
        (self.footage_dir / "clip_manifest.json").unlink()
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
        other = self.save("long-one", "other.md", "x", "")
        self.assertEqual((other.status_code, other.json()["code"]), (404, "video_text_not_found"))
        self.assertEqual(other.json()["params"], {"path": "other.md"})
        self.assertEqual(self.save("long-one", "subtitles/new.srt", "x", "").status_code, 404)

    def test_saving_a_read_file_that_was_deleted_since_is_409(self):
        self.ok(self.save("long-one", "notes.md", "x\n", ""))
        read = self.ok(self.read("long-one", "notes.md"))
        (self.video / "notes.md").unlink()
        r = self.save("long-one", "notes.md", "y\n", read["hash"])
        self.assertEqual((r.status_code, r.json()["code"]), (409, "file_deleted"))
        self.assertFalse((self.video / "notes.md").exists())

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


NAME_RE = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
FORMAT_MD = {"tech-explainer": "# Format: Tech explainer\n", "walk-reel": "# Format: Walk Reel\n"}


class ScriptCuesTest(VideosTestCase):
    """A Library in the Desk's factory.db; a Video folder with a script.json and notes.md."""

    def setUp(self):
        super().setUp()
        from library_fixture import make_library

        make_library(Path(self.tmp.name), root=self.footage, db=self.footage / "factory.db")
        write(self.video / "script.json", json.dumps(good_script(), indent=2))
        write(self.video / "notes.md", "After the reveal: @meme/chipi\n")

    def save_cues(self, cues):
        doc = self.ok(self.client.get("/api/videos/long-one/file", params={"path": "script.json"}))
        script = json.loads(doc["text"])
        script["shots"][1]["assets"] = cues
        return self.client.put("/api/videos/long-one/file",
                               json={"path": "script.json", "text": json.dumps(script), "hash": doc["hash"]})

    def test_desk_put_script_with_a_broken_ref_is_422_with_nearest(self):
        r = self.save_cues([{"ref": "@meme/chipy", "at_s": 0.0}])
        self.assertEqual((r.status_code, r.json()["code"]), (422, "script_invalid"), r.text)
        self.assertTrue(any("nearest: @meme/chipi" in v for v in r.json()["violations"]), r.text)
        self.assertNotIn("assets", json.loads((self.video / "script.json").read_text())["shots"][1])

    def test_desk_put_script_with_a_valid_cue_saves(self):
        self.ok(self.save_cues([{"ref": "@meme/chipi", "at_s": 0.0, "dur_s": 2.0}]))
        self.assertEqual(json.loads((self.video / "script.json").read_text())["shots"][1]["assets"][0]["ref"],
                         "@meme/chipi")
        (self.video / "notes.md").write_text("nothing\n")
        r = self.save_cues([{"ref": "@meme/chipi", "at_s": 0.5, "dur_s": 2.0}])
        self.assertEqual(r.status_code, 422, r.text)
        self.assertTrue(any("unknown rights" in v for v in r.json()["violations"]), r.text)

    def test_without_the_store_cues_need_the_library_and_a_script_without_cues_saves(self):
        (self.footage / "factory.db").rename(self.footage / "moved.db")
        r = self.save_cues([{"ref": "@sfx/own-hit", "at_s": 0.0}])
        self.assertEqual(r.status_code, 422, r.text)
        self.assertTrue(any("need the Library" in v and "/index-pack" in v for v in r.json()["violations"]), r.text)
        self.assertFalse(any("--shared-root" in v for v in r.json()["violations"]), r.text)
        self.ok(self.save_cues(None))


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class CreateTest(VideosTestCase):
    """A seeded factory.db: Watchlist `tools` (tech-explainer, Channel tech-en, language ru) with an Idea that
    has a Brief and one that does not; both Formats as FORMAT.md files."""

    def setUp(self):
        super().setUp()
        for fid, text in FORMAT_MD.items():
            write(self.repo / "formats" / fid / "FORMAT.md", text)
        self.db = self.footage / "factory.db"
        with st.open_store(self.db, create=True) as s:
            wl.create(s, "tools", format_id="tech-explainer", author_channel="tech-en", language="ru")
            add_member(s, "tools", CHANNEL_A, "@alpha")
            add_videos(s, [video_item(V1, CHANNEL_A, ago(2), 40, 9000, title="Alfama at dusk"),
                           video_item(V2, CHANNEL_A, ago(3), 40, 5000, title="Porto stairs")])
            self.briefed = ideas.add(s, "tools", [V1], fields(title="A tool tour")).id
            ideas.shortlist(s, self.briefed)
            self.brief_path = brief.create(s, self.briefed, root=self.footage)
            self.inbox = ideas.add(s, "tools", [V2], fields(title="Inbox one")).id

    def create(self, expect: int = 201, **body):
        r = self.client.post("/api/videos", json={"format": "tech-explainer", "channel": "tech-en", **body})
        self.assertEqual(r.status_code, expect, r.text)
        return r.json()

    def listing(self) -> list[str]:
        return sorted(p.name for p in (self.footage / "videos").iterdir())

    def test_create_writes_video_json_with_status_idea_and_returns_the_detail(self):
        detail = self.create(title="  Vienna, day 2!  ")
        self.assertEqual(detail["slug"], "vienna-day-2")
        folder = self.footage / "videos" / "vienna-day-2"
        self.assertEqual(json.loads((folder / "video.json").read_text()), {
            "schema": "cf-video/1", "slug": "vienna-day-2", "title_working": "Vienna, day 2!",
            "format": "tech-explainer", "channel": "tech-en", "language": "ru", "footage": [],
            "status": "idea", "history": [{"status": "idea", "at": today(), "note": ""}],
            "references": [], "ideas": [], "published_url": None})
        self.assertEqual(detail, self.ok(self.client.get("/api/videos/vienna-day-2")))
        self.assertFalse((folder / "brief.md").exists())

    def test_the_new_video_is_first_in_the_list_with_stage_idea(self):
        self.create(title="Fresh one")
        first = self.ok(self.client.get("/api/videos"))["videos"][0]
        self.assertEqual((first["slug"], first["status"], first["stage"]), ("fresh-one", "idea", "idea"))

    def test_slug_transliterates_cyrillic_and_falls_back_to_video(self):
        cases = (("Вена: день 2", "vena-den-2"), ("Щука и ёж", "shchuka-i-ezh"), ("!!!", "video"))
        for title, slug in cases:
            with self.subTest(title):
                self.assertEqual(self.create(title=title)["slug"], slug)
                self.assertRegex(slug, NAME_RE)
        self.assertIn("vena-den-2", [v["slug"] for v in self.ok(self.client.get("/api/videos"))["videos"]])

    def test_slug_folds_latin_diacritics_and_ukrainian_letters(self):
        cases = (("Zürich", "zurich"), ("Kraków", "krakow"), ("Café crème", "cafe-creme"), ("Київ", "kiyiv"),
                 ("Ґанок і є", "ganok-i-ye"), ("Йошкар-Ола ёлка", "yoshkar-ola-elka"))
        for title, slug in cases:
            with self.subTest(title):
                self.assertEqual(self.create(title=title)["slug"], slug)

    def test_without_a_local_root_create_is_409_and_creates_nothing(self):
        missing = self.footage.parent / "nowhere"
        client = TestClient(create_app(self.repo, local_root=missing, db_path=self.db,
                                       web_dist=self.footage / "dist"))
        r = client.post("/api/videos", json={"title": "T", "format": "tech-explainer", "channel": "x",
                                             "new_channel": True})
        self.assertEqual((r.status_code, r.json()["code"], r.json()["params"]),
                         (409, "local_root_missing", {"path": str(missing)}))
        self.assertFalse(missing.exists())

    def test_a_new_channel_name_is_lower_case_capped_and_matches_known_ones_ignoring_case(self):
        made = self.create(title="Upper", channel="  Walks-IG ", new_channel=True)
        self.assertEqual(made["video"]["channel"], "walks-ig")
        self.assertEqual(self.create(title="Known", channel="TECH-EN", new_channel=True)["video"]["channel"],
                         "tech-en")
        r = self.create(422, title="Long", channel="c" * 65, new_channel=True)
        self.assertEqual((r["code"], r["params"]), ("channel_invalid", {"channel": "c" * 65, "max": 64}))
        self.assertEqual(self.create(title="Max", channel="c" * 64, new_channel=True)["video"]["channel"], "c" * 64)

    def test_slug_is_cut_to_60_chars_at_a_dash(self):
        slug = self.create(title="word " * 30)["slug"]
        self.assertEqual(slug, "-".join(["word"] * 12))
        self.assertLessEqual(len(slug), 60)
        self.assertEqual(self.create(title="x" * 80)["slug"], "x" * 60)

    def test_slug_is_unique(self):
        self.assertEqual(self.create(title="X")["slug"], "x")
        self.assertEqual(self.create(title="X")["slug"], "x-2")
        self.assertEqual(self.create(title="Long one")["slug"], "long-one-2")
        (self.footage / "videos" / "stray").mkdir()
        self.assertEqual(self.create(title="Stray")["slug"], "stray-2")

    def test_empty_or_too_long_title_is_422_and_writes_nothing(self):
        before = self.listing()
        for title, code, params in (("   ", "title_empty", {}), ("y" * 201, "title_too_long", {"max": 200})):
            with self.subTest(code):
                r = self.create(422, title=title)
                self.assertEqual((r["code"], r["params"]), (code, params))
        self.assertEqual(self.listing(), before)

    def test_unknown_format_is_422_naming_the_known_ones(self):
        before = self.listing()
        r = self.create(422, title="T", format="nope")
        self.assertEqual((r["code"], r["params"]), ("format_unknown", {
            "format": "nope", "formats": ["tech-explainer", "walk-reel"]}))
        self.assertEqual(self.listing(), before)

    def test_unknown_channel_is_422_naming_the_known_ones(self):
        before = self.listing()
        r = self.create(422, title="T", channel="travel")
        self.assertEqual((r["code"], r["params"]), ("channel_unknown", {"channel": "travel", "channels": ["tech-en"]}))
        self.assertEqual(self.listing(), before)

    def test_a_new_channel_is_created_on_request_and_then_known(self):
        before = self.listing()
        for bad in ("a/b", ".x", "../x", "", "_unassigned"):
            with self.subTest(bad):
                r = self.create(422, title="T", channel=bad, new_channel=True)
                self.assertEqual((r["code"], r["params"]), ("channel_invalid", {"channel": bad, "max": 64}))
        self.assertEqual(self.listing(), before)
        made = self.create(title="Town", format="walk-reel", channel="walks-ig", new_channel=True)
        self.assertEqual((made["video"]["channel"], made["video"]["language"]), ("walks-ig", None))
        ids = [c["id"] for c in self.ok(self.client.get("/api/channels"))["channels"]]
        self.assertEqual(ids, ["tech-en", "walks-ig"])
        self.assertEqual(self.create(title="Again", channel="tech-en", new_channel=True)["video"]["channel"],
                         "tech-en")

    def test_linking_a_brief_copies_it_and_records_the_idea(self):
        before = (self.brief_path.read_bytes(), self.brief_path.stat().st_mtime_ns)
        made = self.create(title="From the brief", idea_id=self.briefed)
        folder = self.footage / "videos" / made["slug"]
        self.assertEqual((folder / "brief.md").read_bytes(), before[0])
        video = json.loads((folder / "video.json").read_text())
        self.assertEqual((video["ideas"], video["references"], video["language"]), ([self.briefed], [V1], "ru"))
        self.assertEqual((self.brief_path.read_bytes(), self.brief_path.stat().st_mtime_ns), before)
        self.assertIn("brief.md", [f["path"] for f in made["files"]])

    def test_an_idea_without_a_brief_or_unknown_is_404_and_writes_nothing(self):
        before = self.listing()
        for idea, code in ((self.inbox, "brief_missing"), (999, "idea_not_found")):
            with self.subTest(code):
                r = self.create(404, title="T", idea_id=idea)
                self.assertEqual(r["code"], code)
        self.assertEqual(self.listing(), before)

    def test_without_a_db_create_works_but_a_brief_link_is_404_db_missing(self):
        client = TestClient(create_app(self.repo, local_root=self.footage, db_path=self.footage / "none.db",
                                       web_dist=self.footage / "dist"))
        r = client.post("/api/videos", json={"title": "T", "format": "tech-explainer", "channel": "tech-en"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertIsNone(r.json()["video"]["language"])
        self.assertEqual([c["id"] for c in client.get("/api/channels").json()["channels"]], ["tech-en"])
        before = self.listing()
        r = client.post("/api/videos", json={"title": "T", "format": "tech-explainer", "channel": "tech-en",
                                             "idea_id": self.briefed})
        self.assertEqual((r.status_code, r.json()["code"]), (404, "db_missing"))
        self.assertEqual(self.listing(), before)

    def test_missing_fields_are_request_invalid(self):
        for body in ({}, {"title": "T"}, {"title": "T", "format": "tech-explainer", "channel": "tech-en",
                                          "idea_id": "x"}):
            with self.subTest(body):
                r = self.client.post("/api/videos", json=body)
                self.assertEqual((r.status_code, r.json()["code"]), (422, "request_invalid"))

    def test_create_launches_no_process(self):
        with mock.patch("subprocess.Popen", side_effect=AssertionError("Popen")), \
                mock.patch("os.posix_spawn", side_effect=AssertionError("posix_spawn")):
            self.create(title="Quiet", idea_id=self.briefed)

    def brief_ideas(self) -> dict[int, list[str]]:
        r = self.ok(self.client.get("/api/contour/ideas", params={"status": "brief"}))
        return {i["id"]: [v["slug"] for v in i["videos"]] for i in r["ideas"]}

    def test_creating_from_a_brief_links_the_idea_to_the_video(self):
        self.assertEqual(self.brief_ideas(), {self.briefed: []})
        first = self.create(title="From the brief", idea_id=self.briefed)["slug"]
        self.assertEqual(self.brief_ideas(), {self.briefed: [first]})
        second = self.create(title="Second take", idea_id=self.briefed)["slug"]
        self.assertEqual(self.brief_ideas(), {self.briefed: [first, second]})
        self.create(title="No brief")
        with st.open_store(self.db, seed=False, create=True) as s:
            self.assertEqual(s.query("SELECT idea_id, owner, video_slug FROM idea_video ORDER BY rowid"),
                             [{"idea_id": self.briefed, "owner": st.person(), "video_slug": first},
                              {"idea_id": self.briefed, "owner": st.person(), "video_slug": second}])

    def test_a_failed_link_write_leaves_no_folder(self):
        before = self.listing()
        with mock.patch("cf.research.ideas.link_video", side_effect=RuntimeError("locked")):
            client = TestClient(self.client.app, raise_server_exceptions=False)
            r = client.post("/api/videos", json={"title": "Linked", "format": "tech-explainer",
                                                 "channel": "tech-en", "idea_id": self.briefed})
        self.assertEqual((r.status_code, r.json()["code"]), (500, "idea_link_failed"), r.text)
        self.assertEqual(r.json()["params"]["id"], self.briefed)
        self.assertEqual(self.listing(), before)

    def test_a_failure_after_the_folder_is_claimed_leaves_no_folder(self):
        with mock.patch("cf.desk.videos_api.atomic_write", side_effect=OSError("disk full")):
            client = TestClient(self.client.app, raise_server_exceptions=False)
            r = client.post("/api/videos", json={"title": "Doomed", "format": "tech-explainer",
                                                 "channel": "tech-en", "idea_id": self.briefed})
        self.assertEqual(r.status_code, 500)
        self.assertFalse((self.footage / "videos" / "doomed").exists())


class ListStageFilterTest(VideosTestCase):
    def test_each_status_maps_to_its_stage(self):
        for status in ("idea", "brief", "script", "recording", "edit", "review", "published", "weird"):
            write(self.footage / "videos" / f"s-{status}" / "video.json",
                  json.dumps({**VIDEO, "slug": f"s-{status}", "status": status}))
        write(self.footage / "videos" / "s-broken" / "video.json", "{oops")
        body = self.ok(self.client.get("/api/videos"))
        stages = {v["slug"]: v["stage"] for v in body["videos"] if v["slug"].startswith("s-")}
        self.assertEqual(stages, {"s-idea": "idea", "s-brief": "idea", "s-script": "script",
                                  "s-recording": "script", "s-edit": "edit", "s-review": "edit",
                                  "s-published": "done", "s-weird": None, "s-broken": None})
        self.assertEqual(body["stages"], ["idea", "script", "edit", "done"])

    def test_a_legacy_reel_has_the_stage_of_its_derived_status(self):
        def stage() -> str:
            return {v["slug"]: v["stage"] for v in self.ok(self.client.get("/api/videos"))["videos"]}["w1~short-01"]

        self.assertEqual(stage(), "script")
        write(self.reel / "out" / "short-01.mp4", MP4)
        self.assertEqual(stage(), "edit")

    def test_filters_by_format_channel_and_both(self):
        write(self.footage / "videos" / "other" / "video.json",
              json.dumps({**VIDEO, "slug": "other", "channel": "walks-ig", "format": "walk-reel"}))

        def slugs(**params) -> list[str]:
            r = self.client.get("/api/videos", params=params)
            self.assertEqual(r.status_code, 200, r.text)
            return sorted(v["slug"] for v in r.json()["videos"])

        self.assertEqual(slugs(format="walk-reel"), ["other", "w1~short-01"])
        self.assertEqual(slugs(channel="tech-en"), ["long-one"])
        self.assertEqual(slugs(format="walk-reel", channel="walks-ig"), ["other"])
        self.assertEqual(slugs(format="walk-reel", channel="tech-en"), [])
        self.assertEqual(slugs(format="nope"), [])
        self.assertEqual(slugs(format="", channel=""), ["long-one", "other", "w1~short-01"])


class ChannelsTest(VideosTestCase):
    def setUp(self):
        super().setUp()
        self.db = self.footage / "factory.db"
        with st.open_store(self.db, create=True) as s:
            wl.create(s, "tools", format_id="tech-explainer", author_channel="tech-en", language="en")
            wl.create(s, "more-tools", format_id="tech-short", author_channel="tech-en", language="de")
            wl.create(s, "nobody", format_id="walk-reel")
        for name in ("travel", "_unassigned", ".hidden", "tech-en"):
            (self.footage / "channels" / name / "briefs").mkdir(parents=True)
        write(self.footage / "videos" / "town" / "video.json",
              json.dumps({**VIDEO, "slug": "town", "channel": "walks-ig", "format": "walk-reel"}))

    def channels(self, client=None) -> list[dict]:
        return self.ok((client or self.client).get("/api/channels"))["channels"]

    def test_channels_are_the_union_of_watchlists_brief_folders_and_videos(self):
        self.assertEqual(self.channels(), [
            {"id": "tech-en", "formats": ["tech-explainer", "tech-short"], "languages": ["de", "en"],
             "watchlists": ["more-tools", "tools"], "videos": 1},
            {"id": "travel", "formats": [], "languages": [], "watchlists": [], "videos": 0},
            {"id": "walks-ig", "formats": ["walk-reel"], "languages": [], "watchlists": [], "videos": 1}])

    def test_channels_without_a_db_or_with_another_schema_still_list_folders_and_videos(self):
        other = self.footage / "other.db"
        shutil.copy(self.db, other)
        conn = sqlite3.connect(other)
        conn.execute("PRAGMA user_version = 99")
        conn.commit()
        conn.close()
        for db in (self.footage / "none.db", other):
            with self.subTest(db.name):
                client = TestClient(create_app(self.repo, local_root=self.footage, db_path=db,
                                               web_dist=self.footage / "dist"))
                self.assertEqual([(c["id"], c["videos"], c["watchlists"]) for c in self.channels(client)],
                                 [("tech-en", 1, []), ("travel", 0, []), ("walks-ig", 1, [])])
