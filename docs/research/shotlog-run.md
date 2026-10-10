# Shot log: first run on potsdam-2026-10-04 (2026-10-10)

`cf.shotlog` turns each 540x960 proxy into a `reel-shotlog/1.0` JSON (`<walk>/shotlog/<clip>.json`).
The run used ffmpeg 9.0.2, OpenCV 5.0.0, Ultralytics 8.4.175 with `yolo26n.pt` on the CPU (ByteTrack at 3 fps), and `tools/vision-score` at 1 fps.
Machine: M2 with 8 GB. Resolve and other ffmpeg jobs were running at the same time.

```sh
.venv/bin/python -m cf.shotlog --all ~/Movies/content-factory/potsdam-2026-10-04 --force
```

## Summary

| clip | dur s | usable s | best in–out | quality | tags | flags |
|---|---|---|---|---|---|---|
| IMG_0332 | 13.1 | 13/13 | 3.0–8.0 | 0.86 | pan_left, author_on_camera | person_enter |
| IMG_0378 | 20.5 | 20/21 | 7.0–12.0 | 0.87 | drift, author_on_camera | |
| IMG_0386 | 12.8 | 0/13 | **REJECT** | | | shake_px>6, blur_worst20% (handheld selfie) |
| IMG_0405 | 14.2 | 13/14 | 3.0–8.0 | 0.91 | drift, author_on_camera | |
| IMG_0412 | 25.5 | 26/26 | 16.0–21.0 | 0.86 | drift, author_on_camera | |
| IMG_0413 | 29.9 | 29/30 | 2.0–7.0 | 0.89 | pan_right, author_on_camera | |
| IMG_0415 | 10.9 | 2/11 | 2.0–4.0 | 0.69 | pan_left, author_on_camera | person_enter; the rest is shake |
| IMG_0418 | 25.9 | 26/26 | 21.0–25.9 | 0.88 | pan_right, no_people | |
| IMG_0420 | 14.7 | 15/15 | 2.0–7.0 | 0.89 | pan_right, people | person_enter |
| IMG_0457 | 16.8 | 12/17 | 14.0–16.8 | 0.90 | drift, no_people | |
| IMG_0471 | 19.2 | 15/19 | 5.0–10.0 | 0.92 | locked, people | |
| IMG_0484 | 14.2 | 12/14 | 5.0–10.0 | 0.87 | locked, author_on_camera | |
| IMG_0493 | 29.2 | 28/29 | 7.0–12.0 | 0.93 | locked, golden_hour, people | |
| IMG_1621 | 33.6 | 18/34 | 14.0–19.0 | 0.80 | locked, golden_hour, author_on_camera | highlights_near_clip |

Every clip except IMG_0415 and IMG_0386 has 3 segments; the table shows only the best one. IMG_0415 has one segment, and IMG_0386 is a reject with no segment.

## Timing

The Walk has 280.8 s of footage. Analysis took **115.7 s** of wall time, about 0.41x realtime. Peak RSS was 476 MB.

| module | total s | share |
|---|---|---|
| ffstats (signalstats + scdet at full rate, blurdetect at 10 fps, Y-plane clip % at 5 fps; one decode) | 51.2 | 45 % |
| people (YOLO nano + ByteTrack, 3 fps, CPU) | 34.9 | 31 % |
| motion (LK + estimateAffinePartial2D, 10 fps) | 17.8 | 16 % |
| vision-score (Apple Vision, 1 fps) | 9.7 | 9 % |

Per clip it took 4.3–11.6 s. The first clip also pays about 4 s for the Ultralytics import. Run alone, the 3 s test proxy takes 8.5 s, almost all of it imports.

## Calibration on this Walk

| metric | p0 | p10 | p50 | p90 | max |
|---|---|---|---|---|---|
| blurdetect (higher = blurrier) | 4.13 | 4.22 | 4.88 | 6.07 | 13.4 |
| shake_px @1080, before person masking | 0.07 | 0.12 | 0.29 | 11.25 | 131 |

Values set from these numbers:

- **Sharpness anchors:** `blur_good=4.2` and `blur_bad=7.5`.
- **Shake threshold:** `shake_px=6`. Tripod and gimbal shots measure 0.1–0.5 px and stabilised handheld walking 1–3 px. Selfie and turn-around moments measure 10 px or more.
- **Exposure band:** luma 0.30–0.68 scores 1. The tone-mapped proxies have a median luma of 0.46–0.67.

## Open problems

- **Selfie clips.** The author holds the camera, so background "shake" is large by design. IMG_0386 is rejected and IMG_0415 keeps only 2 s.
  - Before person boxes were masked out of the feature set, RANSAC flipped between subject and background, and shake reached 40–250 px.
  - With the mask, the shake is real background motion, but the usable rule may be too strict for vlog-style footage.
  - Option: a looser threshold or a separate rule when `author_on_camera` and the face box is large.
- **Quality range is narrow.** Usable bins score 0.79–0.93. aes (0.45–0.8 on the −1…1 scale) does most of the ranking. Sharpness, stability and exposure sit near 1 for most of this footage.
- **The blur reject is relative.** It needs blur in the clip's top 20 % and above 1.1x the clip median. That still rejects ends of clips where the author walks into or out of the lens, which is correct. On very uniform clips it can cut a second that is only slightly softer.
- **clip_hi>2 % rejects sun-in-frame backlit shots** (IMG_1621, golden hour). That may be the look the author wants, not a defect.
- **No identity.** Author vs. stranger is a heuristic: the dominant track, the tallest box in subject-dominated clips, or a lone person after an ID switch. A friend in frame (IMG_0386) can still trigger `stranger_closeup`. `person_enter` also fires when a pan reveals the author.
- **Light.** The light tag uses sun elevation from the creation time. Without GPS (all these clips have `gps: null`), it guesses the longitude from the UTC offset with a DST correction and assumes latitude 50°.
  - Only clips after about 17:30 get `golden_hour`.
  - Midday clips get no tag (`light.tag: null`, basis "daylight"), because the vocabulary has no daylight or sunny class.
  - `interior` and `overcast` are weak guesses from saturation and contrast.
- **Motion types** are mostly `drift` for slow gimbal follow shots. The thresholds are 25 px/s for locked, 90 px/s for pan and 0.04/s for forward/back divergence. They are a first guess and have not been checked against hand labels.
- **`tools/vision-score --json -`** writes a file literally named `-`. `cf.metrics.vision` therefore reads stdout, by omitting `--json`.
