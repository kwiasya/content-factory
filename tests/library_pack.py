"""A synthetic Pack for the Library tests: tiny media made by ffmpeg once per process, copied per test."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
needs_ffmpeg = unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")

CONFIG = {
    "schema": "cf-pack/1",
    "id": "synth",
    "include": ["sfx", "emoji", "face", "face-resolve", "img", "fonts", "unmapped", "junk"],
    "templates": True,
    "folders": {
        "sfx": {"category": "sfx"},
        "emoji": {"category": "emoji", "key": "green"},
        "face": {"category": "face", "rights": "own", "group": "sticker"},
        "face-resolve": {"category": "face", "rights": "own", "group": "sticker"},
        "img": {"category": "img"},
        "fonts": {"category": "font"},
    },
}

_TEMPLATE: Path | None = None
_KEEP: tempfile.TemporaryDirectory | None = None


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", *args], check=True)


def _build(root: Path) -> None:
    for d in ("sfx", "emoji", "face", "face-resolve", "img", "fonts", "unmapped", "junk", "templates/P.dra"):
        (root / d).mkdir(parents=True, exist_ok=True)
    _ff("-f", "lavfi", "-i", "sine=f=440:d=1", "-c:a", "pcm_s16le", str(root / "sfx/вуш 2.wav"))
    _ff("-f", "lavfi", "-i", "sine=f=660:d=1", "-c:a", "libmp3lame", str(root / "sfx/вуш 2.mp3"))
    _ff("-f", "lavfi", "-i", "sine=f=880:d=0.2", "-c:a", "pcm_s16le", str(root / "sfx/поп.wav"))
    _ff("-f", "lavfi", "-i", "sine=f=330:d=1", "-c:a", "libmp3lame", str(root / "sfx/+1.mp3"))
    _ff("-f", "lavfi", "-i", "color=c=0x00FF00:s=64x64:d=1:r=30", "-f", "lavfi", "-i",
        "color=c=red:s=16x16:d=1:r=30", "-filter_complex", "[0][1]overlay=24:24", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", str(root / "emoji/в шоке.mp4"))
    src = "color=c=red@0.5:s=64x64:d={d}:r=30,format=yuva420p"
    _ff("-f", "lavfi", "-i", src.format(d=1), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        str(root / "face/1000001_sticker.webm"))
    _ff("-f", "lavfi", "-i", src.format(d=1).replace("red", "blue"), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        str(root / "face/1000002_sticker.webm"))
    _ff("-f", "lavfi", "-i", src.format(d=2).replace("yuva420p", "yuva444p10le"), "-c:v", "prores_ks",
        "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(root / "face-resolve/1000001_sticker.mov"))
    _ff("-f", "lavfi", "-i", "color=c=blue@0.5:s=64x64:d=1,format=rgba", "-frames:v", "1",
        str(root / "face-resolve/still — улыбка — 1000002_sticker.png"))
    _ff("-f", "lavfi", "-i", "color=c=yellow:s=64x64:d=1", "-frames:v", "1", "-f", "mjpeg",
        str(root / "img/фон 1.jfif"))
    _ff("-f", "lavfi", "-i", "testsrc=s=64x64:d=0.2:r=10", "-f", "gif", str(root / "img/anim.gif"))
    (root / "fonts/Komika Title.otf").write_bytes(b"OTTO not really a font")
    _ff("-f", "lavfi", "-i", "testsrc=s=64x64:d=1:r=30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(root / "unmapped/clip.mp4"))
    for name in (".DS_Store", "x.url", "list.m3u8", "index.html", "a.pdf", "b.psd"):
        (root / "junk" / name).write_bytes(b"junk")
    os.symlink(root / "emoji/в шоке.mp4", root / "junk/link.mp4")
    (root / "templates/T.drfx").write_bytes(b"drfx bytes")
    (root / "templates/P.dra/project.drp").write_bytes(b"drp bytes")


def template() -> Path:
    global _TEMPLATE, _KEEP
    if _TEMPLATE is None:
        _KEEP = tempfile.TemporaryDirectory()
        _TEMPLATE = Path(_KEEP.name) / "pack"
        _build(_TEMPLATE)
    return _TEMPLATE


def snapshot(root: Path) -> dict[str, tuple]:
    out: dict[str, tuple] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            rel = p.relative_to(root).as_posix()
            st = p.lstat()
            if p.is_symlink() or p.is_dir():
                out[rel] = (st.st_mtime_ns,)
            else:
                out[rel] = (st.st_size, st.st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
    return out


class SyntheticPack(unittest.TestCase):
    """A fresh copy of the Pack, an empty footage root and a db; ``cli`` drives ``cf.library.cli``."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.pack = base / "pack"
        shutil.copytree(template(), self.pack, symlinks=True)
        link = self.pack / "junk/link.mp4"
        link.unlink()
        os.symlink(self.pack / "emoji/в шоке.mp4", link)
        self.footage = base / "footage"
        self.footage.mkdir()
        self.db = base / "factory.db"
        self.config_path = base / "synth.json"
        self.write_config(CONFIG)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_config(self, config: dict, root: Path | None = None) -> None:
        self.config_path.write_text(json.dumps({**config, "root": str(root or self.pack)}, ensure_ascii=False))

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        from cf.library import cli
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*args, "--db", str(self.db), "--footage-root", str(self.footage), "--json"])
        return code, out.getvalue(), err.getvalue()

    def cli(self, *args: str):
        code, out, err = self.run_cli(*args)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def add_and_index(self, *index_args: str) -> dict:
        self.cli("pack", "add", "--config", str(self.config_path))
        return self.cli("index", "synth", *index_args)

    def index(self) -> dict:
        return json.loads((self.footage / "library/synth/index.json").read_text())

    def by_path(self, rel: str) -> dict:
        for a in self.index()["assets"]:
            if any(v["path"] == rel for v in a["variants"]):
                return a
        raise AssertionError(f"no Asset for {rel}")
