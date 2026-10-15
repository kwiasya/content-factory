# HDR (Rec.2100 HLG) delivery and the brighter SDR option

Date: 2026-10-12, DaVinci Resolve Studio 21.1.1, project `cf-walk-2026-09-13-reel-01` (reel "my type", 5 shots, all iPhone HLG / Dolby Vision 8.4 1080p 60 fps clips with Super Scale 2x on a 2160×3840 timeline). Measurements: one frame per shot (the shot's middle), downscaled to 1080×1920, with the overlay pixels masked out using the overlay's own alpha. Per-shot numbers: `reels/reel-01/out/compare.hdr-sdr.json` in that Walk.

## Why

The author watches her source clips on the iPhone in HDR. The SDR render (the −1.02 stop HLG normalization from `color-hlg-experiment.md`, no Look) looked dimmer and flatter to her than the source. SDR cannot show HLG highlights above SDR white, so the faithful option is to deliver HLG.

## HDR build and render (`cf.build --deliver hdr-hlg`, `cf.render --hdr`)

Same project settings as SDR (DWG/Intermediate, HDR 1000, `useInverseDRT='1'`, DaVinci DRTs), no node-1 CDL, no Look. Comparison of the render's 10-bit Y' with the source decoded by ffmpeg at the same source time (MAE after a 6 px blur, so Super Scale detail does not count):

| output color space | outputDRT | mean bias (10-bit code values) | blurred MAE | ≥ 0.97 signal, s02/s03 (source 1.14/1.36 %) |
|---|---|---|---|---|
| `Rec.2100 HLG` | DaVinci | −5 to −7.5 | 6.9–7.8 | 0.06 / 0.10 % (top rolled off) |
| `Rec.2100 HLG` | None | −7 to +4.5 | 13.5–17.7 | 0.04 / 0.05 %, chroma −12 % |
| **`Rec.2020 HLG ARIB STD-B67`** (= the clips' input string) | DaVinci | **−1.0 to −0.1** | **1.5–3.4** | **1.01 / 1.19 %** |

Chosen: `Rec.2020 HLG ARIB STD-B67` out. HLG round-trips through the HDR 1000 timeline.

Overlays (SDR ProRes 4444): with the inverse DRT on, SDR white came out at HLG 0.99, about 940–1000 nits (peak white, glaring). `graphicsWhiteLevel='203'` changed nothing for media clips. `useInverseDRT='0'` put SDR white at 100 nits (HLG 0.63), but it moved the HLG clips by +3.5 code values. Fix in cf.build (`cf.hdr`): each overlay is converted to HLG outside Resolve per BT.2408 (Rec.709 gamma 2.4 → ×203 nits → Rec.2020 → inverse OOTF at 1000 nits, γ 1.2 → HLG OETF). It is imported as `Rec.2020 HLG ARIB STD-B67`, so it passes through unchanged. Measured text white: HLG 0.748–0.750 = 200–203 nits.

Backdrop: Resolve composites V2 over V1 in DaVinci Intermediate (log). Over the 290–460-nit sky, the soft black backdrop (alpha 0.14 mean, 0.45 max) darkened by −1.35 to −1.76 stops on average. The display-gamma design darkens by −0.51 to −0.58. `cf.hdr` therefore rescales alpha so that the log composite matches the gamma composite over a 300-nit background (black at α 0.25 → 0.116). Measured after the fix: −0.66 to −0.91 stops. That is close to the design, and still a little heavier where the sky is brightest (s04, 462 nits).

Trade-off: graphics white (203 nits) is below this sky (290–460 nits). On an HDR screen the text is therefore slightly darker than the sky behind it, and the backdrop gives it contrast. `cf.build --overlay-nits` raises it if the author wants brighter text.

Render: H.265 Main10, `ColorSpaceTag='Rec.2020'`, `GammaTag='Rec.2100 HLG'` → hevc Main 10 `hvc1`, yuv420p10le, bt2020/arib-std-b67/bt2020nc. There is no Dolby Vision metadata (an iPhone shows plain HLG in HDR). AVFoundation reports `containsHDRVideo` for the render and for the ffmpeg preview. 4K render: 73 s.

## SDR without the normalization (`cf.build --hlg-normalize none`)

This is Resolve's own BT.2408 HLG → Rec.709 conversion with no CDL and no Look. Mean luma (0–255, overlays masked): s01 200, s02 183, s03 198, s04 203, s05 206. That is +29 to +31 over the published SDR (−1.02 stop CDL) and +43 to +49 over Apple's own SDR rendition of the clips (AVAssetImageGenerator `forceSDR`: 137–160). Skies go near-white. In the top third of the frame, 28–50 % of pixels have luma ≥ 235, against 0–1.3 % in the published SDR, 1–12 % in Apple's SDR and 5–29 % in the hable proxies. Few pixels hard-clip (≤ 0.2 % with a channel ≥ 254) because the DaVinci DRT rolls off at about 246. Saturation drops to 0.14–0.23 (published 0.24–0.38, Apple 0.26–0.43).

Apple's SDR rendition is darker than the published SDR (by 15–19 levels) and darker than the hable proxies. Brightening the SDR version moves it further from how iOS shows the clip in SDR. The extra brightness of the HDR original comes from highlights above SDR white, which only an HDR file can carry.
