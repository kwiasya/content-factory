"""Deep fetch of one Reference: what fetch makes of a URL and of a yt-dlp info dict, on a temp store.

yt-dlp, stable-ts, proxy, Shot log and OCR are replaced by fakes that write fixture files;
channels.list is answered by a recorded payload. No network, no models.
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import cli, fetch, youtube
from cf.research import watchlist as wl
from cf.research import store as st

FIX = Path(__file__).parent / "fixtures" / "research"


def fixture(name: str) -> dict:
    return json.loads((FIX / name).read_text())


class VideoRefTest(unittest.TestCase):
    def test_urls_and_bare_ids_give_the_video_id(self):
        for text in ("dQw4w9WgXcQ",
                     "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
                     "youtube.com/watch?feature=share&v=dQw4w9WgXcQ",
                     "https://youtu.be/dQw4w9WgXcQ?si=abc",
                     "https://www.youtube.com/shorts/dQw4w9WgXcQ",
                     "https://m.youtube.com/live/dQw4w9WgXcQ",
                     "https://www.youtube.com/embed/dQw4w9WgXcQ"):
            with self.subTest(text=text):
                self.assertEqual(fetch.parse_video_ref(text), "dQw4w9WgXcQ")

    def test_a_trailing_newline_pasted_or_url_encoded_is_dropped_not_kept_in_the_id(self):
        for text in ("https://www.youtube.com/watch?v=dQw4w9WgXcQ%0A", "https://youtu.be/dQw4w9WgXcQ%0A",
                     "https://www.youtube.com/shorts/dQw4w9WgXcQ%0A", "dQw4w9WgXcQ\n"):
            with self.subTest(text=text):
                self.assertEqual(fetch.parse_video_ref(text), "dQw4w9WgXcQ")

    def test_a_newline_inside_the_id_is_refused(self):
        for text in ("https://www.youtube.com/watch?v=dQw4w9WgXcQ%0Ax", "dQw4w9W\ngXcQ"):
            with self.subTest(text=text), self.assertRaises(fetch.FetchError):
                fetch.parse_video_ref(text)

    def test_channel_links_and_junk_are_refused(self):
        for text in ("", "https://www.youtube.com/@slowwalks", "https://vimeo.com/123456",
                     "https://www.youtube.com/watch?v=short", "not a video"):
            with self.subTest(text=text):
                with self.assertRaises(fetch.FetchError):
                    fetch.parse_video_ref(text)


class VideoRowTest(unittest.TestCase):
    def test_a_long_video_row_from_the_info_dict(self):
        row = fetch.video_row_from_info(fixture("info_long.json"))
        raw = json.loads(row.pop("raw"))
        self.assertEqual(row, {
            "platform": "youtube",
            "external_id": "dQw4w9WgXcQ",
            "title": "Lisbon Alfama at Golden Hour — 4K Walk",
            "description": "Start: Miradouro de Santa Luzia\n00:00 Intro\n00:40 Alfama stairs\n01:30 Sunset at the viewpoint",
            "published_at": "2026-10-09T16:00:12Z",
            "duration_s": 120.0,
            "kind": "short",
            "tags": '["lisbon","walking tour","4k walk"]',
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        })
        self.assertEqual(raw["heatmap"][0]["value"], 1.0)
        self.assertNotIn("automatic_captions", raw)

    def test_a_short_without_a_timestamp_falls_back_to_the_upload_date_and_drops_formats(self):
        row = fetch.video_row_from_info(fixture("info_short.json") | {"timestamp": None})
        self.assertEqual(row["published_at"], "2026-10-02T00:00:00Z")
        self.assertEqual((row["duration_s"], row["kind"], row["tags"]), (47.0, "short", "[]"))
        self.assertNotIn("formats", json.loads(row["raw"]))

    def test_snapshot_counts_come_from_the_info_and_hidden_ones_stay_null(self):
        self.assertEqual(fetch.snapshot_from_info(fixture("info_long.json")),
                         {"views": 184022, "likes": 5310, "comments": 402})
        self.assertEqual(fetch.snapshot_from_info(fixture("info_short.json")),
                         {"views": 2400000, "likes": None, "comments": None})


class FakeTransport:
    """Answers every Data API call with the next recorded payload and remembers the calls."""

    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, method, params):
        self.calls.append((method, dict(params)))
        p = self.payloads.pop(0)
        if isinstance(p, Exception):
            raise p
        return p


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = st.open_store(Path(self.tmp.name) / "f.db", seed=False, create=True)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()


class RecordInfoTest(StoreCase):
    def test_an_unknown_channel_is_ingested_by_channels_list_without_watchlist_membership(self):
        tr = FakeTransport(fixture("channels_list_handle.json"))
        got = fetch.record_info(self.store, fixture("info_long.json"), transport=tr, taken_at="2026-10-11T10:00:00Z")
        self.assertEqual([(m, p["id"]) for m, p in tr.calls], [("channels.list", "UCxR9mXyZbC1dEf2GhIjKlMn")])
        self.assertEqual(got["channel_source"], "channels.list")
        ch = self.store.one("SELECT id, handle, subscriber_count, own FROM channel")
        self.assertEqual((ch["handle"], ch["subscriber_count"], ch["own"]), ("@slowwalks", 312000, 0))
        self.assertEqual(self.store.query("SELECT * FROM watchlist_channel"), [])
        v = self.store.one("SELECT id, channel_id, external_id, kind FROM video")
        self.assertEqual((v["id"], v["channel_id"], v["external_id"]), (got["video_id"], ch["id"], "dQw4w9WgXcQ"))
        self.assertEqual(self.store.query("SELECT taken_at, views, likes, comments FROM snapshot"),
                         [{"taken_at": "2026-10-11T10:00:00Z", "views": 184022, "likes": 5310, "comments": 402}])

    def test_a_known_channel_costs_no_api_call_and_a_second_fetch_adds_a_snapshot_not_a_video(self):
        fetch.record_info(self.store, fixture("info_long.json"), transport=FakeTransport(fixture("channels_list_handle.json")),
                          taken_at="2026-10-11T10:00:00Z")
        with self.store.transaction() as c:
            c.execute("UPDATE video SET own = 1")
        tr = FakeTransport()
        info = fixture("info_long.json") | {"view_count": 190000}
        fetch.record_info(self.store, info, transport=tr, media=True, transcript=True, taken_at="2026-10-12T10:00:00Z")
        self.assertEqual(tr.calls, [])
        v = self.store.query("SELECT own, has_media, has_transcript FROM video")
        self.assertEqual(v, [{"own": 1, "has_media": 1, "has_transcript": 1}])
        self.assertEqual([r["views"] for r in self.store.query("SELECT views FROM snapshot ORDER BY taken_at")],
                         [184022, 190000])

    def test_a_video_of_an_own_channel_is_own(self):
        tr = FakeTransport(fixture("channels_list_handle.json"))
        fetch.record_info(self.store, fixture("info_long.json"), transport=tr)
        with self.store.transaction() as c:
            c.execute("UPDATE channel SET own = 1")
            c.execute("DELETE FROM video")
        fetch.record_info(self.store, fixture("info_long.json"), transport=tr)
        self.assertEqual(self.store.one("SELECT own FROM video")["own"], 1)

    def test_without_the_data_api_the_channel_comes_from_the_info_dict_and_is_retried_next_time(self):
        down = FakeTransport(youtube.YouTubeError("YOUTUBE_API_KEY is not set"))
        got = fetch.record_info(self.store, fixture("info_long.json"), transport=down)
        self.assertTrue(got["channel_source"].startswith("yt-dlp info"))
        ch = self.store.one("SELECT external_id, handle, title, subscriber_count, raw FROM channel")
        self.assertEqual(ch, {"external_id": "UCxR9mXyZbC1dEf2GhIjKlMn", "handle": "@slowwalks",
                              "title": "Slow Walks", "subscriber_count": 312000, "raw": None})
        tr = FakeTransport(fixture("channels_list_handle.json"))
        fetch.record_info(self.store, fixture("info_long.json"), transport=tr)
        self.assertEqual(len(tr.calls), 1)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM channel")["n"], 1)


OCR = [{"t": 0.0, "text": []}, {"t": 0.5, "text": [{"s": "ALFAMA", "conf": 0.95, "h": 0.07}]}]


def win(*windows):
    return {"windows": [{"start_s": 10.0 * i, "language": lang, "probability": p, "no_speech_prob": ns}
                        for i, (lang, p, ns) in enumerate(windows)]}


class FakeAdapters(fetch.Adapters):
    """yt-dlp, stable-ts, proxy, Shot log and OCR that write fixture files and count their calls."""

    def __init__(self, transport, info=None, transcript=None):
        self.calls = []
        self.info = info or fixture("info_long.json")
        self.transcript = transcript or fixture("transcript_long.json")
        super().__init__(extract=self._extract, download=self._download, transcribe=self._transcribe,
                         proxy=self._proxy, shotlog=self._shotlog, ocr=self._ocr, transport=transport,
                         captions=self._captions)

    def _extract(self, url):
        self.calls.append(("extract", url))
        return dict(self.info)

    def _download(self, url, ref_dir, video_id):
        self.calls.append(("download", url))
        ref_dir.mkdir(parents=True, exist_ok=True)
        (ref_dir / f"{video_id}.mp4").write_bytes(b"media")
        return dict(self.info)

    def _captions(self, info, ref_dir, video_id, language):
        self.calls.append(("captions", language))
        names = [f"{video_id}.subs.{language}.vtt", f"{video_id}.auto.{language}.vtt"]
        for n in names:
            (ref_dir / n).write_text("WEBVTT\n")
        return names

    def _transcribe(self, media, language):
        self.calls.append(("transcribe", language))
        return dict(self.transcript)

    def _proxy(self, media, dest, force):
        made = force or not dest.exists()
        self.calls.append(("proxy", made))
        dest.write_bytes(b"proxy")
        return {"status": "made" if made else "skipped (fresh)", "proxy_path": str(dest), "error": None}

    def _shotlog(self, proxy, media, transcript):
        self.calls.append(("shotlog", transcript["language"]))
        return fixture("shotlog_long.json")

    def _ocr(self, media):
        self.calls.append(("ocr", media.name))
        return OCR

    def names(self):
        return [c[0] for c in self.calls]


class FetchTest(StoreCase):
    URL = "https://youtu.be/dQw4w9WgXcQ"

    def setUp(self):
        super().setUp()
        self.root = Path(self.tmp.name) / "footage"
        self.fake = FakeAdapters(FakeTransport(fixture("channels_list_handle.json")))

    def run_fetch(self, ref=URL, **kw):
        return fetch.fetch(self.store, ref, adapters=self.fake, root=self.root, **kw)

    def test_the_shot_log_names_its_media_relative_to_the_reference_folder(self):
        def with_path(proxy, media, transcript):
            out = fixture("shotlog_long.json")
            out["clip"]["path"] = str(media)
            return out
        self.fake.shotlog = with_path
        self.run_fetch()
        saved = json.loads((self.root / "references" / "_adhoc" / "dQw4w9WgXcQ" / "shotlog.json").read_text())
        self.assertEqual(saved["clip"]["path"], "dQw4w9WgXcQ.mp4")

    def test_a_first_fetch_lays_every_artifact_into_the_adhoc_reference_folder_and_saves_the_measured_card(self):
        got = self.run_fetch()
        ref = self.root / "references" / "_adhoc" / "dQw4w9WgXcQ"
        self.assertEqual(Path(got["dir"]), ref)
        self.assertEqual(sorted(p.name for p in ref.iterdir()),
                         ["card.json", "dQw4w9WgXcQ.auto.en.vtt", "dQw4w9WgXcQ.mp4", "dQw4w9WgXcQ.subs.en.vtt",
                          "info.json", "ocr.json", "proxy.mp4", "shotlog.json", "transcript.json"])
        self.assertEqual(self.fake.names(), ["download", "transcribe", "captions", "proxy", "shotlog", "ocr"])
        self.assertEqual(got["captions"], ["dQw4w9WgXcQ.auto.en.vtt", "dQw4w9WgXcQ.subs.en.vtt"])
        self.assertEqual(got["steps"]["captions"], "made")
        self.assertIn(("transcribe", "en"), self.fake.calls)
        saved = json.loads((ref / "card.json").read_text())
        self.assertEqual(saved["schema"], "cf-reference-card/1")
        self.assertIsNone(saved["analysis"])
        self.assertEqual((saved["measured"]["cut_count"], saved["measured"]["first_text_s"]), (4, 0.5))
        self.assertEqual(got["card"], saved)
        self.assertEqual(self.store.query("SELECT has_media, has_transcript FROM video"),
                         [{"has_media": 1, "has_transcript": 1}])

    def test_fetching_again_refreshes_the_info_but_neither_downloads_nor_transcribes_nor_reanalyses(self):
        self.run_fetch()
        self.fake.calls.clear()
        got = self.run_fetch("dQw4w9WgXcQ")
        self.assertEqual(self.fake.calls, [("extract", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"), ("proxy", False)])
        self.assertEqual(got["steps"]["media"], "kept")
        self.assertEqual((got["steps"]["transcript"], got["steps"]["captions"]), ("kept", "kept"))
        self.assertEqual(len(got["captions"]), 2)
        self.assertEqual(got["card"]["measured"]["spoken_hook"], "So this is Alfama, the oldest part of Lisbon.")

    def test_force_downloads_transcribes_and_analyses_again(self):
        self.run_fetch()
        self.fake.calls.clear()
        self.run_fetch(force=True)
        self.assertEqual(self.fake.names(), ["download", "transcribe", "captions", "proxy", "shotlog", "ocr"])

    def test_a_watchlist_names_the_folder_but_adds_no_membership(self):
        wl.create(self.store, "lisbon-walks", format_id="walk_reel", language="pt")
        got = self.run_fetch(watchlist="lisbon-walks")
        self.assertEqual(Path(got["dir"]), self.root / "references" / "lisbon-walks" / "dQw4w9WgXcQ")
        self.assertEqual(self.store.query("SELECT * FROM watchlist_channel"), [])

    def test_the_video_language_from_the_info_wins_over_the_watchlist_language(self):
        wl.create(self.store, "city-deep-dive", format_id="walk_reel", language="en")
        self.fake.info = fixture("info_long.json") | {"language": "ru"}
        self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}
        got = self.run_fetch(watchlist="city-deep-dive")
        self.assertIn(("transcribe", "ru"), self.fake.calls)
        self.assertIn(("captions", "ru"), self.fake.calls)
        self.assertNotIn(("transcribe", "en"), self.fake.calls)
        self.assertEqual((got["language"], got["language_source"]), ("ru", "info"))
        self.assertEqual(got["card"]["measured"]["language_source"], "info")
        saved = json.loads((Path(got["dir"]) / "transcript.json").read_text())
        self.assertEqual((saved["language"], saved["_language_source"]), ("ru", "info"))

    def test_a_regional_info_language_is_reduced_to_its_base_code(self):
        self.fake.info = fixture("info_long.json") | {"language": "pt-BR"}
        self.run_fetch()
        self.assertIn(("transcribe", "pt"), self.fake.calls)
        self.assertIn(("captions", "pt"), self.fake.calls)

    def test_without_an_info_language_whisper_detects_it_and_the_captions_follow_the_detection(self):
        wl.create(self.store, "city-deep-dive", format_id="walk_reel", language="en")
        for missing in (None, "", "not a language"):
            with self.subTest(missing=missing):
                self.fake.calls.clear()
                self.fake.info = fixture("info_long.json") | {"language": missing}
                self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}
                got = self.run_fetch(watchlist="city-deep-dive", force=True)
                self.assertIn(("transcribe", None), self.fake.calls)
                self.assertIn(("captions", "ru"), self.fake.calls)
                self.assertEqual((got["language"], got["language_source"]), ("ru", "whisper"))

    def test_the_watchlist_language_is_only_the_caption_fallback_when_nothing_names_the_language(self):
        wl.create(self.store, "lisbon-walks", format_id="walk_reel", language="pt")
        self.fake.info = fixture("info_long.json") | {"language": None}
        self.fake.transcript = fixture("transcript_long.json") | {"language": None}
        got = self.run_fetch(watchlist="lisbon-walks")
        self.assertIn(("transcribe", None), self.fake.calls)
        self.assertIn(("captions", "pt"), self.fake.calls)
        self.assertEqual((got["language"], got["language_source"]), ("pt", "watchlist"))

    def test_codes_whisper_does_not_know_leave_the_language_to_detection_and_legacy_aliases_are_mapped(self):
        supported = frozenset({"en", "ru", "he", "id", "jw", "tl", "ro"})
        for code, want in (("und", None), ("zxx", None), ("mul", None), ("xx", None), ("iw", "he"),
                           ("in", "id"), ("jv", "jw"), ("fil", "tl"), ("mo", "ro"), ("ru-RU", "ru")):
            with self.subTest(code=code):
                self.assertEqual(fetch.info_language({"language": code}, supported), want)
        self.assertEqual(fetch.info_language({"language": "und"}), None)
        self.assertEqual(fetch.transcript_language({"language": "xx"}, supported), (None, "whisper"))

    def test_an_unsupported_info_language_is_not_passed_to_the_transcriber(self):
        self.fake.languages = lambda: frozenset({"en", "ru"})
        self.fake.info = fixture("info_long.json") | {"language": "fil"}
        self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}
        got = self.run_fetch()
        self.assertIn(("transcribe", None), self.fake.calls)
        self.assertEqual((got["language"], got["language_source"]), ("ru", "whisper"))

    def test_measured_language_agrees_with_the_returned_language_and_its_source(self):
        wl.create(self.store, "lisbon-walks", format_id="walk_reel", language="pt")
        self.fake.info = fixture("info_long.json") | {"language": None}
        self.fake.transcript = fixture("transcript_long.json") | {"language": None}
        got = self.run_fetch(watchlist="lisbon-walks")
        m = got["card"]["measured"]
        self.assertEqual((m["language"], m["language_source"]), (got["language"], got["language_source"]))
        self.assertEqual((m["language"], m["language_source"]), ("pt", "watchlist"))

    def test_a_kept_transcript_without_a_language_is_labelled_with_the_fallback_not_the_transcript(self):
        self.fake.transcript = fixture("transcript_long.json") | {"language": None}
        self.run_fetch()
        tr = self.root / "references" / "_adhoc" / "dQw4w9WgXcQ" / "transcript.json"
        data = json.loads(tr.read_text())
        data.pop("_language_source")
        data.pop("_language")
        tr.write_text(json.dumps(data))
        got = self.run_fetch()
        self.assertEqual(got["steps"]["transcript"], "kept")
        self.assertEqual((got["language"], got["language_source"]), ("en", "default"))
        self.assertEqual(got["card"]["measured"]["language_source"], "default")

    def test_captions_of_another_language_than_the_transcript_are_removed(self):
        first = self.run_fetch()
        ref = Path(first["dir"])
        (ref / "dQw4w9WgXcQ.auto.ru-orig.vtt").write_text("WEBVTT\n")
        self.fake.info = fixture("info_long.json") | {"language": "ru"}
        self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}
        got = self.run_fetch(retranscribe=True)
        self.assertEqual(got["captions"], ["dQw4w9WgXcQ.auto.ru-orig.vtt", "dQw4w9WgXcQ.auto.ru.vtt",
                                           "dQw4w9WgXcQ.subs.ru.vtt"])
        self.assertEqual(sorted(p.name for p in ref.glob("*.vtt")), got["captions"])

    def test_whisper_hearing_another_language_than_the_info_overrides_it_and_the_info_is_recorded(self):
        wl.create(self.store, "city-deep-dive", format_id="walk_reel", language="en")
        self.fake.info = fixture("info_long.json") | {"language": "ru"}
        self.fake.transcript = fixture("transcript_long.json") | {"language": "en"}
        self.fake.detect = lambda media: self.fake.calls.append(("detect", media.name)) or win(("en", 0.93, 0.1), ("en", 0.97, 0.3))
        got = self.run_fetch(watchlist="city-deep-dive")
        self.assertEqual(self.fake.names()[:3], ["download", "detect", "transcribe"])
        self.assertIn(("transcribe", "en"), self.fake.calls)
        self.assertEqual((got["language"], got["language_source"]), ("en", "whisper"))
        saved = json.loads((Path(got["dir"]) / "transcript.json").read_text())
        self.assertEqual(saved["_info_language"], "ru")
        self.assertEqual(saved["_language_detection"]["verdict"], "overrides the info (ru -> en)")
        self.fake.calls.clear()
        again = self.run_fetch(watchlist="city-deep-dive")
        self.assertEqual(again["steps"]["transcript"], "kept")

    def test_an_unsure_or_agreeing_detection_keeps_the_info_language(self):
        wl.create(self.store, "city-deep-dive", format_id="walk_reel", language="en")
        self.fake.info = fixture("info_long.json") | {"language": "ru"}
        self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}
        for det, why in ((win(("en", 0.6, 0.1)), "ignored: not sure enough (en at 0.60)"),
                         (win(("ru", 0.99, 0.1)), "agrees with the info"),
                         (win(("en", 0.99, 0.9), ("en", 0.98, 0.65)), "ignored: no speech in the detection windows"),
                         (win(("en", 0.99, 0.1), ("de", 0.95, 0.2)), "ignored: the windows disagree (de, en)"),
                         (win(("en", 0.99, 0.1), ("ru", 0.95, 0.2)), "ignored: the windows disagree (en, ru)"),
                         (None, "no detection (no audio)")):
            with self.subTest(why=why):
                self.fake.calls.clear()
                self.fake.detect = lambda media, det=det: det
                got = self.run_fetch(watchlist="city-deep-dive", force=True)
                self.assertIn(("transcribe", "ru"), self.fake.calls)
                self.assertEqual(got["language_source"], "info")
                saved = json.loads((Path(got["dir"]) / "transcript.json").read_text())
                self.assertEqual(saved["_language_detection"]["verdict"], why)

    def test_a_window_without_speech_does_not_count_against_one_with_speech(self):
        self.assertEqual(fetch.detection_verdict(win(("en", 0.99, 0.1), ("ru", 0.99, 0.8)), "ru"),
                         ("en", "overrides the info (ru -> en)"))

    def test_a_failing_detection_keeps_the_info_language_and_the_fetch_goes_on(self):
        wl.create(self.store, "city-deep-dive", format_id="walk_reel", language="en")
        self.fake.info = fixture("info_long.json") | {"language": "ru"}
        self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}

        def broken(media):
            raise RuntimeError("model download failed")
        self.fake.detect = broken
        got = self.run_fetch(watchlist="city-deep-dive")
        self.assertIn(("transcribe", "ru"), self.fake.calls)
        self.assertEqual((got["language"], got["language_source"], got["steps"]["transcript"]),
                         ("ru", "info", "made (ru from info; detection failed: model download failed)"))
        saved = json.loads((Path(got["dir"]) / "transcript.json").read_text())
        self.assertEqual(saved["_language_detection"], {"error": "model download failed"})

    def test_the_info_is_checked_even_when_it_matches_the_watchlist_and_the_verdict_is_in_the_step(self):
        wl.create(self.store, "city-deep-dive", format_id="walk_reel", language="EN-us")
        self.fake.detect = lambda media: self.fake.calls.append(("detect", media.name)) or win(("ru", 0.97, 0.2), ("ru", 0.95, 0.4))
        self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}
        got = self.run_fetch(watchlist="city-deep-dive")
        self.assertIn("detect", self.fake.names())
        self.assertEqual((got["language"], got["language_source"]), ("ru", "whisper"))
        self.assertEqual(got["steps"]["transcript"], "made (ru from whisper; detection overrides the info (en -> ru))")

    def test_the_transcript_step_names_the_language_and_the_detection_verdict(self):
        self.fake.info = fixture("info_long.json") | {"language": "ru"}
        self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}
        self.assertEqual(self.run_fetch()["steps"]["transcript"], "made (ru from info)")
        self.fake.detect = lambda media: win(("en", 0.99, 0.9), ("en", 0.98, 0.7))
        self.assertEqual(self.run_fetch(force=True)["steps"]["transcript"],
                         "made (ru from info; detection ignored: no speech in the detection windows)")

        def broken(media):
            raise RuntimeError("boom")
        self.fake.detect = broken
        self.assertEqual(self.run_fetch(force=True)["steps"]["transcript"], "made (ru from info; detection failed: boom)")

    def test_a_window_counts_as_speech_below_a_no_speech_probability_of_0_6(self):
        self.assertEqual(fetch.detection_verdict(win(("en", 0.99, 0.55)), "ru")[0], "en")
        self.assertEqual(fetch.detection_verdict(win(("en", 0.99, 0.6)), "ru"),
                         (None, "ignored: no speech in the detection windows"))

    def test_the_watchlist_hint_is_normalized_and_an_unsupported_one_falls_back_to_english(self):
        self.fake.info = fixture("info_long.json") | {"language": None}
        self.fake.transcript = fixture("transcript_long.json") | {"language": None}
        for wl_lang, want in (("pt-BR", "pt"), ("iw", "he"), ("xx", "en")):
            with self.subTest(wl_lang=wl_lang):
                name = f"w-{wl_lang.lower()}"
                wl.create(self.store, name, format_id="walk_reel", language=wl_lang)
                self.fake.languages = lambda: frozenset({"en", "pt", "he"})
                got = fetch.fetch(self.store, self.URL, adapters=self.fake, root=Path(self.tmp.name) / name,
                                  watchlist=name)
                self.assertEqual((got["language"], got["language_source"]), (want, "watchlist"))

    def test_the_fallback_language_is_kept_in_the_transcript_so_another_watchlist_does_not_flip_it(self):
        wl.create(self.store, "lisbon-walks", format_id="walk_reel", language="pt")
        wl.create(self.store, "city-deep-dive", format_id="walk_reel", language="ru")
        self.fake.info = fixture("info_long.json") | {"language": None}
        self.fake.transcript = fixture("transcript_long.json") | {"language": None}
        self.run_fetch(watchlist="lisbon-walks")
        got = self.run_fetch(watchlist="city-deep-dive")
        self.assertEqual(got["steps"]["transcript"], "kept")
        self.assertEqual((got["language"], got["language_source"]), ("pt", "watchlist"))

    def test_the_supported_languages_are_not_asked_for_when_the_transcript_is_kept(self):
        self.run_fetch()
        self.fake.languages = lambda: self.fail("languages must not be loaded")
        got = self.run_fetch()
        self.assertEqual(got["steps"]["transcript"], "kept")

    def test_a_retranscribe_flags_an_analysis_whose_spoken_hook_left_the_transcript(self):
        self.run_fetch()
        with self.store.transaction() as c:
            c.execute("UPDATE card SET analysis = ?", (json.dumps({"hook": {"spoken_hook": "So this is Alfama"}}),))
        got = self.run_fetch(retranscribe=True)
        self.assertEqual(got["steps"]["analysis"], "kept; hook.spoken_hook found in the new transcript")
        with self.store.transaction() as c:
            c.execute("UPDATE card SET analysis = ?", (json.dumps({"hook": {"spoken_hook": "Not said at all"}}),))
        got = self.run_fetch(retranscribe=True)
        self.assertTrue(got["steps"]["analysis"].startswith("kept; stale: hook.spoken_hook not found in the transcript"),
                        got["steps"]["analysis"])
        self.assertTrue(got["steps"]["analysis"].endswith("re-run analyze-reference"))
        self.assertEqual(got["card"]["analysis"], {"hook": {"spoken_hook": "Not said at all"}})
        self.assertEqual(self.run_fetch()["steps"]["analysis"], "kept")

    def test_a_kept_transcript_in_another_language_than_the_video_says_to_retranscribe(self):
        self.run_fetch()
        self.fake.info = fixture("info_long.json") | {"language": "ru"}
        self.fake.calls.clear()
        got = self.run_fetch()
        self.assertNotIn("transcribe", self.fake.names())
        self.assertEqual(got["steps"]["transcript"], "kept (in en, the video is in ru: fetch --retranscribe)")

    def test_retranscribe_keeps_the_media_and_the_analysis_and_redoes_transcript_captions_and_shot_log(self):
        first = self.run_fetch()
        ref = Path(first["dir"])
        with self.store.transaction() as c:
            c.execute("UPDATE card SET analysis = ?", (json.dumps({"summary": "kept"}),))
        (ref / "analysis.json").write_text('{"summary": "kept"}')
        self.fake.info = fixture("info_long.json") | {"language": "ru"}
        self.fake.transcript = fixture("transcript_long.json") | {"language": "ru"}
        self.fake.calls.clear()
        got = self.run_fetch(retranscribe=True)
        self.assertEqual(self.fake.names(), ["extract", "transcribe", "captions", "proxy", "shotlog"])
        self.assertIn(("transcribe", "ru"), self.fake.calls)
        self.assertEqual(got["steps"]["media"], "kept")
        self.assertEqual((got["steps"]["transcript"], got["steps"]["ocr"]), ("made (ru from info)", "kept"))
        self.assertEqual(got["card"]["analysis"], {"summary": "kept"})
        self.assertEqual(got["card"]["measured"]["language"], "ru")
        self.assertEqual((ref / "analysis.json").read_text(), '{"summary": "kept"}')
        self.assertEqual(json.loads((ref / "card.json").read_text())["analysis"], {"summary": "kept"})

    def test_a_refetch_under_another_watchlist_reuses_the_existing_folder_without_moving_it(self):
        wl.create(self.store, "lisbon-walks", format_id="walk-reel", language="pt")
        first = self.run_fetch()
        self.fake.calls.clear()
        got = self.run_fetch(watchlist="lisbon-walks")
        self.assertEqual(got["dir"], first["dir"])
        self.assertEqual((got["steps"]["media"], got["steps"]["transcript"]), ("kept", "kept"))
        self.assertNotIn("download", self.fake.names())
        self.assertNotIn("transcribe", self.fake.names())
        self.assertEqual([p.name for p in (self.root / "references").iterdir()], ["_adhoc"])

    def test_an_adhoc_refetch_finds_the_folder_of_a_watchlist(self):
        wl.create(self.store, "lisbon-walks", format_id="walk-reel")
        first = self.run_fetch(watchlist="lisbon-walks")
        self.fake.calls.clear()
        got = self.run_fetch()
        self.assertEqual(got["dir"], first["dir"])
        self.assertNotIn("download", self.fake.names())
        self.assertFalse((self.root / "references" / "_adhoc").exists())

    def test_captions_that_fail_to_download_do_not_stop_the_fetch(self):
        def broken(info, ref_dir, video_id, language):
            raise fetch.FetchError("yt-dlp: HTTP Error 429")
        self.fake.captions = broken
        got = self.run_fetch()
        self.assertEqual((got["steps"]["captions"], got["captions"]), ("FAILED: yt-dlp: HTTP Error 429", []))
        self.assertIsNotNone(got["card"])

    def test_a_failed_proxy_still_saves_a_card_without_the_shot_log_part(self):
        self.fake.proxy = lambda media, dest, force: {"status": "FAILED", "proxy_path": None, "error": "boom"}
        got = self.run_fetch()
        self.assertEqual(got["steps"]["proxy"], "FAILED: boom")
        self.assertIsNone(got["card"]["measured"]["cut_count"])
        self.assertEqual(got["card"]["measured"]["speech_onset_s"], 0.62)


class CaptionLangsTest(unittest.TestCase):
    ASR = "https://www.youtube.com/api/timedtext?v=x&kind=asr&lang=ru&fmt=vtt"

    def info(self, *keys):
        auto = {}
        for k in keys:
            url = self.ASR if k in ("ru", "ru-orig", "iw-orig") else self.ASR + f"&tlang={k}"
            auto[k] = [{"ext": "vtt", "url": url}]
        return {"automatic_captions": auto}

    def test_auto_captions_prefer_the_original_track_and_never_take_a_translation(self):
        from cf.research import ytdlp
        info = self.info("ru-orig", "ru", "en", "de")
        self.assertEqual(ytdlp.caption_langs(info, "ru")["auto"], [r"ru\-orig"])
        self.assertEqual(ytdlp.caption_langs(self.info("ru", "en"), "ru")["auto"], ["ru"])
        self.assertEqual(ytdlp.caption_langs(info, "en")["auto"], [])
        self.assertEqual(ytdlp.caption_langs({}, "en")["auto"], [])

    def test_subtitles_and_auto_captions_are_asked_for_under_the_youtube_alias_too(self):
        from cf.research import ytdlp
        self.assertEqual(ytdlp.caption_codes("he"), ["he", "iw"])
        self.assertEqual(ytdlp.caption_codes("jw"), ["jw", "jv"])
        langs = ytdlp.caption_langs(self.info("iw-orig", "en"), "he")
        self.assertEqual(langs["subs"], [r"he(-[\w-]+)?", r"iw(-[\w-]+)?"])
        self.assertEqual(langs["auto"], [r"iw\-orig"])


class FetchCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        (Path(self.tmp.name) / "footage").mkdir()
        st.open_store(Path(self.tmp.name) / "f.db", seed=False, create=True).close()
        self.fake = FakeAdapters(FakeTransport(fixture("channels_list_handle.json")))

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        env = {"CF_SHARED_ROOT": str(Path(self.tmp.name) / "footage")}
        with mock.patch.dict(os.environ, env), mock.patch.object(fetch, "default_adapters", lambda: self.fake), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*argv, "--db", str(Path(self.tmp.name) / "f.db")])
        return code, out.getvalue(), err.getvalue()

    def test_fetch_json_reports_the_folder_the_steps_and_the_measured_card(self):
        code, out, err = self.run_cli("fetch", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "--json")
        self.assertEqual(code, 0, err)
        got = json.loads(out)
        self.assertEqual(got["video_id"], "dQw4w9WgXcQ")
        self.assertTrue(got["dir"].endswith("footage/references/_adhoc/dQw4w9WgXcQ"))
        self.assertEqual(got["steps"]["media"], "downloaded")
        self.assertEqual(got["card"]["measured"]["cuts_per_min"], 2.0)

    def test_fetch_prints_a_russian_summary_and_force_is_accepted(self):
        self.run_cli("fetch", "dQw4w9WgXcQ")
        code, out, err = self.run_cli("fetch", "dQw4w9WgXcQ", "--force")
        self.assertEqual(code, 0, err)
        self.assertIn("Склеек", out)
        self.assertIn("So this is Alfama", out)

    def test_a_stale_analysis_is_called_out_in_the_summary(self):
        import sqlite3
        self.run_cli("fetch", "dQw4w9WgXcQ")
        with sqlite3.connect(Path(self.tmp.name) / "f.db") as c:
            c.execute("UPDATE card SET analysis = ?", (json.dumps({"hook": {"spoken_hook": "Not said"}}),))
        code, out, err = self.run_cli("fetch", "dQw4w9WgXcQ", "--retranscribe")
        self.assertEqual(code, 0, err)
        self.assertIn("Анализ устарел: kept; stale: hook.spoken_hook", out)

    def test_retranscribe_is_accepted_and_does_not_download(self):
        self.run_cli("fetch", "dQw4w9WgXcQ")
        self.fake.calls.clear()
        code, out, err = self.run_cli("fetch", "dQw4w9WgXcQ", "--retranscribe", "--json")
        self.assertEqual(code, 0, err)
        self.assertNotIn("download", self.fake.names())
        self.assertIn("transcribe", self.fake.names())
        self.assertEqual(json.loads(out)["language_source"], "info")

    def test_a_bad_reference_is_one_error_line_and_exit_1(self):
        code, out, err = self.run_cli("fetch", "https://www.youtube.com/@slowwalks")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("error: not a YouTube video URL"), err)


if __name__ == "__main__":
    unittest.main()
