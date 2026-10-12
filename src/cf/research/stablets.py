"""Thin stable-ts adapter for the deep fetch: transcript with word timestamps, and the Shot log on top of it.

No unit tests (manual smoke). Loading follows ``cf.metrics.speech.Transcriber``
(Whisper ``small`` on the CPU, Silero VAD, seed 0; ``CF_WHISPER_MODEL`` overrides
the model); the language is the Watchlist's (English by default). The Shot log's
own speech pass is fed the same transcript instead of running Whisper twice.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from cf.metrics import speech


def _plain(result) -> dict:
    """``WhisperResult.to_dict`` without the raw Whisper output and token ids."""
    d = result.to_dict(keep_orig=False)
    d.pop("ori_dict", None)
    for seg in d.get("segments") or []:
        seg.pop("tokens", None)
        for w in seg.get("words") or []:
            w.pop("tokens", None)
    return d


def transcribe(media: Path, language: str | None) -> dict:
    """stable-ts result of the media's first audio stream as a plain dict, plus ``_provenance``.

    A file without audio gives an empty transcript (``segments: []``) and ``_error``.
    """
    if not speech.has_audio(media):
        return {"text": "", "segments": [], "language": language, "_error": "no audio stream"}
    tr = speech.Transcriber(device="cpu", lang=language)
    try:
        with tempfile.TemporaryDirectory(prefix="cf-ref-") as tmp:
            wav = Path(tmp) / "audio.wav"
            speech.extract_wav(media, wav)
            out = _plain(tr.transcribe(wav))
        out["_provenance"] = tr.versions() | {"device": tr.device, "language_hint": language,
                                              "load_s": round(tr.load_s, 2)}
    finally:
        tr.close()
    return out


class Reuse(speech.Transcriber):
    """A Transcriber that answers with an existing transcript and never loads a model."""

    def __init__(self, transcript: dict):
        super().__init__(lang=transcript.get("language"))
        self.transcript = transcript
        prov = transcript.get("_provenance") or {}
        self.name = prov.get("whisper_model") or self.name

    def transcribe(self, wav: Path):
        import stable_whisper

        return stable_whisper.WhisperResult({k: v for k, v in self.transcript.items() if not k.startswith("_")})

    def versions(self) -> dict:
        prov = self.transcript.get("_provenance") or {}
        return {k: prov.get(k) for k in ("stable-ts", "whisper_model", "silero_vad")} | {"speech_from": "transcript.json"}


def shotlog(proxy: Path, media: Path, transcript: dict) -> dict:
    """``cf.shotlog.analyze_proxy`` on the proxy, header from the media, speech from ``transcript``."""
    from cf.shotlog import analyze_proxy

    return analyze_proxy(Path(proxy), source=Path(media), transcriber=Reuse(transcript))
