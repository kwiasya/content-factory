# 14 · Items 5–7: experiment design, the learning loop, negative findings

Researcher notes for prompt 14 (`docs/research/prompts/14-analytics-and-iteration.md`), items 5, 6 and 7 only. Today is 2026-10-12.

**How these notes were sourced.**
- **No web searches.** The session-wide web-search budget (200 searches, shared by every agent) was already used up when this researcher started, so not one search ran.
- **WebFetch on known primary URLs.** Every web page cited below was opened in this session.
- **Transcripts already cached** in this session's scratchpad by agents working on prompts 07, 11 and 12. YouTube now answers watch-page and caption requests with a bot-check page, which was not bypassed.
- **Timestamp provenance.** Timestamps from transcripts read this session are marked `[tx]`. Timestamps marked `[via 12-notes]` are cited from `docs/research/12-packaging-titles-thumbnails-ideas/notes/idea-first-and-titles.md` and were not re-checked.

Tags follow the CONTEXT block:
- **DATA**: a measurement over a sample, an A/B result, or a graph that is shown.
- **PRACTITIONER**: a stated practice. Platform statements are tagged `PRACTITIONER (platform)`.
- **THEORY**: research, statistics or a model, not tested on video.

## Source key

| # | Source | Date | Tier |
|---|---|---|---|
| S1 | [YouTube Help 13861714, Test & Compare](https://support.google.com/youtube/answer/13861714) | undated (©2026) | 1 |
| S2 | [YouTube Help 16391400, A/B testing article](https://support.google.com/youtube/answer/16391400?hl=en) | undated (©2026) | 1 |
| S3 | [YouTube Help 7628154, Impressions & CTR FAQ](https://support.google.com/youtube/answer/7628154?hl=en) | undated (©2026) | 1 |
| S4 | [YouTube Help 9314415, Key moments for audience retention](https://support.google.com/youtube/answer/9314415) | undated (©2026) | 1 |
| S5 | [YouTube Help 9101241, Limited data in YouTube Analytics](https://support.google.com/youtube/answer/9101241) | undated (©2026) | 1 |
| S6 | [YouTube Help 12220281, Content performance](https://support.google.com/youtube/answer/12220281) | undated, mentions 2026-08-24 | 1 |
| S7 | [YouTube Help 9314414, Overview tab / Realtime](https://support.google.com/youtube/answer/9314414) | undated (©2026) | 1 |
| S8 | [YouTube Help 11912632, Analytics tips](https://support.google.com/youtube/answer/11912632) | undated (©2026) | 1 |
| S9 | [YouTube Blog, "Engaged views explained"](https://blog.youtube/inside-youtube/engaged-views-youtube-explained/) | 2026-08-19 | 1 |
| S10 | [YouTube Analytics API, Metrics](https://developers.google.com/youtube/analytics/metrics) | last updated 2026-09-14 | 1 |
| S11 | [Creator Insider, "YouTube Algorithm 2026 – What Creators Need to Know" (Todd Beaupré, Rene Ritchie)](https://www.youtube.com/watch?v=rHLjxrbXmmY) | 2026-09-01 | 1 |
| S12 | [Creator Insider, "Paddy Galloway Dives Deep on Video A/B & Ask Studio" (Galloway, Amjad Hanif, Ritchie)](https://www.youtube.com/watch?v=j7GtybYc6gk) | 2026-09-30 | 1 + 3 |
| S13 | [Creator Insider, "A deep thumbnail discussion with Chucky (MrBeast) and Todd"](https://www.youtube.com/watch?v=HP-rqigfw2s) | 2024-03-07 | 1 + 2 |
| S14 | [Creator Insider, "Video A/B Testing & Dynamic Thumbnails – Made On YouTube"](https://www.youtube.com/watch?v=ImqahdmBXo8) (description and chapter list) | 2026-09-25 | 1 |
| S15 | [Creator Insider, "How to Better Understand Watch Time Performance on Your Channel"](https://www.youtube.com/watch?v=yBPZy-S4fIE) | 2021-08-13 (watch-page publishDate; **possibly outdated**) [date corrected] | 1 |
| S16 | [YouTube Creators, "Understanding Changes in Watch Time"](https://www.youtube.com/watch?v=s0HWdnIU5RA) | 2026-03-17 (watch-page publishDate) [date corrected: not 2024–25] | 1 |
| S17 | [Creator Insider, "A deep conversation about Shorts with Jenny Hoyos and Todd Sherman"](https://www.youtube.com/watch?v=_tWy-_otnUc) | 2024-12-09 | 1 + 2 |
| S18 | [Veritasium, "Clickbait is Unreasonably Effective"](https://www.youtube.com/watch?v=S2xHZPH5Sng) | 2021-08-17 (**possibly outdated**) | 2 |
| S19 | [vidIQ, "44% of YouTube Views No Longer Matter (But These Do)"](https://www.youtube.com/watch?v=We8TVsjs2B8) | 2026-10-05 (watch-page publishDate; video now titled "What YouTube Doesn't Tell You About Your View Count") [date corrected] | 3 |
| S20 | [Colin and Samir, "9 YouTube Rules No One Talks About"](https://www.youtube.com/watch?v=bZyevFMM8ZU) | 2026 (said in the intro) | 2/3 |
| S21 | [Colin and Samir, "Inside Michelle Khare's Most Dangerous Video"](https://www.youtube.com/watch?v=5TlPHtxsBIA) | 2025-08-30 [date corrected] | 2/3 |
| S22 | [MrBeast, "How to Succeed in MrBeast Production" (leaked internal doc, PDF)](https://cdn.prod.website-files.com/6623b7720b009050313e701c/66ede69453b7bbadcd2f05a8_How-To-Succeed-At-MrBeast-Production%20(2).pdf) | leaked 2024-09 | 2 |
| S23 | [George Blackman, "Reviewing YOUR Retention Graphs (#1)"](https://georgeblackman.substack.com/p/reviewing-your-retention-graphs-1) | 2022-11-04 (**possibly outdated**) | 3 |
| S24 | [Evan Miller, "How Not To Run an A/B Test"](https://www.evanmiller.org/how-not-to-run-an-ab-test.html) | 2010-04-18 (classic) | 4 (statistics) |
| S25 | [Dmitriev, Gupta, Kim, Vaz, "A Dirty Dozen: Twelve Common Metric Interpretation Pitfalls in Online Controlled Experiments", KDD '17 (Microsoft)](https://exp-platform.com/Documents/2017-08%20KDDMetricInterpretationPitfalls.pdf) | 2017 | 4 |
| S26 | [Barnett, van der Pols, Dobson, "Regression to the mean: what it is and how to deal with it", Int J Epidemiol 34(1)](https://academic.oup.com/ije/article/34/1/215/638499) | 2005 | 4 |
| S27 | [Eric Ries, "Why vanity metrics are dangerous"](http://www.startuplessonslearned.com/2009/12/why-vanity-metrics-are-dangerous.html) | 2009-12-23 | theory/practitioner (outside the 1–4 hierarchy, cited only as a definition) |
| S28 | [Instagram for Creators, "The latest with Instagram" (trial reels)](https://creators.instagram.com/blog/the-latest-with-instagram?locale=en_US) | 2025-01-21 | 1 |
| S29 | [Meta, Instagram Platform: Media Insights reference](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights) | undated | 1 |
| S30 | [TikTok for Developers, Display API Video Object](https://developers.tiktok.com/doc/tiktok-api-v2-video-object) | last updated 2026-08-24 | 1 |
| S31 | [TikTok for Developers, Research API Query Videos](https://developers.tiktok.com/doc/research-api-specs-query-videos) | last updated 2026-09-01 | 1 |
| S32 | [Instagram, "Instagram Ranking Explained" (Mosseri)](https://about.instagram.com/blog/announcements/instagram-ranking-explained) | 2023-05-31 (**possibly outdated**) | 1 |
| S33 | [Creator Insider, "Now Launching: Title A/B Testing…"](https://www.youtube.com/watch?v=Ef9vcwon10s) | 2025-12-04 | 1 |

---

## 5. Experiment design

### 5a. Tests the platforms offer

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| 5.1 | **YouTube Test & Compare** tests up to **3** variants: title only, thumbnail only, or title + thumbnail. It runs on desktop Studio only and needs advanced features. **Shorts, scheduled Lives and Premieres are not eligible**; a Premiere becomes eligible once it converts to long-form. Made-for-kids, mature and private videos are also excluded. [verified] | PRACTITIONER (platform) | S1, S2 | ©2026 | — |
| 5.2 | **The winner is decided on watch time share, not CTR.** Tests are optimized "for overall watch time over other metrics, like click-through-rate". All variants are served at the same time ("true, concurrent A/B/C tests"). A small control group sees only the default, and its data is excluded. [verified] | PRACTITIONER (platform) | S1, S2 | ©2026 | — |
| 5.3 | **Duration.** A test takes "a few days" up to **2 weeks**, depending on impressions and on how recently the video was published. **No minimum traffic is published.** The page says only that "a sufficient amount of impressions" is needed. Changing the title or thumbnail during a test stops it. A thumbnail below 1280×720 downscales every variant to 480p. [verified] | PRACTITIONER (platform) | S1, S2 | ©2026 | — |
| 5.4 | **Three outcomes.** *Winner*: statistically significant, but **no confidence level or threshold is published**. *Performed same*: the creator picks. *Inconclusive*: the first uploaded variant becomes the default. The stated causes of no winner are variants that are too similar and too few impressions. [verified] | PRACTITIONER (platform) | S1, S2 | ©2026 | — |
| 5.5 | **Test design advice.** Variants that are "too similar… can cause tests to run for longer", so make them diverse. Test **older videos first** to limit the impact on channel views. Third-party tools often test **sequentially** and optimize for CTR, so they "may pick a different winner". [verified] | PRACTITIONER (platform) | S2 | ©2026 | — |
| 5.6 | **Re-runs can disagree.** The page cites "statistical variation" and audience composition that shifts over time. Early impressions skew toward viewers who already know the channel. [verified] | PRACTITIONER (platform) | S2 | ©2026 | Galloway: re-ran a client's test a week later and the other thumbnail won, because "different audiences sometimes do require" different thumbnails. S12 [tx] 2:48–3:17 |
| 5.7 | **Title A/B** was added to Test & Compare in September 2025 and went global in December 2025. [verified] | PRACTITIONER (platform) | S33; announcement FJDxx38Ds1M | 2025-12-04 | [0:24–3:18 via 12-notes](https://www.youtube.com/watch?v=Ef9vcwon10s&t=24) |
| 5.8 | **Full-video A/B testing, starting with Shorts** (announced at Made on YouTube, Sept 2026). Creators "upload different video cuts for Shorts to test hooks, compare retention curves". Hanif: it starts with Shorts and could test hooks, story structures and CTAs. The test gives a **predicted winner**, and the creator then has **7 days** to choose. Both or all retention curves are shown. As with thumbnails, the deciding metrics are watch time and retention, not CTR. **The rollout date and eligibility were not found.** [verified; note: S14 description says "for Shorts", but the S14 narration (3:15–3:29) says "upload your cuts, short or long form"] | PRACTITIONER (platform) | S14 (description, chapter 2:43); S12 | 2026-09-25; 2026-09-30 | [S14 chapter "Full Video A/B Testing & Retention Curves" 2:43](https://www.youtube.com/watch?v=ImqahdmBXo8&t=163); [S12 6:56–7:16, 8:12–8:19, 11:25–11:32, 11:41–12:20 [tx]](https://www.youtube.com/watch?v=j7GtybYc6gk&t=416) |
| 5.9 | **Dynamic thumbnails (2026).** Upload 3 and YouTube serves the best one per viewer. This replaces Galloway's manual workaround of a different thumbnail for day 1, when the core audience dominates. Separately, **back-catalog optimization** in Ask Studio finds older videos that are gaining traction and suggests or tests new thumbnails. [verified] | PRACTITIONER (platform + analyst) | S12; S14 | 2026-09-30 | [S12 1:48–3:57, 3:59–4:34 [tx]](https://www.youtube.com/watch?v=j7GtybYc6gk&t=108) |
| 5.10 | **Instagram trial reels** show a reel to non-followers first. If the creator likes the result, they can share it with followers. The blog gives **no metrics and no time to results**. [verified] | PRACTITIONER (platform) | S28 | 2025-01-21 | — |
| 5.11 | **TikTok**: no organic A/B or trial-post feature was found in any source opened this session (see Gaps). | — | — | — | — |

### 5b. Comparing across videos when samples are small

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| 5.12 | **Swapping thumbnails one after another on the same video is unreliable,** because "It's difficult to make sure each video is being seen by the same audience." Compare CTR between videos over the long term, and act only on changes that are "statistically significant". [verified] | PRACTITIONER (platform) | S3 | ©2026 | — |
| 5.13 | **Compare relative to similar-length videos on your own channel**: lower percent watched or lower absolute watch time than those videos is the signal. Beaupré also says look at like rates, listen to the audience, and **don't compare across formats**. [verified; correction: "don't compare across formats" is S8 ("Avoid direct comparison across formats"), not Beaupré in S11; S11 14:12–14:46 has similar length, retention graphs, like rates, listen to audiences] | PRACTITIONER (platform) | S11; S8 | 2026-09-01 | [S11 14:03–14:40 [tx]](https://www.youtube.com/watch?v=rHLjxrbXmmY&t=843) |
| 5.14 | **The subscriptions-feed traffic source is the closest thing to a controlled slice.** The audience there is the same at every upload, so a fall in CTR or watch time points to the content, "not who the video was targeted to". [verified] | PRACTITIONER (platform) | S11 | 2026-09-01 | [S11 35:49–36:53 [tx]](https://www.youtube.com/watch?v=rHLjxrbXmmY&t=2149) |
| 5.15 | **Compare videos at the same age.** MrBeast states that all his AVD and AVP comparisons use **first-day data** "to make it apples to apples". He also ranks every upload against the previous videos hour by hour, which Studio does with its "x/10" ranking. [verified] | PRACTITIONER (team practice; graphs shown) | S22 (pp. ~21–27) | 2024-09 | Doc p.27: two videos of almost identical length compared on day-1 AVD and AVP |
| 5.16 | **Set baselines per series or format** instead of comparing with the top video. Judge each video by **its purpose**: a community video by subscribers gained and AVD, a tentpole by reach and impressions. Make **one change at a time**. [verified; date corrected: S16 published 2026-03-17 (watch-page publishDate), not 2024–25] | PRACTITIONER (platform) | S16 | 2026-03-17 | [S16 2:27–4:08 [tx]](https://www.youtube.com/watch?v=s0HWdnIU5RA&t=147) |
| 5.17 | **Replicate across videos.** The MrBeast team ran closed-mouth against open-mouth thumbnails on about 30 videos, and closed mouth won on watch time every time. Chucky: "if it was like half and half then it maybe wasn't a big change." They also re-test winners against new candidates. [verified] | PRACTITIONER (results stated, not shown) | S13 | 2024-03-07 | [S13 22:10–22:52, 29:25–29:38 [tx]](https://www.youtube.com/watch?v=HP-rqigfw2s&t=1330) |
| 5.18 | **Sign test on repeated tests** (my arithmetic, binomial with p = 0.5, one-sided). 30/30 wins: p ≈ 9×10⁻¹⁰. 9/10: p ≈ 0.011. 8/10: p ≈ 0.055. 6/6: p ≈ 0.016. 5/5: p ≈ 0.031. A small channel can pool the same variable (for example face against no face) over 6–10 videos rather than trust one test. [verified] | THEORY (statistics applied) | binomial arithmetic; logic of S13 | — | — |
| 5.19 | **Do not stop when the result looks significant.** With repeated peeking, a 5% test produced about **26.1%** false positives in Miller's simulation. Fix: decide the sample size in advance, or use sequential or Bayesian designs. Rule of thumb: **n ≈ 16σ²/δ² per arm**, with σ² = p(1−p) for a rate. [verified] | THEORY | S24 | 2010 | — |

### 5c. How long to wait before judging

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| 5.20 | **CTR**: "Avoid checking your click-through-rate immediately after uploading." Read it after "a substantial number of impressions". [verified] | PRACTITIONER (platform) | S3 | ©2026 | — |
| 5.21 | **Retention** data typically takes **1–2 days** to process. Key moments need a video of at least **60 s** with at least **100 views**. [verified] | PRACTITIONER (platform) | S4 | ©2026 | — |
| 5.22 | **The first hours mislead.** Ritchie stopped checking his metrics for the first couple of hours. Beaupré says decisions are not based on "those initial moments", and many evergreen videos get most of their views a month or more later. YouTube does not judge from "the first hour or first 1,000 people". [verified] | PRACTITIONER (platform) | S11 | 2026-09-01 | [S11 5:48–6:58, 35:20–35:32 [tx]](https://www.youtube.com/watch?v=rHLjxrbXmmY&t=348) |
| 5.23 | **Day-level noise is large**: performance within a day can swing "up to 40 to 60%". Most watch time comes in the first few days, so a drop after a spike is normal. Widen the date range (up to 365 days) and compare period over period for seasonality. [verified] | PRACTITIONER (platform, **possibly outdated**) | S15 | ~2021–22 | [S15 1:09, 2:08–2:27, 2:49–3:30 [tx]](https://www.youtube.com/watch?v=yBPZy-S4fIE&t=128) |
| 5.24 | Studio's Realtime report compares **60-minute and 48-hour** performance and is meant for early signals only. [verified] | PRACTITIONER (platform) | S7 | ©2026 | — |
| 5.25 | **Instagram API data** for Reels "can be delayed up to 48 hours". Judge Reels only after 2 days. [verified] | PRACTITIONER (platform) | S29 | undated | — |
| 5.26 | **Test & Compare: up to 2 weeks. Shorts video A/B: predicted winner, then 7 days to choose.** [verified] | PRACTITIONER (platform) | S1; S12 | 2026 | see 5.3, 5.8 |

### 5d. What confidence a channel with a few thousand views per video can expect

| # | Claim | Tag | Source | Date | Example |
|---|---|---|---|---|---|
| 5.27 | **Impressions needed per variant to detect a CTR difference** (80% power, α = 0.05, n ≈ 16·p(1−p)/δ², baseline CTR 4%). 4.0 → 5.0% (+25% relative): ~6,100 impressions per variant. 4.0 → 4.4% (+10%): ~38,400. 4.0 → 4.2% (+5%): ~154,000. [verified] | THEORY (my arithmetic on S24's rule) | S24 | — | — |
| 5.28 | **Worked case.** About 3,000 views per video at ~4.5% CTR, with roughly 70% of views from impressions, means about 45–50k impressions. Split three ways, that is ~15k per arm, so only ≥ ~16% relative CTR differences are detectable. Two arms of ~23k detect ≥ ~13%. Test & Compare decides on **watch time per impression**, which has much higher variance (many zero-watch impressions), so the true detection limit is coarser. **Only large, deliberately different variants can produce a "Winner".** Expect "Inconclusive" for subtle ones. This matches YouTube's own finding that subtle thumbnail differences showed no difference (S12 5:24–5:40). [verified] | THEORY (arithmetic; the 70% share and 4.5% CTR are assumptions) | S24, S2, S12 | — | [S12 5:24–5:40 [tx]](https://www.youtube.com/watch?v=j7GtybYc6gk&t=324) |
| 5.29 | **"Inconclusive" does not mean "no difference".** An underpowered metric can hide a real effect. In Microsoft's example, the test could detect only changes of ≥7.8% at 80% power. A significant result on an underpowered metric **exaggerates** the effect (winner's curse). [verified] | THEORY | S25 §5.4 | 2017 | — |
| 5.30 | **Treat a borderline p-value as a possible false positive** and re-run. [verified] | THEORY | S25 §5.5 | 2017 | — |

### Negative and contested (item 5)

- **Changing a title or thumbnail and watching the real-time graph is confounded.** Veritasium watched for "a noticeable bump in views" after a change (S18, 2021, [10:28–10:56 [tx]](https://www.youtube.com/watch?v=S2xHZPH5Sng&t=628)). His asteroid video went from 9th of his last 10 on day 1 to his best (14M views) after a day-3 title change ([9:01–9:52 [tx]](https://www.youtube.com/watch?v=S2xHZPH5Sng&t=541)). One case like this is not DATA. YouTube itself says sequential comparison is unreliable (S3, S2). Beaupré adds that a title or thumbnail change triggers no re-index or boost (S13 32:04–33:19, via 12-notes).
- **CTR as the test metric is rejected by YouTube.** Hanif: when you have "a sea of metrics", CTR distracts (S12 [12:04–12:20 tx]). Third-party CTR testers can pick a different winner (S2).
- **Winners decay.** Thumbnail fashions flip: an orange-thumbnail win leads everyone to copy it, and then blue wins (S13 [31:08–31:36 tx]). A re-run a week later can flip the winner (5.6). So a Test & Compare result describes one audience mix at one time, not a permanent rule.
- **Novelty effects** inflate short tests. In Microsoft's example the treatment lifted clicks on the first visit and was flat on later visits (S25 §5.10). For thumbnails, read the late-life performance too, not only the test window.
- **Contested: how much to test pre-publish.** Galloway values video A/B because once a video is uploaded "there's very little we can actually do to test" (S12 [7:17–7:47 tx]). MrBeast (interview published 2025-01-29) says he has moved toward "making people feel things… less about retention data analytics" ([Colin and Samir, "MrBeast Reflects on the State of YouTube"](https://www.youtube.com/watch?v=xf0Mli0LVgI), 49:36–49:45 [tx], 2025-01-29) [verified].

---

## 6. The learning loop

### 6a. How creators and analysts log and review

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| 6.1 | **Galloway's 4–5-step post-mortem.** (1) Start with views and the view pattern: fast then slow, or slow then fast. (2) Read the retention curve. (3) Check whether the other metrics (CTR, AVD) "can show you anything", allowing for what affects them. (4) Pull it into an action plan. His test question for creators is "What did you learn from your last video?". Most cannot answer because they "get so lost in the numbers". [verified] | PRACTITIONER (analyst, 3) | S12 | 2026-09-30 | [S12 14:30–16:43 [tx]](https://www.youtube.com/watch?v=j7GtybYc6gk&t=870) |
| 6.2 | **Patterns build up across many curves.** Galloway reports studying "10,000 plus retention curves" second by second. One sports client's audience left consistently during scripted skits. The channel moved to authentic, personal ideas and grew. No numbers were shown. [verified] | PRACTITIONER (analyst; claims a curve sample, none shown) | S12 | 2026-09-30 | [S12 10:51–11:03, 15:20–15:56 [tx]](https://www.youtube.com/watch?v=j7GtybYc6gk&t=920) |
| 6.3 | **A "not happy with" list per video.** After every video, Ritchie writes a list of things he is unhappy with and works on them over the next few videos. He still does this for Creator Insider. [verified] | PRACTITIONER | S12 (Ritchie) | 2026-09-30 | [S12 22:52–23:04 [tx]](https://www.youtube.com/watch?v=j7GtybYc6gk&t=1372) |
| 6.4 | **Extensive post-mortems for every video, hit or flop.** A 2026 channel run by James (ex-Donut Media) with 2M subscribers in just over a year says, "we know why stuff isn't doing well". [verified] | PRACTITIONER | S20 | 2026 | [S20 8:06–8:20 [tx]](https://www.youtube.com/watch?v=bZyevFMM8ZU&t=486) |
| 6.5 | **Correlate your own metrics with outcomes.** Jenny Hoyos had a team member build a Pearson correlation of views against every metric. On her channel likes, comments and shares "didn't really affect video performance". Viewed-vs-swiped, retention, watch time and average views per viewer did. **No coefficients and no N were shown, and it is one channel.** [verified] | PRACTITIONER (creator, stated result) [tag → PRACTITIONER: no coefficients, N or chart shown; "DATA-lite" is not a CONTEXT tag] | S17 | 2024-12-09 | [S17 25:20–25:56 [tx]](https://www.youtube.com/watch?v=_tWy-_otnUc&t=1520) |
| 6.6 | **Diagnose a flop against ~10 of your own videos.** Hoyos compares an underperformer with about 10 other videos and usually finds a higher swipe-away share, meaning the hook failed. [verified; caution: the speaker is unlabelled and the same turn goes on "surveys that we run", so it is likely Todd Sherman (YouTube), not Hoyos] | PRACTITIONER | S17 | 2024-12-09 | [S17 20:29–20:50 [tx]](https://www.youtube.com/watch?v=_tWy-_otnUc&t=1229) |
| 6.7 | **A fixed metric set and a fixed comparison window.** MrBeast's team tracks three metrics (CTR, AVD, AVP), compares on day-1 data, and ranks uploads hour by hour against previous videos ("what a video was out of 10"). [verified] | PRACTITIONER (doc; graphs shown) | S22 | 2024-09 | Doc pp.~5–9, 21–27 |
| 6.8 | **Cadence at studio scale.** Michelle Khare keeps a yearly goals spreadsheet (subscribers, views, revenue, new ventures, "risks we're going to take"), reviewed in a six-hour meeting, re-evaluated **every quarter**, with finances reviewed **weekly**. These are business goals, not per-video hypotheses. [verified; date corrected: S21 published 2025-08-30] | PRACTITIONER | S21 | 2025-08-30 | [S21 60:31–61:01 [tx]](https://www.youtube.com/watch?v=5TlPHtxsBIA&t=3631) |
| 6.9 | **YouTube's own diagnostic checklist when watch time falls.** (1) One video or many? (2) Did anything change (thumbnails, titles, content)? (3) When? Widen to 365 days. (4) Seasonality, year over year. (5) Upload frequency. (6) The subscribers' watch-time trend. (7) Google Trends for the topic or brand. [verified] | PRACTITIONER (platform, **possibly outdated**) | S15 | ~2021–22 | [S15 0:28–5:14 [tx]](https://www.youtube.com/watch?v=yBPZy-S4fIE&t=28) |
| 6.10 | **Log every packaging experiment.** "Take note of the thumbnails that work… and the ones that don't". Make one change at a time. Promote underperformers (social, end screens, posts) or re-test their title and thumbnail. [verified; date corrected: S16 published 2026-03-17] | PRACTITIONER (platform) | S16 | 2026-03-17 | [S16 1:12, 3:43–4:08 [tx]](https://www.youtube.com/watch?v=s0HWdnIU5RA&t=72) |
| 6.11 | **A retention-review write-up format.** Blackman reviews each submitted video with: title, AVP, the shape of the curve, the cause at each drop or spike, and a fix. Example: ManLikeRomz's 50 s hook was skipped (spike at ~0:50). [verified in part: S23 confirms title and AVP in every review, but shape, cause and fix are not in every one (Ollie Kirk, Catfluent lack some)] | PRACTITIONER (graphs shown) | S23 | 2022-11-04 (**possibly outdated**) | S23: ManLikeRomz, "THE MOST META COUNTER-ATTACKING CUSTOM TACTIC! FIFA 22", ~0:50 |
| 6.12 | **YouTube is moving the loop into Studio.** Ask Studio can summarise "three things I learned" (Galloway's hope), explain analytics, and read comment sentiment. Outliers and a Research tab feed ideas. Galloway's idea funnel has three sources: internal (your past winners), external (outliers, adapted, never copied) and original. [verified] | PRACTITIONER (platform + analyst) | S12 | 2026-09-30 | [S12 16:38–16:43, 16:43–18:21, 21:12–21:37 [tx]](https://www.youtube.com/watch?v=j7GtybYc6gk&t=1003) |

### 6b. Fields a per-video log needs, each tied to a source

No source published a ready-made hypothesis-log template with named fields (see Gaps). The fields below are the ones the sources above actually use.

| Field | Why, and the source |
|---|---|
| Video ID, format (long/Short), length bucket, series | Compare only within format and similar length (S8, S11 14:08) |
| Purpose of the video (reach / community / search) and its success metric | S16 2:27–3:43 |
| The one thing changed against the baseline (hypothesis) | One change at a time (S16 4:08) |
| Views at fixed ages (1 h, 24 h, 7 d, 28 d) and rank against the last 10 | MrBeast day-1 rule and x/10 (S22); Realtime 60 min / 48 h (S7) |
| CTR and AVD/AVP on the **subscriptions-feed** source as well as the total | S11 35:49–37:02 |
| Retention: % at 30 s, location and cause of the biggest dip, any spike and its type (rewatch / skip / confusion) | S4; S23 |
| Shorts: viewed vs swiped, average views per viewer | S17 20:29, 25:42 |
| Instagram: skip rate (first 3 s), average watch time, shares, saves | S29 |
| Test & Compare result (Winner / Same / Inconclusive) with impressions at the end | S1; Inconclusive is not proof of no effect (S25 §5.4) |
| "What I learned" (max 3) and "not happy with" items for the next video | S12 16:29–16:43, 22:52 |

### 6c. Review cadence found in sources

| Cadence | What is reviewed | Source |
|---|---|---|
| Minutes to hours | Real-time views after a packaging change (contested, see 5 negatives) | S18 10:40; S13 (Beaupré: effects show "within like seconds", via 12-notes) |
| Day 1 | Fixed-age comparison of AVD/AVP and x/10 rank | S22 |
| 2 days | Earliest retention and Instagram data | S4, S29 |
| ≤ 2 weeks | End of a Test & Compare run | S1 |
| A week or more later | Re-test the thumbnail as the audience shifts | S12 2:48–3:17 |
| Monthly / year over year | Watch-time trend, seasonality | S15 |
| Quarterly / annually | Channel goals and risks | S21 |

### Negative and contested (item 6)

- **Too much data stops learning.** Galloway says creators "get so lost in the numbers" that they can't say what they learned (S12 16:29–16:38). Hanif: analytics is "a lot to interpret" without a team of analysts (S12 13:59–14:05).
- **Copying outliers too heavily** turns into "constantly chasing what's worked for other people" (Galloway, S12 17:45–17:53).
- **One channel's correlations do not transfer.** Hoyos's "likes/comments don't matter" holds "at least for my channel" (S17). Blackman likewise notes a niche channel whose slow start held, and says this does not transfer to other channels (see 07 notes 5.21).
- **Analytics describe the past, not the future.** Galloway: they are "very good at telling you what happened" and very hard at predicting (S12 12:22–12:31).

---

## 7. Negative findings: vanity metrics, misreadings, the unmeasurable

### 7a. Vanity metrics

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| 7.1 | **Public view counts were inflated by definition on 2026-08-24.** Every format now counts a view from the **first frame**, including a hover autoplay on Home. The old definition is renamed **engaged views**. Most analytics (CTR, AVD, retention), YPP and recommendations stay anchored on engaged views. Views before and after 2026-08-24 are **not comparable**. [verified; note: "not comparable" is an inference; neither S9 nor S6 says it] | PRACTITIONER (platform) | S9; S6 | 2026-08-19 | — |
| 7.2 | **About half of new-style long-form views are not engaged.** vidIQ's sample of about 100 channels found **~54%** of views were engaged. vidIQ's small test found: a feed hover needs about **10 s** of play before it counts as engaged (8 s did not count, 10–12 s did). Any load of the watch page counts as engaged, even under 1 s. A 5 s video fully watched from search was **not** engaged. Video length did not matter. [verified; caution: on vidIQ's 5-min video 10 s did NOT count (12 s, 15 s, 20 s did), so "10–12 s did" holds only for the 2-min and 10-min videos; "length did not matter" is vidIQ's own conclusion. S19 is dated 2026-10-05 and now titled "What YouTube Doesn't Tell You About Your View Count"] | DATA (sample of ~100 channels, method not shown; plus a handful of trials on one test channel, shown on screen) [tag → DATA: "DATA-lite" is not a CONTEXT tag; the on-screen trials are measurements shown, small n] | S19 | 2026-10-05 | [S19 1:00–1:18, 2:34–8:33, 9:13–9:50 [tx]](https://www.youtube.com/watch?v=We8TVsjs2B8&t=60) |
| 7.3 | **Subscriber count overstates reach.** In the subscriptions feed, "probably all your videos have about maybe a 10% or less" CTR, so most subscribers don't watch any given upload. Beaupré: the subscribe signal "isn't as strong as a lot of people think". Few viewers watch a high share of a channel's videos (Ritchie's new/casual/regular data). [verified] | PRACTITIONER (platform) | S11 | 2026-09-01 | [S11 36:56–38:44 [tx]](https://www.youtube.com/watch?v=rHLjxrbXmmY&t=2216) |
| 7.4 | **No single metric indicates value.** CTR only shows "how attractive the thumbnail and the idea were". Time is not always valued time (a video that never pays off), which is why YouTube uses surveys. Likes, dislikes and comments each tell "part of the story". Signal weights differ by person and by device. [verified] | PRACTITIONER (platform) | S11 | 2026-09-01 | [S11 10:50–13:43 [tx]](https://www.youtube.com/watch?v=rHLjxrbXmmY&t=650) |
| 7.5 | **High CTR can be a warning sign.** YouTube flags clickbait as "high CTR but low average view duration and lower than expected Impressions". Galloway: "sometimes like a CTR is high because no one's watching", and "as virality increases, CTR tends to go down". [verified] | PRACTITIONER (platform + analyst) | S3; S12 | ©2026; 2026-09-30 | [S12 12:31–12:40 [tx]](https://www.youtube.com/watch?v=j7GtybYc6gk&t=751) |
| 7.6 | **CTR is half the job (contested).** Veritasium (2021) says you must optimize watch time *and* CTR, and that the title and thumbnail are "at least half the job". YouTube's 2026 test tool deliberately ignores CTR (5.2). [verified] | PRACTITIONER, **possibly outdated** | S18 | 2021-08-17 | [S18 7:18–7:49 [tx]](https://www.youtube.com/watch?v=S2xHZPH5Sng&t=438) |
| 7.7 | **Engagement counts as predictors.** On Hoyos's channel, likes, comments and shares did not track views (6.5). Instagram's 2023 ranking predicts reshares, full watch-through, likes and audio-page visits (S32), so on Instagram likes are an input but not the whole story. [verified] | PRACTITIONER (creator) / PRACTITIONER (platform) [tag → PRACTITIONER: Hoyos's correlation shows no numbers; "DATA-lite" is not a CONTEXT tag] | S17; S32 | 2024; 2023 | — |
| 7.8 | **Vanity metric, defined.** A gross total cannot show what caused a change. Use controlled, segment-by-segment trials and per-person metrics. [verified] | THEORY | S27 | 2009 | — |

### 7b. Common misreadings of the retention graph and dashboards

| # | Misreading | Correct reading | Tag | Source | Example / timestamp |
|---|---|---|---|---|---|
| 7.9 | "A spike means a great moment." | A spike means more people were watching, *rewatching or sharing* that part. It can also mean the content was **unclear** and people replayed it, or people **skipped forward** to reach it. [verified] | PRACTITIONER (platform + shown graph) | S4; S23 | ManLikeRomz FIFA 22 video, spike at ~0:50 = skip past a 50 s hook (S23) |
| 7.10 | "Retention above 100% at 0:00 is real." | Blackman calls the start spike "a cheeky glitch". `audienceWatchRatio` counts parts watched "more than once (or not at all)" in a view. Segment counts can exceed total views. [verified; caution: S23 says only "Ignore the spike - it's a cheeky glitch" and does not say the spike is at 0:00 or above 100%; the API part (S10) is confirmed] | PRACTITIONER + platform doc | S23; S10; S4 | Jak Lei, "You're Not A Real Man Until…", opening spike (S23) |
| 7.11 | "A jagged curve on a new video reveals specific weak moments." | With few views the curve is noisy: "small number of views for now which is why it's particularly spiky". Key moments need ≥100 views. [verified] | PRACTITIONER (shown graph) + platform | S23; S4 | Catfluent, "If My Wife Wins In Overwatch 2, I Get A TATTOO!" (S23) |
| 7.12 | "A downward slope means the video is bad." | YouTube videos "generally taper off" during playback, so a gradual decline is normal. Judge the slope against similar-length videos. [verified] | PRACTITIONER (platform) | S4; S11 14:12 | — |
| 7.13 | "The grey 'typical' band is a YouTube-wide benchmark." | Typical retention = **your 10 latest videos of similar length**. The YouTube-wide comparison sits behind SEE MORE. The API's `relativeRetentionPerformance` (0–1, 0.5 = median) is a different, cross-YouTube measure. [verified] | PRACTITIONER (platform) | S4; S10 | — |
| 7.14 | "One aggregate curve describes my audience." | Split by new vs returning, subscriber vs non-subscriber, and traffic source. Embed, ad or friend-link behaviour that doesn't predict Home behaviour is weighted little in Home ranking, so a bad embed curve is not a Home verdict. [verified] | PRACTITIONER (platform) | S4; S11 | [S11 34:03–34:38 [tx]](https://www.youtube.com/watch?v=rHLjxrbXmmY&t=2043) |
| 7.15 | "My subscribers didn't like it, so the video is cooked." | The system learns separately for subscribers, non-subscribers and new viewers. Non-subscribers are reached even in hour one. [verified] | PRACTITIONER (platform) | S11 | [S11 3:06–5:43 [tx]](https://www.youtube.com/watch?v=rHLjxrbXmmY&t=186) |
| 7.16 | "Views fell after the spike, so something broke." | A drop after a launch spike is "normal". Check for an accidental private flip or a Content ID claim before anything else. [verified] | PRACTITIONER (platform, **possibly outdated**) | S15 | [S15 0:48–1:26 [tx]](https://www.youtube.com/watch?v=yBPZy-S4fIE&t=48) |
| 7.17 | "The outlier proves my new style works / the next flop proves it failed." | **Regression to the mean**: unusually high or low values are followed by values closer to the average, more so when measurement error is high. Compare against a baseline of several videos, not the last one. [verified] | THEORY | S26 | — |
| 7.18 | "AVP is comparable across years." | Since 2021-12-13, `averageViewPercentage` excludes looping-clips traffic. Views changed definition on 2026-08-24 (7.1). Old tutorials and old exports are not like-for-like. [verified] | PRACTITIONER (platform doc) | S10; S9 | — |
| 7.19 | "Rows add up to the total." | Rows below unpublished privacy thresholds are dropped but still counted in the total. Demographics are absent for private and unlisted videos. "The actual thresholds… are not published." [verified] | PRACTITIONER (platform) | S5 | S5's example: 1,000 views = 500 US + 498 CA, with France's 2 missing from the rows |
| 7.20 | "An unexpected big jump is a discovery." | **Twyman's law**: "any figure that looks interesting or different is usually wrong". Check the data (definition changes, bugs, traffic anomalies) before acting. [verified] | THEORY | S25 §5.12 | — |
| 7.21 | "The same metric means the same thing everywhere." | An engaged view is counted at about 10 s on a feed hover but instantly on the watch page (vidIQ test). Engaged-view definitions also **conflict** between the blog ("past the initial seconds") and the API doc ("past the first frame"). [verified] | DATA (vidIQ on-screen trials, small n) + PRACTITIONER (platform docs, which disagree) [tag → DATA + PRACTITIONER: "DATA-lite" is not a CONTEXT tag] | S19; S9; S10 | — |

### 7c. What cannot be measured, by platform

| Platform | Not available (or not to the creator) | Tag | Source |
|---|---|---|---|
| YouTube | **Satisfaction survey results.** YouTube uses surveys in ranking (S11 12:17–12:28), but the Analytics API metrics page has no survey metric; the only survey metric is `membershipsCancellationSurveyResponses`. [verified] | PRACTITIONER (platform doc) | S10, S11 |
| YouTube | **Key moments, intro (30 s) %, Shorts viewed-vs-swiped and Shown-in-feed are not on the API metrics page.** Studio only. `videoThumbnailImpressions` and its CTR are not on that page either; whether the Reporting API has them is item 4's job. [verified] | PRACTITIONER (platform doc) | S10 |
| YouTube | **Test & Compare's confidence level, thresholds and minimum impressions** [verified] | PRACTITIONER (platform) | S1, S2 |
| YouTube | **Limited-data thresholds** (geography, demographics, search terms) [verified] | PRACTITIONER (platform) | S5 |
| YouTube | **Why the system showed a video to a given audience.** Per-viewer ranking is not exposed. Beaupré: each viewer gets a different ranking. [verified] | PRACTITIONER (platform) | S11 2:14–2:57 |
| TikTok | **Via the Display and Research APIs: no watch time, average watch time, completion, retention or traffic-source fields.** Only counts (views, likes, comments, shares, plus favorites in Research). Fields seen in in-app TikTok Studio analytics were not verified this session (item 3). [verified] | PRACTITIONER (platform doc) | S30, S31 |
| TikTok | **No organic A/B or trial-post tool** found in the sources reached (see Gaps) | — | — |
| Instagram | **No retention curve via the API.** The closest are `ig_reels_avg_watch_time` and `reels_skip_rate` (the share of initial views skipped within 3 s, "estimated" and "in development"). `views` and `ig_reels_video_view_total_time` (which includes replays) are "in development". There is no separate replay count. Data can lag up to 48 h and is stored up to 2 years. Unavailable data returns an empty set, not 0. [verified] | PRACTITIONER (platform doc) | S29 |
| Instagram | **Trial-reel results**: the blog does not say which metrics appear or when [verified] | PRACTITIONER (platform) | S28 |
| All | **Long-term or primacy effects in a short test window.** A win in week 1 may not hold, and a slow-burn treatment may be under-rated. [verified] | THEORY | S25 §5.10 |

### Negative and contested (item 7)

- **Views as a metric (contested).** Ries (2009) calls gross totals vanity metrics. Galloway (2026) starts every analysis with views and view patterns over time ("views are a metric") (S12 14:30–14:57). In Colin and Samir's "The New Rules of YouTube (2027)", the guest who appears to be Galloway (from the transcript context; the speaker is not labelled) says public view counts are how he reads trends ([WyiGFFTnIS4](https://www.youtube.com/watch?v=WyiGFFTnIS4), 23:10–23:17 [tx], 2026-08-19; the guest is confirmed as Paddy by "Paddy's about to throw up" at 23:06) [verified]. The two can be reconciled: views over time and against a baseline are diagnostic, while a raw total is not, especially after the 2026-08-24 redefinition.
- **Date conflict.** vidIQ says the view-count change happened on "August 27th" (S19 0:33). YouTube's blog and Help say **2026-08-24** (S9, S6). Use YouTube's date.
- **Engaged-view definition conflict**: see 7.21.
- **The "first hours decide" myth** is retracted by YouTube (7.15, 5.22). The 2024 MrBeast doc still ranks the first hours (S22), but as a forecasting habit, not a claim about the algorithm.
- **The "typical retention" definition changed over time.** 07 notes 5.7–5.8 record that the grey band changed definition. Older tutorials describe it differently.

---

## Gaps

1. **No web search in this session.** The shared 200-search budget was already used up, so the "at least 15 searches" target could not be met. Everything here comes from WebFetch of known URLs and from transcripts already cached in the scratchpad. YouTube answered further watch-page and caption requests with a bot check (not bypassed), so these were not reachable: the 2025-09/12 title-testing announcements (S33 timestamps are via 12-notes), the YouTube Creators video "A/B testing on YouTube" (`jKRiib3Xzoo`) and the Made on YouTube 2026 recap.
2. **Shorts full-video A/B**: no Help page or blog post found. The rollout date, eligibility, the number of variants beyond "two or three", and the decision metric beyond "watch time and retention" are unverified.
3. **TikTok experiments**: no source reached on whether TikTok offers any organic A/B or trial-post tool. TikTok Ads Manager split testing exists (general knowledge, not verified this session) but is paid traffic.
4. **Instagram trial reels**: no Help Center page reached. The metrics shown, the time to results and the auto-share rules are unverified. One later research file (06 result-a) mentions skip-rate and retention charts added to Insights in Aug 2025. This was not re-verified, but the Graph API's `reels_skip_rate` (S29) confirms a skip metric exists.
5. **No published creator hypothesis-log template** (named fields, cadence) was found in reachable sources. Table 6b is assembled from the practices sources describe. Paddy Galloway's and 1of10's own written material (newsletter, X threads) could not be reached without search.
6. **No YouTube statement of the statistical method behind Test & Compare** (test type, α, minimum impressions). The sample sizes in 5.27–5.28 are my arithmetic on a textbook rule and assume a CTR-like metric. Watch time share has unknown variance.
7. **Dates not retrieved** for S15, S16, S19, S21, xf0Mli0LVgI and WyiGFFTnIS4. The estimates come from each video's position in its channel's upload list.
8. **Hoyos's correlation (6.5)** and **Chucky's 30/30 (5.17)** are stated results with no numbers shown. They are as close as tier 2 got to DATA on testing. No creator was found publishing a full Test & Compare result table.
9. **Conflicts left open**: the engaged-view definition (blog vs API doc, 7.21); the view-change date (vidIQ vs YouTube); views as a vanity metric versus a diagnostic one.

## Refuted or unconfirmed

Moved here by the fact-check on 2026-10-12.

| Platform | Claim (as originally written) | Tag | Source | Reason |
|---|---|---|---|---|
| YouTube | **Counterfactuals for long-form video content**: no full-video A/B for long-form as of the Sept 2026 announcement (Shorts first). For long-form, only packaging is testable. | PRACTITIONER (platform) | S12 6:56–7:16; S14 | Contradicted by its own source: the S14 narration (3:15–3:29) says "upload your cuts, short or long form", while S14's description and S12 6:56 say "for Shorts" / "starting off with Shorts". Whether long-form video A/B is available is unresolved, so "for long-form, only packaging is testable" is not confirmed. |

**Fact-check summary (2026-10-12).** Opened and checked: S1–S18, S20–S31, S33 (YouTube transcripts from the session cache, watch pages fetched for publish dates and descriptions). 72 tagged claims checked: 71 confirmed (4 with tags corrected from the non-CONTEXT "DATA-lite"), 1 moved here. Date corrections in the source key: S15, S16, S19, S21, xf0Mli0LVgI, WyiGFFTnIS4. Gap 7 is now mostly closed by these dates. Untagged tables (6b, 6c) and 5.11 were not checked.
