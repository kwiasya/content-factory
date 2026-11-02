# 09 · Notes: structure by length (item 4) and structure without narration or face (item 5)

Researcher share: items 4 and 5 of `docs/research/prompts/09-storytelling-structures.md`. Compiled 2026-10-12.

**Method and limits.**
- 14 web searches ran before the shared search budget for this run was used up. After that the work used direct fetches of known primary pages (YouTube Help, blog.youtube, TikTok Ads Help, Meta for Business, Netflix, PLOS ONE, Crossref and Semantic Scholar DOI lookups, PMC, Creator Science episode pages) and `yt-dlp --skip-download --dump-json` metadata for named videos. That metadata gives the duration, the chapter list, the "Most replayed" heatmap and the creator-uploaded caption track.
- **How to read a heatmap.** The heatmap is YouTube's own "Most replayed" graph: 100 bins, each normalized from 0 to 1. It measures rewatching and seeking, not drop-off. YouTube's Key Moments help says "Spikes are moments in your video that were rewatched or shared" ([YouTube Help](https://support.google.com/youtube/answer/9314415)). It is real platform data for one video, so it is tagged **DATA (single-video replay graph)**, and a replay graph is not a retention curve.
- **Chapters** come from each video's chapter list as yt-dlp returned it on 2026-10-12. Some may be YouTube auto-chapters; MrBeast's generic chapter titles suggest they are.
- **Bracketed timestamps** like "[CC 10:38]" come from the creator's own English caption track (Primitive Technology writes its narration as captions).
- **Tags** follow the prompt: DATA (sample, A/B test or graph shown), PRACTITIONER (stated practice, no data shown; this includes platform guidance pages that show no data), THEORY (research or a model not tested on social video).

---

## Item 4. Structure by length (60 s / 3 min / 10 min / 20+ min)

### 4.1 Claims

| # | Claim | Tag | Source | Source date | Example (link · timestamp · where the timestamp came from) |
|---|---|---|---|---|---|
| 4.1 | YouTube defines the long-form "Intro" key moment as the share of viewers "still watched your video after the first 30 seconds". The platform treats the first 30 s as the opening window. [verified] | PRACTITIONER (tier 1, definition) | [YouTube Help: key moments](https://support.google.com/youtube/answer/9314415) | live page, read 2026-10-12 | — |
| 4.2 | YouTube benchmarks retention by length: it compares a video with "all YouTube videos of similar length" and with your 10 latest videos of similar length. A structure check should compare within a length bucket, not across buckets. [verified] | PRACTITIONER (tier 1) | [YouTube Help: key moments](https://support.google.com/youtube/answer/9314415) | read 2026-10-12 | — |
| 4.3 | Shorts can be up to 3 min (uploads from 2024-10-15, square or taller). YouTube said it would "improve recommendations for longer Shorts", which makes the "3 min" bucket a vertical-video format as well as a long-form one. [verified] | PRACTITIONER (tier 1) | [blog.youtube, "Tall updates coming to Shorts"](https://blog.youtube/news-and-events/tall-updates-coming-to-shorts/) | 2024-10-03 | — |
| 4.4 | First minute: "the first minute has the most loss". It must confirm the thumbnail promise, and the team should go "above and beyond" on it. [verified; the memo names the example "our 100 days in the circle video", not a title] | PRACTITIONER (internal production doc, no graphs in it) | [MrBeast memo "How to succeed in MrBeast production" (full text)](https://www.alexanderjarvis.com/memo-how-to-succeed-in-mrbeast-production/) | leaked 2024-09 | Memo's own example: in "Living in a Circle for 100 Days" the house is craned in "30 seconds into the video" (timestamp from the memo) |
| 4.5 | Minutes 1–3: "Stop telling people what they will be watching and start showing them." Use compressed, fast progression (they covered "multiple days in the first 3 minutes"). [verified] | PRACTITIONER | same memo | 2024 | — |
| 4.6 | Re-engagements sit at fixed points: a "3 minute re-engagement" and "at the 6 minute mark ... another re-engagement". A re-engagement is a spectacle that "fits the story". [verified] | PRACTITIONER | same memo | 2024 | — |
| 4.7 | Minutes 3–6 are "the next most important part"; put "the most exciting and interesting content that is also very simple" there. "If we can get them to watch the first half ... very high chance they'll watch to the end." [verified] | PRACTITIONER | same memo | 2024 | — |
| 4.8 | The back half holds "the not as good content" and "long explanation bits". Stakes rise as the video goes on ("stair stepping": a $1 firework, then $10, then $50…). [verified] | PRACTITIONER | same memo | 2024 | — |
| 4.9 | Ending: "Don't ever signal the end of the video unless it's to build hype for the prize or payoff". Give a "satisfying payoff at the end ... with an abrupt ending". [verified] | PRACTITIONER | same memo | 2024 | — |
| 4.10 | The memo's reference length is "the average mrbeast video is 818 seconds" (13:38). [verified; the memo itself converts 818 s to "13 minutes and 37 seconds"; 818 s is 13:38] | PRACTITIONER | same memo | 2024 | — |
| 4.11 | MrBeast's length has since roughly doubled. His 40 most recent uploads have a median of 1,657 s (27.6 min), range 194–3,479 s. The minute-3 and minute-6 rules come from a ~13-minute video and are not re-validated for 25–60-minute videos. [verified: re-measured 2026-10-12 with yt-dlp flat playlist; MrBeast median 1,657 s, range 194–3,479; Veritasium 2,001; Johnny Harris 2,299.5; Mark Rober 1,261] | DATA (descriptive, n=40, measured by this researcher) | [MrBeast /videos listing](https://www.youtube.com/@MrBeast/videos) via yt-dlp | measured 2026-10-12 | Median length of the 40 most recent uploads on other channels: Veritasium 2,001 s, Johnny Harris 2,300 s, Mark Rober 1,261 s (same method) |
| 4.12 | Long-form length vs. performance: median views rise with length and "peaks between 18–24 minutes", then declines slowly after ~24 min. Entertainment peaks around 20 min, educational around 20–22 min. Over 52% of videos under 30 min are shorter than 12 min, with clusters at 4, 8 and 10 min. [verified, wording corrected: the length section plots "median views by video duration", not median outlier score; the 52k-channel figure appears only in the headline] | DATA (300k+ high-performing 2025 videos, 52k channels; correlational; survivorship, since only high performers are in the sample; vendor) | [1of10, "What actually makes a YouTube video go viral in 2025"](https://1of10.com/blog/what-actually-makes-a-youtube-video-go-viral-in-2025/) | 2026-02-06 | — |
| 4.13 | Shorts sample: 5,400 Shorts, 33 channels, 3.3B views. Most were 20–40 s, and longer Shorts "performed much better on average". Shorts with AVD > 50 s averaged 4.1M views. Shorts under 60% viewed-vs-swiped "rarely performed well"; the best were at 70–90%. Galloway: "the goal is not simply making a long Short" but one that holds attention. [verified] | DATA (sample; 2023, before 3-min Shorts → **possibly outdated**) | [Paddy Galloway thread (Thread Reader)](https://threadreaderapp.com/thread/1646898356419981315.html) · [original on X](https://x.com/PaddyG96/status/1646898356419981315) | 2023-04-14 | — |
| 4.14 | Short structure (Jenny Hoyos): "I do a hook, and then I foreshadow, which is 2 lines, and that is usually 3 seconds or less." The foreshadow sets up what the viewer will see at the end. [verified; creatorscience.com dates the episode 2023-10-10, the YouTube upload is 2023-10-09; transcript puts the quote at 19:20, inside the 19:50 chapter boundary area] | PRACTITIONER (2023 → flag) | [Creator Science ep. page + transcript](https://creatorscience.com/podcast/jenny-hoyos/) · [video](https://www.youtube.com/watch?v=As7abwNhG7Y) | 2023-10-09 | Chapter "Jenny's Shorts Structure" starts at 19:50 (video chapter list) |
| 4.15 | Short beats follow "but therefore" storytelling, "just lots of change in the story". Each beat triggers the next. She wants "a pacing break without the pacing actually breaking". [verified] | PRACTITIONER | same | 2023-10-09 | ~21:20 and ~22:13 (episode transcript, auto-generated, approximate) |
| 4.16 | She writes the last line before filming: "I always know the last line when I'm gonna film". The ending is usually a reaction shot, and viewers must "watch it again". [verified; the "reaction shot" ending is the host's paraphrase ("it cuts to your reaction"), which Hoyos confirms with "Yes"] | PRACTITIONER | same | 2023-10-09 | ~24:07 (chapter "Jenny's Video Making Process", video chapter list) |
| 4.17 | Length vs. retention for Shorts: her best Shorts average ~34 s. She treats 90%+ retention as the floor for a breakout, and says a Short under 30 s "has to have over a 100% retention" (loops). Trimming the last 1 s of a Short (where ~25% dropped) moved retention from 83% to 88% ("that one second accumulates to 2 or 3%"). [verified, wording corrected: the 83%→88% case is a Short whose last second lost ~25%; "32 s" in the transcript is a hypothetical ("let's say you have a 32-second short"), not that video's length] | PRACTITIONER (numbers stated, graph not shown) | same | 2023-10-09 | Chapters "Importance of Retention and Rewatchability" 5:28 and "Relationship Between Short Length and Retention" 18:34 (video chapter list) |
| 4.18 | Ads on TikTok: "Introduce your content proposition in the first 3 seconds", "Prioritize your hook in the first 6 seconds". Structure: hook → unique selling points → CTA. Text at "5-10 words per second". [verified] | PRACTITIONER (tier 1; ads, no data shown) | [TikTok Ads Help: Creative best practices](https://ads.tiktok.com/help/article/creative-best-practices?lang=en) | updated 2025-06 | — |
| 4.19 | Multi-part structure in a short explainer (Kallaway's breakdown of a viral video): "started with the hook itself of the example. He played it without saying anything. Then he introduced what it was and broke it down." His section model runs hook → series intro → setup → live demo → payoff ("like the 5 parts, or they're not always 5"). [verified] | PRACTITIONER | [Creator Science ep. 316 (Kallaway)](https://creatorscience.com/podcast/kallaway/) | 2026-09-01 | ~26:19–27:02 and ~31:43–32:07 (episode transcript, approximate) |
| 4.20 | Pre-shoot test of the opening: write "three or four different intro versions, record them, listen to them back". Audits look for "retention danger zones". [verified] | PRACTITIONER (2023 → flag) | [Creator Science ep. 152 (Paddy Galloway)](https://creatorscience.com/podcast/paddy-galloway/) | 2023-06-13 | ~1:04 (episode transcript) |
| 4.21 | 20+ min beat budget, investigation doc: question cold open 13.8% → explainer 17.6% → short demo 4.5% → investigation 37.8% (4 chapters, 2:15–4:54 each) → reveal plus twist 11.9% (at 73–85% of runtime) → implications 14.5%. The top replay peak (1.0) is at 11:39, inside the demo; other peaks are at 28:27–28:47 (twist) and 6:30 (explainer). [verified: chapters and heatmap re-read 2026-10-12; all six percentages and the 11:39 / 6:30 / 28:27–28:47 peaks match] | DATA (single-video chapter list + replay graph; one example, not a sample) | [Veritasium, "Something is jamming GPS over Europe"](https://www.youtube.com/watch?v=tz23G_UXCGA) | 2026-06-05 | Chapters: 0:00 question, 4:43 "How does GPS work?", 10:46 jam demo, 12:18–25:15 hunt, 25:15 "Cosmos 2546", 28:25 twist, 29:19 implications (video chapter list); peaks from heatmap |
| 4.22 | 47 min history/engineering: origin 8.9% → mechanism 13.8% → 7 story chapters of 2:19–7:57 each → epilogue 6.5%. The replay graph stays fairly flat (decile means 0.16–0.39), and the top peaks are late (42:27, 42:55 = 89–90%, "The Naval Enigma"). Long-form can hold its biggest moment for the last 10%. [verified: chapters, segment percentages, decile range 0.16–0.39 and the 42:27/42:55 peaks match; note 42:27 is at 89%, so "last ~11%"] | DATA (single-video) | [Veritasium, "The Insane Real Engineering of the Nazi Enigma Machine"](https://www.youtube.com/watch?v=JsBZOcqZerk) | 2026-09-21 | Chapters 0:00, 4:16, 10:51, 13:10, 16:45, 22:35, 26:30, 34:27, 41:39, 44:35 (video chapter list) |
| 4.23 | 31 min thematic explainer: Intro 2:27 (7.7%), then 4 topic blocks (Border 38.3%, Trade 13.0%, Indian Ocean 21.0%, Global Politics 19.9%). The replay peak is 7:16–7:35, inside the first block. This is a list of arenas, not one question → journey → answer. [verified] | DATA (single-video) | [Johnny Harris, "India vs China, Explained"](https://www.youtube.com/watch?v=rPckDuTaSnw) | 2025-12-22 | Chapters 0:00/2:27/14:33/18:40/25:19 (video chapter list) |
| 4.24 | 19 min build/challenge video: 7 build-progress chapters of 62–126 s each (a visible new stage every ~1.5 min), then the payoff block "Final completion and opening" 10:49 → "Revealing the homes" 16:12–17:18, at 57–91% of runtime. Top replay peaks: 9:54 (1.0), 12:57 (0.70). [verified, count corrected: 7 build chapters (62–126 s) precede 10:49, not 8; payoff block 57–91% and peaks 9:54 / 12:57 match] | DATA (single-video; chapters probably auto-generated) | [MrBeast, "I Built A City To Save Kids From Illegal Labor"](https://www.youtube.com/watch?v=v9QtM6qnG50) | 2026-09-19 | Chapters 0:00 … 16:12 "Revealing the homes" (video chapter list) |
| 4.25 | ~14 min animated explainer (no chapters): replay peaks at 2:15–2:32 (16–18%), 5:13 and 8:11–8:20 (58–59%). The last decile is the lowest (0.05: outro/sponsor tail). [verified for the peak positions and last decile 0.05; "outro/sponsor tail" is the researcher's reading, not checked against frames] | DATA (single-video replay graph) | [Kurzgesagt, "Why Humanity Will Never Leave The Solar System"](https://www.youtube.com/watch?v=Cyl3X88KEgg) | 2026-08-04 | Timestamps from heatmap |
| 4.26 | Open loops: the "memory advantage for unfinished tasks" (Zeigarnik) is not supported by a 2025 meta-analysis ("no memory advantage for unfinished tasks"). It did find a "general tendency to resume tasks" (Ovsiankina). An open loop holds because viewers want to complete it, not because they remember it better. [verified] | THEORY | [Wikipedia: Zeigarnik effect, citing Ghibellini & Meier 2025, *Humanities and Social Sciences Communications*](https://en.wikipedia.org/wiki/Zeigarnik_effect) | 2025 (meta-analysis) | — |
| 4.27 | YouTube's scale context: Shorts "now averages 200 billion daily views". The letter frames creators' long videos as "shows" for "the largest screen in their home". It gives no length target. [verified] | PRACTITIONER (tier 1) | [blog.youtube, "From the CEO: What's coming to YouTube in 2026"](https://blog.youtube/inside-youtube/the-future-of-youtube-2026/) | 2026-01-21 | — |

### 4.2 Beat templates with time budgets and open loops

Legend: **L1** = the main promise loop (title, thumbnail or first frame). **Lr** = a re-engagement loop. **Lb** = a block-level question. "Derived" marks a timing interpolated from the claims above. It has not been tested and needs to be checked against the author's own retention graphs.

**60 s (Short / Reel / TikTok; target 34–60 s)**

| Beat | Time | Content | Loops open | Basis |
|---|---|---|---|---|
| Hook frame | 0–1 s | The single most striking image. It must read with sound off ("understand it without even listening to it", Hoyos ~2:19). | L1 opens | 4.14, 4.18, 5.6 |
| Foreshadow | 1–3 s | 1–2 lines (spoken or text) that name the end state. | L1 explicit | 4.14, 4.18 ("proposition in first 3 s") |
| Change beats | 3 s → end − 5 s | "But / therefore" chain. Each beat is a visible change of action or goal; a change of location alone is weaker (5.9). Derived: about 4–7 beats at 5–10 s each. | L1 + one micro-loop per beat | 4.15, 5.9, 5.10 |
| Payoff | last 3–5 s | Reveal or reaction that closes L1. Write it before shooting. | L1 closes | 4.16, 4.9 |
| Loop seam | last frame | No outro or sign-off. The last frame should invite a rewatch. | — | 4.16, 4.17, 4.9 |
| Trim rule | whole | Every second costs ~2–3% at 30–35 s. | — | 4.17 |

**3 min (long Short, or a short long-form video).** Thinnest evidence of the four lengths. Derived by scaling the 60 s and 10 min rules.

| Beat | Time | Content | Loops | Basis |
|---|---|---|---|---|
| Hook + proposition | 0–3 s / ≤6 s | Visual hook, then the promise stated. | L1 | 4.18 |
| First visible progress | by ~0:30 | The first concrete step toward the promise (derived from the memo's "crane at 0:30" in a 13 min video). | L1 | 4.4 |
| Escalating steps | 0:30–2:30 | 3–5 stair-steps of ~25–40 s, each bigger than the last. Derived: one re-engagement at ~40–50% (~1:20). This scales the memo's 3:00 and 6:00 marks, which fall at 22% and 44% of 13.6 min. | L1 + Lr | 4.6, 4.8 |
| Payoff + abrupt end | last 10–20 s | Close L1. No "thanks for watching". | — | 4.9 |
| Example | — | [Simon's Cat "Mean Machine"](https://www.youtube.com/watch?v=4d7-gkB1pKM), 3:16, no dialogue. Replay deciles are high in the first 40% (0.72/0.65/0.74), dip to 0.17 at 50–60%, recover to 0.57 at 70–80% and fall to 0.10 on the credits (heatmap). | | 5.12 |

**10 min (the MrBeast memo's native length, avg 13:38)**

| Beat | Time | Content | Loops | Basis |
|---|---|---|---|---|
| Promise delivered | 0:00–0:30 | Show that the thumbnail is true and put the spectacle on screen early. 0:30 is YouTube's "Intro" checkpoint. | L1 | 4.1, 4.4 |
| Stakes and rules | 0:30–1:00 | Who, what is at stake, how it ends. | L1 | 4.4 |
| Show-don't-tell progression | 1:00–3:00 | Compressed timeline, fast progress. | L1 | 4.5 |
| Re-engagement 1 | ~3:00 | A spectacle that fits the story. | L1 + Lr1 | 4.6 |
| Best simple content | 3:00–6:00 | The most exciting, simplest material. | L1 | 4.7 |
| Re-engagement 2 | ~6:00 | Spectacle. | L1 + Lr2 | 4.6 |
| Back half | 6:00–~9:00 | Explanations, weaker content, rising stakes. | L1 | 4.8 |
| Payoff + abrupt end | last 30–60 s | Close L1, then end at once. | — | 4.9 |

**20+ min (chapter evidence; 1of10's correlational peak is 18–24 min, 4.12)**

| Beat | Budget (% of runtime) | Content | Loops | Examples |
|---|---|---|---|---|
| Cold open / question | 8–14% (2:27–4:43) | Pose the question or show the stakes. | L1 | 4.21 (13.8%), 4.22 (8.9%), 4.23 (7.7%) |
| Context / how it works | 14–18% | The explainer the viewer needs to follow the rest. | L1 | 4.21 (17.6%), 4.22 (13.8%) |
| Early concrete payoff | ~30–35% mark, short (≈5%) | A demo or first answer; the GPS video's top replay peak sits here. | L1 + Lb | 4.21 (11:39) |
| Body blocks | 3–7 chapters, ~2–8 min each | Each block opens and closes its own Lb. Build videos: a new visible stage every ~1–2 min. | L1 + one Lb per block | 4.21, 4.22, 4.24 |
| Main reveal | lands at ~73–90% | Close L1 (identity, outcome, final reveal). | L1 closes | 4.21 (25:15–29:19), 4.22 (peak 42:27), 4.24 (16:12) |
| Implications / epilogue | 6–15% | "What it means", aftermath. Replay intensity is low here. | — | 4.21 (14.5%), 4.22 (6.5%) |

### 4.3 Negative and contested (item 4)

- **The minute marks may be dated.** The 3:00 and 6:00 re-engagement marks come from a doc built around an 818 s average (4.10). MrBeast's own median is now ~1,657 s (4.11). Nothing published shows whether the marks scale proportionally or stay fixed in minutes. Contested by default.
- **Length studies disagree.**
  - Galloway 2023: longer Shorts do better.
  - Hoyos 2023: ~34 s is her sweet spot, and under 30 s needs over 100% retention.
  - 1of10 2026: long-form peaks at 18–24 min.
  - All three are correlational. 1of10 sampled only high performers, and Galloway's sample predates 3-min Shorts.
- **Unverified benchmark numbers.** These circulate only through secondary pages, and the primary report was not found:
  - Retention Rabbit 2025 ("23.7% average retention", "55% lost in first 60 s", "5–10 min highest at 31.5%"; e.g. [research.stripo.email](https://research.stripo.email/youtube-benchmarks)). Do not use them as rules.
  - Shorts "viewed vs swiped" thresholds of 70%, 75–80% and 81% from vendor blogs conflict with each other. YouTube publishes no universal threshold (4.2).
- **TikTok's "5–10 words per second" for on-screen text** (4.18) is far faster than subtitle norms (5.4, 5.5). It is probably meant for ads with very short text, and it is contested for narrative text.
- **The Zeigarnik effect is weak.** Open-loop advice that relies on a memory advantage for unfinished items rests on an effect a 2025 meta-analysis did not find (4.26).
- **Ending tails.** Several replay graphs fall to their minimum after the final payoff (Kurzgesagt 0.05, MrBeast City 0.05, Simon's Cat 0.10, Primitive Technology Bow & Arrow 0.02–0.06). This fits the memo's "abrupt ending" rule but proves nothing: replay is not retention.

---

## Item 5. Structure without narration and without a face

### 5.1 Claims

| # | Claim | Tag | Source | Source date | Example (link · timestamp · origin) |
|---|---|---|---|---|---|
| 5.1 | Feed video is mostly watched muted. "Since most video ads in mobile feed are viewed without sound, make sure to express your message visually." "41% of videos were basically meaningless without sound." Captions raised view time by 12%: "captioned video ads increase video view time by an average of 12%". [verified for the three quotes; the ~2016 date could not be confirmed (page undated, search budget exhausted)] | DATA (Meta internal tests; method not shown; ~2016, Facebook Feed ads → **outdated, not Reels**) | [Meta for Business: "Updated features for video ads"](https://www.facebook.com/business/news/updated-features-for-video-ads) | ~2016 (page undated) | — |
| 5.2 | TikTok's ad basics include "using sound/ music" and "captions or text overlays to provide context". Text pace: "5-10 words per second". [verified] | PRACTITIONER (tier 1) | [TikTok Ads Help: Creative best practices](https://ads.tiktok.com/help/article/creative-best-practices?lang=en) | 2025-06 | — |
| 5.3 | Lead with the picture, not the explanation: "Stop telling people what they will be watching and start showing them." [verified] | PRACTITIONER | [MrBeast memo](https://www.alexanderjarvis.com/memo-how-to-succeed-in-mrbeast-production/) | 2024 | — |
| 5.4 | Viewers keep up with fast subtitles. At 12, 16 and 20 characters per second, speed had no effect on comprehension. Slow subtitles caused more re-reading and were "less enjoyable". Viewers spent ~40–60% of display time reading, so they still watched the picture half the time. [verified] | THEORY (peer-reviewed eye-tracking on film clips, not social video) | [Szarkowska & Gerber-Morón 2018, PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0199331) | 2018-06-19 | — |
| 5.5 | Industry ceiling for reading speed: up to 20 cps for adult programs, 17 for children's, 42 characters per line, at most 2 lines. [verified] | PRACTITIONER (industry standard) | [Netflix English (USA) Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide) | live page, read 2026-10-12 | — |
| 5.6 | With no narration, the first frame has to work on its own: "You need to understand it without even listening to it." [verified; transcript timestamp is 2:34, not ~2:19] | PRACTITIONER | [Creator Science: Jenny Hoyos](https://creatorscience.com/podcast/jenny-hoyos/) | 2023-10-09 | ~2:19 / 9:41 (transcript; chapter "Crafting the Perfect 1st Frame Hook" 9:41 from the video chapter list) |
| 5.7 | Show the result first, then explain: the viral example "played it without saying anything. Then he introduced what it was". [verified] | PRACTITIONER | [Creator Science ep. 316: Kallaway](https://creatorscience.com/podcast/kallaway/) | 2026-09-01 | ~26:19 (transcript) |
| 5.8 | Viewers split continuous activity into events at moments of prediction error: changes in action, goals, location, characters or objects. Information at those boundaries gets more processing and is remembered better. [verified] | THEORY | [Zacks et al. 2007, *Psychological Bulletin* (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2852534/) | 2007 | — |
| 5.9 | In edited film, "discontinuities in action had the biggest impact on behavioral event segmentation and discontinuities in space and time had minor effects". A cut to a new place while the same action continues (walking on) registers only weakly as a new beat. A new action or goal does. [verified; the abstract says space/time discontinuities had "minor effects", so read "does not register" as "registers only weakly"] | THEORY (fMRI plus segmentation of a commercial film) | [Magliano & Zacks 2011, *Cognitive Science* (PMC3208769)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3208769/) | 2011 | — |
| 5.10 | Across 150 Hollywood films (1935–2005), each shot's length became more correlated with its neighbours, with spectra approaching 1/f. The authors suggest this "may help harness observers' attention". Pacing works as runs of fast and slow shots, not as a uniform cut rate. [verified] | THEORY (film corpus) | [Cutting, DeLong & Nothelfer 2010, *Psychological Science*](https://doi.org/10.1177/0956797610361679) (abstract via [Crossref](https://api.crossref.org/works/10.1177/0956797610361679)) | 2010 | — |
| 5.11 | Silent process format: Primitive Technology has "no speaking, and only minimal ambient sound". A "closed-caption narrated account" carries the progress, and each video narrates one or more projects. ~11M subscribers. [verified, wording corrected: Wikipedia says each video narrates "one or more projects", not always one; the Cord drill and Pump drill video (5.13) has two] | PRACTITIONER (format description) | [Wikipedia: Primitive Technology](https://en.wikipedia.org/wiki/Primitive_Technology) | infobox 2026-03-21 | See 5.12–5.14 |
| 5.12 | **Replay peaks sit on the "it works" moments, not on the finished object.** "Tiled Roof Hut" (14:09, 91M views): the top replay bin (1.0) is 10:19, between [CC 10:08] "Fire at the front moves under stones" and [CC 10:22] "Chimney added at back to enhance draft". The next peaks are 10:28–10:45 ([CC 10:38] "Heated platform is warm and makes a good bed") and 12:27 ([CC 12:28] "Putting door in place", 21 s before [CC 12:48] "Completed hut"). [verified: heatmap bins and caption cues 10:08, 10:22, 10:38, 12:28, 12:48 match; the 0:00 bin (0.98) is the second-highest overall] | DATA (single-video replay graph) | [Primitive Technology: Tiled Roof Hut](https://www.youtube.com/watch?v=P73REgj-3UE) | uploaded 2015-09-05; heatmap read 2026-10-12 (**old upload**) | Timestamps from heatmap and the creator caption track |
| 5.13 | "Cord drill and Pump drill" (8:24, 84M views): replay peaks at 2:26–2:41 (1.0 / 0.93 / 0.83), where [CC 2:38] reads "As the strings are pulled out wards, the spindle spins" (the first working drill), and at 3:11 (0.63), where [CC 3:13] reads "A coal has been produced". Two mid-video payoffs, not one final one. [verified; the top bin 2:31–2:36 precedes the 2:38 caption, so mapping it to "first working drill" is inferred from captions, not frames] | DATA (single-video) | [Primitive Technology: Cord drill and Pump drill](https://www.youtube.com/watch?v=ZEl-Y1NvBVI) | 2016-01-22 | heatmap + caption track |
| 5.14 | "Bow and Arrow" (5:54, 75M views): peaks at 2:21–2:57, covering [CC 2:22] stringing, [CC 2:39] "Finished bow" and [CC 2:55] "A bush turkey". The shooting test ([CC 3:54] "Shooting a log target at 10 meters") sits in a 0.56 decile. The last 20% falls to 0.02–0.06. Viewers replay the build and a surprise, and the tail after the test is barely replayed. [verified] | DATA (single-video) | [Primitive Technology: Bow and Arrow](https://www.youtube.com/watch?v=SLoukoBs8TE) | 2016-03-23 | heatmap + caption track |
| 5.15 | Music-free, talk-free walk: the description says "No talking, original surround sound only", and the 11 chapters name each room (34–361 s each). **All six top replay bins (0.64–1.0) contain a chapter boundary**: 8:35–8:56 holds "Fishy room" 8:48; 4:07–4:28 holds "Star fall room" 4:22; 18:13–18:34 holds "Flower in outer space" 18:26; then 15:44, 24:43 and 21:54. In a no-voice walk, the unit of progress is "a new place appears". **Confound:** chapter clicks land exactly on boundaries, so part of this is navigation. [verified] | DATA (single-video; confounded) | [Rambalac, "Tokyo teamLab Planets full walk"](https://www.youtube.com/watch?v=C2lMOj2z_4U) | 2023-09-23 | Chapter list + heatmap |
| 5.16 | Text metadata as stakes or setting in a no-voice walk: Rambalac walk descriptions often open with time, temperature and distance ("🕒 12/29 4:15pm 🌡️ 0℃ 🚶‍♂️3km") and a map link. A long 1:43:48 night walk with no chapters has a flat, low replay graph (deciles 0.02–0.19) apart from 0:00, which suggests ambient or background viewing rather than beat-driven viewing. [verified, wording corrected: not every description has the 🌡️/🚶 line; the teamLab walk (5.15) opens "🕒 19 FEB 2022 No talking…" with no temperature or distance] | DATA (single-video) + PRACTITIONER (format) | [Rambalac, "Heavy Snow in Ginzan Onsen"](https://www.youtube.com/watch?v=QytjUFgcmWw) · [Rambalac, "Night Japan – walking from Kanagawa to Tokyo"](https://www.youtube.com/watch?v=tvaMTu6vbEM) | 2023-01-01 · 2023-03-29 | Description text; heatmap |
| 5.17 | A silent recipe uses on-screen text as structure. "[No Music] How to make Boiled Dumplings" (13:21, 4.0M views) has no talk and no music, and its chapters are ingredient quantities: "1/2tsp salt" 1:17, "10g ginger" 2:45, "white pepper" 5:20. The top replay region is 5:44–6:16 (0.44–0.75) within the last chapter. [verified; "white pepper" is an ingredient name, not a quantity] | DATA (single-video) | [Peaceful Cuisine, "[No Music] How to make Boiled Dumplings"](https://www.youtube.com/watch?v=Q_gnVSx_v6Y) | 2016-12-08 | Chapter list + heatmap |
| 5.18 | Animation with no dialogue: stakes are framed outside the video (description: "Will they win?!"), and inside the video by character goals. For the replay profile see the 3 min template in 4.2. [verified] | PRACTITIONER (format observation by the researcher) [tag → PRACTITIONER: the claim is about how stakes are framed; the replay graph does not measure that and is only cross-referenced] | [Simon's Cat, "Mean Machine!"](https://www.youtube.com/watch?v=4d7-gkB1pKM) | 2023-06-15 | heatmap |

### 5.2 How progression, stakes and payoff are carried without voice

| Function | Carrier with no voice and no face | Evidence |
|---|---|---|
| Promise (L1) | First frame shows the end state or the strangest image; title/overlay names the goal ("Tiled Roof Hut", "Will they win?!"). | 5.6, 5.7, 5.11, 5.18 |
| Progression | A visible change of action or goal at each beat. Captions or chapters can label steps ([CC] "Making stone axe" → "Completed hut"; chapters "Entrance" → "Into flowers"). A change of place with the same action is weak (5.9). | 5.8, 5.9, 5.12, 5.15, 5.17 |
| Stakes | A goal that could fail, made visible (the tile kiln, the first spin of the drill), or numbers in text (time, °C, km, quantities). | 5.13, 5.16, 5.17 |
| Payoff | The functional test ("it works") or a reveal of a new space; mid-video payoffs get as many replays as the end. | 5.12–5.15 |
| Pace | Correlated runs of shot lengths; text at ≤ ~20 cps (subtitle norm) unless the text is a short label. | 5.4, 5.5, 5.10 |

### 5.3 Negative and contested (item 5)

- **Sound-off share is unsettled.**
  - Meta's "most feed video ads are viewed without sound" and "+12% with captions" are ~2016 Facebook Feed ad figures.
  - Secondary pages give conflicting Reels numbers, from "60%" to "80%+" watched with sound, attributed to Meta without a primary link.
  - Treat "design for sound-off" as a safety rule, not a measured share for Reels or Shorts in 2026.
- **Text speed conflicts.** TikTok says 5–10 words/s (5.2). The subtitle literature says 12–20 cps is comfortable (5.4) and Netflix caps adults at 20 cps (5.5), which is roughly 3–4 words/s. 5–10 words/s only works for short labels, not for sentences.
- **Primitive Technology is not text-free.** Its "silent" format still narrates through optional captions, so it does not show that pure picture alone carries a 10+ min process video.
- **No-voice walks can become ambience.** The 1:43:48 night walk shows almost no replay structure (5.16). The format can be consumed as background, which is a different job from a 45–60 s Reel.
- **Replay peaks are not drop-off.** All heatmap claims show where people rewatch or seek, not where they leave. The chapter-boundary peaks in 5.15 are partly caused by chapter navigation.
- **Old evidence.** The Primitive Technology videos are 2015–2016 uploads. Their replay data is current, but the viewing context (2015 recommendations) differs from 2026 Shorts and Reels.

---

## Gaps

1. **Search budget.** The shared search budget ran out after 14 queries. Sources that likely exist but could not be located:
   - Film Booth, Colin & Samir and vidIQ material on re-hooks, ideal intro length and 3 min / 10 min structure.
   - A primary Paddy Galloway source on long-form structure.
   - YouTube's own Shorts help page defining "Viewed vs. swiped away".
   - The current TikTok Creator Rewards rule requiring videos over 1 minute (the help page did not render, and the newsroom URL returned unrelated text).
2. **No source counts open loops per length.** All loop counts in 4.2 are derived from MrBeast's two fixed re-engagements and Hoyos's single foreshadow. No dataset links the number of loops to retention.
3. **3 min is the weakest bucket.** No practitioner or analyst gives a 3 min template. The one in 4.2 is a proportional scaling and untested.
4. **The minute-3 and minute-6 rule vs. today's 25–60 min MrBeast videos** is unresolved: fixed minutes or proportional?
5. **Instagram specifics were not re-verified.** Not checked against a primary page this session: Mosseri's January 2025 ranking signals, the 3 min Reels limit, "over 3 min not recommended to non-followers", and the Reels skip-rate metric. The only page reached, Buffer, does not link Mosseri's statement. Repo research 06 cites secondary trackers.
6. **Modality principle (narration vs. on-screen text).** The Ginns 2005 meta-analysis ([DOI](https://doi.org/10.1016/j.learninstruc.2005.07.001)) was blocked (403) and had no abstract via the APIs. Whether text-only explainers lose comprehension compared with narrated ones remains unsourced here.
7. **Screencasts without narration.** No example or source was found. The no-voice evidence covers process videos, walks, recipes and animation only.
8. **Reel or Short music-only examples with data.** Instagram and TikTok expose no replay or retention graph publicly. The no-voice evidence is long-form YouTube only, and it transfers to 45–60 s Reels by analogy, not by measurement.
9. **Heatmap event mapping.** Peaks were mapped to content only where creator captions or chapters exist (Primitive Technology, Rambalac teamLab, Peaceful Cuisine). For Ginzan Onsen, Kurzgesagt and Mark Rober the peak positions are known but the on-screen events are not, because no frames were downloaded.
10. **Conflicting length-performance findings.** Galloway 2023 (longer Shorts win), Hoyos 2023 (~34 s), 1of10 2026 (18–24 min long-form) and the Retention Rabbit figures (unverified) are all correlational and come from different samples. They have not been reconciled.

---

## Refuted or unconfirmed

Fact-check pass 2026-10-12. All 45 claims in 4.1 and 5.1 were checked against their cited sources: the YouTube heatmaps, chapters and caption tracks were re-pulled with yt-dlp (mweb client), the length medians in 4.11 were re-measured, and the web sources were re-read. No claim was refuted outright. One tag was corrected (5.18). Details that were wrong were corrected in place, and each fix is flagged in that row's bracket note: 4.12 metric, 4.17 the "32 s" detail, 4.24 chapter count, 5.11 "one project", 5.16 "every description", 5.9 wording.

Partly unconfirmed (the claim stands, one detail could not be confirmed):
- 5.1: the Meta page is undated, so its ~2016 date is unconfirmed. The web-search budget ran out before the date could be checked.
- 4.25: "outro/sponsor tail" is an interpretation. No frames were checked.
- 5.13: the top bin comes ~2 s before the "spindle spins" caption, so tying it to the first working drill is an inference.
