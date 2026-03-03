import os

from groq import Groq

from .base import BaseProvider


class GroqProvider(BaseProvider):
    """Groq API provider."""

    @property
    def default_model(self) -> str:
        return "llama-3.3-70b-versatile"

    @property
    def known_models(self) -> list[str]:
        return [
            "llama-3.3-70b-versatile  (default)",
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]

    @property
    def models_url(self) -> str:
        return "https://console.groq.com/docs/models"

    def complete(self, system_prompt: str, user_message: str) -> str:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set.")

        client = Groq(api_key=api_key)

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
            raise RuntimeError(f"Groq API error: {e}")

        return response.choices[0].message.content
