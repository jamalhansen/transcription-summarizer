from abc import ABC, abstractmethod


class BaseProvider(ABC):
    def __init__(self, model: str | None = None):
        self._model = model

    @property
    def model(self) -> str:
        return self._model or self.default_model

    @property
    @abstractmethod
    def default_model(self) -> str:
        ...

    @property
    def known_models(self) -> list[str]:
        """Well-known models for this provider. Used in error hints."""
        return []

    @property
    def models_url(self) -> str | None:
        """Link to the provider's model list page, if available."""
        return None

    def _model_hint(self) -> str:
        lines = []
        models = self.known_models
        if models:
            lines.append("  Known models:")
            lines.extend(f"    - {m}" for m in models)
        if self.models_url:
            lines.append(f"  Full list: {self.models_url}")
        return ("\n" + "\n".join(lines)) if lines else ""

    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> str:
        ...
