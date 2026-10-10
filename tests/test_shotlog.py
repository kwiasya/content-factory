"""Unit tests for Shot log binning, scoring and window selection (no video needed)."""

from __future__ import annotations

import math
from datetime import datetime

import cv2
import numpy as np
import pytest

from cf import scoring
from cf.metrics import common, ffstats, motion, people, speech, vision
from cf.shotlog import clip_id, finalize, find_manifest_entry, has_speech


# --------------------------------------------------------------------------- binning


def test_n_bins_drops_short_tail():
    assert common.n_bins(13.1) == 13
    assert common.n_bins(13.5) == 14
    assert common.n_bins(3.0) == 3
    assert common.n_bins(0.2) == 1


def test_bin_reduce_vfr_timestamps_and_gaps():
    # VFR: dense samples in second 0, none in second 1, two in second 2, one past the end
    t = [0.0, 0.1, 0.5, 0.9, 2.2, 2.8, 3.4]
    v = [1, 2, 3, 4, 10, 20, 30]
    out = common.bin_reduce(t, v, 3)
    assert out[0] == pytest.approx(2.5)
    assert out[1] is None
    assert out[2] == pytest.approx(20.0)  # 3.4 folds into the last bin
    assert common.bin_reduce(t, v, 3, np.max)[0] == 4


def test_bin_reduce_ignores_nan():
    assert common.bin_reduce([0.1, 0.2], [float("nan"), 5.0], 1) == [5.0]


def test_fill_gaps():
    assert common.fill_gaps([None, 2.0, None, None, 5.0]) == [2.0, 2.0, 2.0, 5.0, 5.0]
    assert common.fill_gaps([None, None]) == [None, None]


def test_parse_metadata_aligns_fields_per_frame():
    text = "\n".join(
        [
            "frame:0    pts:0       pts_time:0",
            "lavfi.signalstats.YAVG=100",
            "lavfi.scd.score=0.000",
            "frame:1    pts:256     pts_time:0.0166667",
            "lavfi.signalstats.YAVG=110",
            "lavfi.blur=4.5",
            "lavfi.scd.score=12.5",
        ]
    )
    times, cols = ffstats.parse_metadata(text)
    assert times == pytest.approx([0.0, 0.0166667])
    assert cols["yavg"] == [100.0, 110.0]
    assert cols["scd"] == [0.0, 12.5]
    assert math.isnan(cols["blur"][0]) and cols["blur"][1] == 4.5


def test_clip_pcts_and_luma_norm():
    frame = np.array([10, 16, 128, 233, 240, 100, 100, 100, 100, 100], dtype=np.uint8)
    hi, lo = ffstats.clip_pcts(frame, "tv")
    assert hi == pytest.approx(20.0)
    assert lo == pytest.approx(20.0)
    assert ffstats.luma_norm(np.array([16.0, 235.0]), "tv").tolist() == [0.0, 1.0]


# --------------------------------------------------------------------------- scoring


def _ps(n=10, **over):
    ps = {
        "luma_mean": [0.5] * n,
        "clip_hi_pct": [0.1] * n,
        "clip_lo_pct": [0.0] * n,
        "blur": [4.5] * n,
        "scd_score": [1.0] * n,
        "shake_px": [0.5] * n,
        "aes": [0.4] * n,
        "motion": [{"type": "locked", "speed": 0.01, "dx": 0.0, "dy": 0.0, "div": 0.0}] * n,
    }
    ps.update(over)
    return ps


def test_blur_worst20_needs_to_be_clearly_worse():
    assert not any(scoring.blur_bad_mask([4.5, 4.52, 4.51, 4.55, 4.53, 4.5]))
    mask = scoring.blur_bad_mask([4.5, 4.5, 4.6, 4.5, 7.0, 4.4, 4.5, 4.6, 4.5, 6.5])
    assert mask == [False, False, False, False, True, False, False, False, False, True]


