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

## Speech side run (2026-10-10)

The author corrected the speech rule: almost all speech on the Walk is the person filming, talking from behind the camera ("closer", "you're out of frame"). That is fine, because music covers it. Only the person **on camera** talking is a reject, and the author says that happened in one moment. So `per_second.speech` is now a soft flag (candidates over it carry flag `speech`). Only `per_second.speech_on_camera` makes a second unusable (`why: speech_on_camera`). Schema `reel-shotlog/1.2`; 1.0 and 1.1 logs stay readable, and a log without `speech_on_camera` rejects nothing for speech.

**Side per segment** (`cf.metrics.speech_side`). Each Whisper segment gets `side` = `near` (behind the camera) or `far` (on camera), `side_confidence` 0–1, `rms_dbfs` and `mouth_open_var`. It also gets `level_dbfs`, `rel_db`, `snr_db`, `max_face_h`, `median_face_h`, `face_frames`, `mouth_open_std` and `p_far`. Two cues:

- **Loudness**, from the raw clip's 16 kHz WAV (the same file Whisper reads).
  - `level_dbfs` is the 90th percentile of 50 ms frame levels inside the segment. It is robust to pauses between words.
  - The level is compared with the **Walk** reference: the median of the three loudest segment levels, −19.0 dBFS here, because the operator's voice is the loudest. The result is `rel_db`.
  - It is also compared with the clip's noise floor, the 10th percentile of frame levels. The result is `snr_db`.
  - Evidence for far ramps from −1 to +1 around `rel_db` −16 ± 9 dB and `snr_db` 14 ± 8 dB.
- **Face and mouth**, from the proxy: `tools/vision-score <proxy> --fps 5 --landmarks --faces-only`.
  - The Swift change adds `VNDetectFaceLandmarksRequest` through the Swift `DetectFaceLandmarksRequest`. Per frame, `mouth_open` is the inner-lip vertical extent of the largest face divided by its face-box height. `--faces-only` skips aesthetics and humans, which costs about 13 ms per frame.
  - Face size ramps from 0 at 0.03 to +1 at 0.12 of the frame height. No face at all counts −1.
  - The spread of `mouth_open` over the segment is the strongest cue (±1 around sd 0.012 ± 0.008). It is only trusted once the face is big enough for stable landmarks: the weight ramps from a median face height of 0.05 to 0.12.
- **Combination.** The weighted sum (0.5 rel, 0.5 snr, 0.4 face, 1.2 mouth) goes through a logistic to give `p_far`. Then:
  - `side_confidence` = |2·p_far − 1|. It is scaled by Whisper's word probability: 0.5× at prob 0, full from prob 0.5, because low-probability words are often noise.
  - It is capped at 0.4 when no face of at least 0.04 is visible. A far voice that nobody can see talking is covered by music like the operator's.
  - A second is `speech_on_camera` when a `far` segment with confidence ≥ 0.5, padded 0.3 s, overlaps it.
- **Not used.** Reverb or dryness (a direct-to-reverberant estimate is not cheap or reliable from one mono WAV), and speaker identity.

The weights were set by hand on this Walk. Three anchors were checked against frames: IMG_0418 has nobody in frame and is the operator's monologue; IMG_1621 26.8–28.0 has her smiling with closed lips, so the operator is talking; IMG_0412 0.8–1.0 has her looking back at the camera with parted lips. **They are not validated beyond one Walk.**

**Overrides.** `<walk>/shotlog/overrides.json`, `{"<clip>": {"reject": [[in_s, out_s, "reason"]], "allow": [[in_s, out_s]]}}`, is applied after every automatic rule. `allow` clears all flags in the seconds it touches, then `reject` adds its reason, so a reject wins over an allow. The entry is copied into the log as `overrides`.

- `--all` without flags re-scores up-to-date logs in about 0.6 s. Sides are reclassified from the stored levels and face stats, with no audio or video.
- `--speech-only` redoes Whisper, levels and faces, then re-applies the overrides.
- Both were checked on a scratch copy of the Walk. The real Walk has no overrides file yet.

```sh
.venv/bin/python -m cf.shotlog --all ~/Movies/content-factory/potsdam-2026-10-04 --speech-only
```

