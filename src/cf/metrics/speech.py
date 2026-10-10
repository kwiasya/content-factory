"""Speech in a Clip's own audio, with stable-ts (Whisper + Silero VAD, word timestamps).

Speech is a soft flag: the author talks from behind the camera and music covers it.
Only on-camera speech is a reject; cf.metrics.speech_side decides the side per
segment from the levels measured here and from face landmarks on the proxy.

Reads the RAW source, not the proxy (proxies have no audio): the first audio
stream is decoded to a temp 16 kHz mono WAV and transcribed with Whisper `small`
on the CPU, language hint `ru` (auto detection mislabels short Russian phrases
in street noise as Nynorsk or Faroese). Silero VAD keeps Whisper from
hallucinating text on silent clips ("Субтитры ..."); `base` was too unreliable
on short phrases. MPS fails in Whisper's word alignment (float64), hence CPU.

Per 1 s bin: speech = any word, padded by PAD_S on each side, overlaps the bin.
Also speech_segments [{start, end, text, prob, rms_dbfs, level_dbfs}], the full
transcript text, and the clip's noise floor (`_noise_floor_dbfs`) from the same WAV.

The model is loaded once by `Transcriber` and reused across clips. Weights live
in $CF_MODELS_DIR (default ~/Movies/content-factory/_models): `whisper/` for
Whisper, `torch_hub/` for Silero VAD (pinned tag SILERO_REPO).
"""

from __future__ import annotations

import contextlib
import gc
import io
import json
import os
import subprocess
import tempfile
import time
import warnings
import wave
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from cf.metrics import speech_side
from cf.metrics.common import ffmpeg_bin, ffprobe_bin, n_bins
from cf.metrics.people import models_dir

PAD_S = 0.3
SAMPLE_RATE = 16000
DEFAULT_MODEL = "small"
DEFAULT_LANGUAGE = "ru"
SILERO_REPO = "snakers4/silero-vad:v5.1.2"
SEED = 0
RAW_EXTS = (".mov", ".mp4", ".m4v")


def model_name() -> str:
    return os.environ.get("CF_WHISPER_MODEL", DEFAULT_MODEL)


def language() -> str | None:
    lang = os.environ.get("CF_WHISPER_LANG", DEFAULT_LANGUAGE)
    return None if lang in ("", "auto") else lang


# ----------------------------------------------------------------------------
# Pure helpers (tested without a model)


def speech_bins(words: Iterable[tuple[float, float]], nbins: int, pad: float = PAD_S) -> list[bool]:
    """Per 1 s bin: True if any word [start - pad, end + pad] overlaps the bin.

    The last bin is open-ended (a dropped partial second folds into it, as in
    common.bin_reduce); padding before 0 is clipped.
    """
    out = [False] * nbins
    for start, end in words:
        lo, hi = max(0.0, start - pad), end + pad
        if hi <= lo:
            continue
        first = int(lo)
        for b in range(min(first, nbins - 1), nbins):
            b_lo = float(b)
            b_hi = float(b + 1) if b < nbins - 1 else float("inf")
            if b_lo >= hi:
                break
            if lo < b_hi and hi > b_lo:
                out[b] = True
    return out


def speech_seconds(speech: Sequence[bool]) -> int:
    return int(sum(bool(s) for s in speech))


# ----------------------------------------------------------------------------
# Audio


def find_raw(walk: Path | None, cid: str, header_path: str | None = None) -> Path | None:
    """Raw source of a clip: the manifest path if it exists, else <walk>/raw/<cid>.*"""
    if header_path and Path(header_path).exists():
        return Path(header_path)
    if walk is None or not (walk / "raw").is_dir():
        return None
    # glob returns the on-disk spelling (the volume may be case-insensitive)
    hits = sorted(p for p in (walk / "raw").glob(f"{cid}.*")
                  if not p.name.startswith(".") and p.suffix.lower() in RAW_EXTS)
    return hits[0] if hits else None


def has_audio(path: Path) -> bool:
    out = subprocess.run(
        [ffprobe_bin(), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "json", str(path)],
        capture_output=True, text=True,
    ).stdout
    try:
        return bool(json.loads(out or "{}").get("streams"))
    except json.JSONDecodeError:
        return False


def extract_wav(src: Path, wav: Path) -> None:
    """First audio stream -> 16 kHz mono s16 WAV (iPhone files also carry a 4-ch APAC stream)."""
    subprocess.run(
        [ffmpeg_bin(), "-v", "error", "-nostdin", "-y", "-i", str(src), "-map", "0:a:0", "-vn",
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(wav)],
        check=True, capture_output=True,
    )


