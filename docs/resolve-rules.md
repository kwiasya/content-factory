# Working with the Resolve scripting API

Rules every skill that touches DaVinci Resolve Studio 21.1.1 follows. Rationale: `docs/adr/0001-timeline-rebuilt-from-plan.md`, evidence: `docs/research/01-resolve-scripting-api/` and the smoke tests in `docs/research/smoke-results.md` (S1–S10, run on 21.1.1.10).

## Source of truth

The typed stub ships with Resolve:

```
/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi
```

Only methods present in the stub exist. Before calling a method you have not used in this session, grep the stub for its signature. The CHANGELOG in the same folder lists what each version added.

Use the canonical 21.1 forms: `GetSettings()` / `SetSettings({key: value})` on Project and Timeline, `GetProperties()` / `SetProperties({key: value})` on TimelineItem, `GetClipProperty()` (whole dict) on MediaPoolItem. The single-key `GetSetting` / `SetSetting` / `GetProperty` / `SetProperty` forms are deprecated (they still work).

Where the stub and the app disagree, the app wins. Smoke S3 found that the stub's `MediaPool.ImportMedia([{"FilePath": p}])` returns `None` for movie files; import with `MediaStorage.AddItemListToMediaPool([{"media": p}])`.

## Connecting

From the repo venv (`.venv`, Python 3.12). Resolve must be running; `scriptapp("Resolve")` returns `None` otherwise. It connects about 5 s after `open -a "DaVinci Resolve"`, with "Untitled Project" open. The process is named `Resolve` (`pgrep -x Resolve`). Env vars:

```
RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
PYTHONPATH="$RESOLVE_SCRIPT_API/Modules"
```

All calls go through `src/cf/resolve_driver.py`: one process, one connection, a timeout on every call. The driver refuses to create or modify any project whose name does not start with `smoke-` or `cf-`.

## Rebuild, never patch

The timeline is built in one pass from the plan (`AppendToTimeline` with explicit `recordFrame` and `trackIndex`). To change anything, delete the timeline and build it again from the plan. The API has no trim, move or slip.

Order matters (S3, S2):

1. Set project resolution, frame rate and color settings **before** creating the timeline. A timeline with `useCustomSettings='1'` takes a snapshot of the project color settings, and later project changes do not reach it. Once the project has a timeline, `timelineFrameRate` is locked (`SetSettings` returns `False`), but `timelineResolutionWidth/Height` can still be changed, and timelines without custom settings follow the new size (probe, 2026-10-11). That is how cf.build moves an existing 1080×1920 project to 2160×3840.
2. Create the timeline. It starts at frame `108000` (`01:00:00:00`) at 30 fps; read `GetStartFrame()` instead of assuming that.
3. Add tracks first (`AddTrack('video')`). `trackIndex` does not create tracks.
4. `recordFrame` is absolute (timeline start + offset). `startFrame`/`endFrame` are **source frames at the clip's own fps**, and **`endFrame` is exclusive** (duration = endFrame − startFrame).
5. Append video with `mediaType: 1` and audio in a second call with `mediaType: 2`, `trackIndex: 1`. iPhone clips carry 6 audio channels and spill onto A2–A5 **even with `mediaType: 2, trackIndex: 1`** (A1 gets the stereo mix); delete the A2+ items (`Timeline.DeleteClips`) and tracks (`DeleteTrack`) afterwards and read back the track count (cf.build).

## Read back every write

A `True` return proves nothing, and a `False` explains nothing. In 21.1.1 an unknown key or value returns `False` and leaves the old value (S2, S6, S8), but a multi-key call can still apply some keys before failing, and the README's error message never reaches Python. Some writes return `True` and store a different string: separate-mode `Input Color Space='Rec.2020'` reads back `'Rec.2020 (Scene)'`. Others return `None` and still work: Fusion `SetInput`. After each write, read the value back (`GetSettings()`, `GetClipProperty()`, `GetProperties()`, `GetStart`/`GetEnd`) and fail loudly on a mismatch. Set one key per call. The driver helpers `set_setting_verified`, `set_clip_property_verified` and `set_item_property_verified` do this.

## Known gaps (do by hand in the GUI)

Trim/move/slip, speed curves, EQ and compression, Resolve FX on a clip, reading a grade back, IntelliScript, AI Music Editor, Beat Detector, Shot Match, clip `Input Gamma` and `Input LUT` (S6), placing a Fusion title anywhere but a ripple on V1 (S5).

## Known traps

