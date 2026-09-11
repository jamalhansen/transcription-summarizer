from datetime import date, datetime
from pathlib import Path

from local_first_common.obsidian import (
    append_to_daily_note,
    get_daily_note_path,
    render_obsidian_template,
)


class TranscriptionError(Exception):
    """Base typed error for transcription-summarizer."""


class ProviderSetupError(TranscriptionError):
    """Raised when provider resolution fails."""


class ExtractionError(TranscriptionError):
    """Raised when the LLM extraction call fails."""


class AudioTranscribeError(TranscriptionError):
    """Raised when Whisper audio transcription fails."""


def get_note_path(
    vault_path: str, note_dir: str, note_date: date | None = None
) -> Path:
    """Return the path for a daily note file."""
    d = note_date or datetime.now().astimezone().date()
    return get_daily_note_path(Path(vault_path), d, subdir=note_dir)


def append_to_note(
    note_path: Path, content: str, template_path: str | None = None
) -> None:
    """Append a Voice Journal section to an existing or new daily note."""
    tpl = Path(template_path).expanduser() if template_path else None
    append_to_daily_note(
        note_path,
        "## Voice Journal\n\n" + content,
        template_path=tpl,
    )


def new_note_base(note_path: Path, template_path: str | None) -> str:
    """Return the base content for a new note (rendered template or fallback frontmatter)."""
    if template_path:
        tpl = Path(template_path).expanduser()
        if tpl.exists():
            try:
                note_date = date.fromisoformat(note_path.stem[:10])
            except ValueError:
                note_date = datetime.now().astimezone().date()
            rendered = render_obsidian_template(
                tpl.read_text(encoding="utf-8"), note_date
            )
            return rendered.rstrip() + "\n\n---\n\n"
    try:
        note_date = date.fromisoformat(note_path.stem[:10])
    except ValueError:
        note_date = datetime.now().astimezone().date()
    return f"---\ndate: {note_date.isoformat()}\n---\n\n"


def file_date(file_path: Path, fallback: date) -> date:
    """Extract date from filename (YYYY-MM-DD prefix) or fall back to provided date."""
    try:
        return date.fromisoformat(file_path.stem[:10])
    except ValueError:
        return fallback
