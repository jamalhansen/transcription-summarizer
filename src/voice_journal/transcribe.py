"""Local Whisper transcription for voice memo audio, via mlx-whisper.

Runs fully on-device (Apple Silicon, MLX) -- no audio ever leaves the machine.
Replaces the previous design of relying on Apple's on-device dictation to produce
a text transcript upstream, which had no context for names, jargon, or tools and
routinely mangled them.
"""
from pathlib import Path

from .core import AudioTranscribeError

AUDIO_EXTENSIONS = {".m4a", ".wav", ".mp3"}

DEFAULT_WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"


def transcribe_audio(path: Path, model: str = DEFAULT_WHISPER_MODEL) -> str:
    """Transcribe an audio file to text using local Whisper (mlx-whisper).

    The first call for a given model downloads it from Hugging Face (a few GB) and
    caches it under ~/.cache/huggingface; every call after that runs fully offline.
    """
    import mlx_whisper

    try:
        result = mlx_whisper.transcribe(str(path), path_or_hf_repo=model)
    except Exception as e:
        raise AudioTranscribeError(f"Whisper transcription failed for {path.name}: {e}") from e

    return (result.get("text") or "").strip()
