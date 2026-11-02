"""Watchlist operations on a temp store; channels.list answered by recorded payloads, never the network."""

import json
import tempfile
import unittest
from pathlib import Path

from cf.research import hooks
from cf.research import quota
from cf.research import store as st
from cf.research import watchlist as wl

FIX = Path(__file__).parent / "fixtures" / "research"
SLOW = "UCxR9mXyZbC1dEf2GhIjKlMn"
TERM = "UCa1B2c3D4e5F6g7H8i9J0kL"


def payload(name: str) -> dict:
    return json.loads((FIX / name).read_text())


class FakeTransport:
    """Answers every Data API call with the next recorded payload and remembers the calls."""

    def __init__(self, *payloads: dict):
        self.payloads = list(payloads)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, method: str, params: dict) -> dict:
        self.calls.append((method, dict(params)))
        return self.payloads.pop(0)


class WatchlistTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = st.open_store(Path(self.tmp.name) / "f.db", create=True)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def make(self, name="claude-jobs", **kw):
        args = dict(format_id="tech_explainer", author_channel="yt-main", language="en", region="US")
        args.update(kw)
        return wl.create(self.store, name, **args)

    def default_units(self):
        return {b.bucket: b.used for b in quota.usage(self.store).buckets}["default"]

    # --- Watchlist itself -------------------------------------------------

    def test_create_and_list(self):
        self.make()
        self.make("vienna-long", format_id="travel_long", author_channel=None, language="de", region=None)
        got = {w.name: w for w in wl.list_watchlists(self.store)}
        self.assertEqual(set(got), {"claude-jobs", "vienna-long"})
        w = got["claude-jobs"]
        self.assertEqual((w.format_id, w.author_channel, w.language, w.region), ("tech_explainer", "yt-main", "en", "US"))
        self.assertEqual((w.channel_count, w.queries), (0, []))
        self.assertIsNone(got["vienna-long"].author_channel)

    def test_create_with_seed_queries(self):
        self.make(queries=["claude code job search", "ai job hunt automation"])
        self.assertEqual(wl.get(self.store, "claude-jobs").queries,
                         ["claude code job search", "ai job hunt automation"])

    def test_duplicate_name_is_refused(self):
        self.make()
        with self.assertRaises(wl.WatchlistError) as cm:
            self.make()
        self.assertIn("already exists", str(cm.exception))

    def test_names_must_work_as_folder_names(self):
        for bad in ("", "a/b", ".hidden", "two words", "trip\n", "trip\r\n"):
            with self.subTest(name=bad), self.assertRaises(wl.WatchlistError):
                self.make(bad)

    def test_names_starting_with_an_underscore_are_reserved(self):
        for bad in ("_adhoc", "_mine"):
            with self.subTest(name=bad), self.assertRaises(wl.WatchlistError) as cm:
                self.make(bad)
            self.assertIn("reserved", str(cm.exception))
        self.assertEqual(self.make("trip_2026").name, "trip_2026")

    def test_format_is_required(self):
        with self.assertRaises(wl.WatchlistError):
            self.make(format_id="")

    def test_format_id_follows_the_hook_library_rule(self):
        for bad in ("Walk Reel", "walk/reel", "-walk", "WalkReel"):
            with self.subTest(format_id=bad), self.assertRaises(wl.WatchlistError) as cm:
                self.make(format_id=bad)
            self.assertIn("lower case letters, digits, - or _", str(cm.exception))
            self.assertIn("walk-reel", str(cm.exception))
            with self.subTest(format_id=bad), self.assertRaises(hooks.HookError):
                hooks.check_format(bad)
        self.assertEqual(self.make(format_id="walk-reel").format_id, "walk-reel")

    def test_remove(self):
        self.make()
        wl.remove(self.store, "claude-jobs")
        self.assertEqual(wl.list_watchlists(self.store), [])
        with self.assertRaises(wl.WatchlistError) as cm:
            wl.remove(self.store, "claude-jobs")
        self.assertIn("no Watchlist", str(cm.exception))

    def test_queries_are_added_once(self):
        self.make()
        wl.add_query(self.store, "claude-jobs", "claude code agents")
        wl.add_query(self.store, "claude-jobs", "  claude code agents ")
        wl.add_query(self.store, "claude-jobs", "job search automation")
        self.assertEqual(wl.get(self.store, "claude-jobs").queries,
                         ["claude code agents", "job search automation"])
        with self.assertRaises(wl.WatchlistError):
            wl.add_query(self.store, "claude-jobs", "   ")

    def test_unknown_watchlist_is_named_in_the_error(self):
        with self.assertRaises(wl.WatchlistError) as cm:
            wl.add_query(self.store, "nope", "x")
        self.assertIn("nope", str(cm.exception))

    # --- Reference channels -----------------------------------------------

    def test_add_channel_by_handle(self):
        self.make()
        t = FakeTransport(payload("channels_list_handle.json"))
        ch = wl.add_channel(self.store, "claude-jobs", "@SlowWalks", transport=t)
        self.assertEqual(t.calls[0][0], "channels.list")
        self.assertEqual(t.calls[0][1].get("forHandle"), "@slowwalks")
        self.assertEqual((ch.external_id, ch.handle, ch.title), (SLOW, "@slowwalks", "Slow Walks"))
        self.assertEqual((ch.subscriber_count, ch.video_count, ch.view_count), (312_000, 418, 48_213_977))
        self.assertEqual(ch.uploads_playlist_id, "UUxR9mXyZbC1dEf2GhIjKlMn")
        self.assertFalse(ch.own)
        self.assertEqual([c.external_id for c in wl.channels(self.store, "claude-jobs")], [SLOW])
        self.assertEqual(wl.get(self.store, "claude-jobs").channel_count, 1)
        self.assertEqual(self.default_units(), 1)

    def test_add_channel_by_channel_url_asks_by_id(self):
        self.make()
        t = FakeTransport(payload("channels_list_id_hidden_subs.json"))
        ch = wl.add_channel(self.store, "claude-jobs", f"https://www.youtube.com/channel/{TERM}/videos",
                            transport=t)
        self.assertEqual(t.calls[0][1].get("id"), TERM)
        self.assertEqual(ch.handle, "@terminaltuesdays")
        self.assertIsNone(ch.subscriber_count)  # hidden by the channel

    def test_legacy_user_url_asks_by_username(self):
        self.make()
        t = FakeTransport(payload("channels_list_handle.json"))
        wl.add_channel(self.store, "claude-jobs", "https://www.youtube.com/user/SlowWalksTV", transport=t)
        self.assertEqual(t.calls[0][1].get("forUsername"), "SlowWalksTV")

    def test_custom_url_tries_the_handle_then_the_username(self):
        self.make()
        t = FakeTransport(payload("channels_list_not_found.json"), payload("channels_list_handle.json"))
        ch = wl.add_channel(self.store, "claude-jobs", "https://www.youtube.com/c/SlowWalksTV", transport=t)
        self.assertEqual([c[1].get("forHandle") for c in t.calls], ["@slowwalkstv", None])
        self.assertEqual(t.calls[1][1].get("forUsername"), "SlowWalksTV")
        self.assertEqual(ch.external_id, SLOW)
        self.assertEqual(self.default_units(), 2)

    def test_own_flag_is_kept(self):
        self.make()
        t = FakeTransport(payload("channels_list_handle.json"))
        ch = wl.add_channel(self.store, "claude-jobs", "@slowwalks", own=True, transport=t)
        self.assertTrue(ch.own)
        self.assertTrue(wl.channels(self.store, "claude-jobs")[0].own)

    def test_adding_a_known_channel_again_costs_nothing(self):
        self.make()
        self.make("second", format_id="walk_reel")
        wl.add_channel(self.store, "claude-jobs", "@slowwalks",
                       transport=FakeTransport(payload("channels_list_handle.json")))
        quiet = FakeTransport()
        wl.add_channel(self.store, "claude-jobs", "youtube.com/@SlowWalks", transport=quiet)
        wl.add_channel(self.store, "second", f"https://www.youtube.com/channel/{SLOW}", transport=quiet)
        self.assertEqual(quiet.calls, [])
        self.assertEqual(len(wl.channels(self.store, "claude-jobs")), 1)
        self.assertEqual(len(wl.channels(self.store, "second")), 1)
        self.assertEqual(self.default_units(), 1)

    def test_marking_a_known_channel_own(self):
        self.make()
        wl.add_channel(self.store, "claude-jobs", "@slowwalks",
                       transport=FakeTransport(payload("channels_list_handle.json")))
        ch = wl.add_channel(self.store, "claude-jobs", "@slowwalks", own=True, transport=FakeTransport())
        self.assertTrue(ch.own)

    def test_channel_not_found(self):
        self.make()
        t = FakeTransport(payload("channels_list_not_found.json"))
        with self.assertRaises(wl.WatchlistError) as cm:
            wl.add_channel(self.store, "claude-jobs", "@nobodyhere", transport=t)
        self.assertIn("@nobodyhere", str(cm.exception))
        self.assertEqual(wl.channels(self.store, "claude-jobs"), [])
        self.assertEqual(self.default_units(), 1)  # the call itself still cost a unit

    def test_add_channel_refuses_before_calling_when_quota_is_spent(self):
        self.make()
        quota.charge(self.store, "videos.list", calls=10_000)
        t = FakeTransport(payload("channels_list_handle.json"))
        with self.assertRaises(quota.QuotaExceeded):
            wl.add_channel(self.store, "claude-jobs", "@slowwalks", transport=t)
        self.assertEqual(t.calls, [])
        self.assertEqual(wl.channels(self.store, "claude-jobs"), [])

    def test_add_channel_to_unknown_watchlist_calls_nothing(self):
        t = FakeTransport(payload("channels_list_handle.json"))
        with self.assertRaises(wl.WatchlistError):
            wl.add_channel(self.store, "nope", "@slowwalks", transport=t)
        self.assertEqual(t.calls, [])

    def test_remove_channel(self):
        self.make()
        wl.add_channel(self.store, "claude-jobs", "@slowwalks",
                       transport=FakeTransport(payload("channels_list_handle.json")))
        wl.add_channel(self.store, "claude-jobs", TERM,
                       transport=FakeTransport(payload("channels_list_id_hidden_subs.json")))
        wl.remove_channel(self.store, "claude-jobs", "https://www.youtube.com/@slowwalks")
        self.assertEqual([c.external_id for c in wl.channels(self.store, "claude-jobs")], [TERM])
        with self.assertRaises(wl.WatchlistError) as cm:
            wl.remove_channel(self.store, "claude-jobs", "@slowwalks")
        self.assertIn("not in", str(cm.exception))

    def test_removing_a_watchlist_keeps_its_channels_for_other_watchlists(self):
        self.make()
        self.make("second", format_id="walk_reel")
        for name in ("claude-jobs", "second"):
            wl.add_channel(self.store, name, "@slowwalks",
                           transport=FakeTransport(payload("channels_list_handle.json")))
        wl.remove(self.store, "claude-jobs")
        self.assertEqual([c.handle for c in wl.channels(self.store, "second")], ["@slowwalks"])


if __name__ == "__main__":
    unittest.main()