def test_bin_flags_each_rule():
    ps = _ps(6, shake_px=[0.5, 9.0, 0.5, 0.5, 0.5, 0.5], clip_hi_pct=[0.1, 0.1, 3.0, 0.1, 0.1, 0.1],
             scd_score=[1, 1, 1, 25.0, 1, 1])
    flags = scoring.bin_flags(ps)
    assert flags[0] == []
    assert flags[1] == ["shake_px>6"]
    assert flags[2] == ["clip_hi>2%"]
    assert flags[3] == ["scd_spike"]


def test_bin_flags_speech_makes_a_second_unusable():
    ps = _ps(4, speech=[False, True, False, True], shake_px=[0.5, 0.5, 0.5, 9.0])
    flags = scoring.bin_flags(ps)
    assert flags == [[], ["speech"], [], ["shake_px>6", "speech"]]
    # reel-shotlog/1.0 logs have no speech array: nothing flagged for speech
    assert scoring.bin_flags(_ps(2)) == [[], []]


def test_quality_weights_and_aes_redistribution():
    full = {"aes": 1.0, "sharp": 0.0, "stability": 0.0, "exposure": 0.0}
    assert scoring.quality(full) == pytest.approx(0.35)
    no_aes = {"aes": None, "sharp": 1.0, "stability": 0.5, "exposure": 0.0}
    assert scoring.quality(no_aes) == pytest.approx((0.25 + 0.1) / 0.65)
    assert scoring.quality({"aes": None, "sharp": 1, "stability": 1, "exposure": 1}) == pytest.approx(1.0)


def test_components_ranges():
    ps = _ps(3, shake_px=[0.0, 6.0, 20.0], blur=[4.2, 7.5, 5.85], aes=[None, 1.0, -1.0], luma_mean=[0.5, 0.05, 0.9])
    c = scoring.components(ps)
    assert [x["stability"] for x in c] == pytest.approx([1.0, 0.5, 0.0])
    assert [x["sharp"] for x in c] == pytest.approx([1.0, 0.0, 0.5])
    assert [x["aes"] for x in c] == [None, 1.0, 0.0]
    assert c[0]["exposure"] > 0.9 and c[1]["exposure"] == pytest.approx(0.0) and c[2]["exposure"] < 0.2


def test_exposure_penalises_clipping():
    assert scoring.exposure_score(0.5, 0.0, 0.0) == pytest.approx(1.0)
    assert scoring.exposure_score(0.5, 5.0, 0.0) == pytest.approx(0.0)
    assert scoring.exposure_score(0.5, 0.0, 20.0) == pytest.approx(0.5)


# --------------------------------------------------------------------------- windows


def test_select_windows_picks_best_usable_non_overlapping():
    q = [0.2, 0.2, 0.9, 0.9, 0.9, 0.2, 0.5, 0.5, 0.95, 0.95, 0.3, 0.3]
    usable = [True] * 8 + [False, True, True, True]
    w = scoring.select_windows(q, usable)
    assert len(w) <= 3
    assert (w[0]["in_s"], w[0]["out_s"]) == (2.0, 5.0)  # the 0.9 run; 8 is unusable so 0.95 can't pair
    spans = [(x["bins"][0], x["bins"][1]) for x in w]
    for i, a in enumerate(spans):
        for b in spans[i + 1:]:
            assert a[1] <= b[0] or b[1] <= a[0]
    for x in w:
        assert all(usable[x["bins"][0]: x["bins"][1]])
        assert 2 <= x["bins"][1] - x["bins"][0] <= 5


def test_select_windows_prefers_longer_when_equal_and_clips_to_duration():
    q = [0.8] * 7
    w = scoring.select_windows(q, [True] * 7, duration_s=6.6)
    assert w[0]["bins"][1] - w[0]["bins"][0] == 5
    assert all(x["out_s"] <= 6.6 for x in w)


def test_select_windows_skips_window_shortened_by_partial_last_bin():
    w = scoring.select_windows([0.1, 0.1, 0.1, 0.9, 0.9], [True] * 5, duration_s=4.6, p=scoring.Params(top_n=5))
    assert all(x["out_s"] - x["in_s"] >= 1.95 for x in w)
    assert (3.0, 4.6) not in [(x["in_s"], x["out_s"]) for x in w]


