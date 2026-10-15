"""Desk research contour API through the FastAPI TestClient on a temporary db and root."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

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
        self.client = TestClient(create_app(base / "repo", local_root=self.footage, db_path=self.db,
                                            web_dist=base / "dist"))

    def get(self, url: str, expect: int = 200, **params):
        r = self.client.get(url, params=params)
        self.assertEqual(r.status_code, expect, r.text)
        return r.json()

    def send(self, method: str, url: str, expect: int = 200, body=None):
        r = self.client.request(method, url, json=body)
        self.assertEqual(r.status_code, expect, r.text)
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
        got = self.get("/api/contour/watchlists/nowhere", 404)
        self.assertIn("nowhere", got["detail"])
        self.assertEqual((got["code"], got["params"]), ("watchlist_not_found", {"name": "nowhere"}))


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
        got = self.get("/api/contour/watchlists/lisbon/feed", 422, kind="huge")
        self.assertEqual((got["code"], got["params"]), ("feed_kind_invalid", {"kind": "huge"}))
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
        unknown = self.get("/api/contour/cards/nope0000000", 404)
        self.assertEqual((unknown["code"], unknown["params"]), ("reference_not_found", {"id": "nope0000000"}))
        bare = self.get(f"/api/contour/cards/{V3}", 404)
        self.assertIn("fetch", bare["detail"])
        self.assertEqual((bare["code"], bare["params"]),
                         ("card_missing", {"id": V3, "command": f"python -m cf.research fetch {V3}"}))


class SummaryTest(ContourCase):
    def test_hooks_summary_groups_carded_references_and_lists_uncarded_outliers(self):
        got = self.get("/api/contour/watchlists/lisbon/summary/hooks")
        self.assertEqual((got["summary"], got["days"], got["carded"]), ("hooks", 14, 1))
        self.assertEqual((got["weight"], got["weight_code"]),
                         ("sum of Outlier scores, unscored counted as 1", "outlier_sum"))
        self.assertEqual([sec["kind"] for sec in got["sections"]], ["hook_category", "hook_formula"])
        group = got["sections"][0]["groups"][0]
        self.assertEqual((group["value"], group["count"], group["examples"][0]["external_id"]),
                         ("visual_payoff", 1, V1))
        self.assertEqual([(u["external_id"], u["measured"]) for u in got["uncarded"]], [(V2, True)])

    def test_formats_and_topics_have_their_sections(self):
        def kinds(what: str) -> list[str]:
            return [sec["kind"] for sec in self.get(f"/api/contour/watchlists/lisbon/summary/{what}")["sections"]]
        self.assertEqual(kinds("formats"), ["storytelling_format", "visual_layout"])
        self.assertEqual(kinds("topics"), ["topic"])

    def test_days_narrow_the_window(self):
        self.assertEqual(self.get("/api/contour/watchlists/lisbon/summary/topics", days=1)["carded"], 0)

    def test_an_unknown_summary_is_422_and_an_unknown_watchlist_404(self):
        got = self.get("/api/contour/watchlists/lisbon/summary/music", 422)
        self.assertEqual((got["code"], got["params"]), ("summary_invalid", {"summary": "music"}))
        self.get("/api/contour/watchlists/nowhere/summary/hooks", 404)


class IdeasTest(ContourCase):
    def statuses(self, **params) -> dict[int, str]:
        return {i["id"]: i["status"] for i in self.get("/api/contour/ideas", **params)["ideas"]}

    def test_ideas_are_listed_by_watchlist_and_status(self):
        self.assertEqual(self.statuses(), {self.briefed: "brief", self.inbox: "inbox"})
        self.assertEqual(self.statuses(watchlist="lisbon", status="inbox"), {self.inbox: "inbox"})
        self.assertEqual(self.statuses(watchlist="empty"), {})
        got = self.get("/api/contour/ideas", 422, status="maybe")
        self.assertEqual((got["code"], got["params"]), ("idea_status_invalid", {"status": "maybe"}))
        self.get("/api/contour/ideas", 404, watchlist="nowhere")

    def test_shortlist_discard_and_restore_persist(self):
        moved = self.send("POST", f"/api/contour/ideas/{self.inbox}/shortlist")
        self.assertEqual(moved["status"], "shortlisted")
        with st.open_store(self.db) as s:
            self.assertEqual(ideas.get(s, self.inbox).status, "shortlisted")
        refused = self.send("POST", f"/api/contour/ideas/{self.inbox}/discard", 422)
        self.assertIn("inbox", refused["detail"])
        self.assertEqual((refused["code"], refused["params"]),
                         ("idea_move_not_allowed", {"id": self.inbox, "status": "shortlisted", "action": "discard"}))

    def test_discard_then_restore_brings_the_idea_back_to_the_inbox(self):
        self.send("POST", f"/api/contour/ideas/{self.inbox}/discard")
        self.assertEqual(self.statuses(status="discarded"), {self.inbox: "discarded"})
        self.send("POST", f"/api/contour/ideas/{self.inbox}/restore")
        self.assertEqual(self.statuses(status="inbox"), {self.inbox: "inbox"})

    def test_unknown_idea_or_action_is_404(self):
        unknown = self.send("POST", "/api/contour/ideas/999/shortlist", 404)
        self.assertEqual((unknown["code"], unknown["params"]), ("idea_not_found", {"id": 999}))
        got = self.send("POST", f"/api/contour/ideas/{self.inbox}/promote", 404)
        self.assertEqual((got["code"], got["params"]), ("idea_action_unknown", {"action": "promote"}))

    def test_a_note_is_appended_and_kept(self):
        got = self.send("PUT", f"/api/contour/ideas/{self.inbox}/notes", body={"text": "Shoot it at dawn"})
        self.assertEqual([n["text"] for n in got["notes"]], ["Shoot it at dawn"])
        with st.open_store(self.db) as s:
            self.assertEqual([n["text"] for n in ideas.get(s, self.inbox).notes], ["Shoot it at dawn"])
        empty = self.send("PUT", f"/api/contour/ideas/{self.inbox}/notes", 422, body={"text": "  "})
        self.assertEqual(empty["code"], "note_empty")


class BriefTest(ContourCase):
    def url(self, idea_id: int) -> str:
        return f"/api/contour/ideas/{idea_id}/brief"

    def test_the_brief_is_read_from_its_file_with_a_hash(self):
        got = self.get(self.url(self.briefed))
        self.assertEqual(got["path"], str(self.brief_path))
        self.assertEqual(got["text"], self.brief_path.read_text(encoding="utf-8"))
        self.assertTrue(got["hash"].startswith("sha256:"))

    def test_an_idea_without_a_brief_is_404_naming_the_command(self):
        got = self.get(self.url(self.inbox), 404)
        self.assertIn("ideas brief", got["detail"])
        self.assertEqual((got["code"], got["params"]), ("brief_missing", {
            "id": self.inbox, "command": f"python -m cf.research ideas brief {self.inbox}"}))

    def test_writing_with_the_read_hash_saves_and_a_stale_hash_is_409(self):
        h = self.get(self.url(self.briefed))["hash"]
        saved = self.send("PUT", self.url(self.briefed), body={"text": "# Brief\n\nnew\n", "hash": h})
        self.assertEqual(self.brief_path.read_text(encoding="utf-8"), "# Brief\n\nnew\n")
        self.assertNotEqual(saved["hash"], h)
        stale = self.send("PUT", self.url(self.briefed), 409, body={"text": "lost", "hash": h})
        self.assertEqual((stale["text"], stale["hash"]), ("# Brief\n\nnew\n", saved["hash"]))
        self.assertEqual(stale["code"], "brief_changed")
        self.assertEqual(self.brief_path.read_text(encoding="utf-8"), "# Brief\n\nnew\n")


    def point_brief_at(self, path) -> None:
        with st.open_store(self.db) as s:
            with s.transaction() as conn:
                conn.execute("UPDATE idea SET brief_path = ? WHERE id = ?", (str(path), self.briefed))

    def test_a_brief_path_with_dot_dot_a_symlink_or_another_suffix_is_404_and_nothing_is_written(self):
        inside = self.footage / "elsewhere.md"
        inside.write_text("# other\n")
        link = self.brief_path.parent / "link.md"
        link.symlink_to(inside)
        txt = self.brief_path.with_suffix(".txt")
        txt.write_text("# txt\n")
        dotted = self.brief_path.parent / ".." / self.brief_path.parent.name / self.brief_path.name
        for path in (dotted, link, txt):
            with self.subTest(path=str(path)):
                self.point_brief_at(path)
                self.assertEqual(self.get(self.url(self.briefed), 404)["code"], "brief_outside")
                self.send("PUT", self.url(self.briefed), 404, body={"text": "x", "hash": ""})
        self.assertEqual(inside.read_text(), "# other\n")

    def test_a_brief_missing_on_disk_is_404_naming_the_path(self):
        self.brief_path.unlink()
        got = self.get(self.url(self.briefed), 404)
        self.assertEqual((got["code"], got["params"]),
                         ("brief_file_missing", {"id": self.briefed, "path": str(self.brief_path)}))


class TaxonomyTest(ContourCase):
    PROPOSED = "/api/contour/taxonomy/editing_style/golden_hour_descent"

    def test_values_are_listed_by_kind_and_status(self):
        got = self.get("/api/contour/taxonomy", kind="editing_style", status="proposed")
        self.assertEqual([(v["value"], v["source"]) for v in got["values"]],
                         [("golden_hour_descent", f"card:{V1}")])
        self.assertIn("hook_category", got["kinds"])
        self.assertGreater(len(self.get("/api/contour/taxonomy")["values"]), 1)
        got = self.get("/api/contour/taxonomy", 422, kind="mood")
        self.assertEqual((got["code"], got["params"]), ("taxonomy_kind_invalid", {"kind": "mood"}))
        got = self.get("/api/contour/taxonomy", 422, status="maybe")
        self.assertEqual((got["code"], got["params"]), ("taxonomy_status_invalid", {"status": "maybe"}))

    def test_approve_drops_the_proposed_prefix_in_the_stored_card_and_its_file(self):
        got = self.send("POST", self.PROPOSED + "/approve")
        self.assertEqual((got["status"], got["cards"]), ("approved", [V1]))
        with st.open_store(self.db) as s:
            stored = card.load(s, card.video(s, V1)["id"])
        self.assertEqual(stored["analysis"]["visual_layout"]["sub_category"], "golden_hour_descent")
        on_disk = json.loads((self.ref / "card.json").read_text())
        self.assertEqual(on_disk["analysis"]["visual_layout"]["sub_category"], "golden_hour_descent")
        self.assertEqual(self.get(f"/api/contour/cards/{V1}")["proposed"], [])

    def test_reject_lists_the_cards_that_now_fail(self):
        got = self.send("POST", self.PROPOSED + "/reject")
        self.assertEqual((got["status"], got["cards"]), ("rejected", [V1]))
        self.assertEqual(self.get("/api/contour/taxonomy", status="proposed")["values"], [])

    def test_bad_kind_is_422_and_unknown_action_404(self):
        got = self.send("POST", "/api/contour/taxonomy/mood/calm/approve", 422)
        self.assertEqual((got["code"], got["params"]), ("taxonomy_kind_invalid", {"kind": "mood"}))
        got = self.send("POST", "/api/contour/taxonomy/editing_style/Not%20Snake/approve", 422)
        self.assertEqual((got["code"], got["params"]), ("taxonomy_value_invalid", {"value": "Not Snake"}))
        got = self.send("POST", self.PROPOSED + "/maybe", 404)
        self.assertEqual((got["code"], got["params"]), ("taxonomy_action_unknown", {"action": "maybe"}))


class QuotaTest(ContourCase):
    def test_quota_shows_today_per_bucket_and_method(self):
        got = self.get("/api/contour/quota")
        buckets = {b["bucket"]: b for b in got["buckets"]}
        self.assertEqual(set(buckets), {"default", "search", "instagram"})
        self.assertEqual({b: v["window"] for b, v in buckets.items()},
                         {"default": "day", "search": "day", "instagram": "hour"})
        self.assertEqual(buckets["default"]["remaining"], buckets["default"]["limit"] - buckets["default"]["used"])
        self.assertEqual(buckets["default"]["used"], sum(m["units"] for m in got["by_method"]))
        self.assertRegex(got["day"], r"^\d{4}-\d{2}-\d{2}$")

    def test_a_malformed_quota_override_is_422_with_the_research_message(self):
        with mock.patch.dict(os.environ, {"CF_QUOTA_DEFAULT": "lots"}):
            got = self.get("/api/contour/quota", 422)
        self.assertEqual(got["code"], "research_error")
        self.assertIn("lots", got["params"]["message"])


class InstagramTest(ContourCase):
    def test_own_reels_report_is_404_with_the_command_until_a_sync(self):
        got = self.get("/api/contour/own", 404)
        self.assertEqual((got["code"], got["params"]["command"]), ("own_missing", "python -m cf.research own sync"))

    def test_own_reels_report_after_a_sync(self):
        from cf.research import ingest
        with mock.patch.dict(os.environ, {"INSTAGRAM_USER_ID": "17841400000000099"}):
            with st.open_store(self.db) as s:
                cid = ingest.ingest_ig_account(s, {"id": "17841400000000099", "username": "kwi_asya",
                                                   "followers_count": 1742}, own=True)
                vid = ingest.ingest_ig_media(s, cid, [{"id": "1", "media_product_type": "REELS", "like_count": 5,
                                                       "timestamp": "2026-10-10T10:00:00+0000",
                                                       "permalink": "https://www.instagram.com/reel/DeOwn00001/",
                                                       "caption": "Me, close up"}])[0]
                ingest.ingest_insights(s, vid, {"views": 2043, "reach": 1571, "shares": 63, "saved": 14})
            got = self.get("/api/contour/own")
        self.assertEqual((got["handle"], got["followers"]), ("@kwi_asya", 1742))
        self.assertEqual([(r["external_id"], r["views"], r["reach"], r["shares"], r["saved"]) for r in got["reels"]],
                         [("DeOwn00001", 2043, 1571, 63, 14)])

    def test_feed_takes_a_platform(self):
        got = self.get("/api/contour/watchlists/lisbon/feed", platform="youtube")
        self.assertTrue(got["rows"])
        self.assertEqual({r["platform"] for r in got["rows"]}, {"youtube"})
        self.assertEqual(self.get("/api/contour/watchlists/lisbon/feed", platform="instagram")["rows"], [])
        got = self.get("/api/contour/watchlists/lisbon/feed", 422, platform="tiktok")
        self.assertEqual(got["code"], "feed_platform_invalid")
