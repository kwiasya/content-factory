"""S8: H.264 1080x1920 render with ColorSpaceTag / GammaTag candidates; ffprobe each file.

A 3-second SDR timeline is rendered once per tag combination to
~/Movies/content-factory/smoke/. The expected Instagram-safe result is
color_primaries/transfer/space = bt709 (1-1-1), pix_fmt yuv420p, 1080x1920.
"""

import json
import subprocess

from _common import FPS, RENDER_DIR, driver, media, run

COMBOS = [
    ("Rec.709", "Rec.709-A"),
    ("Same as Project", "Same as Project"),
    ("Rec.709", "Gamma 2.4"),
    ("Rec.709", "Rec.709"),
    ("Rec.709-A", "Rec.709-A"),
]


def ffprobe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,profile,width,height,pix_fmt,color_range,color_space,color_transfer,"
                          "color_primaries,r_frame_rate,nb_frames:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    return {**j["streams"][0], "duration": j["format"].get("duration")}


def body(rec):
    d = driver()
    p = d.project
    _, sdr = media(d)
    tl = d.create_timeline("S08", 1080, 1920, FPS)
    start = d.call(tl.GetStartFrame)
    d.append([{"mediaPoolItem": sdr, "startFrame": 0, "endFrame": 90, "trackIndex": 1, "recordFrame": start}])
    rec["codecs_mp4"] = d.call(p.GetRenderCodecs, "mp4")
    rec["SetCurrentRenderMode_single"] = d.call(p.SetCurrentRenderMode, 1)
    rec["page_after_SetCurrentRenderMode"] = d.call(d.resolve.GetCurrentPage)
    rec["SetCurrentRenderFormatAndCodec"] = d.call(p.SetCurrentRenderFormatAndCodec, "mp4", "H264")
    rec["GetCurrentRenderFormatAndCodec"] = d.call(p.GetCurrentRenderFormatAndCodec)
    rec["bogus_tag_returned"] = d.call(p.SetRenderSettings, {"GammaTag": "Bogus Gamma 9.9"})
    rec["bogus_key_returned"] = d.call(p.SetRenderSettings, {"NoSuchKey": 1})

    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    renders = []
    for cs, gamma in COMBOS:
        name = f"s08_{cs}_{gamma}".replace(" ", "_").replace(".", "")
        for f in RENDER_DIR.glob(f"{name}.*"):
            f.unlink()
        row = {"ColorSpaceTag": cs, "GammaTag": gamma,
               "tag_returned": d.call(p.SetRenderSettings, {"ColorSpaceTag": cs, "GammaTag": gamma})}
        try:
            row["status"] = d.render(RENDER_DIR / name, fmt="mp4", codec="H264", settings={
                "SelectAllFrames": True, "FormatWidth": 1080, "FormatHeight": 1920, "FrameRate": float(FPS),
                "ExportVideo": True, "ExportAudio": True, "ColorSpaceTag": cs, "GammaTag": gamma})
            files = sorted(RENDER_DIR.glob(f"{name}.*"))
            row["file"] = str(files[0])
            row["ffprobe"] = ffprobe(files[0])
        except Exception as exc:  # noqa: BLE001
            row["error"] = f"{type(exc).__name__}: {exc}"
        renders.append(row)
    rec["renders"] = renders
    rec["job_list_tail"] = (d.call(p.GetRenderJobList) or [])[-1:]
    d.save()

    def good(r):
        f = r.get("ffprobe") or {}
        return (f.get("color_primaries"), f.get("color_transfer"), f.get("color_space")) == ("bt709",) * 3 \
            and f.get("pix_fmt") == "yuv420p" and (f.get("width"), f.get("height")) == (1080, 1920)

    rec["one_one_one"] = [(r["ColorSpaceTag"], r["GammaTag"]) for r in renders if good(r)]
    return "PASS" if good(renders[0]) else "FAIL"


run("S08_render", body)