def test_people_lone_person_after_id_switch_is_subject():
    samples = [(i / 3, [(1, 0.3, 0.5)]) for i in range(6)] + [(2.0, [(7, 0.9, 0.5)]), (2.33, [(7, 0.95, 0.5)])]
    out = people.summarize(samples, 3)
    assert not [e for e in out["events"] if e["type"] == "stranger_closeup"]


def test_select_windows_none_when_nothing_usable_long_enough():
    assert scoring.select_windows([0.9] * 5, [True, False, True, False, True]) == []


def test_select_windows_motion_consistency_bonus():
    q = [0.7] * 4
    types = ["pan_left", "pan_left", "locked", "pan_right"]
    w = scoring.select_windows(q, [True] * 4, types, scoring.Params(max_len=2, top_n=1))
    assert w[0]["bins"] == (0, 2)


def test_reject_runs_merge_and_why():
    flags = [[], ["shake_px>6"], ["shake_px>6", "scd_spike"], [], ["clip_hi>2%"]]
    r = scoring.reject_runs(flags, duration_s=4.6)
    assert r == [
        {"in_s": 1.0, "out_s": 3.0, "why": ["shake_px>6", "scd_spike"]},
        {"in_s": 4.0, "out_s": 4.6, "why": ["clip_hi>2%"]},
    ]


# --------------------------------------------------------------------------- tags


def test_motion_classify_signs():
    assert motion.classify(-200, 0, 0.0, 1.0) == "pan_right"  # content moves left -> camera pans right
    assert motion.classify(200, 0, 0.0, 1.0) == "pan_left"
    assert motion.classify(0, 0, 0.1, 1.0) == "forward_walk"
    assert motion.classify(0, 0, -0.1, 1.0) == "pull_back"
    assert motion.classify(5, 5, 0.0, 0.5) == "locked"
    assert motion.classify(30, 40, 0.0, 9.0) == "handheld"
    assert motion.classify(30, 40, 0.0, 1.0) == "drift"


def test_motion_tag_push_in_vs_forward_walk():
    fw = {"type": "forward_walk", "speed": 0.02, "dx": 0, "dy": 0, "div": 0.06}
    assert scoring.motion_tag([fw] * 3, [0.5] * 3) == "push_in"
    assert scoring.motion_tag([fw] * 3, [4.0] * 3) == "forward_walk"
    mixed = [{"type": t, "speed": 0.1} for t in ("pan_left", "locked", "drift", "handheld")]
    assert scoring.motion_tag(mixed, [1] * 4) == "handheld"


def test_pair_transform_recovers_translation():
    rng = np.random.default_rng(0)
    img = cv2.GaussianBlur((rng.random((480, 270)) * 255).astype(np.uint8), (5, 5), 0)
    shifted = np.roll(img, 6, axis=1)  # content moves right by 6 px
    r = motion.pair_transform(img, shifted)
    assert r is not None
    assert r["dx"] == pytest.approx(6, abs=0.5)
    assert abs(r["dy"]) < 0.5 and r["scale"] == pytest.approx(1, abs=0.01)


def test_solar_elevation_potsdam():
    lat, lon = 52.39, 13.06
    evening = scoring.solar_elevation(datetime.fromisoformat("2026-10-04T17:33:00+02:00"), lat, lon)
    noon = scoring.solar_elevation(datetime.fromisoformat("2026-06-21T13:15:00+02:00"), lat, lon)
    night = scoring.solar_elevation(datetime.fromisoformat("2026-10-04T23:00:00+02:00"), lat, lon)
    assert 4 < evening < 12
    assert 58 < noon < 62
    assert night < -20


