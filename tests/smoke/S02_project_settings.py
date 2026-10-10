"""S2: color-managed project settings; discover exact DWG / Intermediate and Rec.709 strings.

Writes one key per SetSettings call and reads back with GetSettings. Dumps every
project setting to out/project_settings.json (before and after).
"""

import json

from _common import OUT_DIR, driver, run


def body(rec):
    d = driver()
    p = d.project

    def probe(key, value):
        ret = d.call(p.SetSettings, {key: value})
        got = d.call(p.GetSettings).get(key)
        return {"key": key, "wrote": value, "returned": ret, "read": got, "accepted": str(got) == str(value)}

    before = d.call(p.GetSettings)
    tries = []
    tries.append(probe("colorScienceMode", "davinciYRGBColorManagedv2"))
    tries.append(probe("isAutoColorManage", "0"))
    tries.append(probe("timelineWorkingLuminanceMode", "SDR 100"))
    rec["after_v2_switch"] = {k: v for k, v in d.call(p.GetSettings).items()
                              if k.startswith(("colorSpace", "inputDRT", "outputDRT", "rcm", "separate", "isAuto"))}

    # Combined color space + gamma strings (separateColorSpaceAndGamma = 0).
    tries.append(probe("separateColorSpaceAndGamma", "0"))
    for v in ["DaVinci WG/Intermediate", "DaVinci Wide Gamut Intermediate", "DaVinci WG Intermediate",
              "DaVinci Wide Gamut/DaVinci Intermediate"]:
        tries.append(probe("colorSpaceTimeline", v))
    for v in ["Rec.709 Gamma 2.4", "Rec.709 (Scene)"]:
        tries.append(probe("colorSpaceOutput", v))
    for v in ["DaVinci", "Luminance Mapping", "None"]:
        tries.append(probe("inputDRT", v))
    for v in ["DaVinci", "None"]:
        tries.append(probe("outputDRT", v))

    # Separate color space and gamma (separateColorSpaceAndGamma = 1).
    tries.append(probe("separateColorSpaceAndGamma", "1"))
    rec["after_separate_1"] = {k: v for k, v in d.call(p.GetSettings).items() if k.startswith("colorSpace")}
    for v in ["DaVinci WG", "DaVinci Wide Gamut"]:
        tries.append(probe("colorSpaceTimeline", v))
    for v in ["DaVinci Intermediate"]:
        tries.append(probe("colorSpaceTimelineGamma", v))
    for v in ["Rec.709"]:
        tries.append(probe("colorSpaceOutput", v))
    for v in ["Gamma 2.4", "Rec.709 Gamma 2.4"]:
        tries.append(probe("colorSpaceOutputGamma", v))
    rec["separate_1_state"] = {k: v for k, v in d.call(p.GetSettings).items() if k.startswith("colorSpace")}

    # Back to combined mode, leave the project on DWG/Intermediate -> Rec.709 Gamma 2.4.
    tries.append(probe("separateColorSpaceAndGamma", "0"))
    rec["after_separate_0_again"] = {k: v for k, v in d.call(p.GetSettings).items() if k.startswith("colorSpace")}
    final = {}
    for key, cands in [("colorSpaceTimeline", ["DaVinci WG/Intermediate", "DaVinci Wide Gamut Intermediate"]),
                       ("colorSpaceOutput", ["Rec.709 Gamma 2.4"]),
                       ("inputDRT", ["DaVinci"]), ("outputDRT", ["DaVinci"])]:
        for v in cands:
            t = probe(key, v)
            tries.append(t)
            if t["accepted"]:
                final[key] = v
                break

    # Deprecated single-key form, for the record.
    rec["deprecated_SetSetting"] = {
        "returned": d.call(p.SetSetting, "colorSpaceOutputToneMapping", "None"),
        "GetSetting": d.call(p.GetSetting, "colorSpaceOutputToneMapping"),
    }
    d.save()
    after = d.call(p.GetSettings)
    (OUT_DIR / "project_settings.json").write_text(json.dumps(
        {"before": before, "after": after}, indent=2, ensure_ascii=False, default=str))
    rec["tries"] = tries
    rec["final"] = final
    rec["final_color_settings"] = {k: v for k, v in after.items()
                                   if k.startswith(("colorSpace", "colorScience", "inputDRT", "outputDRT",
                                                    "separate", "isAuto", "timelineWorking"))}
    ok = after.get("colorScienceMode") == "davinciYRGBColorManagedv2" and len(final) == 4
    return "PASS" if ok else "FAIL"


run("S02_project_settings", body)
