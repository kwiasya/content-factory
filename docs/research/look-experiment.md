# Look: LUT generator and three candidates on reel-01

Date: 2026-10-10, DaVinci Resolve Studio 21.1.1, project `cf-potsdam-2026-10-04-reel-01`, timeline `reel-01` (17 shots, the edit in `reels/reel-01/script-v1.json`). Scratch project: `cf-look-probe`.

Brief (`style.json` `look.brief`): rich, saturated, expensive cinematic travel-film image; deep but not crushed shadows, glowing highlights, warm/teal split, skin protected. The author called the first render flat.

## What was built

- `src/cf/look.py` generates a 33-point `.cube` from a JSON spec (`looks/*.json`). It works in the timeline space: decode DaVinci Intermediate to linear, convert DWG to linear Rec.709 primaries, grade, convert back, re-encode, clamp. The grade, in order: exposure trim; filmic contrast in log2 around 0.18 (the slope relaxes to 1 over `toe_stops`/`shoulder_stops`, so blacks get denser but never reach zero); saturation with vibrance, highlight roll-off, a noise-floor fade, a skin hue band and optional hue bands (used to calm yellow-green foliage); luminance-neutral split toning as log offsets; optional black lift; a gamut guard that desaturates instead of clipping. `preview` applies the same grade to a Rec.709 still (gamma 2.4 decoded and treated as linear). That is only an approximation: it has no output tone map, so its highlights blow out where Resolve's do not. All judgements below come from Resolve stills.
- `cf.build` applies `style.look.lut` (or `--look`) to every V1 item. `--stills-only` exports stills from the existing timeline without rebuilding (about 6 s), `--stills-dir` sets where they go, and `--script` picks the script (needed here, see the caveats).
- `python -m cf.look measure|grid` produce the numbers and the comparison grid.

## Where the LUT lives in Resolve (node 2 was not reachable)

- A built clip has **one** node (node 1: HLG CDL). `Graph.SetLUT(2, path)` returns `False` and `GetNumNodes()` stays 1. The timeline graph (`Timeline.GetNodeGraph()`) has 0 nodes, and its `SetLUT(1)` returns `False`.
- The API cannot create nodes. A grabbed still exported as DRX holds the grade as a zstd-compressed protobuf. A hand-made DRX with two nodes did load (`GetNumNodes()` = 2), but the second node was **not connected**: a LUT on it did not change the picture. One guess at the link encoding **crashed Resolve**. Crafted DRX files are not safe to ship. Adding one serial node by hand through computer use was declined, so no neutral 2-node DRX exists yet.
- **What works:** the post-clip graph of a project color group. `Project.AddColorGroup('cf-look')`, `TimelineItem.AssignToColorGroup(group)` on every V1 item, then `group.GetPostClipNodeGraph().SetLUT(1, path)`. `GetLUT(1)` reads back `'content-factory/<file>.cube'` (relative to the LUT folder). `SetLUT(1, '')` clears it. The post-clip grade runs after the clip's own nodes, so the order is the one the brief asked for: node-1 HLG CDL, then the Look. ApplyGradeFromDRX and SetCDL on the clip do not touch the group grade. V2/V3 overlays are not in the group and stay ungraded.
- LUT files must sit under `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/` (the user-level `~/Library/...` folder does not exist on this machine). Ours go in `content-factory/`. cf.build copies the cube there and calls `Project.RefreshLUTList()`.

## Validating the transform in Resolve

- DI curve: the Blackmagic white paper PDF was fetched, but its text could not be extracted (no PDF tools). The constants match the brief, and the curve was checked numerically instead. Decode then encode round-trips to 1e-16. A neutral 33-point LUT built through the full path is an identity within 4e-10 (in units of 1/1023). In Resolve, a neutral LUT in the group changes the stills by a mean of 0.04 levels (max 8 levels on a few sky pixels; 17-point test).
- Against Resolve's own DI: a LUT doing −1 stop in linear was compared with a node-1 CDL Offset of −0.07329 (one stop in DI). Mean difference: 0.5 levels on the HLG shot s01 and 2.4 levels on the SDR shot s13. The larger SDR figure comes from dark foliage, where a CDL offset stops being exactly one stop below the DI log cut.
- The look is applied to the actual render: frames from `out/reel-01.mp4` differ from the cinema-warm stills by a mean of 3–4 levels (H.264), and from the no-look stills by 7–12.

## The three candidates

| spec | one line | key settings |
|---|---|---|
| `looks/cinema-warm.json` | Golden travel film: dense filmic contrast, warm glowing highlights, teal shadows, rich color with protected skin | −0.25 EV, contrast 1.30 (toe 2.5, shoulder 1.2 stops), sat 1.25 + vibrance 0.2, highlights hue 32° +0.16, shadows hue 192° +0.22, skin protect 0.5 |
| `looks/cinema-clean.json` | Rich and clean: deep blacks, punchy contrast, saturated true-to-life color, only a hint of toning | −0.15 EV, contrast 1.35 (toe 2.0), sat 1.28 + vibrance 0.2, toning 0.03/0.05, skin protect 0.55 |
| `looks/cinema-moody.json` | Moody film: darker, strong teal shadows, warm highlights, milky lifted blacks, calmer saturation | −0.5 EV, contrast 1.22, sat 1.0, shadows hue 186° +0.35, highlights +0.12, black lift 0.012 |

