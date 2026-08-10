"""Home Assistant LLM platform for LLM Local Intents."""

from __future__ import annotations

from homeassistant.components import llm
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import LLMContext

from .llm_tools import build_tools


@callback
def async_get_tools(
    hass: HomeAssistant,
    llm_context: LLMContext,
    api_id: str,
) -> llm.LLMTools | None:
    """Return this integration's LLM tools, when any are available."""
    tools = build_tools()
    if not tools:
        return None
    return llm.LLMTools(tools=tools)
