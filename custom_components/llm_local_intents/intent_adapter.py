"""Home Assistant intent registry and direct execution adapter."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import logging
from typing import Any

from .const import DOMAIN

try:
    from homeassistant.exceptions import HomeAssistantError
except ImportError:  # pragma: no cover - only used by dependency-free tests.
    class HomeAssistantError(Exception):
        """Fallback Home Assistant error type."""


_LOGGER = logging.getLogger(__name__)


def get_registered_handlers(hass: Any) -> set[str] | None:
    """Return registered intent names, or ``None`` when the API is unavailable."""
    try:
        from homeassistant.helpers import intent

        handlers: Iterable[Any] = intent.async_get(hass)
    except (AttributeError, ImportError):
        return None
    return {
        name
        for handler in handlers
        if isinstance(name := getattr(handler, "intent_type", None), str)
    }


async def async_handle_local_intent(
    hass: Any,
    intent_name: str,
    slot_values: Mapping[str, Any],
    llm_context: Any,
) -> dict[str, Any]:
    """Fire one exact Assist intent without going through Conversation API."""
    try:
        from homeassistant.helpers import intent
    except ImportError as err:  # pragma: no cover - dependency-free tests inject it.
        raise HomeAssistantError("Home Assistant intent API is unavailable") from err

    slots = {name: {"value": value} for name, value in slot_values.items()}
    platform = getattr(llm_context, "platform", None) or DOMAIN
    language = getattr(llm_context, "language", None)
    if language == "*":
        language = None

    try:
        response = await intent.async_handle(
            hass,
            platform,
            intent_name,
            slots=slots,
            context=getattr(llm_context, "context", None),
            language=language,
            assistant=getattr(llm_context, "assistant", None),
            device_id=getattr(llm_context, "device_id", None),
        )
    except HomeAssistantError:
        raise
    except Exception as err:
        _LOGGER.error(
            "Local Assist handler failed: intent=%s exception=%s",
            intent_name,
            type(err).__name__,
        )
        raise HomeAssistantError("Local Assist intent execution failed") from err

    return {
        "success": True,
        "intent": intent_name,
        "speech": _extract_speech(response),
    }


def _extract_speech(response: Any) -> str:
    """Extract a short plain/SSML speech value without returning HA objects."""
    speech = response.get("speech") if isinstance(response, Mapping) else getattr(response, "speech", None)
    if not isinstance(speech, Mapping):
        return ""

    for key in ("plain", "ssml"):
        value = speech.get(key)
        if isinstance(value, Mapping):
            text = value.get("speech")
            if isinstance(text, str):
                return text
        elif isinstance(value, str):
            return value
    return ""
