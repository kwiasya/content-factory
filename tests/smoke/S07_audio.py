"""S7: audio on the timeline: AudioVolume, SetFades, NormalizeAudioLevel.

Canonical 21.1 form is SetProperties({...}); the deprecated SetProperty(key, value)
is tried as well for the record.
"""

from _common import FPS, driver, media, run


def body(rec):
    d = driver()
    _, sdr = media(d)
    tl = d.create_timeline("S07", 1080, 1920, FPS)
    start = d.call(tl.GetStartFrame)
    d.append([{"mediaPoolItem": sdr, "startFrame": 0, "endFrame": 90, "trackIndex": 1, "recordFrame": start},
              {"mediaPoolItem": sdr, "startFrame": 300, "endFrame": 390, "trackIndex": 1,
               "recordFrame": start + 90}])
    a1 = d.call(tl.GetItemListInTrack, "audio", 1)
    v1 = d.call(tl.GetItemListInTrack, "video", 1)
    rec["a1_items"] = [(d.call(x.GetName), d.call(x.GetType), d.call(x.GetStart), d.call(x.GetEnd)) for x in a1]
    rec["linked_from_video"] = [d.call(x.GetType) for x in d.call(v1[0].GetLinkedItems) or []]
    aud, aud2, vid = a1[0], a1[1], v1[0]
    keys = ("AudioVolumeEnabled", "AudioVolume", "AudioPan", "AudioPitchEnabled")
    rec["audio_props_before"] = {k: d.call(aud.GetProperties).get(k) for k in keys}
    rec["video_props_has_AudioVolume"] = "AudioVolume" in (d.call(vid.GetProperties) or {})

    # AudioVolume, canonical and deprecated forms.
    rec["SetProperties_AudioVolume"] = {"returned": d.call(aud.SetProperties, {"AudioVolume": -20.0}),
                                        "read": d.call(aud.GetProperties).get("AudioVolume")}
    rec["SetProperty_AudioVolume_deprecated"] = {"returned": d.call(aud2.SetProperty, "AudioVolume", -12.0),
                                                 "read": d.call(aud2.GetProperty, "AudioVolume")}
    rec["SetProperties_AudioVolume_on_video_item"] = {"returned": d.call(vid.SetProperties, {"AudioVolume": -20.0}),
                                                      "read": d.call(vid.GetProperties).get("AudioVolume")}

    # Fades.
    rec["fades_before"] = {"audio": d.call(aud.GetFades), "video": d.call(vid.GetFades)}
    rec["SetFades_audio"] = {"returned": d.call(aud.SetFades, {"FadeIn": 15, "FadeOut": 20}),
                             "read": d.call(aud.GetFades)}
    rec["SetFades_video"] = {"returned": d.call(vid.SetFades, {"FadeIn": 10, "FadeOut": 0}),
                             "read": d.call(vid.GetFades)}

    # Normalize.
    modes = d.call(tl.GetNormalizeAudioModes)
    rec["normalize_modes"] = modes
    norm = []
    for opts in ([{"normalizationMode": modes[0], "targetLevel": -9.0}] if modes else []) + \
            [{"normalizationMode": m, "targetLoudness": -14.0} for m in (modes or []) if "1770" in m or "LUFS" in m]:
        ret = d.call(tl.NormalizeAudioLevel, [aud, aud2], opts)
        norm.append({"opts": opts, "returned": ret,
                     "aud_after": {k: d.call(aud.GetProperties).get(k) for k in keys},
                     "aud2_after": {k: d.call(aud2.GetProperties).get(k) for k in keys}})
    rec["normalize"] = norm
    rec["normalize_no_options"] = d.call(tl.NormalizeAudioLevel, [aud])
    d.save()

    ok = (abs(float(rec["SetProperties_AudioVolume"]["read"]) + 20.0) < 0.01
          and rec["SetFades_audio"]["read"] == {"FadeIn": 15, "FadeOut": 20}
          and any(n["returned"] for n in norm))
    return "PASS" if ok else "FAIL"


run("S07_audio", body)
