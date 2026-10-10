"""S9: import a Remotion ProRes 4444 overlay with alpha and put it on V2 over a V1 clip.

SKIP unless ~/Movies/content-factory/smoke/overlay_test.mov exists (rendered by Remotion).
Checks: import works, 'Alpha mode' clip property, AppendToTimeline on V2 lands at the
requested frame, and a rendered frame shows the V1 clip through the transparent area.
"""

import subprocess

import numpy as np
from _common import FPS, RENDER_DIR, driver, media, run

OVERLAY = RENDER_DIR / "overlay_test.mov"


def frame_pixels(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8)


def body(rec):
    if not OVERLAY.exists():
        rec["reason"] = f"{OVERLAY} not found (Remotion overlay not rendered yet)"
        return "SKIP"
    rec["overlay_ffprobe"] = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,nb_frames", "-of", "compact", str(OVERLAY)],
        capture_output=True, text=True).stdout.strip()
    d = driver()
    _, sdr = media(d)
    (ov,) = d.import_media([OVERLAY])
    props = d.call(ov.GetClipProperty)
    rec["overlay_props"] = {k: props.get(k) for k in ("Alpha mode", "Video Codec", "Resolution", "FPS", "Frames",
                                                      "Input Color Space", "Type")}
    tl = d.create_timeline("S09", 1080, 1920, FPS)
    start = d.call(tl.GetStartFrame)
    if d.call(tl.GetTrackCount, "video") < 2:
        d.call(tl.AddTrack, "video")
    d.append([{"mediaPoolItem": sdr, "startFrame": 0, "endFrame": 120, "trackIndex": 1, "recordFrame": start,
               "mediaType": 1}])
    items = d.append([{"mediaPoolItem": ov, "trackIndex": 2, "recordFrame": start + 15, "mediaType": 1}])
    it = items[0]
    rec["overlay_item"] = {"track": d.call(it.GetTrackTypeAndIndex), "start": d.call(it.GetStart),
                           "end": d.call(it.GetEnd), "composite": d.call(it.GetProperties).get("CompositeMode"),
                           "opacity": d.call(it.GetProperties).get("Opacity")}
    frame = start + 30
    out_dir = RENDER_DIR / "s09"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*"):
        f.unlink()
    d.call(d.project.SetCurrentRenderMode, 1)
    d.render(out_dir / "with_overlay", fmt="png", codec="RGB8",
             settings={"SelectAllFrames": False, "MarkIn": frame, "MarkOut": frame,
                       "FormatWidth": 1080, "FormatHeight": 1920})
    png = sorted(out_dir.glob("with_overlay*"))[0]
    px = frame_pixels(png).reshape(-1, 3)
    rec["frame_file"] = str(png)
    rec["non_black_pct"] = round(float((px.max(axis=1) > 16).mean() * 100), 2)
    d.save()
    ok = rec["overlay_item"]["track"] == ["video", 2] and rec["overlay_item"]["start"] == start + 15 \
        and rec["non_black_pct"] > 50
    return "PASS" if ok else "FAIL"


run("S09_remotion_overlay", body)
