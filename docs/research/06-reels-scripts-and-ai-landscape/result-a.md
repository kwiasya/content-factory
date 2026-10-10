# Scripting Travel "Walk With Me" Reels + 2026 AI Short-Form Video Tool Landscape

> Источник: deep research, принесён пользователем 2026-10-10. Инструмент (ChatGPT / Claude) не указан, переименовать файл когда станет известно. Локальная проверка: см. `verification.md` рядом.

Your agent should script for 45–60 seconds, an on-screen text hook in frame one, one short overlay per scene, and a caption with keywords and at most 5 hashtags. Instagram ranks on watch time, likes per reach and sends per reach (Mosseri, Jan 22, 2025: "The top three signals that matter most for ranking are watch time, likes and sends"), and it now enforces originality. Socialinsider's 2026 data has 45–60 s Reels ahead on both engagement and median views. Hashtags have been capped at 5 since Instagram's @creators account announced on Dec 18, 2025: "Starting today, Instagram will allow up to 5 hashtags in a reel or post" (down from 30). For tooling, a Resolve MCP server plus ffmpeg/ffprobe already covers most of what you need; almost every commercial "auto-Reel" product is built around speech and will not help with music-only travel footage.

## TL;DR
- **Script formula:** a visual + text hook in 0–1 s (5–8 words, top third, clear of UI); one overlay per scene, held ≥2 s; 45–60 s total; a loopable last shot; a caption that leads with the searchable place name, then ≤5 specific hashtags and a location tag. The goal is sends ("send this to who you'd go with"), not likes.
- **Algorithm 2026:** Mosseri's three named signals (watch time, likes per reach, sends per reach) have held since Jan 2025. The real 2025–26 changes are: skip-rate and retention charts in Insights (Aug 2025), the 5-hashtag cap (Dec 2025), "Your Algorithm" user controls (Dec 2025 → 2026), originality enforcement extended to photos/carousels (Apr 30, 2026), Google indexing of professional accounts (Jul 2025), and the 3-min recommendation ceiling. The widely repeated claim that "sends weigh 3–5x likes" is not something Mosseri said.
- **Tooling:** use `samuelgursky/davinci-resolve-mcp` (or your own thin Python wrapper over the Resolve API), Gyroflow OFX for stabilization, and the Instagram Graph API (Reels publishing + `ig_reels_avg_watch_time` insights) to close the loop later. Skip Opus Clip, Submagic, Klap, Vizard and Munch, which all assume speech. Watch out: Resolve's scripting module has been reported to break on Python 3.12, and per OpenAI's Help Center the Sora app ended on April 26, 2026 and the Sora API on September 24, 2026.

---

## Section A — Script template for a travel Reel

### A.1 Fields (the agent emits this as YAML/JSON before touching Resolve)

