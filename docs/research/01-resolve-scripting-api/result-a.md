# DaVinci Resolve Studio 21.x Scripting API as a Tool for an AI Agent (macOS, Oct 2026)

> Источник: deep research, принесён пользователем 2026-10-10. Инструмент (ChatGPT / Claude) не указан, переименовать файл когда станет известно. Проверка по локальному стабу: см. `verification.md` рядом.

Resolve Studio 21.1.x can be driven by an external Python script well enough to build the whole first cut of a Reel. That covers import, a 1080x1920 timeline, clips with in/out points, transform and crop, LUTs and CDLs, Text+ titles through Fusion, and rendering. As of 21.1 it also covers transitions, fades, speed changes and audio normalization. What it still can't do is behave like a human editor: there's no trim, slip or blade, no move for a clip already on the timeline, no Fairlight mixing, no Resolve FX parameters, and almost no grade read-back. The architecture that holds up is to have the agent generate a timeline plan, rebuild the timeline from scratch whenever it changes, and leave the finishing work to you in the GUI.

## TL;DR
- **What works:** about 80% of an assembly-style Reel. Media Pool, timeline creation with source in/out and `recordFrame` placement, Inspector transform and crop, LUT/CDL/DRX grades, Fusion Text+ overlays, and the render queue are all solid. Resolve 21.1 (8 Sep 2026) added about 20 APIs, including `TimelineItem.AddTransition`, `Get/SetFades`, `SetSpeed`, `NormalizeAudioLevel` and `MediaPoolItem.GetTranscription`. Resolve 21.1.1 added asynchronous calls for Quick Export, transcription, scene cut detection, Smart Reframe and subtitles.
- **What doesn't work:** editing an existing timeline item (trim, slip, move, razor), Fairlight volume automation, EQ and effects, adding or adjusting Resolve FX on a clip, reading grades back, IntelliScript, the AI Music Editor/Extender, and the AI Audio Assistant. Return values are unreliable: True doesn't mean everything applied, and False doesn't mean nothing did. Treat every write as unverified until you read it back or render it.
- **Recommendation:** Claude Code should drive your own thin Python layer, typed against the 21.1 `DaVinciResolveScript.pyi` stub. Treat timelines as immutable: rebuild from a JSON plan rather than patching. Use samuelgursky/davinci-resolve-mcp, or Blackmagic's native 21.1 MCP server, only as an exploration and debugging aid, not as the production path. Do the per-clip color management and the ffprobe metadata parsing yourself.

## Key Findings

### Table A: Feature × scriptable × API call / workaround

