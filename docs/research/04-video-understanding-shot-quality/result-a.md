# Giving a Reels Agent Eyes: Video Understanding Tools for Travel-Walk Clips (October 2026)

> Источник: deep research, принесён пользователем 2026-10-10. Инструмент (ChatGPT / Claude) не указан, переименовать файл когда станет известно. Локальная проверка окружения: см. `verification.md` рядом.

The best setup in October 2026 has two tiers. First, a free local tier on the M2 (ffmpeg filters + OpenCV optical flow + Apple Vision + a nano YOLO) computes per-second quality, motion and people signals. Second, Gemini Flash-class models, which are the only mainstream frontier API that accepts video natively, describe each clip and propose moments. The whole thing costs well under $1 per 60-clip walk. Claude and OpenAI cannot take video files and should only see frames or contact sheets.

## TL;DR
- **Vision LLM:** use Gemini 3.5 Flash-Lite (or 3.8 Flash for harder judgement) through the Files API, with audio stripped and 1–2 fps sampling. It is the only major API with native video input. Claude and OpenAI's API accept images only, and Qwen3-VL-Plus and TwelveLabs Pegasus are viable alternatives. A 60 × 20 s walk costs roughly $0.20–$0.60 on Gemini, and about $1.40 on TwelveLabs.
- **Local metrics:** nothing on the M2 needs a vision LLM to measure quality. Use ffmpeg `signalstats`/`blurdetect`/`scdet`, OpenCV global-motion estimation for shake, direction and pace, Apple Vision's built-in aesthetics score, and Ultralytics YOLO26n with tracking for people entering frame. Run all of these on a 540p tone-mapped proxy, which stays inside 8 GB. Skip TransNetV2, Lighthouse and local video LLMs: they don't pay off for single-take pre-selected clips on 8 GB.
- **Data and limits:** represent everything as one JSON shot log per clip (per-second metric arrays + scored candidate segments + LLM description). Mirror the candidates into OTIO markers or Resolve markers. Still unreliable in 2026: sub-second timestamp accuracy from LLMs, "taste" (best-moment ranking), metrics on log/HDR footage, and gyro data from the Osmo Pocket, which DJI does not expose.

## Table A — Tool/model × task matrix

Task key: **D** = describe, **BM** = best moment, **Sh** = shake, **Bl** = blur, **Ex** = exposure, **Pe** = people, **SC** = scene cut. ✅ = good, ◐ = partial/unreliable, — = no.

