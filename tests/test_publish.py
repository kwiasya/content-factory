"""cf.publish: Instagram queue, YouTube Shorts playlist folders, the Shorts text, older copies to the Trash."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf import publish as pub


class PublishTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.root, self.trash = base / "ready", base / "Trash"
        self.reel = base / "videos" / "r"
        (self.reel / "out").mkdir(parents=True)
        self.script = {"title": "Пляж — колечко", "caption": "manifested it. literally 👌",
                       "hashtags": ["#beachday", "#Shorts"], "location_tag": "Praia"}
        self._write_script()
        real_trash = pub._to_trash
        trashed = lambda p: real_trash(p, self.trash)  # noqa: E731
        self.patches = [mock.patch.object(pub, "_orientation", return_value="вертикаль"),
                        mock.patch.object(pub, "_duration_s", return_value=9.0),
                        mock.patch.object(pub, "_to_trash", side_effect=trashed)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self._tmp.cleanup()

    def _write_script(self):
        (self.reel / "script.json").write_text(json.dumps(self.script, ensure_ascii=False))

    def _render(self, *names):
        for n in names:
            (self.reel / "out" / n).write_bytes(n.encode())

    def test_instagram_goes_to_queue_with_no_music_file(self):
        self._render("r.mp4", "r.ambience.mp4")
        video, txt = pub.publish(self.reel, self.root)
        self.assertEqual(video, self.root / "Instagram" / "Очередь" / "Пляж — колечко (вертикаль).mp4")
        self.assertEqual(video.read_bytes(), b"r.ambience.mp4")
        self.assertEqual(txt.name, "Пляж — колечко — подпись к посту.txt")
        self.assertIn("Геотег: Praia", txt.read_text())

    def test_instagram_trashes_old_copies_in_queue_posted_and_flat_root(self):
        self._render("r.mp4")
        posted = self.root / "Instagram" / "Выложено"
        posted.mkdir(parents=True)
        (posted / "Пляж — колечко (вертикаль).mp4").write_bytes(b"old")
        (self.root / "Пляж — колечко — подпись к посту.txt").write_text("old")
        sibling = posted / "Пляж — колечко (с текстом) (вертикаль).mp4"
        sibling.write_bytes(b"other title")
        pub.publish(self.reel, self.root)
        self.assertFalse((posted / "Пляж — колечко (вертикаль).mp4").exists())
        self.assertFalse((self.root / "Пляж — колечко — подпись к посту.txt").exists())
        self.assertTrue(sibling.exists())
        self.assertEqual(sorted(p.name for p in self.trash.iterdir()),
                         ["Пляж — колечко (вертикаль).mp4", "Пляж — колечко — подпись к посту.txt"])

    def test_shorts_needs_a_music_render(self):
        self._render("r.mp4")  # main render without an .ambience one: no proof it has music
        with self.assertRaises(SystemExit):
            pub.publish(self.reel, self.root, platform="shorts", playlist="Travel Memes")

    def test_shorts_needs_a_known_playlist(self):
        self._render("r.shorts.mp4")
        with self.assertRaises(SystemExit):
            pub.publish(self.reel, self.root, platform="shorts")
        with self.assertRaises(SystemExit):
            pub.publish(self.reel, self.root, platform="shorts", playlist="Очередь")

    def test_shorts_goes_to_playlist_from_script_and_moves_between_playlists(self):
        self._render("r.mp4", "r.shorts.mp4", "r.shorts.normalized.mp4")
        self.script["youtube_playlist"] = "City Walks"
        self._write_script()
        video, txt = pub.publish(self.reel, self.root, platform="shorts")
        self.assertEqual(video, self.root / "YouTube Shorts" / "City Walks" / "Пляж — колечко (shorts).mp4")
        self.assertEqual(video.read_bytes(), b"r.shorts.normalized.mp4")
        self.assertEqual(txt.name, "Пляж — колечко — shorts.txt")
        video2, _ = pub.publish(self.reel, self.root, platform="shorts", playlist="Travel Memes")
        self.assertEqual(video2.parent.name, "Travel Memes")
        self.assertFalse(video.exists())
        self.assertFalse((self.root / "Instagram").exists())

    def test_shorts_main_render_counts_as_music_when_ambience_exists(self):
        self._render("r.normalized.mp4", "r.ambience.normalized.mp4")
        video, _ = pub.publish(self.reel, self.root, platform="shorts", playlist="Day In My Life")
        self.assertEqual(video.read_bytes(), b"r.normalized.mp4")

    def test_shorts_text(self):
        text = pub.shorts_text(self.script, "Europe Travel Vlogs")
        self.assertIn("Плейлист: Europe Travel Vlogs", text)
        self.assertIn("manifested it. literally 👌", text)
        self.assertTrue(text.rstrip().endswith("#beachday #Shorts"))  # #shorts not repeated
        self.script.update(youtube_title="x " * 80, youtube_description="Longer text for YouTube")
        text = pub.shorts_text(self.script)
        title = text.split("\n")[1]
        self.assertLessEqual(len(title), pub.YT_TITLE_MAX)
        self.assertTrue(title.endswith("…"))
        self.assertIn("Longer text for YouTube", text)
        self.assertNotIn("manifested", text)
        self.assertNotIn("Плейлист", text)


class ShortsLoudnessRuleTest(unittest.TestCase):
    def test_shorts_cut_is_checked_as_music(self):
        from cf import render_check as rc

        self.assertTrue(rc.music_cut(Path("out/meme-x.shorts.mp4")))
        self.assertTrue(rc.music_cut(Path("out/meme-x.shorts.normalized.mp4")))
        self.assertFalse(rc.music_cut(Path("out/meme-x.mp4")))


if __name__ == "__main__":
    unittest.main()
