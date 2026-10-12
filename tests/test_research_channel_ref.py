"""Reference channel input: every way the Author pastes a channel becomes a handle, id or username."""

import unittest

from cf.research.watchlist import ChannelRef, WatchlistError, parse_channel_ref

UC = "UCX6OQ3DkcsbYNE6H8uQQuVA"


class ParseChannelRefTest(unittest.TestCase):
    def test_accepted_forms(self):
        cases = {
            "@MrBeast": ChannelRef("handle", "@mrbeast"),
            "mrbeast": ChannelRef("handle", "@mrbeast"),
            "  @Fireship  ": ChannelRef("handle", "@fireship"),
            "https://www.youtube.com/@Fireship": ChannelRef("handle", "@fireship"),
            "https://youtube.com/@Fireship/videos": ChannelRef("handle", "@fireship"),
            "https://m.youtube.com/@fireship/shorts?si=abc": ChannelRef("handle", "@fireship"),
            "youtube.com/@fireship": ChannelRef("handle", "@fireship"),
            "www.youtube.com/@fireship/": ChannelRef("handle", "@fireship"),
            "https://www.youtube.com/@%D0%BA%D0%B0%D0%BD%D0%B0%D0%BB": ChannelRef("handle", "@канал"),
            UC: ChannelRef("id", UC),
            f"https://www.youtube.com/channel/{UC}": ChannelRef("id", UC),
            f"https://www.youtube.com/channel/{UC}/featured?view_as=subscriber": ChannelRef("id", UC),
            "https://www.youtube.com/user/PewDiePie": ChannelRef("username", "PewDiePie"),
            "https://www.youtube.com/c/Fireship": ChannelRef("custom", "Fireship"),
            "https://www.youtube.com/fireship": ChannelRef("handle", "@fireship"),
            "https://www.youtube.com/@abc%0A": ChannelRef("handle", "@abc"),
            f"https://www.youtube.com/channel/{UC}%0A": ChannelRef("id", UC),
            f"{UC}\n": ChannelRef("id", UC),
        }
        for text, want in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_channel_ref(text), want)

    def test_refused_forms_say_why(self):
        cases = {
            "": "empty",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "video",
            "https://youtu.be/dQw4w9WgXcQ": "video",
            "https://www.youtube.com/shorts/abcdefghijk": "video",
            "https://www.youtube.com/playlist?list=PL123": "playlist",
            "https://vimeo.com/fireship": "YouTube",
            "https://www.youtube.com/": "no channel",
            "two words": "handle",
            "https://www.youtube.com/@ab%0Acd": "handle",
            "@abc\ndef": "handle",
        }
        for text, why in cases.items():
            with self.subTest(text=text):
                with self.assertRaises(WatchlistError) as cm:
                    parse_channel_ref(text)
                self.assertIn(why, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
