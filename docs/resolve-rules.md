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

1. Set project resolution, frame rate and color settings **before** creating the timeline. A timeline with `useCustomSettings='1'` takes a snapshot of the project color settings, and later project changes do not reach it.
2. Create the timeline. It starts at frame `108000` (`01:00:00:00`) at 30 fps; read `GetStartFrame()` instead of assuming that.
3. Add tracks first (`AddTrack('video')`). `trackIndex` does not create tracks.
4. `recordFrame` is absolute (timeline start + offset). `startFrame`/`endFrame` are **source frames at the clip's own fps**, and **`endFrame` is exclusive** (duration = endFrame − startFrame).
5. Append video with `mediaType: 1` and place audio explicitly. iPhone clips with spatial audio otherwise spill onto A1–A5.

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
- Marker frames (S10): timeline markers take an offset from the timeline start (not the absolute frame), and TimelineItem markers take a **source-media frame**. Neither checks the range: absolute frames on a timeline land an hour late, and out-of-range item frames are clamped to the media extent.

## Exact strings (S2, S6, S8)

- Project (`separateColorSpaceAndGamma='0'`): `colorScienceMode='davinciYRGBColorManagedv2'`, `isAutoColorManage='0'`, `colorSpaceTimeline='DaVinci WG/Intermediate'`, `colorSpaceOutput='Rec.709 Gamma 2.4'`, `inputDRT='DaVinci'`, `outputDRT='DaVinci'`, `timelineWorkingLuminanceMode='SDR 100'`.
- Clip `Input Color Space` (combined mode): iPhone HLG `'Rec.2100 HLG'` (Resolve auto-detects it), iPhone SDR `'Rec.709 (Scene)'` (auto-detected). Also accepted: `'Rec.2100 HLG (Scene)'`, `'Rec.2020 HLG ARIB STD-B67'`, `'Apple Log'`, `'Rec.709 Gamma 2.4'`, `'Rec.709-A'`, `'sRGB'`. `'Rec.2020 HLG'` and `'Rec.709'` are rejected.
- `Input Gamma` and `Input LUT` cannot be written through the API (every value returns False). Keep `separateColorSpaceAndGamma='0'`, and apply LUTs (D-Log M) on a node with `Graph.SetLUT`.
- Render: `SetCurrentRenderFormatAndCodec('mp4', 'H264')` with `ColorSpaceTag='Rec.709'`, `GammaTag='Rec.709-A'` gives a 1-1-1 tagged yuv420p file. `'Same as Project'` leaves the transfer untagged, and `'Rec.709-A'` is not a valid ColorSpaceTag. The tags change metadata only, not pixels.
