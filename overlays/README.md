# overlays

Remotion project that renders one text overlay for a Reel as a transparent
ProRes 4444 `.mov` (canvas from style.json, 2160×3840 by default, timeline fps,
alpha). `build-reel` step 2 calls it once per shot that has an overlay; the files go
on V2/V3 in Resolve.

## Canvas and scale

The composition is `style.canvas` (2160×3840 by default). The design is written for a
1080-wide reference canvas (`style.canvas.reference_width`, default 1080): every pixel
number in `src/presets.ts`, `src/slots.json` and style.json (`safe_zone`,
`overlay_positions`, font sizes, `animation.in.distance_px`) is a reference pixel.
`Overlay.tsx` lays the text out in reference pixels inside a 1080×1920 div and scales
that div by one factor, `designScale = canvas.width / reference_width`
(`src/style.ts`). So a 4K overlay is the 1080 design at 2× size: font sizes,
paddings, radii, outlines, shadows, scrim blur, ornaments, slots and the slide-in
distance all scale together, and rotations stay in degrees. Chrome rasterises the
scaled text at the output size, so it is sharp, not an upscaled bitmap. Checked on
reel-01 s01 and s03 (tiktok-hype): the 4K frame downscaled to 1080 matches the
1080 render, with the alpha bounding box within 0.5 px and a mean alpha difference of
0.04–0.3 levels. The safe-zone assertion scales the measured box and `safe_zone` by
the same factor and reports canvas pixels.

Remotion 4.0.534, React 19.2.3, `@remotion/google-fonts` 4.0.534, all pinned
exactly in `package.json`. Node 24 (nvm). First time: `npm ci` in this folder.

## Render one overlay

```sh
node overlays/render.mjs --spec path/to/spec.json --out reels/<reel>/overlays/<shot>.mov
# or, from inside overlays/:
npm run render -- --spec spec.json --out out/test.mov
```

- `--strict`: exit 3 when there is any warning (safe zone, text overflow, font shrunk).
- Relative `--spec`/`--out` resolve against the caller's cwd (`INIT_CWD` under npm).
- The last stdout line is a JSON summary; parse that line, not the npm banner:
  `{"ok":true,"out":"…","type":"place","fps":30,"frames":90,"width":2160,"height":3840,"scale":2,"render_s":11.2,"safe_zone_ok":true,"warnings":[]}`
