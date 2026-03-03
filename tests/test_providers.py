import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from providers.local import LocalProvider
from providers.anthropic_provider import AnthropicProvider
from providers.groq_provider import GroqProvider
from providers.deepseek_provider import DeepSeekProvider


MOCK_RESPONSE = "Reconstructed:\nHello world.\n\n## Thoughts\n\n- Hello world."


class TestLocalProvider:
    def test_default_model(self):
        p = LocalProvider()
        assert p.default_model == "llama3.2:3b"

    def test_model_override(self):
        p = LocalProvider(model="mistral:7b")
        assert p.model == "mistral:7b"

    def test_complete_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": MOCK_RESPONSE}}
        mock_response.raise_for_status = MagicMock()

        with patch("providers.local.requests.post", return_value=mock_response) as mock_post:
            p = LocalProvider()
            result = p.complete("sys", "user")

        assert result == MOCK_RESPONSE
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
        assert payload["model"] == "llama3.2:3b"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"

    def test_complete_connection_error(self):
        import requests as req
        with patch("providers.local.requests.post", side_effect=req.ConnectionError):
            p = LocalProvider()
            with pytest.raises(RuntimeError, match="Could not connect to Ollama"):
                p.complete("sys", "user")


class TestAnthropicProvider:
    def test_default_model(self):
        p = AnthropicProvider()
        assert p.default_model == "claude-haiku-4-5-20251001"

    def test_complete_success(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_content = MagicMock()
        mock_content.text = MOCK_RESPONSE
        mock_message = MagicMock()
        mock_message.content = [mock_content]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        with patch("providers.anthropic_provider.anthropic.Anthropic", return_value=mock_client):
            p = AnthropicProvider()
            result = p.complete("sys", "user")

        assert result == MOCK_RESPONSE

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        p = AnthropicProvider()
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            p.complete("sys", "user")


class TestGroqProvider:
    def test_default_model(self):
        p = GroqProvider()
        assert p.default_model == "llama-3.3-70b-versatile"

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        p = GroqProvider()
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            p.complete("sys", "user")


class TestDeepSeekProvider:
    def test_default_model(self):
        p = DeepSeekProvider()
        assert p.default_model == "deepseek-chat"

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        p = DeepSeekProvider()
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            p.complete("sys", "user")
