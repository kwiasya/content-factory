# overlays

Remotion project that renders one text overlay for a Reel as a transparent
ProRes 4444 `.mov` (1080×1920, timeline fps, alpha). `build-reel` step 2 calls
it once per shot that has an overlay; the files go on V2/V3 in Resolve.

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
  `{"ok":true,"out":"…","type":"place","fps":30,"frames":90,"width":1080,"height":1920,"render_s":5.3,"safe_zone_ok":true,"warnings":[]}`
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

## Presets

A preset is one complete type system for every overlay type: font family, weight,
italic, size, case, tracking, line height, colour or gradient fill, shadow or glow,
backdrop / per-line box, rule, accent bar, ornament, rotation and placement. The
catalogue is `src/presets.ts`; style.json `typography.preset` selects one, and a
spec's `preset` overrides it for one render. The summary line reports `preset`.

| preset | hook | place label |
|---|---|---|
| `legacy` | the original design, read from style.json (Playfair Display, translucent pill) | same |
| `editorial-serif` | Cormorant Garamond Light Italic, lower-left | Cormorant SC, tracked |
| `clean-grotesk` | Inter Tight Medium, lower-left | Inter Tight uppercase, tracked, 1-px rule above |
| `lower-third-tag` | Space Grotesk SemiBold, centred mid-frame | Space Grotesk tag with an accent bar (`colors.accent`) |
| `tiktok-hype` | Montserrat ExtraBold uppercase, black on white per-line boxes, -3° | small white box tag |
| `pinterest-aesthetic` | Bodoni Moda lowercase, cream, tracked, centred mid-frame | lowercase, hairline under it |
| `coquette-girly` | Great Vibes script, soft pink, tilted | Cormorant Garamond italic + pink bow |
| `y2k-gloss` | Unbounded ExtraBold, pink→lavender gradient, glow | same, sparkles both sides |
| `diary-typewriter` | Special Elite lowercase on cream marker strips, top-left | same, e.g. "potsdam · 04.10" |
| `handwritten-note` | Caveat Bold with a hand-drawn squiggle underline, lower-left | Caveat, near the horizon |

With a non-legacy preset, the preset replaces `typography.display/body`,
`colors.text/text_shadow/backdrop` and `overlay_positions`. Still read from
style.json: `canvas`, `safe_zone`, `animation`, `colors.accent`,
`typography.max_words_per_line/max_lines` (unless the preset role sets its own).
Some presets assume a text convention: `pinterest-aesthetic` reads best with
"place, city"; `diary-typewriter` with "city · dd.mm". The renderer does not
rewrite text.

Anchors: `center`, `top-left`, `top-center`, `bottom-left`, `bottom-center`.
`bottom-*` puts the box's bottom edge at `y` at rest (the slide-in starts lower,
which the safe-zone check includes). The text width is limited by the safe zone,
by the right rail when the box can reach below `right_rail.from_y`, and by the
role's `maxWidth` (hooks keep to a ~600 px left column, place labels to ~470 px,
so a centred subject stays clear). Presets break lines after punctuation when they
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
| `canvas.width/height/fps` | Composition size and frame rate. |
| `safe_zone.top/bottom/left/right` | Maximum text width, plus the safe-zone assertion. |
| `safe_zone.right_rail` | Only checked by the assertion. The layout does not avoid it. |
| `typography.display` | Font for `hook` and `place`. |
| `typography.body` | Font for `fact` and `line`. |
| `typography.*.family/weight/size` | Font family (Playfair Display and Inter are loaded from `@remotion/google-fonts`), weight, size in px. |
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

**Line breaking.** Words are split into the fewest lines that respect
`max_words_per_line`, and the text must also fit the width the safe zone
leaves. Among the valid splits it picks the most balanced one, measured with
the real font. If no split up to `max_lines` fits, it shrinks the font, to no
less than 60%, and warns `FONT_SHRUNK`. If the text has more words than
`max_words_per_line × max_lines`, the extra words go on the last line with a
`TEXT_OVERFLOW` warning. For example, "POV: Potsdam at golden hour" fits the
5-word limit but is about 950 px wide at 72 px, so it breaks into two lines.

**Safe-zone assertion.** On the first fully faded-in frame, the composition
measures the pill's layout box. The bottom edge includes the slide distance.
It compares that box with `safe_zone` and logs
`[cf-overlay] SAFE_ZONE_OK …` or `[cf-overlay] WARN SAFE_ZONE_VIOLATION …`.
`render.mjs` relays this and sets `safe_zone_ok` in the summary.

## Measured (M2, 8 GB, 2026-10-10, other jobs running)

| overlay | frames | wall time | largest process RSS | summed tree RSS |
|---|---|---|---|---|
| `place` "Potsdam, Sanssouci", 3 s | 90 | 5.3 s | ~0.46 GB | ~1.6 GB |
| `hook` "POV: Potsdam at golden hour", 2.5 s | 75 | 4.8 s | ~0.55 GB | ~1.5 GB |

- The very first render took 29.5 s, because of the cold bundle and Chrome start.
- Each render re-bundles, which accounts for roughly 2–3 s of the ~5 s.
- File size is about 4–5 MB per second of overlay.
- The summed tree RSS counts Chrome's shared pages more than once, so it overstates real usage.

ffprobe of the output shows `prores`, profile `4444`, tag `ap4h`, 1080×1920,
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
