# Format: Text list

- id: `text-list`
- Platform: Instagram Reels first; YouTube Shorts and TikTok as reposts
- Length: 8–12 s, one take, vertical 2160×3840 at 30 fps
- Source: one calm take of the Author from her own Footage (a walk, a studio or photo shoot); the Author picks it from a board of candidates
- Text: a list adapted from a concrete reference and localized into natural English, on screen from the first to the last frame
- Face and voice: her face and figure, no voice; the list carries the joke
- Sound: none. The file has a silent track; the Author adds the sound in Instagram
- Style profile: `formats/text-list/style.json`
- Build: no composer yet. The list is one overlay from `overlays/render.mjs` (preset `tiktok-list`, `style_path` this profile), laid over the take with ffmpeg by hand; `python -m cf.render_check --format text-list` checks the file, `cf.publish` hands it over
- First Video: "Офис — нишевые слова для парня" (2026-10-19; reference: the Russian reel «как нишево заменить слово «парень»», @3greenindex; `~/Movies/content-factory/videos/ofis-nishevye-slova/`, built ad hoc with Script `cf-textlist/1` before this Format)

## Text

- **Reference**: every list starts from a concrete viral list and is adapted to her. A Russian one is localized, not translated: native English idioms and online phrases, the same mechanism and punch (`formats/meme-cut/FORMAT.md`, Reference).
- **Style `tiktok-list`** (`overlays/src/presets.ts`): TikTok Sans SemiBold 600, white, lowercase, a 4 px round black outline, no shadow, no box. Title 64 px at line height 1.12, then +24 px, then the items at 56 px at 1.14 (not below 48 for a long list). In the text, a blank line (`\n\n`) ends the title.
- **Key words**: exactly one coloured key word or phrase per line, the title included: `{words|pink}`. The colours cycle pink, yellow, cyan, lime, orange, line by line, with the same black outline.
- **Placement**: left-aligned at x 140, right edge ≤ 950; sides 130 px (Instagram crops ~98 px a side on a tall phone), top ≥ 14 % of the height, the whole list above the bottom 35 %, off her face.
- Why this style: the author approved it on 2026-10-19 after the text-style research (`~/Movies/content-factory/research/text-style-2026-10.md`): a viral list reads as a plain compact font with one saturated word per line; the old Nunito Black with outline and shadow looked like a meme generator.

## Footage and the file

- One continuous take where she looks calm and pretty, posed or seated rather than walking; the Editor shows 3–6 candidates on a board and the Author picks.
- Original colour (an HDR Clip through its Apple SDR mezzanine, no grade), the take's sound dropped, a silent stereo track.
- Caption: one short deadpan line in English that plays off the list (one emoji at most), up to 5 hashtags. No CTA.
