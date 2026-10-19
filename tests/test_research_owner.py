"""The owner rule (ADR 0014): Briefs, Video Notes and Idea <-> Video links name the person whose local root holds
the thing; other people's rows are listed with the owner and never opened."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.research import brief, cli, ideas, notes
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import CHANNEL_A, NOW, add_member, add_videos, fields, iso, video_item

V1 = "dQw4w9WgXcQ"


class OwnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.db = self.dir / "factory.db"
        env = mock.patch.dict(os.environ, {"CF_PERSON": "author"})
        env.start()
        self.addCleanup(env.stop)
        self.store = st.open_store(self.db, create=True)
        self.addCleanup(self.store.close)
        wl.create(self.store, "w", format_id="walk-reel", author_channel="me")
        add_member(self.store, "w", CHANNEL_A, "@alpha")
        add_videos(self.store, [video_item(V1, CHANNEL_A, iso(NOW), 40, 900)], taken_at=iso(NOW))

    def test_a_brief_records_who_wrote_it(self):
        idea = ideas.add(self.store, "w", [V1], fields()).id
        ideas.shortlist(self.store, idea)
        brief.create(self.store, idea, root=self.dir)
        got = ideas.get(self.store, idea)
        self.assertEqual(got.brief_owner, "author")
        self.assertTrue(ideas.mine(got.brief_owner))
        with mock.patch.dict(os.environ, {"CF_PERSON": "nastya"}):
            self.assertFalse(ideas.mine(got.brief_owner))
            self.assertTrue(ideas.mine(""))

    def test_video_notes_carry_an_owner_and_list_only_this_persons_unless_all(self):
        mine = notes.add(self.store, "video", "a-walk", "mine")
        theirs = notes.add(self.store, "video", "b-walk", "theirs", owner="nastya")
        legacy = notes.add(self.store, "video", "c-walk", "old", owner="")
        channel = notes.add(self.store, "channel", "instagram:@x", "shared")
        self.assertEqual((mine.owner, theirs.owner, channel.owner), ("author", "nastya", ""))
        self.assertEqual([n.id for n in notes.list(self.store)], [mine.id, legacy.id, channel.id])
        self.assertEqual([n.id for n in notes.list(self.store, all_owners=True)],
                         [mine.id, theirs.id, legacy.id, channel.id])
        with mock.patch.dict(os.environ, {"CF_PERSON": "nastya"}):
            self.assertEqual([n.id for n in notes.list(self.store)], [theirs.id, legacy.id, channel.id])

    def test_cli_notes_list_all_shows_every_owner(self):
        notes.add(self.store, "video", "b-walk", "theirs", owner="nastya")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["notes", "list", "--json", "--db", str(self.db)])
        self.assertEqual(json.loads(out.getvalue()), [])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["notes", "list", "--all", "--json", "--db", str(self.db)])
        self.assertEqual([n["owner"] for n in json.loads(out.getvalue())], ["nastya"])


if __name__ == "__main__":
    unittest.main()
