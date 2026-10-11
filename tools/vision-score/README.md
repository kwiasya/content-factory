# vision-score

Scores sampled video frames with Apple's Vision framework, for the clip-analysis pipeline.
Each sampled frame gets an aesthetics score, a face count and a human count.

Requirements: macOS 15 or later on Apple Silicon, Swift 6 toolchain (Command Line Tools are enough, no Xcode). No third-party dependencies.

## Build

```sh
cd tools/vision-score
swift build -c release
# binary: tools/vision-score/.build/release/vision-score
```

The first release build takes about 50 s. Rebuilds take a few seconds. `.build/` is git-ignored.

## Usage

```sh
vision-score <video> [--fps N] [--json out.json] [--max-side PX]
```

| Option | Default | Meaning |
|---|---|---|
| `--fps N` | `1` | Frames sampled per second, at t = 0, 1/N, 2/N, ... < duration |
| `--json PATH` | stdout | Write the JSON array to PATH instead of stdout |
| `--max-side PX` | `1024` | Downscale decoded frames so the longer side is at most PX (`0` = native). Never upscales. Keeps memory small on 4K sources. 540p proxies are unaffected. |
| `--landmarks` | off | Face landmarks; adds `mouth_open` (inner-lip gap / face height, largest face) |
| `--faces-only` | off | Skip aesthetics and humans (those fields are null) |
| `--text` | off | On-screen text only (Vision `RecognizeTextRequest`, accurate, language auto-detected): adds `text`; every other field is null. Used by `cf.research.ocr` for the first seconds of a Reference |
| `--until S` | whole video | Stop sampling after S seconds |

stdout (or the `--json` file) holds only the JSON. stderr gets per-frame errors and one summary line:

```
vision-score: 26 frames scored, mean aesthetic 0.582, 0.68s elapsed (first frame 196 ms, then 19 ms/frame, 12 ms in Vision)
```

The first frame is reported separately because it includes the one-time Vision model load.

Exit codes: `0` if at least one frame was scored, `1` if the file can't be opened, has no video track, or no frame was scored, `2` for bad arguments.

## Output schema

A JSON array, one object per sampled frame, in time order:

```json
[
  {"t": 0.000, "aesthetic": 0.5796, "is_utility": false, "faces": 1, "max_face_h": 0.2295, "humans": 1, "max_human_h": 0.8470}
]
```

| Field | Type | Meaning |
|---|---|---|
| `t` | float | Time of the decoded frame in seconds. This is the generator's actual time, within ±min(50 ms, ¼ sample interval) of the requested time. |
| `aesthetic` | float −1…1 | `ImageAestheticsScoresObservation.overallScore`. Higher means more aesthetically pleasing. |
| `is_utility` | bool | `isUtility`: true for screenshots, receipts, documents and similar non-memorable images. |
| `faces` | int | Number of faces from `DetectFaceRectanglesRequest`. |
| `max_face_h` | float 0…1 | Height of the largest face as a fraction of the frame height (`0` when there are no faces). |
| `humans` | int | Number of people from `DetectHumanRectanglesRequest`, full body (`upperBodyOnly = false`). |
| `max_human_h` | float 0…1 | Height of the tallest person box as a fraction of the frame height (`0` when there are none). |
| `text` | array, only with `--text` | Recognized lines `{"s": string, "conf": 0…1, "h": box height 0…1}`, top candidate per line; `[]` when the frame has none |
| `error` | string, optional | Only present when one or more requests failed on this frame. The fields of the failed requests are `null`. |

Frames are measured upright. Rotation metadata is applied (`appliesPreferredTrackTransform`), so "height" means height on the displayed frame.

If a frame can't be decoded, the tool logs it to stderr and leaves it out of the array. One bad frame doesn't stop the run.

## Implementation notes

- Frames come from `AVAssetImageGenerator` (async `image(at:)`), one at a time. Each `CGImage` is released before the next frame is decoded. Peak RSS is about 55 MB on 540x960 proxies.
- The tool uses the **modern Swift Vision API** (macOS 15+): the `VisionRequest` / `ImageProcessingRequest` structs `CalculateImageAestheticsScoresRequest`, `DetectFaceRectanglesRequest` (revision 3) and `DetectHumanRectanglesRequest` (revision 2). Each frame gets one `ImageRequestHandler`, which runs the three requests one by one with `perform(_:)` so a failure in one request doesn't lose the others. The Command Line Tools macOS 26 SDK (Swift 6.3) ships all of these, so there is no `VNRequest` fallback.
- Timing on an M-series Mac with 540x960 proxies at 1 fps: about 20 ms per frame (about 12 ms of that in Vision, the rest is decoding). Model warm-up adds about 0.2–0.7 s to the first frame. A 25 s clip takes under 1 s.
