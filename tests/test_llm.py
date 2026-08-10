from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


def _install_homeassistant_stubs() -> None:
    """Provide the small Home Assistant surface used by the skeleton."""
    homeassistant = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    llm = ModuleType("homeassistant.components.llm")
    core = ModuleType("homeassistant.core")
    exceptions = ModuleType("homeassistant.exceptions")
    helpers = ModuleType("homeassistant.helpers")
    helpers_llm = ModuleType("homeassistant.helpers.llm")
    helpers_intent = ModuleType("homeassistant.helpers.intent")
    helpers_reload = ModuleType("homeassistant.helpers.reload")

    class HomeAssistant:
        pass

    class LLMContext:
        pass

    class Tool:
        pass

    class LLMTools:
        def __init__(self, *, tools: list[Tool], prompt: str | None = None) -> None:
            self.tools = tools
            self.prompt = prompt

    class HomeAssistantError(Exception):
        pass

    class ToolInput:
        def __init__(self, tool_args: dict[str, Any], tool_name: str = "tool") -> None:
            self.tool_args = tool_args
            self.tool_name = tool_name
            self.id = "test-call"

    def async_get(hass: Any) -> list[Any]:
        return list(getattr(hass, "data", {}).get("intent", {}).values())

    async def async_handle(hass: Any, platform: str, intent_type: str, slots: dict[str, Any], **kwargs: Any) -> Any:
        handler = getattr(hass, "data", {}).get("intent", {}).get(intent_type)
        if handler is None:
            raise HomeAssistantError(f"Unknown intent {intent_type}")
        return await handler(hass, platform, intent_type, slots, kwargs)

    async def async_integration_yaml_config(
        hass: Any, _domain: str, *, raise_on_failure: bool = False
    ) -> Any:
        return getattr(hass, "data", {}).get("fresh_config")

    def callback(function: Any) -> Any:
        return function

    core.HomeAssistant = HomeAssistant
    core.callback = callback
    core.EVENT_CORE_CONFIG_UPDATE = "core_config_update"
    exceptions.HomeAssistantError = HomeAssistantError
    helpers_llm.LLMContext = LLMContext
    helpers_llm.ToolInput = ToolInput
    llm.LLMTools = LLMTools
    llm.Tool = Tool
    helpers_intent.async_get = async_get
    helpers_intent.async_handle = async_handle
    helpers_reload.async_integration_yaml_config = async_integration_yaml_config
    components.llm = llm
    helpers.llm = helpers_llm
    helpers.intent = helpers_intent
    helpers.reload = helpers_reload
    homeassistant.components = components
    homeassistant.core = core
    homeassistant.exceptions = exceptions
    homeassistant.helpers = helpers
    sys.modules.update(
        {
            "homeassistant": homeassistant,
            "homeassistant.components": components,
            "homeassistant.components.llm": llm,
            "homeassistant.core": core,
            "homeassistant.exceptions": exceptions,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.llm": helpers_llm,
            "homeassistant.helpers.intent": helpers_intent,
            "homeassistant.helpers.reload": helpers_reload,
        }
    )


_install_homeassistant_stubs()

from custom_components.llm_local_intents import async_reload, async_setup  # noqa: E402
from custom_components.llm_local_intents.llm import async_get_tools  # noqa: E402
from custom_components.llm_local_intents.llm_tools import (  # noqa: E402
    LocalAssistTool,
    build_tools,
)
from custom_components.llm_local_intents.catalog import build_catalog  # noqa: E402
from custom_components.llm_local_intents.prompt import policy_for_language  # noqa: E402
from custom_components.llm_local_intents.intent_adapter import (  # noqa: E402
    HomeAssistantError,
    async_handle_local_intent,
)


def test_build_tools_starts_empty() -> None:
    assert build_tools() == []


def test_async_get_tools_returns_none_without_tools() -> None:
    assert async_get_tools(SimpleNamespace(), SimpleNamespace(), "api") is None


def test_async_setup_succeeds_without_configuration() -> None:
    assert asyncio.run(async_setup(SimpleNamespace(), {})) is True


