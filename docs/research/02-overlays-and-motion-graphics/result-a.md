# Programmatic Text Overlays, Transitions & Motion Graphics for Travel Reels (Resolve Studio 21.1.1 + Claude Code, M2 8 GB)

> Источник: deep research, принесён пользователем 2026-10-10. Инструмент (ChatGPT / Claude) не указан, переименовать файл когда станет известно. Проверка по локальному стабу: см. `verification.md` рядом.

Use two engines. Build the cuts, transitions, fades and speed changes natively in Resolve through the new 21.1 scripting calls. Render every animated text overlay outside Resolve with Remotion, as short ProRes 4444 clips with alpha, then place them on upper video tracks. Avoid Fusion Text+ insertion through the API as the main path: on 21.1 it ripple-inserts on V1 and has silent-failure problems.

## TL;DR
- **Primary path:** Remotion (free for a solo creator, v4.0.533 released Oct 5, 2026, official Agent Skills for Claude Code) renders each overlay as a ProRes 4444 alpha clip. The agent imports these into Resolve and places them with `AppendToTimeline` (recordFrame/trackIndex) on V2/V3. Resolve 21.1's `AddTransition`, `SetFades` and `SetSpeed` handle the cuts.
- **Fallbacks:** HyperFrames (HeyGen, Apache-2.0, ProRes 4444 via `--format mov`) if Remotion's 5.0 licence or the 8 GB machine causes trouble. Hand-built Fusion Text+ templates in Resolve when you want titles you can edit live. FCPXML, Motion Canvas, MoviePy and the AI caption SaaS tools are not worth it for this use case.
- **Safe zone:** on 1080×1920, keep text out of the top 269 px, the bottom 672 px and 65 px on each side. That follows the Meta Ads Guide for Instagram Reels, which zeely.ai quotes as: "leaving roughly 14% of the top, 35% of the bottom, and 6% on each side of your asset free from text, logos, or other key creative elements". Zeely also says Meta merged the Stories and Reels safe zones into this one spec in March 2026. It leaves a 950×979 px safe box. Also keep clear of the right-hand action rail in the lower part of the frame. I found no rigorous source on travel-Reel text trends; most "2026 typography trend" articles are generic design blogs.

## Key Findings

1. **What Resolve 21.1 adds for transitions.** Resolve 21.1 (Sept 8, 2026) added roughly 20 Studio-only scripting calls, including "Add transitions", "Query and set timeline item fades" and "Query and set timeline item speed change". Community-confirmed names: `TimelineItem.AddTransition({...})`, `TimelineItem.SetFades/GetFades`, `TimelineItem.SetSpeed({...})`. One tester recorded this call shape: `AddTransition({'type': 'Cross Dissolve', 'category': 'simple', 'position': 'end', 'duration': N})`. They also report that an `alignment` key is effectively required: leave it out and the call silently returns `None`.
2. **Where the official signatures are.** The typed signatures are no longer in `README.txt`. Since 21.1 the scripting pack ships `README.md`, `DaVinciResolveScript.pyi` and `CHANGELOG.md`, which exist only on your install. Have the agent read the `.pyi` on your Mac before it writes any Resolve code.
3. **21.1.1 async APIs are unnamed.** Blackmagic's 21.1.1 readme (updated Oct 1, 2026) only says "Async APIs for quick export, transcription and scene cut detection" and "Async APIs for Smart Reframe and subtitle creation". It also lists "ApplyGradeFromDRX API option to apply changes to all node layers" and "Addressed transitions on clips with foreground composite mode". I found no public method names. Digital Production says the release summary "leaves signatures and completion details" out.
4. **Fusion titles via the API are risky.** On Studio 21.1, `InsertFusionTitleIntoTimeline` "always drops the title into V1 at the playhead as a **ripple insert**, pushing everything after it later". Published macro inputs "read back 0.0 and ignore scripts", so text must be set on the inner Text+ tools. Community ledgers also report Fusion writes that read back correctly but never reach the render.
5. **No free move or trim of placed clips.** The scripting API cannot move or trim a timeline item once it is placed; you delete and re-append. The agent therefore has to build the timeline correctly in one pass with `AppendToTimeline` clip-info dicts. Iterating clip by clip is not possible.
6. **Remotion fits a solo creator on licence.** It is free for individuals and companies of up to 3 people, commercial use included. ProRes 4444 alpha uses `--codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png`. The Remotion MCP is deprecated because, per remotion.dev/docs/ai/mcp, "Remotion pays the token costs for MCP requests" and it "duplicates the /remotion-docs skill". The hosted MCP "will shut down no earlier than August 31, 2026", with updates tracked in GitHub issue #9055. Use Skills instead: install with `npx remotion skills add` and use `/remotion-docs`.
7. **8 GB RAM is a real constraint for Remotion.** By default it uses half the CPU threads for concurrency and half of system memory for the OffthreadVideo cache. Users have reported Chrome running out of memory on long single-pass renders on low-memory machines. Short, separate overlay clips that contain no video avoid most of this.
8. **Motion Canvas is effectively abandoned.** Its site is offline and the last commit was reportedly in Dec 2024; the Canvas Commons fork is the maintained one. MoviePy's latest release is 2.2.1 (May 21, 2025). Neither beats Remotion or HyperFrames for an agent.
9. **AI caption tools don't fit yet.** They are speech-driven, and your Reels have no speech. Submagic is the only one I verified with an API (Business + API, $69/mo, 100 API minutes).

