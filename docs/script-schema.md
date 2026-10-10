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
| `shots[].fade_in_s`, `fade_out_s` | number, optional | Fade from/to black on picture and sound, seconds (default 0) |
| `ending` | enum | `loop_match` (last shot continues into frame 0) · `reveal_last` · `question_overlay` |
| `cta` | string | A send or save prompt |
| `caption` | string | First line carries the place name; then 1–3 lines of value; then the CTA |
| `hashtags` | list ≤5 | Mix of place, niche, format |
| `location_tag` | string | Always set |
| `alt_text` | string | 1–2 descriptive sentences |
| `track` | path or null | The Track the user supplied; null until given |
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
- No speech: a shot never overlaps a second flagged `speech` in the Shot log (until the voiceover phase).
