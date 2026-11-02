# 13 · Notes: item 2 for Jenny Hoyos, Casey Neistat, Drew Binsky, Yes Theory, Ryan Trahan (+ Nas Daily, Kallaway), items 4 and 5 for their principles

Researcher 2 of 3. Collected 2026-10-12. Tags follow the CONTEXT block:
- **DATA**: a measurement over a sample, an A/B test or a retention graph. One video's view count is context, never DATA.
- **PRACTITIONER**: a creator's or analyst's stated practice, with no data shown.
- **THEORY**: a model, not tested on video.
- **OBS**: my own reading of a named video at the given timestamps. It is evidence that a rule shows up in the video, not evidence that the rule works.

How the sources were reached:
- **No web search was available.** The shared WebSearch budget for the run (200 calls) was used up before this agent's first query. Every source here comes from one of these instead:
  - direct fetches of known URLs (Wikipedia pages and the URLs they cite, Creator Science episode pages, the YouTube Official Blog, Tubefilter, Times of Israel);
  - channel listings made with yt-dlp 2026.08.19 (`--flat-playlist`; titles, durations, view counts);
  - YouTube Data API `videos.list` for upload dates, durations, descriptions and credits;
  - YouTube's own transcript panel, read in a browser tab. These are the auto-captions, and a timestamp marks when a caption segment starts.
- yt-dlp caption download was blocked by YouTube's bot wall ("Sign in to confirm you're not a bot") for the whole run. It was not worked around.
- Timestamps marked **[CS page]** come from the chapters and transcript on the Creator Science episode page. They are approximate, to the start of the speaker block.
- Timestamps marked **[sibling captions]** come from an en-orig caption file that another researcher in this run pulled with yt-dlp before the wall went up.
- Channel-catalog numbers are my own measurements of the public listings as of 2026-10-12. The `/videos` tab excludes Shorts.
- Older than 2024 is flagged **(pre-2024, possibly outdated)**.

---

## 2. Comparison creators

### 2.1 Jenny Hoyos (Shorts)

**Stated principles**

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| J1 | Average views per Short of about 10M in 2023. The episode title is the claim, and no data is shown. [verified: episode title "How she averages 10 million views per video"] | PRACTITIONER | Creator Science #167, https://creatorscience.com/podcast/jenny-hoyos/ | 2023-10-10 (pre-2024) | ep. title |
| J2 | The hook is **visual**. Test: could it work as a long-form title plus thumbnail and still get the click? It must be understood without sound. | PRACTITIONER | Creator Science #167 | 2023-10-10 | chapter "Crafting the Perfect 1st Frame Hook" 9:41 [CS page] |
| J3 | She sketches the visual idea on an iPad first, then writes the words. | PRACTITIONER | Creator Science #167 | 2023-10-10 | ~9:41–12:53 [CS page] |
| J4 | Script readability is checked with a tool, with a target of 5th grade or below. She chose the target by analysing popular Shorts. Words like "business" or "profit" push the score up, so she explains them in plain words instead. [verified] | PRACTITIONER (claims an analysis, none shown) | Creator Science #167 | 2023-10-10 | ~4:01 [CS page] |
| J5 | Structure: hook, then a 2-line **foreshadow** under ~3 s that sets up the payoff, then a smooth transition, then the body (problem-solution, or "but/therefore" chains), then the payoff. She writes the hook and the last line before filming and leaves the reaction in the last line blank until the shoot. [verified] | PRACTITIONER | Creator Science #167 | 2023-10-10 | chapter "Jenny's Shorts Structure" 19:50; ~19:20, ~22:17 [CS page] |
| J6 | "Stories can't be stories without change." She rewrites "and then" beats into "but/therefore" beats. She dropped explicit pacing breaks ("I used to have a lot of breaks") in favour of "a pacing break without the pacing actually breaking". [verified] | PRACTITIONER | Creator Science #167 | 2023-10-10 | ~20:52, ~22:17 [CS page] |
| J7 | Retention mechanisms that tell viewers how far along they are: a countdown, a three-step list. A set expectation followed by a twist. | PRACTITIONER | Creator Science #167 | 2023-10-10 | chapter "Retention Mechanisms" 16:24 [CS page] |
| J8 | Length: her most popular Shorts average about **34 s**, so that is her target. On her channel, Shorts under 30 s need near-total retention to take off. TikTok "did not like videos over 30 seconds". [verified] | PRACTITIONER (own analytics, not shown) | Creator Science #167 | 2023-10-10 | 18:34; ~29:13 [CS page] |
| J9 | Her metrics: the average "scroll-through rate" (her term for the share who watch rather than swipe) is about 70% and hers is about 85%. Her average retention is about 95%, mostly from rewatches. She calls 90%+ "the bare minimum" for a Short to blow up. [verified] | PRACTITIONER (numbers stated, no screenshot) | Creator Science #167 | 2023-10-10 | 5:28 [CS page] |
| J10 | One-video test: a Short at about 50k views in 5 days had 83% retention and a sharp drop at the end. She trimmed the last second in YouTube Studio, retention rose to 88%, and the video "then took off". [verified] | PRACTITIONER (n=1, before/after with no control) | Creator Science #167 | 2023-10-10 | 5:28–9:41 [CS page] |
| J11 | Counter-claim from the same interview: "retention doesn't matter as much as people think it does". A Short at 70% retention over its first 100k views still reached about 10M. She suspects **shares** matter, citing one Short with a share-to-view ratio of about 20%. [verified] | PRACTITIONER | Creator Science #167 | 2023-10-10 | chapter "Hot Takes" 36:03 [CS page] |
| J12 | Ideas: a Google Doc of about 1,000 ideas. Filters: does she want to make it, is it doable, strong hook, strong mechanism, rewatchable, where is the virality. About 100 ideas go to 25–50, then her editor, who is also her strategist, cuts them to about 10 ("he's not just a video editor"). Her best ideas come from everyday life, for example wanting a cheaper ratatouille. [verified] | PRACTITIONER | Creator Science #167 | 2023-10-10 | 12:53, ~14:59 [CS page] |
| J13 | She started by "stealing" other creators' hook styles, tested variations, then added her own twist. | PRACTITIONER | Creator Science #167 | 2023-10-10 | ~10:59 [CS page] |
| J14 | Long-form: "I'm never gonna quit shorts", but "I don't see that much more growth for me in shorts". [verified] | PRACTITIONER | Creator Science #167 | 2023-10-10 | ~30:44–30:56 [CS page] |
| J15 | Analyst summary (Colin and Samir, 2026): her "main quote" is roughly "I don't ask if it will go viral, I'll make it viral", and her first principle is a visual hook treated like a thumbnail. They also report that MrBeast's team hired her to **direct** his most-shared TikTok. [verified] | PRACTITIONER (tier 3, second-hand) | Colin and Samir, "Overanalyzing The Most Shared TikTok Ever", https://www.youtube.com/watch?v=FjIZWCX9Qeo | 2026-08-12 | 4:50–6:12 [sibling captions] |

**What her videos show**

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| J16 | "I Built a Secret Room with $0" (45 s, 184.8M views). | OBS | https://www.youtube.com/watch?v=bNrBRtX4mjc | 2023-12-30 | see the beats below |

Beats in J16:
- 0:00: premise plus constraint in one line ("secret room with $0"), with an immediate conflict as a family member objects ("you're destroying the house").
- 0:08: goal stated.
- 0:15: obstacle ("I'm out of wrapping paper").
- 0:31: twist ("but my secret room has a big problem… this is not a secret").
- 0:31–0:39: "therefore" fix (a trash-bag entrance).
- 0:39: payoff ("it looks so nice right").

The title is the hook, word for word (J2). The "but" beat follows J5 and J6.

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| J17 | "What's Faster: Drive Thru or Cooking?" (55 s, 107M). | OBS | https://www.youtube.com/watch?v=Jx5CxOLZlqQ | 2024-07-20 | see the beats below |

