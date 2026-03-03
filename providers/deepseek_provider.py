import os

from openai import OpenAI

from .base import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek provider (OpenAI-compatible API)."""

    @property
    def default_model(self) -> str:
        return "deepseek-chat"

    @property
    def known_models(self) -> list[str]:
        return [
            "deepseek-chat      (default)",
            "deepseek-reasoner",
        ]

    @property
    def models_url(self) -> str:
        return "https://api-docs.deepseek.com/quick_start/pricing"

    def complete(self, system_prompt: str, user_message: str) -> str:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY environment variable is not set.")

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
        except Exception as e:
            err = str(e)
            if "model" in err.lower() and ("not found" in err.lower() or "404" in err):
                raise RuntimeError(f"Model '{self.model}' not found.{self._model_hint()}")
            raise RuntimeError(f"DeepSeek API error: {e}")

        return response.choices[0].message.content