The API is documented in the README that ships with Resolve (Help > Documentation > Developer). In 21.1 the plain `README.txt` was replaced by `README.md`, a typed `DaVinciResolveScript.pyi` and a `CHANGELOG.md`. Public mirrors include the X-Raym gist (https://gist.github.com/X-Raym/2f2bf453fc481b9cca624d7ca0e19de8, current to v21.0.4) and the mhadifilms v20.3 reference (https://gist.github.com/mhadifilms/2b84d469135315793220dbf2226cbe63).

| Area | Feature | Scriptable | API call / workaround | Source |
|---|---|---|---|---|
| Media Pool | Import files / image sequences | Yes | `MediaPool.ImportMedia([paths])`, `MediaStorage.AddItemListToMediaPool` | mhadifilms gist |
| Media Pool | Bins/folders | Yes | `AddSubFolder`, `SetCurrentFolder`, `MoveClips` | mhadifilms gist |
| Media Pool | Metadata read/write | Yes | `GetClipProperty()`, `SetClipProperty`, `Get/SetMetadata`, markers with `customData` | mhadifilms gist; wildlion.media guide |
| Media Pool | Proxies / relink | Yes | Link and unlink proxies, `RelinkClips`, `ReplaceClip`; 21.0.4 relinks proxies across formats | wildlion.media; newsshooter 21.0.4 |
| Media Pool | Per-clip input color space | Partial | `SetClipProperty("Input Color Space", …)`. Gamma isn't exposed separately; one workaround toggles `separateColorSpaceAndGamma`. The value string must match the dropdown exactly. | mhadifilms gist §5.4 |
| Media Pool | Per-clip LUT (clip attribute) | Partial | Apply on a node instead: `TimelineItem.SetLUT(nodeIndex, path)` or `NodeGraph.SetLUT`. Run `Project.RefreshLUTList` first. | electron-rotoscope docs |
| Edit | Create timeline | Yes | `CreateEmptyTimeline`, `CreateTimelineFromClips(name, [clipInfo])` | X-Raym gist |
| Edit | Append with in/out and position | Yes | `AppendToTimeline([{mediaPoolItem, startFrame, endFrame, trackIndex, recordFrame, mediaType}])` | mhadifilms gist |
| Edit | Move/trim/slip/razor an existing clip | **No** | Getters only (`GetStart`, `GetEnd`, `GetLeftOffset`…). Workaround: delete and re-append, which loses grades and markers, so rebuild instead. | wildlion.media; pilotcut.com |
| Edit | Transform/crop/zoom (Inspector) | Yes | `SetProperty("ZoomX"/"Pan"/"Tilt"/"RotationAngle"/"CropTop"…/"Opacity"/"Scaling"/"RetimeProcess")`. 21.1 adds more Inspector keys. | ResolveDevDoc; Digital Production 21.1 |
| Edit | Transitions | Partial (21.1+) | `TimelineItem.AddTransition({...})`. "Cross Dissolve" is confirmed working; "Dip to Color" and "Fade" returned `None` on 21.1.0 in one community test. Read-back is thin. | newsshooter 21.1; danielbaldwin47/resolve-mcp #268; vedanthvdev/resolve-template #2 |
| Edit | Fades (clip handles) | Partial (21.1+) | `TimelineItem.SetFades({FadeIn, FadeOut})` / `GetFades()`. They render correctly, but one report says they didn't survive project export/import. | vedanthvdev/resolve-template #1; samuelgursky PR #208 |
| Edit | Speed change | Partial (21.1+) | `TimelineItem.SetSpeed({..., RippleTimeline})`. A 50% change was verified on 21.1.0.14; reverse, freeze and speed ramps are untested. Retime curves are not scriptable. | samuelgursky PR #208 |
| Edit | Markers | Yes | `AddMarker(frame, color, name, note, dur, customData)` on timeline, item or clip | mhadifilms gist |
| Edit | Compound / Fusion clips | Yes | `CreateCompoundClip`, `CreateFusionClip` | electron-rotoscope docs |
| Edit | Adjustment clips | Partial | No dedicated call. Insert via generator/title calls or a pre-made template; 21.1 allows transitions on adjustment clips in the GUI. | newsshooter 21.1 |
| Edit | Text+ titles | Yes | `InsertFusionTitleIntoTimeline("Text+")`, then `GetFusionCompByIndex(1)` → tool → `SetInput("StyledText", …)`. Built-in Fusion titles such as "Call Out" have failed to insert in community tests. | Blackmagic forum t=198110, t=224452 |
| Edit | Subtitles | Partial | `CreateSubtitlesFromAudio({settings})`. No per-subtitle text or timing setter. | X-Raym v21.0; pilotcut.com |
| Edit | Selection-aware tools | Yes (21.0.4+) | `Timeline.GetSelectedClips()`, which also returns linked audio items | wildlion.media 21.0.4 |
| Fusion | Create/modify comps | Yes | `AddFusionComp`, `ImportFusionComp(.setting)`, `ExportFusionComp`; Fusion `comp.AddTool`, `SetInput`, `ConnectInput` | mhadifilms gist §11; forum t=198110 |
| Fusion | Insert your own macro/.setting template | Partial | `ImportFusionComp(path)` onto a Fusion composition item works. Inserting a custom Edit-page title by name is unreliable; one tester reports only built-in presets work. | StoryToolkitAI #14 |
| Fusion | `fu.GetCurrentComp()` | Gotcha | Returns `None` until the Fusion page has been opened in the session | wildlion.media |
| Color | Apply LUT | Yes | `SetLUT(nodeIndex, path)`, `GetLUT` | wildlion.media |
| Color | Apply grade | Yes | `NodeGraph.ApplyGradeFromDRX(path, mode)`. 21.1.1 adds an "all node layers" option. | mhadifilms gist; Digital Production 21.1.1 |
| Color | CDL | Write-only | `SetCDL({...})`. There is no `GetCDL`. | wildlion.media |
| Color | Wheels, curves, qualifiers, windows, creating nodes | **No** | Use a pre-built DRX or PowerGrade still, or a DCTL/LUT on a node | wildlion.media |
| Color | Copy grades / color groups / versions | Yes | `CopyGrades([items])`, `AddColorGroup`, `AddVersion` | mhadifilms gist §12 |
| Color | Stills/PowerGrades | Partial | `GrabStill`, `ExportStills`, PowerGrade albums. Applying a PowerGrade means going through a DRX. | mhadifilms gist §13 |
| Color | Magic Mask | Partial | `CreateMagicMask("F"/"B"/"BI")`; direction is the only control | wildlion.media |
| Fairlight | Volume / pan / EQ / automation / FairlightFX | **No** | 21.1 adds Inspector audio properties (`AudioVolume`/`AudioPan` names reported). Mixer, automation and effects stay GUI-only. | wildlion.media; samuelgursky #207 |
| Fairlight | Normalize | Yes (21.1+) | `NormalizeAudioLevel({normalizationMode, targetLevel, targetLoudness, setLevelMode})` (LKFS or dBFS) | samuelgursky v4.4.2 release notes |
| Fairlight | Fairlight presets | Partial | `GetFairlightPresets`, `ApplyFairlightPresetToCurrentTimeline` | mhadifilms gist §14.4 |
| Fairlight | Voice Isolation | Yes | `Get/SetVoiceIsolationState(track, {...})` | mhadifilms gist §14.2 |
| Deliver | Render settings, custom 1080x1920 | Yes | `SetCurrentRenderFormatAndCodec("mp4","H264"/"H265")`, `SetRenderSettings({FormatWidth:1080, FormatHeight:1920, …})`. 21.0.4 adds `Encoder`, `AddFrameHandles`, `UseFullExtents`, `DataBurnIn`. | mhadifilms gist §9; wildlion.media 21.0.4 |
| Deliver | Presets | Yes | `LoadRenderPreset`, `SaveAsNewRenderPreset`, `ImportRenderPreset`; 21.1 adds updating presets | mhadifilms gist; newsshooter 21.1 |
| Deliver | Queue and progress | Yes | `AddRenderJob` → `StartRendering([id])` → poll `GetRenderJobStatus` (`CompletionPercentage`, `JobStatus`) | mhadifilms gist §9.3 |
| Deliver | Quick Export | Yes | `RenderWithQuickExport(preset, {...})`; async variant in 21.1.1 | X-Raym gist; Digital Production 21.1.1 |
| Project | Resolution/fps/vertical | Yes | `Project.SetSetting("timelineResolutionWidth","1080")`… For a per-timeline override, call `Timeline.SetSetting("useCustomSettings","1")` first. Set fps before adding media. | Blackmagic forum t=231314 |
| Project | Color management | Yes | `SetSetting("colorScienceMode","davinciYRGBColorManagedv2")` first, then the color space keys in order | mhadifilms gist §5.3 |
| Project | Setting presets | Yes (21.1+) | Create/update/delete/import/export project setting presets | newsshooter 21.1 |
| Interchange | Import FCPXML/AAF/EDL/OTIO/DRT | Yes | `MediaPool.ImportTimelineFromFile(path, {timelineName, importSourceClips, sourceClipsPath})` | wildlion.media; mhadifilms gist |
| Interchange | Export timeline | Yes | `Timeline.Export(path, resolve.EXPORT_FCPXML_1_10 / EXPORT_OTIO / EXPORT_DRT …)` | mhadifilms gist §10 |
| AI | Scene Cut Detection | Yes | `Timeline.DetectSceneCuts()`, no parameters | wiki.dvresolve.com |
| AI | Smart Reframe | Partial | `TimelineItem.SmartReframe()`. Needs the right aspect-ratio setup and has no parameters. | samuelgursky api-coverage |
| AI | Transcription | Yes | `TranscribeAudio(useSpeakerDetection)`; read back with `GetTranscription()` (21.1+). Set the language first, or it gets auto-detected wrongly. | X-Raym; samuelgursky #207 |
| AI | IntelliScript / AI Music Editor / AI Audio Assistant / Dialogue Matcher | **No** | GUI only | wildlion.media |
| AI | Resolve FX on an existing clip | **No** | You can only insert an OFX generator as a new clip (`InsertOFXGeneratorIntoTimeline`) | wildlion.media |

### Table B: Ecosystem projects

| Name | Link | License / price | What it adds | Last activity | Resolve tested | How the agent calls it | Verdict |
|---|---|---|---|---|---|---|---|
| Blackmagic native MCP | Built into Studio 21.1 (File > Setup AI Assistants) | Included with Studio ($295) | Official MCP server; registers itself in Claude Code. Tool list is regenerated per build and published nowhere. | 21.1 (Sep 2026) | 21.1 | MCP (stdio) | Good for ad-hoc chat; opaque, so don't build on it |
| samuelgursky/davinci-resolve-mcp | https://github.com/samuelgursky/davinci-resolve-mcp | MIT, free | 35 compound / 353 granular tools, 361/361 methods covered, guarded workflows, plus an offline "advanced" Node server for .drp/.drt/.drx editing. About 2.2k stars. | v4.8.23 released 30 Sep 2026; active | 19.1.3, 20.3.2, 21.0.2 Studio; 21.1 bug reports handled | MCP, Python 3.10+ | Best third-party option; use it as an API oracle and helper |
| DigitalWorkflowCompany/resolve-mcp | https://github.com/DigitalWorkflowCompany/resolve-mcp | MIT | 88 tools / 20 resources for 21.0 AI calls, dailies workflows | 2 commits; described as "dead" in danielbaldwin47 #263 | 21 | MCP | Skip |
| wassermanproductions/unofficial-davinci-mcp | https://github.com/wassermanproductions/unofficial-davinci-mcp | Apache-2.0 | Live Studio control plus FCPXML fallback, beat grid (librosa), EBU R128 loudness, color-match → .cube | 27 commits, 2026 | "Verified on Studio 21" | MCP, pip | Worth mining for its beat-cut and loudness engines |
| lordhoell/davinci-resolve-mcp | https://github.com/lordhoell/davinci-resolve-mcp | — | 440+ tools plus a Claude Code skill | Based on the 20.2.2 API | 19+ | MCP | Outdated for 21.1 |
| apvlv/davinci-resolve-mcp | https://github.com/apvlv/davinci-resolve-mcp | — | Basic project/timeline/Fusion helpers plus `execute_python` | — | unspecified | MCP | Too thin |
| pydavinci | https://github.com/pedrolabonia/pydavinci | open source | Pythonic wrapper with Pydantic settings | Updated 2026 per awesome list, but the pip release targets Resolve 17 | 18 | Python lib | Stale against 21.x; skip |
| pybmd | https://github.com/WheheoHu/pybmd | — | Wrapper with auto-start of Resolve | Updated 2026 | — | Python lib | Optional |
| fusionscript-stubs | https://github.com/czukowski/fusionscript-stubs | free, PyPI | Type hints generated from the README | Stubs based on the 8 May 2026 (21.0) docs | 21.0 | `pip install fusionscript-stubs` | Use the official 21.1 `.pyi` instead |
| OpenTimelineIO + otio-fcpx-xml-adapter | https://github.com/OpenTimelineIO/otio-fcpx-xml-adapter | Apache-2.0 | Generate timelines in code. Transitions, effects and speed are **not** supported by the FCPX adapter. | — | Resolve imports .otio natively | Python lib | Use native `.otio` for clip and gap structure only |
| superchaospc/video-hardsub-fcp-skill | https://github.com/superchaospc/video-hardsub-fcp-skill/pull/5 | — | Claude/Codex skill that writes 1080x1920 FCPXML projects | Sep 2026 | FCP-targeted | skill + scripts | Reference for vertical FCPXML |
| emircbngl/davinci-resolve-mcp-free | https://github.com/emircbngl/davinci-resolve-mcp-free | — | FCPXML, Lua snippets, macOS UI automation for the free edition | — | Free | MCP | Not needed on Studio |

## Details

### Setup facts (macOS, Studio 21.1.1)
- **Environment variables:** `RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"`, `RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"`, and `PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"`. Set these in the venv activate script.
- **Preference:** Preferences > General > External scripting using = **Local**.
- **Python 3.12 works.** 3.10–3.12 is the lowest-risk range; 3.13/3.14 connect on recent builds but have failed on older ones (samuelgursky README; wildlion.media). Use a python.org build or uv. Scripts in the Workspace > Scripts menu find Python 3 only via `PYTHON3HOME` or `/usr/local/bin/python3`, so set `launchctl setenv PYTHON3HOME …` if you use menu scripts.
- **21.1 is a one-way door.** Projects opened in 21.1 can't be opened in 20.3. 21.1 also dropped Python 2, gated external scripting, UIManager and Workflow Integrations to Studio, and added a built-in Python console.
- **Resolve must be running with a project open.** `scriptapp("Resolve")` returns `None` otherwise. `-nogui` headless mode exists and the API works in it, but on an 8 GB machine running alongside you it gains little. Keep the GUI open because you review in it anyway.
- **Hangs and binding:** API calls can hang forever when the IPC stalls, so wrap them in a timeout thread. On macOS, Resolve sometimes binds to the LAN IP instead of 127.0.0.1; use the `pinghosts` fallback (mhadifilms gist §2.2–2.3).
- **Concurrency:** multiple client processes can connect, but there is no locking and every call runs against one shared project and page state. Serialize all calls through a single process. Some getters have side effects; for example, `GetCurrentRenderMode()` switches Resolve to the Deliver page (samuelgursky v4.8.23).
- **Speed:** most calls return in milliseconds. Imports, transcription, scene detection and renders are long-running; use polling, or the 21.1.1 async variants (their signatures are undocumented as of this writing).
- **Hardware:** Resolve 21.1's macOS baseline is 8 GB, rising to 16 GB with Fusion. Studio's advanced AI tools want 16 GB VRAM. On an 8 GB M2, Fusion titles and Magic Mask are the risky parts.

### Per-clip metadata handling (iPhone HDR / DJI D-Log M)
- Read metadata with `ffprobe` outside Resolve (transfer: `arib-std-b67` = HLG; Dolby Vision side data), and write the result into Resolve as an `Input Color Space` clip property.
- Resolve auto-tags iPhone Dolby Vision clips as Rec.2100 HLG. Users report the result looks too bright on a Rec.709 timeline (Blackmagic forum t=182854).
- There is no official D-Log M color space transform in Resolve; the built-in "DJI D-Log" CST over-saturates D-Log M footage. Apply DJI's official D-Log M→Rec.709 LUT on node 1 with `SetLUT` instead, and leave the input as Rec.709/bypass for those clips. 21.1 added D-Log2 and D-Gamut2, but those are not D-Log M.
- For 4K60 source on a 30 fps timeline, set `RetimeProcess` per clip, or conform the clip FPS before adding it to the timeline.

### Resolve 21.1 / 21.1.1 API additions
Most of what follows is secondhand. The official stub wasn't reachable, so verify it locally against `DaVinciResolveScript.pyi`.
- **21.1 CHANGELOG**, as quoted in danielbaldwin47/resolve-mcp #263: `TimelineItem.AddTransition`, `Get/SetFades`, `SetSpeed`; `MediaPool.CreateMulticamClip`; `TimelineItem.FlattenMulticam`; `PerformMulticamSmartSwitch`; `Timeline.AutoAlignClips`; `NormalizeAudioLevel`; `MediaPoolItem.GetTranscription` (speaker plus per-word timing); presets for project settings, render and keyboard; output blanking; audio mapping; media clone.
- **Stub size:** the 21.1 stub has 410 class-qualified methods, 46 TypedDicts with 513 fields, and 57 methods that weren't in the old README (samuelgursky issue #207, measured on 21.1.0.14).
- **Call shapes seen in community code:**
  - `AddTransition({'type': 'Cross Dissolve', 'category': 'simple', 'position': 'end', 'duration': N})`
  - `SetSpeed` takes a dict with `RippleTimeline`
  - `SetHighPriority(bool)` now requires an argument
- **21.1.1 async APIs** for Quick Export, transcription, scene cut detection, Smart Reframe and subtitle creation. Blackmagic's notes leave out signatures and completion semantics (Digital Production, 6 Oct 2026). Until they're documented, assume you have to poll.

## Section C: "Do not try this"

| Don't | Why |
|---|---|
| Edit an existing timeline in place (trim, nudge, reorder) | There are no setters, and delete-and-re-append drops grades and markers. Rebuild the timeline from the plan instead. |
| Trust boolean return values | `SetRenderSettings` can return True while dropping invalid keys, or return False after applying part of the dict (wildlion.media 21.0.4). Set one key per call and read back. |
| Let the LLM write API calls from memory | Models invent methods like `SetEffect` and pre-21.1 `AddTransition`. Put the 21.1 `.pyi` stub in context and allow only stubbed methods. |
| UI automation (pyautogui, AppleScript keystrokes) | Fragile against page and focus changes, and it fights you while you're using Resolve. It also isn't needed: the gaps are polish tasks you do yourself. |
| Rely on the OTIO FCPX adapter for transitions, effects or speed | Those aren't supported by the adapter. Use OTIO or FCPXML only for cut structure. |
| Script Fairlight mixing, music ducking or Resolve FX parameters | No API. Pre-mix levels with ffmpeg loudnorm or volume keyframes outside Resolve, or do it in the GUI. |
| Use IntelliScript or AI Music Editor from the agent | GUI only. IntelliScript is also speech-based and useless without dialogue. Use librosa beat detection plus the AI Music Editor by hand. |
| Build on undocumented methods | Blackmagic has disabled these without notice before. |
| Run several agent scripts against Resolve in parallel | Shared mutable state, no locking, and IPC hangs. |
| Run Magic Mask or heavy Fusion unattended on 8 GB | Over the memory guidance. Expect beachballs and swapping. |
| Test 21.1 on irreplaceable projects | 21.1 projects can't be opened in 20.3. Back up first. |

## Section D: Recommended architecture

1. **Plan layer (Claude Code, no Resolve).** `ffprobe` each clip to get fps, resolution, transfer (HLG/PQ/Dolby Vision) and D-Log M markers. Generate `reel.json`: clips with source in/out, overlay text and timing, transition type, speed, music path, LUT per camera profile. Optional: librosa beat grid for cut points, borrowed from the wasserman MCP engines.
2. **Build layer (your own `resolve_driver.py`).** Use the official 21.1 `.pyi` for typing. The driver is idempotent: create project from a settings preset (1080x1920, 30 fps, color managed) → import → tag input color space → `CreateTimelineFromClips` with `recordFrame` → `SetProperty` for transform/zoom → `SetSpeed`/`AddTransition`/`SetFades` → `InsertFusionTitleIntoTimeline("Text+")` plus `SetInput("StyledText")` → `SetLUT`/`ApplyGradeFromDRX` → `NormalizeAudioLevel` → markers carrying a JSON "agent notes" payload. On any change, delete the timeline and rebuild it.
3. **Verify layer.** Read back every property you set. Use `ExportCurrentFrameAsStill` at each cut and title so Claude can look at the frames. Fail loudly on any mismatch.
4. **Human pass.** You trim, mix music and polish in the GUI.
5. **Deliver.** A preset H.264/H.265 1080x1920 render queued by script, then poll `GetRenderJobStatus`.
6. **Tools.** Keep samuelgursky's MCP installed for interactive questions like "what does this timeline contain". Don't route production builds through any MCP.

**Top 3 risks**
1. **Silent partial writes and version drift.** Behavior changes between point releases. The 21.1.1 async semantics are undocumented, and community MCPs validate mostly on 19.x–21.0. Mitigation: read back everything, run a smoke-test script after each Resolve update, and pin your Resolve version.
2. **Color pipeline errors with mixed HDR, Dolby Vision and D-Log M sources.** This failure is visual and invisible to the API. Mitigation: a deterministic metadata → color-space/LUT table, a fixed SDR Rec.709 output, and frame grabs for review.
3. **8 GB RAM and IPC hangs.** Fusion titles, 4K60 HEVC decoding and AI tools can stall Resolve mid-script. Mitigation: timeouts on every call, a single serialized client, optimized media or proxies for 4K60 HEVC, few Fusion titles (one comp per overlay), and no Magic Mask in the automated path.

## Caveats
- Several 21.1 behaviors are known only from community repositories and issues (danielbaldwin47, vedanthvdev, samuelgursky), not from Blackmagic's stub. The official 21.1 README, `.pyi` and 21.1.1 release notes could not be fetched for this report.
- wildlion.media's guide, the main source for the API's limits, was co-written with an AI and has been corrected once. Its claim of "no transitions/fades/speed" predates 21.1 and is now outdated.
- The pilotcut.com and screenkite sources are competitor marketing, so their API-gap claims are used only where other sources corroborate them.
- pydavinci, OTIO adapter docs and some forum threads predate 2025 and may be outdated.
