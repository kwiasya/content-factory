# Reference card schema

A Reference card is the deep analysis of one Reference, schema `cf-reference-card/1`. It lives in the research store (table `card`, the source of truth) and as a copy in `<shared root>/references/<watchlist>/<video_id>/card.json` (`/Users/Shared/content-factory`, ADR 0013). Terms: `GLOSSARY.md` (section Исследование). The fields follow the Sandcastles Video Detail page one to one (`docs/research/sandcastles-map.md`, "Поля deep analysis"). Code: `cf.research.card`.

```json
{"schema": "cf-reference-card/1", "measured": {…}, "analysis": {…} | null}
```

- `measured` is computed by `python -m cf.research fetch` from the Reference folder (`cf.research.measure`): duration, cut count and cuts per minute, first-shot length, first on-screen text, first person and face, speech onset, `spoken_hook` (words begun in the first 3 s), `language` (the Whisper code the transcript and captions are in: the video's own language, never translated), `language_source` (below; absent on cards measured before this field), transcript sections, chapters, heatmap peaks with quotes, and `notes` explaining every null. Fetching again rewrites `measured` and never touches `analysis`; `fetch --retranscribe` remakes the transcript, captions and Shot log from the media already in the folder. When a new transcript is made and the card has an analysis, fetch checks its `hook.spoken_hook` against the new transcript and reports the result in the `analysis` step (shown in the summary as well): `kept; stale: hook.spoken_hook … — re-run analyze-reference` means the analysis no longer quotes the transcript and `analyze-reference` should be run again.
- `language_source` says where `language` came from. The info is always checked: Whisper's detection runs on two 30 s windows, a third and two thirds in; only windows with speech (no-speech probability below 0.6) count. The Watchlist language is only a fallback. `transcript.json` keeps what the info said in `_info_language` and the windows with the verdict, or the error, in `_language_detection`; the `transcript` step of the fetch shows the verdict.
  - `info`: yt-dlp's `language` of the video (kept also when the detection fails, finds no speech, or is not sure).
  - `whisper`: Whisper's detection, when the info has no usable language, or when every window with speech names the same other language at 80 % or more.
  - `watchlist` or `default`: the fallback hint (the Watchlist's language, else `en`) when neither gives one, or a kept transcript has none.
  - `transcript`: a transcript kept from an earlier fetch that did not record the source.
- `analysis` is written by the Editor (skill `analyze-reference`), null until then. Saved only through `card save`, which validates it first.

## Analysis fields

All keys are required; unknown keys are violations. "text" means a non-empty string.

| Field | Type | Sandcastles field | Rule |
|---|---|---|---|
| `summary` | text | Summary | What the video is and why it worked, 1–3 sentences |
| `idea_analysis.topic` | text | Topic | The subject, a few words |
| `idea_analysis.idea_seed` | text | Idea Seed | The core idea someone else could reuse |
| `idea_analysis.unique_angle` | text | Unique Angle | What this video does that others on the topic do not |
| `idea_analysis.common_belief` | text or null | Common Belief to Challenge | null when the video challenges nothing |
| `idea_analysis.contrarian_reality` | text or null | Contrarian Reality | null exactly when `common_belief` is null: both or neither |
| `idea_analysis.supporting_evidence` | text | Supporting Evidence | What in the video backs the angle (moments, numbers, timestamps) |
| `hook.category` | taxonomy `hook_category` | Hook Category | See categories below |
| `hook.formula` | text | Hook Formula | The reusable template, e.g. "Place name + superlative, said over the best view" |
| `hook.spoken_hook` | text or null | Spoken Hook | The opening words as said; must quote the transcript (below). null only when the Reference has no speech |
| `hook.alignment` | text | Hook Analysis | How the rest of the video keeps the hook's promise |
| `storytelling_format.category` | taxonomy `storytelling_format` | Storytelling Format Category | |
| `storytelling_format.description` | text | Description | How this video runs the format |
| `storytelling_format.analysis` | text | Analysis | Why the format works for this idea |
| `visual_layout.category` | taxonomy `visual_layout` | Visual Layout Category | What carries the picture: `talking_head`, `screencast`, `broll_voiceover`, `pov_walk`, `text_on_footage`, `split` |
| `visual_layout.sub_category` | taxonomy `editing_style` | Visual Layout Sub-category | The Sandcastles editing-style card (`vlog_pov`, `faceless_visual_explainer`, `office_room_yap`, …) |

`sub_category` validates against `editing_style`, not `visual_layout`: the seed's editing styles are exactly the Sandcastles layout sub-types (their `note` names the Sandcastles group, e.g. "Studio/Set: …"), while our `visual_layout` values are the coarser categories of the research spec. The pair is not cross-checked; any approved editing style goes with any approved layout.

## Categories and `proposed:`

The vocabulary is the `taxonomy` table, seeded from `research/taxonomy.json`; list it with `python -m cf.research taxonomy list [--kind K] [--json]`. A category field holds either:

- an **approved** value of its kind, e.g. `"pov_walk"`; or
- `"proposed:<value>"` for a value the taxonomy lacks, `<value>` in snake_case (`a-z`, `0-9`, `_`).

Rules the validator applies:

| The field holds | Value's status in the taxonomy | Result |
|---|---|---|
| `x` | approved | valid |
| `x` | proposed (awaiting the Author) | violation: write `proposed:x` until it is approved |
| `x` | rejected, or absent | violation |
| `proposed:x` | absent or proposed | valid |
| `proposed:x` | approved | valid; saved as plain `x` |
| `proposed:x` | rejected | violation: pick an approved value |

On `card save`, every `proposed:x` whose value is not approved enters the taxonomy with status `proposed` and source `card:<video_id>`; the card keeps the prefix. `taxonomy approve <kind> x` makes `x` valid and drops the prefix in every card that proposed it (store and `card.json`). `taxonomy reject <kind> x` makes `x` invalid with or without the prefix and lists the cards that carry it, which then fail validation until rewritten. A rejected value stays rejected when the seed loads again, even if the seed lists it. Approving or rejecting a value the store lacks adds it with source `author`. Pending values: `taxonomy list --status proposed`.

## Spoken hook check

`hook.spoken_hook` must appear in the transcript as a run of whole words after normalizing both sides: lower case, apostrophes dropped, every other punctuation mark as a space, whitespace collapsed. So `"so  this is ALFAMA -- the oldest part of lisbon!"` quotes "So this is Alfama, the oldest part of Lisbon.", but `"his is Alfama"` does not. The hook may run past the first 3 s (`measured.spoken_hook` is only the opening). The transcript is `transcript.json` (stable-ts) from the Reference folder; when there is none, `measured.spoken_hook` is the only text to quote; with neither, a non-null spoken hook is a violation ("no transcript to check against"). A null spoken hook is valid only when both are empty (no speech).

## Commands

```
python -m cf.research card validate <video_id|url>              # the stored card
python -m cf.research card validate <card.json>                 # a whole card; transcript.json next to it if present
python -m cf.research card validate <analysis.json> --video <id> # an analysis against the stored measured card
python -m cf.research card save <video_id|url> <analysis.json>   # validates, stores, proposes
python -m cf.research card show <video_id|url> [--json]
python -m cf.research taxonomy list --status proposed
python -m cf.research taxonomy approve|reject <kind> <value>
```

Violations go to stdout one per line, exit 1, as `cf.script_schema` prints them:

```
INVALID analysis.json (2 violations)
- hook.category: 'shock_value' is not an approved hook_category; use one or write proposed:shock_value
- hook.spoken_hook: not found in the transcript: 'Welcome to Porto'
```

With `--json`: `{"target", "ok": false, "violations": [...]}`. `card save` and `card validate` report `proposed`: the card's values still awaiting approval.

## Example

```json
{
 "schema": "cf-reference-card/1",
 "measured": {"duration_s": 95.0, "spoken_hook": "So this is Alfama, the oldest part of Lisbon.", "…": "…"},
 "analysis": {
  "summary": "A slow evening walk through Alfama that ends on the river at sunset.",
  "idea_analysis": {
   "topic": "Walking Lisbon's oldest district",
   "idea_seed": "The old town is best seen on foot at golden hour",
   "unique_angle": "No narration after the first line; the stairs carry the story",
   "common_belief": "Alfama is a tourist trap",
   "contrarian_reality": "Ten minutes off the tram line it is empty",
   "supporting_evidence": "Empty alleys from 0:40 on; the sunset viewpoint at 1:30"
  },
  "hook": {
   "category": "visual_payoff",
   "formula": "Place name + superlative, said over the best view",
   "spoken_hook": "So this is Alfama, the oldest part of Lisbon",
   "alignment": "The promise of the oldest part pays off in the stairs and alleys"
  },
  "storytelling_format": {
   "category": "pov",
   "description": "First-person walk from the top of the hill to the river",
   "analysis": "The descent gives a natural arc that ends at the payoff"
  },
  "visual_layout": {"category": "pov_walk", "sub_category": "proposed:golden_hour_descent"}
 }
}
```
