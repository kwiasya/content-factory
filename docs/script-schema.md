# Script schema

A Script is the text plan of one Reel, written before anything touches Resolve. One file: `reels/<reel>/script.json`. Terms: see `GLOSSARY.md`. Evidence for the rules: `docs/research/06-reels-scripts-and-ai-landscape/result-a.md`.

## Fields

| Field | Type | Rule |
|---|---|---|
| `schema` | `"cf-script/1"` | — |
| `walk` | string | Walk id, e.g. `potsdam-2026-10-04` |
| `concept` | string | One sentence, one idea. The hook must promise what the first shot shows. |
| `canvas` | string, optional | Output canvas: a `style.json` `canvases` name (`portrait` · `landscape`) or `WxH`. Absent = `style.json` `canvas` (2160×3840 portrait). `landscape` = 3840×2160 16:9 with its own safe zone and overlay positions; cf.build, cf.render, cf.render_check and the overlay specs honour it, and their `--canvas` wins over it. Landscape clips on a landscape canvas get no reframe |
| `audience` | string | Who this is for, one line, from `style.json` unless overridden |
| `format` | enum | `pov` · `listicle` · `levels` · `day_in_the_life` · `reveal` · `contrast` |
| `target_length_s` | int | From `style.pacing.target_length_s` (15 s default while reels have no voice); never above 90 |
| `hook.type` | enum | `visual_payoff` · `pov` · `list` · `contrast` · `question` · `curiosity` |
| `hook.text` | string | ≤8 words, on screen from frame 0 |
| `hook.clip` | clip id | The most striking Clip, not the chronologically first |
| `shots[]` | list | Ordered. Each: `clip`, `in_s`, `out_s`, `role` (`hook` · `build` · `payoff` · `loop`), `speed` (1.0 default), `overlay` (`{text, type}` or `null`, type ∈ `place` · `fact` · `line`), `transition` (`cut` · `dissolve` · `dip`), `beat_index` (int or null) |
| `shots[].id` | string, optional | Shot id used for markers, `cuts.json` and `overlays/<id>.mov`; defaults to `s01`, `s02`, … by position |
| `shots[].reframe` | object, optional | How a clip wider than the canvas (landscape on the 9:16 canvas) fills it: `{mode, x, x_end, zoom, hold_s}`. `mode` ∈ `follow` (a static window placed on the person by the build) · `center` · `pan` (a fixed window at `x`) · `smart` (Resolve Smart Reframe; opt-in only, it leaves black bands). `x` −1..1, pan only and required for it: −1 = window at the left edge of the source, 1 = right edge. `x_end` (pan only, −1..1) is recorded but not animated: the API cannot keyframe Pan, so the build applies a static pan at `x`. `zoom` ≥ 1 (default 1): extra zoom over "source height fills the canvas height". Default when absent: `style.json` `reframe.default` (`follow`) for a clip wider than the canvas, none otherwise. Only allowed on a clip whose aspect differs from the canvas, and only for clips wider than it. See Reframe below |
| `shots[].assets` | list, optional | Library Asset cues placed from this shot: `[{ref, at_s, dur_s?, pos?, db?}]`; absent or `null` = none. See Assets below |
| `shots[].fade_in_s`, `fade_out_s` | number, optional | Fade from/to black on picture and sound, seconds (default 0) |
| `ending` | enum | `loop_seamless` (default: the last shot is the run-up into the first shot's first source frame, see below) · `loop_match` (weaker: the last shot ends in a similar pose or move to frame 0) · `reveal_last` · `question_overlay`. Default from `style.ending.default` |
| `cta` | string | A send or save prompt |
| `caption` | string | First line carries the place name; then 1–3 lines of value; then the CTA |
| `hashtags` | list ≤5 | Mix of place, niche, format |
| `location_tag` | string | Always set |
| `alt_text` | string | 1–2 descriptive sentences |
| `track` | path or null | The Track the user supplied (WAV; relative to the reel folder, e.g. `track/source.wav`); null until given. cf.build places it on A2 "music" |
| `track_in_s` | number, optional | Where the Track starts at timeline frame 0, in Track seconds; default `intro_end` from `beats.json` (the quiet start skipped). Resolve snaps it to a whole timeline frame |
| `track_fade_out_s` | number, optional | Fade-out of the Track at the end of the timeline, seconds (default 0.6) |
| `overlay_min_hold_s` | number, optional | Minimum overlay hold for this Script, seconds; replaces `style.json` `animation.min_hold_s` (2 s) in the validator, for a fast list Reel the author planned with shorter text beats |
| `metrics` | object or null | Reserved: `avg_watch_time`, `shares`, `saves`, `reach`, filled by hand after publishing |

## Writing rules

Positive rules, each one checkable by the validator (`src/cf/script_schema.py`):

- Hook text is 5–8 words and sits inside the safe zone from `style.json`; `hook.clip` is the first shot's clip.
- A shot's `transition` is the one into that shot (on the first shot: from black). Durations are timeline seconds: `(out_s − in_s) / speed`.
- One overlay per scene or location change; each overlay holds ≥2 s (or the Script's `overlay_min_hold_s`); ≤8 words (an emoji is not a word). A `\n` in overlay text is a forced line break.
- `overlay.span` (int ≥ 1, default 1) stretches one overlay over this shot and the next span−1 shots (one label for a place cut into short shots): it starts at this shot's record frame and lasts the spanned shots' summed duration (from `cuts.json` record frames when present), which is what the ≥2 s hold checks; the spanned shots carry no overlay of their own, and a span never reaches the last shot of a `loop_seamless` Reel.
- A `place` overlay says what the place is, not only its name: "Hotel: FlipFlop Cala Romantica", "Beach: Cala Romántica", "Park Babelsberg" is fine only when the name already says it (author rule, 2026-10-11).
- Shots are ordered for impact: the Script reorders Clips freely, chronology is one option among many.
- Every `in_s`/`out_s` lies inside the Clip's duration and the shot lasts 1.5–5 s, longer only for `payoff`.
- Total duration equals `target_length_s` ± 3 s.
- A number in the hook comes with the mechanism in the same line.
- The stake comes before any name: say what the viewer gets, then name the place.
- Text reads without sound: overlays carry the story.
- One self-ironic line about the author per Reel (beauty + self-irony is what people subscribe for), as a `line` overlay at the start or near the end, e.g. "me pretending I'm not freezing 🫠", "my feet after 5 castles 💀" (author rule, 2026-10-12).
- Time-limited events get urgency in the caption with the end date verified on the official site that year, e.g. "Festival ends on 18 October — go this weekend".
- Only the user's own footage; no watermarks.
- No on-camera speech: a shot never overlaps a second flagged `speech_on_camera` in the Shot log (until the voiceover phase). Off-camera speech (the author filming) is allowed; music covers it.

## Reframe (landscape clips on the vertical canvas)

`cf.build` scales a landscape clip so its height fills the canvas (Resolve's own fit is fit-width, which letterboxes) and shows a 9:16 window of it. On 2160×3840 the window is 1215×2160 source px of a 3840×2160 DJI clip (upscaled ×1.78) and 607×1080 of a 1920×1080 iPhone clip (×3.56, visibly soft even with Super Scale 2x). Math and probe evidence: `src/cf/reframe.py`.

- `follow` (default): `cf.follow` runs the shot-log person detector (Ultralytics nano + ByteTrack, conf 0.1) on the proxy at 5 fps over the shot's range, takes the subject (the track with the largest summed box height), and picks the one static window that holds her whole box in the most frames; ties go to the window holding the latest frames (the end of a shot is where she looks into the lens). It never leaves the source and has no Tilt, so it can never show black. When her box is wider than the window (close, arms out, carrying the pool ring), no frame fits and the window with the most overlap wins. With `loop_seamless`, a first and last shot that are both `follow` on the same clip share one window computed over both ranges. `hold_s` (follow only, a list of source seconds inside the shot) makes the window hold the whole person at those times, even when that costs other frames: Mallorca reel-01 holds the smile at the end of the hook (`hold_s: [122.19]`) and gives up the first 0.6 s of the run-up. The build report has the window x and the coverage per shot; detections are cached in `<reel>/follow-boxes.json`. A person crossing the frame cannot be held by a static window: reel-01 s01 walks from 0.53 to 0.15 of the width.
- `smart` (opt-in only; the author rejected it for black bars) follows the subject horizontally **and vertically** and does not stop at the source edge. At `zoom` 1 a subject above or below the centre leaves a black band (470 px in the probe); the build exports 5 frames of every smart shot, fails on a band and suggests the `zoom` that hides it (1.35 in the probe). Choose `zoom` ≥ 1.3 up front for a subject far from the vertical centre.
- `pan` with `x` picks a fixed window; use it when the subject is static or `smart` picks the wrong person.
- A `loop_seamless` Reel needs the same reframe on the first and last shot (validator): same mode and zoom, and a pan whose end (`x_end`, else `x`) is the first shot's `x`. Two `smart` shots are analysed separately and can still jump a little at the seam: check it in Resolve.

## Assets (Library cues)

A cue places one Library Asset (`@<category>/<name>`, `GLOSSARY.md` Asset ref) in the Reel: a sound effect on A3, a picture, meme, sticker or effect on V4, a meme's own sound on an A lane. Cues sit under the shot they start in:

```json
"assets": [
  {"ref": "@sfx/вуш-2", "at_s": 2.35},
  {"ref": "@face/шок", "at_s": 0.4, "dur_s": 1.2, "pos": "bottom-left"},
  {"ref": "@meme/chipi", "at_s": 0.0, "dur_s": 2.0, "pos": "center", "db": -3}
]
```

| Key | Type | Rule |
|---|---|---|
| `ref` | string, required | An Asset ref: canonical, file-derived or alias |
| `at_s` | number, required | Start in timeline seconds from the start of this shot (after speed); `0 ≤ at_s <` the shot's duration |
| `dur_s` | number, optional | Length on the timeline. Default: the Asset's length (sound, video); `style.json` `assets.still_s` (1.5 s) for a picture. A sound or video cannot loop or stretch (`≤` its length); a picture stays at most `assets.still_max_s` (5 s); at least one frame |
| `pos` | string, optional | Placement preset of a picture (table below); default `assets.default_pos[category]`. Not allowed on a sound |
| `db` | number, optional | Level offset in dB, `−24…+12`, on top of the level rule; only on a sound or a video with sound |

Unknown keys in a cue are violations. A cue may run into later shots, never past the end of the Reel. Cues place `sfx` (sound) and `meme`, `img`, `emoji`, `face`, `footage`, `fx` (picture, plus its sound when the file has one); `bg`, `music`, `font` and `template` are rejected (the Track is the Author's, fonts come from the Format).

Validator rules (`python -m cf.script_schema validate` loads the Library itself: the Video folder's footage root and `factory.db`, read-only; `--footage-root`, `--db`, `--no-library`). Warnings print as `- WARN …` and never fail. A Script without cues never opens the store.

- **The Library:** no Library (no `factory.db`, an old schema) is one problem for the whole Script.
- **Refs:** a ref that is not `@<category>/<name>` fails; an unknown ref fails with up to 5 nearest refs.
- **Rights:** `own` and `free` pass. `unknown` is allowed, with a warning, only for a sound effect under `assets.sfx_free_max_s` (2 s) or for an Asset the Author named in one of the Video folder's top-level md files (`brief.md`, `notes.md`, `voiceover.md`, …; any ref form counts). Otherwise it fails. The agent never writes refs into those files on its own.
- **Variant:** see below; a green-screen Asset that is not keyed yet, or a sticker with only a VP9 `.webm`, fails; a sticker placed from its still png is a warning.
- **Loudness:** a sound without a measured loudness fails (`python -m cf.library index <pack>` without `--no-loudness`).
- **Loop seam:** on a `loop_seamless` Reel a picture ends at least `assets.loop_clear_s` (0.5 s) before the end (it would blink away when the Reel restarts); sounds may run to the last frame.
- **Lanes:** at most 2 sounds (sound effects plus memes' sounds: A3, A4) and 2 pictures (V4, V5) at any instant.

Timing is checked on the back-to-back shot model; the build re-checks lanes and the end in frames (`cuts.json` can move a shot by a frame) and fails loudly.

**Positions** (`style.json` `assets.pos`, reference px of the 1080×1920 frame; `canvases.landscape.asset_pos` for 16:9). The Asset is scaled to fit inside the box, centred in it; every portrait box lies inside the safe zone and clear of the right rail.

| `pos` | portrait box (x, y, w, h) | landscape box |
|---|---|---|
| `center` | 290, 660, 500, 480 | 710, 290, 500, 500 |
| `top` | 290, 290, 500, 400 | 710, 70, 500, 400 |
| `bottom` | 300, 840, 480, 400 | 710, 540, 500, 400 |
| `top-left` | 80, 290, 400, 400 | 110, 70, 400, 400 |
| `top-right` | 600, 290, 400, 400 | 1410, 70, 400, 400 |
| `bottom-left` | 80, 840, 400, 400 | 110, 540, 400, 400 |
| `bottom-right` | 380, 840, 400, 400 | 1410, 540, 400, 400 |
| `full` | covers the canvas | covers the canvas |
| `fit` | fits inside the canvas | fits inside the canvas |

Defaults: `face` and `emoji` `bottom-left` (clear of Instagram's buttons), `meme`, `img`, `footage` `center`, `fx` `full`.

**Which file is placed** (`cf.assets.placement`, first that applies): a sound → its file; a picture with a Pack `alpha` variant (ProRes 4444) → that; green screen → the keyed ProRes in the cache; an animated gif → the converted file; an image → its png (the converted png for jfif/webp/avif; jpg and png as they are); a `.webm` → its still png, else nothing; otherwise the file itself. The Pack is only read.

**Level** of a sound cue: `raw = reference − 6 − asset LUFS + db`, where the reference is the Track's integrated loudness over the part used (A2 at 0 dB), else `style.audio.target_lufs` (−14) without a Track; capped so the Asset's true peak stays under `style.audio.true_peak_dbtp` (−1), clamped to `assets.gain_range_db` (−40…+12), rounded to 0.1 dB. So a sound effect sits 6 LU under the music before its `db`. The post-render −14 LUFS check stays the final gate.

## Seamless loop (`ending: loop_seamless`)

Every Reel loops: Instagram replays it without a gap, so the last frame should be followed by the next frame of the same action. Take one continuous action from one Clip and split it at a seam P: the first shot plays P→Q, the last shot plays O→P. The validator checks:

- `shots[-1].clip == shots[0].clip`.
- In frames, as Resolve places them (`src/cf/frames.py`): the last shot, continued by one timeline frame, shows the first shot's first source frame. At equal rates (and 60 on 30) that is `shots[-1].out_s == shots[0].in_s`. For a 29.97 clip on the 30 fps timeline the run-up starts one source frame later than the seconds say: its `in_s` is `run_up_start(P, n) / fps` and its `out_s` = `in_s + n / 30` ends a frame past P. The validator prints the in-point to use; cf.build derives it the same way.
- Both shots at `speed` 1.0.
- `shots[0].transition` is `cut` and `shots[0].fade_in_s` is 0; `shots[-1].fade_out_s` is 0. The first play starts with a hard cut from black; the loop has no black.
- `shots[-1].overlay` is null or a `line` (a self-ironic closing line, say): an overlay fills its shot and ends on the last frame, so a line hands over to the hook line at frame 0; a `place` or `fact` label there would vanish at the seam and is rejected. The same holds for a span that runs into the last shot. The hook overlay on the first shot is fine: it fades in after the seam.
- An Asset cue that shows a picture ends at least 0.5 s before the end (`style.json` `assets.loop_clear_s`); a sound cue may run to the last frame (see Assets).

Choose the hook from a Clip whose preceding seconds are usable, so the last shot (1–1.5 s, about 3 beats) can be the run-up. On a beat grid, end the last shot on a downbeat; its `in_s` is P minus its frame count, so the build lays it exactly up to the hook's first source frame (`cf.build` checks the seam in its read-back). The music cannot loop seamlessly: it restarts at `track_in_s` when the picture does.
