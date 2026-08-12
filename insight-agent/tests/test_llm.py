"""Tests for the LLM configuration layer."""
from __future__ import annotations

from insight_agent.llm import LLMConfig


def test_llm_config_reads_env_at_instantiation_not_import(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1")
    cfg = LLMConfig()
    assert cfg.provider == "ollama"
    assert cfg.model == "llama3.1"


def test_llm_config_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    cfg = LLMConfig()
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-sonnet-5"
    assert cfg.temperature == 0.1
    assert cfg.max_tokens == 2048
