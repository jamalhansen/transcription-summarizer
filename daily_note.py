import re
from datetime import date, timedelta
from pathlib import Path


def get_note_path(vault_path: str, note_dir: str, note_date: date | None = None) -> Path:
    d = note_date or date.today()
    return Path(vault_path).expanduser() / note_dir / f"{d.isoformat()}.md"


def render_obsidian_template(template: str, note_date: date) -> str:
    """Replace Obsidian template variables with values for the given date."""
    yesterday = note_date - timedelta(days=1)
    tomorrow = note_date + timedelta(days=1)

    def replace_date_format(m: re.Match) -> str:
        fmt = m.group(1).strip()
        # Map Obsidian format tokens to Python strftime
        fmt = fmt.replace("YYYY", "%G")
        fmt = fmt.replace("MM", "%m")
        fmt = fmt.replace("DD", "%d")
        fmt = re.sub(r"\[W\]W", "W%V", fmt)  # [W]W → W<ISO week>
        return note_date.strftime(fmt)

    result = re.sub(r"\{\{date:([^}]+)\}\}", replace_date_format, template)
    result = re.sub(r"\{\{\s*yesterday\s*\}\}", yesterday.isoformat(), result)
    result = re.sub(r"\{\{\s*tomorrow\s*\}\}", tomorrow.isoformat(), result)
    return result


def append_to_note(note_path: Path, content: str, template_path: str | None = None) -> None:
    """Append a Voice Journal section to an existing or new daily note."""
    note_path.parent.mkdir(parents=True, exist_ok=True)

    if note_path.exists():
        existing = note_path.read_text(encoding="utf-8")
        separator = "\n\n---\n\n" if existing.strip() else ""
        note_path.write_text(
            existing.rstrip() + separator + "## Voice Journal\n\n" + content + "\n",
            encoding="utf-8",
        )
    else:
        base = new_note_base(note_path, template_path)
        note_path.write_text(base + "## Voice Journal\n\n" + content + "\n", encoding="utf-8")


def new_note_base(note_path: Path, template_path: str | None) -> str:
    """Return the base content for a new note (rendered template or fallback frontmatter)."""
    if template_path:
        tpl = Path(template_path).expanduser()
        if tpl.exists():
            # Derive the note date from the filename (YYYY-MM-DD)
            try:
                note_date = date.fromisoformat(note_path.stem[:10])
            except ValueError:
                note_date = date.today()
            rendered = render_obsidian_template(tpl.read_text(encoding="utf-8"), note_date)
            return rendered.rstrip() + "\n\n---\n\n"

    # Fallback if no template or template not found
    return f"---\ndate: {date.today().isoformat()}\n---\n\n"
