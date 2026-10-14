# apple-sdr

Turns an HDR clip (iPhone HLG with Dolby Vision 8.4) into an SDR Rec.709 mezzanine. The tone mapping is AVFoundation's own, so the clip looks the way QuickTime and Photos show it on a Mac. `cf.mezz` and `cf.build` (`--hdr-source apple-sdr`, the default) use it. Why: `docs/adr/0008-hdr-clips-through-apple-tone-mapping.md`.

Requirements: macOS 15 or later on Apple Silicon, Swift 6 toolchain (Command Line Tools are enough, no Xcode). No third-party dependencies.

## Build

```sh
cd tools/apple-sdr
swift build -c release
# binary: tools/apple-sdr/.build/release/apple-sdr
```

The first release build takes about 40 s. `cf.mezz` runs it when the binary is missing. `.build/` is git-ignored.

## Usage

```sh
apple-sdr convert <in> <out.mov> [--method colorsync|vt709|vt2020|composition|export] [--start S] [--duration S]
apple-sdr frames <in> --at T[,T...] --out-dir DIR [--prefix NAME] [--policy sdr|source] [--space display-p3|srgb|709|native]
```

`convert` writes ProRes 422 HQ with Rec.709 tags (1-1-1). It keeps the source's coded size, sample timestamps (so the fps) and rotation matrix, and passes every audio track through unchanged (iPhone: AAC stereo and APAC spatial). The file is written as `<out>.partial.mov` and renamed when complete, so a cache never holds half a file. A 27 s 1080p60 clip takes about 5.5 s and 1.5 GB.

| Method | What it does | Against Apple's rendition (IMG_0477, Display P3) |
|---|---|---|
| `colorsync` (default) | `AVAssetReader` decodes with the tags `AVAssetImageGenerator` forceSDR returns (BT.2020 primaries, SDR 709 transfer). Core Image then converts BT.2020-SDR to Rec.709 through the CoreMedia color spaces of both tag sets, the ColorSync transform a Mac uses to show each one. | mean 0.8–1.3 levels, bias ≈0 |
| `vt709` | reader with Rec.709 color properties (VideoToolbox does the gamut step) | +7 to +8 levels |
| `vt2020` | the forceSDR-tagged buffers written as they are (BT.2020 / 709 / BT.2020) | 0.5 levels, but not Rec.709 |
| `composition`, `export` | `AVVideoComposition` in Rec.709 through a reader, or `AVAssetExportSession` (ProRes 422, LPCM) | same pixels as `vt709` |

The only real difference with `colorsync` is gamut: colours outside Rec.709 (the hot-pink hoodie, about 10 % of the frame) are clipped, at about R −8 / G +8 levels.

`frames` writes `AVAssetImageGenerator` stills (zero time tolerance, rotation applied) as 8-bit PNG. With `--policy sdr` (forceSDR, the default) an HDR clip comes out as Apple's SDR rendition, the same frame `qlmanage -t` gives (0.03 levels apart). ColorSync then draws it into `--space`: `display-p3` (default) shows two images as they look on a Mac screen, and `native` keeps the generator's own code values. This is the reference for the colour checks.

Output: one JSON object on stdout (method, source size, transform and colour tags, frames, audio tracks, seconds). Progress and errors go to stderr. Exit codes: `0` ok, `1` failure, `2` bad arguments.
