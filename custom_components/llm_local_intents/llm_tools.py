"""Dynamic LLM tools for validated local Assist intents."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
import json
import logging
from typing import Any

from homeassistant.components import llm

from .catalog import IntentCatalog, IntentDescriptor
from .intent_adapter import HomeAssistantError, async_handle_local_intent
from .schema import build_parameters_schema


_LOGGER = logging.getLogger(__name__)


Executor = Callable[[Any, str, Mapping[str, Any], Any], Awaitable[dict[str, Any]]]


class LocalAssistTool(llm.Tool):
    """One LLM tool bound to one exact Assist intent."""

    def __init__(
        self,
        descriptor: IntentDescriptor,
        *,
        executor: Executor = async_handle_local_intent,
    ) -> None:
        self.descriptor = descriptor
        self.name = descriptor.tool_name
        self.description = _build_description(descriptor)
        self.parameters = build_parameters_schema(descriptor)
        self._executor = executor

    async def async_call(
        self,
        hass: Any,
        tool_input: Any,
        llm_context: Any,
    ) -> dict[str, Any]:
        """Validate arguments and execute only the bound intent."""
        args = getattr(tool_input, "tool_args", {})
        try:
            validated_args = self.descriptor.validate_args(args)
        except (TypeError, ValueError) as err:
            _LOGGER.warning(
                "Invalid local Assist tool arguments: tool=%s exception=%s",
                self.name,
                type(err).__name__,
            )
            raise HomeAssistantError("Invalid local Assist tool arguments") from err

        tool_call_id = getattr(tool_input, "id", None)
        _LOGGER.info(
            "Calling local Assist tool: tool=%s call_id=%s arg_keys=%s",
            self.name,
            tool_call_id,
            tuple(sorted(validated_args)),
        )
        try:
            result = await self._executor(
                hass,
                self.descriptor.intent_name,
                validated_args,
                llm_context,
            )
        except HomeAssistantError:
            _LOGGER.error("Local Assist tool failed: tool=%s", self.name)
            raise
        if not isinstance(result, Mapping):
            raise HomeAssistantError("Local Assist tool returned an invalid result")

        safe_result = dict(result)
        try:
            json.dumps(safe_result)
        except (TypeError, ValueError) as err:
            _LOGGER.error(
                "Local Assist tool returned non-serializable result: tool=%s",
                self.name,
            )
            raise HomeAssistantError("Local Assist tool returned an invalid result") from err

        _LOGGER.info("Local Assist tool succeeded: tool=%s", self.name)
        return safe_result


def build_tools(catalog: IntentCatalog | None = None) -> list[llm.Tool]:
    """Create one dynamic tool for each catalog descriptor."""
    if catalog is None:
        return []
    return [LocalAssistTool(descriptor) for descriptor in catalog.descriptors]


def _build_description(descriptor: IntentDescriptor) -> str:
    examples = "; ".join(f'"{example}"' for example in descriptor.examples)
    return (
        f"{descriptor.description}\n"
        f"Examples: {examples}\n"
        "Exact local Assist intent; use for matching requests, not broad "
        "area/domain actions."
    )