| Tool / model (where) | D | BM | Sh | Bl | Ex | Pe | SC | Local on M2 8 GB? | Cost | Latency (est.) | How agent calls it | License · last release · maturity | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Gemini 3.5 Flash-Lite (ai.google.dev/gemini-api) | ✅ | ◐ | ◐ | ◐ | ◐ | ✅ | ◐ | No (cloud) | $0.30/M input (text/image/video/audio), $2.50/M output; Batch $0.15/$1.25 (Google's Gemini API pricing page; Samprix, checked Oct 5, 2026, confirms the Batch rates) | ~5–20 s per 20 s clip | Python `google-genai` SDK: Files API upload → generateContent with JSON schema; also REST | Proprietary · released Jul 21, 2026 (per AIPriceCompare) · active | **Primary describer/moment proposer** |
| Gemini 3.8 Flash | ✅ | ✅/◐ | ◐ | ◐ | ◐ | ✅ | ◐ | No | $0.75/M in, $3.75/M out through Dec 31, 2026; doubles to $1.50/$7.50 from Jan 1, 2027 | similar | same | Proprietary · newest Flash · active | Use for the final "pick the hook" pass |
| Gemini 2.5 Flash-Lite | ✅ | ◐ | ◐ | ◐ | ◐ | ✅ | ◐ | No | $0.10/M in, $0.40/M out; Batch $0.05/$0.20 | similar | same | Proprietary · older generation (risk of deprecation) | Cheapest fallback |
| Qwen3-VL-Plus (Alibaba Model Studio) | ✅ | ◐ | ◐ | ◐ | ◐ | ✅ | ◐ | No | $0.20/M in, $1.60/M out (≤32K tokens, International) | similar | OpenAI-compatible HTTP API; video as file/URL or frame list with `fps` | Proprietary API over open Qwen3-VL family · active | Viable second opinion; explicit textual timestamps in architecture |
| TwelveLabs Pegasus 1.5 (twelvelabs.io) | ✅ | ✅/◐ | — | — | — | ✅ | ◐ | No | $0.042/min indexing ($2.50/h) + $0.0292/min analyzed ($1.75/h) + $7.5 per 1M output tokens (UsagePricing.com calculator, third-party); free 600 min | index then query | HTTP API / Python SDK; schema → timestamped metadata | Proprietary · Pegasus 1.5 Apr 2026 · active | Good at timestamped structured output; extra vendor + indexing step |
| Claude (Sonnet/Opus) via frames | ✅ | ◐ | — | ◐ | ◐ | ✅ | — | No | image ≈ (w×h)/750 tokens; ~1,600-token cap per image on standard models | per call | Anthropic API, or Claude Code reading PNGs | Proprietary · **no video input** | Use only on contact sheets of shortlisted moments |
| OpenAI GPT-5.x via frames | ✅ | ◐ | — | ◐ | ◐ | ✅ | — | No | per image token | per call | Responses API with image arrays | Proprietary · **API has no video input** | Not worth adding as a third vendor |
| Qwen3-VL 2B/4B local (MLX/GGUF via LM Studio) | ◐ | — | — | — | — | ◐ | — | Barely (4-bit, single frames) | free | slow, RAM-bound | LM Studio local server / mlx-vlm | Open weights · active | **Not worth it on 8 GB** for video; at most per-frame captions offline |
| ffmpeg `signalstats` (ffmpeg.org) | — | — | — | — | ✅ | — | — | Yes | free | decode-bound | CLI / ffprobe lavfi → per-frame YAVG/YLOW/YHIGH/YMIN/YMAX, SAT*, BRNG | LGPL/GPL · active | **Use** for exposure |
| ffmpeg `blurdetect` | — | — | — | ✅ | — | — | — | Yes | free | decode-bound | CLI, per-frame `lavfi.blur` | since FFmpeg 5.1 · active | **Use** (relative ranking within a clip) |
| ffmpeg `scdet` | — | — | — | — | ◐ | — | ✅ | Yes | free | decode-bound | CLI, `lavfi.scd.score` per frame | active | **Use** to flag whip-pans/exposure jumps |
| ffmpeg `vidstabdetect` | — | — | ✅ | — | — | — | — | Yes | free | ~real-time on proxy | CLI → transforms file | GPL (libvidstab) | Optional; OpenCV gives more control |
| OpenCV optical flow / global motion (opencv.org) | — | ◐ | ✅ | — | — | — | — | Yes | free | ~1–3 min per walk on 480p at 10 fps | Python `cv2` (LK + `estimateAffinePartial2D`) | Apache-2.0 · active | **Use** for shake, direction, pace |
| Gyroflow (gyroflow.xyz) | — | — | ✅ | — | — | — | — | Yes | free | n/a | GUI/CLI | Open source · v1.6.3 · active | **Not usable**: Osmo Pocket 3 not supported (no gyro export); iPhone only via third-party logging apps |
| PySceneDetect (scenedetect.com) | — | — | — | — | ◐ | — | ✅ | Yes | free | fast | Python lib / CLI | BSD-3 · v0.7.1 (Jul 21, 2026); v0.7 added VFR-correct timestamps · active | Use only if a clip has in-camera cuts |
| TransNetV2 (`transnetv2-pytorch`) | — | — | — | — | — | — | ✅ | Yes | free | moderate | Python | Original 2020; PyTorch port 1.0.5 (Jun 2025) · semi-stale | **Skip**: overkill for single-take clips |
| Apple Vision `CalculateImageAestheticsScoresRequest` (developer.apple.com) | — | ✅/◐ | — | ◐ | ◐ | — | — | Yes (Neural Engine) | free | ms per frame | Tiny Swift CLI the agent compiles; outputs `overallScore` (−1…1) + `isUtility` | Apple SDK, iOS 18 / macOS 15+ · maintained | **Use**: best free "is this frame nice" signal |
| Apple Vision face / human detection | — | — | — | — | — | ✅ | — | Yes | free | ms per frame | same Swift CLI | Apple SDK | Use for face-size/"stranger close-up" flag |
| pyiqa: NIMA, LAION-aes, MUSIQ, TOPIQ (github.com/chaofengc/IQA-PyTorch) | — | ◐ | — | ✅ | ◐ | — | — | Yes (small models); Q-Align no | free | slow-ish on MPS (open issue #190) | Python `pyiqa.create_metric()` / CLI | Apache-2.0 · 0.1.15.post2 · active | Optional cross-check; photo-trained (AVA), not video |
| Ultralytics YOLO26n/YOLO11n + tracker (docs.ultralytics.com) | — | — | — | — | — | ✅ | — | Yes (CPU/MPS, CoreML export) | free (AGPL-3.0) | ~1–2 min per walk at 2 fps | Python `ultralytics` `model.track()` | AGPL-3.0 or Enterprise · v8.4.175 (Oct 10, 2026) · very active | **Use** for "person enters frame" events |
| Lighthouse (github.com/line/lighthouse) | — | ◐ | — | — | — | — | — | Feasible but heavy (CLIP+SlowFast features) | free | slow | Python predictor API | Research lib · v1.0 · ICASSP 2026 | **Skip**: trained on QVHighlights vlog/news queries; worse than Gemini for taste |

## Supporting detail

### 1. Video-native APIs

| API | Native video? | Max length / input | Sampling | Timestamps | Notes |
|---|---|---|---|---|---|
| Gemini (3.x Flash family) | Yes | ~45 min with audio, ~1 h without; 10 videos/prompt; File API 20 GB (paid); inline <100 MB | Default 1 fps; custom `fps` and `start_offset`/`end_offset` clipping in static mode | Can "refer to specific timestamps"; MM:SS-style prompts | Gemini 3: 70 tokens/frame default, 280 high, audio 25 tok/s. The 66/258 figures on the older video page apply to "models earlier than Gemini 3" (Gemini Enterprise video docs), and Google's Gemini 3 guide says video is "capped at 70 tokens per frame" (280 at high) — the figures differ by model generation, so they don't actually conflict |
| Gemini agentic video (launched Sep 1, 2026) | Yes | same | Model chooses segments | Google claims "sub-second moment retrieval" | Google's Sep 1, 2026 blog says it can "reduce analysis costs by up to 66% and token consumption by up to 88%, while improving accuracy by up to 7%" (launched on 3.7 Flash, 3.6 Flash, 3.5 Flash-Lite). Per NYU Shanghai RITS's summary, 1H-VideoQA went from 397.6K to 47.7K tokens per query and LVBench from 300.3K to 36.0K. Clipping/fps options only work in static mode; benefit is small for 20 s clips |
| Qwen3-VL-Plus | Yes | 2 s – 1 h (qwen3-vl-plus series) | Default fps 2; `fps` param; frame lists accepted | Text-timestamp alignment ("<3.0 seconds>" tokens) | A GitHub issue (#1175) reports API timestamps not matching the real timeline on a 4:25 video — **verify** |
| TwelveLabs Pegasus 1.5 | Yes (index first) | up to 2 h | ~1 fps internal | Schema-driven, timestamped segments | Segment calls bill video window × number of segment definitions; Pegasus 1.2 rates ($0.021/min) differ from 1.5 ($0.0292/min) |
| Claude | **No** (images/PDF only; GIF = first frame) | — | you sample | none native | Community plugins (claude-video-vision MCP, claude-video skill) do ffmpeg frames → images |
| OpenAI GPT-5.x | **No** in API (GPT-5 model page: Video "Not supported"; openai-node issue #1778) | — | you sample | none native | Official guidance is ffmpeg frames |

Quality for "describe" vs "find best moment": every model describes well (landmarks, weather, crowd density, light). "Best moment" output is plausible but unvalidated. No public benchmark scores short-form travel moment selection; the only benchmarks are generic MR/HD sets such as QVHighlights. **Treat LLM moment picks as candidates to be re-ranked by local metrics, not as ground truth.**

### 2. Frame-sampling approach (for Claude / second opinion)
- **Sampling:** 1 fps is enough for describing; 2 fps for moment proposals; local metrics run at full or 10 fps. Gemini's 1 fps default misses sub-second events, and frame-based plugins have the same blind spot.
- **Contact sheets:** tile 12 frames (3×4) of a 9:16 proxy into one ≤1568 px-long-edge image with burned-in timestamps (`ffmpeg ... tile=3x4,drawtext=...`). On Claude that is ~1,600 tokens per sheet instead of ~1,600 per frame, about 12× cheaper. Fine detail is lost, so use sheets for "which second looks best", not blur judgement.
- **Cost math (60 clips × 20 s, 1 fps):**
  - 1,200 frames → 100 sheets × 1,600 = 160K tokens. That is ~$0.32 at Claude Sonnet 5's $2/M input, which Anthropic's "Introducing Claude Sonnet 5" post confirms ("introductory pricing of $2 per million input tokens and $10 per million output tokens is now permanent", Aug 10, 2026 edit), or ~$0.80 at Opus 5's $5/M (that Opus figure comes from a third-party review and is unverified).
  - Sending 1,200 individual frames instead is ~1.9M tokens. That is too much for one Claude Code context and wasteful.
- **Claude Code rule:** don't let the main agent session ingest frames. Have a Python script call the vision API per clip and write JSON. Claude reasons over JSON plus a few contact sheets.

### 3. Local metrics: how to compute them (all on a 540p proxy)
| Signal | Method | Output per second |
|---|---|---|
| Exposure | `signalstats` YAVG, YLOW/YHIGH (10th/90th pct), YMIN/YMAX; plus numpy % pixels ≥250 / ≤5 on the SDR proxy | `luma_mean`, `clip_hi_pct`, `clip_lo_pct` |
| Blur | `blurdetect` (Marziliano no-reference metric, block mode) + Laplacian variance in OpenCV | `blur` (normalize within clip) |
| Shake | OpenCV LK feature tracks → per-frame similarity transform → subtract a 1 s low-pass → RMS residual (px @1080 w) + roll jitter | `shake_px`, `roll_deg` |
| Direction / pace | Same transforms: mean dx → pan L/R; divergence of the flow field → forward/back walk; median flow magnitude / width / s → pace | `motion: {type, dx, div, speed}` |
| Hard changes | `scdet` score spikes | `scd_score` |
| Aesthetics | Apple Vision `overallScore` (−1…1) at 1 fps; optional pyiqa `laion_aes`/`topiq_iaa` | `aes` |
| People | YOLO26n person boxes + track IDs at 2–5 fps; Apple Vision face rectangles | `persons`, `max_person_h`, events `person_enter` |

**HDR/log handling (critical):** measure on a *normalized* proxy, not on the source.
- iPhone HLG/Dolby Vision: tone-map to SDR Rec.709 (zscale/tonemap) when creating the proxy.
- Osmo D-Log M: apply DJI's D-Log M→Rec.709 LUT via `lut3d` (LUT source not verified in this pass).
- Otherwise flat log footage looks "underexposed/low contrast", and HDR highlights look clipped when they aren't.

### 4. Open-source "auto editor" projects
| Project | What it does | Good at | Bad at (for travel Reels) | Maintained 2026? |
|---|---|---|---|---|
| auto-editor (github.com/WyattBlue/auto-editor) | Threshold cutting by audio loudness or motion (`--edit motion:threshold=2%`), exports to NLEs | Fast, CLI, robust decoding; added dissolve transitions | No notion of "beautiful"; silence-based logic is useless with no speech | **Yes**: 31.7.2 (Oct 3, 2026), ~4.2k stars |
| video-use (github.com/browser-use/video-use) | Claude Code skill: transcript-first editing, renders final.mp4; "The LLM never watches the video" (12 KB text + a few PNGs) | Right architecture (text + on-demand composites), MIT | Built around speech transcripts (ElevenLabs); little signal for no-speech walks | **Yes**: ~28.5k stars |
| claude-video-vision (jordanrendric) | Claude Code plugin + MCP: ffmpeg frames + Gemini/Whisper audio | Drop-in "watch" tool | Generic sampling; no quality metrics | Yes (Apr–May 2026) |
| claude-video (bradautomates), claude-real-video | Skills: scene-aware frames + transcript | Local, dedup keyframes | Q&A-oriented, not editing | Yes (2026) |
| ShortGPT, Jumpcutter, Vidio, Clipper, LosslessCut automation | — | — | Not re-verified in this pass; Jumpcutter-style silence cutting is irrelevant without speech; LosslessCut is a lossless trimmer, not a selector | Treat as unverified/likely stale |

**Verdict:** no existing project does quality + moment selection for wordless travel footage. Borrow video-use's "text-first, pixels on demand" pattern and build the shot-log pipeline yourself (~500 lines of Python + one Swift CLI).

### 5. Free metadata (no ML)
| Field | How | Notes |
|---|---|---|
| Duration, fps, VFR | `ffprobe -show_streams`: `r_frame_rate` vs `avg_frame_rate`, `nb_frames` | iPhone is often VFR; PySceneDetect 0.7 handles VFR timestamps correctly |
| Slow-mo (120/240) | fps ≥ 100 in ffprobe; Apple `Keys:FullFrameRatePlaybackIntent` (0 = slow-mo playback intent, 1 = full rate) via exiftool | Conform 120/240 fps to the 30 fps timeline in Resolve |
| HDR / Dolby Vision | ffprobe `color_transfer` (arib-std-b67 = HLG, smpte2084 = PQ), `color_primaries=bt2020`, DOVI side data | Drives tone-map choice for proxy + Resolve color pipeline |
| 10-bit / log | `pix_fmt` (yuv420p10le), `profile`; D-Log M flag not reliably exposed | Fallback: folder naming convention, or flat-histogram heuristic |
| Device | exiftool `Keys:Make/Model/Software` | Routes iPhone vs Osmo handling |
| Creation time & order | exiftool `Keys:CreationDate` (has timezone) vs `QuickTime:CreateDate` (UTC) | Use Keys date for ordering; GPS is out of scope here |
| Rotation / orientation | ffprobe display-matrix side data | Needed for 9:16 framing |
| Stabilization / Cinematic mode / Action mode | Not reliably documented in metadata (not verified) | Infer shake from OpenCV instead |
| Osmo gimbal data | **Not exposed**: DJI forum: "this function is unavailable" for Pocket 3; Gyroflow lists Action 2/4/5, Avata, Neo, O3/O4, not Pocket | Negative finding |

## Section B — Recommended two-tier pipeline

**Tier 0: ingest (local, ~minutes)**
1. Run `ffprobe` + `exiftool -json` → clip header (device, fps, VFR, HDR/log, creation time).
2. Make one proxy per clip: 540×960 H.264 SDR, tone-mapped or LUT'd, audio stripped, encoded with `-hwaccel videotoolbox`. All later steps read the proxy, never the 4K HEVC, which keeps RAM well under 8 GB. Process clips sequentially, not in parallel.

**Tier 1: local metrics (free, ~5–10 min per walk; rough estimate, not benchmarked)**
3. Run one ffmpeg pass per proxy: `signalstats,blurdetect,scdet` with `metadata=print:file=` → per-frame values → aggregate per second.
4. OpenCV global motion at 10 fps → shake, direction, pace.
5. Swift CLI with Apple Vision at 1 fps → aesthetics + faces. YOLO26n `track()` at 3 fps → person tracks/events.
6. Score each 1 s bin:
   - Usable = not (shake > T, blur in worst 20% of clip, clip_hi > 2%, scd spike).
   - `quality = 0.35·aes + 0.25·sharp + 0.2·stability + 0.2·exposure`.
   - Slide 2–5 s windows → top 3 local candidates per clip, with reasons.

**Tier 2: vision LLM (cloud)**
7. Gemini 3.5 Flash-Lite, Files API, `fps=2`, default resolution, structured JSON output. Prompt includes the Tier-1 candidate windows and flags.
   - It returns: description, mood, subjects, overlay-text ideas, hook potential (0–10), confirmation or rejection of each candidate, and up to 2 new candidates.
   - Snap all returned times to local metric boundaries (LLM timestamps are coarse).
8. Optional: one Gemini 3.8 Flash or Claude call over contact sheets of the ~15 shortlisted moments → hook choice + ordering for cut matching (e.g. forward-walk → forward-walk, pan-left → pan-left).
9. Claude Code writes the Script from the shot logs and builds the Resolve timeline. It also adds Resolve markers at candidates for your review.

**Cost for one walk (60 clips × 20 s = 20 min of footage)**
| Item | Assumptions | Cost |
|---|---|---|
| Tier 0–1 local | M2 CPU/ANE | $0 |
| Gemini 3.5 Flash-Lite, 1 fps, default | 1,200 frames × 70 = 84K + 36K prompt = 120K in × $0.30/M; ~132K out+thinking × $2.50/M | ≈ $0.04 + $0.33 = **~$0.37** (Batch ≈ $0.18) |
| Same at 2 fps, high res | 2,400 × 280 = 672K + 36K in; same output | **~$0.54** |
| Gemini 3.8 Flash, 1 fps | 120K × $0.75/M + 132K × $3.75/M | **~$0.59** (≈ $1.18 after Jan 1, 2027) |
| Claude second opinion | 15 contact sheets × 1,600 tokens on Sonnet 5 ($2/M input, confirmed in Anthropic's Sonnet 5 announcement) | **~$0.05** |
| Alternative: TwelveLabs | 20 min × ($0.042 + $0.0292) | **~$1.42** + output |

Output/thinking tokens, not video, dominate Gemini cost, so cap thinking budget and keep JSON terse. Free tier exists but per Google's pricing page, free-tier content is used to improve their products. Use the paid tier for personal footage.

## Section C — Proposed JSON shot-log schema (one file per clip)

```json
{
  "schema": "reel-shotlog/1.0",
  "clip": {
    "id": "IMG_4821", "path": "src/IMG_4821.MOV", "proxy": "proxy/IMG_4821_540.mp4",
    "device": {"make": "Apple", "model": "iPhone 15 Pro"},
    "created": "2026-09-14T17:42:10+02:00",
    "duration_s": 21.4, "fps": 59.94, "vfr": true, "slowmo": false,
    "color": {"transfer": "arib-std-b67", "primaries": "bt2020", "dolby_vision": true, "bit_depth": 10, "log": null},
    "orientation": "portrait"
  },
  "per_second": {
    "t": [0,1,2],
    "luma_mean": [0.41,0.43,0.44], "clip_hi_pct": [0.2,0.4,3.1], "clip_lo_pct": [0.0,0.0,0.1],
    "blur": [0.21,0.18,0.35], "shake_px": [1.2,0.9,4.8], "roll_deg": [0.1,0.1,0.6],
    "motion": [{"type":"forward","speed":0.06,"dx":0.00,"div":0.12}],
    "aes": [0.32,0.41,0.12], "persons": [0,1,3], "max_person_h": [0,0.18,0.52], "scd_score": [0.4,0.6,9.8]
  },
  "events": [
    {"t": 1.6, "type": "person_enter", "track": 7, "side": "left"},
    {"t": 2.3, "type": "stranger_closeup", "track": 9, "box_h": 0.52}
  ],
  "segments": [
    {"id": "s1", "in_s": 4.0, "out_s": 7.5, "source": ["local","gemini"],
     "scores": {"quality": 0.78, "aes": 0.44, "stability": 0.9, "exposure": 0.95, "hook": 7},
     "tags": ["golden_hour","archway","forward_walk","no_people"],
     "motion": {"type": "forward", "pace": "slow", "dir_in": "center", "dir_out": "center"},
     "flags": [], "reason": "steady push through arch, light flare at 6.2s"}
  ],
  "rejects": [{"in_s": 9.0, "out_s": 12.0, "why": ["shake_px>4","clip_hi>2%"]}],
  "llm": {
    "model": "gemini-3.5-flash-lite", "fps": 2, "prompt_ver": "v3",
    "description": "Slow walk through a stone archway into a sunlit square...",
    "subjects": ["archway","café terraces"], "mood": "warm, calm",
    "overlay_ideas": ["Built in the 1500s"], "hook_potential": 7
  },
  "provenance": {"tool_versions": {"ffmpeg": "8.x", "ultralytics": "8.4.175", "scenedetect": "0.7.1"}, "created": "2026-10-10T12:00:00Z"}
}
```

**Standards:**
- **Adopt OTIO for interchange, not as the primary store.** OTIO 0.18.1 (Nov 2025, macOS arm64 wheels) lets you nest the shot log under `clip.metadata["reelagent"]` (OTIO's convention is namespaced sub-dictionaries). Express `segments` as OTIO `Marker`s (`marked_range`, `color`, `name`, plus the `comment` field added to Marker). Note that file-format adapters moved to the separate `opentimelineio-plugins` package.
- **Mirror candidates as Resolve markers** via the scripting API so you can review them on the timeline.
- **EBU Core / Frame.io schemas:** not researched in depth. They are heavyweight and archive- or review-oriented, with no benefit for an agent-only pipeline.

## Section D — Still unsolved or unreliable in 2026
- **Precise timing from LLMs.** Gemini samples at 1 fps by default, and agentic mode's "sub-second moment retrieval" is Google's claim, not independently verified. A Qwen3-VL issue reports timestamps drifting from the real timeline. Always snap to local metrics.
- **"Best moment" taste.** There is no benchmark for travel/short-form moment quality. Aesthetic models (NIMA, LAION-aes) are trained on still photos (AVA). Apple's score is a black box. Expect to override about a third of picks; log your overrides and use them as few-shot examples.
- **Metrics on HDR/log.** Exposure and blur thresholds only mean something on a consistently tone-mapped proxy. D-Log M detection from metadata is unreliable.
- **Shake ground truth.** No gyro data from the Osmo Pocket, and none usable from the iPhone camera app. Optical-flow shake is confused by moving crowds and by strong parallax in forward walks.
- **People semantics.** Detectors find people but can't tell "stranger who ruins the shot" from "nice street life". Face-size thresholds are a crude proxy. Identity/consent questions remain manual.
- **Pricing and doc drift.** Gemini token-per-frame figures depend on model generation (70/280 for Gemini 3 per Google's Gemini 3 guide; 66/258 for "models earlier than Gemini 3" per the Gemini Enterprise video docs), so budget by model. 3.8 Flash pricing doubles on Jan 1, 2027. Pegasus pricing differs by version. Re-check before each billing month.
- **Local video LLMs on 8 GB.** Not practical. Even 4B VLMs on MLX can't hold multi-frame video context comfortably.

## Caveats
- Latency and runtime numbers are engineering estimates, not benchmarks on your M2.
- Claude Sonnet 5's $2/M input price is confirmed by Anthropic's Sonnet 5 announcement; the Opus 5 $5/M price comes from a third-party review and is unverified.
- The ShortGPT/Jumpcutter/Vidio/Clipper rows and the iPhone Cinematic/Action-mode metadata were not re-verified in this pass.
- Ultralytics is AGPL-3.0. That is fine for a personal pipeline, but the license spreads to any code you distribute with it.
