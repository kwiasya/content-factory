# Color Pipeline for Mixed iPhone + DJI Osmo Pocket Reels in DaVinci Resolve Studio 21.1.1

> Источник: deep research, принесён пользователем 2026-10-10. Инструмент (ChatGPT / Claude) не указан, переименовать файл когда станет известно. Проверка по стабу API: см. `verification.md` рядом.

Use one DaVinci YRGB Color Managed project with a wide-gamut working space, tag every clip's input color space by script based on ffprobe/exiftool metadata, deliver SDR Rec.709 tagged 1-1-1 (Rec.709-A on macOS), and add your "travel look" as one shared node or LUT after normalization. The one thing that won't automate cleanly is DJI Osmo Pocket 3 D-Log M: the file doesn't identify itself and Resolve has no color space for it.

## TL;DR

- **Detection:** iPhone HDR is easy to detect. ffprobe shows `color_transfer=arib-std-b67` plus a DOVI record with profile 8 and `dv_bl_signal_compatibility_id=4`. Pocket 4/4P writes `com.dji.camera.ColorGammaSxS`. Pocket 3 writes no profile field, and every DJI clip carries BT.709 1-1-1 `colr` tags whatever the profile. So Pocket 3 D-Log M has to come from your own convention: a folder, a filename suffix, or a flag in the script.
- **Resolve setup:** project `colorScienceMode = davinciYRGBColorManagedv2`, timeline in DaVinci Wide Gamut / Intermediate, output Rec.709 Gamma 2.4, Deliver gamma tag Rec.709-A. Set per-clip input color space with `MediaPoolItem.SetClipProperty("Input Color Space", …)`. This only works while the project is color managed, and the string must match the dropdown exactly. D-Log M is the exception: tag it Rec.709 (or bypass) and apply DJI's official LUT on node 1 with `Graph.SetLUT`.
- **Delivery:** deliver SDR, not HDR. Instagram does play HDR: Meta Engineering's July 17, 2023 post "Bringing HDR video to Reels" announced HDR uploads to Reels on Facebook and Instagram, and its Nov 17, 2025 post says that "as of June 2025, all of our delivered AV1 encodings derived from iPhone-produced HDR include Dolby Vision metadata" (profile 8.4). But viewers who switch HDR off get Instagram's automatic SDR conversion, and you can't control or check that tone map from an M2 Air. Export H.264 or H.265, 8-bit, 1080x1920, at about 20–25 Mbps. Check it with ffprobe: `bt709/bt709/bt709`, and no DOVI side data.

## Table A — Footage type → detection → Resolve input → scriptable

Run `ffprobe -v error -select_streams v:0 -show_streams -show_entries stream=codec_name,profile,pix_fmt,color_range,color_space,color_transfer,color_primaries:stream_side_data -of json FILE` and `exiftool -a -G1 -ee -u FILE` on each clip.

