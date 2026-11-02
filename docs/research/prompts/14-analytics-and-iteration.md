# 14 · Analytics and iteration: reading retention, programmatic access

Скопировать всё, что между линиями, в ChatGPT Deep Research или Claude Research. Ответ положить в `docs/research/14-analytics-and-iteration/result-a.md`. Контекстный блок: `_context-content.md`.

---

CONTEXT (same for every research task in this series, 07–14)

I am a solo creator making videos for YouTube (long-form and Shorts), TikTok and
Instagram Reels, in whatever format fits the idea: talking head, voice-over on footage,
screencast, POV walks with music only, vlog, challenge. I am building an AI agent
(Claude Code: markdown "skills" plus Python) that writes video scripts, proposes hooks,
titles and structure, and critiques a draft script before I shoot or edit. This research
series collects the evidence-based rules that agent will follow. Platform priority:
YouTube first, TikTok second, Instagram third.

Research rules:
- Source hierarchy, best to worst: (1) statements, docs and published research from
  YouTube / Google, TikTok and Meta; (2) creators showing their own data (retention
  graphs, A/B thumbnail tests, analytics screenshots, internal documents);
  (3) analysts working from samples (Paddy Galloway, Colin and Samir, VidIQ, 1of10,
  Film Booth, Jon Youshaei and similar); (4) peer-reviewed research on attention,
  curiosity, suspense, emotion and narrative. Exclude marketing blogs, SEO listicles
  and paid-course content unless they quote a tier 1–4 source; then cite that source.
- Tag every rule or claim with its evidence level: DATA (a measurement over a sample,
  an A/B test or a retention graph is shown; one video's view count is not DATA),
  PRACTITIONER (a creator's or analyst's stated practice, no data shown) or THEORY
  (research or a model, not tested on video). Keep the three apart.
- Time horizon: for platforms, algorithms and creator case studies prefer 2024–2026
  and flag anything older as possibly outdated. For psychology, emotion and
  storytelling theory there is no date limit; classic sources are welcome.
- Examples must be concrete: a named video with a link and a timestamp (or a named
  creator and a named video), never "many creators do X". A timestamp taken from a
  transcript, a chapter list or a published breakdown is fine; say where it came from.
- Be explicit about what does NOT work, what is contested, and what is a myth that
  the sources themselves have retracted. Negative findings are valuable.
- Do not pad. Tables over prose. Cite a link for every claim.

RESEARCH TASK 14: reading analytics to iterate, and fetching retention data programmatically

Goal: two things. First, a diagnosis playbook: which metric says what, what is noise,
and which experiment to run next. Second, the facts about programmatic access to
retention and performance data on each platform, so the agent can later pull my own
videos' numbers and check them against the rules from tasks 07–13.

Find and document:

1. YouTube Studio metrics: absolute and relative retention, the "intro" segment (first
   30 s), key moments (spikes, dips, top moments), average view duration, average
   percentage viewed, impressions, impressions click-through rate, returning versus
   new viewers, subscribers per video, the satisfaction survey. For each: what it
   measures, what it does not, typical ranges, and the source.
2. Diagnosis playbook: symptom → likely cause → next experiment. Low CTR versus low
   retention versus low impressions; a cliff at 30 s versus a steady slope; spikes
   that mean rewatches versus spikes that mean the link was shared to a timestamp.
3. Short-form analytics: Shorts "viewed versus swiped away" and retention; TikTok
   analytics (average watch time, watched full video percentage, traffic sources,
   retention graph); Instagram Reels insights (watch time, replays, sends, reach
   sources). What each exposes and what it hides.
4. Programmatic access, with exact facts: YouTube Analytics API (the audienceRetention
   report: dimensions, metrics, elapsedVideoTimeRatio granularity, filters, the
   minimum views before data appears, OAuth scopes, quota); YouTube Data API for
   statistics; whether key moments or Shorts swipe-away data are available via API;
   TikTok's APIs (Display API, Research API, Content Posting API: what performance
   data each returns, who can get access, approval process); Instagram Graph API
   insights for Reels (metrics available, account requirements, limits); third-party
   tools with APIs (VidIQ, TubeBuddy, Metricool and similar) and what they add. For
   every API: link, auth, quota, data granularity, last documentation update.
5. Experiment design: the A/B tests the platforms offer (YouTube Test & Compare for
   thumbnails and titles: what it measures, duration, minimum traffic), how to compare
   across videos with small samples, how long to wait after publishing before judging,
   what confidence is realistic for a channel with a few thousand views per video.
6. The learning loop: how creators log hypotheses and results per video (templates,
   fields, review cadence), with examples from creators who show their process.
7. Negative findings: vanity metrics, common misreadings of the retention graph, and
   what cannot be measured at all (per platform).

Output format:
- Table A: metric × platform × what it means × typical range × source.
- Section B: diagnosis table: symptom → cause → next experiment.
- Table C: API access per platform: endpoint, retention data available, granularity,
  auth, quota, access requirements, link.
- Section D: experiment protocol for a small channel.
- Section E: what cannot be measured and the misreadings to avoid.

---
