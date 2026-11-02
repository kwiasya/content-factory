"""S11: Library Asset cues the way cf.build places them (docs/script-schema.md, Assets).

Generates its own media with ffmpeg into tests/smoke/out/S11/ (no Pack, no external clips) and records:
tracks up to V4/A3; an mp3 on A3 (start/end, clip FPS, AudioVolume -7.3 / +12 / +20 read back); a 512x512
ProRes 4444 disc on V4 with ZoomX 0.4444, Pan 0, Tilt 120 and a still (centroid -> the Tilt sign, diameter
-> whether scaleToFit upscales a small item); a png appended for 45 and 200 frames (the still length); a VP9
webm with alpha (import, alpha mode, transparency in a still); a 1280x720 mp4 meme with stereo sound as a
video and an audio append (audio track spill).

PASS when the tracks, the mp3, the disc (with the Tilt sign recorded either way) and the meme hold; the png
and webm facts are recorded.
"""

import subprocess
import time
from pathlib import Path

from _common import FPS, OUT_DIR, driver, run, try_call

W, H = 2160, 3840
MEDIA = OUT_DIR / "S11"
DISC = "color=c=red:s=512x512:d={d}:r=30,format=rgba,geq=r='255':g='0':b='0':a='if(lte(hypot(X-255.5,Y-255.5),256),255,0)'"


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", *args], check=True)


