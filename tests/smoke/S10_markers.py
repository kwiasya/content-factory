"""S10: AddMarker with customData JSON on the timeline and on a timeline item; read back.

Records which frame base each marker uses. Found on 21.1.1: timeline marker frames are
offsets from the timeline start (no range check); item marker frames are source-media
frames, clamped to the media extent.
"""

import json

from _common import FPS, driver, media, run


def body(rec):
    d = driver()
    _, sdr = media(d)
    tl = d.create_timeline("S10", 1080, 1920, FPS)
    start = d.call(tl.GetStartFrame)
    (item,) = d.append([{"mediaPoolItem": sdr, "startFrame": 100, "endFrame": 190, "trackIndex": 1,
                         "recordFrame": start, "mediaType": 1}])
    payload = json.dumps({"beat": 3, "shot": "IMG_1621#2", "note": "hook ends", "ünï": "ok"}, ensure_ascii=False)

    rec["timeline_marker"] = d.add_marker(tl, 45, "Blue", "beat-3", "agent note", 1, payload)
    rec["timeline_markers_all"] = d.call(tl.GetMarkers)
    rec["timeline_absolute_frame_attempt"] = d.call(tl.AddMarker, start + 60, "Red", "abs", "", 1, "{}")
    rec["timeline_markers_after_abs"] = sorted(d.call(tl.GetMarkers))
    rec["timeline_GetMarkerByCustomData"] = d.call(tl.GetMarkerByCustomData, payload)
    rec["timeline_UpdateMarkerCustomData"] = d.call(tl.UpdateMarkerCustomData, 45, '{"beat": 4}')
    rec["timeline_GetMarkerCustomData"] = d.call(tl.GetMarkerCustomData, 45)

    rec["item_marker"] = d.add_marker(item, 10, "Green", "shot-good", "sharp, stable", 5, payload)
    rec["item_markers_all"] = d.call(item.GetMarkers)
    rec["item_source_frame_attempt"] = d.call(item.AddMarker, 120, "Yellow", "src", "", 1, "{}")
    rec["item_markers_after_src"] = sorted(d.call(item.GetMarkers))
    rec["mediapool_clip_markers"] = d.call(sdr.GetMarkers)
    # Range probe: item frames outside the source media are clamped to [0, last source frame],
    # which shows item marker frames are source frames, not offsets from the item start.
    rec["item_left_offset"] = d.call(item.GetLeftOffset)
    rec["item_clamp_probe"] = {"add_2000": d.call(item.AddMarker, 2000, "Red", "far", "", 1, ""),
                               "add_-5": d.call(item.AddMarker, -5, "Red", "neg", "", 1, ""),
                               "keys": sorted(d.call(item.GetMarkers))}
    rec["timeline_beyond_end"] = {"add_5000": d.call(tl.AddMarker, 5000, "Red", "far", "", 1, ""),
                                  "timeline_duration": d.call(tl.GetEndFrame) - start,
                                  "keys": sorted(d.call(tl.GetMarkers))}

    rec["json_roundtrip"] = json.loads(rec["item_marker"]["customData"]) == json.loads(payload)
    d.save()
    ok = rec["json_roundtrip"] and rec["timeline_GetMarkerCustomData"] == '{"beat": 4}'
    return "PASS" if ok else "FAIL"


run("S10_markers", body)
