"""Tests for logic.py — CLI entry point and file processing orchestration."""

from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import typer
from voice_journal import logic
from voice_journal.extractor import ExtractionResult
from voice_journal.logic import TranscriptionError, ProviderSetupError, ExtractionError


class TestTypedErrors:
    def test_error_hierarchy(self):
        assert issubclass(ProviderSetupError, TranscriptionError)
        assert issubclass(ExtractionError, TranscriptionError)

    def test_provider_setup_error_message(self):
        err = ProviderSetupError("bad provider")
        assert "bad provider" in str(err)

    def test_extraction_error_message(self):
        err = ExtractionError("parse failed")
        assert "parse failed" in str(err)


def test_get_note_path():
    """Returns correct daily note path."""
    with patch(
        "voice_journal.logic.get_daily_note_path", return_value=Path("/v/2026-03-20.md")
    ) as mock_get:
        p = logic.get_note_path("/v", "d", date(2026, 3, 20))
        assert p == Path("/v/2026-03-20.md")
        mock_get.assert_called_once_with(Path("/v"), date(2026, 3, 20), subdir="d")


def test_append_to_note():
    """Appends to daily note with header."""
    with patch("voice_journal.logic.append_to_daily_note") as mock_append:
        logic.append_to_note(Path("/p"), "content", "/tpl")
        mock_append.assert_called_once()
        args = mock_append.call_args[0]
        assert args[0] == Path("/p")
        assert "## Voice Journal" in args[1]
        assert "content" in args[1]


def test_new_note_base_no_template():
    """Fallback frontmatter if no template provided."""
    res = logic.new_note_base(Path("2026-03-20.md"), None)
    assert "date: 2026-03-20" in res


def test_collect_files_single_file(tmp_path):
    """Returns single file if --file provided."""
    f = tmp_path / "test.txt"
    f.write_text("content")
    res = logic.collect_files(str(f), None)
    assert res == [f]


def test_collect_files_directory(tmp_path):
    """Returns sorted text files from directory."""
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "other.jpg").write_text("not text")

    with patch("voice_journal.logic.resolve_input_dir", return_value=tmp_path):
        res = logic.collect_files(None, str(tmp_path))
        assert [f.name for f in res] == ["a.txt", "b.txt"]


def test_file_date_from_name():
    """Extracts date from YYYY-MM-DD prefix."""
    assert logic.file_date(Path("2026-03-21-memo.txt"), date.today()) == date(
        2026, 3, 21
    )


def test_file_date_fallback():
    """Returns fallback if no date in filename."""
    d = date(2026, 1, 1)
    assert logic.file_date(Path("memo.txt"), d) == d


def test_process_file_empty(tmp_path):
    """Skips empty files."""
    f = tmp_path / "empty.txt"
    f.write_text("  ")
    res = logic.process_file(f, MagicMock(), False)
    assert res is None


@patch("voice_journal.logic.extract")
def test_process_file_success(mock_extract, tmp_path):
    """Calls extract and returns result."""
    f = tmp_path / "memo.txt"
    f.write_text("raw text")
    mock_extract.return_value = ExtractionResult(reconstructed="fixed")

    res = logic.process_file(f, MagicMock(), False)
    assert res.reconstructed == "fixed"
    mock_extract.assert_called_once()


@patch("voice_journal.logic.resolve_vault_path")
@patch("voice_journal.logic.collect_files")
@patch("voice_journal.logic.process_file")
def test_main_dry_run(mock_proc, mock_collect, mock_vault, tmp_path):
    """Dry run orchestration."""
    mock_vault.return_value = tmp_path
    f = tmp_path / "2026-03-20-memo.txt"
    mock_collect.return_value = [f]
    mock_proc.return_value = ExtractionResult(reconstructed="r", thoughts=["t"])

    with patch("voice_journal.logic.PROVIDERS", {"local": MagicMock()}):
        logic.main(provider="local", dry_run=True, vault_path=str(tmp_path))

    mock_collect.assert_called_once()
    mock_proc.assert_called_once()


def test_collect_files_not_found():
    """Typer.Exit on missing file."""
    with pytest.raises(typer.Exit):
        logic.collect_files("missing.txt", None)


def test_main_invalid_provider():
    """Typer.Exit on unknown provider."""
    with patch("voice_journal.logic.PROVIDERS", {}):
        with pytest.raises(typer.Exit):
            logic.main(provider="unknown")


def test_main_invalid_date():
    """Typer.Exit on bad date format."""
    with pytest.raises(typer.Exit):
        logic.main(override_date="bad-date")


@patch("voice_journal.logic.resolve_vault_path")
@patch("voice_journal.logic.collect_files")
@patch("voice_journal.logic.process_file")
@patch("voice_journal.logic.append_to_note")
def test_main_write_loop(mock_append, mock_proc, mock_collect, mock_vault, tmp_path):
    """Writing loop orchestration."""
    mock_vault.return_value = tmp_path
    f = tmp_path / "2026-03-20-memo.txt"
    mock_collect.return_value = [f]
    mock_proc.return_value = ExtractionResult(reconstructed="r", thoughts=["t"])

    with (
        patch("voice_journal.logic.PROVIDERS", {"local": MagicMock()}),
        patch.object(Path, "rename") as mock_rename,
    ):
        logic.main(
            provider="local", dry_run=False, no_llm=False, vault_path=str(tmp_path)
        )

    mock_append.assert_called_once()
    mock_rename.assert_called_once()
