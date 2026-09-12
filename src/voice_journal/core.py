import re
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


_STEM_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-(\d{2})-(\d{2})-(\d{2})")


def parse_memo_time(stem: str) -> str:
    """Extract "HH:MM" from a recording filename stem like "2026-09-11-20-01-43".

    Returns "" if the stem doesn't carry a time component (e.g. a hand-named
    text file), since a memo note's frontmatter should never claim a time it
    doesn't actually have.
    """
    m = _STEM_TIME_RE.match(stem)
    return f"{m.group(1)}:{m.group(2)}" if m else ""


def memo_note_path(vault_path: str, memo_dir: str, stem: str) -> Path:
    """Return the path for an individual voice-memo note, named after its source file."""
    return Path(vault_path).expanduser() / memo_dir / f"{stem}.md"


_SLUG_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def memo_title_slug(entry: str, max_words: int = 6, max_chars: int = 50) -> str:
    """Derive a short filename slug from the entry's own content.

    Uses the entry's "## " heading when present -- the extraction prompt only adds
    one when an entry genuinely covers more than one topic, which makes it a
    reasonable label the rest of the time too -- and falls back to the first few
    words of the entry otherwise. Returns "" for an empty entry rather than guess.
    """
    entry = entry.strip()
    if not entry:
        return ""

    first_line = entry.splitlines()[0]
    heading_match = re.match(r"^#{1,6}\s+(.+)$", first_line)
    source = heading_match.group(1) if heading_match else " ".join(entry.split()[:max_words])

    slug = _SLUG_NON_ALNUM_RE.sub("-", source.lower()).strip("-")
    return slug[:max_chars].rstrip("-")


def render_memo_note(memo_date: date, memo_time: str, source_name: str, entry: str) -> str:
    """Render a single voice memo as its own note: frontmatter, then the finished entry.

    One memo, one note -- each recording stays composable and linkable on its own
    instead of having its content folded directly into the daily note.
    """
    lines = ["---", f"date: {memo_date.isoformat()}"]
    if memo_time:
        lines.append(f'time: "{memo_time}"')
    lines += ["type: voice-memo", f"source_audio: {source_name}", "---", "", entry.strip(), ""]
    return "\n".join(lines)


def write_memo_note(note_path: Path, content: str) -> None:
    """Write a rendered memo note to disk, creating its folder if needed."""
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(content, encoding="utf-8")


def memo_link_line(memo_dir: str, stem: str, memo_time: str) -> str:
    """Return the daily-note bullet line linking to a memo note."""
    label = f" ({memo_time})" if memo_time else ""
    return f"- [[{memo_dir}/{stem}]]{label}"