| Footage type | Exact metadata to detect | Resolve Input Color Space (RCM) | Scriptable? | Sources / confidence |
|---|---|---|---|---|
| iPhone HDR (Dolby Vision 8.4 / HLG, HEVC) | ffprobe: `codec_name=hevc`, `profile=Main 10`, `pix_fmt=yuv420p10le`, `color_space=bt2020nc`, `color_transfer=arib-std-b67`, `color_primaries=bt2020`, side data `DOVI configuration record: profile 8 … dv_bl_signal_compatibility_id=4`. MediaInfo: `HDR format: Dolby Vision, Version 1.0, dvhe.08.06, BL+RPU, HLG compatible`. QuickTime Inspector: Transfer Function `ITU-R BT.2100 (HLG)` | `Rec.2100 HLG (Scene)` or `Rec.2020 HLG ARIB STD-B67` (both scene-referred; forum guidance says plain "Rec.2100 HLG" is display-referred and wrong for camera HLG). Ignore DV RPU for SDR delivery. | Yes: `SetClipProperty('Input Color Space', '<exact dropdown string>')` | immich issue #31053 (2026 ffprobe dump); MacRumors MediaInfo dump; Apple Community; BMD forum t=165221 (older, flag) — **high** |
| iPhone SDR (HEVC/H.264, HDR Video off) | `color_transfer=bt709`, `color_primaries=bt709`, `color_space=bt709`, 8-bit `yuv420p` typical; no DOVI side data | `Rec.709 Gamma 2.4`, or `Rec.709-A` if you enable "Automatically tag Rec.709 Scene clips as Rec.709-A" | Yes, same call | Radiant Media Player (HDR = transfer function rule) — **high** |
| iPhone Apple Log (15 Pro+ ProRes Log) | Codec ProRes (`prores`), primaries BT.2020. Apple's identifier is the Core Video key `kCVImageBufferLogTransferFunctionKey` = `…AppleLog` (`…AppleLog2` on iPhone 17 Pro). **Unverified:** ffprobe likely shows `color_primaries=bt2020` with an unknown/unspecified transfer (ffmpeg cannot even write a log transfer to ProRes). Practical rule: ProRes + BT.2020 + transfer not `arib-std-b67` → Apple Log; confirm with a test file. | Combined preset `Apple Log` (Rec.2020 / Apple Log; built in since Resolve 18.6, whose New Features Guide lists "Support for Apple Log video formats"). Apple Log 2 uses Apple Wide Gamut; davinciresolve21.com (2026) says Resolve "doesn't ship a labeled 'Apple Log 2' entry" in the Input Color Space dropdown. Check your 21.1.1 dropdown. | Yes (preset string) | Apple developer docs (AppleLog identifier); Prolost; Apple Community; Adobe (detects "Apple Log/ Rec 2020") — **medium** |
| DJI Osmo Pocket 3, Normal (8-bit H.264 or 10-bit HEVC) | `colr` nclx 1/1/1 → ffprobe `bt709/bt709/bt709`; no DJI profile key | `Rec.709 Gamma 2.4` | Yes | Pocket 3 spec (Normal 8-bit H.264 / 10-bit H.265); subagent finding, erik-sutton95/dji-clip-color — **medium** |
| DJI Osmo Pocket 3, HLG | 10-bit HEVC; `arib-std-b67` *probably* (unverified) | `Rec.2100 HLG (Scene)` | Yes | Spec sheet; unverified tag — **low** |
| DJI Osmo Pocket 3, D-Log M | **Not detectable from metadata.** 10-bit HEVC `yuv420p10le`, `colr` still BT.709; DJI forum admin: "There are no camera parameters recorded in Osmo Pocket 3 video metadata." 10-bit alone doesn't separate it from HLG. Fall back to your folder or filename convention, or a histogram heuristic (flat, low-contrast luma). | No D-Log M entry exists (DJI never published the curve). Tag `Rec.709 Gamma 2.4` (treat as display-referred) and apply DJI's LUT on node 1, or use the community D-Log M→DWG DCTL. **Never** use `DJI D-Gamut/D-Log`; that's a different curve. | Partially: `SetClipProperty` + `Graph.SetLUT(1, path)` | BMD forum t=202495, t=192412; DJI forum; github.com/erik-sutton95/dji-clip-color — **high that it's undetectable** |
| DJI Osmo Pocket 4 / 4P, D-Log or D-Log2 (10-bit) | exiftool `QuickTime:DjiCameraColorGammaSxS` (key `com.dji.camera.ColorGammaSxS`) = `D-Log`, `D-Log2`, `Rec.709`, or an HLG value; `colr` stays 1/1/1. 4P firmware older than 01.01.65.18 doesn't write the tag. | D-Log → `DJI D-Gamut / DJI D-Log` (native). D-Log2 → `DJI D-Gamut2 / D-Log2` (native in Resolve 21.1). | Yes | COOKIE-9963/DJI_Pocket4P_AutoGrade; MathieuLalonde/Tag-Osmo-Pocket-Clips; Resolve 21.1 notes ("Support for DJI D-Gamut2 and D-Log2") — **high** |
| Any clip, Resolve-side check | `MediaPoolItem.GetClipProperty()` returns the *assigned* `Input Color Space`, not what's in the file. ende.app notes Resolve doesn't read the DJI metadata block. | — | Read: yes | BMD forum t=197441; ende.app — **high** |