## Table A — Rendering paths head to head

| Path | Agent can fully automate? | Output format | Render time estimate (M2 8 GB) | License / cost | Maintenance | Verdict for you |
|---|---|---|---|---|---|---|
| **Resolve Fusion Text+ via API** (`InsertFusionTitleIntoTimeline` + `GetFusionCompByIndex` → Text+ `StyledText`/`Font`) | Partly. Text and font can be set; placement ripple-inserts on V1; animation keyframes need Fusion BezierSpline scripting; silent-failure reports | Native timeline title (editable) | Real-time in Resolve; final render cost only | Included in Studio ($295 one-time) | Active (Blackmagic) | **Fallback** for titles you want to edit by hand; not the unattended main path |
| **Resolve title templates / Fusion macros (.setting, multi-template .drfx)** you author once | Partly. Same insertion problem; published macro inputs ignore scripts | Native title | Same as above | Free (your own) or paid packs | Active; 21.1 updated the Macro Editor (per your preliminary lead) | Good for a hand-tuned "house" title you insert manually or via a carrier-clip workaround |
| **Resolve 21.1 transitions/fades/speed API** | Yes for dissolves, fades and constant speed changes; `alignment` key required; rippled `SetSpeed` reportedly deleted music | Native timeline edits | Instant | Studio | New in 21.1 (Sept 2026), early | **Primary for transitions** |
| **Remotion → ProRes 4444 alpha → Resolve V2/V3** | Yes (CLI `npx remotion render`, Skills) | ProRes 4444 `.mov` with alpha, or PNG sequence | Estimate (unverified): roughly 10–60 s per 2–4 s overlay at 1080×1920; benchmark it with `npx remotion benchmark` | Free for individuals / ≤3 people; companies pay $25/seat/mo or $0.01/render ($100 min) | Very active (v4.0.533, Oct 5, 2026); 5.0 licence change pending | **Primary for text and motion graphics** |
| **HyperFrames (HTML/GSAP → MOV)** | Yes (CLI, `npx skills add heygen-com/hyperframes`) | ProRes 4444 `.mov` alpha, WebM, PNG sequence | One public test: 8 s 1440p title, median 22 s (hardware not stated) | Apache-2.0, free | Active (launched May 2026) | **Best fallback**; fully open licence |
| **Lottie → video** (lottie-to-video, Puppeteer + ffmpeg) | Yes (CLI) | MOV/WebM with transparency | Similar to the browser-capture tools | Open source; LottieFiles assets vary | Small community project | Only if you buy or design Lottie title packs; it adds a design step |
| **Motion Canvas** | Yes in principle | Image sequence / video | n/a | MIT | Original abandoned; Canvas Commons fork active | **Not worth it** |
| **Manim** | Yes | Video | n/a | MIT | Not assessed in this pass | Built for maths explainers; wrong aesthetic. **Skip** |
| **ffmpeg drawtext / ASS (libass)** | Yes | Burned-in video (alpha possible but awkward) | Fastest | LGPL/GPL, free | Mature | Only for drafts or burned-in previews; no Resolve-editable layer and weak easing. Not verified in depth here |
| **MoviePy 2.x** | Yes (Python) | Video | Slow per frame on CPU | MIT | Last release 2.2.1, May 2025 | **Skip.** Slower and less expressive than Remotion |
| **FCPXML generation → Resolve import** | Yes for cuts and dissolves | Timeline | Instant | Free | Format is mature; Resolve import has known retime quirks | Unnecessary now that the 21.1 API exists; reported speed-ramp round-trip bugs |
| **AI caption / template SaaS** (Submagic API; others GUI-only) | Submagic only, and speech-based | Burned-in MP4 | Cloud | Submagic Business + API $69/mo | Active | **Not useful** with no speech |

