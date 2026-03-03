import json
import os

import requests

from .base import BaseProvider


class LocalProvider(BaseProvider):
    """Ollama local provider."""

    @property
    def default_model(self) -> str:
        return "llama3.2:3b"

    @property
    def known_models(self) -> list[str]:
        """Return models currently installed in Ollama, falling back to a static list."""
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        try:
            resp = requests.get(f"{host}/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            if models:
                return [f"{m}  ← default" if m == self.default_model else m for m in models]
        except Exception:
            pass
        return [
            "llama3.2:3b   (default)",
            "llama3.1:8b",
            "llama3.1:70b",
            "mistral:7b",
            "gemma2:9b",
        ]

    def complete(self, system_prompt: str, user_message: str) -> str:
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        url = f"{host}/api/chat"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
        except requests.ConnectionError:
            raise RuntimeError(
                f"Could not connect to Ollama at {host}. Is it running?"
            )
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise RuntimeError(
                    f"Model '{self.model}' not found in Ollama.{self._model_hint()}\n"
                    f"  Run `ollama pull {self.model}` to download it."
                )
            raise RuntimeError(f"Ollama request failed: {e}")

        data = response.json()
        return data["message"]["content"]
