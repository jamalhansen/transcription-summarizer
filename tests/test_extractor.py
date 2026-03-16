import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from extractor import ExtractionResult, _parse_response


FULL_RESPONSE = """\
Reconstructed:
I am really grateful for Robyn and Jon Jon today. We went to the park
and I was thinking about how I need to write more about DuckDB for the blog.
Also need to call the pediatrician tomorrow.

## Thoughts

- Went to the park with Robyn and Jon Jon. Thinking about writing more DuckDB content for the blog.

## Actions

- [ ] Call the pediatrician tomorrow

## Gratitude

- Grateful for Robyn and Jon Jon
"""

THOUGHTS_ONLY_RESPONSE = """\
Reconstructed:
I was thinking about the nature of time and memory.

## Thoughts

- The nature of time and memory is fascinating.
"""

ACTIONS_ONLY_RESPONSE = """\
Reconstructed:
I need to buy groceries and email Sarah.

## Actions

- [ ] Buy groceries
- [ ] Email Sarah
"""

NO_SECTIONS_RESPONSE = """\
Reconstructed:
It was a quiet day with nothing particular to note.
"""


class TestParseResponse:
    def test_full_response_reconstructed(self):
        result = _parse_response(FULL_RESPONSE)
        assert "Robyn" in result.reconstructed
        assert "Jon Jon" in result.reconstructed
        assert "DuckDB" in result.reconstructed

    def test_full_response_thoughts(self):
        result = _parse_response(FULL_RESPONSE)
        assert len(result.thoughts) == 1
        assert "DuckDB" in result.thoughts[0]

    def test_full_response_actions(self):
        result = _parse_response(FULL_RESPONSE)
        assert len(result.actions) == 1
        assert "pediatrician" in result.actions[0]

    def test_full_response_gratitude(self):
        result = _parse_response(FULL_RESPONSE)
        assert len(result.gratitude) == 1
        assert "Robyn" in result.gratitude[0]

    def test_thoughts_only(self):
        result = _parse_response(THOUGHTS_ONLY_RESPONSE)
        assert len(result.thoughts) == 1
        assert result.actions == []
        assert result.gratitude == []

    def test_actions_only(self):
        result = _parse_response(ACTIONS_ONLY_RESPONSE)
        assert len(result.actions) == 2
        assert result.thoughts == []
        assert result.gratitude == []

    def test_no_sections(self):
        result = _parse_response(NO_SECTIONS_RESPONSE)
        assert result.reconstructed != ""
        assert result.thoughts == []
        assert result.actions == []
        assert result.gratitude == []


class TestExtractionResultToMarkdown:
    def test_all_sections(self):
        result = ExtractionResult(
            reconstructed="x",
            thoughts=["Idea A"],
            actions=["Do thing B"],
            gratitude=["Family"],
        )
        md = result.to_markdown()
        assert "## Thoughts" in md
        assert "- Idea A" in md
        assert "## Actions" in md
        assert "- [ ] Do thing B" in md
        assert "## Gratitude" in md
        assert "- Family" in md

    def test_omits_empty_sections(self):
        result = ExtractionResult(reconstructed="x", thoughts=["Idea A"])
        md = result.to_markdown()
        assert "## Thoughts" in md
        assert "## Actions" not in md
        assert "## Gratitude" not in md

    def test_empty_result(self):
        result = ExtractionResult(reconstructed="")
        assert result.to_markdown() == ""