- Exit codes: 0 ok, 1 render failed (Remotion's log tail goes to stderr), 2 bad spec or style, 3 warnings with `--strict`.
- Set `CF_OVERLAY_VERBOSE=1` to see Remotion's full output.
- Only one render runs at a time: the script holds a lock at `$TMPDIR/cf-overlays-render.lock`
  and waits up to 15 min for another render to finish (stale locks are cleared).

What it runs, with `--props` set to a temp file holding `{text, type, durationInFrames, style}`:

```sh
npx --no-install remotion render src/index.ts Overlay <out> --props=<tmp> \
  --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le \
  --image-format=png --concurrency=2 --color-space=bt709 --overwrite --log=verbose
```

## Spec format

```json
{ "text": "Potsdam, Sanssouci", "type": "place", "duration_s": 3, "style_path": "../../style.json", "preset": "editorial-serif" }
```

| field | meaning |
|---|---|
| `text` | Overlay text, written as it should appear. |
| `type` | `hook` \| `place` \| `fact` \| `line`. |
| `duration_s` | Length of the clip. Frames = `round(duration_s × canvas.fps)`. |
| `style_path` | Path to the Style profile; a relative path resolves against the spec file's folder. |
| `preset` | Optional. Overlay preset name (see Presets); defaults to `typography.preset` in style.json, then `legacy`. An unknown name exits 2 and lists the known ones. |
| `anchor` | Optional. A named slot from `src/slots.json` (`lower-left`, `lower-center`, `mid-left`, `mid-center`, `high-left`, `high-center`, `upper-left`, `upper-center`) that replaces the preset role's placement, for example the calmest, darkest area of this shot that is clear of the face. Unknown → exit 2. |
| `scrim` | Optional, 0..1. Overrides the preset role's scrim strength. |
| `in_frames`, `out_frames` | Optional ints ≥ 0. Replace `animation.in/out.frames` for this overlay; 0 = no fade on that side (a list item that cuts on with its shot, a header that must not blink at the cut). |
| `canvas` | Optional. A style.json `canvases` name (`portrait`, `landscape`) or `WxH`; `--canvas` on the command line wins. The preset's size, `reference_width`, `safe_zone`, `overlay_positions` and `slots` replace the top-level ones. On `landscape` (3840×2160, reference 1920×1080) every overlay preset keeps its type system and takes its placement from `canvases.landscape.overlay_positions`, and `anchor` names resolve against `canvases.landscape.slots`; `designScale` is 2 on both 4K canvases, so text is the same size relative to the frame's short side. |

## Presets

A preset is one complete type system for every overlay type: font family, weight,
italic, size, case, tracking, line height, colour or gradient fill, shadow or glow,
backdrop / per-line box, rule, accent bar, ornament, rotation and placement. The
catalogue is `src/presets.ts`; style.json `typography.preset` selects one, and a
spec's `preset` overrides it for one render. The summary line reports `preset`.

| preset | hook | place label |
|---|---|---|
| `legacy` | the original design, read from style.json (Playfair Display, translucent pill) | same |
| `editorial-serif` | Cormorant Garamond SemiBold Italic 96 px, outline, scrim | Cormorant SC SemiBold 48 px, tracked |
| `clean-grotesk` | Inter Tight SemiBold 86 px, scrim | Inter Tight Bold uppercase 40 px, tracked, 2-px rule above |
| `lower-third-tag` | Space Grotesk SemiBold 86 px, centred, scrim | Space Grotesk 48 px tag with an accent bar (`colors.accent`) |
| `tiktok-hype` | Montserrat ExtraBold uppercase, black on white per-line boxes, -3° | small white box tag |
| `pinterest-aesthetic` | Bodoni Moda SemiBold 84 px lowercase, cream, outline, scrim | 42 px lowercase, hairline under it |
| `coquette-girly` | Great Vibes 104 px, light pink, plum outline, tilted, full scrim | Cormorant Garamond Bold Italic 52 px + pink bow |
| `y2k-gloss` | Unbounded ExtraBold 84 px, pastel gradient, violet outline, glow, full scrim | 40 px, sparkles both sides |
| `diary-typewriter` | Special Elite lowercase on cream marker strips, top-left | same, e.g. "potsdam · 04.10" |
| `handwritten-note` | Caveat Bold 104 px, outline, squiggle underline, scrim | Caveat Bold 72 px, near the horizon |

**Legibility without a box.** These are the role fields that make the box-free presets
readable on bright footage (reel-01 measurements are in
`reels/reel-01/overlay-design/README.md`):
- `shadow`: every box-free text uses the layered shadow
  `0 2px 3px rgba(0,0,0,.7), 0 10px 40px rgba(0,0,0,.55)`.
- `stroke: {width, color}`: a dark outline. It is drawn as a stroked copy of the
  text *under* the fill (stroke width 2×), so the glyph shape is not thinned.
  Use it for serifs, scripts and thin faces.
- `scrim: 0..1`: a feathered dark ellipse behind the text block, about 1.6× its
  size plus 50 px, centre alpha 0.6 × scrim, blurred 48 px. It darkens pale sky
  or stone under the text without drawing a shape. At 1.0 on bright sky it shows
  as a faint grey haze.
- `layers` (prop only, for measurement): `background` renders only the scrim and
  boxes; `glyphs` renders only the glyph fill.

With a non-legacy preset, the preset replaces `typography.display/body`,
`colors.text/text_shadow/backdrop` and `overlay_positions`. Still read from
style.json: `canvas`, `safe_zone`, `animation`, `colors.accent`,
`typography.max_words_per_line/max_lines` (unless the preset role sets its own).
Some presets assume a text convention: `pinterest-aesthetic` reads best with
"place, city"; `diary-typewriter` with "city · dd.mm". The renderer does not
rewrite text.

Anchors: `center`, `middle-left`, `top-left`, `top-center`, `bottom-left`, `bottom-center`.
`bottom-*` puts the box's bottom edge at `y` at rest (the slide-in starts lower,
which the safe-zone check includes). The text width is limited by the safe zone,
by the right rail when the box can reach below `right_rail.from_y`, and by the
role's `maxWidth` (hooks ≤ 760 reference px, place labels ≤ 640 for most presets; keeping
clear of the person is the job of the `anchor` choice). Presets break lines after punctuation when they
can ("POV: Sunday walk, / but make it castles"); `legacy` keeps the old
most-balanced rule. `legacy` output is pixel-identical to before presets existed
(checked on reel-01 s01 and s06, frame 12).

