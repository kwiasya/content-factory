"""Desk research contour API through the FastAPI TestClient on a temporary db and footage root."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from cf.desk.app import create_app
from cf.research import brief, card, ideas
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import CHANNEL_A, CHANNEL_B, V1, V2, V3, add_member, add_videos, analysis, fields, video_item

NOW = datetime.now(timezone.utc)
BETA = "betaHit0001"
MEASURED = {
    "duration_s": 40.0, "kind": "short", "cut_count": 8, "cuts_per_min": 12.0, "first_shot_s": 1.0,
    "first_text": "ALFAMA", "first_text_s": 0.0, "speech_onset_s": 0.2,
    "spoken_hook": "So this is Alfama, the oldest part of Lisbon.",
    "sections": [{"start_s": 0.2, "end_s": 3.1, "text": "So this is Alfama, the oldest part of Lisbon."},
                 {"start_s": 4.0, "end_s": 6.0, "text": "Watch the stairs."}],
    "chapters": [{"start_s": 0.0, "end_s": 20.0, "title": "Top"}, {"start_s": 20.0, "end_s": None, "title": "River"}],
    "heatmap_peaks": [{"start_s": 30.0, "end_s": 36.0, "value": 1.0, "quote": "Okay, sunset time."}],
    "notes": [],
}
TRANSCRIPT = {"text": "So this is Alfama, the oldest part of Lisbon. Watch the stairs. Okay, sunset time.",
              "segments": []}


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def ago(days: float = 0) -> str:
    return iso(NOW - timedelta(days=days))


class ContourCase(unittest.TestCase):
    """Watchlist lisbon: channel A with a baseline, V1 (9x, analyzed card with a proposed value, proxy),
    V2 (5x, measured card), V3 (long, unscored), channel B with one unscored short; an Idea with a Brief
    and one in the inbox."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        (base / "repo").mkdir()
        self.footage = base / "footage"
        self.db = self.footage / "factory.db"
        with st.open_store(self.db) as s:
            wl.create(s, "lisbon", format_id="walk-reel", author_channel="travelwalks", queries=["lisbon walk"])
            wl.create(s, "empty", format_id="tech-explainer")
            add_member(s, "lisbon", CHANNEL_A, "@alpha")
            add_member(s, "lisbon", CHANNEL_B, "@beta")
            add_videos(s, [video_item(f"base{i:07d}", CHANNEL_A, ago(10 + i), 40, 1000) for i in range(5)]
                       + [video_item(V1, CHANNEL_A, ago(2), 40, 9000, title="Alfama at dusk"),
                          video_item(V2, CHANNEL_A, ago(3), 40, 5000, title="Porto stairs"),
                          video_item(V3, CHANNEL_A, ago(4), 600, 3000, title="Sintra fog"),
                          video_item(BETA, CHANNEL_B, ago(1), 40, 70_000, title="Beta hit")],
                       taken_at=iso(NOW))
            self.ref = self.footage / "references" / "lisbon" / V1
            self.ref.mkdir(parents=True)
            (self.ref / "transcript.json").write_text(json.dumps(TRANSCRIPT))
            (self.ref / "proxy.mp4").write_bytes(b"\0" * 64)
            v1 = card.video(s, V1)["id"]
            card.save(s, v1, MEASURED, path=self.ref / "card.json")
            card.save_analysis(s, v1, analysis(visual_layout__sub_category="proposed:golden_hour_descent"),
                               root=self.footage)
            card.save(s, card.video(s, V2)["id"], {"duration_s": 40.0, "spoken_hook": None})
            self.briefed = ideas.add(s, "lisbon", [V1], fields()).id
            ideas.shortlist(s, self.briefed)
            self.brief_path = brief.create(s, self.briefed, root=self.footage)
            self.inbox = ideas.add(s, "lisbon", [V2], fields(title="Porto stairs at noon")).id
        self.client = TestClient(create_app(base / "repo", footage_root=self.footage, db_path=self.db,
                                            web_dist=base / "dist"))

    def get(self, url: str, status: int = 200, **params):
        r = self.client.get(url, params=params)
        self.assertEqual(r.status_code, status, r.text)
        return r.json()

    def send(self, method: str, url: str, status: int = 200, body=None):
        r = self.client.request(method, url, json=body)
        self.assertEqual(r.status_code, status, r.text)
        return r.json()


