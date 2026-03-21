import os
from typing import Any, Protocol

try:
    import httpx
except ImportError:

    class _HttpxFallback:
        @staticmethod
        def post(*_args: object, **_kwargs: object) -> object:
            msg = "httpx is required for provider calls"
            raise RuntimeError(msg)

    httpx = _HttpxFallback()

from arwiz.foundation import LLMConfig


class LLMProvider(Protocol):
    def generate(self, prompt: str, model: str, **kwargs: object) -> str: ...


class OpenAIProvider:
    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com").rstrip("/")

    def generate(self, prompt: str, model: str, **kwargs: object) -> str:
        response: Any = httpx.post(
            url=f"{self.base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                **kwargs,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


class AnthropicProvider:
    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = (base_url or "https://api.anthropic.com").rstrip("/")

    def generate(self, prompt: str, model: str, **kwargs: object) -> str:
        raw_max_tokens = kwargs.pop("max_tokens", 1024)
        max_tokens = raw_max_tokens if isinstance(raw_max_tokens, int) else 1024
        response: Any = httpx.post(
            url=f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                **kwargs,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


class OllamaProvider:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    def generate(self, prompt: str, model: str, **kwargs: object) -> str:
        response: Any = httpx.post(
            url=f"{self.base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, **kwargs},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["response"]


def get_provider(config: LLMConfig) -> LLMProvider:
    provider = config.provider.lower()
    if provider == "openai":
        return OpenAIProvider(
            api_key=os.environ.get(config.api_key_env_var, ""),
            base_url=config.base_url,
        )
    if provider == "anthropic":
        return AnthropicProvider(
            api_key=os.environ.get(config.api_key_env_var, ""),
            base_url=config.base_url,
        )
    if provider == "ollama":
        return OllamaProvider(base_url=config.base_url)
    msg = f"Unsupported LLM provider: {config.provider}"
    raise ValueError(msg)