## Table B — Tools and templates found

| Name | Link | Type | Cost / license | Last release / status | macOS Apple Silicon | How an agent calls it |
|---|---|---|---|---|---|---|
| DaVinci Resolve Studio 21.1.1 | https://www.blackmagicdesign.com/support/content/readme/dfbb6e4233c144d1b328c109c7ebc11e | NLE + scripting API + native MCP | $295 one-time | 21.1.1 notes updated Oct 1, 2026 | Yes | Python API (`DaVinciResolveScript`), native MCP via File → Setup AI Assistants |
| Resolve 21.1 API surface (community capture of CHANGELOG.md) | https://github.com/danielbaldwin47/resolve-mcp/issues/263 | Docs/issue | — | Sept 15, 2026 | — | Reference for method names |
| samuelgursky/davinci-resolve-mcp | https://github.com/samuelgursky/davinci-resolve-mcp | Community MCP server (37 compound / 389 granular tools) | MIT | Releases through Oct 8, 2026 (v4.8.x line) | Yes | MCP server (stdio), `python install.py` |
| CLI-Anything fusion title PR | https://github.com/Matty-1337/CLI-Anything/pull/3 | Reference implementation | Open source | Sept 30, 2026 | Yes | Shows how to place Fusion titles without ripple (carrier clip) |
| Remotion | https://www.remotion.dev/docs/transparent-videos | React video renderer | Free ≤3 people; Company licence otherwise | v4.0.533, Oct 5, 2026 | Yes (renderer needs macOS 15+ since v4.0.450) | CLI `npx remotion render`, Node `renderMedia()` |
| Remotion Agent Skills | https://www.remotion.dev/docs/ai/skills | Claude Code skills | Free | Active | — | `npx skills add remotion-dev/skills`; `/remotion-markup`, `/remotion-captions`, `/remotion-maps`, `/remotion-render`, `/remotion-docs` |
| Remotion MCP | https://www.remotion.dev/docs/ai/mcp | MCP | — | **Deprecated**; shutdown no earlier than Aug 31, 2026 | — | Don't use |
| Remotion licence / 5.0 terms | https://github.com/remotion-dev/remotion/blob/main/LICENSE.md ; https://www.remotion.dev/docs/licensing/ | Licence | — | 5.0 terms not yet in force | — | 5.0 makes telemetry mandatory for Automators only |
| remotion-superpowers (DojoCodingLabs) | https://github.com/dojocodinglabs/remotion-superpowers | Third-party Claude Code plugin (5 MCP servers, 13 commands incl. `/create-short`) | Free, open source | v2.1.0 | Yes | Claude Code plugin; overkill for you |
| HyperFrames (HeyGen) | https://hyperframes.heygen.com/guides/rendering | HTML → video renderer | Apache-2.0 | Active (May 2026 launch) | Yes (Node 22+, Chrome, FFmpeg) | `npx hyperframes render --format mov`; `npx skills add heygen-com/hyperframes` |
| html-video (Open Design) | https://github.com/nexu-io/html-video | Agent studio on top of HyperFrames, 21 templates | Apache-2.0 | Active | Yes | CLI/studio; Remotion adapter only planned |
| lottie-to-video | https://github.com/followLemmi/lottie-to-video | Lottie → MP4/WebM/MOV CLI | Open source | Small project | Yes (Puppeteer) | `npx lottie-to-video in.json -b transparent -o out.mov` |
| Motion Canvas / Canvas Commons | https://github.com/motion-canvas ; https://news.ycombinator.com/item?id=47191103 | Canvas animation | MIT | Original abandoned; fork active | Yes | Don't adopt |
| MoviePy | https://pypi.org/project/moviepy/0.2.1.7.12/ | Python video lib | MIT | 2.2.1, May 21, 2025 | Yes | Python import |
| Submagic | https://cutsnap.ai/blog/submagic-pricing-2026 | Caption SaaS with API | $69/mo Business + API (100 API min) | Active | Web | HTTP API; speech-dependent |
| MotionVFX mTitle Mega Pack DVR | https://www.motionvfx.com/store,mtitle-mega-pack-dvr,p4267.html | Paid Resolve titles (125, horizontal or vertical) | Paid | Requires Resolve 18.6, **16 GB system memory, 4 GB VRAM** | Yes, but above your RAM spec | Manual insert / `InsertFusionTitleIntoTimeline` by name |
| Motion Array free Resolve presets | https://www.miracamp.com/learn/davinci-resolve/free-presets | Free .setting titles/transitions | Free | — | Yes | Copy into Fusion Templates folder |
| 9 Free Elegant Titles (MotionElements) | https://www.freevisuals.net/item/9-free-elegant-titles-davinci-resolve-pack | Free Resolve titles | Free, commercial OK | Listed Sept 2026 | Yes | Template insert |
| Figma Motion | https://www.figma.com/blog/introducing-figma-motion/ | Design-tool motion timeline (exports MP4/WebM/CSS/JSON) | Open beta; paid plans for agent | June 24, 2026 | Web/desktop | MCP-compatible but GUI-first; **mostly GUI** |
| GUI-only (no usable public API for this use) | — | Captions app, Opus Clip, CapCut templates, Canva video, Adobe Express | — | — | — | GUI-only (not verified individually in this pass) |