To compare presets on real frames, render each through `render.mjs` with a spec
`preset`, pull one frame with
`ffmpeg -i x.mov -vf "select=eq(n\,12)" -frames:v 1 -pix_fmt rgba x.png`
and composite it over a still. reel-01 has such a board in
`reels/reel-01/overlay-design/`.

## What it reads from style.json

These are the `legacy` preset's inputs.

| field | use |
|---|---|
| `canvas.width/height/fps` | Composition size (output pixels) and frame rate. |
| `canvas.reference_width` | Width the design is written for (default 1080); the design scale is `width / reference_width`. |
| `safe_zone.top/bottom/left/right` | Maximum text width, plus the safe-zone assertion. |
| `safe_zone.right_rail` | Only checked by the assertion. The layout does not avoid it. |
| `typography.display` | Font for `hook` and `place`. |
| `typography.body` | Font for `fact` and `line`. |
| `typography.*.family/weight/size` | Font family (Playfair Display and Inter are loaded from `@remotion/google-fonts`), weight, size in reference px. |
| `typography.*.case` | `upper` and `lower` transform the text. `sentence` keeps it as written, so "POV" survives. |
| `typography.max_words_per_line`, `max_lines` | Line breaking (see below). |
| `colors.text`, `colors.text_shadow` | Text colour and soft shadow (`0 2px 12px`). |
| `colors.backdrop` | Rounded pill behind the text (padding 16/28 px, radius 24 px). |
| `overlay_positions[type]` | `anchor: "top-left"` puts the pill's top-left at (`x`, `y`). `anchor: "center"` centres the pill horizontally on the canvas, with its vertical centre at `y`. |
| `animation.in` | `frames`, `ease` and `distance_px` drive the fade plus slide-up. |
| `animation.out` | `frames` and `ease` drive the fade-out. |
| `animation.min_hold_s` | Gives a warning when `duration_s` is shorter. |

`ease` names are `linear` or `in|out|in-out` + `-` + `quad|cubic|sin|exp|circle`
(for example `out-cubic`). Not read: `colors.accent`, `typography.*.file`, and
everything about pacing, look and audio.

**Line breaking.** A `\n` in `text` is a forced break: each paragraph is laid out on its own lines with the rules below, all at one font size (a list header "my type:" over its item). Words are split into the fewest lines that respect
`max_words_per_line`, and the text must also fit the width the safe zone
leaves. Among the valid splits it picks the most balanced one, measured with
the real font. If no split up to `max_lines` fits, it shrinks the font, to no
less than 60%, and warns `FONT_SHRUNK`. If the text has more words than
`max_words_per_line × max_lines`, the extra words go on the last line with a
`TEXT_OVERFLOW` warning. For example, "POV: Potsdam at golden hour" fits the
5-word limit but is about 950 px wide at 72 px, so it breaks into two lines.