def read_wav(wav: Path) -> np.ndarray:
    """16-bit mono WAV -> float samples in -1..1."""
    with wave.open(str(wav)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0


# ----------------------------------------------------------------------------
# Model


@contextlib.contextmanager
def _quiet():
    """Silence download progress bars, hub messages and library warnings."""
    with warnings.catch_warnings(), contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        warnings.simplefilter("ignore")
        yield


class Transcriber:
    """Whisper model loaded once; call `transcribe(wav)` per clip, `close()` at the end."""

    def __init__(self, name: str | None = None, device: str | None = None, lang: str | None = "default"):
        self.name = name or model_name()
        self.device = device or os.environ.get("CF_WHISPER_DEVICE", "cpu")
        self.language = language() if lang == "default" else lang
        self.load_s = 0.0
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        t0 = time.perf_counter()
        with _quiet():
            import torch

            torch.hub.set_dir(str(models_dir() / "torch_hub"))
            import stable_whisper

            root = models_dir() / "whisper"
            root.mkdir(parents=True, exist_ok=True)
            self._model = stable_whisper.load_model(self.name, device=self.device, download_root=str(root))
            # Load (and on first use download) Silero VAD now, so its messages stay quiet too.
            from stable_whisper.stabilization import load_silero_vad_model

            load_silero_vad_model(repo_or_dir=SILERO_REPO)
        self.load_s = time.perf_counter() - t0
        return self._model

    def transcribe(self, wav: Path):
        model = self._load()
        import torch

        # Whisper falls back to sampling at temperature > 0 on hard audio; a fixed seed
        # keeps the Shot log reproducible from run to run.
        torch.manual_seed(SEED)
        with _quiet():
            return model.transcribe(
                str(wav), language=self.language, vad={"repo_or_dir": SILERO_REPO}, word_timestamps=True,
                verbose=None, fp16=False,
            )

    def versions(self) -> dict:
        try:
            with _quiet():
                import stable_whisper
            v = stable_whisper.__version__
        except Exception:  # pragma: no cover
            v = None
        return {"stable-ts": v, "whisper_model": self.name, "silero_vad": SILERO_REPO.split(":")[-1]}

    def close(self) -> None:
        self._model = None
        gc.collect()


# ----------------------------------------------------------------------------
# One clip


def from_result(result, nbins: int, pad: float = PAD_S) -> dict:
    words, segments = [], []
    for seg in result.segments:
        ws = [(float(w.start), float(w.end), float(w.probability)) for w in (seg.words or []) if w.word.strip()]
        if not ws or not seg.text.strip():
            continue
        words += [(s, e) for s, e, _ in ws]
        segments.append({
            "start": round(min(s for s, _, _ in ws), 2),
            "end": round(max(e for _, e, _ in ws), 2),
            "text": seg.text.strip(),
            "prob": round(sum(p for _, _, p in ws) / len(ws), 2),
        })
    return {
        "speech": speech_bins(words, nbins, pad),
        "speech_segments": segments,
        "speech_text": " ".join(s["text"] for s in segments),
        "_language": getattr(result, "language", None),
    }


def analyze(raw: Path | None, duration_s: float, transcriber: Transcriber | None = None) -> dict:
    """Speech per 1 s bin of a clip. `duration_s` is the proxy duration (bins match the other metrics).

    No raw file or no audio stream -> all False and `_audio` False; never raises for those.
    """
    nb = n_bins(duration_s)
    empty = {"speech": [False] * nb, "speech_segments": [], "speech_text": "", "_language": None,
             "_noise_floor_dbfs": None}
    if raw is None or not raw.exists():
        return empty | {"_audio": False, "_error": "raw source not found"}
    if not has_audio(raw):
        return empty | {"_audio": False, "_error": "no audio stream"}
    own = transcriber is None
    tr = transcriber or Transcriber()
    try:
        with tempfile.TemporaryDirectory(prefix="cf-speech-") as tmp:
            wav = Path(tmp) / "audio.wav"
            extract_wav(raw, wav)
            res = tr.transcribe(wav)
            out = from_result(res, nb)
            out["_noise_floor_dbfs"] = speech_side.add_levels(out["speech_segments"], read_wav(wav), SAMPLE_RATE)
    finally:
        if own:
            tr.close()
    return out | {"_audio": True, "_error": None, "_model": tr.name, "_device": tr.device, "_lang_hint": tr.language}


if __name__ == "__main__":
    import sys

    from cf.metrics.common import probe_proxy

    src = Path(sys.argv[1])
    print(json.dumps(analyze(src, probe_proxy(src).duration_s), ensure_ascii=False))