- `fu.GetCurrentComp()` is `None` until the Fusion page has been opened once in the session. `TimelineItem.GetFusionCompByIndex(1)` works without opening it (S5).
- `GetCurrentRenderMode()` and `SetCurrentRenderMode()` both switch the UI to the Deliver page (S8).
- `SetSpeed` with `RippleTimeline: true` has deleted audio tracks in the field; leave it `false`.
- `AddTransition` returns `None` unless **both** `category: 'simple'` and `alignment` are passed (S4). Full form: `{'type': 'Cross Dissolve', 'category': 'simple', 'position': 'end', 'alignment': 'center', 'duration': N}`. Type names are case-sensitive: `Cross Dissolve`, `Dip To Color Dissolve`, `Smooth Cut`, `Additive Dissolve`, `Blur Dissolve`, `Non-Additive Dissolve`, `Edge Wipe`, `Push`, `Slide`, `Center Wipe`, `Cross Iris`, `Box`. `Fade` is not a transition. Use fades through `SetFades`.
- `InsertFusionTitleIntoTimeline` ripple-inserts a 150-frame title on V1 at the playhead and pushes every later item on all video tracks (S5). With V1 locked it returns `None`. Never call it on a built timeline. Overlays go through Remotion on V2/V3.
- `NormalizeAudioLevel` writes its result into the item's `AudioVolume` (S7). Set manual volume offsets after normalizing, not before. `AudioVolume` lives on the audio item (`GetLinkedItems()`); the video item has no such key.
- Source fps (cf.build, 2026-10-10): Resolve reads a `60000/1001` iPhone clip as `FPS 60.0` (and one more frame than ffprobe's `nb_frames`). Compute `startFrame`/`endFrame` from the clip's `FPS` in `GetClipProperty()`, not from the manifest.
- Frame rounding (cf.build): the timeline duration of an append is `floor((endFrame − startFrame) × timeline_fps / clip_fps)`, and a float `endFrame` is honoured. 61.6 source frames of a 24 fps clip give 77 timeline frames, 62 also give 77, 61 give 76. Pass the exact span (+0.001 when fractional) to get the planned duration.
- `SetSpeed({'Percentage': p, 'RippleTimeline': False})` keeps the item's timeline duration and rescales its source span (50 % on a 45-frame item: still 45 frames, source span halved). So append the 100 %-speed range for the planned duration, then `SetSpeed` the video and the audio item separately (they are not linked). `GetSpeed()` reads back `{'Percentage': p}`.
- `Timeline.GetItemListInTrack('video', n)` returns transitions as items too (`GetName()` = `'Cross Dissolve'`, `GetMediaPoolItem()` and `GetSourceStartFrame()` = `None`). Filter them out before matching items to shots.
- Stills: `Timeline.SetCurrentTimecode(tc)` then `Project.ExportCurrentFrameAsStill(path.png)` from the Edit page writes an 8-bit RGB PNG of the output frame at the timeline resolution (1080×1920, or 2160×3840 on a 4K timeline; managed, after the DRT, with Super Scale applied). cf.build checked all 8 stills of a real build against the source frames (correlation ≥ 0.95 on the diagonal), so the playhead is honoured without a wait. No Gallery album is touched.
- `CreateEmptyTimeline` puts the timeline in the media pool's current folder, i.e. the bin the last import selected.
- An imported ProRes 4444 overlay reads `Alpha mode = 'Straight'` and `Input Color Space = 'Project'` (the project's `colorSpaceInput`, `'Rec.709 Gamma 2.4'` by default).
- HLG too bright (HLG experiment, 2026-10-10): Resolve converts HLG per BT.2408, which puts reference white at 203 nits, one stop over SDR white. No input color space string and no DRT changes the midtones by more than 2 luma levels. The fix is a −1.02 stop node-1 CDL offset **before** the tone map, so the working luminance must be `HDR 1000` (at `SDR 100` the input DRT has already compressed the clip, and the offset only greys the highlights). `HDR 1000` darkens SDR clips unless `useInverseDRT='1'`. With it, an SDR clip round-trips bit-identically through the `DaVinci` DRT. The GUI option "Convert HLG and PQ using methods specified in ITU-R BT.2408-7" is not exposed in `GetSettings()`; leave it at its default.
- Node 1 is reserved for input normalization (HLG CDL, D-Log M LUT). `ApplyGradeFromDRX` replaces the whole grade, so cf.build applies the CDL after the Look, and a Look DRX must keep node 1 neutral. There is no `GetCDL`: check the result with stills (cf.build compares still luma with the proxy frame).
- Look LUT (look experiment, 2026-10-10): a built clip has one node, and `Graph.SetLUT(2, …)` returns `False`. The API cannot add nodes. The timeline graph has 0 nodes. A hand-crafted 2-node DRX loads but leaves node 2 unconnected, and one variant crashed Resolve, so never write DRX files by hand. The Look goes on node 1 of the post-clip graph of the project color group `cf-look` (`AddColorGroup`, `AssignToColorGroup` on every V1 item, `GetPostClipNodeGraph().SetLUT(1, path)`). That runs after the clip's node-1 CDL. `GetLUT` reads back the path relative to the LUT folder (`'content-factory/x.cube'`), and `SetLUT(1, '')` clears it. LUTs must be under `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/`; call `RefreshLUTList()` after writing one. A node LUT runs in the timeline space (DWG / DaVinci Intermediate). See `docs/research/look-experiment.md`.
- Super Scale (4K experiment, 2026-10-11): `MediaPoolItem.SetClipProperty('Super Scale', n)` takes an **int** 1–4 (1 = off, 2 = 2x, 3 = 3x, 4 = 4x); the string `'2'` returns `False`. **2x Enhanced** exists only in the 4-argument form `SetClipProperty('Super Scale', 2, sharpness, noise_reduction)` with floats 0.0–1.0; it reads back as `'SuperScale Sharpness'` / `'SuperScale Noise Reduction'` strings (`'0.5'`, `'0.25'`; `1.0` reads `'1'`). Those two keys can also be written as numeric strings (`'0.7'`), but `'Medium'` returns `True` and stores `'0'`. The read-back cannot tell 2x from 2x Enhanced: both read `Super Scale = 2`, and nothing else in `GetClipProperty()` changes. **Writing `2` over 2x Enhanced keeps Enhanced** (identical pixels in the stills), so cf.build writes `1` first and then the target. The project-level keys (`superScale` 0=Auto, `superScaleSharpness`/`superScaleNoiseReduction` reading `'Medium'`) are a different, project-wide default and are not touched. Cost on reel-01 (476 frames, 4 of 8 shots from 1080p clips, M2 8 GB): render 27 s with Super Scale off, 47 s with 2x, 314 s with 2x Enhanced (1080×1920 render: 10 s). Build time also goes up (19 s off, 20 s 2x, 31 s Enhanced) because the stills export runs the scaler.
- Marker frames (S10): timeline markers take an offset from the timeline start (not the absolute frame), and TimelineItem markers take a **source-media frame**. Neither checks the range: absolute frames on a timeline land an hour late, and out-of-range item frames are clamped to the media extent.

## Exact strings (S2, S6, S8)

- Project (`separateColorSpaceAndGamma='0'`): `colorScienceMode='davinciYRGBColorManagedv2'`, `isAutoColorManage='0'`, `colorSpaceTimeline='DaVinci WG/Intermediate'`, `colorSpaceOutput='Rec.709 Gamma 2.4'`, `inputDRT='DaVinci'`, `outputDRT='DaVinci'`, `timelineWorkingLuminanceMode='HDR 1000'`, `useInverseDRT='1'` (HLG experiment, `docs/research/color-hlg-experiment.md`). Also accepted: `timelineWorkingLuminanceMode='SDR 100'`; DRTs `'Luminance Mapping'`, `'Saturation Preserving'`, `'None'`.
- Clip `Input Color Space` (combined mode): iPhone HLG `'Rec.2020 HLG ARIB STD-B67'`, iPhone SDR `'Rec.709 Gamma 2.4'`. cf.build forces the manifest value. Resolve auto-detects `'Rec.2100 HLG'` and `'Rec.709 (Scene)'`; these give the same pixels as `'Rec.2100 HLG (Scene)'` and `'Rec.709 Gamma 2.4'`. `'Rec.2020 HLG ARIB STD-B67'` clips fewer highlights. Also accepted: `'Rec.2100 HLG (Scene)'`, `'Apple Log'`, `'Rec.709-A'`, `'sRGB'`. `'Rec.2020 HLG'` and `'Rec.709'` are rejected.
- HLG normalization (every HLG timeline item, after the Look): `TimelineItem.SetCDL({'NodeIndex': '1', 'Slope': '1 1 1', 'Offset': '-0.0749 -0.0749 -0.0749', 'Power': '1 1 1', 'Saturation': '1.25'})`.
- `Input Gamma` and `Input LUT` cannot be written through the API (every value returns False). Keep `separateColorSpaceAndGamma='0'`, and apply LUTs (D-Log M) on a node with `Graph.SetLUT`.
- Render: `SetCurrentRenderFormatAndCodec('mp4', 'H264')` with `ColorSpaceTag='Rec.709'`, `GammaTag='Rec.709-A'` gives a 1-1-1 tagged yuv420p file. `'Same as Project'` leaves the transfer untagged, and `'Rec.709-A'` is not a valid ColorSpaceTag. The tags change metadata only, not pixels.
- Render bit rate: `SetRenderSettings({'VideoQuality': n})` with an int is the bit-rate cap in **kbit/s**: 22000 gave 22.2 Mbit/s at 1080×1920, 45000 gave 45.5–45.8 Mbit/s at 2160×3840 (H.264 High). The stub also accepts `'Least'/'Low'/'Medium'/'High'/'Best'` and `MultiPassEncode` (H.264 only); neither is used. `FormatWidth/Height` 2160/3840 are accepted with `FrameRate` 30.0, and a 1080×1920 job renders from a 2160×3840 timeline (Resolve downscales). `GetRenderCodecs('mp4')` lists `{'H.264': 'H264', 'H.265': 'H265', 'YUV 422 10-bit': 'APVYUV422_10'}`.
