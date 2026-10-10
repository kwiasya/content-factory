# Environment: ffmpeg build (2026-10-10)

Machine: macOS 26.6, Apple Silicon M2, 8 GB RAM, Homebrew 7.0.9.

## What was installed

| | Before | After |
|---|---|---|
| Formula | `ffmpeg` (homebrew-core) 8.0.1_4 | **`ffmpeg-full` (homebrew-core) 9.0.2**, bottle `arm64_tahoe` |
| Binary | `/opt/homebrew/bin/ffmpeg` | `/opt/homebrew/bin/ffmpeg` -> `../Cellar/ffmpeg-full/9.0.2/bin/ffmpeg` (same for `ffprobe`, `ffplay`) |

The stock `ffmpeg` formula is still lean at 9.0.2. `brew info ffmpeg` lists only dav1d, lame, libvmaf, libvpx, openssl@4, opus, sdl2-compat, svt-av1, x264, x265 and xz, with no zimg, freetype or libass. A `brew reinstall ffmpeg` would not have fixed this.
homebrew-core now ships **`ffmpeg-full`** as a bottled formula with 47 deps, including zimg, freetype, harfbuzz, fontconfig, libass, libvidstab and libplacebo. That made the `homebrew-ffmpeg/ffmpeg` tap, which compiles from source, unnecessary. No source compile happened.

`ffmpeg-full` is keg-only because it is an alternate of `ffmpeg`. Nothing installed depended on `ffmpeg` (`brew uses --installed ffmpeg` was empty), so the old formula was uninstalled and the new keg was linked.

Key libs: zimg 3.0.6, freetype 2.14.3, harfbuzz 14.6.0, libass 0.17.5_1, libvidstab 1.1.2.

## Exact commands

```sh
brew install ffmpeg-full          # bottle; ~131 s wall time incl. all deps
brew uninstall ffmpeg             # removes 8.0.1_4
brew link ffmpeg-full             # 112 symlinks into /opt/homebrew
```

Time taken: about 2 min 11 s for the install (bottles only) and a few seconds for uninstall and link.

If `brew upgrade` ever reinstalls plain `ffmpeg` as a dependency of another formula, the two will conflict on links. Re-run `brew unlink ffmpeg && brew link ffmpeg-full`.

## Verification

`ffmpeg -version`: `ffmpeg version 9.0.2`. The configure line includes `--enable-libzimg --enable-libfreetype --enable-libharfbuzz --enable-libfontconfig --enable-libass --enable-libvidstab --enable-libplacebo --enable-videotoolbox --enable-audiotoolbox --enable-whisper`.
`ffprobe -version`: `ffprobe version 9.0.2`.

`ffmpeg -hide_banner -filters | grep -wE "zscale|drawtext|subtitles|vidstabdetect|tonemap|lut3d|signalstats|blurdetect|scdet|tile|loudnorm"`:

```
 .. loudnorm          A->A       EBU R128 loudness normalization
 .. ass               V->V       Render ASS subtitles onto input video using the libass library.
 .. blurdetect        V->V       Blurdetect filter.
 T. drawtext          V->V       Draw text on top of video frames using libfreetype library.
 TS lut3d             V->V       Adjust colors using a 3D LUT.
 .. scdet             V->V       Detect video scene change
 .S signalstats       V->V       Generate statistics from video analysis.
 .. subtitles         V->V       Render text subtitles onto input video using the libass library.
 .. tile              V->V       Tile several successive frames together.
 .S tonemap           V->V       Conversion to/from different dynamic ranges.
 .. vidstabdetect     V->V       Extract relative transformations, pass 1 of 2 for stabilization (see vidstabtransform for pass 2).
 .. vidstabtransform  V->V       Transform the frames, pass 2 of 2 for stabilization (see vidstabdetect for pass 1).
 .S zscale            V->V       Apply resizing, colorspace and bit depth conversion.
```

All 11 required filters are present.

`ffmpeg -hwaccels`: `videotoolbox`, `vulkan`. The encoders `h264_videotoolbox`, `hevc_videotoolbox` and `prores_videotoolbox` are also present.

## HDR to SDR proxy smoke test

Input: `Instagram/1/IMG_0332.MOV`. It is HEVC yuv420p10le 1920x1080 at 60 fps, tagged bt2020nc / arib-std-b67 (HLG) / bt2020, tv range, with a display matrix rotation of -90.

Working chain. It ran unchanged on the first try:

```sh
ffmpeg -i IMG_0332.MOV -t 3 \
  -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,scale=540:960" \
  -c:v h264_videotoolbox -an proxy.mp4
```

Output (`ffprobe`): h264, yuv420p, 540x960, color_range=tv, color_space=bt709, color_transfer=bt709, color_primaries=bt709, 60 fps, 180 frames, 3.000 s. The output has no rotation side data left.

Autorotate is confirmed in the verbose filtergraph log. ffmpeg inserts `transpose` (`w:1920 h:1080 dir:1 -> w:1080 h:1920 rotation:clockwise`) ahead of the user chain. The final `scale` therefore goes from 1080x1920 to 540x960 and keeps the aspect ratio. An extracted frame is upright and portrait, with natural colors and no clipped highlights.

Speed: 3 s of 60 fps 4:2:0 10-bit HDR took 2.7 s wall (about 1.1x realtime, 12.9 s user CPU). The float32 zscale and tonemap steps on the CPU are the bottleneck, not the encoder. For long ingest batches, consider putting `scale` before the float stage, or try `libplacebo` (now available) for GPU tone-mapping.
