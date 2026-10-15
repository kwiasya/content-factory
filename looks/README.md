# Looks

`<name>.json` is a Look spec; `python -m cf.look build looks/<name>.json -o looks/<name>.cube` writes the 33-point LUT in the timeline space (DWG / DaVinci Intermediate). cf.build puts the LUT on node 1 of the `cf-look` group's post-clip graph (`--look looks/<name>.cube`, or `style.json` `look.lut`).

Since 2026-10-12 no Look is applied by default (`style.json` `look.lut` is null): the author's rule is original colour, as on her Mac (ADR 0011). These files are kept for an explicit `--look` only.

## author-day.cube

The author's own hand grade of reel-01 "my type" (walk 2026-09-13, daylight meadow), made in Resolve on 2026-10-12. It has no JSON spec: it is Resolve's `TimelineItem.ExportLUT` (33 points) of her one-node clip grade. All five clips gave the same file.

- Compared with Resolve's plain HLG → Rec.709 conversion it is about 42 luma levels darker (mean 200 → 158), with 2.4× the saturation, a lavender sky with no clipping, and pinker, more saturated skin.
- She graded on an SDR build without the −1.02 stop HLG CDL and without a Look (`cf.build --hlg-normalize none --look none`), so use it on the same kind of build.
- Probably a timeline-space LUT (DWG / DaVinci Intermediate). It is not a Rec.709 display LUT: on Rec.709 stills it gets only halfway to her result. Check the stills before trusting it on other footage.
- For reel-01 itself, re-apply the exact grade from `reels/reel-01/author-grade/*.drx` (`cf.build --grade-drx`), not this LUT.
