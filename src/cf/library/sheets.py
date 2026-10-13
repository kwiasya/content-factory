"""The agent tag pass hand-off: contact sheets of untagged Assets, and applying the agent's proposals.

Sheets are ``library/<pack>/sheets/NN.jpg`` (6×4 numbered tiles) with ``NN.json`` naming each tile's Asset.
Proposals land in ``index.json`` as the Asset's ``agent`` field, the only thing the tag pass writes.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2
import numpy as np

from cf.library.files import atomic_write
from cf.library.index import cache_dir, read_index, write_index
from cf.library.library import Asset, Library
from cf.research.store import now_iso

TILE = 240
COLS, ROWS = 6, 4
GREY = (64, 64, 64)


def tag_todo(library: Library, pack_id: str) -> list[Asset]:
    return [a for a in sorted(library.assets, key=lambda a: (a.category, a.ref))
            if a.pack == pack_id and not a.agent_caption and not a.agent_tags]


def _tile(a: Asset) -> np.ndarray:
    tile = np.full((TILE, TILE, 3), GREY, np.uint8)
    poster = a.derived.get("poster")
    img = cv2.imread(str(a.cache / poster)) if poster else None
    if img is not None and img.size:
        h, w = img.shape[:2]
        scale = min(TILE / w, TILE / h)
        img = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))))
        y, x = (TILE - img.shape[0]) // 2, (TILE - img.shape[1]) // 2
        tile[y:y + img.shape[0], x:x + img.shape[1]] = img
    elif a.kind == "audio":
        c = TILE // 2
        cv2.rectangle(tile, (c - 50, c - 20), (c - 20, c + 20), (220, 220, 220), -1)
        cv2.fillPoly(tile, [np.array([[c - 20, c - 20], [c + 20, c - 55], [c + 20, c + 55], [c - 20, c + 20]])],
                     (220, 220, 220))
        for r in (35, 55):
            cv2.ellipse(tile, (c + 20, c), (r, r), 0, -45, 45, (220, 220, 220), 4)
    else:
        cv2.putText(tile, a.kind, (20, TILE // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2)
    return tile


def write_sheets(footage: Path, library: Library, pack_id: str, per_sheet: int = COLS * ROWS) -> list[Path]:
    folder = cache_dir(footage, pack_id) / "sheets"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    todo = tag_todo(library, pack_id)
    out = []
    for s in range(0, len(todo), per_sheet):
        chunk = todo[s:s + per_sheet]
        sheet = np.zeros((ROWS * TILE, COLS * TILE, 3), np.uint8)
        listing = []
        for i, a in enumerate(chunk):
            tile = _tile(a)
            cv2.rectangle(tile, (0, 0), (52, 36), (0, 0, 0), -1)
            cv2.putText(tile, str(i + 1), (6, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            r, c = divmod(i, COLS)
            sheet[r * TILE:(r + 1) * TILE, c * TILE:(c + 1) * TILE] = tile
            listing.append({"n": i + 1, "id": a.id, "ref": a.ref, "folder": a.folder,
                            "name": a.primary["path"].rsplit("/", 1)[-1], "kind": a.kind,
                            "duration_s": a.duration_s})
        n = s // per_sheet + 1
        jpg = folder / f"{n:02d}.jpg"
        ok, buf = cv2.imencode(".jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ok:
            atomic_write(jpg, buf.tobytes())
        atomic_write(folder / f"{n:02d}.json", json.dumps(listing, ensure_ascii=False, indent=1).encode("utf-8"))
        out.append(jpg)
    return out


def apply_tags(footage: Path, pack_id: str, proposals: dict) -> tuple[int, list[str]]:
    idx = read_index(footage, pack_id)
    if idx is None:
        return 0, sorted(proposals)
    by_id = {a["id"]: a for a in idx["assets"]}
    applied, unknown = 0, []
    at = now_iso()
    for aid, p in proposals.items():
        a = by_id.get(aid)
        if a is None or not isinstance(p, dict):
            unknown.append(aid)
            continue
        tags = [" ".join(t.split()) for t in p.get("tags") or [] if isinstance(t, str) and t.strip()]
        caption = p.get("caption")
        a["agent"] = {"caption": " ".join(caption.split()) if isinstance(caption, str) else None,
                      "tags": list(dict.fromkeys(tags)), "at": at,
                      "basis": p.get("basis") if p.get("basis") in ("sheet", "name") else "sheet"}
        applied += 1
    if applied:
        write_index(footage, pack_id, idx)
    return applied, unknown
