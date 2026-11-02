---
name: resolve-smoke
description: Run the Resolve API smoke tests S1–S11 against the open Resolve and record what the API actually does. Use after installing or updating Resolve, or when a build-reel step fails in a way the rules do not predict.
---

# Resolve smoke tests

Rules and connection details: `docs/resolve-rules.md`. Test list and the claim each one checks: `docs/research/SYNTHESIS.md` §3.

## Steps

1. Confirm Resolve is running (`pgrep -x Resolve`; launch with `open -a "DaVinci Resolve"` and wait ~5 s if not). The suite creates and uses its own project `smoke-<date>`; it never touches any other project.
2. Run every test script in `tests/smoke/` in order (`S01_*.py` … `S11_*.py`) with `.venv/bin/python`. Each prints `PASS`, `FAIL` or `SKIP` plus the raw values it read back. S11 (Library Asset cues) makes its own media with ffmpeg into `tests/smoke/out/S11/` and records the Tilt sign (`tilt_up_positive`), whether scaleToFit upscales a small item, a still's default length, an mp3's clip FPS, the AudioVolume range and whether a VP9 webm keeps its alpha; when it says a cue assumption is wrong, change `cf.assets.TILT_SIGN`, `style.json` `assets.still_max_s` or `cf.assets.placement` and record it in `docs/resolve-rules.md`.
3. For every FAIL, grep the stub for the method and try the documented signature once more; record both attempts.
4. Write `docs/research/smoke-results.md`: a table of test, result, exact strings discovered (color space names, transition type names, where a Fusion title landed), Resolve version, date.
5. Update `docs/resolve-rules.md` where a result contradicts a rule or trap listed there.

Done when every test has a recorded result and the rules file agrees with them.
