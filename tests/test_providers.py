import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from local_first_common.providers.ollama import OllamaProvider
from local_first_common.providers.anthropic import AnthropicProvider
from local_first_common.providers.groq import GroqProvider
from local_first_common.providers.deepseek import DeepSeekProvider


MOCK_RESPONSE = "Reconstructed:\nHello world.\n\n## Thoughts\n\n- Hello world."


class TestOllamaProvider:
    def test_default_model(self):
        p = OllamaProvider()
        assert p.default_model == "phi4-mini"

    def test_model_override(self):
        p = OllamaProvider(model="mistral:7b")
        assert p.model == "mistral:7b"

    def test_complete_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": MOCK_RESPONSE}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch("local_first_common.providers.ollama.httpx.Client", return_value=mock_client):
            p = OllamaProvider()
            result = p.complete("sys", "user")

        assert result == MOCK_RESPONSE
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
        assert payload["model"] == "phi4-mini"
        assert "sys" in payload["prompt"]
        assert "user" in payload["prompt"]

    def test_complete_connection_error(self):
        import httpx
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.RequestError("connection refused", request=MagicMock())

        with patch("local_first_common.providers.ollama.httpx.Client", return_value=mock_client):
            p = OllamaProvider()
            with pytest.raises(RuntimeError, match="Ollama"):
                p.complete("sys", "user")


class TestAnthropicProvider:
    def test_default_model(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
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

        with patch("local_first_common.providers.anthropic._Anthropic", return_value=mock_client):
            p = AnthropicProvider()
            result = p.complete("sys", "user")

        assert result == MOCK_RESPONSE

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider()


class TestGroqProvider:
    def test_default_model(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        p = GroqProvider()
        assert p.default_model == "llama-3.3-70b-versatile"

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            GroqProvider()


class TestDeepSeekProvider:
    def test_default_model(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        p = DeepSeekProvider()
        assert p.default_model == "deepseek-chat"

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            DeepSeekProvider()
