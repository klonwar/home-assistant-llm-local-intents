"""Home Assistant LLM platform for LLM Local Intents."""

from __future__ import annotations

from homeassistant.components import llm
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import LLMContext

from . import get_catalog
from .llm_tools import build_tools
from .prompt import policy_for_language


@callback
def async_get_tools(
    hass: HomeAssistant,
    llm_context: LLMContext,
    api_id: str,
) -> llm.LLMTools | None:
    """Return the current local Assist tools for one LLM request."""
    catalog = get_catalog(hass)
    tools = build_tools(catalog)
    if not tools:
        return None
    return llm.LLMTools(
        tools=tools,
        prompt=policy_for_language(getattr(llm_context, "language", None)),
    )