All three have a narrow yellow-green band (hue 80° ± 12°, gain 0.88–0.9). In the first rounds, sunlit grass in s12/s14 turned acid yellow. A wide band (72° ± 22°) also dulled brick and stone, so it was narrowed.

Tuning took four rounds in Resolve. Round 1 brightened everything: the shoulder was 3 stops and there was no exposure trim, so mean luma rose 8–11 levels and ≥235 pixels went from 1.4 % to about 10 %. Round 2 shortened the shoulder to 1.2 stops and added −0.15 to −0.45 EV of density. Rounds 3 and 4 added and then narrowed the foliage band.

### Measurements (17 Resolve stills per look, 1080×1920, after the DRT)

| look | mean luma | 2nd pct luma | 98th pct luma | mean Lab chroma | mean HSV S | % luma ≥ 235 | % luma ≤ 16 | % any channel ≥ 254 |
|---|---|---|---|---|---|---|---|---|
| no look | 146.5 | 31.2 | 234.5 | 16.7 | 0.28 | 1.39 | 0.87 | 0.17 |
| **warm** | 143.1 | 19.1 | 236.6 | 21.4 (+28 %) | 0.37 | 2.65 | 2.17 | 0.54 |
| clean | 147.3 | 20.2 | 239.3 | 21.2 (+27 %) | 0.36 | 4.19 | 1.96 | 0.63 |
| moody | 135.0 | 30.2 | 229.2 | 15.2 (−9 %) | 0.26 | 0.75 | 0.25 | 0.09 |

Per-shot numbers: `reels/reel-01/look-measurements.json`.

### Skin (fixed cheek boxes, mean RGB of the box → HSV hue; natural = 15–35°)

| shot | box x,y,w,h | no look | warm | clean | moody |
|---|---|---|---|---|---|
| s05 (profile, fountain) | 820,770,40,50 | 25.3° S 0.18 | 26.7° S 0.22 | 26.4° S 0.19 | 25.1° S 0.20 |
| s10 (selfie, Flatow Tower) | 412,870,44,36 | 31.9° S 0.29 | 33.2° S 0.34 | 34.0° S 0.30 | 30.3° S 0.30 |
| s16 (golden hour, Cecilienhof) | 500,690,36,18 | 9.3° S 0.24 | 8.7° S 0.31 | 8.6° S 0.32 | 8.7° S 0.20 |

s05 and s10 stay inside 15–35° with every look; the hue shifts by at most +2°. s16 is **outside the range already without a look** (9°, pink-red). It is a backlit face in warm bounce light, and no look moves it by more than 0.7°. Warm and clean raise its saturation (0.24 → 0.31). On screen it reads as a sunlit flush, not orange. Clean pushes s10 closest to the yellow edge (34°).

## Verdict

Grid: `reels/reel-01/look-compare.png` (s01, s05, s09, s10, s12, s14 × no look / warm / clean / moody, 270 px cells). Full-resolution golden-hour stills: `reels/reel-01/look-golden/s14-{none,warm,clean,moody}.png`.

- **cinema-warm is the closest to "rich, saturated, expensive cinematic". Recommended.** It is denser than the original: mean luma −3, but the 2nd percentile goes from 31 to 19, so the shadows have weight without crushing (2 % of pixels ≤ 16). Color is +28 % chroma. The sun in s14 glows gold instead of white, the oak leaves get a teal-olive depth, and the brick of the Flatow Tower turns a warm amber. Skies stay blue, slightly deeper. Skin gets a little warmer and more saturated but stays natural (s05 27°, s10 33°). Highlights roll off rather than clip: 0.5 % of pixels have a channel at 254 or above.
- **cinema-clean** is the most saturated and the brightest. It looks punchy and "phone-premium" rather than filmic. It clips the most (4.2 % ≥ 235, the castle sky in s01 and the sun in s14), and its grass stays the most yellow-green. Choose it if the author wants vivid over cinematic.
- **cinema-moody** is darker and calmer: chroma −9 %, teal shadows, lifted blacks. It is the most "film" in tonality, but it contradicts "saturated, juicy". It reads close to the flat original, only darker. It is kept as the contrast option.

What the author sees in Resolve (Color page, any clip of `reel-01`): clip node **01** holds the HLG normalization CDL (Offset −0.0749, Sat 1.25) on HLG clips. It is empty on the SDR clip IMG_1621. With the node graph's mode set to **Post-Clip** (group `cf-look`), node **01** holds the LUT `content-factory/cinema-warm.cube`. To compare looks she can swap the LUT on that one node (right-click › LUTs › content-factory), or rebuild with `--look`. Clip-level fixes (node 2 onward on a clip) remain hers to add by hand.

## Caveats

- `reels/reel-01/script.json` was replaced during this session by a 7-shot script; the 17-shot version is now `script-v1.json`. The Resolve timeline, the stills and the render are still the 17-shot v1 edit. cf.build was run with `--stills-only --script script-v1.json` and never rebuilt the timeline. A rebuild from the new `script.json` will reapply the Look from `style.json` automatically.
- The LUT clips DI input to 0–1. Negative DWG values (a few out-of-gamut sky pixels) are clamped. This is the source of the ±8-level outliers in the identity test.
- The preview path (`cf.look preview`) is only for quick iteration. It exaggerates highlight clipping.
- Skin protection is a hue window in display-encoded HSV. It also calms orange brick and sunset light a little, which suited this footage.
- `cf-look-probe` (scratch project) still exists in the project list.