## Details

### 1. Inside Resolve: how far an agent can go
- **Create a title:** `Timeline.InsertTitleIntoTimeline(name)` and `InsertFusionTitleIntoTimeline(name)` return a TimelineItem. On 21.1 the Fusion call is a ripple insert at the playhead on V1, which is unsafe on a cut timeline. The workaround in CLI-Anything PR #3 is to make an explicit "carrier" clip and put the Fusion comp on it.
- **Set text and font:** get `item.GetFusionCompByIndex(1)`, take the Text+ tool from `comp.GetToolList(False, "TextPlus")`, then call `SetInput("StyledText", ...)` and set `Font`/`Style`. These examples are pre-2024 community posts, so they may be outdated, but the pattern still holds. For templates, write to the **inner** Text+ tools, because published macro inputs ignore scripted writes on 21.1.
- **Animation in/out:** possible only through Fusion scripting, for example assigning `comp.BezierSpline()` to an input and setting keyed values per frame (forum post, older). A better approach is to bake the animation into the template and let the clip duration drive it.
- **Position and track control:** you cannot move a clip after placing it. Build with `AppendToTimeline([{mediaPoolItem, startFrame, endFrame, recordFrame, trackIndex}])`.
- **Reliability:** community ledgers report Fusion "success-without-write" (values read back but never render) and comps that "render as identity". Every Fusion-based overlay therefore needs a render-and-check step, such as a frame grab with ffmpeg that Claude then looks at.
- **Templates:** free packs (Motion Array freebies, MotionElements) are mostly 16:9. MotionVFX sells vertical-capable packs but lists 16 GB RAM. I found no well-maintained free library aimed at 9:16 travel titles. You will get better results by building 3–4 of your own `.setting` templates.