def test_catalog_builds_and_sorts_tools() -> None:
    catalog = build_catalog(
        {
            "intents": {
                "LowPriority": {
                    "description": "Low",
                    "examples": ["low"],
                    "priority": 1,
                    "slots": {},
                },
                "HighPriority": {
                    "description": "High",
                    "examples": ["high"],
                    "priority": 100,
                    "slots": {},
                },
            }
        }
    )
    assert [item.intent_name for item in catalog.descriptors] == [
        "HighPriority",
        "LowPriority",
    ]
    assert [tool.name for tool in build_tools(catalog)] == [
        "local_assist_high_priority",
        "local_assist_low_priority",
    ]


def test_catalog_skips_invalid_and_hidden_entries() -> None:
    catalog = build_catalog(
        {
            "intents": {
                "Hidden": {
                    "expose": False,
                    "description": "hidden",
                    "examples": ["hidden"],
                },
                "MissingDescription": {"examples": ["bad"]},
                "Valid": {"description": "valid", "examples": ["ok"]},
            }
        }
    )
    assert catalog.declared_count == 3
    assert catalog.skipped_count == 2
    assert [item.intent_name for item in catalog.descriptors] == ["Valid"]


def test_catalog_validates_parameterized_slots_and_internal_enum_values() -> None:
    catalog = build_catalog(
        {
            "intents": {
                "SetMode": {
                    "description": "Set mode",
                    "examples": ["set mode"],
                    "slots": {
                        "mode": {"type": "string", "enum": {"quiet": "silent"}},
                        "level": {"type": "integer", "minimum": 0, "maximum": 10},
                    },
                }
            }
        }
    )
    descriptor = catalog.descriptors[0]
    assert descriptor.validate_args({"mode": "quiet", "level": 4}) == {
        "mode": "silent",
        "level": 4,
    }
    with pytest.raises(ValueError):
        descriptor.validate_args({"mode": "loud", "level": 4})


def test_catalog_skips_unknown_handlers() -> None:
    catalog = build_catalog(
        {
            "intents": {
                "Known": {"description": "known", "examples": ["known"]},
                "Unknown": {"description": "unknown", "examples": ["unknown"]},
            }
        },
        available_handlers={"Known"},
    )
    assert [item.intent_name for item in catalog.descriptors] == ["Known"]
    assert catalog.skipped_count == 1


def test_generic_prompt_is_language_aware_and_project_independent() -> None:
    assert "Hallway" not in policy_for_language("en")
    assert "Коридор" not in policy_for_language("ru")
    assert "local" in policy_for_language("en").lower()
    assert "локаль" in policy_for_language("ru").lower()
    assert policy_for_language("de") == policy_for_language("en")


def test_local_tool_calls_bound_intent_without_native_fallback() -> None:
    catalog = build_catalog(
        {
            "intents": {
                "ExampleIntent": {
                    "description": "Example",
                    "examples": ["do example"],
                    "slots": {"level": {"type": "integer", "minimum": 1}},
                }
            }
        }
    )
    calls: list[tuple[str, dict[str, Any]]] = []

    async def executor(
        _hass: Any,
        intent_name: str,
        slots: dict[str, Any],
        _context: Any,
    ) -> dict[str, Any]:
        calls.append((intent_name, slots))
        return {"success": True, "intent": intent_name, "speech": ""}

    tool = LocalAssistTool(catalog.descriptors[0], executor=executor)
    result = asyncio.run(
        tool.async_call(
            SimpleNamespace(),
            SimpleNamespace(tool_args={"level": 2}, id="call-1"),
            SimpleNamespace(language="en"),
        )
    )
    assert result["success"] is True
    assert calls == [("ExampleIntent", {"level": 2})]


def test_async_get_tools_includes_prompt_after_setup() -> None:
    hass = SimpleNamespace(
        data={
            "intent": {
                "ExampleIntent": SimpleNamespace(intent_type="ExampleIntent")
            }
        },
        bus=SimpleNamespace(),
    )
    config = {
        "llm_local_intents": {
            "intents": {
                "ExampleIntent": {
                    "description": "Example",
                    "examples": ["do example"],
                }
            }
        }
    }
    assert asyncio.run(async_setup(hass, config)) is True
    result = async_get_tools(hass, SimpleNamespace(language="en"), "api")
    assert result is not None
    assert len(result.tools) == 1
    assert "local tool" in result.prompt.lower()


