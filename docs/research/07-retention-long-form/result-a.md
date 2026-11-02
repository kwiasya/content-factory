# 07 · Audience retention in long-form YouTube video

Source: Claude Opus research agents (3 researchers, 3 fact-checkers, 1 writer), 2026-10-12. Notes: notes/.

## How to read this file

- **Tags**: **DATA** means a measurement over a sample, an A/B test or a shown retention graph. **PRACTITIONER** means a stated practice with no data shown. **THEORY** means research or a model not tested on video. YouTube staff statements and Help pages show no data, so they are PRACTITIONER and marked **T1**. "n=1" marks one video. When a breakdown reads a shown graph, the shape counts as DATA (n=1) and the cause the reviewer names counts as PRACTITIONER.
- **Most-replayed heatmap ≠ retention.** Rows marked "heatmap" read YouTube's public replay-intensity graph. It is normalised min–max per video, so every video has one 0.00 bin and one 1.00 bin. A trough near 0 followed by a spike means viewers are seeking past that stretch.
- **Timestamps** come from caption tracks, chapter lists or the breakdown post that is cited. The fact-check found that caption-block timestamps from the Creator Insider, Colin and Samir, vidIQ and Film Booth videos run 10–20 s late. Start about 15 s before the cited time.
- **Old** means before 2024 and possibly outdated. George Blackman's "Retention Review" (RR) breakdowns (Nov 2022 – Mar 2023, small and mid-size channels) are all Old. They link to channels, not to the videos, so their examples are a named creator, a named video and the reviewer's own timestamp.
- **The MrBeast document** ("How To Succeed In MrBeast Production") is cited as [memo text][mbmemo] / [PDF][mbpdf]. Its date is disputed between the notes: one note calls it "~2022", another "undated, roughly 2023–24", and all agree it circulated publicly in Sept 2024 ([GIGAZINE][gigaleak]). MrBeast has not confirmed it is authentic. Its retention graphs are real Studio screenshots, so it counts as tier 2.

---

## Table A · Retention benchmarks

No source with a disclosed sample gives platform-wide benchmarks by genre (essay, vlog, tutorial, challenge, documentary) for retention at 30 s, AVD or APV. YouTube publishes none. Studio only benchmarks a video against your own similar-length videos. The table therefore holds YouTube's own thresholds, a few large-creator and analyst figures, non-YouTube studies, and single-video graphs.

### A1. YouTube's own reference points (T1)

| Length | Genre | Metric | Value | Source | Tag |
|---|---|---|---|---|---|
| any, ≥60 s and ≥100 views | any | Retention at 30 s ("Intro" key moment) | Defined as "what percentage of your audience still watched your video after the first 30 seconds". "A typical intro is about 30 seconds long." Videos with **≥50%** still watching at 30 s appear on the channel card as "above typical intros". This is the only number YouTube publishes for the opening, and no data is shown behind it. | [Help 9314415][h9314415]; [Help 12942217][h12942217] | PRACTITIONER (T1) |
| any | any | "Typical retention" grey band | Today: "your 10 latest videos of similar length". At the 2021 launch: similar-length videos "published on a creator's channel within the past year". The channel intro card compares your last 30 videos. **The baseline definition has changed**, so older tutorials describe a different band. | [Help 1715160][h1715160]; Creator Insider [zNy3jxmT26o][ci21km] at 02:19, 03:29; [SEJ 2021-10-01][sej21] | PRACTITIONER (T1) |
| any | any | Cross-channel comparison | Studio's "SEE MORE" compares the video "to all YouTube videos of similar length", per video only. The API's `relativeRetentionPerformance` runs 0–1, where 0.5 is the median of similar-length videos. No published number exists. | [Help 9314415][h9314415]; [Analytics API metrics][api] | PRACTITIONER (T1) |
| any | any | Absolute retention | `audienceWatchRatio` is the share of views watching a given point. It **can exceed 1** when viewers rewind. | [API metrics][api] | PRACTITIONER (T1) |
| any | any | View denominator | "Beginning August 24, 2026", a view counts "the moment a video starts to play across all formats". Earnings use "engaged views". vidIQ dates the change 2026-08-27, so the two sources disagree on the date. Help does not say whether the Studio retention graph uses all views or engaged views. | [Help 2991785][h2991785]; [vidIQ 2026-10-05][vidiqviews] | PRACTITIONER (T1) |
| ≥8 min | any monetised | Mid-roll eligibility | Mid-roll ads need 8 min or more. This is a money incentive, not a ranking signal. | [Help 6175006][h6175006] | PRACTITIONER (T1) |

### A2. Measured figures from creators, analysts and research

| Length | Genre | Metric | Value | Source | Tag |
|---|---|---|---|---|---|
| 13:59 | challenge (MrBeast, unnamed video) | Retention at 1:00; AVD; APV | 60M clicked and **21M were lost in the first minute**, so about 65% remained at 1:00. AVD 7:24, APV 53.0%. The document says this "compared to other channels is above average". One note first paraphrased this as above the *platform* average; the fact-check corrected it. | [memo][mbmemo]; [PDF][mbpdf] p.6–7 | DATA (n=1 graph) |
| ~11 min (one is 11:09) | challenge (MrBeast, unnamed) | APV / AVD from first-day data | 49.9% / 5:58 against 68.3% / 7:36, a gap of 1:38 in AVD. Views: 45M vs 120M. The document compares on first-day data "to make it apples to apples". | [PDF][mbpdf] p.27–29 | DATA (n=2 graphs); the claim that AVD caused the views gap is PRACTITIONER |
| 9:00 | challenge (MrBeast, unnamed) | Retention at 0:30 | **74%**, flat through an integrated sponsor read | [PDF][mbpdf] p.33 | DATA (n=1 graph) |
| 14:38 | challenge (MrBeast, unnamed) | Retention around 3:00 | From ~70% to ~53–55% during an old-style sponsor read (~2:50–3:30), a small rebound to ~57%, then flat | [PDF][mbpdf] p.32 | DATA (n=1 graph) |
| channel, last 100 videos | challenge (MrBeast) | Average length | 81,801 s, an average of **13:37** | [memo][mbmemo] | DATA |
| long-form, 2021 → 2025 | Paddy Galloway's clients and accelerator students | AVD | **4:35 → 8:00 (+77%)**, shown as a graph. Sample size not stated. | Colin and Samir with Galloway, [WyiGFFTnIS4][cs26] at 13:17–13:45 | DATA (T3) |
| long-form, 2020 → 2025–26 | Galloway agency data ("100 billion views worth") | Video length | **+51%** in mean and median. Typical length went from 12–16 min to "20-minute plus". | [WyiGFFTnIS4][cs26] at 02:43–03:15 | DATA (T3, method not published) |
| long-form | Galloway's clients | TV share of viewing | ~23–24% in 2021 → **>50%**. TV overtook other devices around 2023. Colin and Samir: most creators they talk to get 40–50% from TV. | [WyiGFFTnIS4][cs26] at 01:36–02:27 | DATA (client graph) / PRACTITIONER |
| long-form | ~100 channels (vidIQ) | Share of counted views that are engaged, after the Aug 2026 change | **~54%**. On Browse or Search, a hover-play under ~10 s counted as a view but not as an engaged view; 10 s or more was engaged, whatever the video length. A watch-page load counted as engaged in under 1 s. | [vidIQ We8TVsjs2B8][vidiqviews] at 00:48–01:05, 03:41–04:29, 06:10–07:03, 07:36–08:14 | DATA (an n=1 test plus a 100-channel aggregate; method not published; T3) |
| any length | edX MOOC lectures and tutorials (6.9M sessions, 4 courses, 2012) | Median engagement time | **At most 6 min, regardless of video length.** Students often watched less than half of videos longer than 9 min. For 0–3 min videos, 75% of sessions lasted more than ¾ of the video. | [Guo, Kim, Rubin 2014][guo] | DATA (T4; a log study, not YouTube, Old) |
| any length | edX tutorials | Engagement time | **2–3 min regardless of length.** Tutorials are re-watched and skimmed more than lectures. | [Guo 2014][guo] | DATA (T4, Old) |
| length buckets, shortest → longest | edX lectures | Share attempting the problem after the video | 56%, 48%, 43%, 41%, 31% | [Guo 2014][guo] | DATA (T4, Old) |
| <1 min / 1–5 min / >30 min | business videos hosted on Wistia (13M+), **not YouTube** | "Engagement" (undefined) | 52% / "over 50%" for educational and tutorial videos / an "11% drop" past 30 min | [Wistia 2025-07-01][wistia] | DATA (vendor; method not disclosed) |
| average ~12 min | channels with 250K+ subscribers (Pew, 43,770 channels, first week of 2019) | Length | Average ~12 min. Children's and gaming videos "tended to be longer" and drew more views. | [Pew 2019][pew] | DATA (Old) |
| average 14:50 | first-page YouTube search results (Backlinko, 1.3M videos, 2017) | Length | 14:50. This is a correlation with search rank, not reach. | [Backlinko][backlinko] | DATA (Old) |

### A3. Single-video graphs from breakdowns (n=1 each)

