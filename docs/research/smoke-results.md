# Resolve API smoke results (S1–S10)

- Date: 2026-10-10
- Resolve: DaVinci Resolve Studio `21.1.1.10` (`GetVersion()` = `[21, 1, 1, 10, '']`), macOS 26.6.2
- Client: repo `.venv`, Python 3.12.15, env vars from `docs/resolve-rules.md`
- Project: `smoke-2026-10-10` (created by the suite; no other project was opened)
- Media (read-only): `IMG_0332.MOV` (iPhone HEVC 10-bit HLG, 1080x1920 after rotation, 60 fps), `IMG_1621.mov` (iPhone HEVC SDR, 2160x3840 after rotation, 30 fps)
- Scripts: `tests/smoke/S01_connect.py` … `S10_markers.py`. Raw read-backs: `tests/smoke/out/*.json`. All project settings before/after: `tests/smoke/out/project_settings.json`
- Driver: `src/cf/resolve_driver.py`

## Results

| Test | Result | What the API actually does |
|---|---|---|
| S1 connect | PASS | `GetVersionString()` = `21.1.1.10`, `GetProductName()` = `DaVinci Resolve Studio`, `IsStudio()` = True. Connected on the first try about 5 s after `open -a "DaVinci Resolve"`. The process is named `Resolve`, so `pgrep -x "DaVinci Resolve"` finds nothing. |
| S2 project settings | PASS | `colorScienceMode=davinciYRGBColorManagedv2`, `isAutoColorManage=0`, `timelineWorkingLuminanceMode=SDR 100`. With `separateColorSpaceAndGamma=0`: `colorSpaceTimeline='DaVinci WG/Intermediate'`, `colorSpaceOutput='Rec.709 Gamma 2.4'`. With `=1`: `colorSpaceTimeline='DaVinci WG'` + `colorSpaceTimelineGamma='DaVinci Intermediate'`, `colorSpaceOutput='Rec.709'` + `colorSpaceOutputGamma='Gamma 2.4'`. `inputDRT`/`outputDRT` = `'DaVinci'` accepted. Unknown values return False and leave the old value. |
| S3 timeline + append | PASS | Project-level `timelineResolutionWidth/Height=1080/1920` and `timelineFrameRate='30'` work while the project has no timelines. Per-timeline `useCustomSettings='1'` + res/fps also read back correctly. Timeline starts at frame `108000` (`01:00:00:00`). `recordFrame` is absolute (108000 + offset). `trackIndex=2` lands on V2 (the track must exist, so call `AddTrack('video')` first). **`endFrame` is exclusive**: source 0..89 gives duration 89. Source frames are in the clip's own fps: 120 source frames of the 60 fps clip become 59 timeline frames. |
| S4 transitions | PASS (with retry) | A transition item comes back only when **both `category: 'simple'` and `alignment`** are passed. Type only, type+alignment, and type+category without alignment all return `None`. Accepted names (case-sensitive): `Cross Dissolve`, `Dip To Color Dissolve`, `Smooth Cut`, `Additive Dissolve`, `Blur Dissolve`, `Non-Additive Dissolve`, `Edge Wipe`, `Push`, `Slide`, `Center Wipe`, `Cross Iris`, `Box`. Rejected: `Fade`, `Dip to Color Dissolve` (lower-case "to"), `Zoom`. `alignment='center', duration=10` on a cut at F gives a transition spanning F-5..F+5, and clip positions do not move. Without `duration`, `left` alignment filled the whole 30-frame clip. `position='start', alignment='right'` on the first clip works (head fade). Categories `fusion`/`ofx` did not find these names. |
| S5 Fusion Text+ | PASS (but unusable for placement) | `InsertFusionTitleIntoTimeline('Text+')` **ripple-inserts on V1 at the playhead**: it splits the V1 clip under the playhead, adds a 150-frame (5 s) title and pushes **every later item on V1 and V2** right by 150 frames. With V1 locked it returns `None`. With V1 disabled it still lands on V1. `GetFusionCompByIndex(1)` works without opening the Fusion page. `comp.GetToolList(False, 'TextPlus')` returns 1 tool. `StyledText` defaults to `'Custom Title'`. `SetInput('StyledText','SMOKE')` returns `None` but the read-back is `'SMOKE'`. `ExportCurrentFrameAsStill` returned True from the Edit page. A 1-frame PNG render shows the text (0.17 % of pixels change between title enabled and disabled). |
| S6 clip color space | PASS (partial) | Auto-detected on import: HLG clip `'Rec.2100 HLG'`, SDR iPhone clip `'Rec.709 (Scene)'`. Accepted `Input Color Space` (combined mode): `Rec.2100 HLG`, `Rec.2100 HLG (Scene)`, `Rec.2020 HLG ARIB STD-B67`, `Apple Log`, `Rec.709 Gamma 2.4`, `Rec.709-A`, `Rec.709 (Scene)`, `sRGB`. Rejected: `Rec.2020 HLG`, `Rec.709`. **`Input Gamma` is not writable**: every value returns False, including after a retry with a separate-mode color space set. **`Input LUT` is not writable**: relative and absolute paths both return False, also after `RefreshLUTList()`. In separate mode, writing `Input Color Space='Rec.2020'` returns True but reads back `'Rec.2020 (Scene)'`, and writing `'Rec.2020 (Scene)'` returns False. |
| S7 audio | PASS | `SetProperties({'AudioVolume': -20.0})` on the A1 item reads back `-20.0`. The deprecated `SetProperty('AudioVolume', -12.0)` also works. The video item has no `AudioVolume` key (`SetProperties` returns False), so use the linked audio item (`GetLinkedItems()` or `GetItemListInTrack('audio', n)`). `SetFades({'FadeIn':15,'FadeOut':20})` on audio reads back exactly, and on video too. `GetNormalizeAudioModes()` returns 14 modes (`Sample Peak Program`, `True Peak`, `ITU-R BS.1770-1`, `ITU-R BS.1770-4`, `ATSC A/85`, `EBU R128`, …, `YouTube`). `NormalizeAudioLevel` returns True and **writes the result into `AudioVolume`**: BS.1770-4 at -14 LKFS set +12.4 dB and +20.5 dB on two quiet clips. The relative mode keeps the offset between clips. |
| S8 render | PASS | `SetCurrentRenderFormatAndCodec('mp4','H264')` OK. 1080x1920 30 fps, 90 frames, 2–3 s per render. `ColorSpaceTag='Rec.709'` + `GammaTag='Rec.709-A'` gives `bt709/bt709/bt709` (1-1-1), `yuv420p`, `tv` range, H.264 High, AAC 48 kHz stereo. `Rec.709`+`Rec.709` also gives 1-1-1. `Same as Project` and `Gamma 2.4` leave **color_transfer untagged**. `ColorSpaceTag='Rec.709-A'` is rejected (SetRenderSettings returns False). The decoded pixels are bit-identical across all tag choices, so the tags change only metadata. Unknown keys or values make SetRenderSettings return False. |
| S9 Remotion overlay | SKIP | `~/Movies/content-factory/smoke/overlay_test.mov` does not exist yet. The script is ready: it imports the file, logs `Alpha mode`, appends it on V2 at +15 and renders one frame. |
| S10 markers | PASS | `AddMarker(frame, color, name, note, duration, customData)` with a JSON string (incl. non-ASCII) round-trips exactly on the timeline and on the item. `GetMarkerByCustomData`, `UpdateMarkerCustomData` and `GetMarkerCustomData` work. **Timeline marker frames are offsets from the timeline start** (45 means 01:00:01:15). An absolute frame (108060) is accepted silently and lands an hour later; 5000 on a 90-frame timeline is also accepted. **TimelineItem marker frames are source-media frames**: values outside the media are clamped to `[0, 1007]` for a 1008-frame clip, not to the item. Item markers do not appear on the MediaPoolItem. |