**What this means:** detection is reliable for iPhone HDR, iPhone SDR and Pocket 4 clips. It is unreliable for Pocket 3 D-Log M and only medium-confidence for Apple Log. Have the agent write a `clip_manifest.json` with `{file, detected_profile, confidence, source_field}`. When confidence is low, it should ask you, or use a filename convention you apply at offload (e.g. `_DLM`), rather than guess.

## Section B — Recommended pipeline for one mixed timeline

**Step 0. Shooting-side recommendations.** These remove most of the automation risk.
- On the Pocket 3, prefer HLG over D-Log M. HLG is a standard Resolve can transform exactly; D-Log M has no published spec. One BMD forum user's advice: "Avoid D-Log M unless there are no other alternatives."
- If you do shoot D-Log M, keep it in a separate offload folder.

**Step 1. Probe and classify (shell, before Resolve).**
- ffprobe JSON + exiftool for every clip, written to `clip_manifest.json`.
- Also record fps, resolution and rotation. Pocket 3 vertical tops out at 3K 9:16 (1728×3072@24/25/30/48/50/60fps), per DJI's official Osmo Pocket 3 specs.
- Why: Resolve can't detect DJI profiles itself, and your metadata becomes the single source of truth the agent can diff in git.

**Step 2. Create the project with color management set by script.** Order matters: set `colorScienceMode` first.
```python
for k, v in [("colorScienceMode","davinciYRGBColorManagedv2"),
             ("isAutoColorManage","0"),
             ("separateColorSpaceAndGamma","0"),
             ("colorSpaceTimeline","DaVinci WG/Intermediate"),  # exact strings: read back via project.GetSetting()
             ("colorSpaceOutput","Rec.709 Gamma 2.4"),
             ("inputDRT","None"), ("outputDRT","DaVinci"),
             ("timelineResolutionWidth","1080"), ("timelineResolutionHeight","1920"),
             ("timelineFrameRate","30")]:
    assert project.SetSetting(k, v), k
```
- Why use the wide-gamut DWG/Intermediate working space rather than a Rec.709 timeline: HLG and log highlights stay unclipped while you grade, and the output DRT handles the HDR→SDR roll-off once, for every clip.
- Exact setting strings vary by version. Have the agent dump `project.GetSetting()` once from a manually configured project and copy the values.
- Pick 30 fps. Shoot iPhone 60 fps clips for slow motion, or let them conform.

**Step 3. Import, then tag each clip's input color space.**
- Call `SetClipProperty('Input Color Space', value)` per the Table A mapping. Assert that it returns True.
- It returns False if the project isn't color managed or the string doesn't exactly match the dropdown.
- Input Gamma isn't separately settable. Use combined presets such as `Rec.2100 HLG (Scene)` or `Apple Log`, which is why `separateColorSpaceAndGamma=0`.
- Why per-clip tagging instead of CST nodes: one transform per clip, done in one place. That avoids the classic double transform: RCM *plus* a CST or conversion LUT produces "too contrasty and oversaturated" images.

**Step 4. Handle D-Log M (the only LUT-based input).**
- Build the timeline, then for each D-Log M timeline item: `g = item.GetNodeGraph(); g.SetLUT(1, "DJI/OSMO_Pocket3_DLogM_to_Rec709.cube")`.
- Call `project.RefreshLUTList()` first. `SetLUT` only accepts LUTs Resolve has already discovered.
- Because the clip is tagged Rec.709 Gamma 2.4, RCM moves the LUT's Rec.709 output into DWG.
- Trade-off: DJI's LUT clips highlights to Rec.709 *before* your grade. If you need the extra latitude, use the community "Pocket 3 D-Log M → DWG" DCTL (thatcherfreeman/dwg-transforms) with the clip set to bypass. Note that it's reverse-engineered, not DJI-official.
- Pocket 4 D-Log/D-Log2 needs **no LUT**: tag it natively.

**Step 5. Dolby Vision metadata.**
- Ignore it. For SDR delivery you're using the HLG base layer (that's what profile 8.4 means), so the RPU is irrelevant.
- Don't enable Dolby Vision mastering in the project. Resolve 21.1's new per-format MultiMaster trims are for HDR deliverables you aren't making.
- Blackmagic's Resolve 20.2 New Features Guide (Sept 2025) states that RCM and CST "now use ITU BT.2408 for HLG and PQ conversion." HLG→SDR is now more consistent than in the older forum threads.