def make_media() -> dict[str, Path]:
    MEDIA.mkdir(parents=True, exist_ok=True)
    m = {k: MEDIA / v for k, v in {"mp3": "tone.mp3", "wav": "tone.wav", "disc": "disc.mov", "png": "disc.png",
                                   "webm": "disc.webm", "meme": "meme.mp4", "base": "base.mp4"}.items()}
    ff("-f", "lavfi", "-i", "sine=f=1000:d=0.4", "-c:a", "libmp3lame", str(m["mp3"]))
    ff("-f", "lavfi", "-i", "sine=f=1000:d=1", "-c:a", "pcm_s16le", str(m["wav"]))
    ff("-f", "lavfi", "-i", DISC.format(d=2), "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
       str(m["disc"]))
    ff("-f", "lavfi", "-i", DISC.format(d=1), "-frames:v", "1", str(m["png"]))
    ff("-f", "lavfi", "-i", DISC.format(d=2), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", str(m["webm"]))
    ff("-f", "lavfi", "-i", "testsrc=s=1280x720:d=2:r=30", "-f", "lavfi", "-i", "sine=f=500:d=2", "-ac", "2",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(m["meme"]))
    ff("-f", "lavfi", "-i", f"color=c=0x808080:s={W}x{H}:d=20:r=30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
       str(m["base"]))
    return m


def still(d, tl, frame: int, path: Path) -> dict:
    from cf.build import timecode

    page = d.call(d.resolve.GetCurrentPage)
    if page not in ("edit", "color"):
        d.call(d.resolve.OpenPage, "edit")
    tc = timecode(frame, FPS)
    path.unlink(missing_ok=True)
    d.call(tl.SetCurrentTimecode, tc)
    ok = False
    for _ in range(3):
        ok = d.call(d.project.ExportCurrentFrameAsStill, str(path), timeout=60)
        if ok and path.exists():
            break
        time.sleep(1.0)
    return {"timecode": tc, "playhead": d.call(tl.GetCurrentTimecode), "returned": ok, "exists": path.exists()}


def red_disc(path: Path) -> dict | None:
    import cv2
    import numpy as np

    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        return None
    b, g, r = img[..., 0].astype(int), img[..., 1].astype(int), img[..., 2].astype(int)
    ys, xs = np.nonzero((r > 180) & (g < 90) & (b < 90))
    if not len(xs):
        return {"size": [img.shape[1], img.shape[0]], "red_pixels": 0}
    return {"size": [img.shape[1], img.shape[0]], "red_pixels": int(len(xs)),
            "centroid": [round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
            "diameter_x": int(xs.max() - xs.min() + 1), "diameter_y": int(ys.max() - ys.min() + 1)}


def pixel(path: Path, x: int, y: int) -> list[int] | None:
    import cv2

    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return None if img is None else [int(v) for v in img[y, x][::-1]]


def item_row(d, it) -> dict:
    return {"name": d.call(it.GetName), "start": d.call(it.GetStart), "end": d.call(it.GetEnd),
            "duration": d.call(it.GetDuration)}


def body(rec):
    m = make_media()
    d = driver()
    tl = d.create_timeline("S11", W, H, FPS)
    start = int(d.call(tl.GetStartFrame))
    rec["mismatch"] = (d.call(tl.GetSettings) or {}).get("timelineInputResMismatchBehavior")
    base, mp3, disc, png, meme = d.import_media([m["base"], m["mp3"], m["disc"], m["png"], m["meme"]],
                                                bin_name="S11")
    d.append([{"mediaPoolItem": base, "startFrame": 0, "endFrame": 600, "mediaType": 1, "trackIndex": 1,
               "recordFrame": start}])

    # 1. tracks.
    rec["tracks"] = {"video": d.ensure_tracks(tl, "video", 4, {4: "assets"}),
                     "audio": d.ensure_tracks(tl, "audio", 3, {2: "music", 3: "sfx"}, sub_type="stereo")}
    ok1 = rec["tracks"] == {"video": 4, "audio": 3}

    # 2. mp3 on A3.
    rec["mp3_clip"] = {k: (d.call(mp3.GetClipProperty) or {}).get(k) for k in ("FPS", "Frames", "Duration")}
    (a,) = d.append([{"mediaPoolItem": mp3, "startFrame": 0, "endFrame": 12, "mediaType": 2, "trackIndex": 3,
                      "recordFrame": start + 15}])
    rec["mp3_item"] = item_row(d, a)
    vols = {}
    for v in (-7.3, 12.0, 20.0, 31.0):
        vols[str(v)] = {"returned": d.call(a.SetProperties, {"AudioVolume": v}),
                        "read": (d.call(a.GetProperties) or {}).get("AudioVolume")}
    rec["mp3_AudioVolume"] = vols
    ok2 = (rec["mp3_item"]["start"], rec["mp3_item"]["end"]) == (start + 15, start + 27) and \
        abs(float(vols["-7.3"]["read"]) + 7.3) < 0.05 and abs(float(vols["12.0"]["read"]) - 12.0) < 0.05

    # 3. the ProRes disc on V4.
    rec["disc_clip"] = {k: (d.call(disc.GetClipProperty) or {}).get(k) for k in ("FPS", "Frames", "Alpha mode",
                                                                                  "Resolution")}
    (v,) = d.append([{"mediaPoolItem": disc, "startFrame": 0, "endFrame": 45, "mediaType": 1, "trackIndex": 4,
                      "recordFrame": start + 30}])
    rec["disc_item"] = item_row(d, v)
    before = d.call(v.GetProperties) or {}
    rec["disc_before"] = {k: before.get(k) for k in ("ZoomX", "ZoomY", "ZoomGang", "Pan", "Tilt")}
    writes = {}
    for key, val in (("ZoomGang", True), ("ZoomX", 0.4444), ("Pan", 0.0), ("Tilt", 120.0)):
        writes[key] = {"returned": d.call(v.SetProperties, {key: val}), "read": (d.call(v.GetProperties) or {}).get(key)}
    rec["disc_writes"] = writes
    after = d.call(v.GetProperties) or {}
    rec["disc_after"] = {k: after.get(k) for k in ("ZoomX", "ZoomY", "ZoomGang", "Pan", "Tilt")}
    f = MEDIA / "disc-still.png"
    rec["disc_still"] = still(d, tl, start + 52, f)
    got = red_disc(f) or {}
    rec["disc_measured"] = got
    expect_d = 512 * min(W / 512, H / 512) * 0.4444
    rec["disc_expected_diameter_if_upscaled"] = round(expect_d, 1)
    if got.get("centroid"):
        cy = got["centroid"][1]
        rec["tilt_up_positive"] = abs(cy - (H / 2 - 120)) < abs(cy - (H / 2 + 120))
        rec["small_item_upscaled_by_scaleToFit"] = abs(got["diameter_x"] - expect_d) <= 0.02 * expect_d
        rec["base_scale_measured"] = round(got["diameter_x"] / 512 / 0.4444, 4)
    ok3 = (rec["disc_item"]["start"], rec["disc_item"]["end"]) == (start + 30, start + 75) and \
        abs(float(after.get("ZoomX") or 0) - 0.4444) < 1e-3 and abs(float(after.get("Tilt") or 0) - 120) < 0.5 \
        and "tilt_up_positive" in rec

    # 4. the png still.
    rec["png_clip"] = {k: (d.call(png.GetClipProperty) or {}).get(k) for k in ("Frames", "Duration", "FPS",
                                                                                "Alpha mode")}
    rec["png_items"] = {}
    for n, at in ((45, 100), (200, 150)):
        got_items = try_call(d.append, [{"mediaPoolItem": png, "startFrame": 0, "endFrame": n, "mediaType": 1,
                                         "trackIndex": 4, "recordFrame": start + at}])
        rec["png_items"][str(n)] = item_row(d, got_items["value"][0]) if got_items["ok"] else got_items

    # 5. the VP9 webm.
    imp = try_call(d.import_media, [m["webm"]], "S11")
    rec["webm_import"] = {"ok": imp["ok"], "error": imp.get("error")}
    if imp["ok"]:
        webm = imp["value"][0]
        rec["webm_clip"] = {k: (d.call(webm.GetClipProperty) or {}).get(k) for k in ("FPS", "Frames", "Alpha mode",
                                                                                      "Video Codec", "Resolution")}
        app = try_call(d.append, [{"mediaPoolItem": webm, "startFrame": 0, "endFrame": 30, "mediaType": 1,
                                   "trackIndex": 4, "recordFrame": start + 360}])
        rec["webm_item"] = item_row(d, app["value"][0]) if app["ok"] else app
        if app["ok"]:
            f = MEDIA / "webm-still.png"
            rec["webm_still"] = still(d, tl, start + 370, f)
            rec["webm_corner_rgb"] = pixel(f, 20, (H - W) // 2 + 20)
            rec["webm_disc_measured"] = red_disc(f)
            corner = rec["webm_corner_rgb"] or [0, 0, 0]
            rec["webm_alpha_kept"] = all(abs(c - 128) < 24 for c in corner)

    # 6. the mp4 meme: picture and sound in two appends.
    n_audio_before = int(d.call(tl.GetTrackCount, "audio"))
    (mv,) = d.append([{"mediaPoolItem": meme, "startFrame": 0, "endFrame": 60, "mediaType": 1, "trackIndex": 4,
                       "recordFrame": start + 420}])
    ma = d.append([{"mediaPoolItem": meme, "startFrame": 0, "endFrame": 60, "mediaType": 2, "trackIndex": 3,
                    "recordFrame": start + 420}])
    rec["meme_video"] = item_row(d, mv)
    rec["meme_audio"] = [item_row(d, x) for x in ma]
    rec["meme_clip"] = {k: (d.call(meme.GetClipProperty) or {}).get(k) for k in ("FPS", "Frames", "Audio Ch",
                                                                                  "Audio Codec")}
    rec["audio_tracks"] = {"before": n_audio_before, "after": int(d.call(tl.GetTrackCount, "audio"))}
    ok6 = (rec["meme_video"]["start"], rec["meme_video"]["end"]) == (start + 420, start + 480) and \
        bool(ma) and (rec["meme_audio"][0]["start"], rec["meme_audio"][0]["end"]) == (start + 420, start + 480)
    d.save()
    rec["holds"] = {"1_tracks": ok1, "2_mp3": ok2, "3_disc": ok3, "6_meme": ok6}
    return "PASS" if ok1 and ok2 and ok3 and ok6 else "FAIL"


run("S11_library_assets", body)
