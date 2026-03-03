import os

import anthropic

from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider."""

    @property
    def default_model(self) -> str:
        return "claude-haiku-4-5-20251001"

    @property
    def known_models(self) -> list[str]:
        return [
            "claude-haiku-4-5-20251001  (default, fastest)",
            "claude-sonnet-4-5-20251001",
            "claude-opus-4-5-20251001",
        ]

    @property
    def models_url(self) -> str:
        return "https://docs.anthropic.com/en/docs/about-claude/models"

    def complete(self, system_prompt: str, user_message: str) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")

        client = anthropic.Anthropic(api_key=api_key)

        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.AuthenticationError:
            raise RuntimeError("Invalid ANTHROPIC_API_KEY.")
        except anthropic.APIConnectionError:
            raise RuntimeError("Could not connect to Anthropic API.")
        except anthropic.NotFoundError:
            raise RuntimeError(
                f"Model '{self.model}' not found.{self._model_hint()}"
            )
        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API error: {e}")

        return message.content[0].text