The genre column is my reading of each title. These are small and mid-size channels, 2022–23, and the length is mostly not given.

| Length | Genre | Metric | Value | Example (named creator, named video) | Source | Tag |
|---|---|---|---|---|---|---|
| ≥14:30 | gaming (niche, loyal audience) | Retention at 0:30 / 7:30 / 14:30; APV | 80% / 70% / 65% (approximate, sponsor dip excluded); APV 64.1%. This held despite a long title card and no topic until about 0:30. | Only Trails, "I Got an Elite Clue from EVERY Wilderness Boss…" | [RR#3][rr3] | DATA (n=1) |
| n/a | travel vlog / challenge | APV | 56.9% | Ollie Kirk, "I Spent 48 Hours In Croatia's Most Expensive City With Only $100" | [RR#1][rr1] | DATA (n=1) |
| n/a | history essay | Loss by ~1:30; APV | 70% gone by about 90 s, then flat for the last ~7 min; APV 26.0% | Harsh Raval, "Winston Churchill: The Mastermind Behind Bengal Famine" | [RR#6][rr6] | DATA (n=1) |
| n/a | explainer | APV | 58.6% | Theory Y, "Why It's Almost Impossible To Gain 63lbs In A Month" | [RR#5][rr5] | DATA (n=1) |
| n/a | commentary / review | APV | 54.6% | RoyalPear, "I Watched a Kid's Show, and it Broke Me (Bluey)" | [RR#13][rr13] | DATA (n=1) |
| n/a | tutorial | APV | 42.0%; more than 50% had left by ~3:00 | Erudite Magic, "2 Simple Tools to Unlock Your Magic Potential" | [RR#4][rr4] | DATA (n=1) |
| n/a | tutorial | APV | 36.6% | Jazzmentl, "How to Play Salsa Montuno on Piano" | [RR#4][rr4] | DATA (n=1) |
| n/a | tutorial / listicle | APV | 33.0% | Design. Draw. Do., "This will make you want to buy a sketchbook" | [RR#6][rr6] | DATA (n=1) |
| n/a | cooking | APV | 37.2% | Jason Farmer (farmageddon), "Chinese Takeout Fried Rice Secrets Revealed" | [RR#14][rr14] | DATA (n=1) |
| n/a | gaming list (search) | APV | 27.1% | Minecraft & Chill, "TOP 20 BEST NEW SEEDS For MINECRAFT 1.19!" | [RR#3][rr3] | DATA (n=1) |
| n/a | gaming challenge | APV | 25.4% | Catfluent, "If My Wife Wins In Overwatch 2, I Get A TATTOO!" | [RR#1][rr1] | DATA (n=1) |
| n/a | gaming challenge | APV | 18.5% | DookyFace, "Can 3 Idiots Beat 1 Gang Beasts God?" | [RR#1][rr1] | DATA (n=1) |
| n/a | gaming vlog | APV | 51.7% | LadToDad, "I Purchased Baby RONALDINHO!" | [RR#4][rr4] | DATA (n=1) |
| n/a | sports challenge | APV | 34.6% | JnA Golf, "Strangers Take Cash Prize if They Beat us in Golf" | [RR#11][rr11] | DATA (n=1) |
| n/a | poker vlog | APV | 51.4% | Bitty Plays Poker, "The Poker Hand That Changed My Life \| Degen Diaries 6" | [RR#2][rr2] | DATA (n=1) |
| n/a | skit / storytime | Loss in 30 s; APV | ~45% left within 30 s; APV 14.9% | Effxayy, "If you ever see this on a GAS PUMP at the gas station call 911 IMMEDIATELY!! (STROMEDY INSPIRED)" | [RR#2][rr2] | DATA (n=1) |

---

## Section B · Timeline of a long video

### 0–5 s

| Rule | Tag | Source |
|---|---|---|
| **Confirm the click.** Show straight away what the thumbnail and title promised, visually or in words, so the viewer feels "they made the right decision". | PRACTITIONER (T3) | Galloway and Colin and Samir, [L9CO1FcRHCM][cs25] at 79:03–80:59, 81:15–81:31 |
| No logo stinger and no "hello, I'm…". Fold the "what this channel is about" setup into the story. | PRACTITIONER (T3, Old) | Film Booth [TplwkCc89wU][fb19] at 02:36 (2019); [YwbPVcGQT5s][fb21] at 02:27–04:52 (2021) |
| A cold open mid-action, with "no welcome, no intro music", is one of vidIQ's 9 intro patterns. Others are an explicit deal ("in the next 60 seconds…"), stakes or a consequence, a contrarian claim, and a surprising stat. | PRACTITIONER (T3) | [vidIQ WHGw3j2BUG0][vidiqintros] at 00:21, 01:51, 02:56, 04:16 |
| A logo or sting is not a separate "intro" to YouTube. The Intro metric is simply the first 30 s, whatever they contain. | PRACTITIONER (T1) | [Help 9314415][h9314415] |
| Since 2026-08-24, hover-plays on Home count as views, and ~46% of long-form views are not engaged. Part of the drop in the first ~10 s of an all-views curve is impressions, not viewers rejecting the opening. Do not diagnose the first 10 s without engaged-view context. | DATA (vidIQ) + contested interpretation | [vidIQ][vidiqviews] at 11:17–11:40; [Help 2991785][h2991785] |
| Ignore a spike above 100% at the first frame. It is a replay artefact. Read the curve from about 0:01. | PRACTITIONER | [RR#1][rr1]; [API metrics][api] |

### 5–30 s

| Rule | Tag | Source |
|---|---|---|
| First ~7 s: set up the video and its context. **By 30 s, add a new hook the thumbnail did not promise**, so open loops carry the viewer forward. | PRACTITIONER (T3) | Colin and Samir, [L9CO1FcRHCM][cs25] at 81:15–81:31 |
| "Necessary context, not over context." Tease the intriguing parts and flow into the first story beat so the intro has no visible boundary. | PRACTITIONER (T3) | Galloway, [L9CO1FcRHCM][cs25] at 79:03–80:59 |
| Keep the hook in the first ~15 s even in 30–50 min TV-era videos: "capitalize on the first 15 seconds … and then let it breathe". | PRACTITIONER (T3) | [WyiGFFTnIS4][cs26] at 52:20–53:35 |
| "The first act can't just be an introduction. The first act has to be a reward." "The thumbnail makes a promise, and the video has to deliver on it." | PRACTITIONER (T1, Old) | Rene Ritchie via [SEJ 2023-08-14][sej23] |
| Put the tension, the "but" the title implies, inside the hook. When the reversal arrived late, 70% of viewers were gone by about 90 s. | DATA (n=1) + PRACTITIONER cause | Harsh Raval, [RR#6][rr6] |
| Do not give the whole payoff away in the hook. About 45% left within 30 s when the hook showed it. | DATA (n=1) + PRACTITIONER cause | Effxayy, [RR#2][rr2] |
| A hook that only restates the title gets skipped, unless the premise is outlandish (MrBeast-style). | PRACTITIONER on shown graphs | [5 mistakes][rr5m]; [RR#1][rr1] |
| Do not let the opening contradict the packaging. A video whose creator praised a show under a "this was not fun" title dipped at ~15 s. | PRACTITIONER on a shown graph | RoyalPear, [RR#13][rr13] |
| If the Intro is low, YouTube lists the packaging fix first: "Consider changing your video thumbnail and title to better reflect your video content". Its second fix is to change the first 30 s. | PRACTITIONER (T1) | [Help 9314415][h9314415] |
| Put 20–30% of the edit effort on the first minute of a 10-min video. | PRACTITIONER (T3) | Galloway, [L9CO1FcRHCM][cs25] at 79:03–80:59 |
| The intro protects views; it does not create them ("rarely that a better intro leads to 270 times more views"). Title, thumbnail and idea do the multiplying. | PRACTITIONER (T3) | Galloway, [L9CO1FcRHCM][cs25] at 78:49 |
| Fast visual change in the intro, as an example of a practice: 10 scene changes in the first 20 s, and 19 B-roll clips against 18 s on camera in the first 60 s. | PRACTITIONER (one intro counted, no curve shown; Old) | Shelby Church's Medium video, in Film Booth's breakdown [YwbPVcGQT5s][fb21] at 02:27–04:52 |

### 30 s – 2 min

| Rule | Tag | Source |
|---|---|---|
| The first minute loses the most viewers on almost every video. MrBeast's ~65% at 1:00 was "above average" against other channels. | DATA (n=1) | [PDF][mbpdf] p.6–7 |
| 1–3 min: "transition from hype to execution… Stop telling people what they will be watching and start showing them." | PRACTITIONER (T2) | [memo][mbmemo] |
| **"Crazy progression"**: cover several days or steps in the first 3 minutes, not day 1 in full as "a logical filmmaker would". | PRACTITIONER (T2) | [memo][mbmemo]; example: [hD1YtmKXNb4][mbprison] at 3:41 (researcher) or 3:44 (fact-check) |
| A bad start anchors the viewer, who "give[s] you less leeway as you go longer". | PRACTITIONER (T3) | Galloway, [L9CO1FcRHCM][cs25] at 79:39–80:20 |
| Cut any rundown or self-intro that delays the core content. One creator cut 27 s after upload, and the curve became "mostly completely flat" (no number given). | PRACTITIONER (before and after described) | Darren Allatt, [RR#7][rr7] |
| A slow intro can hold for a loyal niche audience (80% at 0:30). Check new against returning viewers before copying it. Contrary case: cutting straight to the first deal *worsened* early retention on Breakout Cards' other videos. Both are n=1. | DATA (n=1) / PRACTITIONER | Only Trails, [RR#3][rr3]; Breakout Cards, [RR#5][rr5] |
| A "slow start" in the first hour after upload does not "cook" the video. The system learns separately for subscribers, non-subscribers and people new to the channel. | PRACTITIONER (T1) | Beaupré, [rHLjxrbXmmY][ci26] at 03:14–05:43, 35:14–35:35 |

### The middle

| Rule | Tag | Source |
|---|---|---|
| A gradual decline is normal ("Videos on YouTube generally taper off"). "The flatter the line, the more engaged your audience is." | PRACTITIONER (T1) | [Help 9314415][h9314415]; Creator Insider [V8f_VWMV8pY][ci22] at 00:33–00:57 |
| If the top moments sit late, move that content earlier, because "audience sizes typically decrease over the length of the video". | PRACTITIONER (T1) | [Help 9314415][h9314415]; [Help 12942217][h12942217] |
| Place a **re-engagement at ~3 min**, a spectacle that "fits the story and makes people genuinely impressed". Then use simple, exciting content with "lots of quick scene changes" for minutes 3–6. Place a **second re-engagement at ~6 min** that "needs a little more explanation and will push the story". | PRACTITIONER (T2; tuned to a 13:37 average, not validated for 20–30 min) | [memo][mbmemo] |
| "If we can get them to watch the first half… very high chance they'll watch to the end." Long explanations can live in the back half, but "many videos have been killed because the back half content was ass". | PRACTITIONER (T2) | [memo][mbmemo] |
| **Stair-step the stakes**: they rise as the video goes deeper, and the payoff comes at the end. | PRACTITIONER (T2) | [memo][mbmemo] |
| Ground open loops in the information gap (a gap between what one knows and wants to know) and in the tendency to resume interrupted tasks, not in "people remember unfinished things". | THEORY | [Loewenstein 1994][loew]; [Kang et al. 2009][kang]; [Ghibellini & Meier 2025][ghib] |
| Every middle segment must earn its place. A competition frame does not save a weak round: viewers sought past it. | DATA (n=1, heatmap) | Mark Rober [0XgcOz95hTs][rober] at 9:04–9:52 |
| Open each segment with context, then reveal the point. If the first line gives the point away, viewers skip to the tip and leave. | PRACTITIONER on shown graphs | Erudite Magic, [RR#4][rr4]; Design. Draw. Do., [RR#6][rr6] |
| Dense information over dry visuals produces a sawtooth curve. Add B-roll of the action being described. | PRACTITIONER on a shown graph | ManLikeRomz, [RR#1][rr1] |
| Cut repetition and show only new information. | PRACTITIONER on a shown graph | Zamby, [RR#3][rr3] |
| Do not stretch the peak: 3+ minutes of card counting during the biggest deal sagged. | PRACTITIONER on a shown graph | Breakout Cards, [RR#5][rr5] |
| Integrate sponsor reads. An old-style read made a "crater" (viewers skipped and some left); an integrated read made a small dip. | DATA (2 graphs) | [PDF][mbpdf] p.32–33 |
| Vary the tempo by section and speed up into the climax rather than holding one cut rate. In films, shots shorten into the climax and lengthen in the epilogue. | THEORY (film DATA, not YouTube) | [Cutting 2016][cut16]; [Cutting et al. 2010][cut10] |
| Use edits within a scene freely. Keep scene cuts at or below about 10 per 2 min, and make every cut relate to the story: "unrelated cuts do not make it into memory". | THEORY (1990s TV lab) | [Kubey & Csikszentmihalyi 2002][kubey]; Lang 2000 via [LC4MP][lc4mp] |
| On informational videos, alternate the talking head with slides, code or visuals: median engagement was longer than with slides alone (46% vs 33% problem attempts in one course). | DATA (MOOC, Old) | [Guo 2014][guo] |
| Energy over a target wpm. Faster speakers held longer, up to 2×, and 145–165 wpm was the *least* engaging bucket for 6–12 min videos. The authors read speech rate as a proxy for enthusiasm. | DATA (MOOC, Old) | [Guo 2014][guo] |
| Tightly edit out "umm", "uhh", filler words and pauses. | PRACTITIONER (reported in a DATA paper) | [Guo 2014][guo] |
| Make "slower" mean longer scenes and more story in places, not slow throughout. The same team that "slowed down" still asks for "no dull moments". | PRACTITIONER (T2) | [MrBeast X 2024-03-03][mbx1]; [memo][mbmemo] |

### The last 10 %

| Rule | Tag | Source |
|---|---|---|
| End at the payoff. "If your payoff happens at the end of your video… end the video." Material after the payoff is wasted ("end at 7:48"). | PRACTITIONER on shown graphs (Old) | [RR#11][rr11]; Aquarium Shed, [RR#13][rr13] |
| "The video endings must always be abrupt to protect retention." "Don't ever signal the end of the video unless it's to build hype for the prize." | PRACTITIONER (T2) | [PDF][mbpdf] p.8, p.29, p.35 |
| Do not recap: "Summarising the video at the end is almost always a retention killer." | PRACTITIONER on a shown graph | [RR#4][rr4] |
| No caveat near the end. In one video it caused "the biggest dropoff across the whole video". | PRACTITIONER on a shown graph | Jason Farmer, [RR#14][rr14] |
| No long reflections or repeated sign-offs. Blackman allows an exception for "the right niche". | PRACTITIONER on a shown graph | Bitty Plays Poker, [RR#2][rr2] |
| "Your outro should be your Call To Action and nothing more." Name a specific next video and the reason it suits this viewer. Do not just ask for comments. | PRACTITIONER | [5 mistakes][rr5m]; [RR#7][rr7]; [RR#14][rr14] |
| End screens need a video of at least 25 s. They occupy the last 5–20 s and hold up to 4 elements. YouTube says nothing about their effect on retention. | PRACTITIONER (T1) | [Help 6388789][h6388789] |
| A 20–30 point drop in the final seconds appears even on MrBeast's abrupt endings. Do not flag it as a defect. The actionable drop starts 30–120 s before the end, at an outro, recap or caveat. | DATA (2 graphs, visual reading) | [PDF][mbpdf] p.28, p.32 |
| The end has to deliver. YouTube discounts time in "a video that didn't deliver at the end … you kind of hung on for a long time hoping for a payoff". | PRACTITIONER (T1) | Beaupré, [rHLjxrbXmmY][ci26] at 12:17–12:49 |
| Retrospective ratings track the peak and the end of an experience. Since post-view survey ratings feed "valued watch time", a strong ending may matter for them. The link to YouTube surveys is an inference, untested on video. | THEORY | [Peak–end rule summary][peakend]; [Fredrickson & Kahneman 1993][fk93] |
| Cliffhangers are an underused way to make viewers want the next video. | PRACTITIONER (T1, Old, paraphrased by press) | Ritchie via [SEJ 2023][sej23] |

---

## Table C · Techniques

| Technique | Effect on the curve | Evidence | Example video + timestamp (origin) | When it backfires |
|---|---|---|---|---|
| Cold open / confirm the click | Protects the 30-s Intro checkpoint | PRACTITIONER (T3: [Galloway, Colin and Samir][cs25]; [Film Booth][fb21]). T1 links a high Intro to matching "the viewer's expectation of the video's thumbnail and title" ([Help 9314415][h9314415]). No controlled test exists. | 51-min woodworking build (creator not named): "confirmed the click" and revealed a celebrity expert, John Malecki, in **16 s**. Played inside [WyiGFFTnIS4][cs26] at 51:52–52:46. | The whole payoff is shown in the hook (Effxayy, ~45% gone in 30 s, [RR#2][rr2]). The hook only restates an ordinary title ([5 mistakes][rr5m]). |
| Teaser / "coming up" | Meant to carry viewers past the opening | PRACTITIONER on a shown graph | DookyFace, "Can 3 Idiots Beat 1 Gang Beasts God?", first ~40 s (from [RR#1][rr1]) | A ~40 s "COMING UP" that turned out to be an already-started highlight reel coincided with a sharp opening drop. |
| Open loop (announce the payoff, insert the explanation inside the loop) | Holds viewers through explanatory stretches until the payoff | THEORY for the mechanism ([Loewenstein][loew]; [Kang 2009][kang]: curious people spend waiting time to get the answer). The example is DATA (n=1, heatmap): replay, not retention. | Mark Rober, "I Blew Up A 24 Story Building" [0XgcOz95hTs][rober]: **5:47–6:05** sets up the "Demolympics" that decide who triggers the implosion, then "But before we commence… let's quickly talk about how you demolish". Payoff heatmap 0.95–1.00 at **20:20–21:40** (captions). | A loop that is never paid off: Theory Y never answers its title question, and the viewers who wanted the answer leave ([RR#5][rr5]). YouTube discounts unvalued time ([Goodrow 2021][goodrow21]). A weak round inside the loop is still skipped (same video, 9:04–9:52). |
| "But first" before a sponsor | Keeps viewers in the video, **not** in the ad | DATA (n=1, heatmap) | Johnny Harris, "Why This Island Could Trigger World War 3" [x-XdOaZPhBw][harris]: **9:24** "things are about to dramatically change here. But first… today's sponsor". Heatmap 0.00–0.01 at 9:35–10:10, then 0.80 at 10:44 ("let's dive back into the map"). Second break at **16:25**, promoting his own New Press, not a sponsor: heatmap 0.02–0.03, then 1.00 at 17:25 (auto captions). | Viewers seek past the ad anyway. An old-style read makes a "crater" where some viewers leave the video ([PDF][mbpdf] p.32). |
| Chapter promises / chapters | Unknown. YouTube says only that chapters let viewers "easily rewatch different parts". | PRACTITIONER (T1). No retention data at any tier. For tutorials, Guo advises supporting "re-watching and skimming" (DATA, MOOC). | Veritasium, "Something is jamming GPS over Europe" [tz23G_UXCGA][vgps]: chapter "The Hunt To Find The Jammer" at **12:18** (chapter list). | List and search videos turn spiky as viewers jump to their item and leave satisfied. That is not a priority if search rank holds (Minecraft & Chill, [RR#3][rr3]). |
| Re-hook at a chapter boundary (restate the central question) | Meant to reset attention at a boundary | PRACTITIONER (named example). A replay heatmap cannot show whether it held viewers. | Same Veritasium video, **12:18–12:23**: "Which brings us back to the question… Was this accidental? Or was someone flooding this band on purpose?" Heatmap 1.00 at 11:39, then 0.00–0.09 at 12:20–14:44 (subs). | Not measured. |
| Re-engagement at ~3 and ~6 min | Meant to prevent mid-video slides at fixed minute marks | PRACTITIONER (T2); unvalidated past 13–14 min | MrBeast, "$10,000 Every Day You Survive Prison" [hD1YtmKXNb4][mbprison]: **2:47** "So Carl's gonna take care of you tomorrow", with Karl chaos through 3:15. Girlfriend visit at **6:10–6:56** with a 10-min timer and a $5k vs $10k trade-off. Heatmap local peaks 0.46 at 4:53 and 0.55 at 7:07 (subs, heatmap). | The marks fit a 13:37 average video. No source scales them to 20–30 min essays. |
| Crazy progression (compress the early timeline) | Invests the viewer in minutes 1–3 | PRACTITIONER (T2) | Same prison video: "It has officially been eight days in this room" at **3:41** per the researcher's captions, **3:44** per the fact-check. | Not stated. |
| Stakes escalation ("stair stepping") | Pulls viewers toward the payoff at the end | PRACTITIONER (T2); the heatmap peak is n=1 | MrBeast, "$1 vs $100,000 Firework!" [erQ_9yEz0ls][mbfire] (2020, Old). The match to the memo's "I Bought The World's Largest Firework" is an inference supported by the $375 step at 1:02. Chapters: $1,000 at **1:02**, $10,000 at **6:46**, $40,000 at **8:07**, world record at **9:20**. Heatmap maximum 1.00 at **8:41**. | The stated stakes are undercut by what happens on screen: Catfluent, steady slope, APV 25.4% ([RR#1][rr1]). For story formats Blackman prefers concept and story to artificial challenge stakes (Ollie Kirk, [RR#1][rr1]). |
| Complication beats ("but there's a problem") | Turns an explanation into a sequence of obstacles | PRACTITIONER (named example) | Veritasium, "Google Maps is unreasonably fast" [kS-CGkiPetQ][vmaps]: **3:11** "But there's a problem with this approach"; **22:56** "Except, there's a problem." Chapter "Shortest Doesn't Mean Fastest" at 12:40 (subs, chapter list). | The dense technical stretch at 22:43–23:55 still reads 0.01–0.08 on the heatmap (n=1; the cause cannot be attributed). |
| Withhold the outcome to the end | "Strong payoffs at the end of videos boost retention." | PRACTITIONER (T2) | MrBeast formats named in the memo: "Last To Leave" and chase videos. No timestamps. | Contested: "Story Spoilers Don't Spoil Stories" (THEORY, short stories in a lab, [Leavitt & Christenfeld 2011][leavitt]). |
| Pattern interrupts (edits, cuts) | Edits set off automatic orienting responses: heart-rate deceleration for 4–6 s | THEORY (lab, TV) | None in the notes | More than ~10 **scene** cuts in 2 min cut recognition "sharply". Unrelated cuts are not encoded ([Kubey & Csikszentmihalyi][kubey]; [LC4MP][lc4mp]). |
| B-roll and visual change rate | Fixes a sawtooth over dense explanation. Alternating head and visuals lengthened engagement. | DATA (MOOC, [Guo][guo]); PRACTITIONER on a graph ([RR#1][rr1]) | Shelby Church's Medium video: 19 B-roll clips in the first 60 s, in Film Booth's breakdown [YwbPVcGQT5s][fb21] at 02:27–04:52 | edX staff flag a "jarring effect" from switching repeatedly. The optimal switch rate is unknown ("Open questions include when and how often to switch"). |
| Music changes | **Unsourced** | None found | None. Caption music tags are inconsistent across years and cannot serve as a proxy. | Unknown |
| Jump cuts / removing dead air | Tightens talking-head pace | PRACTITIONER (no data): a cut every 3–8 s (~7.5–20 per min) and removing gaps longer than ~0.5 s ([1of10, 2026-10-05][oneof10]). The edX practice is to remove "umm" and pauses ([Guo][guo]). | None in the notes | Interviews, emotional beats, and audiences who say a channel feels "too fast" ([1of10][oneof10]). Jump cuts within one scene are closer to Lang's "edits" than to "cuts", so the 7–20/min folklore and the ~5/min lab limit are not comparable. |
| Speech rate | Faster, more energetic delivery held longer | DATA (MOOC, Old, [Guo][guo]) | Caption words per runtime minute (not a true speech rate; fact-checked recount): MrBeast 163 (2020) → 208 (2024); Veritasium 166–193; Johnny Harris 157–167; Mark Rober 145–195. DATA (n=14, caption-based). | Speeding up "an unenthusiastic instructor might not improve engagement" ([Guo][guo]). |
| Slower editing, "let scenes breathe" (2024 shift) | MrBeast: "our views have skyrocketed". No figures. | PRACTITIONER (T2) | Posted the day after "I Survived 7 Days In An Abandoned City" [tWYsfOSY9vY][mbcity] ([X 2024-03-03][mbx1]). "7 Days Stranded On An Island" [erLbbextvlY][mbisland]: "slower and especially toward the end shows more depth" ([X 2024-03-30][mbx2]). Its late chapters are longer ("Exploring the ruins" 12:26–16:28, "Stormy night nightmare" 16:28–20:10), but the chapters look auto-generated. | The 2024 videos are not less talky (195–208 words/min against 164 in 2020, the researcher's count). The same team's guide still asks for quick scene changes in minutes 3–6. |
| Integrated sponsor read | Small dip instead of a crater | DATA (2 graphs) | MrBeast, unnamed videos ([PDF][mbpdf] p.32–33) | An old-style read: ~70% → ~55% around 3:00 that never recovered. |
| End at the payoff, abruptly | Avoids the slow outro slide | PRACTITIONER on shown graphs | NathanLIVE, "I Built A Minecraft Trap That Never Ends…", ends right after the trap catches the friend: "Perfect" ([RR#12][rr12]). Aquarium Shed, "Building a Mayan Temple For Your Shrimp!", should "end at 7:48" ([RR#13][rr13]). | An abrupt end with no next-video pointer: "we don't really have anything we NEED to stick around for anymore" (LadToDad, [RR#4][rr4]). |
| Second payoff, foreshadowed | Carries viewers past the first payoff | PRACTITIONER on a shown graph | LadToDad, "I Purchased Baby RONALDINHO!": Ronaldinho scores at ~8:00 and the curve spikes, but the moment was never foreshadowed ([RR#4][rr4]) | A payoff placed mid-video without a second one set up: the premise goes slack (Adzi Gaming, "A Non-Horror Fan Reviews Callisto Protocol", [RR#11][rr11]). |
| Next-video hand-off | Converts end-of-video watch time into a session | PRACTITIONER | Darren Allatt, "I Bought HDZero Goggles…", ending CTA ([RR#7][rr7]) | Blackman's claim that "the algorithm rewards… longer viewer 'session times'" is unsourced, and YouTube has no first-party statement on it. |

---

## Section D · Diagnosis guide

### D1. Curve shape → likely cause → what to change next time

| Curve shape | Likely cause | What to change | Tag | Example (creator, video, timestamp) | Source |
|---|---|---|---|---|---|
| Intro below 50% at 0:30 while CTR is high | Packaging mismatch: the wrong viewers clicked | Change the title or thumbnail "to better reflect your video content" first, then the first 30 s | PRACTITIONER (T1) | — | [Help 9314415][h9314415] |
| Early drop on Browse and Suggested, but not among subscriptions-feed viewers | The packaging promises new viewers something the opening does not deliver. If subscribers also leave early, the opening itself is at fault. | Fix the promise for new viewers, or fix the opening | PRACTITIONER (T1 logic). The rule is the researcher's inference from Beaupré's "a clean way to isolate the content from the algorithm"; YouTube does not state it. | — | [rHLjxrbXmmY][ci26] at 35:51–37:03; [Help 9314415][h9314415] |
| Steep fall in the first ~10 s (after 2026-08-24) | Partly non-engaged hover-plays counted as views (~46%). vidIQ itself reads the same figure as "the hook failed almost half of the time". | Compare engaged views before blaming the hook | DATA (vidIQ) + contested reading | — | [vidIQ][vidiqviews] at 11:17–11:40 |
| Cliff before the core content starts | Too much intro and context | Cut it; the Studio editor can do this after upload | PRACTITIONER (before and after described) | Darren Allatt, "I Bought HDZero Goggles…": review started at 0:38, cut to 0:11 | [RR#7][rr7] |
| Spike at ~0:50, then a cliff | Viewers skip a laboured hook; the spike is a skip target | Shorten the hook | PRACTITIONER on a graph | ManLikeRomz, "THE MOST META COUNTER-ATTACKING CUSTOM TACTIC! FIFA 22", ~0:50 | [RR#1][rr1] |
| Dip at ~15 s | The content contradicts the packaging | Check the script and edit against the title's promise | PRACTITIONER on a graph | RoyalPear, "I Watched a Kid's Show…", ~0:15 | [RR#13][rr13] |
| Early cliff (70% gone by 90 s), then flat | The reversal the title promises arrives too late | Put the tension and the "but" inside the hook | DATA (n=1) + PRACTITIONER cause | Harsh Raval, "Winston Churchill…", ~1:30 | [RR#6][rr6] |
| ~45% gone within 30 s | The hook gave the payoff away | Keep the payoff for later | DATA (n=1) + PRACTITIONER cause | Effxayy, "If you ever see this on a GAS PUMP…", 0:00–0:30 | [RR#2][rr2] |
| Sharp opening drop under a "coming up" reel or a title restatement | Viewers skip the teaser or restated title | Replace it with a new hook (the 30-s rule in Section B) | PRACTITIONER on graphs | DookyFace, "Can 3 Idiots Beat 1 Gang Beasts God?", first ~40 s | [RR#1][rr1]; [5 mistakes][rr5m] |
| Drop in segment 2, after the hook's implied tension is disproved | The hook implied something the video then proves false, so the tension is gone | Keep the hook's tension true to the content | PRACTITIONER on a graph | JnA Golf, "Strangers Take Cash Prize if They Beat us in Golf", S2 | [RR#11][rr11] |
| Steady slope with no early cliff | Low tension: nothing makes the viewer stay. Or the stated stakes are undercut on screen. | Build intrigue through concept and story (recurring characters, small three-act arcs). Keep the stakes consistent with what happens on screen. | PRACTITIONER on graphs | Ollie Kirk, "I Spent 48 Hours In Croatia's Most Expensive City With Only $100"; Catfluent, "If My Wife Wins In Overwatch 2…" | [RR#1][rr1] |
| Sawtooth ("ski slope"): flat stretches broken by sharp drops | Dense information over dry visuals | B-roll of the action described; zooms on the relevant screen element | PRACTITIONER on a graph | ManLikeRomz (same video) | [RR#1][rr1] |
| A dip with a spike at each tip | Viewers skip ahead to the tip, then leave once they have it | Reach the point sooner; open each segment with context, then the point | PRACTITIONER on a graph | Erudite Magic, "2 Simple Tools…", first tip at ~3:00 with more than 50% already gone | [RR#4][rr4] |
| Even decline across a listicle | Each segment opens with its conclusion | Context first, then the reveal | PRACTITIONER on a graph | Design. Draw. Do., "This will make you want to buy a sketchbook" | [RR#6][rr6] |
| Spiky curve on a list or search video that still ranks | Viewers navigate to their item and leave satisfied | Low priority if search rank holds; still tighten the hook | PRACTITIONER on a graph | Minecraft & Chill, "TOP 20 BEST NEW SEEDS…" | [RR#3][rr3] |
| Drop at a failure point | Repeating content the viewer has already seen | Show only new information | PRACTITIONER on a graph | Zamby, "I Reached Round 100 With 0 Kills", ~4:00 | [RR#3][rr3] |
| Sag during the intended high point | The peak is stretched (3+ min of counting) | Compress the peak | PRACTITIONER on a graph | Breakout Cards, "I Spent $10,000 at the Chantilly Card Show", S3 | [RR#5][rr5] |
| Crater at a sponsor read that never recovers | Viewers skip the read and some leave the video | Integrate the read into the content. Ignore the expected ad dip when reading the rest of the curve. | DATA (2 graphs) | MrBeast, unnamed (p.32 vs p.33); Exposure Ninja, "START TODAY: How SEO Works", S4 ad dip | [PDF][mbpdf]; [RR#5][rr5] |
| Replay heatmap near 0 during a section, then a spike at re-entry | Viewers seek past the section. The heatmap is not retention. | Shorten or cut the skipped section | DATA (n=1, heatmap) | Mark Rober [0XgcOz95hTs][rober], 9:04–9:43; Johnny Harris [x-XdOaZPhBw][harris], 9:35–10:10 | notes heatmap readings |
| Drop starting 30–120 s before the end | Outro, recap, caveat or long reflections | Cut them; end at the payoff; make the outro a CTA | PRACTITIONER on graphs | Erudite Magic recap before 10:06 ([RR#4][rr4]); Bitty Plays Poker final ~2 min ([RR#2][rr2]); Jason Farmer caveat near the end ([RR#14][rr14]) | as listed |
| Drop only in the final seconds (20–30 points) | Normal. It appears even on MrBeast's graphs. YouTube: "The dip at the end means you saw the outro coming and moved on." | Usually nothing. Do not flag it by itself. | DATA (2 graphs) / PRACTITIONER (T1) | MrBeast, unnamed ([PDF][mbpdf] p.28, p.32) | [V8f_VWMV8pY][ci22] at 00:33–00:57 |
| Late drop after an abrupt end with no CTA | Nothing left to stay for | Foreshadow a second payoff; add a next-video CTA | PRACTITIONER on a graph | LadToDad, "I Purchased Baby RONALDINHO!", ~8:00 and the end | [RR#4][rr4] |
| Late dip during a full demo | Some viewers want the demo and others do not | Acceptable; not every end drop needs fixing | PRACTITIONER on a graph | Jazzmentl, "How to Play Salsa Montuno on Piano", final demo | [RR#4][rr4] |
| Spike above 100% at the first frame | Measurement artefact or replays (`audienceWatchRatio` > 1) | Read from ~0:01. Discount spikes on low-view videos. | PRACTITIONER | Jak Lei, "You're Not A Real Man Until You Unf*ck Your Testosterone Levels", 0:00 | [RR#1][rr1]; [API][api] |
| A slow start that still holds (80% at 0:30) | A loyal niche audience | Split new vs returning viewers before copying it elsewhere | DATA (n=1) + PRACTITIONER | Only Trails, "I Got an Elite Clue…" | [RR#3][rr3] |
| Spike mid-video | Rewatched or shared, **or** unclear and replayed, **or** a skip target | Check the content at the spike and the dip that follows it. A demo spike tells you what to make more of. | PRACTITIONER (T1) + practitioner graphs | Creator Insider demo spikes, [zNy3jxmT26o][ci21km] at 04:13 | [Help 9314415][h9314415]; [RR#1][rr1]; [RR#4][rr4] |
| Top moments late in the video | Good material comes after many viewers have left | Move it earlier | PRACTITIONER (T1) | — | [Help 12942217][h12942217] |
| Watch time falls on the subscriptions-feed source | "Probably your new content isn't as engaging as your previous videos" | Fix the content, not the targeting | PRACTITIONER (T1, Old) | — | [yBPZy-S4fIE][ci21wt] at 04:11–04:30 |
| Watch time collapses after a thumbnail-style change | "Viewers didn't recognize their content": new packaging changes who arrives | Change the packaging style gradually | PRACTITIONER (one-channel anecdote, T1) | — | [yBPZy-S4fIE][ci21wt] at 01:45 |

### D2. Reading method and iteration

| Practice | Tag | Source |
|---|---|---|
| Compare against your own similar-length videos (the grey band), not against a published benchmark. Beat your own best. | PRACTITIONER (T1, T3) | [Help 1715160][h1715160]; Beaupré [rHLjxrbXmmY][ci26] at 14:12–14:28; Film Booth [YwbPVcGQT5s][fb21] at 01:17–01:35 |
| Absolute retention (`audienceWatchRatio`) can exceed 1. Relative retention (`relativeRetentionPerformance`, 0.5 = median) compares with all similar-length videos. The current Studio Help no longer uses the term "relative retention". | PRACTITIONER (T1) | [API metrics][api]; [Help 1715160][h1715160] |
| `startedWatching` and `stoppedWatching` separate viewers who join mid-video from viewers who leave, which a dip alone cannot do. `averageViewPercentage` excludes looping-clip traffic since 2021-12-13. | PRACTITIONER (T1) | [API metrics][api] |
| Split the curve by subscriber/non-subscriber, new/returning and organic/paid. Tested in March 2024; segment breakdowns now sit in Advanced Mode. YouTube gives no separate retention guidance per segment. | PRACTITIONER (T1) | [Social Media Today 2024-03-20][smt24]; [Help 9314415][h9314415]; [Help 1715160][h1715160] |
| Use the subscriptions-feed traffic source as a control: the audience is the same every upload. | PRACTITIONER (T1) | [rHLjxrbXmmY][ci26] at 35:51–37:03 |
| A bad curve from embeds, ads or friend links does not by itself hurt Home, because ranking for Home weights behaviour in the Home context. | PRACTITIONER (T1) | [rHLjxrbXmmY][ci26] at 34:19–34:56 |
| Long and evergreen videos often get most of their views "a month or … later" and may be saved for TV in the evening, so early-hours metrics understate them. | PRACTITIONER (T1) | [rHLjxrbXmmY][ci26] at 06:14–07:05, 08:14 |
| Judge each video by its intent: a community video by subscribers and AVD, a tentpole by reach. Compare against your own baselines, not your top video. | PRACTITIONER (T1) | YouTube Creators [s0HWdnIU5RA][yt26wt] at 00:34, 03:05 |
| Compare videos on first-day data "to make it apples to apples". | PRACTITIONER (T2), with graphs | [PDF][mbpdf] p.27–29 |
| Checkpoints: minute 1, minutes 1–3, re-engagement at ~3, minutes 3–6, re-engagement at ~6, then the back half. Every crew member must know "what minute mark" they are working on. | PRACTITIONER (T2) | [PDF][mbpdf] p.7–9 |
| Read the curve segment by segment (S1, S2, …) and attribute the loss to each. Example: Exposure Ninja S1 lost ~30% and S2 and S3 lost 5–10% each. | PRACTITIONER on graphs | [RR#5][rr5] |
| Fix after upload: check retention after a few days and cut what does not serve the video in the Studio editor. | PRACTITIONER (n=1) | [RR#7][rr7] |
| Look at retention "not just in a video but across videos". Check the Audience tab for which videos grow the audience. | PRACTITIONER (T1, second-hand) | Ritchie via [Buffer 2025][buffer]; [Tubefilter 2024][tf24] |
| Studio key moments need a video of ≥60 s with ≥100 views and lag 1–2 days. The report exists only per video. | PRACTITIONER (T1) | [Help 9314415][h9314415] |

---

## Section E · Myths and contested claims

| Claim | Who claims what | Status |
|---|---|---|
| "Average YouTube retention is 23.7%; 16.8% of videos keep half; 55% lost in the first minute; 5–10 min retains best at 31.5%" (Retention Rabbit 2025) | Repeated in 2025–26 blogs. The vendor's site ([retentionrabbit.com][rrabbit]) has no report page and no methodology, and the secondary versions disagree on sample size and on the length table. | **Unverified. Do not use.** The one blog cited for it turned out not to contain it (see Refuted). |
| "Videos where >65% pass the first minute get 58% higher AVD" (Retention Rabbit) | Seen only second-hand | **Unverified.** |
| Niche "strong retention" bands (education 45–55%, gaming 35–45%, …) | prepublish.ai says its brackets are "aggregated from surveys and secondary reports rather than measured". The Backlinko and Tubular sources it cites do not contain the figures. | **Unsourced.** |
| "Good retention is 50/60%" | Film Booth: "a good percentage isn't 50% or 60. It's 85 in the case of Mr. Beast … this number doesn't matter at all"; beat your own best ([YwbPVcGQT5s][fb21] at 01:17–01:35). | The 85% figure is unsourced. The "beat your own" framing matches YouTube's own-channel band. |
| A fixed cross-channel benchmark exists | YouTube publishes none; it offers only similar-length comparisons inside Studio. | **Settled: no.** |
| "90% of viewers decide in the first few seconds" | vidIQ 2025 ([WHGw3j2BUG0][vidiqintros] at 00:08 in the raw captions) | **Unsourced.** |
| A slow first hour after upload kills the video | Beaupré 2026: no. Signals are learned per audience segment ([rHLjxrbXmmY][ci26] at 03:14–05:43). | **Refuted by T1.** |
| Cold open beats a branded intro (controlled evidence) | Every source is PRACTITIONER. Test & Compare covers thumbnails and titles only ([Creator Insider][testcompare]); there is no native intro A/B. | **No controlled test exists.** |
| Spikes mean good moments | YouTube: a spike can mean unclear content was replayed. Practitioners show spikes made by skipping a hook or skipping to a tip. A spike can also come from people skipping forward ([V8f_VWMV8pY][ci22] at 00:49). | **Contested.** Read the spike together with the dip after it. |
| "The algorithm pushes long videos" | Beaupré and Ritchie 2026: it is **pulled** by TV viewers ("It's not like YouTube is saying, 'Oh, well, we want long videos, so let's juice that'"; [rHLjxrbXmmY][ci26] at 16:32–18:57). Galloway names mid-roll money and TV as joint causes ([WyiGFFTnIS4][cs26] at 06:29). | **Contested.** YouTube denies a length preference; analysts point to incentives. |
| "Longer is always better in the TV era" | Galloway: given "a great 12-minute video or a great 24-minute video … I'll make the great 24-minute video"; Red Bull's 31-min Everest ski video, few cuts, no narration, 30M+ views ([WyiGFFTnIS4][cs26] at 04:30–06:56, 08:48–09:02; no direct link). Colin, in the same episode: on TV he looks for **6–8 min** videos from new creators (07:14–08:31). YouTube 2020: "The run-time should match the content" ([G1tHzUGdMwY][goodrow20] at 01:57–02:50). Beaupré 2026: YouTube weighs absolute **and** relative watch time ([rHLjxrbXmmY][ci26] at 11:39–12:17). | **Contested.** No causal data separates length from topic. |
| Padding raises watch time | YouTube 2020: "start padding the length … it often hurts – not helps" ([G1tHzUGdMwY][goodrow20] at 00:53–01:57). YouTube 2021: only survey-rated "valued watchtime" counts as valued ([Goodrow 2021][goodrow21]). YouTube 2026: time spent "hoping for a payoff" is discounted ([rHLjxrbXmmY][ci26] at 12:17–12:49). Galloway: "you can't get away with just a great title and thumbnail with no substance anymore", tied to "regrettable watch time" ([WyiGFFTnIS4][cs26] at 24:47–25:09). | **Negative finding** (in YouTube's words; no numbers published). |
| "Watch time is king" | YouTube retracted it as the sole target. Clicks gave way to watch time in 2012 ("less clicking, more watching", [YouTube blog 2012][yt12]), after adding watch time produced "an immediate 20% drop in views". Watch time was then weighted by 4–5-star survey ratings ([Goodrow 2021][goodrow21]), then reframed as satisfaction: "how they feel about the time they're spending" (Beaupré 2025 via [Buffer][buffer]); "North Star is long-term user value" ([rHLjxrbXmmY][ci26] at 13:03–13:43). Surveys "help the system understand satisfaction, not just watch time" ([Help 16089387][h16089387]). | **Retracted by the platform.** |
| "Satisfaction replaced watch time in an early-2025 discovery overhaul" | Vendor blogs (outlierkit, virvid.ai). YouTube sources say watch time is one signal among many, with surveys added. | **Unverified**; no YouTube source found. |
| "Home feed cut long-form slots from ~12 to 2 (−80%), Dec 2025" | Mario Joos on [X][joos] via [ppc.land][ppchome], about 1,000 channels, no method given. Beaupré 2026: the desktop homepage redesign "drove more … attention and engagement around long-form" ([rHLjxrbXmmY][ci26] at 19:19–20:32). Galloway sees no material decline in his clients' viewership ([WyiGFFTnIS4][cs26] at 11:51, 13:17). | **Contested.** A practitioner screenshot against a YouTube experiment claim. |
| "Shorts destroyed attention spans for long-form" | Galloway: client AVD rose 77% in the years after Shorts launched. | **Contradicted** by client data. |
| "10-minute videos: YouTube loves that number" | Film Booth 2019 ([TplwkCc89wU][fb19] at 00:44). It comes from the old ~10-min mid-roll threshold; the threshold is now 8 min, and YouTube does not endorse stretching for ads ([Help 6175006][h6175006]). | **Folklore, outdated.** |
| Open loops work through the Zeigarnik effect ("people remember unfinished things") | A 2025 meta-analysis: "no memory advantage for unfinished tasks", but "a general tendency to resume tasks" (Ovsiankina) ([Ghibellini & Meier 2025][ghib]) | **Refuted mechanism (THEORY).** Use the information gap and resumption instead. |
| Never reveal the outcome early | MrBeast holds the winner until the end ([memo][mbmemo]). [Leavitt & Christenfeld 2011][leavitt]: "Story Spoilers Don't Spoil Stories" (lab, short stories; abstract not retrieved). | **Contested.** Revealing *what* happens may keep tension that rests on *how*. Untested on video. |
| A teaser before an ad keeps viewers through the ad | Johnny Harris heatmap: near zero during both breaks, a spike at re-entry | **Against (n=1).** |
| Fixed re-hooks at 3 and 6 minutes are universal | The memo's marks fit its own 13:37 average | **Unvalidated** for 20–30 min videos. |
| More pattern interrupts = more attention | Lang: edits improved recognition; more than ~10 scene cuts per 2 min reduced it; unrelated cuts are not encoded | **Backfire condition (THEORY).** |
| Fake open loops and artificial stretching raise watch time and reach | YouTube discounts unvalued time. Mohan 2026: YouTube is "building on our established systems… combatting spam and clickbait" ([2026 letter][mohan26]). | **Against (T1, no data).** |
| The back half can be weaker | The memo says so, and adds "Many videos have been killed because the back half content was ass". Mark Rober's game 2 shows a mid-video skip. | **Nuanced:** weaker means slower and more explanatory, not filler. |
| "Ultra fast pacing doesn't work" | MrBeast 2024: "lets get rid of the ultra fast paced/overstim era of content. It doesn't even work" ([X][mbx1], no figures). Ex-editor Trey Yates: the fast style came from analytics, and viewers now want "something to sit back and relax to" ([Passionfruit 2024][passion]). The memo still asks for "lots of quick scene changes" in minutes 3–6. In Lang's lab, edits *improved* recognition. | **Contested.** The evidence supports *varied* pacing, not slow pacing. The notes disagree on sourcing: the endings researcher could not open a primary source for MrBeast's slowdown, while the pacing researcher quotes his 2024 X posts as relayed by [GIGAZINE][gigaret] and [Passionfruit][passion]. |
| Fixed cut-rate numbers: a cut every 1.3–1.5 s; every 3–8 s; a "pattern interrupt every 5–7 s"; a "new stimulus every 20–30 s" | Editor Dara Pesheva via [GIGAZINE 2024][gigaret] (cuts under 2 s, every 1.3–1.5 s); [1of10][oneof10] (3–8 s). The 5–7 s and 20–30 s figures appear only in vendor-blog summaries, and [Digital Information World][diw], named as the 20–30 s source, does not contain it. Noah Kettle: some 90-minute whiteboard videos beat "optimized" retention-edited ones. | **Folklore.** No tier 1–4 measurement links YouTube cut rate to retention. |
| "Speak at 150–160 wpm" | A 1967 guideline for live lectures. [Guo 2014][guo]: faster speakers held longer; mid-speed was least engaging. | **Contradicted by DATA** (MOOC). |
| Slower editing means less speech | Caption count: the 2024 "slower" MrBeast videos run 194–208 words per runtime minute, against 163 in 2020 (188 if music tags count) | **Against (small n).** |
| Talking head vs B-roll | [Guo][guo]: alternating raised engagement, but repeated switching was called "jarring" | **Mixed.** The optimal switch rate is unknown. |
| Slow intros always lose | Only Trails held 80% at 0:30 despite a slow start ([RR#3][rr3]). Breakout Cards found that cutting straight to the first deal *worsened* early retention on the creator's other videos ([RR#5][rr5]). | **Contested, n=1 each.** |
| Abrupt ending vs a spoken next-video hand-off | MrBeast: always end abruptly and never signal the end ([PDF][mbpdf] p.8). Blackman criticises an abrupt end with no next-video pointer and wants the outro to be only a CTA ([RR#4][rr4]; [5 mistakes][rr5m]). Leroy Creates: "The best outro is an intro to another interesting idea"; new viewers "click off with the first word that indicates an ending is happening" (no data; [newsletter][leroy]). | **Contested.** Both sides agree on no recap, no signalling and no lingering. Neither shows a graph comparing the two endings. |
| An abrupt ending removes the end cliff | MrBeast's own graphs drop 20–30 points in the final seconds | **No.** |
| Reflective outros always hurt | Blackman: "ending the video with reflections and personality is ok in the right niche" ([RR#2][rr2]) | **Niche exception.** |
| End screens or "session time" improve recommendations | Blackman says it without a source ([RR#4][rr4]). YouTube says end screens were "designed to keep users engaged" ([TechCrunch 2016][tc16]) and publishes no test numbers or ranking statement. | **No first-party evidence.** |
| Dead air under end-screen elements hurts | Only SEO blogs say so | **No tier 1–3 source.** |
| Clickbait is bad | Veritasium separates accurate curiosity-gap "legitbait" from misleading "clicktrap" ([S2xHZPH5Sng][vclick] at 04:21–05:51; THEORY, 2021). The memo says "match the expectations of the clickbait". YouTube moved ranking off clicks because "Ranking by click-through rate often promotes deceptive videos that the user does not complete" ([Covington et al. 2016][covington]). Maliciously misleading packaging that "does not deliver what was promised" violates policy and can lead to demonetisation ([Help 2801973][h2801973]). Off-platform, clickbait headlines "may lower" perceived credibility ([Molyneux & Coddington][molyneux]; THEORY, text news). | **Contested at the margin.** A strong promise is fine **if the opening delivers it**; the mismatch is what fails. |
| "Relative retention" in Studio | Third-party guides still describe it. Current Help does not use the term; only the API keeps `relativeRetentionPerformance`. The typical-retention baseline also changed from "past year" to "10 latest". | **Old tutorials are unreliable.** |

### Conflicts between the notes

| Point | One side | Other side |
|---|---|---|
| Date of the MrBeast document | Anatomy notes: "leaked internal memo, ~2022" | Middle notes: "undated, roughly 2023–24", leaked Sep 2024 ([GIGAZINE][gigaleak]). Diagnosis notes: the PDF producer string matches the Chrome build of Sept 2024, and it circulated Sept 2024. |
| "Eight days" line in the prison video | Researcher: 3:41 | Fact-check: 3:44 |
| Effective date of the view-count change | [Help 2991785][h2991785]: 2026-08-24 | [vidIQ][vidiqviews]: 2026-08-27 |
| Beaupré 2026 quotes | Anatomy notes read them from the transcript, with timestamps | Middle notes had them only through [PPC Land][ppcsubs], with no exact second |

---

## Refuted during verification

| Claim | Reason |
|---|---|
| vidIQ's own channel: 3:11 AVD and 30.3% APV across 16.5M long-form views | **Unconfirmable.** The vidIQ blog returned 403 and 429, so the figures came only from a search-engine extract. |
| vidIQ APV target bands by length: <5 min 50–70%, 5–15 min 40–55%, 15–30 min 30–45%, >30 min 25–35% | **Unconfirmable**, for the same reason. |
| The Retention Rabbit figures (23.7% etc.) "repeated in" prepublish.ai's 2026 benchmarks post | **Refuted as cited.** The page does not mention Retention Rabbit or the figures. The figures stay "do not use". |
| "Retention Rabbit: >65% past the first minute → 58% higher AVD", seen on prepublish.ai | **Refuted for prepublish.ai.** The claim is not on the page; gyre.pro was not checked. |
| "Fast pacing combined with arousing content can tip into cognitive overload" (Lang et al. 1999) | **Unconfirmed.** Neither cited source shows it, and the 1999 paper has no retrievable abstract. |
| Jak Lei: "padding with clips and B-roll goes with a mid-video slide, about 33% left by 3:00" | **Refuted.** The source says ~33% were still *watching* at ~3:00 of a 13-min video (APV 27.8%), and its padding remark is about the first minute. |
| "Don't copy the fast style": non-stop cutting went with a drop at the start of a later section | **Refuted as framed.** The RR#11 quote is about one creator's rough visual style. In RR#7 the non-stop cutting (Thomas Chow) is tied to a drop over the **first 40 s**, and the fix was to slow down "once the video properly started". |
| Beaupré's "We don't want to just assume that all time is valuable" sits in the 9:57–15:43 chapter | **Placement unconfirmed** when relayed second-hand. The anatomy notes place it at 12:17–12:49 from the transcript. |

---

## Coverage

| Prompt item | Status | What is missing |
|---|---|---|
| 1. Anatomy of the curve, benchmarks by length and genre | **Partial** | YouTube's definitions and Studio thresholds are fully covered. **Platform-wide benchmarks by genre (essay, vlog, tutorial, challenge, documentary) at 30 s, AVD and APV with a disclosed sample: unsourced.** The only genre split with data is MOOC lectures vs tutorials (not YouTube). Whether the Studio retention graph uses all views or engaged views after 2026-08-24 is not stated. |
| 2. First 30 seconds | **Partial** | YouTube guidance and practitioner frameworks are covered. **A controlled cold-open vs branded-intro test: unsourced.** **A published method or thresholds for separating packaging mismatch from a slow opening: unsourced**; the subscriptions-feed rule is an inference. |
| 3. Keeping the middle | **Partial** | Every technique has a mechanism or practitioner source, and most have a named example with a timestamp. **No retention-graph or A/B evidence for any middle technique**: the examples are replay heatmaps (n=1). **Music changes: unsourced.** **Chapters' effect on retention: unsourced.** |
| 4. Pacing and editing tempo | **Partial** | Speech rate (MOOC DATA), film shot-length data and lab cut limits are covered, and the 2024–26 slowdown has practitioner and T1 statements. **Cuts per minute measured on YouTube: unsourced.** **Genre differences in YouTube pacing: unsourced.** **YouTube data showing slower videos retain better: unsourced.** |
| 5. Reading the curve for diagnosis | **Mostly answered** | Studio and API metrics, curve-shape readings and iteration practices are covered. Most shape → cause pairings are n=1 practitioner readings from 2022–23. **Sample-level data on new vs returning retention gaps: unsourced.** |
| 6. Length, watch time, satisfaction | **Answered** | YouTube's 2020–2026 position (valued watch time, surveys, regret, absolute vs relative time, pull not push) is covered at T1. **Causal data separating length from topic: unsourced.** |
| 7. Endings | **Partial** | End-screen requirements and practitioner rules on graphs are covered. **A first-party statement on how end screens or outros affect recommendations or session time: unsourced.** **End-cliff size by genre or length: unsourced.** **A list of phrases to avoid with measured effect: unsourced.** The abrupt end vs hand-off conflict has no comparative graph. |
| 8. Negative findings | **Mostly answered** | Clickbait history, policy, padding, Zeigarnik, the 10-minute folklore and the fast-pacing reversal are covered. **YouTube's "egregious clickbait" enforcement post (India, ~Dec 2024): not reached.** |

Sources the researchers could not reach: Paddy Galloway's own channel and newsletter, 1of10 and Jon Youshaei studies, Film Booth case studies from 2025–26, and two official YouTube videos that were bot-blocked ([HI03HqWdX0k][hi03] on engaged views, [6NKhcV3v2nw][6nkh] on keeping viewers watching).

[h9314415]: https://support.google.com/youtube/answer/9314415
[h12942217]: https://support.google.com/youtube/answer/12942217
[h1715160]: https://support.google.com/youtube/answer/1715160?hl=en
[h2991785]: https://support.google.com/youtube/answer/2991785
[h16089387]: https://support.google.com/youtube/answer/16089387
[h6175006]: https://support.google.com/youtube/answer/6175006?hl=en
[h6388789]: https://support.google.com/youtube/answer/6388789?hl=en
[h2801973]: https://support.google.com/youtube/answer/2801973?hl=en
[api]: https://developers.google.com/youtube/analytics/metrics
[ci26]: https://www.youtube.com/watch?v=rHLjxrbXmmY
[ci21km]: https://www.youtube.com/watch?v=zNy3jxmT26o
[ci22]: https://www.youtube.com/watch?v=V8f_VWMV8pY
[ci21wt]: https://www.youtube.com/watch?v=yBPZy-S4fIE
[testcompare]: https://www.youtube.com/watch?v=0veygaKzdjw
[yt26wt]: https://www.youtube.com/watch?v=s0HWdnIU5RA
[goodrow20]: https://www.youtube.com/watch?v=G1tHzUGdMwY
[goodrow21]: https://blog.youtube/inside-youtube/on-youtubes-recommendation-system/
[yt12]: https://blog.youtube/news-and-events/youtube-search-now-optimized-for-time/
[mohan26]: https://blog.youtube/inside-youtube/the-future-of-youtube-2026/
[covington]: https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45530.pdf
[sej21]: https://www.searchenginejournal.com/youtube-typical-audience-retention/421700/
[sej23]: https://www.searchenginejournal.com/youtube-algorithm-insights-from-creator-liaison-renee-ritchie/493901/
[smt24]: https://www.socialmediatoday.com/news/youtube-tests-new-audience-filters-for-its-video-retention-stats/710915/
[tf24]: https://www.tubefilter.com/2024/08/26/rene-ritchie-shorts-creator-faqs/
[buffer]: https://buffer.com/resources/youtube-algorithm/
[tc16]: https://techcrunch.com/?p=1407335
[mbmemo]: https://www.alexanderjarvis.com/memo-how-to-succeed-in-mrbeast-production/
[mbpdf]: https://cdn.prod.website-files.com/6623b7720b009050313e701c/66ede69453b7bbadcd2f05a8_How-To-Succeed-At-MrBeast-Production%20(2).pdf
[gigaleak]: https://gigazine.net/gsc_news/en/20240917-mrbeast-youtube-production
[gigaret]: https://gigazine.net/gsc_news/en/20240403-retention-editing-beastification-may-be-end/
[passion]: https://passionfru.it/youtube-editing-mrbeast-54202/
[mbx1]: https://twitter.com/MrBeast/status/1764293361437909406
[mbx2]: https://twitter.com/MrBeast/status/1774114267261767898
[cs25]: https://www.youtube.com/watch?v=L9CO1FcRHCM
[cs26]: https://www.youtube.com/watch?v=WyiGFFTnIS4
[vidiqviews]: https://www.youtube.com/watch?v=We8TVsjs2B8
[vidiqintros]: https://www.youtube.com/watch?v=WHGw3j2BUG0
[fb21]: https://www.youtube.com/watch?v=YwbPVcGQT5s
[fb19]: https://www.youtube.com/watch?v=TplwkCc89wU
[oneof10]: https://1of10.com/blog/what-is-a-jump-cut/
[diw]: https://www.digitalinformationworld.com/2025/08/how-mrbeast-builds-viral-videos.html
[guo]: https://pg.ucsd.edu/publications/edX-MOOC-video-production-and-engagement_LAS-2014.pdf
[wistia]: https://wistia.com/learn/marketing/optimal-video-length
[pew]: https://www.pewresearch.org/internet/2019/07/25/a-week-in-the-life-of-popular-youtube-channels/
[backlinko]: https://backlinko.com/youtube-ranking-factors
[rrabbit]: https://www.retentionrabbit.com/
[joos]: https://x.com/MarioJoos/status/2002768005353140427
[ppchome]: https://ppc.land/youtubes-home-feed-quietly-kills-long-form-video-discovery/
[ppcsubs]: https://ppc.land/subscribers-skip-90-of-uploads-in-their-feed-youtube-director-says/
[rr1]: https://georgeblackman.substack.com/p/reviewing-your-retention-graphs-1
[rr2]: https://georgeblackman.substack.com/p/retention-review-2-payoff-outro-core
[rr3]: https://georgeblackman.substack.com/p/this-creator-had-70-retention-after
[rr4]: https://georgeblackman.substack.com/p/retention-review-4-second-payoff
[rr5]: https://georgeblackman.substack.com/p/retention-review-5-why-should-i-care
[rr6]: https://georgeblackman.substack.com/p/retention-review-6-and-this-but-that
[rr7]: https://georgeblackman.substack.com/p/retention-review-7-he-fixed-retention
[rr11]: https://georgeblackman.substack.com/p/rr11-were-all-trapped
[rr12]: https://georgeblackman.substack.com/p/rr12-this-system-gets-more-views
[rr13]: https://georgeblackman.substack.com/p/rr13-the-luckiest-shrimp-in-the-world
[rr14]: https://georgeblackman.substack.com/p/rr14-this-technique-will-save-your
[rr5m]: https://georgeblackman.substack.com/p/5-retention-killing-youtube-mistakes
[leroy]: https://creatorunited.beehiiv.com/p/stop-making-outros
[loew]: https://doi.org/10.1037/0033-2909.116.1.75
[kang]: https://doi.org/10.1111/j.1467-9280.2009.02402.x
[lc4mp]: https://en.wikipedia.org/wiki/LC4MP
[kubey]: https://www.simpletoremember.com/vitals/TV_Danger_SCIAM2.htm
[cut16]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5256470/
[cut10]: https://doi.org/10.1177/0956797610361679
[ghib]: https://doi.org/10.1057/s41599-025-05000-w
[leavitt]: https://doi.org/10.1177/0956797611417007
[peakend]: https://en.wikipedia.org/wiki/Peak%E2%80%93end_rule
[fk93]: https://doi.org/10.1037/0022-3514.65.1.45
[molyneux]: https://doi.org/10.1080/17512786.2019.1628658
[vclick]: https://www.youtube.com/watch?v=S2xHZPH5Sng
[mbprison]: https://www.youtube.com/watch?v=hD1YtmKXNb4
[mbfire]: https://www.youtube.com/watch?v=erQ_9yEz0ls
[mbcity]: https://www.youtube.com/watch?v=tWYsfOSY9vY
[mbisland]: https://www.youtube.com/watch?v=erLbbextvlY
[harris]: https://www.youtube.com/watch?v=x-XdOaZPhBw
[rober]: https://www.youtube.com/watch?v=0XgcOz95hTs
[vgps]: https://www.youtube.com/watch?v=tz23G_UXCGA
[vmaps]: https://www.youtube.com/watch?v=kS-CGkiPetQ
[hi03]: https://www.youtube.com/watch?v=HI03HqWdX0k
[6nkh]: https://www.youtube.com/watch?v=6NKhcV3v2nw