def test_light_tag_classes():
    golden = scoring.light_tag(0.5, 0.2, 0.2, 0.5, "2026-10-04T17:33:00+02:00")
    assert golden["tag"] == "golden_hour"
    night = scoring.light_tag(0.1, 0.1, 0.0, 0.3, "2026-10-04T22:00:00+02:00")
    assert night["tag"] == "night"
    day = scoring.light_tag(0.6, 0.25, 0.1, 0.6, "2026-10-04T14:00:00+02:00")
    assert day["tag"] is None and day["confidence"] >= 0.4
    overcast = scoring.light_tag(0.6, 0.06, 0.0, 0.3, "2026-10-04T14:00:00+02:00")
    assert overcast["tag"] == "overcast"
    assert scoring.light_tag(0.5, 0.2, 0.1, 0.5, None)["confidence"] <= 0.3
    for r in (golden, night, day, overcast):
        assert r["tag"] is None or r["tag"] in scoring.LIGHT_VOCAB


# --------------------------------------------------------------------------- people / vision


def test_people_events_and_subject():
    samples = [
        (0.0, [(1, 0.6, 0.5)]),
        (0.33, [(1, 0.62, 0.5)]),
        (0.66, [(1, 0.6, 0.5), (2, 0.2, 0.1)]),
        (1.0, [(1, 0.6, 0.5), (2, 0.5, 0.15)]),
        (1.33, [(1, 0.6, 0.5)]),
        (1.66, [(1, 0.6, 0.5), (3, 0.3, 0.9)]),
    ]
    out = people.summarize(samples, 2)
    assert out["persons"] == [2, 2]
    assert out["max_person_h"] == [0.62, 0.6]
    types = [(e["type"], e["track"]) for e in out["events"]]
    assert ("person_enter", 2) in types
    assert ("person_enter", 3) not in types  # seen once only
    assert ("person_enter", 1) not in types  # present from the start
    assert ("stranger_closeup", 2) in types
    assert ("stranger_closeup", 1) not in types  # the author on camera
    assert out["subject"]["dominated"] and out["subject"]["tracks"] == [1]
    enter = next(e for e in out["events"] if e["type"] == "person_enter")
    assert enter["side"] == "left"


def test_vision_summarize_bins_and_nulls():
    frames = [
        {"t": 0.0, "aesthetic": 0.5, "is_utility": False, "faces": 1, "max_face_h": 0.2, "humans": 1, "max_human_h": 0.8},
        {"t": 1.02, "aesthetic": None, "is_utility": False, "faces": 0, "max_face_h": 0.0, "humans": 0, "max_human_h": 0.0, "error": "x"},
    ]
    out = vision.summarize(frames, 3)
    assert out["aes"] == [0.5, None, None]
    assert out["faces"] == [1, 0, None]
    assert out["is_utility"] == [False, False, None]


# --------------------------------------------------------------------------- header


def test_clip_id_and_manifest_lookup():
    from pathlib import Path

    assert clip_id(Path("proxy/IMG_1621_approx.mp4")) == "IMG_1621"
    m = {"clips": [{"file": "IMG_1621.mov"}, {"file": "IMG_0332.MOV"}]}
    assert find_manifest_entry(m, "IMG_1621")["file"] == "IMG_1621.mov"
    assert find_manifest_entry(m, "nope") is None


# --------------------------------------------------------------------------- speech


def test_speech_bins_padding():
    # 1.8-1.9 padded by 0.3 -> 1.5-2.2: seconds 1 and 2
    assert speech.speech_bins([(1.8, 1.9)], 4) == [False, True, True, False]
    # padding before 0 is clipped; 0.05-0.2 -> 0-0.5: second 0 only
    assert speech.speech_bins([(0.05, 0.2)], 3) == [True, False, False]
    # 0.4-0.7 -> 0.1-1.0 ends exactly on the boundary: second 1 stays clean
    assert speech.speech_bins([(0.4, 0.7)], 3) == [True, False, False]
    # 0.4-0.71 -> 0.1-1.01 reaches into second 1
    assert speech.speech_bins([(0.4, 0.71)], 3) == [True, True, False]
    # without padding only the seconds the word itself touches
    assert speech.speech_bins([(1.8, 1.9)], 4, pad=0.0) == [False, True, False, False]
    # a word past the last bin (dropped partial second) folds into the last bin
    assert speech.speech_bins([(5.2, 5.4)], 5) == [False, False, False, False, True]
    assert speech.speech_bins([], 3) == [False, False, False]
    assert speech.speech_seconds([True, False, True]) == 2