### 2. Remotion
- **Maturity:** releases ship almost daily (v4.0.524–533 between Sept and Oct 5, 2026). `@remotion/transitions` (including a push presentation) and `@remotion/effects` (including light leak) cover overlay-style transitions.
- **Licence:** free for your situation. For companies, Creators is $25/seat/mo and Automators is $0.01 per render with a $100 monthly minimum (checked Sept 11, 2026 by a third party). The 5.0 terms make telemetry mandatory for Automators. Per remotion.dev/docs/licensing, opting out from 5.0 requires an Enterprise License with "monthly usage reports", which "has the same per-render pricing, but requires a minimum spend of $500 per month". These terms take effect only when 5.0 ships.
- **Agent integration:** official Skills (`/remotion-markup`, `/remotion-render`, `/remotion-captions`, `/remotion-maps`) and a Claude Code / Codex plugin. `/remotion-maps` is directly useful for animated route maps.
- **Best practices for transparent overlays:** never set a background. Render ProRes 4444 with `yuva444p10le`. Keep each overlay a separate short composition, sized 1080×1920 at your timeline frame rate. Don't embed footage, so the OffthreadVideo cache never comes into play.
- **Settings for 8 GB:** set `--concurrency` to 2–4 (benchmark it) and enable `disallowParallelEncoding` if memory runs short.

### 3. Other code-driven renderers
HyperFrames is the only real competitor. It writes plain HTML with GSAP and needs no React build step, which is arguably easier for an agent to diff. MOV output is ProRes 4444 with alpha. Its WebM alpha works only in browsers: "every video editor renders the transparent areas black". HDR is MP4-only, and transparent output falls back to SDR. Lottie is worth it only if you source Lottie title assets. Motion Canvas, Manim and MoviePy: skip them.

### 4. Transitions in Resolve
| Effect | Programmatic route | Notes |
|---|---|---|
| Dissolve / dip | `TimelineItem.AddTransition({...,'alignment':...})` | Confirmed working for Cross Dissolve. Other type names: read them from the `.pyi` |
| Fade in/out | `TimelineItem.SetFades({...})` (frames) | Works; fades reportedly lost through project export/import |
| Constant speed change | `TimelineItem.SetSpeed({...})` | Never use `RippleTimeline: true`: reported to cut unlinked tracks and delete music |
| Speed ramp (variable) | No evidence of a curve API; pre-conform the clip with ffmpeg, or ramp by hand in review | Negative finding |
| Whip pan | Pre-rendered blur/streak overlay (Remotion), or a Fusion transition `.setting` you apply by hand | No native API "whip pan" found |
| Zoom punch | Pre-render: ffmpeg `zoompan` / scale on a short segment, or a Fusion comp on the clip | No evidence of Inspector keyframe setters in the API |
| Match cut | Editorial: the agent extracts frames with ffmpeg, Claude compares them visually, then it orders clips | A cut decision, not an effect |
| Luma fade | Fusion transition template, or a pre-rendered luma matte overlay | Manual or templated |

### 5. Style profile (store it in git)
Keep one `style.json` and treat it as the single source of truth. Fields: fonts (files committed, licensed for video), colours, type scale, the safe-zone rectangle, easing curves and durations per animation preset (e.g. `locationTag.in = 12f slide+fade`), maximum characters per line, and a `transitions` map. Remotion imports it as TypeScript tokens. Resolve-side scripts read the same file for fade lengths and transition types. Render a "style test sheet" overlay after any style change and compare it against a reference PNG.

### 6. Trends: what the evidence supports
- I found **no** data-driven analysis of 2025–2026 travel or "walk with me" Reel text styles. That is a negative finding.
- 2026 typography roundups (design blogs, not platform data) list kinetic typography and a serif comeback as trends.
- One short-form guide reports a move "away from constant all-caps", renewed interest in lowercase, and advises keeping "the typeface stable" while motion comes from scale, position and timing.
- Treat "minimal serif location tag + small fact line" as a reasonable style choice, not an evidenced trend. Test it yourself through Instagram Insights.

## Section C — Recommendation

