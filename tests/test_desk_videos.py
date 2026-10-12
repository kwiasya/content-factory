"""Desk Videos API and media streaming through the FastAPI TestClient on a temporary footage root."""

import json
import os
import shutil
import tempfile
import unittest
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