The run took 45 s wall time: Whisper load 5.7 s, and the landmark pass is about 1–2 s per clip with speech. Peak RSS was 1.8 GB. The Walk reference was −19.0 dBFS.

| clip | start–end | text | rms dBFS | level (vs Walk / over floor) | face max h (frames with face) | mouth var (sd) | side | conf |
|---|---|---|---|---|---|---|---|---|
| IMG_0378 | 0.00–0.10 | «Давай!» | -41.1 | -40.0 (-21.0 / +4.8) | 0.026 (1/2) | — | far | 0.35 |
| IMG_0386 | 9.70–10.10 | «Хорошо в prefix» | -38.5 | -30.7 (-11.7 / +19.4) | 0.201 (4/4) | 0.00051 (0.022) | far | 0.40 |
| IMG_0412 | 0.94–1.12 | «Леток?» | -36.8 | -34.6 (-15.6 / +9.2) | 0.045 (2/2) | 0.00011 (0.011) | far | 0.21 |
| IMG_0412 | 1.90–2.96 | «Леток?» | -41.1 | -39.1 (-20.1 / +4.7) | 0.052 (5/7) | 0.00001 (0.003) | **far** | **0.68** |
| IMG_0418 | 0.19–0.67 | «Какая-то гоня» | -38.3 | -36.5 (-17.5 / +15.2) | 0.000 (0/3) | — | near | 0.37 |
| IMG_0418 | 2.86–5.72 | «100% какая-то бибильная история с этими собаками» | -27.2 | -23.4 (-4.4 / +28.3) | 0.000 (0/16) | — | near | 0.89 |
| IMG_0418 | 5.72–6.10 | «Ну ничего,» | -24.3 | -21.3 (-2.3 / +30.4) | 0.000 (0/2) | — | near | 0.85 |
| IMG_0418 | 6.18–6.68 | «это все в код,» | -25.3 | -22.1 (-3.1 / +29.6) | 0.000 (0/3) | — | near | 0.89 |
| IMG_0418 | 6.82–7.20 | «скормлю,» | -23.8 | -21.0 (-2.0 / +30.7) | 0.000 (0/3) | — | near | 0.89 |
| IMG_0418 | 7.70–8.74 | «там меня смонтируют видео» | -25.0 | -21.0 (-2.0 / +30.7) | 0.000 (0/6) | — | near | 0.89 |
| IMG_0471 | 0.28–0.62 | «Кашка, да?» | -42.7 | -41.3 (-22.3 / +11.9) | 0.000 (0/3) | — | far | 0.08 |
| IMG_0471 | 0.88–1.12 | «Иди» | -31.9 | -30.5 (-11.5 / +22.7) | 0.000 (0/3) | — | near | 0.82 |
| IMG_0471 | 5.54–7.64 | «Все, стой, не так далеко» | -29.9 | -26.4 (-7.4 / +26.8) | 0.000 (0/11) | — | near | 0.88 |
| IMG_0471 | 12.61–15.08 | «Сильно далеко, конечно» | -50.1 | -47.9 (-28.9 / +5.3) | 0.033 (1/13) | — | far | 0.40 |
| IMG_0484 | 0.74–1.50 | «Го!» | -21.8 | -15.8 (+3.2 / +34.1) | 0.000 (0/5) | — | near | 0.58 |
| IMG_0493 | 5.44–7.48 | «Нет, очень далеко.» | -27.7 | -22.3 (-3.3 / +42.2) | 0.000 (0/11) | — | near | 0.89 |
| IMG_0493 | 8.18–8.54 | «Ближе?» | -52.3 | -48.4 (-29.4 / +16.1) | 0.000 (0/3) | — | near | 0.03 |
| IMG_0493 | 8.94–9.70 | «Раз в два.» | -22.2 | -19.0 (+0.0 / +45.5) | 0.000 (0/5) | — | near | 0.89 |
| IMG_0493 | 12.78–13.08 | «А тут?» | -55.4 | -50.5 (-31.5 / +14.0) | 0.000 (0/3) | — | far | 0.10 |
| IMG_0493 | 13.73–14.42 | «Еще ближе.» | -26.5 | -22.8 (-3.8 / +41.7) | 0.000 (0/4) | — | near | 0.89 |
| IMG_0493 | 14.94–15.16 | «Тут?» | -56.3 | -53.5 (-34.5 / +11.0) | 0.000 (0/2) | — | far | 0.28 |
| IMG_0493 | 16.02–17.54 | «Нет, ты уже вышла с камеры.» | -25.1 | -20.9 (-1.9 / +43.6) | 0.033 (3/9) | 0.00010 (0.010) | near | 0.76 |
| IMG_0493 | 19.28–19.46 | «Тут?» | -52.8 | -50.7 (-31.7 / +13.8) | 0.000 (0/1) | — | far | 0.11 |
| IMG_0493 | 20.02–22.28 | «Ну, я бы еще раз в два ближе подошел.» | -24.3 | -20.1 (-1.1 / +44.4) | 0.030 (7/13) | 0.00006 (0.008) | near | 0.76 |
| IMG_0493 | 23.22–24.30 | «Ну, вот хотя бы тут.» | -26.5 | -23.2 (-4.2 / +41.3) | 0.030 (5/7) | 0.00002 (0.005) | near | 0.76 |
| IMG_0493 | 25.72–26.36 | «Но размыто.» | -22.3 | -19.7 (-0.7 / +44.8) | 0.030 (1/4) | — | near | 0.76 |
| IMG_0493 | 27.30–27.44 | «Ну,» | -59.6 | -59.2 (-40.2 / +5.3) | 0.031 (1/1) | — | far | 0.40 |
| IMG_0493 | 27.72–28.14 | «переключи на киски,» | -47.7 | -44.3 (-25.3 / +20.2) | 0.032 (3/3) | 0.00004 (0.006) | far | 0.12 |
| IMG_0493 | 28.14–28.98 | «на эффект она нормальная.» | -43.0 | -40.4 (-21.4 / +24.1) | 0.032 (5/5) | 0.00004 (0.006) | near | 0.19 |
| IMG_1621 | 1.76–2.48 | «Можешь начинать.» | -35.5 | -31.8 (-12.8 / +28.3) | 0.000 (0/4) | — | near | 0.79 |
| IMG_1621 | 4.32–5.60 | «Да.» | -42.0 | -36.3 (-17.3 / +23.8) | 0.000 (0/7) | — | near | 0.43 |
| IMG_1621 | 8.38–9.78 | «О, всё, заебись.» | -37.6 | -34.7 (-15.7 / +25.4) | 0.064 (8/8) | 0.00031 (0.018) | near | 0.23 |
| IMG_1621 | 15.57–17.43 | «О, да, как будто хрен.» | -33.4 | -29.7 (-10.7 / +30.4) | 0.000 (0/10) | — | near | 0.83 |
| IMG_1621 | 22.98–23.80 | «И можешь назад идти.» | -34.4 | -30.1 (-11.1 / +30.0) | 0.056 (5/5) | 0.00004 (0.007) | near | 0.61 |
| IMG_1621 | 26.00–26.10 | «Всё,» | -52.7 | -51.3 (-32.3 / +8.8) | 0.085 (2/2) | 0.00009 (0.009) | far | 0.37 |
| IMG_1621 | 26.78–28.00 | «всё хватит.» | -42.0 | -38.3 (-19.3 / +21.8) | 0.140 (5/7) | 0.00011 (0.010) | near | 0.14 |
| IMG_1621 | 29.48–29.86 | «Ага.» | -34.7 | -32.9 (-13.9 / +27.2) | 0.000 (0/3) | — | near | 0.77 |

