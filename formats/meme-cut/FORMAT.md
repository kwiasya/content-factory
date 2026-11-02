# Format: Meme cut

- id: `meme-cut`
- Platform: Instagram Reels first; YouTube Shorts and TikTok as reposts
- Length: 6–9 s, vertical 2160×3840 at 30 fps
- Source: one fitting Clip of the Author (the setup), optionally 1–2 more of her own shots, from any Footage with a clip manifest: a walk, a studio or photo shoot; plus Meme inserts from the Library
- Script: `cf-memecut/1`, `script.json` in the Video folder (fields below); the Editor writes it, the Author only approves the finished draft
- Face and voice: her face and figure in the setup, no voice; the text carries the joke
- Sound: none. The file has a silent track; the Author adds the sound in Instagram
- Ending: `last_meme`: the cut ends on its last Meme insert
- Style profile: `formats/meme-cut/style.json` (every number below lives there)
- Build: `cf.memecut` with ffmpeg, not Resolve: a Meme insert sits over a blurred copy of itself, and Resolve FX on a clip are outside the API (`docs/resolve-rules.md`, Known gaps; ADR 0012)
- Pipeline: `/meme-cut`
- First Video: "Потсдам — effortless" (2026-10-19, the approved 7.0 s cut; reference TikTok @malyshka894 "looked vs felt"; Script `~/Movies/content-factory/videos/potsdam-sbory/script.json`)

## Structure

Two blocks: her own footage first, then the memes. Her clips and the memes never interleave (author, 2026-10-21: "должно быть чётко мои кадры и только потом мемы, не вперемешку").

1. **Her block.**
   - **Setup**, 2.3–3 s: her own calm, pretty footage (Original colour: an HDR Clip through its Apple SDR mezzanine, no grade), full frame. The setup line is on screen from frame 0.
   - **Own shots** (`own`, optional): at most 2 more of her own shots, 1–3 s each (e.g. a punch shot of her), in Original colour. Each may carry its own line (`me, ready:`), placed off her face like the setup's.
2. **The meme run.** A hard cut to the punch line (`me 1 hour before leaving:`, `my brain:`, `how it actually felt:`), held to the last frame over **3–6 Meme inserts** of about 1 s each (2–6 after an own shot).
3. **The last Meme insert** is the strongest beat and holds longest (1–1.5 s). The cut ends on it.

The cut from calm footage to chaos at second 2–3 is the joke: how it looked against how it felt.

The order follows the Script's story beat by beat (author, 2026-10-21: "чтобы мемы шли логично, можно миксовать меня из разных папок, если это идёт логично в сценарии"):
- **Her shots** may come from different Footage (`setup.footage` and each `own[].footage`), whenever that tells the story better. The setup never gives the punch away. For example, "Берлин — wood" opens on the umbrella walk and shows the wooden-blocks room only in the own shot `me, ready:`.
- **The memes** read as one escalating reaction to what came just before them: the first one reacts, the next one escalates, and the last one lands the beat. Each meme answers its own line, such as `him:` reacting to her `me, ready:` shot. Order them by that logic, not by availability.

The approved cut: setup 2.5 s, three inserts of 1.0 s, the last of 1.5 s, 7.0 s in all.

## Reference

Every Meme cut starts from a concrete reference (a viral reel she sent, or one from research) and adapts it to her: her footage, her look, her life. The Script names it in `reference`. The premise comes from the reference; the Editor adapts it.

A reference in Russian (or any other language) is localized, not translated:
- Write each line the way native English speakers say it online: their idioms, set phrases and meme formats ("the call is coming from inside the house", "it's giving…", "the audacity", customer-service or call-centre phrases).
- Keep the joke's mechanism and punch; swap a culture-bound reference or pun for an English one that lands.
- Test: an English-speaking viewer gets it on first read, and it reads as written in English.

## The match rule