**Step 6. Normalize clips (per-clip node 2).**
- Run auto exposure and white-balance balancing, then optional matching (see Table C and the exposure section).
- Push the results as CDL values or DRX grades.

**Step 7. Apply the look once.**
- Put the creative look on a **shared node after normalization**. Options:
  - a Timeline-level node graph;
  - a group post-clip node;
  - the same `.drx` applied to all items with `Timeline.ApplyGradeFromDRX(path, 0, items)`.
- Resolve 21.1.1 adds an option to apply a DRX across all node layers.
- Use LUTs designed for Rec.709 input only if the node runs in Rec.709. In a DWG timeline, use DWG-aware tools instead: Film Look Creator, or a look LUT wrapped between CSTs.

**Step 8. Review in Resolve.**
- On the M2 Air, enable "Use Mac display color profiles for viewers" so the viewer matches what QuickTime and Instagram will show.

**Step 9. Render.**
- Use the Section D settings, then run the verification script before upload.

**Why this order:** detect → tag → (only D-Log M gets a LUT) → normalize → one look → one output transform. Every clip is converted exactly once, the agent can audit every transform as data, and you only tweak nodes 2 and later by hand.

## Table C — Grading, LUT and matching tools

| Tool | Link | License / cost | Last release / maturity | Agent-callable? | Verdict |
|---|---|---|---|---|---|
| Resolve Studio 21.1.1 Python API | Resolve Developer/Scripting README (local) | Included in Studio ($295) | 21.1.1 (Oct 2026); active | Yes. External Python access is Studio-only in 21.1. `SetClipProperty`, `Graph.SetLUT/GetLUT`, `SetCDL`, `ApplyGradeFromDRX`, `CopyGrades`, grade-to-LUT export; 21.1.1 adds async APIs (Smart Reframe, scene cut detection) | **Core. Use it.** |
| Resolve 21.1 built-in MCP server | File > Setup AI Assistants (manual p. 4,318) | Studio | Sept 2026; new | Yes; detects Claude Code. Blackmagic has published no fetchable tool list. | **Try it.** Fall back to raw API for color-management settings. |
| samuelgursky/davinci-resolve-mcp | github.com/samuelgursky/davinci-resolve-mcp | Open source (MIT per listing); free | Active 2026; covers node graph, LUT, DRX, CDL | MCP (stdio) | Good alternative. One listing says it requires **Python 3.10/3.11** because Resolve's module imports `imp` (removed in 3.12). Test this with your 3.12 venv. |
| Resolve Shot Match / Color Match chart / Auto Color (UI) | Resolve manual | Included | Mature | **No documented API call** in the scripting docs reviewed | Use manually during your review pass. Don't plan the agent around it. |
| DJI official D-Log M → Rec.709 LUT (Pocket 3) | dji.com/lut | Free | v1.0, 2023-10-25 (stable; flag age) | `.cube` via `Graph.SetLUT` | **Required for Pocket 3 D-Log M.** |
| DJI Pocket 4P D-Log → Rec.709 V2.0 LUT | dji.com/lut (Pocket 4P downloads) | Free | 2026 | `.cube` | Not needed in RCM; use native D-Gamut/D-Log tagging. |
| color-matcher (hahnec) | github.com/hahnec/color-matcher, pypi `color-matcher` | GPL-3.0, free | 0.6.0, Mar 30 2025; single maintainer, slow | Python lib / CLI (`hm`, `reinhard`, `mvgd`, `mkl`, `hm-mvgd-hm`) | **Useful offline.** Match a midpoint still from each clip to a hero still, then fit a 3×3 matrix and offsets for Resolve CDL or a 33-point `.cube`. Light enough for 8 GB. GPL is fine for a private tool. |
| OpenCV / NumPy (gray-world WB, LAB stats) | opencv.org | Apache-2.0, free | Active | Python | DIY per-clip WB/exposure stats on downscaled frames. |
| Colourlab AI | colourlab.ai/colourlab-ai-for-davinci-resolve | Creator $29/mo or $290/yr; Pro $49/mo or $490/yr (vendor page; third-party prices conflict: $14–15/mo) | Active 2026 | Plugin + desktop app; **no public API found** | Best-in-class shot matching, but GUI-driven. Use it only if manual matching becomes the bottleneck. |
| Dehancer, fylm.ai, FilmConvert | vendor sites | Paid (not verified in this pass) | Active | OFX / web; no API confirmed | Good film emulation for *you* to use. Not agent-callable; skip for automation. |
| Resolve Film Look Creator + Film Grain/Halation (built-in) | Resolve FX | Included | Active; 21.1 adds Film Grain softness controls | Applied via a saved DRX (build once by hand, then apply by script) | **Recommended look engine.** Free, DWG-aware, reproducible via DRX. |
| Community D-Log M → DWG DCTL | github.com/thatcherfreeman/dwg-transforms | Open source | Community; reverse-engineered | DCTL in node (via DRX) | Optional for D-Log M latitude; not official. |

