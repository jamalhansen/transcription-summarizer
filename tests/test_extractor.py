import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from local_first_common.testing import MockProvider

from voice_journal.extractor import SYSTEM_PROMPT, extract


class TestExtract:
    def test_returns_stripped_provider_response(self):
        provider = MockProvider(response="  \nI went to the park with Jon Jon.\n\n")
        result = extract(provider, "went to the park with jon jon")
        assert result == "I went to the park with Jon Jon."

    def test_passes_transcript_as_user_message(self):
        provider = MockProvider(response="entry")
        extract(provider, "the raw transcript text")
        system, user = provider.calls[0]
        assert system == SYSTEM_PROMPT
        assert user == "the raw transcript text"

    def test_empty_response_falls_back_to_transcript(self):
        # An empty LLM response for real input is itself a sign something went
        # wrong with the rewrite -- fall back to the transcript rather than
        # silently producing an empty journal entry.
        provider = MockProvider(response="")
        assert extract(provider, "a real transcript with actual content") == ("a real transcript with actual content")


class TestThinInputGuard:
    """Below MIN_WORDS_FOR_LLM_EDIT, skip the LLM entirely and pass the
    transcript through verbatim -- guards against a demonstrated failure where
    a small local model fabricated an entire elaborate journal entry from a
    3-word placeholder transcript instead of saying there was nothing to work
    with."""

    def test_thin_transcript_bypasses_the_llm(self):
        provider = MockProvider(response="a fabricated multi-paragraph story")
        result = extract(provider, "test transcript one")
        assert result == "test transcript one"
        assert provider.calls == []

    def test_transcript_at_threshold_still_goes_to_the_llm(self):
        provider = MockProvider(response="entry")
        result = extract(provider, "the raw transcript text")
        assert result == "entry"
        assert len(provider.calls) == 1


class TestExpansionRatioGuard:
    """Above the word-count floor, a short transcript turned into a much
    longer response is the same failure mode at a smaller scale -- fall back
    to the transcript rather than trust a wildly disproportionate rewrite."""

    def test_wildly_expanded_response_falls_back_to_transcript(self):
        transcript = "thinking about the artist agent project today"
        fabricated = "A" * (len(transcript) * 5)
        provider = MockProvider(response=fabricated)
        assert extract(provider, transcript) == transcript

    def test_modest_expansion_is_not_flagged(self):
        transcript = "thinking about the artist agent project today"
        reasonable = "## Artist Agent\n\n" + transcript.capitalize() + "."
        provider = MockProvider(response=reasonable)
        assert extract(provider, transcript) == reasonable

    def test_expansion_guard_does_not_apply_to_long_transcripts(self):
        transcript = "word " * 60  # well over SHORT_TRANSCRIPT_CHARS
        fabricated = "A" * (len(transcript) * 5)
        provider = MockProvider(response=fabricated)
        assert extract(provider, transcript) == fabricated
