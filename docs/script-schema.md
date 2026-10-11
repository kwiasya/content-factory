# Script schema

A Script is the text plan of one Reel, written before anything touches Resolve. One file: `reels/<reel>/script.json`. Terms: see `GLOSSARY.md`. Evidence for the rules: `docs/research/06-reels-scripts-and-ai-landscape/result-a.md`.

## Fields

| Field | Type | Rule |
|---|---|---|
| `schema` | `"cf-script/1"` | — |
| `walk` | string | Walk id, e.g. `potsdam-2026-10-04` |
| `concept` | string | One sentence, one idea. The hook must promise what the first shot shows. |
| `audience` | string | Who this is for, one line, from `style.json` unless overridden |
| `format` | enum | `pov` · `listicle` · `levels` · `day_in_the_life` · `reveal` · `contrast` |
| `target_length_s` | int | From `style.pacing.target_length_s` (15 s default while reels have no voice); never above 90 |
| `hook.type` | enum | `visual_payoff` · `pov` · `list` · `contrast` · `question` · `curiosity` |
| `hook.text` | string | ≤8 words, on screen from frame 0 |
| `hook.clip` | clip id | The most striking Clip, not the chronologically first |
| `shots[]` | list | Ordered. Each: `clip`, `in_s`, `out_s`, `role` (`hook` · `build` · `payoff` · `loop`), `speed` (1.0 default), `overlay` (`{text, type}` or `null`, type ∈ `place` · `fact` · `line`), `transition` (`cut` · `dissolve` · `dip`), `beat_index` (int or null) |
| `shots[].id` | string, optional | Shot id used for markers, `cuts.json` and `overlays/<id>.mov`; defaults to `s01`, `s02`, … by position |
| `shots[].reframe` | object, optional | How a clip wider than the canvas (landscape on the 9:16 canvas) fills it: `{mode, x, x_end, zoom}`. `mode` ∈ `follow` (a static window placed on the person by the build) · `center` · `pan` (a fixed window at `x`) · `smart` (Resolve Smart Reframe; opt-in only, it leaves black bands). `x` −1..1, pan only and required for it: −1 = window at the left edge of the source, 1 = right edge. `x_end` (pan only, −1..1) is recorded but not animated: the API cannot keyframe Pan, so the build applies a static pan at `x`. `zoom` ≥ 1 (default 1): extra zoom over "source height fills the canvas height". Default when absent: `style.json` `reframe.default` (`follow`) for a clip wider than the canvas, none otherwise. Only allowed on a clip whose aspect differs from the canvas, and only for clips wider than it. See Reframe below |
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
| `metrics` | object or null | Reserved: `avg_watch_time`, `shares`, `saves`, `reach`, filled by hand after publishing |

## Writing rules

Positive rules, each one checkable by the validator (`src/cf/script_schema.py`):

- Hook text is 5–8 words and sits inside the safe zone from `style.json`; `hook.clip` is the first shot's clip.
- A shot's `transition` is the one into that shot (on the first shot: from black). Durations are timeline seconds: `(out_s − in_s) / speed`.
- One overlay per scene or location change; each overlay holds ≥2 s; ≤8 words.
- Shots are ordered for impact: the Script reorders Clips freely, chronology is one option among many.
- Every `in_s`/`out_s` lies inside the Clip's duration and the shot lasts 1.5–5 s, longer only for `payoff`.
- Total duration equals `target_length_s` ± 3 s.
- A number in the hook comes with the mechanism in the same line.
- The stake comes before any name: say what the viewer gets, then name the place.
- Text reads without sound: overlays carry the story.
- Only the user's own footage; no watermarks.
- No on-camera speech: a shot never overlaps a second flagged `speech_on_camera` in the Shot log (until the voiceover phase). Off-camera speech (the author filming) is allowed; music covers it.

## Reframe (landscape clips on the vertical canvas)

`cf.build` scales a landscape clip so its height fills the canvas (Resolve's own fit is fit-width, which letterboxes) and shows a 9:16 window of it. On 2160×3840 the window is 1215×2160 source px of a 3840×2160 DJI clip (upscaled ×1.78) and 607×1080 of a 1920×1080 iPhone clip (×3.56, visibly soft even with Super Scale 2x). Math and probe evidence: `src/cf/reframe.py`.

- `follow` (default): `cf.follow` runs the shot-log person detector (Ultralytics nano + ByteTrack, conf 0.1) on the proxy at 5 fps over the shot's range, takes the subject (the track with the largest summed box height), and picks the one static window that holds her whole box in the most frames; ties go to the window holding the latest frames (the end of a shot is where she looks into the lens). It never leaves the source and has no Tilt, so it can never show black. When her box is wider than the window (close, arms out, carrying the pool ring), no frame fits and the window with the most overlap wins. With `loop_seamless`, a first and last shot that are both `follow` on the same clip share one window computed over both ranges. The build report has the window x and the coverage per shot; detections are cached in `<reel>/follow-boxes.json`. A person crossing the frame cannot be held by a static window: reel-01 s01 walks from 0.53 to 0.15 of the width.
- `smart` (opt-in only; the author rejected it for black bars) follows the subject horizontally **and vertically** and does not stop at the source edge. At `zoom` 1 a subject above or below the centre leaves a black band (470 px in the probe); the build exports 5 frames of every smart shot, fails on a band and suggests the `zoom` that hides it (1.35 in the probe). Choose `zoom` ≥ 1.3 up front for a subject far from the vertical centre.
- `pan` with `x` picks a fixed window; use it when the subject is static or `smart` picks the wrong person.
- A `loop_seamless` Reel needs the same reframe on the first and last shot (validator): same mode and zoom, and a pan whose end (`x_end`, else `x`) is the first shot's `x`. Two `smart` shots are analysed separately and can still jump a little at the seam: check it in Resolve.

## Seamless loop (`ending: loop_seamless`)

Every Reel loops: Instagram replays it without a gap, so the last frame should be followed by the next frame of the same action. Take one continuous action from one Clip and split it at a seam P: the first shot plays P→Q, the last shot plays O→P. The validator checks:

- `shots[-1].clip == shots[0].clip`.
- `shots[-1].out_s == shots[0].in_s` within half a frame at the Clip's fps (manifest `fps`; without a manifest, the timeline's).
- Both shots at `speed` 1.0.
- `shots[0].transition` is `cut` and `shots[0].fade_in_s` is 0; `shots[-1].fade_out_s` is 0. The first play starts with a hard cut from black; the loop has no black.
- `shots[-1].overlay` is null. An overlay fills its shot, so one on the last shot would vanish at the seam. The hook overlay on the first shot is fine: it fades in after the seam.

Choose the hook from a Clip whose preceding seconds are usable, so the last shot (1–1.5 s, about 3 beats) can be the run-up. On a beat grid, end the last shot on a downbeat; its `in_s` is P minus its frame count, so the build lays it exactly up to the hook's first source frame (`cf.build` checks the seam in its read-back). The music cannot loop seamlessly: it restarts at `track_in_s` when the picture does.