**Look design guidance.**
- The usual travel-film look is: normalize → warm/teal split via Film Look Creator or a print-film emulation → subtle halation → fine grain → gentle vignette.
- Build it **once by hand** in Resolve, save it as a still/DRX in the repo (`looks/travel_v1.drx`), and let the agent only apply it. That's more consistent than stacking third-party creative LUTs, which assume a specific input.
- Most cheap "D-Log M cinematic LUT packs" (Gumroad etc.) expect raw D-Log M input and conflict with the RCM pipeline. Avoid them.
- Per clip by script: `item.GetNodeGraph().SetLUT(n, path)`.
- Timeline-wide: apply the same DRX to all items, or place the look in a group post-clip/timeline node.
- Note that `TimelineItem.SetLUT` is deprecated in favor of `Graph.SetLUT`.

## Exposure and white balance at scale (item 7)

| Task | Method | Agent-callable |
|---|---|---|
| Clipped highlights | Extract about 5 frames per clip at low resolution with ffmpeg *after* a quick tone map, or use the Resolve-rendered still. Compute % of pixels at code values ≥ 235 (8-bit) or ≥ 940 (10-bit) per channel with NumPy. ffmpeg's `signalstats` filter (YMAX/YHIGH) is a no-Python alternative. Flag clips above a threshold for you instead of "fixing" them; clipped data can't be recovered. | Yes (shell/Python) |
| Mixed white balance | Compute a/b means in LAB on normalized stills. Gray-world or a hero-matched offset → Resolve `SetCDL` (slope/offset per channel) on node 2. | Yes |
| Exposure mismatch | Match median luma in the normalized space to a target (e.g. scene-referred mid-grey around 0.18 linear equivalent); write it as CDL offset. | Yes |
| Final polish | Resolve Shot Match / Color Match in the UI during your review | Manual |

**Practical verdict:** automate *measurement* and a first CDL correction. Leave subjective matching to your review pass. It's cheap on 8 GB if the agent works on 540-px stills, not full 4K decodes.

## Section D — Instagram export settings and macOS gotchas

**Instagram HDR status (2026).**
- Meta has supported HDR uploads to Reels since 2023 ("Bringing HDR video to Reels," Engineering at Meta, July 17, 2023: "Meta has made it possible for people to upload high dynamic range (HDR) videos from their phone's camera roll to Reels on Facebook and Instagram").
- Since June 2025, "all of our delivered AV1 encodings derived from iPhone-produced HDR include Dolby Vision metadata." Instagram iOS is the first Meta app supporting Dolby Vision 8.4, where ".4 means cross-compatible with HLG" (Meta Engineering, Nov 17 2025).
- Instagram Edits lead Tom Bender wrote on Threads that viewers "can turn it off in Instagram settings (we automatically convert your content to SDR for these viewers)."
- Secondary sources (2026) say HLG triggers HDR playback while PQ uploads tend to play as SDR, and HDR renditions can take a day or two to appear.
- **Recommendation:** deliver SDR Rec.709. Your source mix includes D-Log M and SDR clips, HDR grading needs an HDR reference you don't have, and Instagram's SDR fallback tone map is outside your control. Revisit HDR only for all-iPhone-HDR reels.