def test_reload_keeps_previous_snapshot_when_new_config_is_invalid() -> None:
    hass = SimpleNamespace(
        data={
            "intent": {
                "ExampleIntent": SimpleNamespace(intent_type="ExampleIntent")
            }
        },
        bus=SimpleNamespace(),
    )
    valid = {
        "llm_local_intents": {
            "intents": {
                "ExampleIntent": {
                    "description": "Example",
                    "examples": ["do example"],
                }
            }
        }
    }
    assert asyncio.run(async_setup(hass, valid)) is True
    previous = hass.data["llm_local_intents"]["catalog"]
    assert asyncio.run(
        async_reload(hass, {"llm_local_intents": {"intents": []}})
    ) is False
    assert hass.data["llm_local_intents"]["catalog"] is previous


def test_config_update_listener_reads_fresh_yaml_config() -> None:
    class Bus:
        callback: Any

        def async_listen(self, _event: str, callback: Any) -> Any:
            self.callback = callback
            return lambda: None

    bus = Bus()
    hass = SimpleNamespace(
        data={
            "intent": {
                "FirstIntent": SimpleNamespace(intent_type="FirstIntent"),
                "SecondIntent": SimpleNamespace(intent_type="SecondIntent"),
            }
        },
        bus=bus,
    )
    first = {
        "llm_local_intents": {
            "intents": {
                "FirstIntent": {"description": "first", "examples": ["first"]}
            }
        }
    }
    second = {
        "llm_local_intents": {
            "intents": {
                "SecondIntent": {"description": "second", "examples": ["second"]}
            }
        }
    }
    assert asyncio.run(async_setup(hass, first)) is True
    hass.data["fresh_config"] = second
    asyncio.run(bus.callback(None))
    assert [
        item.intent_name
        for item in hass.data["llm_local_intents"]["catalog"].descriptors
    ] == ["SecondIntent"]


def test_direct_intent_adapter_wraps_slots_and_extracts_speech() -> None:
    captured: dict[str, Any] = {}

    async def handler(
        _hass: Any,
        platform: str,
        intent_name: str,
        slots: dict[str, Any],
        _kwargs: Any,
    ) -> Any:
        captured.update(platform=platform, intent_name=intent_name, slots=slots)
        return SimpleNamespace(speech={"plain": {"speech": "done"}})

    hass = SimpleNamespace(
        data={"intent": {"ExampleIntent": handler}},
    )
    result = asyncio.run(
        async_handle_local_intent(
            hass,
            "ExampleIntent",
            {"level": 3},
            SimpleNamespace(language="en", platform="conversation"),
        )
    )
    assert result == {"success": True, "intent": "ExampleIntent", "speech": "done"}
    assert captured["platform"] == "conversation"
    assert captured["intent_name"] == "ExampleIntent"
    assert captured["slots"] == {"level": {"value": 3}}


def test_tool_error_does_not_fallback_to_another_tool() -> None:
    descriptor = build_catalog(
        {
            "intents": {
                "FailingIntent": {
                    "description": "Fail",
                    "examples": ["fail"],
                }
            }
        }
    ).descriptors[0]

    async def failing_executor(*_args: Any) -> dict[str, Any]:
        raise HomeAssistantError("handler failed")

    tool = LocalAssistTool(descriptor, executor=failing_executor)
    with pytest.raises(HomeAssistantError):
        asyncio.run(
            tool.async_call(
                SimpleNamespace(),
                SimpleNamespace(tool_args={}, id="call-fail"),
                SimpleNamespace(language="en"),
            )
        )


def test_tool_rejects_non_serializable_result() -> None:
    descriptor = build_catalog(
        {
            "intents": {
                "BadResultIntent": {
                    "description": "Bad result",
                    "examples": ["bad result"],
                }
            }
        }
    ).descriptors[0]

    async def bad_executor(*_args: Any) -> dict[str, Any]:
        return {"not_json": object()}

    tool = LocalAssistTool(descriptor, executor=bad_executor)
    with pytest.raises(HomeAssistantError):
        asyncio.run(
            tool.async_call(
                SimpleNamespace(),
                SimpleNamespace(tool_args={}, id="call-bad"),
                SimpleNamespace(language="en"),
            )
        )