| Field | Type | Rule (with evidence basis) |
|---|---|---|
| `concept` | 1 sentence | One idea per Reel. The hook must promise something the first shot can actually show. |
| `target_length_s` | int | Default 45–60. Socialinsider (6M brand Reels, Jan–Jun 2026) found 45–60 s best on engagement (0.35%) and median views (10,374). A separate Socialinsider set of 140K Reels found 30–60 s had the best reach rate (5.60%). Never exceed 180 s: Instagram Help says "Reels over 3 minutes won't be recommended to new audiences." |
| `hook.type` | enum | `visual_payoff` / `pov` / `list` / `contrast` / `question` / `curiosity` (see Table B). |
| `hook.text` | ≤8 words | On screen from frame 0, high contrast, top third, outside the bottom caption/UI zone. |
| `hook.shot` | clip_id | The single most striking shot (reveal, view, landmark), not chronological shot #1. |
| `shots[]` | list | `clip_id, in, out, duration_s, role (hook/build/payoff/loop), overlay_text, overlay_type (place/fact/line/none), transition, beat_index`. |
| `overlay rules` | — | One overlay per scene or location change, not per cut. ≤6–8 words. Each holds ≥2 s. Never covers faces or the horizon line. Consistent font/position across the series. |
| `pacing` | — | Cut on music beats. Use 1.5–3 s shots for scenic walk content, and allow a longer hold (3–5 s) on the payoff/reveal. *(No rigorous travel-specific ASL dataset exists; see Table B caveat.)* |
| `ending` | enum | `loop_match` (last frame visually continues into frame 0), `reveal_last`, or `question_overlay`. Loops add views because Instagram's "Views" now counts repeat plays. |
| `cta` | 1 line | Prefer a send/save prompt ("Send this to who you'd walk here with", "Save for your [city] trip"). Sends per reach is the signal tied to non-follower reach. |
| `caption` | text | First line = keyword-rich hook with the place name (searchable in-app and by Google). Then 1–3 lines of value (fact, tip, best time). Then the CTA. Then ≤5 hashtags. |
| `hashtags` | ≤5 | Hard cap since Dec 18, 2025. Mix: place (#lisbon), niche (#citywalk), format (#walkwithme). |
| `location_tag` | string | Always set it; search matches against places. |
| `alt_text` | 1–2 sentences | Descriptive (indexed by Google for professional accounts since Jul 10, 2025). |
| `audio` | — | Original or licensed track. Avoid watermarked or reposted material, which counts against the originality rules. |
| `trial_reel` | bool | Optionally publish as a Trial Reel (non-followers only); the API supports `trial_params`. |

### A.2 Hard rules for the agent
1. **Hook in second 0–1, not 3.** Instagram reports *skip rate* (share leaving inside 3 s) in Reels Insights since August 2025. Socialinsider 2026 measured average skip rates of 60.5% (100K–1M accounts) to 65.5% (1–5K accounts), so most viewers are gone before second 3.
2. **Reorder for impact.** Do not keep chronological order by default. MEDit-Bench (arXiv 2607.25300) found professional editors reorder shots in 26.1% of edits, while GPT-5/Gemini models reorder in 0–2%. LLMs are biased toward chronology, so the prompt must explicitly allow reordering.
3. **Text is the narration.** With no voice, overlays carry the story. Write them for sound-off viewing.
4. **Originality.** Only your own footage, no watermarks. Instagram's April 2024 rule removes accounts that repost others' content "10 or more times in the last 30 days" from recommendations, and Instagram's Apr 30, 2026 post "Rewarding original creators on Instagram" extends this: accounts that "primarily post unoriginal content in photos or carousel posts, in addition to reels, will no longer be shown in places where we recommend content" (Instagram says original posts now make up 75% of US recommendations).
5. **Keep under 3 min** (recommendation eligibility); target 45–60 s.

### A.3 Feeding clip descriptions into script generation (prompt pattern)
This pattern follows LAVE (arXiv 2402.10294, 2024) and "From Shots to Stories" / L-Storyboard (arXiv 2505.12237, 2025): turn each shot into a structured *language* description, then let the LLM plan over the text.

1. **Per-clip "storyboard card"** (generated once per clip, cached in repo): `clip_id, camera (iPhone/Osmo), duration, fps, HDR/DV/D-Log flag (from ffprobe), GPS/place (from metadata), 3–5 keyframe captions (from a cloud VLM over ffmpeg-extracted frames at e.g. 1 fps), motion (walk/pan/static), best_moment_ts, visual_score 1–5, mood`.
2. **Planner prompt** = system rules (Section A.2) + the hook library (Table B) + style references (Table C) + all cards + music BPM and beat timestamps → output the Script schema (A.1) as strict JSON.
3. **Generate 3–5 hook variants**, have the model self-critique against the rules, and pick one (an Editor/Critic loop like EditDuet, arXiv 2509.10761, SIGGRAPH 2025).
4. **Validator** (plain Python): total duration, overlay word counts, ≥2 s overlay holds, ≤5 hashtags, safe-zone boxes, and clip in/out within source duration.

### A.4 Example script (abbreviated)
```yaml
concept: "Golden-hour walk from Alfama to Miradouro de Santa Luzia"
target_length_s: 48
hook: {type: visual_payoff, shot: C014@00:12, text: "POV: Lisbon at 7pm"}
shots:
  - {clip: C014, in: 12.0, out: 14.5, role: hook, overlay: "POV: Lisbon at 7pm", type: line}
  - {clip: C003, in: 4.0, out: 6.5, role: build, overlay: "Alfama", type: place}
  - {clip: C005, in: 0.0, out: 2.5, role: build, overlay: none}
  - {clip: C007, in: 8.0, out: 11.0, role: build, overlay: "Oldest district in Lisbon", type: fact}
  # ... beat-cut walk shots, one overlay per new location ...
  - {clip: C021, in: 3.0, out: 8.0, role: payoff, overlay: "Miradouro de Santa Luzia", type: place}
  - {clip: C014, in: 9.5, out: 12.0, role: loop, overlay: none}   # matches frame 0
caption: |
  Golden hour walk through Alfama to Lisbon's prettiest viewpoint 🌅
  Go 30 min before sunset; tram 28 stops right below.
  Send this to who you'd walk here with.
  #lisbon #alfama #portugaltravel #citywalk #walkwithme
location_tag: "Miradouro de Santa Luzia"
alt_text: "Walking through Alfama's narrow streets at sunset to a tiled viewpoint over Lisbon's rooftops and the Tagus river."
```

---

## Table B — Hook types and pacing numbers

| Item | Number / rule | Source | Strength of evidence |
|---|---|---|---|
| Top ranking signals | Watch time, likes per reach, sends per reach; sends "slightly more important" for non-followers | Mosseri, Jan 22, 2025 (via keywordseverywhere.com tracker, hanamisocial.com) | **Primary** (platform head) |
| "Sends = 3–5x likes" | **Not confirmed.** Mosseri only said sends matter "slightly more" | postey.ai, keywordseverywhere.com debunks vs. posteverywhere.ai, socialday.live claims | Treat as myth |
| Originality | Original creator gets distribution over reposters; share of impressions to originals "gone way up" | Mosseri four-video series, Sept 2026 (via bazzaal.com) | Primary (secondhand summary) |
| Skip-rate metric | % of viewers leaving within first 3 s, shown in Reels Insights since Aug 2025 | creatorflow.so citing Social Media Today; teleprompter.com | Platform feature |
| Skip-rate benchmark | 60.5% (100K–1M followers) vs 65.5% (1–5K) | Socialinsider, 140K Reels, Jan–Jun 2026 | Large dataset (brand accounts) |
| Best length | 45–60 s: 0.35% ER, 10,374 median views (~2x <30 s) | Socialinsider, 6M Reels, Jan–Jun 2026 | Large dataset (brands, not creators) |
| Best reach by length | 30–60 s: 5.60% reach rate | Socialinsider, 140K Reels 2026 | Large dataset |
| Recommendation ceiling | >3 min not recommended to new audiences; max length 20 min | help.instagram.com | **Primary** |
| Replays | No longer a separate metric; "Views" counts repeat plays (since Apr 2025 overhaul) | frameos.studio | Secondary |
| Text hook length | 5–8 words, first frame, high contrast | overlaytext.com, captionstudio.in, creatorflow.so | Practitioner consensus, no study |
| Overlay hold | ≥2 s per text element | overlaytext.com | Practitioner rule |
| Text-led hooks | ~50% of top Reels hooks lead with text overlay; avg hook 15 words | captain-hook.ai (vendor, method not disclosed) | Weak |
| Shot length | Short-form "often cuts every 1–2 s" | cutscore.io (vendor) | Weak; no travel-specific dataset |
| Shot length (Shorts) | "Top 100 Shorts 2024 avg clip 2.5 s → 35% higher completion" | vidpros.com (unsourced, 2024) | **Weak, possibly outdated** |
| Shot reordering | Pros reorder in 26.1% of edits; LLMs 0–2% | MEDit-Bench, arXiv 2607.25300 (2026) | Peer-review-track dataset |

**Hook types for walk/travel (map to `hook.type`):**

| Type | Template | When to use |
|---|---|---|
| Visual payoff first | Show the reveal/view at 0 s, then "how we got here" | Default for scenic walks |
| POV | "POV: you're in [place] at [time]" | Immersive walk-with-me |
| Numbered list | "5 streets in [city] you can't miss" | Multi-location walks; pairs with one overlay per item |
| Contrast / contrarian | "Skip [famous spot], walk here instead" | Lesser-known places |
| Question | "Would you walk this at 6am?" | Comment/send driver |
| Curiosity gap | "This street isn't on any map" | Hidden spots |

**Negative finding:** no credible public dataset gives the average shot length of 2025–26 *trending travel* Reels. Every number above is either a vendor rule of thumb or from other genres. Measure it yourself: run `ffmpeg -vf "select='gt(scene,0.3)'"` / PySceneDetect over 20–30 reference Reels and calibrate.

---

## Table C — Style-reference accounts/Reels

*Verification level: only @citiesbydiana has independent press coverage. The rest are verified via profile pages and the ContentScout weekly travel ranking (Oct 5, 2026) or a Buzzlytics leaderboard. Hook styles are inferred from caption or title text, so open each one to confirm the on-screen overlay. Follower counts are approximate and undated.*

| Account | Link | ~Followers | Why it works / what to copy |
|---|---|---|---|
| @goanniewhere | https://www.instagram.com/goanniewhere/ · Reel https://www.instagram.com/reel/DFA70GfOeRT/ | ~655K | Numbered/yearly roundup hook ("Best Places to Visit in the USA in 2025 ⬇️"); 2.2M views across 4 ranked posts |
| @theloverspassport | https://www.instagram.com/theloverspassport/ · https://www.instagram.com/reel/DWum_KrgVf5/ | ~1M | Numbered list + surprise emoji ("20 Must Visit Places in the USA 🤯"); also runs @thecreatorpassport coaching |
| @voyagefox_ | https://www.instagram.com/voyagefox_/ · https://www.instagram.com/reel/DT5kO5EDFXB/ | ~661K | Place-name-as-guide hook + "Comment GUIDE" (comment/DM driver) |
| @escapetolandscapes | https://www.instagram.com/escapetolandscapes/ · https://www.instagram.com/reel/DNPb77uxZzJ/ | ~616K | Contrarian hook ("Skip Switzerland and France and go to this country") |
| @elinaways | https://www.instagram.com/elinaways/ | ~36K | City numbered list ("13 places to visit in Los Angeles 🌴"); shows the format works for small accounts |
| @expeditionkristen | https://www.instagram.com/expeditionkristen/ · https://www.instagram.com/reel/DGI3hgmxJhg/ | n/a | Urgency list ("17 Places in Minnesota You Must See Before You Die") + "Comment 'MN'"; 10.5% engagement |
| @amomexplores | https://www.instagram.com/amomexplores/ · https://www.instagram.com/reel/DTB7VZcDvXi/ | n/a | List naming each city in text, one per shot; 625K views |
| @sophiabergholm | https://www.instagram.com/sophiabergholm/ · https://www.instagram.com/reel/DV_jAKvCF_M/ | n/a | Question hook ("Do you want to explore Sweden? 😍") → location guide |
| @stevenwommack | https://www.instagram.com/stevenwommack/ · https://www.instagram.com/reel/DTc9My6jALd/ | n/a | Match-cut travel transitions (2.9M views); an editing reference, not an overlay one |
| @citiesbydiana | https://www.instagram.com/citiesbydiana/ | ~249K | Fast satirical city ratings; strong city-hook writing (SF Standard interview, Nov 2025) |
| @4kwalk | https://www.instagram.com/4kwalk/ | ~5K | Pure city/nature walk format; closest to your niche but small, overlay style unverified |
| @earthpix | https://www.instagram.com/reel/DQCal5PDn7I/ | large | Caption-led storytelling hook; aggregator, so don't copy its repost model (originality rules) |
| @helenowen | https://www.instagram.com/helenowen/ | ~1.5M | High Reel views (104M per Buzzlytics); overlay style unconfirmed |

**Negative finding:** no large, verified "walk with me" / "POV: you're in X" Instagram account turned up in this sweep. The format is common but fragmented across small accounts. Build your own reference set from Instagram search on #citywalk / #walkwithme, and use the scene-detection idea from Table B to measure them.

---

## Table D — Tool landscape (grouped)

Legend: **Agent call** = how Claude Code would drive it. "n/v" = not verified in this sweep; check before relying on it.

### D1. AI video editors / auto-Reel generators

| Tool | Link | What it automates | API? | Price | Verdict for music-only travel footage |
|---|---|---|---|---|---|
| OpusClip | https://www.opus.pro | Long-video → clips (ClipAnything), captions, reframe, virality score, scheduling | **Conflicting:** Business-only (ssemble.com) vs Pro/Max API + MCP beta with caps (valmera.io, Aug 2026) | Free 60 credits; Starter $15/mo; Pro $29/mo or $174/yr; Business custom (checked Aug–Oct 2026) | **Skip.** Clip selection is "hit or miss on non-talking-head content" (usefastlane.ai); built for long → short, not curated walks |
| Instagram Edits | https://creators.instagram.com/edits | Meta's CapCut-style mobile editor (launched Apr 2025) | No | Free | Manual only; useful for checking safe zones/trending audio on phone |
| Submagic, Captions (Mirage), Klap, Vizard, Munch | n/v | Caption/subtitle animation and long-form clipping | Some offer APIs (n/v) | n/v | **Skip.** All are driven by speech transcripts; with no speech they have nothing to anchor on. Vizard/Klap Pro reportedly ~$14–14.50/mo (checkthat.ai) |
| Descript | n/v | Transcript-based editing | n/v | n/v | Skip until you add voiceover |
| CapCut AI, Veed, InVideo, Pictory | n/v | Template/auto-edit, stock-driven text-to-video | Mostly no public editing API (n/v) | n/v | Not relevant to a Resolve pipeline; Pictory/InVideo are stock-footage generators |
| Runway | n/v | Generative video + editing tools | Yes (Runway API, per devtk.ai) | n/v | Only for b-roll generation (D3), not editing your footage |

### D2. Agent-oriented video tooling (MCP, skills, OSS, papers)

| Tool | Link | License | Maturity / last release | Apple Silicon | Agent call | Verdict |
|---|---|---|---|---|---|---|
| samuelgursky/davinci-resolve-mcp | https://github.com/samuelgursky/davinci-resolve-mcp | n/v (check repo) | Active; ~3.4K stars; tested on Resolve 21.0.2 Studio | Yes (macOS paths) | MCP (`npx davinci-resolve-mcp setup`); 37 compound / 389 granular tools | **Best-maintained Resolve MCP. Start here.** |
| DigitalWorkflowCompany/resolve-mcp | https://github.com/DigitalWorkflowCompany/resolve-mcp | MIT | Targets Resolve 21; 88 tools / 20 resources | Built for macOS | MCP (`resolve-mcp`) | Strong alternative; includes Resolve 21 AI features (IntelliSearch, transcription) |
| lordhoell/davinci-resolve-mcp | https://github.com/lordhoell/davinci-resolve-mcp | n/v | Based on 20.2.2 API; 440+ tools | Yes | MCP + bundled Claude Code skill | Too many tools for context. Use only if you want the skill file |
| wassermanproductions/unofficial-davinci-mcp | https://github.com/wassermanproductions/unofficial-davinci-mcp | Apache-2.0 | Verified on Studio 21 | Yes | MCP (`pip install git+…`) | Worth reading for **beat-aware music cuts** and loudness logic |
| Tooflex/davinci-resolve-mcp | https://github.com/Tooflex/davinci-resolve-mcp | n/v | 19 stars; small | Yes | MCP | **Key warning:** says Resolve's scripting module imports `imp`, removed in Python 3.12, and requires CPython 3.10/3.11. Test your 3.12 venv; keep a 3.11 venv for Resolve calls if needed |
| apvlv/davinci-resolve-mcp, hiteshK03, emircbngl (Free-edition) | https://github.com/apvlv/davinci-resolve-mcp | n/v | Small | Yes | MCP | Not needed (you have Studio) |
| Remotion + official Claude Code plugin/skills | https://www.remotion.dev/docs/ai/claude-code-plugin | Remotion license (free for individuals; company license terms n/v) | Active; skills launched Jan 2026 | Yes (Node) | `claude plugin install remotion@remotion` / `npx remotion skills add` | **Good for rendering overlay graphics** (animated place-name titles) as ProRes 4444 alpha clips to drop into Resolve. Don't render the whole Reel in Remotion |
| misbahsy/video-audio-mcp | https://github.com/misbahsy/video-audio-mcp | MIT | 30+ ffmpeg tools | Yes | MCP (Python) | Optional; Claude Code can call ffmpeg directly via shell |
| kevinwatt/ffmpeg-mcp-lite | (via a1adams comparison) https://github.com/a1adams/mcp-servers-for-video-editing | Apache-2.0 | v0.2.0, 27★ | Yes | `claude mcp add ffmpeg uvx ffmpeg-mcp-lite` | Minimal; redundant with shell ffmpeg |
| KyaniteLabs/kinocut (ex mcp-video) | https://github.com/KyaniteLabs/kinocut | Open source (n/v) | Active, on MCP Registry | Yes | MCP + `kino` CLI + Python | Interesting "quality gates"/receipts idea for validating renders |
| claude-code-video-toolkit, haidrrrry/claude-remotion-skill | https://github.com/haidrrrry/claude-remotion-skill | OSS | Community | Yes | Skill (markdown) | Copy their render-then-inspect-frames loop |
| **Papers** | LAVE arXiv 2402.10294 (2024); L-Storyboard 2505.12237 (2025); EditDuet 2509.10761 (SIGGRAPH 2025); CutClaw 2603.29664 (music-synced, 2026); DIRECT 2604.04875 (mashups, 2026); VideoAgent 2606.23327 (beat-synced edits, 2026); MEDit-Bench 2607.25300 (2026); Unified Agentic Video Editing 2609.12769 (2026); ELLMPEG 2602.00028 (2026) | — | — | — | Design patterns | Steal: text storyboard cards (LAVE/L-Storyboard), Editor+Critic loop (EditDuet), beat alignment (VideoAgent/CutClaw) |

### D3. Related-step AI tools

| Tool | Link | Category | API? | Price | Verdict |
|---|---|---|---|---|---|
| Gyroflow + OFX plugin | https://gyroflow.xyz/download · https://github.com/gyroflow/gyroflow-plugins | Gyro stabilization | CLI/app + OpenFX plugin in Resolve | Free, open source (GPL, n/v) | App v1.6.3, OFX v2.1.1; Metal acceleration on Mac; supports DJI gyro. **Use it for Osmo footage** (confirm your Pocket model logs gyro). Agent can apply OFX via Resolve script or pre-render with the CLI |
| Kling 3.0 | via fal.ai https://fal.ai | Image-to-video b-roll | Yes (fal.ai, Replicate) | $0.084/s silent, $0.126/s with audio at 720p; 4K $0.42/s (teamday.ai, Sept 2026) | Cheapest quality option; 15 s max |
| Seedance 2.0 / 2.5 | via fal.ai | Image-to-video | Third-party API | ~$0.15/s at 720p (2.0); ~$0.23/s (2.5) | Good image-to-video; data routes via ByteDance |
| Veo 3.1 | Gemini API / Vertex AI | Text/image-to-video with audio | Yes (official) | **Conflicting:** $0.15–$0.75/s depending on tier/source | 8 s max per generation |
| Sora 2 | — | — | **Discontinued**: app Apr 26, 2026, API Sept 24, 2026 (OpenAI Help Center) | — | **Do not build on it** |
| Runway, Luma, Pika, Higgsfield | n/v | Generative video | Runway API exists; others n/v | n/v | Optional |
| fal.ai | https://fal.ai | Multi-model hub (600+ models) | HTTP API / Python SDK | Pay-per-use | **The one integration** if you want gen-video b-roll |
| Topaz Video AI | n/v | Upscale/denoise | CLI (n/v) | Paid (n/v) | Heavy on 8 GB RAM; low priority since you shoot 4K → 1080 output |
| Auto-reframe 9:16 | Resolve Studio Smart Reframe (built-in) | Reframe | Resolve UI (script exposure n/v) | Included | Mostly unnecessary if you shoot vertical; for horizontal clips, use Smart Reframe in Resolve |
| Thumbnail/cover | Instagram API `cover_url` / `thumb_offset` | Cover selection | Graph API | Free | Simplest: agent picks the hook frame and exports a still from Resolve/ffmpeg as cover |
| Background removal | Resolve Magic Mask (built-in) | Matte | Resolve | Included | Use for text-behind-subject overlays; it's GPU-heavy on M2 8 GB |

**Negative finding:** generative b-roll on a channel built on real walks works against Instagram's authenticity push. Mosseri's Dec 2025 memo argues raw content proves a human made it, and since Aug 31, 2026 profiles showing an AI-generated person need a label. Use gen-video sparingly (maps, transitions), not as fake scenery.

### D4. Publishing, scheduling, analytics

| Tool | Link | API? | Price | Limits / notes | Verdict |
|---|---|---|---|---|---|
| Instagram Graph API (Content Publishing + Insights) | https://developers.facebook.com/docs/instagram-platform | REST; `POST /{ig-user-id}/media` `media_type=REELS` → poll `status_code` → `media_publish` | Free (needs Business/Creator acct + app) | 100 API-published posts per 24-hour moving period per Meta's Content Publishing guide (a carousel counts as 1); the 50 figure some sites quote is a leftover in the same guide's carousel section, and 25 was the 2021 launch limit; containers expire in 24h; `trial_params` for Trial Reels; insights incl. `ig_reels_avg_watch_time`, `ig_reels_video_view_total_time`, reach, shares, saved; video must be at a public URL or resumable upload; Meta docs reportedly still say 30 hashtags (the app enforces 5) | **Best long-term loop-closer.** Pull avg watch time + shares per reach per Reel into the repo |
| Buffer API | https://buffer.com | GraphQL; public MCP server + CLI | Free plan 1 API key; paid 5; ~3,000/7,500/15,000 requests/mo by tier | 11 channels incl. Instagram | Easiest scheduling via MCP; weaker analytics |
| Metricool API | https://metricool.com | REST | API requires Advanced/Custom plan | Strong analytics | Use if you want analytics without building Graph API code |
| Later | https://later.com | n/v (no public dev API confirmed) | From ~$25/mo | Visual planner | Manual use only |

---

## Section E — Top 5 things you'd be foolish to ignore

1. **Test the Resolve Python version issue first.** One Resolve MCP states that Resolve's `fusionscript` module imports `imp`, which was removed in Python 3.12. Your venv is 3.12. Verify `import DaVinciResolveScript` under 3.12 with Resolve 21.1.1 on day one, and keep a 3.11 venv as a fallback.
2. **Don't write a Resolve bridge from scratch.** `samuelgursky/davinci-resolve-mcp` (tested on Resolve 21 Studio) plus a thin custom Python layer for your specific operations (timeline from Script JSON, Text+ overlays, LUT per camera profile) is the fastest path. Borrow beat-cut logic from `unofficial-davinci-mcp`.
3. **Optimize for sends and watch time, write for search.** Use a 0–1 s text + visual hook, aim for 45–60 s, loop the ending, and add a send CTA. Lead the caption with the place name, add ≤5 hashtags, and fill in the location tag and alt text. Professional-account posts are indexed by Google since July 2025.
4. **Close the loop with the Instagram Graph API.** Store each Script next to its `ig_reels_avg_watch_time`, shares, saves and reach. After 10–20 Reels, the agent can learn which hook types work for *your* audience, which beats any blog benchmark. Trial Reels via API let you A/B hooks on non-followers.
5. **Ignore the speech-first SaaS and treat "algorithm hacks" with skepticism.** OpusClip, Submagic and similar tools don't fit music-only walks. Claims like "sends = 3–5x likes," "the first 90 minutes decide reach," or a "July 2026 skip-rate signal" are not backed by Instagram. Sora is gone, so any gen-video dependency should go through a multi-model hub (fal.ai).

## Caveats
- Most "data" on hooks and pacing comes from vendors or practitioners without disclosed methods. Socialinsider's datasets are large but cover **brand** accounts, not small travel creators.
- Several Mosseri statements (Sept 2026 videos, Dec 2025 memo) were read through secondary summaries, not the original posts.
- Table D rows marked n/v were not verified in this sweep (price/API/license). Check vendor pages before committing.
- Instagram API publishing limits: Meta's Content Publishing guide states 100 API-published posts per 24-hour moving period, but the guide's carousel section and the `content_publishing_limit` field reference still show 50. Read `GET /{ig-user-id}/content_publishing_limit` at runtime instead of hard-coding.
- Pre-2024 sources: none relied on, except LAVE (Feb 2024, still relevant as a design pattern).
