"""Voluptuous schemas with a small dependency-free test fallback."""

from __future__ import annotations

from typing import Any

from .catalog import IntentDescriptor, SlotSpec

try:  # Home Assistant supplies voluptuous at runtime.
    import voluptuous as vol
except ModuleNotFoundError:  # pragma: no cover - exercised by isolated tests.
    vol = None  # type: ignore[assignment]


class FallbackSchema:
    """Minimal callable schema used when HA dependencies are not installed."""

    def __init__(self, descriptor: IntentDescriptor) -> None:
        self.descriptor = descriptor

    def __call__(self, value: Any) -> dict[str, Any]:
        return self.descriptor.validate_args(value)


def build_parameters_schema(descriptor: IntentDescriptor) -> Any:
    """Build the voluptuous schema advertised to Home Assistant LLM APIs."""
    if vol is None:
        return FallbackSchema(descriptor)

    schema: dict[Any, Any] = {}
    for slot in descriptor.slots:
        key = vol.Required(slot.name) if slot.required else vol.Optional(slot.name)
        schema[key] = _slot_validator(slot)
    return vol.Schema(schema)


def _slot_validator(slot: SlotSpec):
    def validate(value: Any) -> Any:
        try:
            return slot.validate(value)
        except ValueError as err:
            raise vol.Invalid(str(err)) from err

    return validate
