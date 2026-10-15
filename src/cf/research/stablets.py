"""Thin stable-ts adapter for the deep fetch: transcript with word timestamps, and the Shot log on top of it.

No unit tests (manual smoke). Loading follows ``cf.metrics.speech.Transcriber``
(Whisper ``small`` on the CPU, Silero VAD, seed 0; ``CF_WHISPER_MODEL`` overrides
the model); the language is the video's own, None leaves it to Whisper's detection. The Shot log's
own speech pass is fed the same transcript instead of running Whisper twice.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from cf.metrics import speech
from cf.metrics.common import ffmpeg_bin, ffprobe_bin


def _plain(result) -> dict:
    """``WhisperResult.to_dict`` without the raw Whisper output and token ids."""
    d = result.to_dict(keep_orig=False)
    d.pop("ori_dict", None)
    for seg in d.get("segments") or []:
        seg.pop("tokens", None)
        for w in seg.get("words") or []:
            w.pop("tokens", None)
    return d


def languages() -> frozenset[str]:
    """The language codes Whisper accepts."""
    from whisper.tokenizer import LANGUAGES

    return frozenset(LANGUAGES)


DETECT_WINDOW_S = 30.0
_loaded: speech.Transcriber | None = None


def _transcriber(language: str | None) -> speech.Transcriber:
    """The Transcriber of this process: the one ``detect`` loaded, else a new one."""
    global _loaded
    if _loaded is None:
        _loaded = speech.Transcriber(device="cpu", lang=language)
    _loaded.language = language
    return _loaded


def _release() -> None:
    global _loaded
    if _loaded is not None:
        _loaded.close()
    _loaded = None


def _duration(media: Path) -> float:
    out = subprocess.run([ffprobe_bin(), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(media)],
                         check=True, capture_output=True, text=True).stdout
    return float(json.loads(out).get("format", {}).get("duration") or 0.0)


def _windows(dur: float) -> list[float]:
    if dur <= 2 * DETECT_WINDOW_S:
        return [0.0]
    return [max(0.0, dur * k / 3 - DETECT_WINDOW_S / 2) for k in (1, 2)]


def detect(media: Path) -> dict | None:
    """Whisper's language detection on 30 s windows a third and two thirds into the audio.

    Each window gets Whisper's language probabilities and, from a short ``whisper.decode``,
    its no-speech probability. Returns ``{"windows": [{"start_s", "language", "probability",
    "no_speech_prob"}]}``, None without an audio stream. The loaded model stays for the
    ``transcribe`` that follows.
    """
    if not speech.has_audio(media):
        return None
    tr = _transcriber(None)
    model = tr._load()
    import numpy as np
    import torch
    import whisper

    options = whisper.DecodingOptions(without_timestamps=True, fp16=False, sample_len=8)
    out = []
    for start in _windows(_duration(media)):
        with tempfile.TemporaryDirectory(prefix="cf-ref-") as tmp:
            wav = Path(tmp) / "window.wav"
            subprocess.run([ffmpeg_bin(), "-v", "error", "-nostdin", "-y", "-ss", f"{start:.2f}",
                            "-t", str(DETECT_WINDOW_S), "-i", str(media), "-map", "0:a:0", "-vn", "-ac", "1",
                            "-ar", str(speech.SAMPLE_RATE), "-c:a", "pcm_s16le", str(wav)],
                           check=True, capture_output=True)
            samples = speech.read_wav(wav).astype(np.float32)
        audio = whisper.pad_or_trim(torch.from_numpy(samples))
        mel = whisper.log_mel_spectrogram(audio, model.dims.n_mels).to(model.device)
        with torch.no_grad():
            _, probs = model.detect_language(mel)
            res = whisper.decode(model, mel, options)
        lang = max(probs, key=probs.get)
        out.append({"start_s": round(start, 2), "language": lang, "probability": round(float(probs[lang]), 3),
                    "no_speech_prob": round(float(res.no_speech_prob), 3)})
    return {"windows": out}


def transcribe(media: Path, language: str | None) -> dict:
    """stable-ts result of the media's first audio stream as a plain dict, plus ``_provenance``.

    A file without audio gives an empty transcript (``segments: []``) and ``_error``.
    """
    if not speech.has_audio(media):
        return {"text": "", "segments": [], "language": language, "_error": "no audio stream"}
    tr = _transcriber(language)
    try:
        with tempfile.TemporaryDirectory(prefix="cf-ref-") as tmp:
            wav = Path(tmp) / "audio.wav"
            speech.extract_wav(media, wav)
            out = _plain(tr.transcribe(wav))
        out["_provenance"] = tr.versions() | {"device": tr.device, "language_hint": language,
                                              "load_s": round(tr.load_s, 2)}
    finally:
        _release()
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