| Setting | Value | Reason / source |
|---|---|---|
| Resolution / AR | 1080×1920 (or 1440×2560) | Your target. Edits lead Tom Bender on Threads: "Edits supports HD (1080x1920), 2K (1440x2560), and 4K (2160x3840). I recommend filming and exporting at 2K." Optional upgrade. |
| Frame rate | 30 fps (≤ 60) | Meta spec cited in a 2026 integration PR: 23–60 fps |
| Codec | H.264 High, 8-bit 4:2:0, or H.265 8-bit | 4:2:0 required per the same spec. M2 hardware encoders are fast and light on RAM. |
| Bitrate | about 20–25 Mbps VBR | Secondary 2026 guide cites a 25 Mbps cap; Instagram re-encodes anyway |
| Audio | AAC, 48 kHz, stereo | Meta spec: AAC, ≤ 48 kHz, 1–2 channels |
| Color Space Tag | Rec.709 | — |
| Gamma Tag | **Rec.709-A** (timeline/output stays Rec.709 Gamma 2.4) | Writes NCLC **1-1-1**. A plain Gamma 2.4 export is tagged **1-2-1** (transfer "Unspecified") and looks washed out or shifted in QuickTime/ColorSync and on platforms that assume 1-1-1. |
| Data levels | Video (limited) | Avoid the full-range `yuvj420p` trap |
| Scripted render | `project.SetRenderSettings({... "ColorSpaceTag": ..., "GammaTag": ...})`, then `AddRenderJob()` / `StartRendering()` | Gist API reference (v20.3, Apr 2026). Verify the exact tag strings by reading back a manually saved preset. |

**Verify before upload (agent step):**
```
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,pix_fmt,color_range,color_space,color_transfer,color_primaries,width,height,r_frame_rate -of json out.mp4
```
- Pass when: `color_primaries=bt709`, `color_transfer=bt709`, `color_space=bt709`, `color_range=tv`, `pix_fmt=yuv420p`, 1080×1920, no DOVI side data.
- Cross-check with MediaInfo or the QuickTime Inspector: "Code Points: (1-1-1)".
- If tags are wrong, you can re-tag without re-encoding the image via ffmpeg bitstream filters (`h264_metadata` / `hevc_metadata`). Fix the Resolve preset rather than relying on this.

**macOS gotchas.**
1. **1-1-1 vs 1-2-1 gamma shift.** Rec.709-A dates from Resolve 16.2.2 and the core guides are from 2020–2021 (flag: older, but the behavior persists in 2026 guides). Rec.709-A as a *timeline* space means grading to about 1.96 gamma; use it only as the output tag.
2. **Viewer mismatch.** Enable "Use Mac display color profiles for viewers." Optionally enable "Automatically tag Rec.709 Scene clips as Rec.709-A" for SDR iPhone input; it affects import only, not export.
3. **Washed-out iPhone HDR.** Caused by treating HLG as Rec.709, or by Instagram/ffmpeg tone mapping. Fix it by tagging HLG correctly in RCM and always delivering SDR you rendered yourself.
4. **Double transform.** RCM tagging plus a CST or conversion LUT on the same clip. Rule: exactly one input transform per clip.
5. **Wrong DJI preset.** Resolve's `DJI D-Log` applied to D-Log M gives oversaturated blues.
6. **AirDrop.** AirDropping HDR to older Apple devices can silently convert it to SDR. Copy originals by cable or Image Capture.
7. **Python 3.12.** Some Resolve MCP wrappers report the scripting module needing `imp`; pin a 3.11 venv if the import fails.

## Caveats

- Several values are **unverified against real files** and should be confirmed with one sample of each type before you trust the classifier: Apple Log ffprobe output, Pocket 3 HLG transfer tag, and the exact Resolve dropdown and render-tag strings in 21.1.1.
- Many Instagram spec details (25 Mbps cap, HLG-vs-PQ behavior) come from secondary 2026 guides, not Meta documentation. Meta publishes no organic Reels file spec.
- Colourlab pricing conflicts across sources; the vendor page values are used. Dehancer, fylm.ai and FilmConvert pricing was not verified.
- Resolve 21.1's built-in MCP is new and its tool surface is undocumented publicly. Keep the raw Python API path as the reliable baseline.
