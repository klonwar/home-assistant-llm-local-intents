from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace
from typing import Any


def _install_homeassistant_stubs() -> None:
    """Provide the small Home Assistant surface used by the skeleton."""
    homeassistant = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    llm = ModuleType("homeassistant.components.llm")
    core = ModuleType("homeassistant.core")
    helpers = ModuleType("homeassistant.helpers")
    helpers_llm = ModuleType("homeassistant.helpers.llm")

    class HomeAssistant:
        pass

    class LLMContext:
        pass

    class Tool:
        pass

    class LLMTools:
        def __init__(self, *, tools: list[Tool]) -> None:
            self.tools = tools

    def callback(function: Any) -> Any:
        return function

    core.HomeAssistant = HomeAssistant
    core.callback = callback
    helpers_llm.LLMContext = LLMContext
    llm.LLMTools = LLMTools
    llm.Tool = Tool
    components.llm = llm
    helpers.llm = helpers_llm
    homeassistant.components = components
    homeassistant.core = core
    homeassistant.helpers = helpers
    sys.modules.update(
        {
            "homeassistant": homeassistant,
            "homeassistant.components": components,
            "homeassistant.components.llm": llm,
            "homeassistant.core": core,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.llm": helpers_llm,
        }
    )


_install_homeassistant_stubs()

from custom_components.llm_local_intents import async_setup  # noqa: E402
from custom_components.llm_local_intents.llm import async_get_tools  # noqa: E402
from custom_components.llm_local_intents.llm_tools import build_tools  # noqa: E402


def test_build_tools_starts_empty() -> None:
    assert build_tools() == []


def test_async_get_tools_returns_none_without_tools() -> None:
    assert async_get_tools(SimpleNamespace(), SimpleNamespace(), "api") is None


def test_async_setup_succeeds_without_configuration() -> None:
    assert asyncio.run(async_setup(SimpleNamespace(), {})) is True