class _W:
    def __init__(self, word, start, end, probability=0.9):
        self.word, self.start, self.end, self.probability = word, start, end, probability


class _Seg:
    def __init__(self, text, words):
        self.text, self.words = text, words


class _Res:
    language = "ru"

    def __init__(self, segments):
        self.segments = segments


def test_speech_from_result_segments_text_and_bins():
    res = _Res([
        _Seg(" Ты снимаешь?", [_W(" Ты", 2.1, 2.3, 0.8), _W(" снимаешь?", 2.3, 2.9, 0.6)]),
        _Seg(" ", []),  # empty segment is dropped
    ])
    out = speech.from_result(res, 5)
    assert out["speech"] == [False, True, True, True, False]
    assert out["speech_segments"] == [{"start": 2.1, "end": 2.9, "text": "Ты снимаешь?", "prob": 0.7}]
    assert out["speech_text"] == "Ты снимаешь?"
    assert out["_language"] == "ru"


def test_speech_analyze_without_raw_or_audio(tmp_path):
    out = speech.analyze(None, 3.4)
    assert out["speech"] == [False, False, False] and out["speech_segments"] == [] and out["_audio"] is False
    assert speech.analyze(tmp_path / "missing.MOV", 2.0)["_error"] == "raw source not found"


def test_find_raw_prefers_manifest_path_then_walk_raw(tmp_path):
    (tmp_path / "raw").mkdir()
    raw = tmp_path / "raw" / "IMG_1621.mov"
    raw.write_bytes(b"")
    assert speech.find_raw(tmp_path, "IMG_1621") == raw
    assert speech.find_raw(tmp_path, "IMG_1621", "/nonexistent/IMG_1621.mov") == raw
    assert speech.find_raw(tmp_path, "IMG_0001") is None
    assert speech.find_raw(None, "IMG_1621", str(raw)) == raw


def _log(n=8, speech_arr=None):
    ps = _ps(n)
    ps.update({
        "t": list(range(n)), "persons": [0] * n, "sat": [0.2] * n, "warmth": [0.0] * n, "contrast": [0.5] * n,
        "is_utility": [False] * n, "quality": [0.0] * n, "usable": [True] * n,
    })
    if speech_arr is not None:
        ps["speech"] = speech_arr
    return {
        "schema": "reel-shotlog/1.0",
        "clip": {"id": "IMG_X", "duration_s": float(n), "created": None, "gps": None},
        "per_second": ps,
        "events": [],
        "summary": {"flags": ["author_on_camera"]},
        "provenance": {"notes": {"subject": {"dominated": True}}},
    }


def test_finalize_speech_rejects_and_new_best():
    data = finalize(_log(8, [False, False, False, True, True, False, False, False]))
    ps = data["per_second"]
    assert ps["usable"] == [True, True, True, False, False, True, True, True]
    assert data["rejects"] == [{"in_s": 3.0, "out_s": 5.0, "why": ["speech"]}]
    for seg in data["segments"]:
        assert seg["out_s"] <= 3.0 or seg["in_s"] >= 5.0
    assert data["summary"]["speech_s"] == 2
    assert data["summary"]["flags"] == ["author_on_camera", "speech"]
    assert data["summary"]["usable_s"] == 6


def test_finalize_reads_old_log_without_speech():
    old = _log(6)
    assert not has_speech(old)
    data = finalize(old)
    assert data["summary"]["speech_s"] is None
    assert data["rejects"] == [] and data["summary"]["usable_s"] == 6
    # a log where everything is speech becomes a reject with that reason
    talk = finalize(_log(4, [True] * 4))
    assert talk["segments"] == [] and talk["summary"]["reject_clip"]
    assert talk["summary"]["reject_why"] == ["speech"]
