"""S5: InsertFusionTitleIntoTimeline('Text+'): where it lands, whether it ripples, StyledText, render.

Layout before insert: V1 = A [0,60) B [60,120) C [120,180); V2 = D [150,180); playhead at +30.
The title's track/start/end and every other item's start/end are recorded after the insert.
Then the TextPlus tool's StyledText is set to 'SMOKE' and read back, and one frame is
rendered to PNG with the title enabled and disabled; the pixel difference proves it renders.
"""

import subprocess

import numpy as np
from _common import FPS, RENDER_DIR, driver, media, run


def layout(d, tl):
    out = {}
    for t in ("video", "audio"):
        for i in range(1, d.call(tl.GetTrackCount, t) + 1):
            out[f"{t}{i}"] = [(d.call(x.GetName), d.call(x.GetStart), d.call(x.GetEnd))
                              for x in d.call(tl.GetItemListInTrack, t, i) or []]
    return out


def png_pixels(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).astype(np.int16)


def render_frame(d, frame, name):
    out_dir = RENDER_DIR / "s05"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob(f"{name}*"):
        f.unlink()
    d.call(d.project.SetCurrentRenderMode, 1)
    d.render(out_dir / name, fmt="png", codec="RGB8",
             settings={"SelectAllFrames": False, "MarkIn": frame, "MarkOut": frame,
                       "FormatWidth": 1080, "FormatHeight": 1920})
    files = sorted(out_dir.glob(f"{name}*"))
    return files


def body(rec):
    d = driver()
    hlg, sdr = media(d)
    tl = d.create_timeline("S05", 1080, 1920, FPS)
    start = d.call(tl.GetStartFrame)
    if d.call(tl.GetTrackCount, "video") < 2:
        d.call(tl.AddTrack, "video")
    d.append([
        {"mediaPoolItem": sdr, "startFrame": 0, "endFrame": 60, "trackIndex": 1, "recordFrame": start, "mediaType": 1},
        {"mediaPoolItem": sdr, "startFrame": 100, "endFrame": 160, "trackIndex": 1, "recordFrame": start + 60,
         "mediaType": 1},
        {"mediaPoolItem": sdr, "startFrame": 200, "endFrame": 260, "trackIndex": 1, "recordFrame": start + 120,
         "mediaType": 1},
        {"mediaPoolItem": hlg, "startFrame": 0, "endFrame": 60, "trackIndex": 2, "recordFrame": start + 150,
         "mediaType": 1},
    ])
    rec["layout_before"] = layout(d, tl)
    rec["SetCurrentTimecode"] = d.call(tl.SetCurrentTimecode, "01:00:01:00")
    rec["playhead_tc"] = d.call(tl.GetCurrentTimecode)
    rec["page"] = d.call(d.resolve.GetCurrentPage)

    title = d.call(tl.InsertFusionTitleIntoTimeline, "Text+")
    rec["returned"] = title is not None
    if title is None:
        rec["retry_InsertTitleIntoTimeline_Text+"] = d.call(tl.InsertTitleIntoTimeline, "Text+") is not None
        return "FAIL"
    rec["title"] = {"name": d.call(title.GetName), "type": d.call(title.GetType),
                    "track": d.call(title.GetTrackTypeAndIndex), "start": d.call(title.GetStart),
                    "end": d.call(title.GetEnd), "duration": d.call(title.GetDuration)}
    rec["layout_after"] = layout(d, tl)
    rec["rippled"] = rec["layout_before"]["video1"] != [x for x in rec["layout_after"]["video1"]
                                                        if x[0] != rec["title"]["name"]]

    rec["comp_count"] = d.call(title.GetFusionCompCount)
    comp = d.call(title.GetFusionCompByIndex, 1)
    tools = d.call(comp.GetToolList, False, "TextPlus") or {}
    rec["textplus_tools"] = len(tools)
    tool = list(tools.values())[0]
    rec["default_StyledText"] = d.call(tool.GetInput, "StyledText")
    rec["SetInput_returned"] = d.call(tool.SetInput, "StyledText", "SMOKE")
    rec["readback_StyledText"] = d.call(tool.GetInput, "StyledText")

    # Does it render? Same frame with the title enabled and disabled.
    frame = int(rec["title"]["start"]) + 10
    rec["render_frame"] = frame
    still = RENDER_DIR / "s05" / "still.png"
    still.parent.mkdir(parents=True, exist_ok=True)
    d.call(tl.SetCurrentTimecode, "01:00:01:10")
    rec["ExportCurrentFrameAsStill"] = d.call(d.project.ExportCurrentFrameAsStill, str(still))
    on = render_frame(d, frame, "title_on")
    d.call(title.SetClipEnabled, False)
    off = render_frame(d, frame, "title_off")
    d.call(title.SetClipEnabled, True)
    rec["files"] = [str(f) for f in on + off]
    a, b = png_pixels(on[0]), png_pixels(off[0])
    diff = np.abs(a - b)
    rec["pixels_changed_pct"] = round(float((diff.reshape(-1, 3).max(axis=1) > 32).mean() * 100), 3)
    d.save()
    ok = rec["readback_StyledText"] == "SMOKE" and rec["pixels_changed_pct"] > 0.1
    return "PASS" if ok else "FAIL"


run("S05_fusion_title", body)