Every Meme insert, the last one included, shows literally the same situation as the setup and punch text. A dating setup takes memes of dates, flirting, texting a crush; a getting-ready setup takes memes of closets, try-ons, clothes flying. An emotion alone (panic, a stare) is not a match.

Why: on the first Meme cut (dating text over work-chaos memes, plus a Cillian Murphy stare that reads as calm) Kostya did not get the joke on the first watch.

How it is enforced: the Script names its `situation` as one Library tag (`свидание`, `сборы`, `монтаж`), and every insert's Asset carries that tag (`cf.memecut validate` fails otherwise); each insert also says in `shows` what it literally shows. When no Asset carries the situation, the cut needs new memes (below), not a looser tag.

## Text

- English, lowercase, deadpan: no exclamation marks. Setup ≤10 words, punch ≤6.
- The setup line is either someone else's line, written as `everyone:` or `him:` (for example `everyone: your outfits always look so effortless`), or her own line. These are examples; each cut finds its own line in its reference.
- An emoji goes on screen only when it fits the video or the text; at most one in the whole cut.
- **Style `tiktok-caption`** (`overlays/src/presets.ts`): TikTok Sans Medium 64 px (60–72 allowed), line height 1.2, white, soft shadow `0 3px 10px rgba(0,0,0,.75)`, no outline, no box, centred, at most 820 px wide. Why: it is the natural, native TikTok caption look; the old Nunito Black with outline and heavy shadow (`bold-outline-wide`, now legacy) looked like a meme generator (author, 2026-10-19). Research: `~/Movies/content-factory/research/text-style-2026-10.md`.
- **Outlined variant**: `"style": "stroke"` on a text gives `tiktok-caption-stroke`, a 2 px black outline in place of the shadow. Only for a line over a bright or white background.
- **Key word**: exactly one key word or phrase in the whole text, in colour: the setup's pink, an own shot's and the punch's yellow. None is a warning, two a problem.
- **Size**: 64 px (reference, 1080 wide); outside 60–72 px the validator fails. A line too wide is broken with `\n`, not set smaller.
- **Placement**: the setup sits at 24–35 % of the height (top edge at y 461–672), off her face. The punch sits in the blurred band, its bottom edge 24–40 px above the top edge of the highest meme; the build computes it (`text.punch_anchor.above_meme_px`).
- **Safe zone**: all text sits below the top 14 % of the frame, above the bottom 35 % and clear of the right rail, so the Instagram header, caption and buttons leave it readable. The renderer measures every line against it.
- **Sides**: text stays ≥130 px (reference) from both sides, which is why a line is at most 820 px wide: Instagram fills a tall phone (19.5:9) with the 9:16 Reel by height and crops ~98 px off each side (her post "Офис — нишевые слова для парня", 2026-10-19, lost the list's left edge). The build fails text closer than 130 px to a side.
- **Off her face**: the setup line sits on free sky or background. When the joke is about the outfit, the setup shows her full figure, the whole outfit. The text stays at least 20 px (reference) off her body: pick `setup.anchor` (and an own shot's `anchor`) off the frames; the build checks each with the person detector.
- Write it with `author/how-i-talk.md` and `author/joke-log.md` open, starting from the reference (above); log her verdict in the joke log.

## Meme inserts on the canvas

- **blur-fill**: a low-res or landscape meme sits whole at full width, centred, over a blurred, darkened, zoomed copy of itself.
- **fill**: a source at least as large as the canvas (short side ≥2160, a 4K shot) covers the frame with a centred crop.
- `auto` (the default) picks between them by that size rule. Nothing is ever stretched.
- `trim` cuts logos, watermarks and burned captions off the edges first, so they appear in neither the picture nor the blur. Trim a meme to leave room for the punch line above it.

## Caption

One short deadpan line in English that adds to the text on screen (≤10 words, one emoji at most), up to 5 hashtags. No geotag by default: the joke is not about a place (author, 2026-10-21: "в формате мем не привязывайся к гео, тут на него пофиг"); add one only when the place is part of the joke. No CTA, no alt text.

## Where memes come from

- Library Packs `memes` (`<shared root>/packs/memes/clips/`, with `index.json`: source page, resolution, watermark notes) and `memes-inbox` (a copy of her iCloud folder `Мемы/` at `<shared root>/packs/memes-inbox/`; `docs/shared-setup.md` N7). Find them by tag: `python -m cf.library query --pack memes --tag <situation>`.
- Her `Мемы/ссылки.txt` holds links with a note on what each is for. Download a link into `memes/clips/` (ask her first) with an `index.json` entry, then re-index the Pack and tag it (`/index-pack`).
- Prefer clean sources: no broadcaster logo, no burned captions; the largest rendition there is.
- Only the picture of a meme goes in; its sound stays out.

## What flops

- Memes about another situation than the text (the first cut: work chaos under a dating setup).
- A stock disaster shot (explosion, fire, storm) that is not the text's situation.
- Her shot between memes, or her setup shot repeated at the end: her shots all come before the first meme.
- A meme whose emotion contradicts the punch (a calm stare in a panic run).
- A setup longer than 3 s: the cut comes too late.
- Meme-generator text: a heavy rounded font with an outline and a heavy shadow, Impact in caps.
- Text under the Instagram header, caption or buttons, or nearer than 130 px to a side.
- A literal translation of a foreign reference that loses the joke.
- Uppercase, exclamation marks, a long caption, a CTA.

## Script (`cf-memecut/1`)

| Field | Rule |
|---|---|
| `schema` | `"cf-memecut/1"` |
| `title` | The name in "Готовые ролики" (Russian), e.g. "Потсдам — effortless" |
| `reference` | The reel this cut adapts (account, link, name); a missing one is a warning |
| `concept` | Optional: the premise and how it is adapted |
| `situation` | One lowercase Library tag every insert carries (the match rule) |
| `setup` | `footage` (the Footage id under the local root with a `clip_manifest.json`: a walk, a shoot; the legacy `walk` is still read), `clip` (file name in that manifest), `in_s`, `dur_s` (2.3–3), `text`, optional `size` (60–72 reference px), optional `anchor` (a slot name or `{anchor, x?, y, align?}` in reference px, as in `docs/script-schema.md`), optional `style` (`stroke`), optional `trim` |
| `own` | Optional, at most 2 of her shots after the setup, before the inserts: `{footage?, clip, in_s, dur_s (1–3), text?, size?, anchor?, style?, trim?}`; `footage` defaults to the setup's; `text` (≤6 words, key word yellow by default) is on screen over that shot only. An insert or finale with `footage`/`clip` fails: her clips never go between memes |
| `punch` | `text`, optional `size`, optional `anchor` (default: the band above the highest meme), optional `style` (`stroke`); on screen over the meme run only |
| `text` | `\n` breaks a line. The key word is `{words}` or `{words\|colour}`, a palette name (`pink`, `yellow`, `cyan`, `lime`, `orange`); a bare mark is pink in the setup and yellow in the punch. One per text: none is a warning, two or more a problem |
| `inserts[]` | 3–6 (2–6 with an `own` shot) of `{ref, in_s, dur_s, shows, fit?, trim?}`; `dur_s` 0.8–1.2, the last 1–1.5; `ref` is a Library Asset ref; `fit` ∈ `auto` · `blur-fill` · `fill` |
| `trim` | `{left?, right?, top?, bottom?}`: whole source px cut off each edge |
| `ending` | `last_meme` (may be omitted; `reveal_last` is its old name) |
| `caption`, `hashtags`, `location_tag` | As under Caption; `cta` and `alt_text` are rejected |
| `finale` | Deprecated. An old Script's `{ref, in_s, dur_s (1–1.5), fit?, trim?, shows?}` still validates and builds, with a warning; there the last insert is an ordinary one |

Durations are checked in frames at 30 fps (`round(s × 30)`); the total is 6–9 s. Unknown keys fail.
