"""Model-agnostic LLM layer.

`get_client()` reads environment configuration and returns a client exposing a
single `.complete(system, prompt)` method. Supports Claude (Anthropic) and local
Ollama models, so the project runs with an API key OR fully offline and free.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    # default_factory so the environment is re-read at each instantiation,
    # not once at module import (dotenv/test fixtures may set env late).
    provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "anthropic"))
    model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "claude-sonnet-5"))
    temperature: float = field(
        default_factory=lambda: float(os.environ.get("LLM_TEMPERATURE", "0.1"))
    )
    max_tokens: int = field(default_factory=lambda: int(os.environ.get("LLM_MAX_TOKENS", "2048")))


class BaseLLM:
    def __init__(self, cfg: LLMConfig) -> None:
        self.cfg = cfg

    def complete(self, system: str, prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError


class AnthropicLLM(BaseLLM):
    def complete(self, system: str, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model=self.cfg.model,
            system=system,
            max_tokens=self.cfg.max_tokens,
            temperature=self.cfg.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


class OllamaLLM(BaseLLM):
    def complete(self, system: str, prompt: str) -> str:
        import ollama

        resp = ollama.chat(
            model=self.cfg.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": self.cfg.temperature},
        )
        return resp["message"]["content"]


class EchoLLM(BaseLLM):
    """Deterministic offline stub used in tests and when no provider is set.

    It returns a minimal, valid code block so the pipeline can be exercised end
    to end without network access or an API key.
    """

    def complete(self, system: str, prompt: str) -> str:
        if "Return ONLY Python" in system or "write Python" in prompt.lower():
            return (
                "```python\n"
                "result = df.describe()\n"
                "```"
            )
        return "This is a stub explanation generated without an LLM provider."


_PROVIDERS = {
    "anthropic": AnthropicLLM,
    "ollama": OllamaLLM,
    "echo": EchoLLM,
}


def get_client(cfg: LLMConfig | None = None) -> BaseLLM:
    cfg = cfg or LLMConfig()
    provider = cfg.provider
    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        # Fall back to the offline stub so the app never hard-crashes in a demo.
        provider = "echo"
    return _PROVIDERS.get(provider, EchoLLM)(cfg)