**Rejected now:** IMG_0412 seconds 1–3 (1.0–4.0). The far segment 1.90–2.96, padded, covers 1.6–3.26. Nothing else on the Walk is rejected for speech.

| clip | usable before speech | 1.1 (all speech rejected) | 1.2 (on-camera only) | speech s | on-camera s | best now |
|---|---|---|---|---|---|---|
| IMG_0332 | 13 | 13 | 13 | 0 | 0 | 3–8 (q 0.86) |
| IMG_0378 | 20 | 19 | 20 | 1 | 0 | 7–12 (q 0.87) |
| IMG_0386 | 0 | 0 | 0 | 2 | 0 | REJECT (shake, blur) |
| IMG_0405 | 13 | 13 | 13 | 0 | 0 | 3–8 (q 0.91) |
| IMG_0412 | 26 | 22 | **23** | 4 | 3 | 16–21 (q 0.86) |
| IMG_0413 | 29 | 29 | 29 | 0 | 0 | 2–7 (q 0.89) |
| IMG_0415 | 2 | 2 | 2 | 0 | 0 | 2–4 (q 0.69) |
| IMG_0418 | 26 | 17 | **26** | 9 | 0 | 21–25.9 (q 0.88) |
| IMG_0420 | 15 | 15 | 15 | 0 | 0 | 2–7 (q 0.89) |
| IMG_0457 | 12 | 12 | 12 | 0 | 0 | 14–16.8 (q 0.90) |
| IMG_0471 | 15 | 8 | **15** | 9 | 0 | 5–10 (q 0.92) |
| IMG_0484 | 12 | 10 | **12** | 2 | 0 | 5–10 (q 0.87) |
| IMG_0493 | 28 | 6 | **28** | 22 | 0 | 7–12 (q 0.93) |
| IMG_1621 | 18 | 9 | **18** | 19 | 0 | 14–19 (q 0.80) |
| **Walk** | 229 | 175 | **226** | 68 | 3 | |

