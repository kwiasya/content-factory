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

## Speech run (2026-10-10)

The author's review of reel-01 asked to cut every moment where someone talks to the camera ("ты снимаешь?"). Until a voiceover phase a Reel carries no speech, so speech is now a reject reason. Schema `reel-shotlog/1.1` adds `per_second.speech`, top-level `speech_segments` (`start`, `end`, `text`, `prob` = mean word probability) and `speech_text`, plus `summary.speech_s`; 1.0 logs stay readable (no speech array means nothing is flagged).

`cf.metrics.speech` decodes the first audio stream of the **raw** clip (proxies have no audio) to a temp 16 kHz mono WAV and runs stable-ts 2.19.1 with Whisper `small` on the CPU, language hint `ru`, Silero VAD (pinned `v5.1.2`) and word timestamps. A second is `speech` when any word, padded 0.3 s on each side, overlaps it. The model is loaded once per `--all` run (lazily, so the first clip's `runtime_s.speech` includes the load); weights are cached in `~/Movies/content-factory/_models/{whisper,torch_hub}`.

```sh
.venv/bin/python -m cf.shotlog --all ~/Movies/content-factory/potsdam-2026-10-04          # 1.0 logs get only the speech pass
.venv/bin/python -m cf.shotlog --all ~/Movies/content-factory/potsdam-2026-10-04 --speech-only
```

Model choice, from runs over all 14 clips:

- `base` garbled the clear dialogue ("Сын дареко" for "Сильно далеко") and produced nonsense on IMG_1621's tail; `small` transcribed the same speech cleanly.
- Language auto-detection labelled short phrases in street noise as Nynorsk or Faroese and was 10x slower (temperature fallbacks); the `ru` hint fixes both.
- Without VAD, Whisper hallucinated on silent clips ("Субтитры субтитров Н.Новикова" on IMG_0332 and IMG_0420); with VAD those clips come out empty.
- Beam search (5) changed some wording but not which seconds are speech, at 2-3x the time; greedy decoding is kept.
- MPS fails in Whisper's word alignment (float64 DTW), so it runs on the CPU.
- Hard clips fall back to sampling; a fixed torch seed makes the log identical from run to run (checked with two runs).

| clip | speech s | speech segments (start–end, text) | best before | best after | usable s |
|---|---|---|---|---|---|
| IMG_0332 | 0 | — | 3–8 (q 0.86) | 3–8 (q 0.86) | 13 → 13 |
| IMG_0378 | 1 | 0–0.1 «Давай!» | 7–12 (q 0.87) | 7–12 (q 0.87) | 20 → 19 |
| IMG_0386 | 2 | 9.7–10.1 «Хорошо в prefix» (garbled) | REJECT | REJECT | 0 → 0 |
| IMG_0405 | 0 | — | 3–8 (q 0.91) | 3–8 (q 0.91) | 13 → 13 |
| IMG_0412 | 4 | 0.9–1.1 «Леток?»; 1.9–3.0 «Леток?» (a short question, likely the "are you filming?" moment, misheard) | 16–21 (q 0.86) | 16–21 (q 0.86) | 26 → 22 |
| IMG_0413 | 0 | — | 2–7 (q 0.89) | 2–7 (q 0.89) | 29 → 29 |
| IMG_0415 | 0 | — | 2–4 (q 0.69) | 2–4 (q 0.69) | 2 → 2 |
| IMG_0418 | 9 | 0.2–0.7 «Какая-то гоня»; 2.9–5.7 «100% какая-то бибильная история с этими собаками»; 5.7–6.1 «Ну ничего,»; 6.2–6.7 «это все в код,»; 6.8–7.2 «скормлю,»; 7.7–8.7 «там меня смонтируют видео» | 21–25.9 (q 0.88) | 21–25.9 (q 0.88) | 26 → 17 |
| IMG_0420 | 0 | — | 2–7 (q 0.89) | 2–7 (q 0.89) | 15 → 15 |
| IMG_0457 | 0 | — | 14–16.8 (q 0.90) | 14–16.8 (q 0.90) | 12 → 12 |
| IMG_0471 | 9 | 0.3–0.6 «Кашка, да?»; 0.9–1.1 «Иди»; 5.5–7.6 «Все, стой, не так далеко»; 12.6–15.1 «Сильно далеко, конечно» | 5–10 (q 0.92) | **8–12 (q 0.91)** | 15 → 8 |
| IMG_0484 | 2 | 0.7–1.5 «Го!» | 5–10 (q 0.87) | 5–10 (q 0.87) | 12 → 10 |
| IMG_0493 | 22 | 5.4–7.5 «Нет, очень далеко.»; 8.2–8.5 «Ближе?»; 8.9–9.7 «Раз в два.»; 12.8–13.1 «А тут?»; 13.7–14.4 «Еще ближе.»; 14.9–15.2 «Тут?»; 16.0–17.5 «Нет, ты уже вышла с камеры.»; 19.3–19.5 «Тут?»; 20.0–22.3 «Ну, я бы еще раз в два ближе подошел.»; 23.2–24.3 «Ну, вот хотя бы тут.»; 25.7–26.4 «Но размыто.»; 27.3–29.0 «Ну, переключи на киски, на эффект она нормальная.» | 7–12 (q 0.93) | **10–12 (q 0.93)** | 28 → 6 |
| IMG_1621 | 19 | 1.8–2.5 «Можешь начинать.»; 4.3–5.6 «Да.»; 8.4–9.8 «О, всё, заебись.»; 15.6–17.4 «О, да, как будто хрен.»; 23.0–23.8 «И можешь назад идти.»; 26.0–28.0 «Всё, всё хватит.»; 29.5–29.9 «Ага.» | 14–19 (q 0.80) | **20–22 (q 0.82)** | 18 → 9 |

Usable footage on the Walk went from 229 s to 175 s (−54 s, −24 %); 68 s carry speech in total, some of which was already unusable. Eight clips have speech; three best segments moved (IMG_0471, IMG_0493, IMG_1621). Seven of reel-01's 17 shots overlap speech: IMG_0418 7.0–9.5, IMG_0412 1.0–4.0, IMG_0471 14.0–17.8, IMG_0493 1.5–6.0 and 23.0–26.0, IMG_1621 20.5–23.5 and 14.0–17.6.

### Timing

The speech-only pass over the 14 existing logs took **28–32 s** of wall time for 280.8 s of audio (about 0.11x realtime), including 4.2–4.7 s to load the cached `small` model and Silero VAD. The very first load, which downloads `small` (461 MB), took about 30 s. Peak RSS was 1.7 GB.

| clip | speech s (runtime) |
|---|---|
| IMG_0332 | 4.6 (includes the 4.2 s model load; about 0.4 s of work) |
| IMG_0378 | 2.9 |
| IMG_0386 | 2.6 |
| IMG_0405 | 0.3 |
| IMG_0412 | 2.1 |
| IMG_0413 | 0.4 |
| IMG_0415 | 0.3 |
| IMG_0418 | 2.4 |
| IMG_0420 | 0.3 |
| IMG_0457 | 0.3 |
| IMG_0471 | 2.0 |
| IMG_0484 | 1.5 |
| IMG_0493 | 5.7 |
| IMG_1621 | 5.6 |

Clips where VAD finds no voice cost 0.3 s (ffmpeg decode plus VAD); Whisper only runs on clips with voice.

### Open problems

- **Every voice counts.** A passer-by talking in the background rejects the second just like the author does. That matches "no speech until voiceover", but it costs footage on busy streets.
- **Short low-confidence words** at clip edges ("Давай!" at 0.0–0.1, prob 0.03) may be noise. They are kept, because missing speech costs more than losing one second. `speech_segments[].prob` lets the Editor judge.
- **Text is approximate** for short, noisy phrases (IMG_0412 «Леток?», IMG_0386). The timing is what the reject uses.
- **Audio/video offset.** Bins assume the raw audio and the proxy both start at 0; the 0.3 s padding absorbs small offsets.