## Discovered strings

- Project color (combined): `colorSpaceTimeline='DaVinci WG/Intermediate'`, `colorSpaceOutput='Rec.709 Gamma 2.4'`, `inputDRT='DaVinci'`, `outputDRT='DaVinci'`.
- Project color (separate): `'DaVinci WG'` + `'DaVinci Intermediate'`, `'Rec.709'` + `'Gamma 2.4'`.
- Clip `Input Color Space`: iPhone HLG `'Rec.2100 HLG'` (auto-detected; `'Rec.2100 HLG (Scene)'` and `'Rec.2020 HLG ARIB STD-B67'` also accepted), iPhone SDR `'Rec.709 (Scene)'` (auto-detected; `'Rec.709 Gamma 2.4'` and `'Rec.709-A'` accepted), `'Apple Log'` accepted.
- Transitions: `{'type': 'Cross Dissolve', 'category': 'simple', 'position': 'end', 'alignment': 'center', 'duration': N}`. Accepted names are listed under S4.
- Render: `SetCurrentRenderFormatAndCodec('mp4', 'H264')`, `{'ColorSpaceTag': 'Rec.709', 'GammaTag': 'Rec.709-A', 'FormatWidth': 1080, 'FormatHeight': 1920}`. mp4 codecs: `H264`, `H265`, `APVYUV422_10`. Alpha-capable mov codec: `ProRes4444`.
- Normalize modes: see S7. The default is `Sample Peak Program`.

