"""Tests for transcribe.py — local Whisper (mlx-whisper) audio transcription."""

from unittest.mock import MagicMock, patch

import pytest

from voice_journal.core import AudioTranscribeError
from voice_journal.transcribe import AUDIO_EXTENSIONS, transcribe_audio


class TestAudioExtensions:
    def test_expected_extensions_present(self):
        assert AUDIO_EXTENSIONS == {".m4a", ".wav", ".mp3"}


class TestTranscribeAudio:
    def test_returns_text_field(self, tmp_path):
        f = tmp_path / "memo.m4a"
        f.write_bytes(b"fake audio")
        mock_mlx = MagicMock()
        mock_mlx.transcribe.return_value = {"text": "  hello from the memo  "}

        with patch.dict("sys.modules", {"mlx_whisper": mock_mlx}):
            result = transcribe_audio(f, model="mlx-community/whisper-tiny")

        assert result == "hello from the memo"
        mock_mlx.transcribe.assert_called_once_with(
            str(f), path_or_hf_repo="mlx-community/whisper-tiny"
        )

    def test_empty_text_field_returns_empty_string(self, tmp_path):
        f = tmp_path / "memo.m4a"
        f.write_bytes(b"fake audio")
        mock_mlx = MagicMock()
        mock_mlx.transcribe.return_value = {"text": ""}

        with patch.dict("sys.modules", {"mlx_whisper": mock_mlx}):
            result = transcribe_audio(f)

        assert result == ""

    def test_wraps_failure_as_audio_transcribe_error(self, tmp_path):
        f = tmp_path / "memo.m4a"
        f.write_bytes(b"fake audio")
        mock_mlx = MagicMock()
        mock_mlx.transcribe.side_effect = RuntimeError("model load failed")

        with (
            patch.dict("sys.modules", {"mlx_whisper": mock_mlx}),
            pytest.raises(AudioTranscribeError, match="model load failed"),
        ):
            transcribe_audio(f)

    def test_uses_default_model_when_unspecified(self, tmp_path):
        f = tmp_path / "memo.m4a"
        f.write_bytes(b"fake audio")
        mock_mlx = MagicMock()
        mock_mlx.transcribe.return_value = {"text": "ok"}

        with patch.dict("sys.modules", {"mlx_whisper": mock_mlx}):
            transcribe_audio(f)

        _, kwargs = mock_mlx.transcribe.call_args
        assert kwargs["path_or_hf_repo"] == "mlx-community/whisper-large-v3-turbo"