**Primary path:** Resolve-native editorial plus Remotion overlays.
1. The agent writes `script.json`, then builds the timeline in one pass with `AppendToTimeline`, using recordFrame and trackIndex for V1 footage and V2/V3 overlays.
2. It renders each overlay (hook, place name, fact) with `npx remotion render` as ProRes 4444 with alpha, at the timeline's resolution and frame rate.
3. It imports the overlays and appends them to V2/V3 at their exact frames.
4. It applies `AddTransition`, `SetFades` and non-ripple `SetSpeed`.
5. It renders a review proxy and extracts frames for a visual check.

You then tweak in Resolve. A text change means editing the JSON and re-rendering one overlay in seconds, not retyping in Fusion.

**Why this path:**
- It avoids the 21.1 Fusion insertion and silent-write problems.
- Overlays are deterministic and version-controlled.
- Remotion is free for you, the best-maintained option, and has official Claude Code skills.
- Overlays without footage keep memory low on 8 GB.

**Fallbacks:**
- (a) HyperFrames, same alpha-MOV contract, if Remotion's licence or renders cause trouble.
- (b) Your own Fusion Text+ `.setting` templates, inserted through a carrier clip, when you want titles you can edit live in Resolve.

**Top 3 risks:**
1. **API immaturity and drift.** The 21.1 calls are weeks old, signatures live only in your local `.pyi`, the 21.1.1 async calls are undocumented publicly, and LLMs invent method names. Mitigation: a skill file that forces the agent to grep the `.pyi`, plus a smoke-test script run after every Resolve update.
2. **Running out of memory with Resolve and Chromium together on 8 GB.** Mitigation: render overlays before opening the project or while Resolve is idle, at concurrency 2.
3. **HDR / colour mismatch.** iPhone Dolby Vision and D-Log M timelines need a defined output colour space. SDR graphics placed into an HDR or wide-gamut timeline can look dim or shifted. Mitigation: fix the timeline colour management and test the overlay brightness once.

Blackmagic's 21.1.1 readme (updated Oct 1, 2026) lists Mac memory minimums of "8 GB of system memory or 16 GB when using Fusion", "At least 16 GB for advanced AI tools" and "At least 32 GB for background rendering and analysis". It says nothing specific about the MCP server. The Fusion fallback is therefore above your 8 GB spec.

## Section D — Instagram Reels safe zone (1080×1920)

| Source | Top | Bottom | Sides | Safe area |
|---|---|---|---|---|
| Meta guidance as relayed by sprites.ai / imageresizers.net / 1clickreport (14% / 35% / 6%) | 269 px | 672 px | 65 px each | 950×979 px |
| Hopper HQ | ~270 px | ~670 px | Right action rail ~230 px wide over the bottom 40% (~770 px) | — |
| xyla.ai | 220 px | 430 px | 130 px | — |
| reformat.video | 220 px | 420 px | 35 px | — |
| Minta / Outfy (older, looser) | 108 px | 320 px | L 60 / R 120 px | 996×1400 |

**Use:** top 269 px, bottom 672 px, sides 65 px, plus no text in the right 230 px below y≈1150. Place location tags in the upper-middle band (y≈300–600) and hooks centred. For Reels ads carrying disclaimers, bereel.pro credits Meta Business Help with "Leave the bottom 40% free of text, logos, and key elements", which Mockingbird puts at about 768 px on a 1080×1920 frame. For organic posts, bereel.pro notes that "Meta publishes no safe-zone measurement for organic Reels, so treat the ad numbers as a safe, conservative margin, not an organic rule." The 14/35/6 figures come from the Meta Ads Guide wording as quoted by zeely.ai ("leaving roughly 14% of the top, 35% of the bottom, and 6% on each side of your asset free from text, logos, or other key creative elements"). I did not retrieve Meta's page directly.

## Caveats
- Several sources are vendor blogs (PilotCut sells a competing editor) or community issues. Method behaviour comes from community live probes on 21.1.0.x, not from Blackmagic docs.
- Your lead mentioned samuelgursky MCP "v2.29.0". The GitHub releases show a v4.8.x line (v4.8.20 on Sept 24, v4.8.23 on Sept 30, more through Oct 8, 2026). Check which one you actually have installed.
- Render-time figures are estimates. No M2 8 GB benchmark was found.
- Items flagged as pre-2024 (Text+ forum scripting, FCPXML round-trip bugs) may be outdated.
