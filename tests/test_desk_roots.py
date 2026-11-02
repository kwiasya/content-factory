"""Desk over two roots: References, the Library cache and the store from the shared root; Videos, Footage
and Briefs from the local root."""

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cf.desk import videos_api
from cf.desk.app import create_app
from cf.desk.problems import Problem
from cf.research import brief, card, ideas
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import CHANNEL_A, MEASURED, NOW, add_member, add_videos, analysis, fields, iso, video_item

V1 = "dQw4w9WgXcQ"


class TwoRootsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        (base / "repo").mkdir()
        self.local, self.shared = base / "local", base / "shared"
        self.local.mkdir()
        self.db = self.shared / "factory.db"
        with st.open_store(self.db, create=True) as s:
            wl.create(s, "lisbon", format_id="walk-reel", author_channel="travelwalks")
            add_member(s, "lisbon", CHANNEL_A, "@alpha")
            add_videos(s, [video_item(V1, CHANNEL_A, iso(NOW), 40, 9000)], taken_at=iso(NOW))
            self.ref = self.shared / "references" / "lisbon" / V1
            self.ref.mkdir(parents=True)
            (self.ref / "proxy.mp4").write_bytes(b"\0" * 64)
            v1 = card.video(s, V1)["id"]
            card.save(s, v1, MEASURED, path=self.ref / "card.json")
            card.save_analysis(s, v1, analysis(visual_layout__sub_category="proposed:golden_hour_descent"),
                               root=self.shared)
            self.idea = ideas.add(s, "lisbon", [V1], fields()).id
            ideas.shortlist(s, self.idea)
            self.brief = brief.create(s, self.idea, root=self.local)
        cache = self.shared / "library" / "p" / "previews"
        cache.mkdir(parents=True)
        (cache / "x.jpg").write_bytes(b"\xff\xd8\xff")
        render = self.local / "videos" / "v1" / "renders"
        render.mkdir(parents=True)
        (render / "a.mp4").write_bytes(b"\0" * 16)
        decoy = self.local / "references" / "lisbon" / "other"
        decoy.mkdir(parents=True)
        (decoy / "proxy.mp4").write_bytes(b"\0" * 16)
        self.client = TestClient(create_app(base / "repo", local_root=self.local, shared_root=self.shared,
                                            db_path=self.db, web_dist=base / "dist"))

    def media(self, path: str) -> int:
        return self.client.get("/api/media", params={"path": path}).status_code

    def test_media_comes_from_the_root_that_holds_it(self):
        self.assertEqual(self.media(f"references/lisbon/{V1}/proxy.mp4"), 200)
        self.assertEqual(self.media("library/p/previews/x.jpg"), 200)
        self.assertEqual(self.media("videos/v1/renders/a.mp4"), 200)
        self.assertEqual(self.media("references/lisbon/other/proxy.mp4"), 404)

    def test_the_card_player_and_the_brief_use_their_roots(self):
        got = self.client.get(f"/api/contour/cards/{V1}").json()
        self.assertEqual(got["media"], f"references/lisbon/{V1}/proxy.mp4")
        r = self.client.get(f"/api/contour/ideas/{self.idea}/brief")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(Path(r.json()["path"]), self.brief)
        self.assertTrue(self.brief.is_relative_to(self.local))

    def test_approving_a_value_rewrites_the_card_copy_under_the_shared_root(self):
        r = self.client.post("/api/contour/taxonomy/editing_style/golden_hour_descent/approve")
        self.assertEqual(r.status_code, 200, r.text)
        copy = json.loads((self.ref / "card.json").read_text())
        self.assertEqual(copy["analysis"]["visual_layout"]["sub_category"], "golden_hour_descent")

    def test_a_brief_of_another_person_is_not_opened_and_names_the_owner(self):
        with st.open_store(self.db, create=True) as s:
            s.conn.execute("UPDATE idea SET brief_owner = 'someone-else' WHERE id = ?", (self.idea,))
            s.conn.commit()
        r = self.client.get(f"/api/contour/ideas/{self.idea}/brief")
        self.assertEqual((r.status_code, r.json()["code"]), (404, "brief_elsewhere"), r.text)
        self.assertEqual(r.json()["params"]["owner"], "someone-else")
        with self.assertRaises(Problem) as cm:
            videos_api.linked_brief(self.local, self.db, self.idea)
        self.assertEqual(cm.exception.code, "brief_elsewhere")

    def test_meta_reports_both_roots(self):
        meta = self.client.get("/api/meta").json()
        self.assertEqual((meta["local_root"], meta["shared_root"], meta["shared_available"]),
                         (str(self.local), str(self.shared), True))


if __name__ == "__main__":
    unittest.main()
