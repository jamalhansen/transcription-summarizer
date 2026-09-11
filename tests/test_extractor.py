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

    def test_empty_response_returns_empty_string(self):
        provider = MockProvider(response="")
        assert extract(provider, "something") == ""
