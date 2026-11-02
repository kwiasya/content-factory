"""A hand-written Library for the Script, build and font tests: a Pack of byte files, an index.json written by hand,
Author rows and an alias in a temp factory.db. No ffmpeg."""

from __future__ import annotations

from pathlib import Path

from cf import library
from cf.library import author
from cf.library.index import write_index
from cf.research.store import open_store

PACK = "fixture"
BYTES = bytes(range(256)) * 4

IDS = {
    "whoosh": "1" * 16, "whoosh2": "2" * 16, "boom": "3" * 16, "own_hit": "4" * 16, "shock": "5" * 16,
    "still_face": "6" * 16, "webm_face": "7" * 16, "emoji": "8" * 16, "emoji_raw": "9" * 16, "chipi": "a" * 16,
    "silent": "b" * 16, "img": "c" * 16, "bg": "d" * 16, "music": "e" * 16, "font": "f" * 16,
    "no_loud": "0" * 15 + "1",
}

LOUD = {"i": -22.0, "tp": -3.0, "lra": 1.0, "method": "padded"}


def _variant(path: str, role: str = "original", kind: str = "audio", **kw) -> dict:
    return {"role": role, "path": path, "size": len(BYTES), "mtime": 1759491000.0, "mtime_ns": 1, "content_id": "0",
            "kind": kind, "alpha": kw.pop("alpha", False), "codec": kw.pop("codec", None),
            "width": kw.pop("width", None), "height": kw.pop("height", None), "fps": kw.pop("fps", None),
            "duration_s": kw.pop("duration_s", None), "has_audio": kw.pop("has_audio", kind == "audio"), **kw}


def _asset(key: str, category: str, name: str, kind: str, variants: list[dict], **kw) -> dict:
    p = variants[0]
    return {"id": IDS[key], "category": category, "category_source": "mapping", "name": name, "slug": name,
            "kind": kind, "folder": p["path"].rsplit("/", 1)[0], "group": kw.get("group"), "variants": variants,
            "duration_s": kw.get("duration_s", p.get("duration_s")), "fps": kw.get("fps", p.get("fps")),
            "width": kw.get("width", p.get("width")), "height": kw.get("height", p.get("height")),
            "has_audio": kw.get("has_audio", kind == "audio"), "alpha": kw.get("alpha", False),
            "green_screen": kw.get("green_screen", False), "loudness": kw.get("loudness"),
            "derived": {"alpha": None, "converted": None, "png": None, "poster": None, "preview": None,
                        **kw.get("derived", {})},
            "rights_default": kw.get("rights", "unknown"), "agent": None}


