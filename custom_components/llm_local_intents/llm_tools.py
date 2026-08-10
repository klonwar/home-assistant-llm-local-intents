"""LLM tool registry for LLM Local Intents."""

from __future__ import annotations

from homeassistant.components import llm


def build_tools() -> list[llm.Tool]:
    """Return the tools exposed by this integration."""
    return []
