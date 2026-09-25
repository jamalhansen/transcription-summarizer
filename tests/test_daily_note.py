import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from local_first_common.obsidian import render_obsidian_template

from voice_journal.core import (
    append_to_note,
    get_note_path,
    memo_link_line,
    memo_note_path,
    memo_title_slug,
    parse_memo_time,
    render_memo_note,
    write_memo_note,
)


class TestGetNotePath:
    def test_default_date(self, tmp_path):
        path = get_note_path(str(tmp_path), "Timeline")
        assert path.name == f"{datetime.now().astimezone().date().isoformat()}.md"
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


class TestParseMemoTime:
    def test_extracts_time_from_recording_stem(self):
        assert parse_memo_time("2026-09-11-20-01-43") == "20:01"

    def test_no_time_in_hand_named_stem(self):
        assert parse_memo_time("2026-03-20-memo") == ""

    def test_no_time_when_date_missing_entirely(self):
        assert parse_memo_time("memo") == ""


class TestMemoNotePath:
    def test_builds_path_under_memo_dir(self, tmp_path):
        path = memo_note_path(str(tmp_path), "Voice Memos", "2026-09-11-20-01-43")
        assert path == tmp_path / "Voice Memos" / "2026-09-11-20-01-43.md"


class TestRenderMemoNote:
    def test_includes_date_time_source_and_entry(self):
        content = render_memo_note(
            date(2026, 9, 11), "20:01", "2026-09-11-20-01-43.m4a", "Finished journal entry."
        )
        assert "date: 2026-09-11" in content
        assert 'time: "20:01"' in content
        assert "type: voice-memo" in content
        assert "source_audio: 2026-09-11-20-01-43.m4a" in content
        assert "Finished journal entry." in content

    def test_omits_time_field_when_absent(self):
        content = render_memo_note(date(2026, 9, 11), "", "memo.txt", "Entry text")
        assert "time:" not in content


class TestWriteMemoNote:
    def test_writes_file_and_creates_parent_dir(self, tmp_path):
        note_path = tmp_path / "Voice Memos" / "2026-09-11-20-01-43.md"
        write_memo_note(note_path, "---\ndate: 2026-09-11\n---\n\nEntry text\n")
        assert note_path.exists()
        assert "Entry text" in note_path.read_text()


class TestMemoLinkLine:
    def test_includes_time_label(self):
        line = memo_link_line("Voice Memos", "2026-09-11-20-01-43", "20:01")
        assert line == "- [[Voice Memos/2026-09-11-20-01-43]] (20:01)"

    def test_omits_label_when_no_time(self):
        line = memo_link_line("Voice Memos", "2026-03-20-memo", "")
        assert line == "- [[Voice Memos/2026-03-20-memo]]"


class TestMemoTitleSlug:
    def test_uses_heading_when_present(self):
        entry = "## Artist Agent Vault\n\nI've been thinking about..."
        assert memo_title_slug(entry) == "artist-agent-vault"

    def test_falls_back_to_first_words_without_heading(self):
        entry = "I was also thinking about the voice memos and maybe it makes sense."
        assert memo_title_slug(entry) == "i-was-also-thinking-about-the"

    def test_empty_entry_returns_empty_string(self):
        assert memo_title_slug("") == ""

    def test_truncates_long_slug(self):
        entry = "## " + " ".join(["word"] * 20)
        assert len(memo_title_slug(entry)) <= 50
