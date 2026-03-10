import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from local_first_common.obsidian import get_daily_note_path, render_obsidian_template
from voice_journal import append_to_note, get_note_path


class TestGetNotePath:
    def test_default_date(self, tmp_path):
        path = get_note_path(str(tmp_path), "Timeline")
        assert path.name == f"{date.today().isoformat()}.md"
        assert path.parent.name == "Timeline"

    def test_custom_date(self, tmp_path):
        d = date(2026, 3, 3)
        path = get_note_path(str(tmp_path), "Timeline", d)
        assert path.name == "2026-03-03.md"


class TestAppendToNote:
    CONTENT = "## Thoughts\n\n- Some thought"

    def test_creates_new_file(self, tmp_path):
        note = tmp_path / "notes" / "2026-03-03.md"
        append_to_note(note, self.CONTENT)
        text = note.read_text()
        assert "date:" in text
        assert "## Voice Journal" in text
        assert "## Thoughts" in text

    def test_appends_to_existing(self, tmp_path):
        note = tmp_path / "2026-03-03.md"
        note.write_text("# Existing Content\n\nSome stuff here.\n")
        append_to_note(note, self.CONTENT)
        text = note.read_text()
        assert "# Existing Content" in text
        assert "---" in text
        assert "## Voice Journal" in text
        assert "## Thoughts" in text

    def test_does_not_overwrite_existing_content(self, tmp_path):
        note = tmp_path / "2026-03-03.md"
        original = "# My Day\n\nOriginal entry.\n"
        note.write_text(original)
        append_to_note(note, self.CONTENT)
        text = note.read_text()
        assert "Original entry." in text

    def test_creates_parent_dirs(self, tmp_path):
        note = tmp_path / "deep" / "nested" / "dir" / "note.md"
        append_to_note(note, self.CONTENT)
        assert note.exists()

    def test_multiple_appends(self, tmp_path):
        note = tmp_path / "2026-03-03.md"
        append_to_note(note, "## Thoughts\n\n- First")
        append_to_note(note, "## Actions\n\n- [ ] Second")
        text = note.read_text()
        assert "First" in text
        assert "Second" in text
        assert text.count("## Voice Journal") == 2

    def test_uses_template_for_new_file(self, tmp_path):
        tpl = tmp_path / "Daily Note.md"
        tpl.write_text("---\nday: \"{{date:YYYY-MM-DD}}\"\n---\n\n## Morning Pages\n\n")
        note = tmp_path / "notes" / "2026-03-03.md"
        append_to_note(note, self.CONTENT, template_path=str(tpl))
        text = note.read_text()
        assert "2026-03-03" in text
        assert "Morning Pages" in text
        assert "## Voice Journal" in text

    def test_template_not_found_falls_back(self, tmp_path):
        note = tmp_path / "notes" / "2026-03-03.md"
        append_to_note(note, self.CONTENT, template_path="/nonexistent/template.md")
        text = note.read_text()
        assert "## Voice Journal" in text


class TestRenderObsidianTemplate:
    NOTE_DATE = date(2026, 3, 3)

    def test_date_format(self):
        result = render_obsidian_template('{{date:YYYY-MM-DD}}', self.NOTE_DATE)
        assert result == "2026-03-03"

    def test_week_format(self):
        result = render_obsidian_template('{{date:YYYY-[W]W}}', self.NOTE_DATE)
        assert result == "2026-W10"

    def test_yesterday(self):
        result = render_obsidian_template('{{yesterday}}', self.NOTE_DATE)
        assert result == "2026-03-02"

    def test_tomorrow(self):
        result = render_obsidian_template('{{ tomorrow }}', self.NOTE_DATE)
        assert result == "2026-03-04"

    def test_full_template(self):
        tpl = 'day: "{{date:YYYY-MM-DD}}"\nPrevious: "[[{{yesterday}}]]"\nNext: "[[{{ tomorrow }}]]"\nWeek: "[[{{date:YYYY-[W]W}}]]"'
        result = render_obsidian_template(tpl, self.NOTE_DATE)
        assert '2026-03-03' in result
        assert '2026-03-02' in result
        assert '2026-03-04' in result
        assert '2026-W10' in result
