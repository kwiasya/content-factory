"""Hooks, formats and topics summaries of a Watchlist on synthetic cards and snapshots."""


from cf.research import summary
from cf.research import watchlist as wl
from research_synth import NOW, SummaryCase, hook, put_card


class HooksSummaryTest(SummaryCase):
    def test_groups_are_hook_categories_weighed_by_summed_outlier_with_unscored_as_one(self):
        r = summary.hooks(self.store, "lisbon", now=NOW)
        groups = self.section(r, "hook_category").groups
        self.assertEqual([(g.value, g.count) for g in groups],
                         [("question", 1), ("visual_payoff", 2), ("sunset_tease", 2), ("list", 2)])
        self.assertEqual([round(g.weight, 2) for g in groups], [9.0, 8.0, 3.5, 2.0])

    def test_examples_are_best_outlier_first_with_title_outlier_views_link_spoken_hook_and_formula(self):
        r = summary.hooks(self.store, "lisbon", now=NOW)
        vp = next(g for g in self.section(r, "hook_category").groups if g.value == "visual_payoff")
        self.assertEqual([e.external_id for e in vp.examples], ["alfamaDawn1", "gracaStair2"])
        e = vp.examples[0]
        self.assertEqual((e.title, e.views, e.url, e.spoken_hook, e.formula),
                         ("Alfama at dawn", 5000, "https://www.youtube.com/watch?v=alfamaDawn1", "So this is Alfama",
                          "Place name + superlative"))
        self.assertAlmostEqual(e.outlier, 5.0)
        self.assertEqual((vp.label, vp.best_outlier), ("Visual payoff", 5.0))

    def test_a_card_without_a_spoken_hook_shows_the_measured_opening(self):
        r = summary.hooks(self.store, "lisbon", now=NOW)
        st_ = next(g for g in self.section(r, "hook_category").groups if g.value == "sunset_tease")
        self.assertEqual([(e.external_id, e.spoken_hook) for e in st_.examples],
                         [("sunsetSoon4", "Sunset in ten minutes"), ("waitForSun5", "measured words")])

    def test_a_leftover_proposed_prefix_groups_under_the_bare_value_flagged_proposed(self):
        groups = self.section(summary.hooks(self.store, "lisbon", now=NOW), "hook_category").groups
        flags = {g.value: g.proposed for g in groups}
        self.assertEqual(flags, {"question": False, "visual_payoff": False, "sunset_tease": True, "list": False})
        st_ = next(g for g in groups if g.value == "sunset_tease")
        self.assertEqual([e.proposed for e in st_.examples], [True, False])

    def test_a_second_section_ranks_hook_formulas_folded_for_case_and_spaces(self):
        put_card(self.store, "waitForSun5", hook("sunset_tease", "  sunset IN n   minutes", None))
        r = summary.hooks(self.store, "lisbon", now=NOW)
        self.assertEqual([sec.kind for sec in r.sections], ["hook_category", "hook_formula"])
        groups = self.section(r, "hook_formula").groups
        self.assertEqual([(g.value, g.count, round(g.weight, 2)) for g in groups],
                         [("why is <place> <adjective>?", 1, 9.0), ("place name + superlative", 1, 5.0),
                          ("sunset in n minutes", 2, 3.5), ("stairs + count", 1, 3.0),
                          ("n cafes", 1, 1.0), ("n viewpoints", 1, 1.0)])
        sunset = groups[2]
        self.assertEqual(sunset.label, "Sunset in N minutes")
        self.assertEqual([e.external_id for e in sunset.examples], ["sunsetSoon4", "waitForSun5"])

    def test_cards_outside_the_window_or_the_watchlist_are_left_out(self):
        values = {g.value for g in self.section(summary.hooks(self.store, "lisbon", now=NOW), "hook_category").groups}
        self.assertNotIn("contrast", values)  # oldhit is 20 days old, c1 belongs to another Watchlist
        wider = summary.hooks(self.store, "lisbon", days=30, now=NOW)
        self.assertIn("contrast", {g.value for g in self.section(wider, "hook_category").groups})

    def test_uncarded_outliers_above_the_threshold_are_listed_best_first(self):
        r = summary.hooks(self.store, "lisbon", now=NOW)
        self.assertEqual([(u.external_id, u.measured) for u in r.uncarded], [("uncardHit01", False), ("measuredOn3", True)])
        self.assertAlmostEqual(r.uncarded[0].outlier, 6.0)
        lower = summary.hooks(self.store, "lisbon", min_outlier=1.2, now=NOW)
        self.assertEqual([u.external_id for u in lower.uncarded], ["uncardHit01", "measuredOn3", "uncardMeh02"])

    def test_counts_of_references_and_cards_in_the_window(self):
        r = summary.hooks(self.store, "lisbon", now=NOW)
        self.assertEqual((r.references, r.carded, r.format_id), (10, 7, "walk-reel"))

    def test_limit_caps_groups_and_uncarded_and_examples_caps_each_group(self):
        r = summary.hooks(self.store, "lisbon", limit=2, examples=1, now=NOW)
        groups = self.section(r, "hook_category").groups
        self.assertEqual([g.value for g in groups], ["question", "visual_payoff"])
        self.assertEqual([len(g.examples) for g in groups], [1, 1])
        self.assertEqual(groups[1].count, 2)
        self.assertEqual(len(r.uncarded), 2)

    def test_an_unknown_watchlist_is_an_error(self):
        with self.assertRaises(wl.WatchlistError):
            summary.hooks(self.store, "nope", now=NOW)


class FormatsSummaryTest(SummaryCase):
    def test_storytelling_formats_and_visual_layouts_are_two_sections(self):
        r = summary.formats(self.store, "lisbon", now=NOW)
        self.assertEqual([s.kind for s in r.sections], ["storytelling_format", "visual_layout"])
        fmt = [(g.value, g.count, round(g.weight, 2)) for g in self.section(r, "storytelling_format").groups]
        self.assertEqual(fmt, [("pov", 4, 17.5), ("listicle", 3, 5.0)])
        lay = [(g.value, g.count, round(g.weight, 2), g.proposed) for g in self.section(r, "visual_layout").groups]
        self.assertEqual(lay, [("pov_walk", 4, 11.5, False), ("talking_head", 1, 9.0, False),
                               ("map_overlay", 2, 2.0, True)])


class TopicsSummaryTest(SummaryCase):
    def test_topics_group_after_folding_case_and_whitespace_only(self):
        r = summary.topics(self.store, "lisbon", now=NOW)
        groups = self.section(r, "topic").groups
        self.assertEqual([(g.value, g.count, round(g.weight, 2)) for g in groups],
                         [("lisbon hills", 1, 9.0), ("walking lisbon's oldest district", 2, 8.0),
                          ("sunset spots", 2, 3.5), ("cafes", 1, 1.0), ("viewpoints", 1, 1.0)])
        self.assertEqual(groups[1].label, "Walking Lisbon's oldest district")
        self.assertFalse(any(g.proposed for g in groups))
