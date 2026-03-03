from .anthropic_provider import AnthropicProvider
from .base import BaseProvider
from .deepseek_provider import DeepSeekProvider
from .groq_provider import GroqProvider
from .local import LocalProvider

PROVIDERS = {
    "local": LocalProvider,
    "anthropic": AnthropicProvider,
    "groq": GroqProvider,
    "deepseek": DeepSeekProvider,
}

__all__ = [
    "BaseProvider",
    "LocalProvider",
    "AnthropicProvider",
    "GroqProvider",
    "DeepSeekProvider",
    "PROVIDERS",
]
