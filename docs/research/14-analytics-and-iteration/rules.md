# 14 Analytics and iteration: rules

Distilled from `result-a.md` (A: verified, authoritative) and `chatgpt.md` (C: unlinked, partly wrong). Tags: DATA, PRACTITIONER, THEORY, DOC (platform spec); [T1]-[T4] tier; Old = pre-2024; INFERENCE = researcher-derived.

## Metrics

| Metric | Platform | Measures | Does not | Range | Source |
|---|---|---|---|---|---|
| Absolute retention | YouTube | Share watching at each point; can exceed 100% | Why they left | not published | [Help](https://support.google.com/youtube/answer/1715160?hl=en) |
| Relative retention | YouTube | Hold vs similar videos, 0-1 | Your channel norm | 0.5 = median | [API](https://developers.google.com/youtube/analytics/metrics) |
| Typical retention band | YouTube | Your last 10 similar videos | Cross-channel benchmark | own band | [Help](https://support.google.com/youtube/answer/12942217?hl=en) |
| Intro (30 s) | YouTube | % still watching at 0:30 | Mismatch vs slow opening | >=50% "above typical", no data | [Help](https://support.google.com/youtube/answer/1715160?hl=en) |
| Key moments | YouTube | Top moments, spikes, dips | Whether a spike is good | only >=60 s, >=100 views | [Help](https://support.google.com/youtube/answer/9314415?hl=en) |
| Average view duration | YouTube | Time per engaged view | Curve shape | not published; Galloway clients 4:35 to 8:00 (DATA [T3]) | [Help](https://support.google.com/youtube/answer/9313698?hl=en) |
| Average percentage viewed | YouTube | Share watched | Cross-length comparison | not published | [Film Booth](https://www.youtube.com/watch?v=YwbPVcGQT5s&t=77) |
| Views | YouTube | Play starts since 2026-08-24 | Intent | ~54% engaged (vidIQ) | [Help](https://support.google.com/youtube/answer/2991785?hl=en) |
| Engaged views | YouTube | Old view rule; earnings, YPP | Published cutoff | hover ~10 s (vidIQ, one channel) | [Blog](https://blog.youtube/inside-youtube/engaged-views-youtube-explained/) |
| Impressions | YouTube | Thumbnail >1 s, >=50% visible | External, end screens | not published | [Help](https://support.google.com/youtube/answer/9314486?hl=en) |
| Impressions CTR | YouTube | Views per impression | Satisfaction | half of channels 2-10% | [Help](https://support.google.com/youtube/answer/7628154?hl=en) |
| New/casual/regular | YouTube | History segments | Identity | regular <1% sometimes | [Help](https://support.google.com/youtube/answer/10246996?hl=en) |
| Monthly audience | YouTube | Unique viewers, 28 d | - | not published | same |
| Subscribers per video | YouTube | Watch-page subscriptions | Later ones | Old: 22.7 per 10k long-form, 16.9 Shorts (DATA [T3]) | [Help](https://support.google.com/youtube/answer/9717879?hl=en) |
| Satisfaction survey | YouTube | 1-5 stars in ranking | Shown to creators: never | not exposed | [Goodrow](https://blog.youtube/inside-youtube/on-youtubes-recommendation-system/) |
| x out of 10 | YouTube | Rank vs last 9-10 uploads | Final outcome | own rank | [Insider](https://www.youtube.com/watch?v=wrIlifWnKDs&t=249) |
| Stayed to watch | Shorts | % past "initial seconds" | CTR (none) | not published | [Help](https://support.google.com/youtube/answer/9314355?hl=en) |
| Views, engaged views | Shorts | Starts, replays; engaged excludes loops | Intent | not published | [Help](https://support.google.com/youtube/answer/12220281?hl=en) |
| Key moments, 45-59 s | Shorts | None shown (THEORY) | - | - | [Help](https://support.google.com/youtube/answer/9314415?hl=en) |
| Video views | TikTok | First play per session, >0 s | Organic vs paid | not published | [Docs](https://business-api.tiktok.com/portal/docs/get-post-data-of-a-tiktok-account/v1.3) |
| Average watch, play time, full-watch rate | TikTok | Seconds; share reaching end | - | not published | same |
| Audience retention | TikTok | % per second | - | not published | same |
| Traffic source, viewer types, likes by second | TikTok | For You, Follow, Search; new/returning | - | not published | same |
| Views, watch time | Instagram | Starts and replays; play time | - | not published | [Help](https://help.instagram.com/202865988324236) |
| Viewers, average watch time | Instagram | Accounts on screen; watch/initial views | - | not published | same |
| Skip rate | Instagram | Skips in first 3 s | In-app graph undocumented | not published | [Docs](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights) |
| Replays | Instagram | Not separate since 2025-04-21 | - | - | [Log](https://developers.facebook.com/docs/instagram-platform/changelog) |
| Interactions, reach sources | Instagram | Counts; account-level reach split | Per-reel sources; "sends" | not published | [Help](https://help.instagram.com/788388387972460) |

## Diagnosis

| Symptom | Likely cause | Next experiment | Tag |
|---|---|---|---|
| Low impressions, CTR/AVD normal | Topic demand or supply; too new | Higher-demand topic, same format | PRACTITIONER [T1] |
| Low impressions, new channel | No history; topic matching | Legible topic, packaging | PRACTITIONER [T1] |
| Low CTR | Reach mix; Subscriptions-feed CTR also low = idea/packaging | New thumbnail/title; Test & Compare | PRACTITIONER [T1] |
| High CTR, low AVD/Intro | Packaging over-promises (A, C agree) | Match packaging to first 30 s | PRACTITIONER [T1] |
| Cliff before 0:30 | Mismatch or slow opening; subscribers also leave = opening | Cut context or change packaging | INFERENCE; fix PRACTITIONER [T2/3] Old |
| Teaser, then minute-one cliff | Audience not addressed | Context and stakes first | PRACTITIONER [T2/3] Old, n=1 |
| Steady slope below band | Low tension | Restructure around stakes | PRACTITIONER [T2/3] Old |
| Gradual decline | Normal (A, C agree) | Keep format | PRACTITIONER [T1] |
| Sharp segment drops | Dense, dry visuals | B-roll or cut | PRACTITIONER [T2/3] Old |
| Spike then dip | Skip target | Shorten what precedes | PRACTITIONER [T1]+[T3] |
| Spike that holds | Rewatched content | Show longer, earlier | PRACTITIONER [T1] Old |
| Spike on unclear part | Replay to understand | Re-cut for clarity | PRACTITIONER [T1] |
| Spike at chapter/shared timestamp | Entry, not rewatch | Compare `startedWatching` with `totalSegmentImpressions` | INFERENCE |
| Strong hour one, then sinks | Core audience first | Re-check 7, 28 d | PRACTITIONER [T1] |
| Short underperforms | Higher swipe-away | Compare ~10 own Shorts; re-cut start | PRACTITIONER [T1] |

C's SEO-tag and sharing fixes: unsupported in A, dropped.

## API access

| API | Endpoint | Retention | Granularity | Auth, scopes | Quota | Access | Link, date |
|---|---|---|---|---|---|---|---|
| YT Analytics | `reports`, `elapsedVideoTimeRatio` | Yes: `audienceWatchRatio`, `relativeRetentionPerformance`, `startedWatching` | 100 points (60 s = 0.6 s); 48-72 h | OAuth `yt-analytics.readonly`, `youtube.readonly` | 1 unit; daily limit unpublished | Owner; min views unpublished | [Docs](https://developers.google.com/youtube/analytics/channel_reports), 2026-09-14 |
| YT Reporting | `channel_reach_basic_a1` | No; only impressions, CTR | Daily | same | unstated | 30-day backfill | [Docs](https://developers.google.com/youtube/reporting/v1/reports/channel_reports), 2026-09 |
| YT Data v3 | `videos.list` | No | Lifetime | key; OAuth | 10,000/day | Cloud project | [Docs](https://developers.google.com/youtube/v3/docs/videos), 2026-10-08 |
| TikTok Accounts | `business/video/list/` | Yes: `video_view_retention`, `full_video_watched_rate` | Per second; T+24-48 h | `video.insights` | 40 QPM | Access form since 2026-03-20; personal account untested | [Docs](https://business-api.tiktok.com/portal/docs/get-post-data-of-a-tiktok-account/v1.3), no date |
| TikTok Display | `/v2/video/list/` | No | Lifetime | `video.list` | 600/min | App | [Docs](https://developers.tiktok.com/doc/display-api-overview), 2026-08-04 |
| TikTok Research | `/v2/research/video/query/` | No | 30-day window | `research.data.basic` | 1,000/day | Academics; not creators | [FAQ](https://developers.tiktok.com/doc/research-api-faq), 2026-09-01 |
| TikTok Posting | `/v2/post/publish/status/fetch/` | No | - | `video.publish` | - | Audit | [Docs](https://developers.tiktok.com/doc/content-posting-api-get-started), 2026-08-04 |
| Instagram media | `/<IG_MEDIA_ID>/insights` | No curve; `reels_skip_rate`, `ig_reels_avg_watch_time` | Lifetime; 48 h | `instagram_business_manage_insights` | 4,800 x impressions/24 h | Professional account | [Docs](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights), 2026-09-11 |
| Metricool | `app.metricool.com/api` | No curve | Per post | token | unstated | Advanced plan | [Guide](https://help.metricool.com/basic-guide-for-api-integration-r97af), ~2026-09 |

C claims A refuted:
- Retention "quartiles only"; `audienceSurpassedXPercent`; Reporting-API playlist retention.
- Research API returns watch metrics; no TikTok API gives watch time.
- Instagram lacks skip rate and lists `impressions`, `plays`.
- Contradicted by A's table only: "1,000 views minimum", "50,000 units/day", "200 calls/hour", `instagram_graph_user_media`.

## Experiment protocol

- Test 2-3 deliberately different title/thumbnail variants with Test & Compare, older long-form first; no mid-test edits; no Shorts. Winner by watch time; confidence, minimum traffic unpublished; days to 2 weeks. PRACTITIONER [T1].
- Short-form: no TikTok A/B tool; compare across videos.
- Wait 48 h; compare at day 1, 7, 28 against ~10 same-format videos. PRACTITIONER [T1].
- Power (researchers' arithmetic, THEORY): 4% to 5% CTR needs ~6,100 impressions per variant; +10% relative ~38,400. ~3,000 views/video (~45-50k impressions, assumed): three arms detect only >=~16% relative. Expect Inconclusive.
- Inconclusive is not equal; underpowered wins overstate. THEORY [T4].
- Pool a variable over 6-10 videos, sign test (researchers' arithmetic): 6/6 p=0.016, 9/10 p=0.011. MrBeast team ran ~30 (PRACTITIONER [T2]).
- Peeking inflated 5% tests to 26.1% false positives. THEORY [T4].

## Learning loop

Fields (no template published; each appears in sources):
- Video, platform, format, length, series
- Purpose and success metric
- Hypothesis: the one changed variable
- Views at 1 h, 24 h, 7 d, 28 d; x/10
- CTR, AVD/AVP, total and Subscriptions feed
- Retention: % at 30 s, biggest dip, spike type
- Platform metrics: stayed-to-watch; TikTok curve; Instagram skip rate
- Result (Winner/Same/Inconclusive) with impressions; verdict
- Up to 3 learnings; "not happy with"

Cadence: day 1; 48 h; test end; 7 and 28 d; monthly.

## Rules

| ID | Rule | Tag | Source | Confidence |
|---|---|---|---|---|
| R14-01 | Compare only with your recent same-format, same-length videos at the same age. | PRACTITIONER [T1] | [Help](https://support.google.com/youtube/answer/11912632) | high |
| R14-02 | Judge nothing before 48 h; re-check at 7 and 28 days. | PRACTITIONER [T1] | A D3 | high |
| R14-03 | Read order: views, retention, other metrics, action. | PRACTITIONER [T3] | Galloway | medium |
| R14-04 | Change one variable per video; log it first. | PRACTITIONER [T1] | A D2.5 | high |
| R14-05 | Classify spikes as rewatch, confusion, skip or entry before editing. | INFERENCE | [Help](https://support.google.com/youtube/answer/1715160?hl=en) | medium |
| R14-06 | Read CTR with AVD and Intro; high CTR, low AVD means over-promise. | PRACTITIONER [T1] | [Help](https://support.google.com/youtube/answer/7628154?hl=en) | high |
| R14-07 | Check Subscriptions-feed CTR before blaming packaging. | PRACTITIONER [T1] | A B1.5 | medium |
| R14-08 | Do not compare views or retention across 2026-08-24. | INFERENCE | A V1 | medium |
| R14-09 | Ignore spikes under ~100 views; no key moments under 60 s. | DOC, PRACTITIONER [T3] Old | A M3 | medium |
| R14-10 | Pull curves via YouTube Analytics and TikTok Accounts APIs; Instagram gives only skip rate, average watch time. | DOC | API table | high |
| R14-11 | Thumbnail impressions and CTR come only from Reporting API. | DOC | API table | high |
| R14-12 | Test only deliberately different variants; Inconclusive means unknown. | PRACTITIONER [T1], THEORY | [Help](https://support.google.com/youtube/answer/16391400?hl=en) | medium |
| R14-13 | Pool a variable over 6-10 videos; fix the stop point first. | THEORY | A D2.7-2.8 | medium |
| R14-14 | Write "not published" where no range exists; never use C's ranges. | DOC | A Refuted | high |
| R14-15 | For a flop Short, compare stayed-to-watch with ~10 own Shorts. | PRACTITIONER [T1] | A D19 | medium |
| R14-16 | Treat Blackman-derived curve causes as hypotheses. | PRACTITIONER [T2/3] Old | A B3 | medium |

## Cannot be measured

- YouTube: survey results; key moments, Intro, stayed-to-watch via API; Test & Compare confidence; engaged-view cutoff; why a video was shown.
- TikTok: organic vs paid; data after 365 days; Display/Research retention.
- Instagram: API curve; per-reel reach sources; separate replays; trial-reel metrics.

## Refuted and myths

- "Watch time is king": YouTube retracted (A).
- "First hours decide": YouTube denies (A).
- "A dud tanks the channel": YouTube denies, except via audience memory (A).
- "Average retention 23.7%": no methodology (A).
- C's relative retention "0-200%": API is 0-1 (A).
- C's Shorts 75-80%, TikTok 50-70%, Instagram skip 50-70% ranges: no tier 1-3 source (A).
- C's "any loop counts": Shorts count replays since 2025-03-31 (A).
- C's "5% to 6% on 5K impressions, p~0.07": z-test gives ~0.03 (distiller's arithmetic).

## Disagreements

- Test & Compare: C "upcoming beta"; A live. A better (Help pages).
- Healthy CTR: C 4-6% (blogs); A half of channels 2-10%. A better.
- Confidence: C 75-90% actionable, unsourced; A none published. A better.
- Agree: spikes ambiguous; high CTR, low retention is clickbait.
- Open in A: engaged-view definition; view-change date (YouTube 08-24, vidIQ 08-27).

## Gaps

- No web search ran for A; C has no links.
- No ranges for APV, Intro, Shorts stayed-to-watch, TikTok watch time, Instagram skip rate.
- Unknown: curve basis after 2026-08-24; Analytics quota, minimum views, Shorts retention; personal-account `video.insights`.
- Instagram in-app graph undocumented; vidIQ/TubeBuddy APIs unverified.
- Full-video A/B rollout; no log template; sample sizes are arithmetic.