class WatchlistsTest(ContourCase):
    def test_watchlists_are_listed_with_their_channel_counts(self):
        got = {w["name"]: w for w in self.get("/api/contour/watchlists")["watchlists"]}
        self.assertEqual(set(got), {"lisbon", "empty"})
        self.assertEqual((got["lisbon"]["format_id"], got["lisbon"]["channel_count"]), ("walk-reel", 2))

    def test_a_watchlist_shows_its_channels_and_queries(self):
        got = self.get("/api/contour/watchlists/lisbon")
        self.assertEqual(got["watchlist"]["queries"], ["lisbon walk"])
        self.assertEqual(sorted(c["handle"] for c in got["channels"]), ["@alpha", "@beta"])

    def test_an_unknown_watchlist_is_404(self):
        self.assertIn("nowhere", self.get("/api/contour/watchlists/nowhere", 404)["detail"])


class FeedTest(ContourCase):
    def ids(self, **params) -> list[str]:
        return [r["external_id"] for r in self.get("/api/contour/watchlists/lisbon/feed", **params)["rows"]]

    def test_default_feed_is_the_last_30_days_best_outlier_first_with_unscored_last(self):
        got = self.get("/api/contour/watchlists/lisbon/feed")
        self.assertEqual((got["days"], got["limit"]), (30, 20))
        rows = got["rows"]
        ids = [r["external_id"] for r in rows]
        self.assertEqual(ids[:2] + ids[7:], [V1, V2, BETA, V3])
        self.assertEqual(sorted(ids[2:7]), [f"base{i:07d}" for i in range(5)])
        self.assertEqual([r["outlier"] for r in rows[7:]], [None, None])
        first = rows[0]
        self.assertEqual((first["outlier"], first["views"], first["title"], first["handle"], first["analyzed"],
                          first["candidate"]), (9.0, 9000, "Alfama at dusk", "@alpha", True, False))
        self.assertEqual(first["url"], f"https://www.youtube.com/watch?v={V1}")
        self.assertFalse(rows[1]["analyzed"])

    def test_filters_narrow_the_feed_like_the_cli(self):
        self.assertEqual(self.ids(min_outlier=2), [V1, V2])
        self.assertEqual(self.ids(min_views=4000), [V1, V2, BETA])
        self.assertEqual(self.ids(kind="long"), [V3])
        self.assertNotIn(V3, self.ids(max_duration=60))
        self.assertEqual(self.ids(limit=1), [V1])
        self.assertEqual(self.ids(days=1.5), [BETA])

    def test_an_unknown_kind_is_422_and_an_unknown_watchlist_404(self):
        self.get("/api/contour/watchlists/lisbon/feed", 422, kind="huge")
        self.get("/api/contour/watchlists/nowhere/feed", 404)


class CardTest(ContourCase):
    def test_card_carries_measured_analysis_sections_the_proxy_and_pending_values(self):
        got = self.get(f"/api/contour/cards/{V1}")
        self.assertEqual((got["reference"]["title"], got["reference"]["outlier"]), ("Alfama at dusk", 9.0))
        self.assertEqual(got["card"]["measured"]["cuts_per_min"], 12.0)
        self.assertEqual(got["card"]["measured"]["heatmap_peaks"][0]["quote"], "Okay, sunset time.")
        self.assertEqual(got["card"]["analysis"]["visual_layout"]["sub_category"], "proposed:golden_hour_descent")
        self.assertEqual([x["text"] for x in got["sections"]],
                         ["So this is Alfama, the oldest part of Lisbon.", "Watch the stairs."])
        self.assertEqual(got["media"], f"references/lisbon/{V1}/proxy.mp4")
        self.assertEqual(got["proposed"], [{"kind": "editing_style", "value": "golden_hour_descent"}])
        self.assertEqual(self.client.get("/api/media", params={"path": got["media"]}).status_code, 200)

    def test_a_measured_only_card_has_no_analysis_and_no_player(self):
        got = self.get(f"/api/contour/cards/{V2}")
        self.assertIsNone(got["card"]["analysis"])
        self.assertIsNone(got["media"])
        self.assertEqual(got["sections"], [])

    def test_unknown_reference_or_one_without_a_card_is_404(self):
        self.get("/api/contour/cards/nope0000000", 404)
        self.assertIn("fetch", self.get(f"/api/contour/cards/{V3}", 404)["detail"])