**Safe-zone assertion.** On the first fully faded-in frame, the composition
measures the pill's layout box. The bottom edge includes the slide distance.
It scales that box to canvas pixels, compares it with `safe_zone` (also scaled), and logs
`[cf-overlay] SAFE_ZONE_OK …` or `[cf-overlay] WARN SAFE_ZONE_VIOLATION …`.
`render.mjs` relays this and sets `safe_zone_ok` in the summary.

## Measured at 2160×3840 (M2, 8 GB, 2026-10-11, Resolve open and idle)

reel-01, preset `tiktok-hype`, measured with `/usr/bin/time -l` and a 0.5 s `ps` sampler over the process tree:

| overlay | frames | wall time 4K | wall time 1080 (same harness) | largest process RSS 4K (1080) | summed tree RSS 4K (1080) | file 4K (1080) |
|---|---|---|---|---|---|---|
| s01 `hook` upper-center | 75 | 12.8 s | 4.9 s | 0.97 GB ffmpeg (0.46 GB node) | 1.77 GB (1.49 GB) | 23.5 MB (8.9 MB) |
| s03 `place` lower-left-loose | 71 | 11.1 s | 4.0 s | 1.02 GB ffmpeg (0.50 GB node) | 1.78 GB (1.43 GB) | 12.5 MB (3.7 MB) |
| s04 `place` upper-left | 72 | 11.1 s | – | 0.96 GB ffmpeg | 1.77 GB | 12.0 MB (3.4 MB) |
| s06 `place` default | 71 | 11.2 s | – | 1.00 GB ffmpeg | 1.77 GB | 11.9 MB (3.6 MB) |

At 4K a render takes about 2.5× as long, and the ProRes encoder (ffmpeg, about 1 GB)
becomes the largest process. Files are 3–3.5× larger.

## Measured at 1080×1920 (M2, 8 GB, 2026-10-10, other jobs running)

| overlay | frames | wall time | largest process RSS | summed tree RSS |
|---|---|---|---|---|
| `place` "Potsdam, Sanssouci", 3 s | 90 | 5.3 s | ~0.46 GB | ~1.6 GB |
| `hook` "POV: Potsdam at golden hour", 2.5 s | 75 | 4.8 s | ~0.55 GB | ~1.5 GB |

- The very first render took 29.5 s, because of the cold bundle and Chrome start.
- Each render re-bundles, which accounts for roughly 2–3 s of the ~5 s.
- File size is about 4–5 MB per second of overlay.
- The summed tree RSS counts Chrome's shared pages more than once, so it overstates real usage.

ffprobe of the output shows `prores`, profile `4444`, tag `ap4h`, 2160×3840 (the canvas),
`30/1`, and colour tags bt709 for primaries, transfer and matrix.
`pix_fmt` reads `yuva444p12le`, which is how ffmpeg's ProRes decoder reports
4444. It was encoded from `yuva444p10le`.

## Known limits

- The fonts come from Google's CDN at render time, so a render needs a network
  connection. Only the face in use is fetched. Known families are listed in
  `src/fonts.ts` (Playfair Display, Inter, Inter Tight, Cormorant Garamond,
  Cormorant SC, Space Grotesk, Montserrat, Bodoni Moda, Great Vibes, Unbounded,
  Special Elite, Caveat). Any other family falls back to a locally installed font
  with a `FONT_FALLBACK` warning.
- Rotation (`rotate`) is not included in the safe-zone measurement; keep it to a few degrees.
  `typography.*.file` is not supported yet.
- The right rail (`safe_zone.right_rail`) is only checked. Text placed low
  on the right would be reported, not moved.
- The text shadow blur (about 12 px) reaches slightly past the measured pill box.
- When a clip is shorter than the in and out animations combined, each
  animation is cut to half the clip.
- Every render bundles again. For a long batch, a Node script using
  `@remotion/bundler` plus `@remotion/renderer` with one bundle would be
  faster. That is not done here.
- In Studio (`npm run dev`), the default props come from `../style.json`.
- Licence: Remotion is free for individuals and teams of up to 3. See the 5.0
  terms in `docs/research/02-overlays-and-motion-graphics/result-a.md`.