Usable footage is back from 175 s to 226 s (+51 s). Only IMG_0412's three seconds remain lost. The best segments of IMG_0471, IMG_0493 and IMG_1621 are back to their pre-speech picks.

### Best guess: the on-camera moment

**IMG_0412, 0.9–3.0 s: the two «Леток?» segments.** «Леток?» is very likely Whisper mishearing «Снимаешь?» ("are you filming?"). That is the phrase the author quoted in the reel-01 review ("ты снимаешь?"). Evidence:

- The voice is 15–20 dB under the operator's and only 5–9 dB over the clip's noise floor: a far voice.
- A face is visible in 7 of 9 sampled frames. In the raw frames at 0.8–1.0 s she looks back over her shoulder at the camera with her lips parted, then turns away.
- No other segment with a visible face is quiet. The candidates where faces are big (IMG_1621 26.8–28.0, IMG_0386) either show closed, smiling lips or come from a selfie clip that is already a reject.

The model rejects only the second «Леток?» (1.90–2.96, conf 0.68). The first (0.94–1.12) has Whisper prob 0.13 and a 0.045 face, so its conf is 0.21; its padding into second 0 is not rejected. reel-01's shot IMG_0412 1.0–4.0 overlaps the rejected seconds.

**To confirm (author):**

1. Is IMG_0412 0.9–3.0 the moment? If yes, pin it with `{"IMG_0412": {"reject": [[0.6, 3.3, "speech_on_camera"]]}}` in `shotlog/overrides.json`, which covers seconds 0–3. If not, use `allow` on 1–4 and name the real moment.
2. The quiet questions in IMG_0493 («Ближе?», «А тут?», «Тут?» ×2, at −48 to −54 dBFS) sound like the person on camera answering the operator from far away. She is too small for a face to be detected, so they stay soft (conf ≤ 0.4). Reject them only if the author counts them.
3. The IMG_0386 selfie (9.7–10.1, face 0.20, mouth moving, conf 0.40 after the low Whisper probability) is on-camera talk in a selfie. The clip is already rejected for shake.

### Open problems

- **One Walk, hand-set weights.** The thresholds come from 37 segments and three visual checks. Expect overrides on the next Walk until there are more labels.
- **Small faces.** Most subjects are 0.03–0.06 of the frame height on the 540p proxy, so landmarks there are too noisy to trust. Face presence and loudness carry the decision. Running landmarks on the raw 4K would make mouth movement usable for far subjects, at a higher decode cost.
- **Per-clip operator level varies.** In IMG_1621 the operator sits at −30 to −38 dBFS, 11–19 dB under the Walk reference, so the loudness cue alone would lean far. The noise-floor margin and mouth cue keep those segments near.
- **Whisper probability as reliability** also discounts real short words (IMG_0412 «Леток?» first instance, prob 0.13).
