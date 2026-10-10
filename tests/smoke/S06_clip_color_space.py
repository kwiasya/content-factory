"""S6: which 'Input Color Space' / 'Input Gamma' / 'Input LUT' strings SetClipProperty accepts.

Accepted means the value read back with GetClipProperty() equals the value written.
Combined strings are tried with separateColorSpaceAndGamma = 0, separate ones with 1.
Each clip is put back to its auto-detected value at the end.
"""

from _common import driver, media, run

HLG_CANDIDATES = ["Rec.2100 HLG (Scene)", "Rec.2020 HLG ARIB STD-B67", "Rec.2100 HLG", "Rec.2020 HLG",
                  "Apple Log", "Rec.709 Gamma 2.4"]
SDR_CANDIDATES = ["Rec.709 Gamma 2.4", "Rec.709-A", "Rec.709 (Scene)", "sRGB", "Rec.709"]
SEPARATE_CS = ["Rec.2020", "Rec.709", "Rec.2100"]
SEPARATE_GAMMA = ["Rec.2100 HLG", "Gamma 2.4", "Rec.709", "Rec.2100 ST2084", "Gamma 2.4 (Scene)"]
LUTS = ["DJI/DJI_X7_DLOG2Rec709.cube",
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/DJI/DJI_X7_DLOG2Rec709.cube"]


def body(rec):
    d = driver()
    p = d.project
    hlg, sdr = media(d)

    def props(clip):
        c = d.call(clip.GetClipProperty)
        return {k: c.get(k) for k in ("Input Color Space", "Input Gamma", "Input LUT", "IDT")}

    def probe(clip, key, value):
        ret = d.call(clip.SetClipProperty, key, value)
        got = d.call(clip.GetClipProperty).get(key)
        return {"key": key, "wrote": value, "returned": ret, "read": got, "accepted": got == value}

    original = {"hlg": props(hlg), "sdr": props(sdr)}
    rec["detected"] = original
    rec["project_separate_before"] = d.call(p.GetSettings).get("separateColorSpaceAndGamma")

    d.set_setting_verified("separateColorSpaceAndGamma", "0")
    rec["combined"] = {
        "hlg": [probe(hlg, "Input Color Space", v) for v in HLG_CANDIDATES],
        "sdr": [probe(sdr, "Input Color Space", v) for v in SDR_CANDIDATES],
    }

    d.set_setting_verified("separateColorSpaceAndGamma", "1")
    rec["after_separate_1"] = {"hlg": props(hlg), "sdr": props(sdr)}
    rec["separate"] = {
        "hlg_cs": [probe(hlg, "Input Color Space", v) for v in SEPARATE_CS],
        "hlg_gamma": [probe(hlg, "Input Gamma", v) for v in SEPARATE_GAMMA],
        "sdr_gamma": [probe(sdr, "Input Gamma", v) for v in SEPARATE_GAMMA],
    }
    rec["separate_state"] = {"hlg": props(hlg), "sdr": props(sdr)}
    # Retry (documented form: 'Input Gamma' e.g. 'Gamma 2.4') after first giving the clip a
    # separate-mode color space string as Resolve itself reports it ('... (Scene)').
    rec["separate_retry"] = [probe(hlg, "Input Color Space", "Rec.2020 (Scene)")] + [
        probe(hlg, "Input Gamma", v) for v in ("Rec.2100 HLG", "Rec.2100 HLG (Scene)", "ARIB STD-B67 HLG",
                                               "Linear", "Gamma 2.2", "sRGB", "Rec.709")]

    d.set_setting_verified("separateColorSpaceAndGamma", "0")
    rec["input_lut"] = [probe(sdr, "Input LUT", v) for v in LUTS]
    rec["RefreshLUTList"] = d.call(p.RefreshLUTList)
    rec["input_lut_retry"] = [probe(sdr, "Input LUT", v) for v in LUTS]
    rec["input_lut_clear"] = probe(sdr, "Input LUT", "")

    # Restore the auto-detected color spaces.
    for clip, key in ((hlg, "hlg"), (sdr, "sdr")):
        d.set_clip_property_verified(clip, "Input Color Space", original[key]["Input Color Space"])
    rec["final"] = {"hlg": props(hlg), "sdr": props(sdr)}
    # Is 'Input Gamma' re-derived when the combined color space is written again?
    for clip, key in ((hlg, "hlg"), (sdr, "sdr")):
        d.call(clip.SetClipProperty, "Input Color Space", "Rec.709 Gamma 2.4")
        d.call(clip.SetClipProperty, "Input Color Space", original[key]["Input Color Space"])
    rec["final_after_rewrite"] = {"hlg": props(hlg), "sdr": props(sdr)}
    d.save()

    acc = lambda rows: [r["wrote"] for r in rows if r["accepted"]]  # noqa: E731
    rec["accepted"] = {
        "hlg_combined": acc(rec["combined"]["hlg"]), "sdr_combined": acc(rec["combined"]["sdr"]),
        "separate_cs": acc(rec["separate"]["hlg_cs"]), "separate_gamma_hlg": acc(rec["separate"]["hlg_gamma"]),
        "separate_gamma_sdr": acc(rec["separate"]["sdr_gamma"]), "input_lut": acc(rec["input_lut"]),
        "separate_retry": acc(rec["separate_retry"]), "input_lut_retry": acc(rec["input_lut_retry"]),
    }
    ok = rec["accepted"]["hlg_combined"] and rec["accepted"]["sdr_combined"]
    return "PASS" if ok else "FAIL"


run("S06_clip_color_space", body)