def assets() -> list[dict]:
    face = dict(kind="video", alpha=True, width=512, height=512)
    return [
        _asset("whoosh", "sfx", "вуш-2", "audio", [_variant("sfx/вуш 2.mp3", duration_s=0.31)], loudness=LOUD),
        _asset("whoosh2", "sfx", "вуш-2-2", "audio", [_variant("sfx/вуш 2.wav", duration_s=0.5)],
               loudness={**LOUD, "method": "loudnorm"}),
        _asset("boom", "sfx", "boom", "audio", [_variant("sfx/boom.mp3", duration_s=2.5)],
               loudness={"i": -18.0, "tp": -2.0, "lra": 3.0, "method": "loudnorm"}),
        _asset("own_hit", "sfx", "own-hit", "audio", [_variant("sfx/own hit.wav", duration_s=1.0)],
               loudness={"i": -20.0, "tp": -10.0, "lra": 1.0, "method": "loudnorm"}, rights="own"),
        _asset("no_loud", "sfx", "тихо", "audio", [_variant("sfx/тихо.wav", duration_s=1.0)], rights="own"),
        _asset("shock", "face", "1750738-sticker", "video",
               [_variant("face/1750738_sticker.webm", codec="vp9", duration_s=0.001, **face),
                _variant("face-resolve/1750738_sticker.mov", role="alpha", codec="prores", fps=30.0,
                         duration_s=2.1, **face)],
               duration_s=2.1, fps=30.0, width=512, height=512, alpha=True, rights="own", group="sticker:1750738"),
        _asset("still_face", "face", "1750770-sticker", "image",
               [_variant("face/1750770_sticker.webm", codec="vp9", **{**face, "kind": "image"}),
                _variant("face-resolve/still — улыбка — 1750770_sticker.png", role="still", kind="image",
                         alpha=True, width=512, height=512)],
               duration_s=None, width=512, height=512, alpha=True, rights="own", group="sticker:1750770",
               derived={"png": f"png/{IDS['still_face']}.png"}),
        _asset("webm_face", "face", "1750799-sticker", "video",
               [_variant("face/1750799_sticker.webm", codec="vp9", fps=30.0, duration_s=2.0, **face)],
               duration_s=2.0, fps=30.0, width=512, height=512, alpha=True, rights="own", group="sticker:1750799"),
        _asset("emoji", "emoji", "в-шоке", "video",
               [_variant("emoji/в шоке.mp4", kind="video", codec="h264", width=1080, height=1080, fps=30.0,
                         duration_s=3.0, has_audio=False)],
               green_screen=True, derived={"alpha": f"keyed/{IDS['emoji']}.mov"}),
        _asset("emoji_raw", "emoji", "не-ключён", "video",
               [_variant("emoji/не ключён.mp4", kind="video", codec="h264", width=1080, height=1080, fps=30.0,
                         duration_s=3.0, has_audio=False)],
               green_screen=True),
        _asset("chipi", "meme", "chipi", "video",
               [_variant("memes/chipi.mp4", kind="video", codec="h264", width=1280, height=720, fps=30.0,
                         duration_s=4.0, has_audio=True)],
               has_audio=True, loudness={"i": -16.0, "tp": -1.5, "lra": 4.0, "method": "loudnorm"}),
        _asset("silent", "meme", "silent", "video",
               [_variant("memes/silent.mp4", kind="video", codec="h264", width=1280, height=720, fps=30.0,
                         duration_s=2.0, has_audio=False)],
               rights="free"),
        _asset("img", "img", "фон-1", "image",
               [_variant("img/фон 1.jfif", kind="image", width=800, height=600, has_audio=False)],
               derived={"png": f"png/{IDS['img']}.png"}),
        _asset("bg", "bg", "loop", "video",
               [_variant("bg/loop.mp4", kind="video", width=720, height=1280, fps=30.0, duration_s=10.0,
                         has_audio=False)], rights="free"),
        _asset("music", "music", "pixabay", "audio", [_variant("music/pixabay.mp3", duration_s=120.0)],
               rights="free", loudness={"i": -14.0, "tp": -1.0, "lra": 5.0, "method": "loudnorm"}),
        _asset("font", "font", "komika-title", "font", [_variant("fonts/Komika Title.otf", kind="font")],
               rights="free"),
    ]


def write_file(path: Path, data: bytes = BYTES) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def make_library(tmp: Path, root: Path | None = None, db: Path | None = None
                 ) -> tuple[library.Library, Path, Path]:
    """``(Library, shared root, factory.db)``; the Pack root is ``tmp/pack``, the root and db default to
    ``tmp/footage`` and ``<root>/factory.db``."""
    tmp = Path(tmp)
    pack = tmp / "pack"
    data = assets()
    for a in data:
        for v in a["variants"]:
            write_file(pack / v["path"])
    root = Path(root) if root else tmp / "footage"
    db = Path(db) if db else root / "factory.db"
    with open_store(db, seed=False, create=True) as s:
        library.register_pack(s, {"schema": "cf-pack/1", "id": PACK, "root": str(pack)})
        write_index(root, PACK, {"schema": "cf-library-index/1", "pack": PACK, "root": str(pack),
                                 "indexed_at": "2026-10-14T10:00:00Z", "assets": data, "report": {}})
        for a in data:
            for sub in a["derived"].values():
                if sub:
                    write_file(root / "library" / PACK / sub)
        author.write(s, IDS["shock"], PACK, {"name": "шок"})
        author.add_alias(s, "@emoji/старое-имя", IDS["emoji"], "rename")
        lib = library.load(root, s)
    return lib, root, db
