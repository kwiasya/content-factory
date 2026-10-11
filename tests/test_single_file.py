"""Proxy and Shot log for one media file outside a Walk (no clip_manifest.json).

A 2 s synthetic clip is made with ffmpeg's testsrc (landscape pixels, 90 degree display
rotation, 25 fps); the heavy Shot log metrics (YOLO, OpenCV motion, Apple Vision, Whisper)
are replaced by stubs, so nothing here loads a model.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from cf import proxy, shotlog
from cf.metrics import common, people, vision

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None or shutil.which("ffprobe") is None, reason="needs ffmpeg and ffprobe")


def _ffprobe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-show_format",
                          "-of", "json", str(path)], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


@pytest.fixture(scope="module")
def media(tmp_path_factory) -> Path:
    """2 s, 320x180 pixels shown rotated 90 degrees (portrait 180x320), 25 fps, no manifest anywhere."""
    d = tmp_path_factory.mktemp("download")
    flat = d / "flat.mp4"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=25", "-t", "2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(flat)], check=True)
    rotated = d / "dQw4w9WgXcQ.mp4"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-display_rotation", "90", "-i", str(flat), "-c", "copy", str(rotated)],
                   check=True)
    flat.unlink()
    return rotated


def test_proxy_one_file_into_a_directory(media, tmp_path):
    out_dir = tmp_path / "proxy"
    assert proxy.main([str(media), str(out_dir)]) == 0
    made = out_dir / "dQw4w9WgXcQ.mp4"
    probe = _ffprobe(made)
    stream = probe["streams"][0]
    assert (stream["width"], stream["height"]) == (540, 960)  # display-oriented, short side 540
    assert float(probe["format"]["duration"]) == pytest.approx(2.0, abs=0.1)
    assert not (tmp_path / "clip_manifest.json").exists()


def test_proxy_one_file_to_an_explicit_path(media, tmp_path):
    out = tmp_path / "ref" / "proxy.mp4"
    assert proxy.main([str(media), str(out)]) == 0
    stream = _ffprobe(out)["streams"][0]
    assert (stream["width"], stream["height"]) == (540, 960)
    assert [p.name for p in out.parent.iterdir()] == ["proxy.mp4"]


# --------------------------------------------------------------------------- Shot log


def _no_people(info):
    nb = common.n_bins(info.duration_s)
    return {"persons": [0] * nb, "max_person_h": [0.0] * nb, "events": [], "tracks": 0,
            "subject": {"dominated": False, "tracks": [], "coverage": 0.0}, "_boxes": None, "_model": "stub", "_device": "cpu"}


def _no_vision(info):
    nb = common.n_bins(info.duration_s)
    return {"aes": [None] * nb, "is_utility": [None] * nb, "faces": [None] * nb, "max_face_h": [None] * nb,
            "_available": False, "_error": "stub"}


@pytest.fixture
def light_models(monkeypatch):
    """YOLO, Apple Vision and the version banner (imports torch) replaced; ffmpeg stats, OpenCV
    motion and the speech pass (the synthetic clip has no audio, so Whisper never loads) are real."""
    monkeypatch.setattr(people, "analyze", _no_people)
    monkeypatch.setattr(vision, "analyze", _no_vision)
    monkeypatch.setattr(shotlog, "_versions", lambda *a: {"generator": shotlog.GENERATOR})


def test_shotlog_for_a_proxy_without_manifest_takes_the_header_from_the_source(media, tmp_path, light_models):
    ref = tmp_path / "references" / "travel" / "dQw4w9WgXcQ"
    made = proxy.proxy_file(media, ref / "proxy.mp4")
    out = ref / "shotlog.json"

    assert shotlog.main([made["proxy_path"], "--source", str(media), "-o", str(out)]) == 0

    data = json.loads(out.read_text())
    assert data["schema"] == "reel-shotlog/1.2"
    assert {"clip", "per_second", "segments", "rejects", "summary", "provenance"} <= data.keys()
    clip = data["clip"]
    assert clip["header_source"] == "probe(source)"
    assert clip["id"] == "dQw4w9WgXcQ"
    assert clip["path"] == str(media.resolve())
    assert clip["fps"] == 25
    assert clip["source_duration_s"] == pytest.approx(2.0, abs=0.05)
    assert clip["orientation"] == "portrait"  # 320x180 pixels, rotated 90 on display
    assert len(data["per_second"]["t"]) == 2
    assert sorted(p.name for p in ref.iterdir()) == ["proxy.mp4", "shotlog.json"]


def test_shotlog_outside_a_walk_needs_an_output_path(media, tmp_path, light_models):
    made = proxy.proxy_file(media, tmp_path / "ref" / "proxy.mp4")
    with pytest.raises(SystemExit):
        shotlog.main([made["proxy_path"], "--source", str(media)])
