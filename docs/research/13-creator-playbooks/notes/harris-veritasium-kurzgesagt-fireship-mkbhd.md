# 13 · Notes: Johnny Harris, Veritasium, Kurzgesagt, Fireship, MKBHD (item 2; items 4–5 for these schools)

Researcher share: item 2 for five comparison creators, plus items 4 (solo transfer) and 5 (negative findings) for their principles. Prompt: `prompts/13-creator-playbooks.md`. Collected 2026-10-12.

Method notes:
- Tags follow the CONTEXT block. **DATA** = a measurement over a sample (here mostly my own counts over a channel's upload list), an A/B test, or a retention graph shown. **PRACTITIONER** = a creator's stated practice, or a practice I observed in their video, with no data. **THEORY** = research or a model not tested on video. "Most replayed" heatmaps are replay intensity, not retention. A single-video heatmap is marked **DATA-weak**.
- Timestamp provenance: **(captions)** = YouTube auto-caption track pulled with `yt-dlp` on 2026-10-12, accurate to about ±3 s. **(chapters)** = the creator's chapter list, read through the YouTube Data API `videos.list` description. **(heatmap)** = the YouTube "most replayed" array in the `yt-dlp` info JSON pulled on 2026-10-12 for research 09.
- Channel statistics (lengths, title patterns) are my own counts. They cover every upload on each channel's `/videos` tab (Shorts excluded) as listed by `yt-dlp --flat-playlist`, up to 400 per channel, and use dates and durations from the Data API on 2026-10-12. Coverage: Johnny Harris 227 uploads (2018-11 → 2026-10), Veritasium 400 (2011-08 → 2026-09), Kurzgesagt 253 (2013-07 → 2026-10), Fireship 400 (2022-03 → 2026-10), MKBHD 400 (2021-04 → 2026-10). Views are never used as evidence of a technique. Median views appear only as descriptive context, and recent years are confounded by less time online.
- Search budget: the shared WebSearch budget for this run was used up before my first query (0 of 15+ queries possible). All sources were opened directly: known URLs, Wikipedia reference lists, creator pages, the Data API, and captions. YouTube's watch page was bot-gated for part of the session. I did not try to bypass it and resumed only when plain requests worked again. See Gaps.
- Quotes are short phrases; everything else is paraphrase.

---

## 2. Comparison creators: stated principles, structure, hooks, retention devices, packaging, what is unique

### 2.1 Johnny Harris (narrative/visual journalism; Newpress)

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| JH1 | A video takes about **4 months** from idea to release. He writes the script and directs the visuals at the same time, with colour-coded notes for visual assets and fact-checks. [verified: Podwise summary and chapters 3:40, 16:45, 27:06] | PRACTITIONER | *How I Write* (David Perell), episode page and chapter list on [Podwise](https://podwise.ai/dashboard/episodes/3299864). Only the chapter list and summary were readable (sign-in wall). | 2025-03-12 | Chapters 3:40 "Four-Month Video Production Process", 16:45 "Visual Storytelling and Scripting Process", 27:06 "Interplay Between Writing and Visuals" (chapters) |
| JH2 | **Promise and payoff.** The title and thumbnail make a promise that the video pays off, then the video widens the viewer's curiosity past the hook. [verified: chapter titles only] | PRACTITIONER | Same episode | 2025-03-12 | Chapters 11:23 "The Promise and Payoff", 46:06 "Video Titles, Thumbnails, and the Importance of Promises" (chapters) |
| JH3 | Stated pillars of YouTube writing: visual, plain, clear, concrete. He alternates "active prose" with "contemplative moments", uses a "let me show you" stance toward the viewer, and puts "craftsmanship over optimization". [verified: chapter titles only] | PRACTITIONER (chapter titles only; the content was not readable) | Same episode | 2025-03-12 | Chapters 31:40, 54:06, 1:04:28, 1:21:06 (chapters) |
| JH4 | **Greenlight filter = "I can see it."** A story passes his final filter only when he can picture a concrete visual: an intro, a data visualization or a colour scheme. Example: listening to a *Washington Post* investigation, he pictured a dark map, thin connecting lines and money icons. If he cannot see it, he can still make the video, but it is "way less pleasant". [verified; the "I can see it" line is at 54:07 and 58:00, the WaPo story is Trump and Egypt] | PRACTITIONER | Colin and Samir, [*An Honest Conversation with Johnny Harris*](https://www.youtube.com/watch?v=mFRMvhY9ajE) | 2025-03-04 | 54:09–55:00 visual filter; 55:20–56:00 the WaPo example; 57:08 "I want people to feel something" (captions) |
| JH5 | **Packaging before production.** On "story days", Johnny and Iz Harris draw thumbnails on a large sheet of paper and argue the idea out. Introduced about 6 months before the interview; Iz calls it "revolutionary". [verified] | PRACTITIONER | Same interview | 2025-03-04 | 47:51–48:15 (captions) |
| JH6 | **"Defend the story."** Iz's rule: asking 2–4M people for 30 minutes means the story has to be defended. Johnny agrees that gut feel works at about 100k viewers but not at 2–4M. Sponsors need "home runs" every time to pay 25 staff. [verified; Iz says "4 million", then "two to four million"] | PRACTITIONER | Same interview | 2025-03-04 | 48:35–49:35 (captions) |
| JH7 | **One-sentence pitch.** Anyone on the team can pitch, and a pitch is one sentence. Historically most staff pitches were not made. | PRACTITIONER | Same interview | 2025-03-04 | 52:21–53:40 (captions) |
| JH8 | **"Fresh brain."** Iz edits the story with no prior immersion, to find the most interesting part. Her reason: people steeped in a story, and experts, no longer know what is interesting. [verified] | PRACTITIONER | Same interview | 2025-03-04 | 1:00:51–1:01:15 (captions) |
| JH9 | Reporters on the team fact-check and story-produce. The schedule is fixed 6 months ahead. Johnny writes in time blocks and runs the team asynchronously by voice notes and Looms. | PRACTITIONER | Same interview | 2025-03-04 | 43:40–45:45, 47:42 (captions) |
| JH10 | **Packaging is the gate.** Johnny gives "if they don't click they don't watch" as the first rule of YouTube. The Trump and Kamala Harris biographies used the same thumbnail treatment, title pattern, music and art direction. Both did well. [verified] | PRACTITIONER | Same interview | 2025-03-04 | ≈10:00–10:40 (captions) |
| JH11 | Sponsors are held behind a "garden wall": advertisers can ask to skip an episode but have no editorial say. | PRACTITIONER (contradicted, see Negative) | Same interview | 2025-03-04 | 14:30–15:00 (captions) |
| JH12 | **Map craft is learned, and there is a free path.** He shows his bad 2012 first map and says years of After Effects tutorials got him better. Two workflows: (a) After Effects plus a reusable Illustrator base map, no plugins, used for years including at Vox; (b) the ~$200 GeoLayers plugin with Mapbox Studio styles, free for non-commercial use. | PRACTITIONER | [*How I Make My Maps*](https://www.youtube.com/watch?v=GsojLuJpe_0) (Intel-sponsored) | 2020-12-11 (possibly outdated tooling) | 0:23–0:40 first map; 3:31–3:50 "practice"; 5:06 workflow without plugins; 12:18 and 14:10 GeoLayers and Mapbox (captions) |
| JH13 | Music is commissioned (composer Tom Fox) and used as a storytelling tool. [verified] | PRACTITIONER | Standard description block "how i make my videos" (e.g. [GsojLuJpe_0](https://www.youtube.com/watch?v=GsojLuJpe_0)); [*How I Use Music*](https://www.youtube.com/watch?v=fqB5W-AdFqw) | 2019-10-31 | n/a |
| JH14 | **Length keeps growing.** Median long-form length: 13.2 min (2020, n=29) → 17.4 (2021) → 21.5 (2022) → 25.7 (2024, n=33) → 34.5 (2025, n=28) → 41.3 min (2026, n=8, excluding five 2–3 h uploads). Those five (e.g. *How Money Actually Works*, 2:58:31) are compilations of earlier videos; its chapter 0:00 is "Gold Explained, Finally". [verified: re-counted 2026-10-12, all medians and n match; 5 uploads in 2026 are over 2 h] | DATA (descriptive, own count) | [@johnnyharris/videos](https://www.youtube.com/@johnnyharris/videos) via Data API; chapters of [XXpqejgnaB0](https://www.youtube.com/watch?v=XXpqejgnaB0) | 2026-10-12 | n/a |
| JH15 | **Title signature (2024+, n=74).** 26/74 titles start with "Why" or "How". 9/74 use "Explained". 10/74 contain an all-caps emphasis word, acronyms excluded ("REAL" ×3, "BILLIONAIRE", "SO", "ACTUALLY", "WAR", "TRILLION", "WILD", "HEIST"). 0/74 use "!", 2/74 use "?". [verified after correction: 26/74, 9/74, 0/74, 2/74 match; the all-caps count was 9 → 10, and the "DAMN" example came from 2021/2023 titles outside the window] | DATA (descriptive, own count) | Same listing | 2026-10-12 | e.g. "The REAL reason the US can't beat Iran" |
| JH16 | Upload rate was cut to about 2–2.5 videos a month so Johnny only makes stories he "feels". A push toward ~4 a month had produced stories he disliked. [verified] | PRACTITIONER | C&S interview | 2025-03-04 | 1:02:33–1:05:20 (captions) |

**Example video: [*China's Dirty Money Problem, Explained*](https://www.youtube.com/watch?v=nAFw5i39m9I)** (2026-04-16, 33:17). Timestamps are (captions); chapters and heatmap as marked.

| Time | Beat | Device |
|---|---|---|
| 0:03 | A subject's line about "ghosts" | Cold-open quote before any context |
| 0:12–1:13 | Johnny holds a bag of $100,000 and role-plays a drug dealer who cannot spend it | First-person **prop hypothetical**: the viewer is put inside the problem |
| 1:13 | "No, I did not sell drugs… it's not even real" | Reveal and reset; the prop stays as an anchor |
| 1:30–2:00 | A $50M single-city case → "3 to 5% of world GDP", about $4T | Scale escalation with numbers |
| 2:26 | Names the concept "flying money" | Labelled mystery |
| 3:07–3:25 | Credits the investigator who pitched him the story | Source credibility |
| 3:27 | Says he wants to show how it works, what it enables and what to do about it | The "let me show you" promise (JH3) |
| 3:35–5:31 | Sponsor read, bridged by "I'm in Taiwan right now…" | **Early sponsor** (~11%), introduced with a location vlog line |
| 5:31 | Chapter "Origins": Tang dynasty (chapters) | Jump back in history after the hook |
| 13:00–13:30 | "Now watch this clever move": the trade-invoice laundering mechanism | Mechanism demo. Heatmap 0.82, the second-highest region (heatmap) |
| 5:20–5:40 | Highest heatmap value (1.0) | Lands right after the sponsor ends, so this is a **skip-landing** artifact, not a content peak (DATA-weak) |
| 31:14–32:38 | Experts on enforcement incentives; music out | Ends on solutions and implications, with no recap |

Heatmap decile means: 0.20, 0.31, 0.43, 0.50, 0.35, 0.27, 0.34, 0.31, 0.20, 0.04 (heatmap). Second example of the opening device: [*Gold Explained, Finally*](https://www.youtube.com/watch?v=JMObz0Dgq7M) (2025-10-24). It opens on **all the gold ever mined, shown as a cube in Washington, D.C.** (0:00–0:20), cuts to a news montage for timeliness (1:08–1:24), and teases the thesis with "it never went away" (1:28) (captions).

**What is unique:** maps and data visualization as the main visual language, first-person presence as a guide, and a greenlight test that asks for a visual image before the story is approved (JH4). Packaging is drafted before research (JH5).

**Negative and contested (Harris)**
- **Accuracy.** McGill OSS (Jonathan Jarry, ["The Many Mistakes of Johnny Harris"](https://www.mcgill.ca/oss/article/critical-thinking-health-and-nutrition/many-mistakes-johnny-harris), 2024-08-02) lists errors: the UAP video's foreign-drone suggestion, at t=17:42 per the article; the Australian submarines described as "given"; and Columbus's land-claiming, dramatised by Harris's own account as a "device". Harris did not cite sources until September 2022. The article argues that ominous music, rapid montage and document close-ups "dull your critical thinking skills" [verified]. **The same devices that drive retention are named as the epistemic risk.** PRACTITIONER (critic).
- **Sponsor wall breached.** The video "How China Became So Powerful" was co-written with the World Economic Forum, and the disclosure came only in the last minute (same McGill article) [verified]. This contradicts JH11, although JH11 was stated later (2025) and may reflect a fixed process.
- **Framing.** The Kyiv Independent (Jason Blevins, [2024-12-11](https://kyivindependent.com/youtuber-johnny-harris-lens-on-eastern-europe-is-distorted-and-irresponsible/)) criticised "Why People Blame America for the War in Ukraine" (2024-12-05). It was removed, and Harris apologised on Dec 6 for omitting Eastern European perspectives. The piece also names a cut to a politician during a "rules-based order" line as editing used as persuasion. [verified]
- **Gut-only greenlighting failed internally.** Iz describes stories Johnny "hated" being pushed through, and fights months into production (C&S 2025, 1:02–1:05, captions). The fix was the visual filter, the one-sentence pitch and fewer uploads (JH4, JH7, JH16).

### 2.2 Veritasium (misconception-first explainers; Derek Muller and team)

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| V1 | Stated rule: teaching has to account for what learners already know, including what they wrongly believe, so many Veritasium videos open with the misconceptions. [verified] | PRACTITIONER | Description of [*Why Do You Make People Look Stupid?*](https://www.youtube.com/watch?v=cY_o4A1wzsg) | 2012-03-18 (old, but the principle is unchanged) | n/a |
| V2 | **Why misconceptions go first.** Clear, well-illustrated explanations make students *feel* they learned and grow more confident, but tests show little learning. Putting the misconception in the video raises mental effort and learning. | THEORY [tag → THEORY: peer-reviewed learning research measuring test scores, not viewer behaviour on a platform; the paper's results were not readable (abstract elided by the publisher), only Muller's own summary in the video description, so no sample is shown here; mixed tags break the "keep the three apart" rule] | Description of [*Khan Academy and the Effectiveness of Science Videos*](https://www.youtube.com/watch?v=eVtCO84MDj8); Muller, Bewes, Sharma & Reimann, "Saying the wrong thing: improving learning with multimedia by including misconceptions", *J. Computer Assisted Learning* 2007, [doi:10.1111/j.1365-2729.2007.00248.x](https://doi.org/10.1111/j.1365-2729.2007.00248.x) (abstract paywalled; metadata via Semantic Scholar) | 2011 / 2007 | n/a |
| V3 | Restated in 2024: think about the misconceptions people bring in, or the video only reinforces them. He also says it is easy to watch a video and think you understand. [verified] | PRACTITIONER | [Univ. of Sydney news](https://www.sydney.edu.au/news-opinion/news/2024/11/05/the-element-of-truth.html) | 2024-11-05 | n/a |
| V4 | **Packaging is at least half the job.** Muller used to think his job was the video plus a title that described it. Now he says title and thumbnail are "at least half the job". [verified] | PRACTITIONER (creator analytics shown on screen) | [*Clickbait is Unreasonably Effective*](https://www.youtube.com/watch?v=S2xHZPH5Sng) | 2021-08-17 (older than 2024) | 7:22–7:49 (captions) |
| V5 | **"Legitbait" vs clickbait.** Packaging should be enticing and true. "There is no one true title" for a video. [verified] | PRACTITIONER [tag → PRACTITIONER: "legitbait" is a creator's stated practice and coinage (credited to Brady Haran), not research or a tested model] | Same video | 2021-08-17 | 5:26–5:50 (captions) |
| V6 | **Packaging is tested by polling the audience.** Candidate titles and thumbnails were put to Twitter and Patreon. Dropping "Surprising" from *The Secret of Synchronization* made it perform about 10% better. His claim: the more clickable titles and thumbnails often describe the content *better*. [verified] | PRACTITIONER (number stated; method not shown) | Same video | 2021-08-17 | 15:19–15:56 (captions) |
| V7 | **Old videos can be retitled.** "Why the Neutron is the Hero of Nuclear Physics" became "Why Einstein Thought Nuclear Weapons Impossible", and "Strange Applications of the Magnus Effect" became "Backspin Basketball Flies Off Dam". Views rose after each change (graph shown). Views fund the next video, which he calls a "symbiotic" loop. [verified] | PRACTITIONER + creator analytics (before/after only, no control) | Same video | 2021-08-17 | 16:07–16:40; 17:50–18:10 (captions) |
| V8 | An earlier hypothesis, later revised: the algorithm, not viewer preference, drives views, and CTR is "the key metric". [verified] | PRACTITIONER (outdated, 2019) | Description of [*My Video Went Viral. Here's Why*](https://www.youtube.com/watch?v=fHsa9DqmId8) | 2019-05-19 | n/a |
| V9 | **Now a team.** Nearly 20 people (2025), then "more than 30" (writers, directors, researchers, editors, illustrators, animators). Each video takes 2–6 months. Writer-directors and other hosts front some videos. Majority-owned by Electrify Video Partners since 2023-04-21. A team-run spin-off, InGenius, hosted by Latif Nasser, launched 2026-09-30. [verified; Electrify says "more than 30 people involved" in each video, which is not a headcount] | PRACTITIONER | [Sci. Am.](https://www.scientificamerican.com/article/how-youtube-star-derek-muller-of-veritasium-is-challenging-scientific/) 2025-05-28; [Electrify, Dec 2025](https://www.electrify.video/news/electrify-co-ceo-blog-post-about-veritasium-december-2025); [Electrify, 2023](https://www.electrify.video/post/electrify-completes-majority-investment-in-veritasium); description of [ONAuUyml0yI](https://www.youtube.com/watch?v=ONAuUyml0yI) | 2023–2026 | In [*This Skyscraper Was Days From Collapsing…*](https://www.youtube.com/watch?v=Q56PMJbCFXQ), producer-engineer Henry Van Dyck is the on-camera investigator from 0:59 (captions) |
| V10 | Team test for an idea: will it make people "change the way they view the world". Episodes run like a mystery novel, with layered demonstrations and "slow-burn narrative reveals". [verified; the "mystery novel" line describes Muller's post-2012 long-form style] | PRACTITIONER (journalist's paraphrase + team quotes) | Sci. Am. | 2025-05-28 | n/a |
| V11 | **Length doubled.** Median long-form length: 12.4 min (2019, n=31) → 18.1 (2021) → 23.4 (2023) → 25.4 (2024, n=27) → 32.8 (2025, n=30) → 30.2 min (2026, n=22). [verified: re-counted 2026-10-12] | DATA (descriptive, own count) | [@veritasium/videos](https://www.youtube.com/@veritasium/videos) via Data API | 2026-10-12 | n/a |
| V12 | **Title signature (2024+, n=79).** 16/79 titles are questions, 16/79 start with Why or How, 0/79 use "!", 0/79 have all-caps words. Recurring templates include "…And No One Knew" (2/79). "…is unreasonably fast/effective" appears once in the window (2026) and once before it (2021). [verified after correction: 16/79 questions, 16/79 Why/How, 0 "!", 0 emphasis caps match; "unreasonably" is one title in the window, not a recurring template] | DATA (descriptive, own count) | Same listing | 2026-10-12 | e.g. "Google Maps is unreasonably fast. Let me explain" |
| V13 | **Cold-open pattern (2025–26):** stakes, then one or two explicit questions, then a jump back to an origin story. [verified for Maps and Skyscraper captions; Internet not re-checked] | PRACTITIONER (observed, 3 videos) | See the beat table; [*The Internet Was Weeks Away From Disaster…*](https://www.youtube.com/watch?v=aoag03mSuXQ) (2026-02-25); [*Google Maps is unreasonably fast*](https://www.youtube.com/watch?v=kS-CGkiPetQ) (2026-05-30) | 2025–2026 | Internet: 0:00–1:04 stakes, told through expert soundbites → 1:07 "the story begins with a jammed printer". Maps: 0:00–0:41 the impossible number (about 10^220 routes, yet the app answers in 4 s) → 0:41 "So how is that possible?" → 0:53 a 1956 origin (captions) |
| V14 | **Sponsor read as a cliffhanger break**, not after the payoff. The read is placed mid-story and the video resumes with a hook line. [verified for Skyscraper and Maps] | PRACTITIONER (observed) | Skyscraper; Internet; Maps | 2025–2026 | Skyscraper 23:10–24:20, at ~70%, ending "now back to Project Serene" → phone-ring cliffhanger. Internet 24:42–25:55, at ~47%. Maps sponsor ends 9:39 (captions); the heatmap peak at 9:34 (1.0) is a skip landing (heatmap). A 2023 segue: "something that is not overhyped is this video sponsor", [czjisEGe5Cw](https://www.youtube.com/watch?v=czjisEGe5Cw) 10:51 (captions) |

**Example video: [*This Skyscraper Was Days From Collapsing And No One Knew*](https://www.youtube.com/watch?v=Q56PMJbCFXQ)** (2025-04-26, ~33:20). Timestamps are (captions).

| Time | Beat | Device |
|---|---|---|
| 0:00–0:14 | "This is Citicorp Center… a fatal flaw" | Place plus stakes in the first sentence |
| 0:14–0:28 | Collapse at 110 km/h, 200,000 people nearby, hurricane season weeks away | Concrete numbers and a ticking clock |
| 0:28–0:36 | Archival voice: "the only man in the world who knew this" | A secret held by one person |
| 0:36–0:57 | The dilemma: stay silent or risk ruin. "100% probability of total collapse". Two questions: how could he save New York, and how was this allowed? | **Two open loops stated outright** |
| 0:59 | The producer-engineer (not Muller) is introduced as the investigator | A team host (V9) |
| 1:05 | Jump to Citicorp in the 1960s | Origin after the hook |
| 1:19–3:17 | The church-site constraint → stilts at mid-face, explained with a chair analogy | Constraint drives the design; the analogy (3:01) is the "misconception" step: it "doesn't seem very stable" |
| 3:19–4:04 | A napkin sketch, then the engineer explains the chevrons on site | Expert explanation in place |
| 23:10–24:20 | Sponsor read, ending on a phone-ring cliffhanger | Sponsor as a mid-story break (V14) |
| 24:23–25:20 | The cover-up: "white lies", the NYT calls, then the NYT strike | A second act after the sponsor |
| 31:31–32:18 | The firm and the building owner decline comment; a 2021 NIST study raises new questions | A late complication, with the story left honestly unresolved |
| 32:19–33:18 | The case is now taught in engineering ethics, ending on an expert's "you must do something" | Ends on the moral, no recap |

**What is unique:** the viewer's wrong belief is the engine (V1–V3), the creator publishes his own packaging analytics (V4–V7), and since 2023 a team-and-investor model in which Muller is one of several hosts (V9).

**Negative and contested (Veritasium)**
- **Self-admitted overhype.** In 2023 Muller says he was "guilty of overhyping" BICEP2 in a 2014 video ([czjisEGe5Cw](https://www.youtube.com/watch?v=czjisEGe5Cw) 3:29–3:36, captions). The same video sells the sponsor with a hype joke (10:51).
- **Misconception framing invites corrections.** On the wind-powered cart, Muller conceded he "could have done a better job" explaining it the first time ([Wikipedia: Veritasium](https://en.wikipedia.org/wiki/Veritasium), citing Vice 2021-07-01). The 2021 electricity video needed a 2022 follow-up (research 09 notes, `09-storytelling-structures/notes/frameworks-stakes-payoff.md`).
- **The "look stupid" cost.** Street-quiz openings draw "condescending" and "pretentious" comments (Sci. Am. 2025), and Muller answered the charge in a 2012 video (V1).
- **Self-reversal on metrics.** In 2019 CTR was "the key metric" (V8). In 2021 the line became "legitbait": title tests that also have to match the content (V5–V6).
- **Observation, not confirmed:** on 2026-10-12 one video had two titles at once: "The Problem With Science Communication" (Data API) and "Why It's so hard to make science videos." (the `/videos` listing). This may be a live title test or a localisation. Not verified.

### 2.3 Kurzgesagt (animated explainers; studio of about 70)

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| K1 | **At least 1,200 hours per video.** Topics are picked by what excites the team. Research means books, papers and experts, and their view often changes during research. Writing is "the bottleneck": a few weeks to years per script. About 200 illustrated panels; 2–3 illustrators for 8–12 weeks; 2–3 animators for 8–10 weeks, all moved by hand; original music and sound per video; 2–4 videos in parallel; reviews every few days. [verified] | PRACTITIONER | [*How to Make a Kurzgesagt Video in 1200 Hours*](https://www.youtube.com/watch?v=uFk0mgljtns) | 2020-02-16 (process restated in 2024–25) | 0:22–0:41 topics; 1:01–1:40 research and script; 1:45–2:26 illustration; 2:54–3:32 animation; 3:36–4:24 music, parallel work, reviews (captions) |
| K2 | **Story test for an idea:** something surprising to learn, a larger context, or a new perspective. Experts fact-check the first readable draft, and "many scripts die" there. The hardest part is being brief without oversimplifying. A script is about 1,300 words. A second expert round uses different experts. Opinions are marked as opinions. [verified] | PRACTITIONER | [*Can You Trust Kurzgesagt Videos?*](https://www.youtube.com/watch?v=JtUAAXe_0VI) | 2019-03-03 (older; restated 2025, K4) | 0:31–0:47; 0:49–1:02; 1:15–1:19; 2:06–2:12; 1:22–1:35 (captions) |
| K3 | Process page: about a dozen script drafts; scene and metaphor sketching before illustration; one narrator (Steve), whose voiceover sets the animation timing; a sources sheet for every video. [verified] | PRACTITIONER | [kurzgesagt.org/youtube](https://kurzgesagt.org/youtube/) | undated, live 2026-10-12 | n/a |
| K4 | **2025 update:** 2–3 people fact-check each script against first-hand sources, ideally papers. 1–3 experts critique it. Fact-checking and sourcing alone take about 100 hours per video. [verified] | PRACTITIONER | [*AI Slop Is Destroying The Internet*](https://www.youtube.com/watch?v=_zfN9wnPvU0) | 2025-10-07 | 1:46–2:06 (captions) |
| K5 | Stated creed: "nothing is boring if you tell a good story". [verified] | PRACTITIONER | Channel description, [@kurzgesagt](https://www.youtube.com/@kurzgesagt) (Data API) | live 2026-10-12 | n/a |
| K6 | The effort is called a "really bad business decision", made possible by patrons. The shop is the most important income source. | PRACTITIONER | [*What Makes Kurzgesagt So Special?*](https://www.youtube.com/watch?v=OvKr6loCciE) 1:27–1:33 (captions); description of [1x-i9z617z4](https://www.youtube.com/watch?v=1x-i9z617z4) | 2024-04-30; 2023-03-28 | n/a |
| K7 | **Human-made pledge:** AI only as a utility (their example is an Illustrator-style align tool, or a faster search engine). The videos are "made by humans for humans and it will remain that way". [verified after correction: the quoted wording was a paraphrase; the actual line at 8:48–8:53 is quoted now] | PRACTITIONER | AI Slop video 8:18–8:53 (captions); its [sources page](https://sites.google.com/view/sources-aislop) | 2025-10-07 | n/a |
| K8 | **Length creep.** Median long-form length: 8.0 min (2019) → 10.7 (2021) → 11.8 (2024, n=27) → 12.3 (2025, n=26) → 14.1 min (2026, n=14). Median views fell from 9.2M (2024) to 5.5M (2025); recency confounds this. [verified: re-counted 2026-10-12, medians and median views match] | DATA (descriptive, own count) | [@kurzgesagt/videos](https://www.youtube.com/@kurzgesagt/videos) via Data API | 2026-10-12 | n/a |
| K9 | **Hook pattern:** a superlative fact with a vivid comparison → the naive intuition ("You'd think…") → a surprising answer within 30 s → "only half of the story" → a question → title card. The "half the story" loop is re-opened mid-video. [verified] | PRACTITIONER (observed) | [*Why Are There No Holes Around Trees?*](https://www.youtube.com/watch?v=pHJIhxZEoxg) | 2026-01-07 | See the beat table |
| K10 | **Second-person absolute claim plus self-contradiction.** The video opens "You will never leave the solar system". At 0:34 it turns on the channel's own earlier videos ("We've made countless videos imagining…"). A 6-second shop-pin plug runs **before** the hook (0:00–0:06). Heatmap peaks at 2:15–2:32, 5:13 and 8:11–8:20; the last decile is lowest (research 09). [verified after correction: the plug is 0:00–0:06, not 0:00–0:09] | PRACTITIONER (observed) [tag → PRACTITIONER: a single-video "most replayed" heatmap is neither a retention graph nor a sample; heatmap peaks re-pulled 2026-10-12 match (2:16–2:50, 5:14–5:31, 8:12–8:29; last decile lowest, 0.05)] | [*Why Humanity Will Never Leave The Solar System*](https://www.youtube.com/watch?v=Cyl3X88KEgg) | 2026-08-04 | 0:00–0:06 plug; 0:06–0:30 claim; 0:32 "how can this be?"; 0:57 "You don't understand how large space is. We don't either." (captions) |
| K11 | **Correction by re-upload.** The Ozempic video was revised and re-released longer. The team's statement: the first version "did not contain wrong information" but its framing was "not good enough". The old version was unlisted and a change log published. The same happened to the 2024 exercise video (made again with expert input after feedback). [verified] | PRACTITIONER | Description of [TYhNHX372ek](https://www.youtube.com/watch?v=TYhNHX372ek); [Tubefilter](https://www.tubefilter.com/2024/09/23/top-5-youtube-branded-videos-faze-rug-i-did-a-thing-kurzgesagt/) | 2026-05-19; 2024-09-23 | n/a |

**Example video: [*Why Are There No Holes Around Trees?*](https://www.youtube.com/watch?v=pHJIhxZEoxg)** (2026-01-07, 11:21). Timestamps are (captions).

| Time | Beat | Device |
|---|---|---|
| 0:00–0:10 | The heaviest living thing weighs about 2,000 t, "as much as ten blue whales" | Superlative plus a familiar unit of comparison |
| 0:10–0:15 | It reaches 25 storeys into the sky on shallow roots | The paradox |
| 0:19–0:28 | "You'd think trees grow from the ground… it would have to leave holes" | **The naive model stated** (the same misconception move as Veritasium) |
| 0:30 | "trees are growing by literally eating thin air!" | **The title question is answered at 4%** |
| 0:35–0:42 | "But this is only half of the story" → roots mine rock → "How does this work?" | A new loop opens straight away |
| 0:44 | Title card | The hook ends at 0:44 |
| 1:51–2:25 | The crown as "industrial megalopolises", then "Let's zoom into a single leaf" | Extended **visual metaphor** plus a zoom down the scale |
| 5:11 | "But this is only half of the story" (again) | Mid-video loop reset |
| 7:42 | "…but it gets even wilder" | Escalation line |
| 9:27–9:46 | A wonder line ("Trees are just so incredibly wild") | Emotional close |
| 9:57–11:00 | Sponsor read (Brilliant) | **After** the content ends |

**What is unique:** a published production budget (K1, K4); one narrator voice; an answer-early, chain-loops structure (K9); and public correction rituals: deleting videos, re-uploading them, posting change logs (K11, Negative).

**Negative and contested (Kurzgesagt)**
- **They deleted the formula that worked best.** In 2019 they removed *Addiction* and *The European Refugee Crisis and Syria*, "two of our most successful videos to date". Their account: they had "found a formula that really worked" and never used it again, because the videos simplified an idea "so much that it made a great story but became distorting". The refugee script was written on one Sunday afternoon and animated within a week ([JtUAAXe_0VI](https://www.youtube.com/watch?v=JtUAAXe_0VI) 2:32–4:37, captions). **This is the clearest case in this set of a creator dropping a high-performing playbook on purpose.**
- **Simplification complaints persist:** Art Libraries Society 2016; the exercise video 2024; Ozempic 2026 (K11; [Wikipedia: Kurzgesagt](https://en.wikipedia.org/wiki/Kurzgesagt)).
- **Funding independence questioned:** Gates Foundation (2015, $570k), Open Philanthropy (2022, €2.97M). Their January 2023 statement says about 65% of income comes from viewers and that funders have no editorial influence (Wikipedia, citing the studio's Reddit statement).

### 2.4 Fireship (fast tech explainers; Jeff Delaney, now a small team)

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| F1 | Mission: fast, approachable developer content "that doesn't waste your time", explaining complex ideas quickly "without taking ourselves too seriously". Run by "a tiny, remote team". [verified] | PRACTITIONER | [fireship.dev/about](https://fireship.dev/about/) | live 2026-10-12 | n/a |
| F2 | Positioning: "High-intensity" code tutorials and tech news. The channel is home to three named series: #100SecondsOfCode, #TheCodeReport, #CodeThisNotThat. [verified] | PRACTITIONER | Channel description, [@Fireship](https://www.youtube.com/@Fireship) (Data API) | live 2026-10-12 | n/a |
| F3 | **2026 operating rules:** Jeff still works on and voices every video and keeps creative control. No AI for voiceovers, visuals or other content. Ads go at the end, never in the first 60 seconds. Only products the team uses get promoted. He sold a stake to Electrify about 18 months before the ui.dev merger. [verified] | PRACTITIONER | ["ui.dev + Fireship join forces"](https://fireship.dev/uidotdev-and-fireship-join-forces) | 2026-01-14 | n/a |
| F4 | **The "100 Seconds" format was largely dropped.** Share of uploads titled "…in 100 Seconds": 28/67 (2022) → 15/87 (2023) → 14/92 (2024) → **1/82 (2025)** → 3/72 (2026). In 2024 those videos had a median of 620k views against 971k for the whole channel that year (same-year comparison). Despite the name, they run a median 153–188 s. [verified: re-counted 2026-10-12; all shares and the 620k vs 971k comparison match; median length 153–188 s for 2022–2024, the single 2025 video is 143 s] | DATA (descriptive, own count) | [@Fireship/videos](https://www.youtube.com/@Fireship/videos) via Data API | 2026-10-12 | n/a |
| F5 | **Length grew slowly:** median 3.2 min (2022) → 4.4 (2024) → 5.4 min (2026). [verified] | DATA (descriptive) | Same listing | 2026-10-12 | n/a |
| F6 | **Title signature (2024+, n=246):** 122/246 titles (50%) end with an ellipsis. 21/246 are questions. 0 use "!". News-reaction framing ("…just…", "…is furious"). [verified] | DATA (descriptive) | Same listing | 2026-10-12 | e.g. "Tragic mistake... Anthropic leaks Claude's source code" |
| F7 | **The 100 Seconds template:** first words are the name plus a superlative → origin → what makes it different → ecosystem → "to get started" → code demo with a joke → a fixed sign-off. No greeting, no channel intro. In 2023 the sponsor's product was written into the tutorial itself. [verified] | PRACTITIONER (observed) | [*PostgreSQL in 100 Seconds*](https://www.youtube.com/watch?v=n2Fluyr3lbc) | 2023-07-27 | 0:00 "the most trusted name in Open Source relational databases"; 0:05 origin 1986; 0:17 object-relational difference; 1:05 "to get started"; 1:07 Neon (the sponsor) as the setup step; 2:19 the "Lambos" joke; 2:25 "this has been postgresql in 100 seconds"; ends 2:35 (captions) |
| F8 | **The Code Report template:** a news-hook first sentence → a joke about every 6–10 s → "in today's video" promise at about 0:56 → a date stamp and "you're watching the code report" → an abrupt sign-off. [verified] | PRACTITIONER (observed) | [*Big Tech in panic mode… DeepSeek R1*](https://www.youtube.com/watch?v=Nl7aCUsWykg) | 2025-01-27 | 0:00 news hook; 0:16 "vibe test"; 0:22 a political-censorship joke; 0:56 "in today's video we'll find out…"; 3:33 "this has been the code report" (captions) |
| F9 | **2026 form:** the first line uses irony ("the most ironic thing ever happened"). A self-deprecating aside ("slop tubers like Fireship") comes at 1:04. A curiosity promise ("…Anthropic doesn't want you to know about") comes at 1:13. No sponsor read; no fixed sign-off. [verified] | PRACTITIONER (observed) | [*Tragic mistake… Anthropic leaks Claude's source code*](https://www.youtube.com/watch?v=mBHRPeg8zPU) | 2026-04-01 | 0:02; 1:04; 1:13 (captions) |
| F10 | In 2023 Jeff built an AI pipeline that wrote, narrated and edited videos "in my own style", as a demo. By 2026 the stated policy was no AI content (F3). [verified] | PRACTITIONER | Description of [*I built my own AutoGPT that makes videos*](https://www.youtube.com/watch?v=_rGXIXyNqpk) | 2023-04-11 | n/a |

**Example video:** see F7 for the beats of *PostgreSQL in 100 Seconds* (2:35 total; about 15 s of origin and definition before the first "why it matters"). **What is unique:** humour density as the retention device; voice-over on screen recordings and memes (faceless); fixed series names as packaging; and an explicit "doesn't waste your time" contract.

**Negative and contested (Fireship)**
- **Its signature format was dropped** (F4). The creator did not explain why. The same-year view gap is the only signal: by 2024, "100 Seconds" videos under-performed the channel median.
- **Sponsor placement reversed.** In 2023 the sponsor was woven into the tutorial at 1:07 (F7). The 2026 rule says ads go at the end, never in the first 60 s (F3).
- **Ownership.** Electrify (the same investor as Veritasium) bought a stake in about mid-2024. Jeff says he kept creative control (F3). That claim cannot be checked from outside.
- No tier 1–3 critique of Fireship's accuracy or humour was found (see Gaps).

### 2.5 MKBHD (tech review; Marques Brownlee and studio)

| # | Claim | Tag | Source | Date | Example / timestamp |
|---|---|---|---|---|---|
| M1 | **Writing is the biggest job.** Writing takes about a full day, while the rest of post-production takes about one day. In 2021 he wanted to hire a writer, for evergreen explainers to sit between short-lived reviews. [verified] | PRACTITIONER | Colin and Samir, [*The Full Story of MKBHD*](https://www.youtube.com/watch?v=pWH1TF1ZfKA) | 2021-03-08 (older) | 13:29–13:51; 14:39 (captions) |
| M2 | **The review pipeline.** Test the device → notes in a shared Google Doc that becomes the script → the crew reads the doc as a live shot list and shoots B-roll in parallel → talking head → he edits it himself. He keeps the edit because the small fixes he finds there make it an MKBHD video. Elaborate intro shots (the first 5 s) go to the motion designers. [verified in part: the Google Doc that becomes the script and shot list (15:24–15:44) and the motion designer for intros (21:27) were confirmed; "edits it himself" was not re-checked] | PRACTITIONER | Same interview | 2021-03-08 | 15:26–16:30; 17:09; 18:10 (captions) |
| M3 | **Accuracy loop (2024).** A Notion template sets pre- and post-production vetting. A writer-researcher tests the device alongside him and challenges the script. The final cut goes to everyone who tested, to check for factual errors, because he does not read the script word for word. He used the Humane pin for over a week. [verified] | PRACTITIONER | Colin and Samir, [*We asked MKBHD about his 'devastating' reviews*](https://www.youtube.com/watch?v=UwDwizVsUG8) | 2024-04-16 | 11:00–11:44; 15:23 (captions) |
| M4 | **Ethics.** A friendly PR person "never changes the video". A negative review feels "more of a PSA". Bad products, not bad reviews, kill companies ("90 something percent true"); reviews only accelerate what was coming. Trust is "the ultimate" leverage he has, so his Ridge role is limited to categories he does not review. [verified; the Ridge and trust lines come from the C&S interview, not TIME] | PRACTITIONER | Same; [TIME100 AI](https://time.com/7012892/marques-brownlee/) | 2024-04-16; 2024-09-05 | 3:02; 8:27; 9:09–10:10; 13:00–13:45 (captions) |
| M5 | **Title and thumbnail are hard.** The Humane review was "one of the hardest reviews to title", because many viewers did not know the product. The video went out with the verdict as its title. [verified] | PRACTITIONER | Same C&S | 2024-04-16 | 14:18–15:00 (captions) |
| M6 | He uses AI to help edit thumbnails and brainstorm video ideas. [verified] | PRACTITIONER | TIME100 AI | 2024-09-05 | n/a |
| M7 | **Sustainability principles.** "A dream job is still a job". Creative jobs do not scale like regular jobs: scaling up takes time away from the creative work. Don't chase algorithm changes ("a carrot on a string"). Copying MrBeast's blueprint comes with costs people don't see. Find your own "speed on the treadmill". He cannot review every phone, so he picks one. **Octopus analogy:** hand off the arms you're bad at (e.g. thumbnails to a designer, taxes) but keep the "three hearts", the core craft you love. [verified] | PRACTITIONER | [*On "Quitting" YouTube*](https://www.youtube.com/watch?v=GQAvce3MA44) | 2024-01-19 | 1:32; 3:59; 9:11; 9:29; 9:56; 11:26; 13:21; 13:59–14:46 (captions) |
| M8 | **Lessons from A/B testing (2025–26).** He has run thumbnail tests for about a year. Small differences (text size, arrow vs no arrow) are usually not statistically meaningful; whole different concepts teach him something. He has tried title tests once or twice. [verified] | PRACTITIONER (creator's own tests; no numbers shown) | [*Dear YouTube!*](https://www.youtube.com/watch?v=e1q-TuHdc4Y) | 2026-09-30 | 3:00–3:50 (captions) |
| M9 | **Against video A/B testing.** YouTube announced it at Made on YouTube 2026, rolling out "early next year". YouTube engineers told him a semantic-similarity model will gate tests, and tests are allowed only at launch. His view: best retention does not necessarily mean a better video; most creators shouldn't use it; finishing and publishing more videos beats optimizing cuts; "stand by your creative choices". [verified] | PRACTITIONER (contains a tier-1 product fact relayed second-hand) | Same video | 2026-09-30 | 0:43 announcement; 5:24–6:09 gating; 9:22–10:30 retention vs quality; 11:14–11:36 (captions) |
| M10 | **Length is stable:** median 12.8 min (2021) → 11.6 (2022) → 11.3 (2023) → 12.8 (2024) → 11.9 (2025) → 11.4 min (2026). He did **not** follow the long-form length creep of the explainer schools. [verified: re-counted 2026-10-12] | DATA (descriptive, own count) | [@mkbhd/videos](https://www.youtube.com/@mkbhd/videos) via Data API | 2026-10-12 | n/a |
| M11 | **Title signature (2024+, n=174):** 94/174 contain "!", 87/174 use "Product: verdict-phrase", 68/174 say "Review" or "Impressions", 27/174 are questions. [verified: re-counted 2026-10-12] | DATA (descriptive) | Same listing | 2026-10-12 | "Galaxy Z Fold 8 Review: Honeymoon's Over" |
| M12 | **Hook = verdict plus thesis in the first 45 s**, then a roadmap. [verified for the Humane video] | PRACTITIONER (observed, 2 videos) | [*The Worst Product I've Ever Reviewed… For Now*](https://www.youtube.com/watch?v=TitZV6k8zfA); [*iPhone 18 Pro Review: All About that Chip*](https://www.youtube.com/watch?v=ohqxP8EEumo) | 2024-04-14; 2026-09-16 | Humane: 0:26 "the new worst product I think I've ever reviewed"; 0:43–0:54 roadmap (captions). iPhone: 0:23–0:32 "an S update" → 0:39 "underrated" → 0:41 "queue all the shill comments", pre-empting objections (captions) |
| M13 | Studio team (2021): producer, DP/art director, creative director, motion designer, second producer, graphic designer, writer/researcher, podcast producer. [verified] | PRACTITIONER | [Tubefilter](https://www.tubefilter.com/2021/07/27/marques-brownlee-second-channel-the-studio/) | 2021-07-27 | n/a |

**Example video: [*The Worst Product I've Ever Reviewed… For Now*](https://www.youtube.com/watch?v=TitZV6k8zfA)** (2024-04-14, 25:04). Chapters (chapters) plus caption lines (captions).

| Time | Beat | Device |
|---|---|---|
| 0:00–0:26 | "This is the Humane AI pin… ultra futuristic wearable computer… so sick that we get… genuinely new" | Fair framing first: credit before the verdict |
| 0:26–0:30 | "…the new worst product I think I've ever reviewed" | **Verdict = title, delivered within 30 s** |
| 0:43–0:54 | First what it is supposed to do, then his actual experience | Roadmap |
| 1:26–1:40 | $700 plus $24/month | Price on the table early |
| 2:30 / 4:26 / 8:14 | Chapters: The Hardware / What Does It Do? / The Review (It's Bad) | Chaptered review spine (chapters) |
| 15:00 | Chapter "Smartphones are OP" | Zoom out from the product to a thesis about the category |
| 21:11–21:17 | "a victim of its future ambition" | A named take-away line |
| 23:29 | "a glimmer of hope for that future" | Balance |
| 24:15–24:23 | "skip this product… never buy a product based on the future promise of updates" | **An actionable rule as the ending** |
| 24:33–24:57 | Respect for the attempt, then the sign-off | Ends quickly |

**What is unique:** a review is a verdict plus a personal rule, delivered in a stable ~12-minute format; trust is treated as the asset (M4); and the creator questions optimisation tooling in public (M9).

**Negative and contested (MKBHD)**
- **Panels (2024).** He admits "a lot of mistakes", including not explaining the app and its $50 tier, and says "we failed on the price front" ([*Let's Talk About Panels*](https://www.youtube.com/watch?v=65ciAONXv0M) 0:06–0:31, 4:08, captions). The app shut down at the end of 2025 ([Wikipedia](https://en.wikipedia.org/wiki/Marques_Brownlee), citing The Verge 2025-12-01). A trust failure off-channel, but it hit the brand.
- **Speeding in a sponsored DJI video (Nov 2024).** Footage at 96 mph in a 35 zone was cut and he apologised (Wikipedia, citing The Verge 2024-11-12).
- **Was the Humane review too harsh?** Contested. Critics said yes (TIME 2024). His position is M4, and the claim that one review moves markets is disputed in the C&S episode (Fisker's share price was already falling).

---

## 4. Solo transfer: can one person with no team and no budget do it?

| Principle (creator) | Solo? | Substitute when partly or no | Basis |
|---|---|---|---|
| Promise in title/thumbnail paid off in the video (JH2, V4–V5) | **Yes** | Draft title and thumbnail first. Have the script agent check that the promise is paid off, and where | JH2, JH5, V4 |
| Draw thumbnails before research ("story days", JH5) | **Yes** | Sketch 3 thumbnail concepts on paper before scripting; drop the idea if none excites | JH5 |
| "I can see it" visual greenlight test (JH4) | **Yes** | The agent asks for one concrete opening image or visual metaphor before a script is approved | JH4, K3 (sketching) |
| One-sentence pitch; "defend the story" (JH6–JH7) | **Yes** | A one-line pitch plus a written answer to "why would a stranger give this 1 minute / 30 minutes?" | JH6–JH7 |
| "Fresh brain" editor (JH8) | **Partly** | No second person: let a day pass, or have the AI read it cold and name the most interesting part; compare with your own pick | JH8 |
| Maps and data visualization (JH12) | **Partly** | The free path: Illustrator base map plus After Effects, or Mapbox Studio's free non-commercial styles. For phone-shot travel walks, a simple route map overlay (Remotion/Resolve) | JH12 |
| Commissioned score (JH13; K1 original music) | **No** | Licensed library music; for Reels, platform sounds | JH13, K1 |
| Misconception-first opening (V1–V3) | **Yes** | One line: "You'd think X…", then the reveal. Zero cost | V1–V3, K9 |
| Audience polls on titles (V6) | **Partly** | Without a large Twitter/Patreon following: YouTube Test & Compare on thumbnails, and only for big concept differences (M8) | V6, M8 |
| Retitling old videos (V7) | **Yes** | Revisit under-performers with a clearer, more concrete title. Before/after only, so it is confounded (see research 12) | V7 |
| Multi-month research plus an expert cameo (V9–V10, K1–K4) | **No** | Narrow the topic until a week of reading covers it. Email 1 expert for a read-through. Publish a sources list | K2–K4, V9 |
| Cold-open stakes, then explicit questions (V13) | **Yes** | Script rule: 2 open questions stated in the first 60 s; for a 45–60 s Reel, 1 question in the first 3 s | V13, Skyscraper table |
| Sponsor read as a mid-story cliffhanger (V14) | **Partly** | Solo creators seldom have sponsors. The same device works for any break (a CTA, or a chapter end): break on an open question and come back with a hook line | V14 |
| 1,200-hour animation (K1) | **No** | Voice-over on your own footage, plus a few simple animated diagrams; reuse one visual metaphor across a video | K1, K3 |
| Answer at 4%, then chain loops ("only half of the story", K9) | **Yes** | Script template: answer → "but that's only half" → the next question, repeated every 2–4 min (long form) or every 10–15 s (Reels) | K9 |
| Public corrections, re-upload, change log (K11, Kurzgesagt deletions) | **Yes** | Pinned correction comment, or re-upload with a change note; costs time, not money | K11, Negative 2.3 |
| Human-made pledge, AI only as a utility (K7, F3) | **Yes** | Use the agent for checking, structure and logistics; keep voice and judgement human. For this project the pledge is partly at odds with an AI script agent; disclose how it is used | K7, F3 |
| Humour density, a joke every ~6–10 s (F8) | **Partly** | Depends on the creator's voice; the agent can propose jokes but not judge them | F8 |
| Fixed series names and a format template (F2, F7) | **Yes** | A named series with a fixed open and close. But retire it when same-year data says it lags (F4) | F2, F4, F7 |
| Ads only after 60 s or at the end (F3) | **Yes** | Put any CTA or affiliate mention after the payoff | F3 |
| Shared doc = script + shot list (M2) | **Yes** | One file holds the script and the shot list, so B-roll is planned while writing (fits `script.json`) | M2 |
| Verdict in the first 30 s (M12) | **Yes** | For opinion and review formats, say the verdict in the hook and spend the rest on the reasons | M12 |
| Post-production factual check by co-testers (M3) | **Partly** | A checklist pass on the final cut, plus the AI checking claims against the sources list | M3 |
| Octopus: hand off weak arms, keep the "hearts" (M7) | **Partly** | No money to hire: hand the weak arms to tools (templates, AI checks) and decide which craft stays manual | M7 |
| Treadmill speed: pick a sustainable cadence (M7, JH16) | **Yes** | Choose a cadence you can hold; cutting output (Harris, to ~2–2.5/month) raised quality per his team | M7, JH16 |
| Don't A/B-test video cuts; test only big packaging differences (M8–M9) | **Yes** | Cheapest of all: publish more and learn per video | M8–M9 |

---

## 5. Negative findings: copies that failed, and principles the creators abandoned or contradicted

### 5.1 Principles the creators themselves dropped or reversed

| # | What changed | Creator's own words / evidence | Tag | Source | Date |
|---|---|---|---|---|---|
| N1 | Kurzgesagt deleted two of its best-performing videos and never reused the formula, because it distorted the facts [verified] | "found a formula that really worked", then removed it; "made a great story but became distorting" | PRACTITIONER | [JtUAAXe_0VI](https://www.youtube.com/watch?v=JtUAAXe_0VI) 3:58–4:37 (captions) | 2019-03-03 |
| N2 | Fireship stopped making its signature "100 Seconds" videos [verified: 28/67 = 42%, 1/82 = 1%] | Share fell from 42% of uploads (2022) to 1% (2025); same-year median views were below the channel's in 2024 | DATA (descriptive) | F4 | 2026-10-12 |
| N3 | Fireship moved sponsors out of the content | 2023: the sponsor is the tutorial's setup step (1:07). 2026: "ads at the end, never in the first 60 s" | PRACTITIONER | F7, F3 | 2023 → 2026 |
| N4 | Fireship went from an AI video-generation experiment to a no-AI pledge | 2023 AutoGPT video demo → 2026 "No AI is used" | PRACTITIONER | F10, F3 | 2023 → 2026 |
| N5 | Veritasium: from "CTR is the key metric" to "legitbait" | 2019 description → 2021 video | PRACTITIONER | V8, V5 | 2019 → 2021 |
| N6 | Veritasium admits overhyping in its own past [verified] | "guilty of overhyping" BICEP2 | PRACTITIONER | czjisEGe5Cw 3:29 | 2023-10-31 |
| N7 | Veritasium went from a one-man channel to a team with other hosts, investor-owned | Muller is one of several hosts; 30+ staff | PRACTITIONER | V9 | 2023–2026 |
| N8 | Harris: gut-only greenlighting and ~4 videos/month replaced by the visual filter, one-sentence pitches and 2–2.5/month | Iz: stories he "hated" were pushed through | PRACTITIONER | JH4, JH7, JH16 | 2025-03-04 |
| N9 | Harris: no sources cited until Sept 2022; a sponsored WEF video with late disclosure; a Russia video removed after criticism [verified] | McGill 2024; Kyiv Independent 2024 | PRACTITIONER (critics) | 2.1 Negative | 2024 |
| N10 | Kurzgesagt tried AI for research and found it "confidently incorrect": invented facts, and a cited source likely AI-written (a detector gave it a 72% match) [verified] | The AI pledge followed | PRACTITIONER | AI Slop 2:23–2:39; [sources page](https://sites.google.com/view/sources-aislop) | 2025-10-07 |
| N11 | Kurzgesagt republished videos when framing, not facts, was the problem | The Ozempic description; the exercise video | PRACTITIONER | K11 | 2024, 2026 |
| N12 | MKBHD contradicts a retention-max reading of craft, contrary to the MrBeast school | "best retention" ≠ "better video"; don't copy the MrBeast blueprint | PRACTITIONER | M7, M9 | 2024, 2026 |

### 5.2 Copies that failed or went wrong (named examples)

| # | Copy | What happened | Tag | Source |
|---|---|---|---|---|
| C1 | An unnamed "relatively new channel" that copied Kurzgesagt's **"structure and rhythm"** on brown dwarfs [verified] | It got hundreds of thousands of views but repeated the AI-invented facts Kurzgesagt had flagged. Kurzgesagt uses it as its example of AI-assisted imitation spreading misinformation into the next AI's sources | PRACTITIONER (the channel is not named, so it cannot be verified) | [*AI Slop Is Destroying The Internet*](https://www.youtube.com/watch?v=_zfN9wnPvU0) 5:06–5:44 (captions) |
| C2 | MKBHD's warning about MrBeast-blueprint copiers | He says they may succeed but carry hidden costs (burnout, the "treadmill"). No named failure is given | PRACTITIONER | [GQAvce3MA44](https://www.youtube.com/watch?v=GQAvce3MA44) 9:11–9:56 (captions) |
| C3 | Kurzgesagt copying its *own* 2015 activist formula | The fast, angry refugee video (one Sunday, one week) and the one-source *Addiction* video did very well but were deleted | PRACTITIONER | N1 |

No tier 1–3 source names a failed channel that copied Johnny Harris, Veritasium, Fireship or MKBHD. See Gaps.

---

## Cross-creator signals for item 3 (to merge with the other researchers)
- **Agree:** all five put packaging first or treat it as half the job (JH5, JH10, V4, M5, F6), state the payoff early or promise it outright (JH3, V13, K9, M12, F8), and invest in accuracy loops as they grow (JH9, V9, K2/K4, M3).
- **Contradict:**
  - Length: Harris and Veritasium roughly doubled to 30–40 min in 2024–26, MKBHD stayed flat at ~12 min, and Fireship stays under 6 min (JH14, V11, M10, F5).
  - Where the answer comes: Kurzgesagt answers at 4%; Veritasium and Harris answer late, at 79–96% (research 09).
  - Sponsor position: Harris early (~11%); Veritasium mid-story as a cliffhanger; Kurzgesagt and Fireship at the end. Kurzgesagt also runs a shop plug at 0:00.
  - Face: Harris and MKBHD are on camera; Fireship and Kurzgesagt are voice only; Veritasium is moving to multiple hosts.
  - Optimisation: Veritasium tests packaging; MKBHD rejects testing video cuts (V6 vs M9).
- **Self-report only:** nearly all "why" claims (JH1–JH11, V4–V7, K1–K7, M1–M9, F1–F3). The only DATA here is my descriptive channel counts and single-video heatmaps; no creator in this set has shown a retention graph with a sample.

---

## Gaps
1. **Web search unavailable.** The shared search budget was used up before this agent's first query, so the "15+ queries" requirement could not be met. Sources were opened directly instead; some known pages returned 403 (Nieman Lab 2026 Newpress profile; Kurzgesagt's Medium research article; Fast Company; Big Think), and The Verge is blocked for the fetch tool. Items that depend on them are cited second-hand through Wikipedia's reference list.
2. **No creator retention graphs.** None of the five has published a retention curve with a sample in 2024–26 that I could find. Veritasium's 2021 view graphs are before/after views, not retention. All structure claims are observation or self-report.
3. **Fireship has no first-person "how I make videos" interview** from a tier 1–3 source, and no external critique was found. F1–F3 rest on fireship.dev pages. The reason for dropping "100 Seconds" is not stated anywhere I found; F4 is a count, not a cause.
4. **Johnny Harris *How I Write* (2025):** only the chapter list and summary were readable (sign-in wall); JH1–JH3 rest on chapter titles. The Colin and Samir interview (captions) covers the process in depth instead.
5. **Muller 2007 paper:** abstract paywalled. The effect-size figure (~0.8 SD) used in research 09 came from Big Think, which returned 403 here. Not re-verified.
6. **Named cargo-cult failures** for Harris, Veritasium, Fireship and MKBHD styles: none found in tier 1–3 sources. C1 is real but anonymous.
7. **Heatmaps are not retention.** Peaks right after a sponsor read (Harris 5:20–5:40, Veritasium Maps 9:34) look like skip landings and should not be read as "best content".
8. **Single-video examples:** each beat table is one video. Patterns marked "observed" come from 1–3 videos per creator, not a sample.
9. **Sources in conflict:** Harris's stated sponsor wall (2025) vs the WEF co-written video (pre-2024). Kurzgesagt's "no editorial influence" vs critics of its foundation funding. Fireship's "creative control" vs Electrify ownership (unverifiable). The Veritasium title shown differently by two YouTube endpoints (possible live test; unconfirmed).
10. **Older-than-2024 items, flagged as possibly outdated:** Veritasium 2011–2021 (V1, V2, V4–V8), Kurzgesagt 2019–2020 (K1–K2; partly restated in 2025 by K4), Johnny Harris maps 2020 (JH12), MKBHD 2021 (M1–M2, M13), Fireship 2023 (F7, F10).

---

## Refuted or unconfirmed

Fact-check pass on 2026-10-12. Channel counts were re-pulled with `yt-dlp --flat-playlist` (227 / 400 / 253 / 400 / 400 uploads, identical to the method note) and Data API `videos.list`. Caption claims were re-checked against freshly pulled auto-captions; web sources were opened directly. No whole claim was refuted. The parent rows below stay in place, corrected and marked "verified after correction". These parts did not hold:

| Was in | Refuted or unconfirmed part | Reason |
|---|---|---|
| JH15 | "9/74 contain an all-caps word ("REAL", "DAMN")" | The 2024+ titles have 10/74 with an all-caps emphasis word (REAL ×3, BILLIONAIRE, SO, ACTUALLY, WAR, TRILLION, WILD, HEIST), not counting acronyms. "DAMN" occurs only in 2021 and 2023 titles ("Why is Russia So DAMN BIG?", "Why are politicians so DAMN RICH?!"), outside the 2024+ window. |
| K7 | The quote "will always remain human-made" | The words are not in the captions. The line at 8:48–8:53 is "made by humans for humans and it will remain that way". The meaning holds; the quote does not. |
| V12 | "…is unreasonably fast" as a recurring title template | Only one 2024+ title uses it ("Google Maps is unreasonably fast. Let me explain", 2026). The other is "Clickbait is Unreasonably Effective" from 2021, outside the window. "…And No One Knew" does recur (2/79). |
| K10 | "A 7-second shop-pin plug… (0:00–0:09)" | The captions put the plug at 0:00–0:06 and the hook line "You will never leave the solar system" at 0:06. |
| Harris example beat table (*China's Dirty Money Problem*) | Heatmap values (1.0 at 5:20–5:40; 0.82 at 13:00) and decile means | Not re-checked. YouTube returned HTTP 429 when the info JSON was re-pulled. Length (33:18) and date (2026-04-16) confirmed through the Data API. |
| JH7 (second sentence), JH9, JH11, JH12, K6, M2 ("he edits it himself", see the row's note) and the V13 Internet example | Not opened in this pass | Left without a marker; treat as unverified. |
