# Research adapters smoke (ticket #5: deep fetch)

- Date: 2026-10-11, MacBook Air M2 8 GB, macOS 26, repo `.venv` (Python 3.12.13)
- Packages (extra `research` in `pyproject.toml`, installed with `uv pip install --python .venv/bin/python 'yt-dlp[default]' stable-ts`): yt-dlp 2026.08.19, yt-dlp-ejs 0.8.0, stable-ts 2.19.1, openai-whisper 20250625, torchaudio 2.11.0 with torch 2.14.1 (untouched). `import torch, torchaudio, stable_whisper, yt_dlp` works; `torchaudio.functional.resample` runs. JS runtime for YouTube: deno at `/opt/homebrew/bin/deno` (yt-dlp default).
- OCR: `tools/vision-score` gained `--text` (Apple Vision `RecognizeTextRequest`) and `--until S`; built with `swift build -c release` (31 s).
- Store and footage: a scratch `--db` and `CF_FOOTAGE_ROOT` in a temp dir, so the real `factory.db` was not touched. Model weights went to the default `~/Movies/content-factory/_models` (Whisper `small`, Silero VAD v5.1.2, `yolo26n.pt`: first download).

## Data API part: PASS (2026-10-11, key from `.env`, scratch DB and footage root)

Watchlist `smoke` (Format `tech-explainer`, en, US), Reference channel `@GoogleDevelopers`, one query «claude code tutorial».

| Step | Result | Calls |
|---|---|---|
| `watchlist add-channel smoke @GoogleDevelopers` | handle, title, 2 680 000 subscribers, 6 111 videos, channel id resolved | channels.list ×1 |
| `scout smoke --search-pages 1` | 3.3 s; 3 uploads pages (150 videos, backfill ≥ 30 per kind), 1 search page (50 hits, 37 candidate channels), no errors, `stopped: null` | playlistItems.list ×3, videos.list ×4, search.list ×1, channels.list ×1 |
| `snapshot smoke` | 200 Reference, one snapshot row each | videos.list ×4 |
| `feed smoke --days 365 --limit 8` | 8 rows ranked by Outlier score (930x … 19,7x), all `без разбора` | none |
| `quota` | default 13 / 10 000, search 1 / 100; per-method table matches the calls above | none |

Quota accounting matched the calls one to one. A Watchlist with 15–20 channels costs about 5 units per channel on the first scout and 1–2 afterwards, plus 1 search call per query page.

## yt-dlp + stable-ts + proxy + Shot log + OCR: PASS

Video: "Me at the zoo", `jNQXAC9IVRw`, 19 s, public, no sign-in. Command:

```
CF_FOOTAGE_ROOT=<tmp>/footage PYTHONPATH=src .venv/bin/python -m cf.research fetch "https://www.youtube.com/watch?v=jNQXAC9IVRw" --db <tmp>/factory.db
```

| Run | Steps | Wall time |
|---|---|---|
| 1, cold (Whisper, Silero, YOLO weights downloaded) | media downloaded, transcript made, proxy made, shotlog made, ocr made | 59 s (Whisper load 34 s) |
| 2, same command again | media kept, transcript kept, proxy skipped (fresh), shotlog kept, ocr kept: only the info dict is refreshed (new snapshot) | 5 s |
| 3, `--force --json` via `youtu.be/` URL | everything redone | 28 s (Whisper load 4.3 s, transcribe 2 s, Shot log metrics 9 s) |

Reference folder `references/_adhoc/jNQXAC9IVRw/`: `jNQXAC9IVRw.mp4` (H.264 `avc1.4D400C` + AAC, 320x240: the best the video has under `res:720`), `info.json` (100-point heatmap, 3 chapters), `transcript.json` (stable-ts dict, `_provenance`), `proxy.mp4`, `shotlog.json` (`reel-shotlog/1.2`; its speech reuses `transcript.json`, tool_versions `speech_from: transcript.json`, so Whisper runs once per Reference), `ocr.json` (first 5 s at 4 fps), `card.json`.

Measured card (excerpt): duration 19.0 s, kind short, 0 cuts (single take), first shot 19.0 s, first person 0 s, first face 0 s, speech onset 1.04 s, spoken hook "Alright, so here we are, one of the elephants.", language en, 4 transcript sections, 3 chapters, one heatmap peak 0:00–0:06.5 (value 1.0) quoting "Alright, so here we are, one of the elephants. The cool thing about these guys is", first on-screen text null with the note "no on-screen text in the first 5.0 s sampled" (true: the video has none). Store: one `video` row (`has_media` 1, `has_transcript` 1), one snapshot per fetch, one `card` row with `analysis` NULL, no `watchlist_channel` row.

OCR checked separately on a synthetic 720x1280 clip with "LISBON IN 60s" overlaid from 1.0 s: `vision-score --text --fps 2 --until 2` found nothing at 0 and 0.5 s and `LISBON IN 60s` (conf 1.0, box height 0.054) from 1.0 s on, about 170 ms per frame.

Format choice on a vertical video (metadata only, no download; `k_YfvehOKFE`, 720x1280 portrait): `res:720` sort gives format `136+140`, 720x1280 H.264 + AAC, where a `height<=720` filter would have picked 406x720.

## Findings

- yt-dlp's default format choice without our options is `395+251` (AV1 + Opus) on this video; `extract` now passes the same `format`/`format_sort` as `download`, so `info.json` describes the file on disk.
- Ultralytics prints its weight download progress to stdout; `fetch` sends the tools' stdout to stderr while it runs, so `--json` stays parseable.
- `comment_count` from yt-dlp can be a rounded figure (10 000 000 here); the Data API snapshot (ticket #4) is the exact one.