Beats in J17:
- 0:00: the title question is spoken as the first line.
- The drive-thru queue works as a visible **countdown** (J7): "good thing there's a line" (0:08), "one person away" (0:24), "next next next" (0:41).
- 0:51: payoff ("we cooked faster and better").

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| J18 | Long-form carries the Shorts devices over. Her first Q&A (6:35) opens with a **jump-cut teaser of answers out of context** (0:00–0:08). A visual completion goal follows ("I'm trying to make the picture on screen", 0:13), a cooking task carries through the whole video, and the payoff is plating and tasting (6:07–6:27). The video ends with an end-screen CTA. | OBS | https://www.youtube.com/watch?v=2idU7KQV_2U | 2025-05-12 | 0:00, 0:13, 6:07 |
| J19 | **Duration of her outliers.** Her top 50 Shorts by views (#ad/FIFA excluded; 2022-10 to 2026-05): median **38 s**, interquartile range 33–45 s, 10 of 50 under 30 s, median 42.6M views. This roughly confirms J8 (≈34 s) and shows the outliers sit at 30–45 s, not under 15 s. [verified: re-measured 2026-10-12 via Data API: median 38 s, IQR 33–45 s, 10/50 under 30 s; median views now 44.0M] | DATA (n=50; my measurement via Data API) | https://www.youtube.com/@jennyhoyos/shorts | measured 2026-10-12 | — |
| J20 | **Her output changed after Nov 2025.** About 4,200 of the ~4,600 items on her Shorts tab date from 2025-11 to 2026-10 (item 4,201 is dated 2025-11-01), roughly 12 a day. A systematic sample (every 40th item, n=100) has median **10 s** (IQR 8–16 s), 94/100 under 30 s, and median 201k views. Many are subscribe asks ("SUBSCRIBE SO U CAN SEE ME AGAIN!", 5–8 s), bloopers or collab clips. This is the opposite of her 2023 playbook (J5, J8, J12). She has stated no reason, and I found no source that explains it. [verified: 4,202 items dated 2025-11-01 or later, item 4,201 dated 2025-11-01; my own every-40th sample gives median 11 s, IQR 8–14 s, 96/100 under 30 s, median 227k, so the same picture] | DATA (n=100; my measurement) | same | 2025-11 to 2026-10 | e.g. https://www.youtube.com/shorts/IYak0fL9V0Q (17 s, 2026-10-11) |

**Typical structure:** a visual first frame that equals the title, then a 2-line foreshadow, then a "but/therefore" body with a progress device (countdown, list, queue), then a payoff, at 34–45 s (J5, J7, J16, J17).
**Hook habit:** a question or a "$0 / $1 / faster than" constraint, read as the first line over a striking first frame (J2, J16, J17).
**Retention devices:** progress meters, an end cut to the bone (J10), loop or rewatch value (J9).
**Packaging:** title = hook = first line. Low reading level (J4).
**Unique:** she treats the Short's first frame as a thumbnail, uses a reading-level target, and a strategist-editor filters her ideas.

**Negative and contested**
- J11 contradicts J9 inside the same interview: 90% retention is called "the minimum", yet a 70% Short reached 10M. Her own explanation, shares, is untested.
- J10 is one before/after with no control.
- The 2025–26 output (J20) abandons the long scripted Short in practice. It is unknown whether this is a strategy or a side channel of clips.
- Shorts subscribers may not convert to long-form. See Z1 in section 5.

### 2.2 Casey Neistat (vlog)

**Stated principles**

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| C1 | "The most important thing is of course the story." Every episode aims at a three-act narrative: beginning, middle, end, or setup, conflict, resolution. "In some episodes that's super literal." [verified] | PRACTITIONER | "HOW TO VLOG LIKE CASEY NEISTAT by CASEY NEISTAT", https://www.youtube.com/watch?v=Q980C74SdYQ | 2017-06-08 (pre-2024) | 4:48–5:45 |
| C2 | The deal with himself was "never an obligation to share… the intimacies of every day… this isn't a journal". The question was whether he could find a three-act narrative in every day. His 2015 test was to vlog a Belgium trip "with really precise cinematography… movie-like" instead of talking to camera. | PRACTITIONER | same | 2017-06-08 | 3:48–4:41; 5:52–6:08 |
| C3 | Shot mix: roughly equal parts handheld, locked-off (tripod) and wide establishing shots. Establishing shots tell you where he is. Locked-off shots let the viewer "forget about the camera". Handheld gives "spontaneity and urgency". [verified] | PRACTITIONER | same | 2017-06-08 | 6:17–6:51 |
| C4 | Hardware: "always use the very best camera you have at your disposal", including the phone on runs. "Hold the camera steady": shaky footage "goes straight in the trash". [verified] | PRACTITIONER | same | 2017-06-08 | 6:51–7:46 |
| C5 | Time-lapses and drone shots only work as a **transition** between scenes or as **context** for where he is. Without a link to the narrative they get "boring very very fast". [verified] | PRACTITIONER | same | 2017-06-08 | 8:19–9:26 |
| C6 | "If you make the most perfect Casey vlogs you will have failed before you've begun… be original." [verified] | PRACTITIONER | same | 2017-06-08 | 10:06–10:47 |
| C7 | The daily vlog was a "forcing agent": "how do I make this interesting enough to warrant a video?" You had to find the story rather than wait for it. Now "the threshold is much higher". [verified] | PRACTITIONER | Colin and Samir, "Casey Neistat: The Death of 'Art' on YouTube", https://www.youtube.com/watch?v=WclA5UTdVBE | 2025-10-07 | 26:09–26:48 |
| C8 | His core approach: when something interesting happens, "especially things from my own life", he wants "to share that interestingness". [verified] | PRACTITIONER | same | 2025-10-07 | 23:54–24:10 |
| C9 | He calls "MY ALL TIME GREATEST!!!" "the greatest three-act narrative ever". His wife's verdict was "You lost your drone… Nothing happens here", and he agrees it is "such a nothing video". The craft was "finding the dramatic tension" in it. [verified] | PRACTITIONER | same | 2025-10-07 | 27:32–28:44 |
| C10 | He works alone. Of about 1,200 videos, "1198 of them I edited". He hired Dan Mace to help edit the daily vlog and stopped after two weeks: "taking 10 times as long, and the videos are half as good". Only Max Joseph sees his rough cuts. [verified] | PRACTITIONER | same | 2025-10-07 | 29:09–31:26 |
| C11 | He does not use the YouTube Studio app. Metric-chasing is "the conflation" of art and economy. [verified] | PRACTITIONER | same | 2025-10-07 | 13:43–13:57; 11:29–12:35 |
| C12 | Analyst: Casey's on-screen text is **diegetic**. He points the camera at a real sign long enough for viewers to read it, so they "fill in the gaps" (South Africa example). The film-booth contrast is Mrwhosetheboss's animated keyword text. [verified] | PRACTITIONER (tier 3 analyst) | Film Booth, "Editing Hacks YouTubers Use To Hook You", https://www.youtube.com/watch?v=sZ4t7fJXnT0 | 2023-04-19 (pre-2024) | 0:29–2:00 |
| C13 | Analyst: what made the daily vlog compound was a **contained world of recurring elements**: Marlin the delivery guy, the studio as a set, dollar pizza, time-lapses. "It's not just going daily. It's making sure that almost every element is familiar." [verified] | PRACTITIONER (tier 3) | Colin and Samir, "Ryan Trahan reacts to 50 States in 50 Days", https://www.youtube.com/watch?v=CQE2E88QJes | 2025-07-13 | 53:00–53:16 |

**What his videos show**

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| C14 | "MY ALL TIME GREATEST!!!" (9:51). He names it as his literal three-act example (C1, C9). | OBS | https://www.youtube.com/watch?v=nrcMDnPTdBU | 2016-02-02 (pre-2024) | see the beats below |

Beats in C14:
- 0:05–0:55: domestic cold open (banter).
- **0:55**: the mission is stated ("today's vlog is a mission, a rescue and recovery mission"). The hook comes late by short-form standards.
- 1:03: he lowers expectations, which raises the stakes ("I'm not expecting this to be a successful rescue").
- 1:31: setup (drone left on a roof).
- 2:24–4:19: failed attempts (conflict).
- **4:19**: turn ("I need an entirely new approach").
- 5:25: new plan with explicit stakes (900 ft of twine; "if… it falls… that's lights out").
- 6:19–9:04: execution, narrated live.
- **9:04**: resolution ("I got it").
- 9:38: "mission accomplished".

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| C15 | The "how to vlog" video practices what it teaches. It opens with a weather complaint (0:23), then a data check that undercuts it: it rains on only 11–15% of days (1:43). This setup licenses the topic (2:07). He announces act three on screen (11:00: "this is the beginning of act three"). | OBS | https://www.youtube.com/watch?v=Q980C74SdYQ | 2017-06-08 | 0:23, 1:43, 2:07, 11:00 |
| C16 | **2026 form: the thesis vlog.** "yeah, 730 days no exceptions" (8:19). | OBS | https://www.youtube.com/watch?v=OBtnKCG3QAE | 2026-06-04 | see the beats below |

Beats in C16:
- 0:35–0:48: cold-open payoff (2-year running streak).
- **1:03**: thesis stated ("doing the thing every day is easier than not doing the thing every day").
- 1:24–1:58: argument.
- 2:01–6:24: supporting interviews (a runner with a 9-year streak, his sister on quitting sugar, a sober friend). He says on camera, "I'm making a movie about consistency" (4:09).
- **6:47–7:51**: personal climax anecdote (running in an airport garbage tunnel to keep the streak).
- 8:07: button.

The three acts are kept, but the spine is an argument rather than an event.

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| C17 | **Cadence after the daily vlog.** Per the channel listing: 70 uploads between 2020-09-15 and 2024-11-14, about 1.4 a month, while he had largely stepped away ("that was like 7 years ago", 2025 interview, 3:23). Then 30 uploads between 2025-04 and 2026-08, about 1.9 a month. Median length 6.7–8.1 min, against about 7.4–9.5 min in the 2015–2020 vlog era. He has not returned to daily. [verified: 70 uploads 2020-09-15 to 2024-11-14, median 6.7 min; latest 30 median 8.1 min; the 2015–2020 range comes out at about 7.5–9.8 min depending on binning] | DATA (catalog n≈1,138; my measurement) | https://www.youtube.com/@casey/videos ; WclA5UTdVBE 3:13–3:23 | measured 2026-10-12 | — |

**Typical structure:** a cold open of life texture, then the mission or thesis, then attempts or obstacles, a turn, and resolution. About 8–10 min (C1, C14, C16).
**Hook habit:** a late, plain statement of the day's mission or thesis (C14 at 0:55; C16 at 1:03). There is no front-loaded promise in the first 5 s.
**Retention devices:** stakes and lowered expectations (C14 1:03), live narration of attempts, music-driven montage, diegetic text (C12), recurring characters and places (C13).
**Packaging:** all-caps or lower-case emotional titles with no curiosity formula ("DO HARD THINGS", "yeah, 730 days no exceptions"). Zero of his 100 most recent titles use the bracketed "(…)" hook that Yes Theory and Drew Binsky use (catalog count).
**Unique:** he shoots and edits everything himself (C10). Story is found in ordinary days (C7, C9).

**Negative and contested**
- His rule "story over everything" sits next to his own admission that his favourite story is "about nothing" (C9). The craft lies in the edit, not the event.
- His audience scale came from 2015–2016 daily volume, and he says the threshold is now "much higher" (C7). The vlog-daily principle is abandoned (C17; see section 5).
- Analysts note his peak views "weren't astronomical" compared with Ryan Trahan or Dude Perfect (Paddy Galloway on Colin and Samir, https://www.youtube.com/watch?v=WyiGFFTnIS4, 2026-08-19, 29:24–29:33 [sibling captions]).

### 2.3 Drew Binsky (travel)

**Stated principles**

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| B1 | He was a one-person operation until Aug 2020: "over a thousand videos over the last three years", with "editing… the vast majority of my time". A hired editor had to have seen 50+ of his videos and must "mimic my exact style of storytelling". The test edit was a **2–4 minute** video, delivered within 48 h. [verified] | PRACTITIONER | "I'm Hiring a VIDEO EDITOR!!!", https://www.youtube.com/watch?v=5gyV-YXKrMY | 2020-08-25 (pre-2024) | 0:00–1:36 |
| B2 | Self-taught in Premiere from YouTube tutorials. "I'm kind of cookie cutter, I don't put these crazy transitions." His signature open is formulaic: "I'm Drew Binsky and I'm going to show you what ten dollars can get you in…". [verified] | PRACTITIONER | "WHY DO I TRAVEL?… Q&A", https://www.youtube.com/watch?v=vA8ZX125Cb0 | 2019-09-20 (pre-2024) | 4:21–4:44 |
| B3 | Kit: Lumix GH5, DJI Air drone, GoPro, Osmo Pocket, phone. "Everything fits in my small backpack." | PRACTITIONER | same | 2019-09-20 | 6:25–6:41 |
| B4 | Little research beforehand: stories come "from spontaneous adventures". He is a "next day kind of person: make the video, post a video". [verified] | PRACTITIONER | same | 2019-09-20 | 10:01–10:25 |
| B5 | Advice to new creators: start before you are ready ("my first videos… are horrible"), post what you love, post consistently ("3… 4… or if you're crazy like me 7 videos a week"). [verified] | PRACTITIONER | same | 2019-09-20 | 9:05–9:29 |
| B6 | Stated plan for after visiting every country: "cut back on the daily videos" and go "into more longer form content". He later did (B10). [verified] | PRACTITIONER | same | 2019-09-20 | 0:08–0:22 |
| B7 | 90% of his income came from ads on YouTube and **Facebook**, 10% from sponsors, which he keeps "as low as possible". | PRACTITIONER | same | 2019-09-20 | 3:58–4:06 |
| B8 | Mission statement: help viewers "become a better traveler", "the #1 resource". He spends 2–3 h a day answering messages. | PRACTITIONER | https://drewbinsky.com/about/ | undated, read 2026-10-12 | — |
| B9 | Finished all 197 countries on 2021-10-29. Book *Just Go* (2024). A Netflix deal for his travels (2026; Variety, paywalled). | context | https://en.wikipedia.org/wiki/Drew_Binsky (citing Yahoo 2021-10-29, USA Today 2024, Variety 2026) | 2021–2026 | — |

**What his videos show**

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| B10 | **Format shift, measured.** Per the channel listing: 2012–2018 uploads have median 2.6 min (80 of 314 under 2 min). 2018-11 to 2019-12 brought 300 uploads in about 13 months (near-daily) at median 3.7 min. 2021-05 to 2023-08 median 18.0 min. **2025-10 to 2026-10: 30 uploads, median 33.6 min.** [verified: oldest 314 uploads (to 2018-11-14) median 2.6 min, 80 under 2 min; 2021-05 to 2023-08 median 18.0; latest 30 median 33.6] | DATA (catalog n=1,014; my measurement) | https://www.youtube.com/@drewbinsky/videos | measured 2026-10-12 | — |
| B11 | Short-era template, "Why is Everything FREE in Pakistan?!" (4:08, 10.2M). Like J16, the title question is the spine. | OBS | https://www.youtube.com/watch?v=CWeWxl7ruGE | 2019-03-31 (pre-2024) | see the beats below |

Beats in B11:
- 0:00: cold open of evidence (strangers handing over gifts and food).
- 0:15: quantified premise ("took out 28,000 rupees… day 8… my wallet is still full").
- 0:49: on-camera test ("I'm gonna show you… they won't accept my payment").
- 1:09–2:02: repeated trials.
- **2:19**: the title question spoken ("why are Pakistanis like this?").
- 2:27: a local gives the answer.
- 2:34–3:00: reflection contrasting this with the West.
- 4:01: signature subscribe tag.

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| B12 | Long-form template, "This American Town Is 36 Miles From Russia" (59:47, 14.4M). | OBS | https://www.youtube.com/watch?v=V0ZRVUdIf7s | 2026-08-29 | see the beats below |

Beats in B12:
- **0:00–0:28**: trailer open. The claim ("most remote town in America… that is Russia") plus a list of promises (local guide, strange food, "a walrus hunt on the Bering Sea").
- 0:39: uncertainty ("it's a gamble to get to Gambell"; fog can ground the plane).
- 1:27: credibility line ("I've been making videos for a decade… I can tell when something's going to be good").
- 2:27–3:32: early high-interest scene (polar bear hide, with a pre-emptive answer to commenters at 3:16).
- 27:14: mid-roll sponsor.
- **40:48**: the promised walrus hunt is paid off at about 68% of runtime.
- 58:48–59:06: reflective closing message.

**Typical structure:** short era: the title question, then quantified evidence, a demonstration, a local's answer and a reflection. Long era: a trailer of promises, then travel logistics as obstacles, a guide character, set pieces, the promised climax late, and a message.
**Hook habit:** a superlative or "why is X" claim spoken in the first 5 s, matching the title (B11 at 0:00–0:15; B12 at 0:00).
**Retention devices:** promises made in the first 30 s and paid off late (B12 15 s → 40:48), a guide or local as a recurring character, pre-emptive objection handling (B12 3:16).
**Packaging:** superlative or "secret/most dangerous/smallest" geography titles. 47 of 100 titles from 2021–2023 carry a bracketed qualifier, for example "(Philippines)" (catalog count).
**Unique:** one person, a backpack kit and next-day posting at volume in the short era (B1–B4), then an editor and long form.

**Negative and contested**
- His own "cookie cutter" description (B2) and a hired editor told to "mimic my exact style" (B1) show the style was a template, which helped volume and made him replaceable.
- His income in 2019 depended on Facebook (B7). That 1-minute Facebook travel-video era ended for him and for Nas Daily (N4). Distribution-specific formats age out.
- I found no 2024–2026 interview where he states his current long-form rules. The current structure (B12) is inferred from the videos only.

### 2.4 Yes Theory (travel / "Seek Discomfort" documentary)

**Stated principles**

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| Y1 | They started by emulating Casey Neistat, Jerome Jarre and MTV's *The Buried Life*, then had to "let our own personalities, opinions and ideas shine through". The "first big mistake" is never breaking the pattern: "too many channels on YouTube look exactly like Casey Neistat's vlogs or Sam Kolder's edits and never evolve". [verified] | PRACTITIONER | "Standing out on YouTube", https://www.youtube.com/watch?v=bKpS4m4Z28s | 2017-06-15 (pre-2024) | 0:36–1:39 |
| Y2 | Refusing to copy pranks and vlogs made them grow "way slower than everyone else". Early videos got about 800 views. A Snapchat-backed network found them after 6 months "and loved our originality". [verified: the network is "a new channel on Snapchat called Brother"] | PRACTITIONER | same | 2017-06-15 | 2:02–2:58 |
| Y3 | The "second biggest mistake" is doing it for the wrong reasons, i.e. making what you think a platform or buyer wants. [verified] | PRACTITIONER | same | 2017-06-15 | 2:27–3:22 |
| Y4 | The video ends with a dated cliffhanger: "huge episode coming out this Sunday… backyard… worth $200,000… you have to watch". A dated tease is used as a retention bridge between uploads. [verified] | OBS | same | 2017-06-15 | 4:25–5:03 |
| Y5 | Ammar Kandil on *Project Iceman* (a feature documentary, 2022): he was attached to "being a part of a process that is Oscar-worthy", not to the award. YouTube is "the platform that allows us to communicate… very effective and free". The reach of a YouTube hit "can far exceed the impact of… an Oscar". [verified] | PRACTITIONER | Colin and Samir, "Creator Roundtable", https://www.youtube.com/watch?v=kQRBnC3_AvE | 2023-08-25 (pre-2024) | 7:00–7:42; 11:27–11:51 |
| Y6 | *Frozen Alive* (Wim Hof documentary, 2019) was edited in about **6 days**. Colin and Samir co-edited it. It reached about 16M views and "unlocked a whole new lifeline for Yes Theory… today it's continued to be the direction". Speaker attribution is inferred from the transcript. [verified] | PRACTITIONER | same | 2023-08-25 | 34:35–36:26 |
| Y7 | Ammar on what audiences respond to in a creator: "contentment", "crack exactly the jokes that I want", even "a screen recording off of Photoshop". Said about Ryan Trahan; it is his view of authenticity over polish. [verified] | PRACTITIONER | same | 2023-08-25 | 1:00:56–1:01:28 |
| Y8 | Brand mantra "Seek Discomfort", which is also their apparel line. The group began as "Project 30" (30 new things in 30 days, Montreal, 2015). | context | https://en.wikipedia.org/wiki/Yes_Theory | last edited 2026-06-05 | — |
| Y9 | Colin and Samir's 2022 interview has chapters titled "The Role of Data in Yes Theory's YouTube Growth" (9:03), "Hiding the Vegetables" (18:00) and "How Yes Theory Makes Viral Videos" (43:45). **The transcript could not be loaded.** The content of these chapters is unverified. | — | https://www.youtube.com/watch?v=3vbZvRHpM8w | 2022-04-18 | chapter list only |

**What their videos show**

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| Y10 | **Format shift, measured.** Per the channel listing: 2015–2019 median 8.4 min (200 uploads). 2019-03 to 2022-05 median 17.5 min. 2022-06 to 2025-06 median 28.4 min. **2025-06 to 2026-10: 30 uploads, median 34.8 min.** Titles moved to an "Exploring / X Hours in [superlative place] **(parenthetical curiosity tag)**" formula: 12 of the last 30, for example "(is it a scam?)", "(nobody comes here)", "(39 years isolated)". [verified: the "2015–2019" bin is the 200 uploads from 2015-12-29 to 2019-02-24 (median 8.4); 12 of the last 30 titles have a parenthetical] | DATA (catalog n=453; my measurement) | https://www.youtube.com/@yestheory/videos | measured 2026-10-12 | — |
| Y11 | 2026 documentary template, "'he's crazy' – We Found a Man Living Alone in the Amazon (39 years isolated)" (42:45, 9.6M). The narration is scripted voice-over laid on top of unscripted footage. | OBS | https://www.youtube.com/watch?v=dpHpKeXm-B0 | 2026-06-21 | see the beats below |

Beats in Y11:
- **0:03–1:04**: cinematic cold open of ominous local voices ("a land that God has created in anger", "I've seen people die").
- 1:09: the question that started the trip ("do you think there's anyone surviving on their own in the Amazon?").
- 1:26–1:53: the search is shown as costly (2 months, six guides, a BBC journalist's lead).
- 2:09: expert guide introduced as a character.
- **2:40**: central question restated ("how does a man survive here for decades completely on his own?").
- 3:28–4:34: weather and logistics as obstacles.
- 42:03–42:13: a closing line that reframes the subject.

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| Y12 | **Personal-story pivots.** "hardest video I've ever had to make" (22:43; 2.08M, 2025-09-14) and "I hit rock bottom" (16:39; 0.58M, 2025-09-28) are first-person confessionals breaking from the adventure format. The second's description says "my second and final personal story for now… Next week we're back with more Yes Theory adventures". | OBS (descriptions) | https://www.youtube.com/watch?v=fq5uGvkPJ14 ; https://www.youtube.com/watch?v=0FVBN8afvHg | 2025-09 | — |

**Typical structure (2024–26):** a cold open of danger or mystery voices, then the origin question, the cost of the search, a guide character, a restated central question, obstacle travel, the encounter and a reflective ending. 25–45 min.
**Hook habit:** a quote-first title ("'he's crazy' – …") plus a cold open of third-party voices, not the hosts.
**Retention devices:** a mystery question restated at the 2–3 min mark (Y11 2:40), logistics as jeopardy, an expert or guide character.
**Packaging:** a curiosity parenthetical in the title (Y10). Earlier, dated cliffhangers between uploads (Y4).
**Unique:** they began as a friend-group challenge brand, and the "Seek Discomfort" ethos doubles as merch (Y8). The group of hosts shrank: Derin left in 2017 over a visa, Matt stepped back in 2021 and said goodbye in 2023 (Wikipedia; https://www.youtube.com/watch?v=cd9or9hVpAw, 2023-10-30).

**Negative and contested**
- Their 2017 rule "refuse to look at what other people do" (Y2) is in tension with their 2024–26 packaging, which uses the same "Exploring the world's most X (parenthetical)" formula as Drew Binsky and other travel-documentary channels (Y10, B10). They converged on the genre's packaging.
- Y2 is an explicit self-reported cost of originality: slower growth.
- The view counts in Y12 show the personal-story pivot pulled 0.58–2.08M, against their 2025–26 adventure median of about 3M (single-video context, not DATA).

### 2.5 Ryan Trahan (challenges)

**Stated principles**

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| R1 | Before 2022 he chased what "the people at the top" did: "retention is a primary focus, exploiting CTR in any way possible". When the penny series took off he "made my team smaller… made the production value lower… made it more about myself and… my weaknesses", and "people really gravitated towards that". [verified] | PRACTITIONER | Colin and Samir, "How Ryan Trahan changed YouTube with $0.01", https://www.youtube.com/watch?v=wkDlfvTed1c | 2022-06-06 (pre-2024) | 1:00–1:49 |
| R2 | Packaging is still non-negotiable: "I have to do good titles and thumbnails that grab people's attention". The story inside should not be what you expect from the click. [verified] | PRACTITIONER | same | 2022-06-06 | 1:57–2:12 |
| R3 | "Exploitative work vs redemptive work": "retention, you can exploit that… or you can make the storyline something… actively energizing them". [verified] | PRACTITIONER | same | 2022-06-06 | 5:58–6:25 |
| R4 | Realism in packaging: realistic thumbnails with "a very subtle face", and a plain system font instead of a "corporate" one, because "it just feels more like me". Copying the top was "correlation is not causation". [verified] | PRACTITIONER | same | 2022-06-06 | 8:58–9:48 |
| R5 | Same point in the YouTube Official Blog: "How can we honestly make a very pretty photo?" Subtle emotions connect more than exaggerated faces. About 3,000 photos over five sessions for one thumbnail. A "complementary subtitle" decides click versus scroll. [verified: the 3,000 photos and five 5:30 a.m. mornings were for the "100 Days in GTA" thumbnail] | PRACTITIONER (tier 1 venue, creator statement) | https://blog.youtube/creator-and-artist-stories/ryan-trahan-thumbnail-editing-secrets-to-going-viral/ | 2022-06-09 (pre-2024) | — |
| R6 | **Thumbnails before footage.** All 30 penny-series thumbnails were made before the trip as "reverse engineering": "the thumbnail is done and now I just have to go do it". All 50 thumbnails for *50 States* were also made before departure, after "months and months" of ideation. [verified] | PRACTITIONER | wkDlfvTed1c; CQE2E88QJes | 2022-06-06; 2025-07-13 | 18:50–20:11; 24:50–25:06 |
| R7 | Mid-series repackaging. The series title changed from "I tried the top 50 Airbnbs in America" to "I visited 50 states in 50 days" because viewers were already calling it that ("package it in a way that people… are already talking about via word of mouth"). The first concept came from an outlier on his own channel ("OMG Airbnbs"). [verified] | PRACTITIONER | CQE2E88QJes | 2025-07-13 | 26:01–26:59 |
| R8 | Daily series need "segments that are repeatable and satisfying". Every episode's first four segments are fixed: good morning, morning routine, ranking, game plan. He writes the next episode's segments in his Notes app each night. The structure "allows the real stories to thrive" and stops viewers wondering "where are we?" [verified] | PRACTITIONER | CQE2E88QJes | 2025-07-13 | 6:36–7:32; 9:57–11:32 |
| R9 | Viewer-triggered stakes. Donations of $50k+ spin a "Wheel of Doom" of penalties (for example, no highways or no phones). His team triggers it. He calls it interactive, "like the live-stream magic". The 10 penalties are listed in the Day 1 description. [verified: the $50k threshold is said at 29:32] | PRACTITIONER | CQE2E88QJes 2:30–2:44, 3:17–4:18; https://www.youtube.com/watch?v=KTYbvU-aSf4 (description) | 2025-07-13; 2025-06-10 | — |
| R10 | 99% shot on iPhone. Graphics are iPhone and Airbnb UI ("very native"). A phone makes strangers comfortable on camera, whereas a DSLR in a 7-Eleven is "obnoxious". [verified: the "99%" is the host's figure, which Ryan confirms] | PRACTITIONER | CQE2E88QJes | 2025-07-13 | 18:16–19:56 |
| R11 | Team: "a team of like five people". The two editors (Zach and Cohen) cut 20–30-min dailies overnight, which he calls "by far the hardest part". In 2023 he said he had "a big team at one point" making "higher produced content", then "restarted" with two people on revenue share. Speaker for the 2023 quote inferred from context. [verified] | PRACTITIONER | CQE2E88QJes 7:32–7:58, 38:45; kQRBnC3_AvE 12:47–13:49 | 2025-07-13; 2023-08-25 | — |
| R12 | Cost comparison, self-reported: the 30-video penny series cost about **$6,000** and matched the views of a MrBeast Squid Game video that cost about $3.5M. "Frequency is another way" to compete. [verified] | PRACTITIONER (numbers stated, none shown) | kQRBnC3_AvE | 2023-08-25 | 58:28–59:26 |
| R13 | Low-effort and "underwhelming" concepts ("I tried public sleep pods", "I asked 100 drive-thrus for banned items") got 13–14M, while a high-effort Japan "world's oldest hotel" video was among his lowest. Rule drawn: "underwhelming ideas really stink if you don't end them in a way that's at least euphoric". Example: "I Invited 100 Celebrities To My Birthday": none came, but it ends in a party. [verified] | PRACTITIONER | kQRBnC3_AvE | 2023-08-25 | 1:13:17–1:15:10 |
| R14 | A think tank of creator friends on Discord pitches titles and thumbnails as homework ("four original titles and thumbnails and 10 random titles"). "The ideas we end up doing, there is precedent for." He runs "hypothesis weeks" because "the meta has changed so much". The 2023 hypothesis was that sensational "bangers" click less than human, ironic concepts. [verified] | PRACTITIONER | kQRBnC3_AvE | 2023-08-25 | 19:12–23:15 |
| R15 | Advice: "create an event", for example a week-long series that "feels scary", with a coinable name people repeat ("50 states in 50 days"). Balance it with regular uploads "every two weeks", or the event is wasted. [verified] | PRACTITIONER | CQE2E88QJes | 2025-07-13 | 21:03–23:46 |
| R16 | An emotional moment he thought was too raw to use (crying in the "quietest room" video) went into the cut because the editor insisted. "Those are the moments we crave." [verified] | PRACTITIONER | wkDlfvTed1c | 2022-06-06 | 11:54–12:27 |

**What his videos show**

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| R17 | "I Visited 50 States in 50 Days – Day 28" (26:51) runs his stated segment rule (R8) exactly. | OBS | https://www.youtube.com/watch?v=RpmS5x6dFjk | 2025-07-07 | see the beats below |

Beats in R17:
- 0:00: "good morning" with day count and recap.
- 0:20: fast morning-routine montage.
- 0:53: Airbnb **ranking** ("Connecticut is ranked 22").
- 1:34: **game plan**.
- 2:20: "good news / bad news" stakes ("the scariest house in America").
- 2:43: fundraiser stake ("$3 million… activates the switch").
- 20:27: nightly donation reading.
- 26:09: "see you in the morning".

| # | Observation | Tag | Source | Date | Timestamps |
|---|---|---|---|---|---|
| R18 | **Daily-series audience curve.** Public views (2026-10-12) of the *50 States* episodes: Day 1 12.0M, D2 8.3M, D3 7.2M, D5 6.2M, D10 5.4M, D15 4.5M, D20 4.0M, D25 3.9M, D30 3.7M, D35 3.4M, D42 3.0M, then D48 4.9M, D49 5.7M, finale 7.7M. €0.01 week (2023): D1 14M, then 8.1M, 7.4M, 6.9M, 6.6M, 6.6M, finale 6.4M. Pattern: steep loss over the first 3–5 episodes, a plateau at about 25–30% of Day 1, and a rise at the ending. Episodes are within ~7 weeks of each other, so age bias is small but not zero. [verified for *50 States* (Day 1 now 12.5M, the rest within 0.1M). The €0.01 week bottoms out at about 45% of Day 1, not 25–30%, so the plateau figure fits *50 States* only] | DATA (n=50 and n=7 episodes; my measurement) | https://www.youtube.com/@ryan/videos | measured 2026-10-12 | — |
| R19 | **Recut compilations outperform most dailies.** "Can I Travel Back to America with €0.01?" (66:44, 2023-07-28) has 44.1M, against 6–14M per daily. "I Stayed in Every State's Top Ranked Airbnb" (81:43, 2025-09-20) has 21.6M. "I crossed America with $0.01" (4:42:32 full movie of the 2022 series, 2024-06-01) has 24.6M. [verified] | OBS (single-video counts, context) | https://www.youtube.com/watch?v=guXTAOcrZaY ; https://www.youtube.com/watch?v=xyIF9hoNGqU ; https://www.youtube.com/watch?v=Py_tOOG99Hw | 2023–2025 | — |
| R20 | Length grew. Per the channel listing: 2016–2021 median 12.4 min. 2021-04 to 2023-12 median 14.2 min. 2023-12 to 2025-07 median 24.8 min. 2025-07 to 2026-09 median 27.8 min (includes daily episodes). [verified: 2023-12 to 2025-07 comes out at 25.0 min, the other bins as stated] | DATA (catalog n=345; my measurement) | same | measured 2026-10-12 | — |
| R21 | Brand-side work is **not** solo. "My last video" (2024-02-13) and "We need to talk" (2025-03-29), both Joyride candy ads styled as channel videos, credit directors (Sticks), a DP, gaffer, VFX, stunt doubles and a production designer. | OBS (credits in descriptions) | https://www.youtube.com/watch?v=kAixrLE_Wro ; https://www.youtube.com/watch?v=lb-B2zi9DtY | 2024-02-13; 2025-03-29 | — |
| R22 | Analyst: Ryan's map graphic is deliberately crude next to Johnny Harris's polished maps. It works because it matches his playful tone. Polished graphics on his videos would cost trust. [verified] | PRACTITIONER (tier 3) | Film Booth, https://www.youtube.com/watch?v=sZ4t7fJXnT0 | 2023-04-19 (pre-2024) | 2:13–3:35 |

**Typical structure:** a conceptual challenge (penny, 1-star, every seat or room) with a rulebook. In series: fixed opening segments, then variable adventure, then a nightly fundraiser beat and a tease for tomorrow (R8, R17). For one-offs: an underwhelming premise must still end euphoric (R13).
**Hook habit:** an "I tested / I stayed in every…" title with a realistic thumbnail. Daily episodes open on a ritual line ("Good morning…"), not a cold-open hook.
**Retention devices:** a progress counter (day N of 50; a ranking table), viewer-triggered jeopardy (Wheel of Doom), recurring characters (Haley, the editors, donors), cliff-tease into the next day.
**Packaging:** thumbnails designed before shooting (R6), realistic and subtle faces (R4, R5), a name the audience coins (R7).
**Unique:** "redemptive" framing (R3), charity events as the spine of a series, lo-fi iPhone production in public (R10).

**Negative and contested**
- He abandoned retention-first, CTR-exploiting videos (R1) and an edgy, "highly edited" reaction-video persona from his early channel (wkDlfvTed1c 42:03–43:06).
- A high-effort travel concept underperformed low-effort ones (R13).
- He warns against committing on camera to a goal "you haven't already validated as possible", using his Dr. Phil video as the example (wkDlfvTed1c 32:35–32:50).
- "Lo-fi and solo" is partly a presentation. The daily series has a team of about five, and the brand pieces have full crews (R11, R21).
- The cost comparison (R12) is self-reported and uncontrolled: different years and audiences, and 30 uploads against one.

---

### 2.6 Own additions

| Creator | Why added (one line) |
|---|---|
| **Nas Daily (Nuseir Yassin)** | The 1-minute daily travel-video school (Facebook-first, 1,000 days). It is the closest match to the author's 45–60 s travel Reels, and a documented case of a format being dropped. |
| **Kallaway** | The research- and data-driven short-form school (study transcripts and outliers, topic before hook). It is the closest analogue to the author's Watchlist → Reference → Hook library contour. |

Both are listed here, but most short-form hook rules belong to prompts 08 and 11.

**Nas Daily**

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| N1 | One 1-minute video a day for 1,000 days on Facebook. The 1,000th was on 2019-01-05, followed by a planned weekly cadence from 2019-02. Each video took about 6 h to shoot and 3 h to edit. [verified] | PRACTITIONER / context | https://en.wikipedia.org/wiki/Nas_Daily ; Times of Israel, https://www.timesofisrael.com/for-israeli-arab-one-minute-video-blogger-time-is-of-the-essence/ | 2017-03-04 (pre-2024) | — |
| N2 | The script "makes or breaks" a video. Over time he moved from travel moments to "more relevant topics" (for example, cost of living). He believes you only get better at something by doing it every day. | PRACTITIONER | Times of Israel | 2017-03-04 (pre-2024) | — |
| N3 | 2023: he now sees last year's "1 minute videos" about anything as attention with little money or impact. He frames creator priorities as attention, impact or money, chosen by "season". "Machine-gun" creators fail on 700 of 1,000 videos. He uses fixed daily deadlines (idea by 11 AM, script by 2 PM). [verified: the "700 of 1,000" failures are his own 1,000 days, not "machine-gun" creators in general] | PRACTITIONER | Creator Science #159, https://creatorscience.com/podcast/nuseir-yassin/ | 2023-08-08 (pre-2024) | ~6:58; ~15:22; ~18:07 [CS page] |
| N4 | Format shift, measured on the YouTube listing: 2019-11 to 2020-09 brought 300 uploads at median 1.4 min (158 under 2 min). **2024-07 to 2026-09: 30 uploads at median 8.7 min.** [verified] | DATA (catalog n=760; my measurement) | https://www.youtube.com/@NasDaily/videos | measured 2026-10-12 | — |
| N5 | Personal cost: "the benefits are public, but the price is very private". He says he "committed more to my work than to my relationship". [verified] | PRACTITIONER | Creator Science #159 | 2023-08-08 | ~0:34, ~3:31 [CS page] |

**Kallaway**

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| K1 | "If you have a bad topic… the video will fail." Topic outranks hook. Hooks are logged by formula, wording, why they worked and category. [verified] | PRACTITIONER | Creator Science #316, https://creatorscience.com/podcast/kallaway/ | 2026-09-01 | 22:18, 36:34 [CS page] |
| K2 | "Views are not the right metric to study." Study **mid-size** creators, because mega-creators' outliers reflect fame, not the idea. Drop brand-deal videos and anything under 2% engagement from the reference set. [verified] | PRACTITIONER | same | 2026-09-01 | 5:40, 16:14 [CS page] |
| K3 | Early on, 70–80% of topics come from validated competitor data and about 20% are original, tested in batches of about 10. After 10–20 of your own videos, mine your own channel's patterns. [verified] | PRACTITIONER | same | 2026-09-01 | 12:42, 31:16, 35:12 [CS page] |
| K5 | His audience of one: "I like to think of it as an audience of one" (narrow ideal customer profile). He has a small team: a daily idea researcher and a head of content. [verified: the "head of content" is at 27:02] | PRACTITIONER | same | 2026-09-01 | 3:45; 24:59 [CS page] |

---

## 4. Solo transfer (these creators' principles)

"Solo" here means one person, no team, no budget, a phone or a small camera, and DaVinci Resolve. The author's format is 45–60 s POV travel-walk Reels with music, plus whatever else fits.

| # | Principle | Source claims | Solo? | Substitute when partly / no |
|---|---|---|---|---|
| 4.1 | Visual first frame that works as a thumbnail and reads without sound | J2, J16 | **Yes** | Pick the frame in the edit, from the Shot log's best aesthetic and motion candidates. Put the title line on it as text, because many viewers watch muted. |
| 4.2 | Hook = title = first line; a constraint or question premise ("$0", "faster than", "why is X") | J16, J17, B11 | **Yes** | For music-only walks, the "line" is on-screen text in the first second. |
| 4.3 | 2-line foreshadow under 3 s, then "but/therefore" body | J5, J6 | **Partly** | A walk has no scripted plot. Substitute a **route promise** ("…until I found X") and cut beats so each one changes the situation (rain, a closed gate, a view). The Script writes the "but" as an overlay. |
| 4.4 | Progress device: countdown, list, queue, day N of 50, ranking | J7, J17, R8, R17 | **Yes** | "3 streets you shouldn't skip", a step counter, a map dot moving. Cheap overlays. |
| 4.5 | Trim the last second and end on the payoff for the loop | J10 | **Yes** | Free in the edit. It rests on n=1 (J10), so A/B it on your own Reels before making it a rule. |
| 4.6 | 5th-grade reading level for on-screen text | J4 | **Yes** | Automatable: a readability check in the critique step. |
| 4.7 | Idea bank of ~1,000 filtered to ~10 by a strategist-editor | J12 | **Partly** | No strategist. The agent's Idea triage and Hook library play that role. A peer or friend pass replaces the editor's veto. |
| 4.8 | Three-act story found in an ordinary day ("forcing agent") | C1, C2, C7, C9 | **Yes** | This is Casey's strongest solo claim: he edited 1,198 of about 1,200 videos himself (C10). For a walk, choose one micro-conflict per Reel (lost, rain, a closed spot, a found view) and resolve it. |
| 4.9 | Shot mix: handheld, locked-off and establishing in roughly equal parts | C3 | **Partly** | POV walks are almost all handheld or gimbal. Add 2–3 locked-off or tripod shots and one wide establishing shot per walk at capture time. Without them, everything feels "claustrophobic" (C3). |
| 4.10 | Drone and time-lapse only as transitions or context | C5 | **Yes** (as a restraint) | Free; it is a cut rule. Useful as a critique check: flag B-roll that has no narrative job. |
| 4.11 | Diegetic text: point the camera at a real sign instead of typing an overlay | C12 | **Yes** | Capture signs and street names on the walk. It is cheaper than graphics and reads as authentic. |
| 4.12 | Thesis vlog: state the argument, then gather interviews and anecdotes | C16 | **Partly** | Interviews take people and time. Substitute: the author's own voice-over thesis plus walk footage as evidence. |
| 4.13 | Next-day posting at volume (7 a week) with one kit in a backpack | B1, B3–B5 | **Partly** | Drew managed it alone, and editing ate "the vast majority" of his time (B1). For the author, the agent pipeline (ingest, Shot log, Script, build) is the substitute for an editor. Volume is capped by footage, not edit time. |
| 4.14 | Formula opener ("I'm X and I'm going to show you what $10 gets you in Y") | B2 | **Yes** | Template it as a Hook-library entry. Risk: sameness (see 5.6). |
| 4.15 | Trailer open: promise list in the first 30 s, payoffs late | B12 | **Partly** (long-form) | In a 45–60 s Reel, compress it to one promise in the first 2 s and pay it off in the last 5 s. |
| 4.16 | Cinematic documentary: cold open of others' voices, scripted VO, expert guide, months of search | Y5, Y6, Y11 | **No** | It needs crews, guides, fixers and months. Substitute a **single-question walk**: one question in text at 0 s ("Why is nobody here?"), the walk as the search, the answer at the end. |
| 4.17 | Curiosity parenthetical in titles ("(nobody comes here)") | Y10 | **Yes** | Free. Reels have captions, not titles, so put it in the first caption line or on the cover text. |
| 4.18 | Break out of the emulation phase into your own voice | Y1, C6 | **Yes** | The agent should keep a "style drift" note: which hooks and looks are borrowed, and from whom. |
| 4.19 | Thumbnail or cover designed **before** shooting ("reverse engineering") | R6 | **Yes** | Design the Reel cover and first-frame text before the walk; it becomes the shot list. |
| 4.20 | Fixed opening segments plus variable middle (series rulebook) | R8, R17, C13 | **Yes** | A recurring walk series ("Street N of …") with a fixed 3 s open and a fixed outro, and a recurring element such as a coffee or a ranking. |
| 4.21 | Viewer-triggered stakes (Wheel of Doom, donations) | R9 | **Partly** | No fundraiser scale. Substitute: comments pick tomorrow's street or rule (a poll), announced in the Reel. |
| 4.22 | 99% iPhone, native UI graphics | R10 | **Yes** | It already matches the iPhone and Osmo capture in this project. |
| 4.23 | Underwhelming premise must end euphoric | R13 | **Yes** | The ending is the payoff beat. The critique step can check that the last 3–5 s are the visual peak (view, light, reaction). |
| 4.24 | Event series with a coinable name, plus regular uploads between | R15 | **Partly** | A small event: "7 days, 7 neighbourhoods", posted daily, then a recap compilation (R19). |
| 4.25 | Daily dailies with overnight editing of 20–30 min episodes | R11 | **No** | Needs two editors. A daily 45–60 s Reel is feasible with the pipeline. |
| 4.26 | Recut the series into one long compilation | R19 | **Yes** | Cheap: the Resolve timeline already holds the parts. YouTube long-form gets a "full trip" cut. |
| 4.27 | Topic before hook; study mid-size creators; strip brand deals and low-engagement videos from the reference set | K1, K2 | **Yes** | It is already in the research contour. Add K2's filters (mid-size only, brand deals out, engagement floor) to Outlier scoring. |
| 4.28 | 70–80% validated topics, 20% original, batches of 10, then mine your own data after 10–20 videos | K3 | **Yes** | It maps to Watchlist outliers → Ideas. After about 20 Reels, switch the Reference set to the author's own analytics (prompt 14). |
| 4.29 | Daily posting as discipline | N1, N2, C7 | **Partly** | It is feasible for 45–60 s, but N3 and N5 report that the cost is personal life, and N3 says such videos bring "little money or impact". Cap it as a time-boxed event (4.24), not a permanent rule. |

---

## 5. Negative findings and abandoned principles

### 5a. Cargo-cult copies that failed

| # | Finding | Tag | Source | Date |
|---|---|---|---|---|
| 5.1 | Yes Theory, 2017: "too many channels on YouTube look exactly like Casey Neistat's vlogs or Sam Kolder's edits and never evolve". "Imitating Casey's vlogs because he's popular will not make you big on YouTube." No named failed channels are given. [verified] | PRACTITIONER | https://www.youtube.com/watch?v=bKpS4m4Z28s 1:23–1:39, 3:05–3:14 | 2017-06-15 (pre-2024) |
| 5.2 | Casey himself, 2017: "if you make the most perfect Casey vlogs you will have failed before you've begun". [verified] | PRACTITIONER | https://www.youtube.com/watch?v=Q980C74SdYQ 10:14–10:23 | 2017-06-08 (pre-2024) |
| 5.3 | Colin and Samir on their own Casey-copy daily phase: "when Casey did daily uploads, we did it and tons of creators were like 'Okay, I'm going to go daily now'… we probably made that decision without much thought… 'Wow, that's really hard… I'm not going to do that anymore.'" This is a named failed copy: their own channel. [verified] | PRACTITIONER (tier 3 analysts, about themselves) | https://www.youtube.com/watch?v=CQE2E88QJes 20:04–20:26 | 2025-07-13 |
| 5.5 | Copying a hit challenge format leads to replaceability. One roundtable speaker, unidentified (one of Ammar Kandil, Cleo Abram or Michelle Khare), describes the TikTok track of replicating one hit "over and over… really boring creatively… you could probably move them out and put someone else in". [verified] | PRACTITIONER | https://www.youtube.com/watch?v=kQRBnC3_AvE 29:13–29:46 | 2023-08-25 (pre-2024) |
| 5.6 | Dan Mace, "a better filmmaker than me in every capacity" (Casey), could not reproduce Casey's daily edit: "10 times as long… half as good". A personal edit style did not transfer to a skilled copier. [verified] | PRACTITIONER | https://www.youtube.com/watch?v=WclA5UTdVBE 30:13–31:06 | 2025-10-07 |
| 5.7 | Drew Binsky required editors to "mimic my exact style of storytelling" (B1). His channel then left that 2–4 min style for 30–60 min long-form (B10). The cloned template did not survive his own format change. [verified] | OBS + DATA (B10) | https://www.youtube.com/watch?v=5gyV-YXKrMY ; catalog | 2020-08-25; measured 2026-10-12 |
| Z1 | **Shorts → long-form does not convert** (Zach King; speaker inferred from "you have Zach King shorts" and the topic). "Our channel gets a million subscribers every month from short form only… none of those are converting to long form… now our long form doesn't even do well". A Shorts subscriber is "almost like the like button". This matters for Jenny Hoyos's long-form move (J14, J18). [verified] | PRACTITIONER | https://www.youtube.com/watch?v=kQRBnC3_AvE 46:20–48:50 | 2023-08-25 (pre-2024) |

**Gap:** I found no named third-party channel that copied Neistat, Hoyos, Binsky, Yes Theory or Trahan and documented its failure with numbers. Every cargo-cult finding above is a creator's or analyst's own statement.

### 5b. Principles the creators abandoned or contradicted

| # | Creator | Was | Now / contradiction | Tag | Source | Date |
|---|---|---|---|---|---|---|
| 5.8 | Casey Neistat | Daily vlog, 2015–2016 (about 800 episodes) | Stopped Nov 2016, came back Mar 2017, stepped away about 2018–2019 ("that was like 7 years ago", said in 2025), now posts 1–2 videos a month (C17). "The threshold is much higher now" (C7). [verified] | DATA (C17) + PRACTITIONER | WclA5UTdVBE 26:09–26:24; https://www.youtube.com/watch?v=dujs-an7ppQ 3:11–4:04 ("for the last year I've been doing nothing… trying to find that focus again"); Wikipedia citing Washington Post 2016-11-20 | 2016–2026 |
| 5.9 | Casey Neistat | Event-driven three-act vlog (C14) | 2024–26 thesis essays built on interviews (C16); "DO HARD THINGS", "DO IT ANYWAY" are argument titles | OBS | https://www.youtube.com/watch?v=StMltAX0mp0 (2024-11-14); https://www.youtube.com/watch?v=-jCQerxzF48 (2025-12-17); OBtnKCG3QAE | 2024–2026 |
| 5.10 | Jenny Hoyos | 34 s scripted Shorts, filtered from 1,000 ideas (J5, J8, J12) | Since Nov 2025, about 12 posts a day, median 10 s, many subscribe asks (J20) [verified] | DATA | J19/J20 measurement | 2025-11 to 2026-10 |
| 5.11 | Ryan Trahan | Retention-first, CTR-exploiting videos and a "big team" making "higher produced content" (R1, R11) | Smaller team, lower production, realism, "redemptive" framing. Ad pieces are still fully crewed (R21). | PRACTITIONER + OBS | wkDlfvTed1c 1:00–1:49; kQRBnC3_AvE 12:47–13:26 | 2022–2025 |
| 5.12 | Ryan Trahan | Pre-filmed series released after the fact (the first €0.01 week was "pre-filmed… by myself") | Real-time dailies driven by comments and donations [verified] | PRACTITIONER | wkDlfvTed1c 17:16–17:33 | 2022-06-06 |
| 5.13 | Ryan Trahan | Sensational "bangers" | 2023 hypothesis: sensational concepts click less, so lean into human and ironic concepts. Contested by his own 2024–25 superlatives ("I Flew Around the World in First Class", 47M, 2024-12-21). [verified: 47.4M, 2024-12-21] | PRACTITIONER + OBS | kQRBnC3_AvE 22:52–23:15; catalog | 2023–2024 |
| 5.14 | Drew Binsky | Daily 1–4 min videos, Facebook-heavy income (B7) | 30–60 min YouTube documentaries, about 2–3 a month (B10); a Netflix show (B9) [verified] | DATA + PRACTITIONER | B6, B10 | 2019 → 2026 |
| 5.15 | Yes Theory | "Refuse to look at what other people are doing" (Y2); a friend-group challenge format | Genre-standard "Exploring / X hours in the most… (parenthetical)" documentary packaging (Y10). Hosts left (2017, 2021, 2023). [verified] | DATA (Y10) + PRACTITIONER | bKpS4m4Z28s 2:02; catalog; cd9or9hVpAw | 2017 → 2026 |
| 5.16 | Nas Daily | 1,000 daily 1-minute videos | Weekly from 2019. In 2023 he called 1-minute videos about anything attention with little money or impact. YouTube median now 8.7 min (N4). [verified] | PRACTITIONER + DATA | N1, N3, N4 | 2019–2026 |
| 5.17 | Jenny Hoyos | "90%+ retention is the bare minimum" (J9) | Same interview: "retention doesn't matter as much as people think", a 70% Short reached 10M (J11) | PRACTITIONER (self-contradiction) | Creator Science #167 | 2023-10-10 |
| 5.18 | All five | Short and frequent | **Every long-form channel here got longer.** Median length of the latest 30 uploads against the early era: Binsky 2.6 → 33.6 min; Yes Theory 8.4 → 34.8; Trahan 12.4 → 27.8; Nas Daily 1.4 → 8.7. Casey is the exception, flat at about 7–8 min. Cadence fell to 1–3 a month, except event dailies. [verified] | DATA (catalog measurements) | B10, Y10, R20, N4, C17 | measured 2026-10-12 |

---

## Gaps

1. **No WebSearch.** The shared search budget was used up before this agent started. Sources are limited to URLs I knew or found by following links (Wikipedia references, Creator Science index), plus YouTube channel listings. These were therefore not found:
   - press or blog pieces on Jenny Hoyos beyond Creator Science, for example her VidCon talks or Business Insider and Publish Press profiles;
   - any 2024–2026 interview with Drew Binsky about his process (only his 2019–2020 own videos, his website and Wikipedia);
   - Yes Theory's own 2024–2026 statements on documentary craft.
2. **Transcripts that failed to load:**
   - Colin and Samir × Yes Theory, 2022 (https://www.youtube.com/watch?v=3vbZvRHpM8w). The chapters "The Role of Data…", "Hiding the Vegetables" and "How Yes Theory Makes Viral Videos" are unread.
   - Matt Dajer, "I'm Leaving YouTube" (2021).
   - Colin and Samir × Nas Daily (2021).
   - yt-dlp caption download was bot-walled all run; the browser transcript panel worked for most videos.
3. **Speaker attribution** in the 2023 Colin and Samir roundtable comes from auto-captions with no speaker labels. R11 (2023 part), Y6, 5.5 and Z1 are inferred from context.
4. **Little DATA.** None of these creators showed a retention graph or an A/B result in the sources read:
   - Jenny Hoyos gives numbers verbally (J9–J11) without screenshots.
   - Ryan Trahan's $6k vs $3.5M comparison (R12) is self-reported.
   - The only DATA here is my own catalog measurements (J19, J20, B10, Y10, R18, R20, N4, C17). These show *what they did*, not *what works*. View counts are confounded by age, topic and channel size.
5. **Conflicts:**
   - Hoyos: retention is "minimum 90%" vs "doesn't matter as much" (5.17).
   - Trahan: "sensational bangers click less" (2023) vs his 2024–25 superlative hits (5.13).
   - Yes Theory: "don't copy what others do" vs converging on the genre's title formula (5.15).
   - Casey: "story is everything" vs "a video about nothing" as his best (C9).
6. **Jenny Hoyos 2025–26 output shift (J20)** has no stated reason. It may be a separate team-run clip strategy, a test, or monetisation of subscriber asks. Do not read it as her endorsing 10 s Shorts.
7. **Variety's Netflix–Drew Binsky article** (2026) is paywalled (tollbit redirect). The deal is cited only through Wikipedia.
8. **No documented cargo-cult failure with numbers** for any third party (see 5a gap).
9. **Overlap note for the synthesiser:** Kallaway (K1–K5) overlaps with prompt 08 (hooks) and prompt 14 (analytics). Nas Daily overlaps with prompt 11 (short-form).

## Refuted or unconfirmed

Fact-check 2026-10-12. The original rows are kept as written, each followed by the reason.

- **K4** (moved from its table): `| K4 | Map a strong creator's transcript into sections (hook, intro, setup, demo, payoff), but "don't clone the flow". Keep writing and the contrarian angle manual: "I don't think you can fully build an AI factory". | PRACTITIONER | same | 2026-09-01 | 27:02, 31:16, 36:34 [CS page] |`
  - Reason: The quoted phrase "don't clone the flow" is not on the source page, and the page says close to the opposite. At 26:19 he says "I don't really like doing close clones", but at 27:02 he asks whether they "could… run a similar flow like a similar story structure, but using a different example", so he reuses the flow and changes the example. The section mapping (31:43) and "I don't think you can fully build an AI factory" are confirmed.

- **5.4** (moved from its table): `| 5.4 | Ryan Trahan: copying the top's retention and CTR tactics was "correlation is not causation". His channel grew when he dropped them (R1, R4). He also calls taking another creator's thumbnail photo and swapping in your face "theft". | PRACTITIONER | https://www.youtube.com/watch?v=wkDlfvTed1c 1:00–1:49, 8:58–9:08, 37:20–38:07 | 2022-06-06 (pre-2024) |`
  - Reason: The word "theft" is not in the source. At 37:42–38:07 he says that swapping someone else's face onto another creator's thumbnail photo "can be hurtful" and is "using it exploitatively". "Correlation is not causation" (8:58) and the R1/R4 parts are confirmed.

