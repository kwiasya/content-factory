"""S3: 1080x1920 30 fps timeline; AppendToTimeline with recordFrame + trackIndex on V1 and V2.

Reads back GetStart/GetEnd/GetDuration/track for every returned item.
"""

from _common import FPS, driver, media, run


def describe(d, it):
    return {
        "name": d.call(it.GetName),
        "type": d.call(it.GetType),
        "track": d.call(it.GetTrackTypeAndIndex),
        "start": d.call(it.GetStart),
        "end": d.call(it.GetEnd),
        "duration": d.call(it.GetDuration),
        "src_start": d.call(it.GetSourceStartFrame),
        "src_end": d.call(it.GetSourceEndFrame),
    }


def body(rec):
    d = driver()
    p = d.project
    hlg, sdr = media(d)
    rec["clips"] = {c.GetName(): {k: c.GetClipProperty().get(k) for k in
                    ("FPS", "Resolution", "Frames", "Input Color Space", "Video Codec", "Type")} for c in (hlg, sdr)}

    # Project-level first (works only while the project has no timelines).
    proj = {}
    for k, v in [("timelineResolutionWidth", "1080"), ("timelineResolutionHeight", "1920"),
                 ("timelineFrameRate", str(FPS))]:
        ret = d.call(p.SetSettings, {k: v})
        proj[k] = {"returned": ret, "read": d.call(p.GetSettings).get(k)}
    rec["project_level"] = proj

    tl = d.create_timeline("S03", 1080, 1920, FPS)
    s = d.call(tl.GetSettings)
    rec["timeline_settings"] = {k: s.get(k) for k in ("useCustomSettings", "timelineResolutionWidth",
                                                      "timelineResolutionHeight", "timelineFrameRate")}
    start = d.call(tl.GetStartFrame)
    rec["timeline_start_frame"] = start
    rec["timeline_start_tc"] = d.call(tl.GetStartTimecode)
    rec["tracks_before"] = {"video": d.call(tl.GetTrackCount, "video"), "audio": d.call(tl.GetTrackCount, "audio")}
    if d.call(tl.GetTrackCount, "video") < 2:
        rec["AddTrack_video"] = d.call(tl.AddTrack, "video")

    plan = [
        {"mediaPoolItem": sdr, "startFrame": 0, "endFrame": 89, "trackIndex": 1, "recordFrame": start},
        {"mediaPoolItem": hlg, "startFrame": 0, "endFrame": 119, "trackIndex": 1, "recordFrame": start + 90},
        {"mediaPoolItem": hlg, "startFrame": 200, "endFrame": 259, "trackIndex": 2, "recordFrame": start + 45,
         "mediaType": 1},
    ]
    items = d.append(plan)
    rec["returned_count"] = len(items)
    rec["items"] = [describe(d, it) for it in items]
    rec["tracks_after"] = {"video": d.call(tl.GetTrackCount, "video"), "audio": d.call(tl.GetTrackCount, "audio")}
    rec["track_contents"] = {
        f"{t}{i}": [describe(d, it) for it in d.call(tl.GetItemListInTrack, t, i) or []]
        for t in ("video", "audio") for i in range(1, d.call(tl.GetTrackCount, t) + 1)
    }
    rec["timeline_end_frame"] = d.call(tl.GetEndFrame)

    v1 = rec["track_contents"].get("video1", [])
    v2 = rec["track_contents"].get("video2", [])
    ok = (rec["timeline_settings"]["timelineResolutionWidth"] == "1080"
          and rec["timeline_settings"]["timelineResolutionHeight"] == "1920"
          and float(rec["timeline_settings"]["timelineFrameRate"]) == FPS
          and len(v1) == 2 and len(v2) == 1
          and v1[0]["start"] == start and v1[1]["start"] == start + 90 and v2[0]["start"] == start + 45)
    d.save()
    return "PASS" if ok else "FAIL"


run("S03_timeline_append", body)
