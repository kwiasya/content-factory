"""S4: AddTransition with and without ``alignment``; which transition type names return an item.

V1 gets back-to-back 30-frame SDR clips (video only) with >= 30-frame handles on both
sides (source offsets wrap so every clip stays inside the 1008-frame source).
Each trial uses a fresh cut (the 'end' edge of clip i).
"""

from _common import FPS, driver, media, run

TRIALS = [
    {"type": "Cross Dissolve", "position": "end"},  # no alignment
    {"type": "Cross Dissolve", "position": "end", "alignment": "center"},
    {"type": "Cross Dissolve", "position": "end", "alignment": "center", "duration": 10},
    {"type": "Cross Dissolve", "position": "end", "alignment": "left", "category": "simple"},
    {"type": "Dip To Color Dissolve", "position": "end", "alignment": "center"},
    {"type": "Dip To Color Dissolve", "position": "end"},
    {"type": "Smooth Cut", "position": "end", "alignment": "center"},
    {"type": "Smooth Cut", "position": "end"},
    {"type": "Fade", "position": "end", "alignment": "center"},
    {"type": "Dip to Color Dissolve", "position": "end", "alignment": "center"},
    {"type": "Additive Dissolve", "position": "end", "alignment": "center"},
    {"type": "Blur Dissolve", "position": "end", "alignment": "center"},
    {"type": "Non-Additive Dissolve", "position": "end", "alignment": "center"},
    {"type": "Cross Dissolve", "category": "simple", "position": "end"},  # category, no alignment
    {"type": "Cross Dissolve", "category": "simple", "position": "end", "duration": 10},
    {"type": "Smooth Cut", "category": "simple", "position": "end", "duration": 4},
]


def body(rec):
    d = driver()
    _, sdr = media(d)
    tl = d.create_timeline("S04", 1080, 1920, FPS)
    start = d.call(tl.GetStartFrame)
    n = 2 * len(TRIALS) + 2
    plan = [{"mediaPoolItem": sdr, "startFrame": 30 + (i % 15) * 60, "endFrame": 60 + (i % 15) * 60, "trackIndex": 1,
             "recordFrame": start + i * 30, "mediaType": 1} for i in range(n)]
    items = d.append(plan)
    rec["clips"] = [(d.call(it.GetStart), d.call(it.GetEnd)) for it in items]
    trials = []
    for i, opts in enumerate(TRIALS):
        it = items[i]
        before = (d.call(it.GetStart), d.call(it.GetEnd), d.call(items[i + 1].GetStart))
        tr = d.call(it.AddTransition, opts)
        row = {"opts": opts, "returned": tr is not None, "clip_before": before,
               "clip_after": (d.call(it.GetStart), d.call(it.GetEnd), d.call(items[i + 1].GetStart))}
        if tr is not None:
            row.update(tr_type=d.call(tr.GetType), tr_name=d.call(tr.GetName),
                       tr_start=d.call(tr.GetStart), tr_end=d.call(tr.GetEnd), tr_track=d.call(tr.GetTrackTypeAndIndex))
        trials.append(row)
    # Retry every failure once with the full documented TransitionOptions
    # (type + category + position + alignment + duration), on fresh cuts.
    k = len(TRIALS)
    for row in [t for t in trials if not t["returned"]]:
        opts = {"category": "simple", "alignment": "center", "duration": 10, **row["opts"]}
        it = items[k]
        tr = d.call(it.AddTransition, opts)
        retry = {"opts": opts, "returned": tr is not None, "retry_of": row["opts"]}
        if tr is not None:
            retry.update(tr_name=d.call(tr.GetName), tr_start=d.call(tr.GetStart), tr_end=d.call(tr.GetEnd),
                         clip_after=(d.call(it.GetStart), d.call(it.GetEnd), d.call(items[k + 1].GetStart)))
        trials.append(retry)
        k += 1
    # Head transition on the first clip (no neighbour): fade from nothing.
    head = {"type": "Cross Dissolve", "category": "simple", "position": "start", "alignment": "right", "duration": 10}
    tr = d.call(items[0].AddTransition, head)
    trials.append({"opts": dict(head, clip=0),
                   "returned": tr is not None,
                   **({"tr_start": d.call(tr.GetStart), "tr_end": d.call(tr.GetEnd)} if tr else {})})
    rec["trials"] = trials
    rec["v1_after"] = [(d.call(x.GetType), d.call(x.GetName), d.call(x.GetStart), d.call(x.GetEnd))
                       for x in d.call(tl.GetItemListInTrack, "video", 1)]
    rec["accepted_types"] = sorted({t["opts"]["type"] for t in trials if t["returned"]})
    rec["rejected_types"] = sorted({t["opts"]["type"] for t in trials if not t["returned"]} - set(rec["accepted_types"]))
    d.save()
    rec["working_option_sets"] = [t["opts"] for t in trials if t["returned"]]
    return "PASS" if any(t["returned"] and t["opts"]["type"] == "Cross Dissolve" for t in trials) else "FAIL"


run("S04_transitions", body)