## Surprises

1. **The canonical `MediaPool.ImportMedia([{'FilePath': p}])` returns `None`** for plain movie files, even though the README documents it. The deprecated `ImportMedia([path])` works, and so does `MediaStorage.AddItemListToMediaPool([{'media': p}])`. The driver uses the latter.
2. The 21.1 canonical calls are `GetSettings`/`SetSettings({k: v})`, `GetProperties`/`SetProperties({k: v})` and `GetClipProperty()` (a dict). `GetSetting`/`SetSetting`/`SetProperty`/`GetProperty` are deprecated but still work.
3. `AddTransition` needs `category` **and** `alignment`. The research said only `alignment` mattered; that alone still returns `None`.
4. A Fusion title is a ripple insert on V1 at the playhead (5 s) that also shifts V2. It cannot be targeted at V2, and locking V1 makes it fail.
5. `endFrame` in `AppendClipInfo` is exclusive (duration = endFrame − startFrame, in source frames).
6. The iPhone HLG clip (spatial audio) brings **5 audio tracks**: a plain append grew the timeline from A1 to A5. Overlay and B-roll appends need `mediaType: 1`.
7. `useCustomSettings='1'` snapshots the project color settings into the timeline. Later project-level color changes do **not** reach that timeline (checked with `outputDRT`).
8. `SetCurrentRenderMode()` also switches the UI to the Deliver page, not only `GetCurrentRenderMode()`.
9. `Input Gamma` and `Input LUT` are listed in the stub's ClipProperties but cannot be written. After a separate-mode round trip, `Input Gamma` reads stale values in combined mode, so read only `Input Color Space`.
10. `NormalizeAudioLevel` sets `AudioVolume`, so a manual `AudioVolume` written before it is overwritten.
11. Marker frame bases differ: timeline markers use offsets from the timeline start, item markers use source frames, and neither validates range.
12. `timelineWorkingLuminanceMode='SDR 100'` leaves `timelineWorkingLuminance` reading `'1000'`.
13. `SetSettings` returns a plain `False` on a bad key or value. The "error message listing the keys" from the README never reaches the Python caller.

## Impact on build-reel

Nothing blocks it. Things it must do differently from the original plan:

- Import through `MediaStorage.AddItemListToMediaPool` (driver `import_media`).
- Set project resolution, fps and color **before** creating the timeline. Use custom timeline settings only if needed, and never change project color afterwards.
- Use `endFrame` as exclusive. Convert cuts to source frames at the clip's own fps.
- Append video with `mediaType: 1` and place audio explicitly, so iPhone spatial-audio clips do not spill onto A2–A5.
- Pass `category: 'simple'` + `alignment` in every `AddTransition`.
- Overlays: Remotion on V2/V3 (S9 pending the overlay file). Fusion titles via API are out, because of the ripple on V1.
- Color: tag clips with combined `Input Color Space` strings (above). D-Log M needs a LUT on a node (`Graph.SetLUT`), since `Input LUT` cannot be written.
- Render with `ColorSpaceTag='Rec.709'`, `GammaTag='Rec.709-A'` and verify 1-1-1 with ffprobe.
