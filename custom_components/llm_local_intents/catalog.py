"""Configuration parsing and immutable catalog for local Assist intents."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import logging
import re
from typing import Any


_INTENT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_SUPPORTED_SLOT_TYPES = {"integer", "number", "string", "boolean"}
_LOGGER = logging.getLogger(__name__)


class CatalogValidationError(ValueError):
    """Raised when a catalog entry cannot be validated."""


@dataclass(frozen=True, slots=True)
class SlotSpec:
    """Validated metadata for one tool slot."""

    name: str
    type: str
    required: bool = True
    minimum: int | float | None = None
    maximum: int | float | None = None
    enum: tuple[Any, ...] | None = None
    enum_values: tuple[Any, ...] | None = None

    def validate(self, value: Any) -> Any:
        """Validate one value and return its internal representation."""
        if self.type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"slot {self.name} must be an integer")
        elif self.type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"slot {self.name} must be a number")
        elif self.type == "string":
            if not isinstance(value, str):
                raise ValueError(f"slot {self.name} must be a string")
        elif self.type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"slot {self.name} must be a boolean")

        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"slot {self.name} is below minimum")
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"slot {self.name} is above maximum")

        if self.enum is not None:
            try:
                index = self.enum.index(value)
            except ValueError as err:
                raise ValueError(f"slot {self.name} is not in enum") from err
            if self.enum_values is not None:
                return self.enum_values[index]

        return value


@dataclass(frozen=True, slots=True)
class IntentDescriptor:
    """Immutable, validated metadata for one exposed intent."""

    intent_name: str
    tool_name: str
    description: str
    examples: tuple[str, ...]
    priority: int
    category: str | None
    notes: str | None
    slots: tuple[SlotSpec, ...]

    @property
    def slot_map(self) -> dict[str, SlotSpec]:
        """Return slots keyed by their public names."""
        return {slot.name: slot for slot in self.slots}

    def validate_args(self, args: Mapping[str, Any]) -> dict[str, Any]:
        """Validate and normalize model-provided tool arguments."""
        if not isinstance(args, Mapping):
            raise ValueError("tool arguments must be a mapping")

        known = self.slot_map
        unknown = set(args) - set(known)
        if unknown:
            raise ValueError("unknown tool arguments")

        result: dict[str, Any] = {}
        for name, slot in known.items():
            if name not in args:
                if slot.required:
                    raise ValueError(f"missing required slot {name}")
                continue
            result[name] = slot.validate(args[name])
        return result


@dataclass(frozen=True, slots=True)
class IntentCatalog:
    """Immutable catalog plus load counters used for diagnostics."""

    descriptors: tuple[IntentDescriptor, ...] = ()
    declared_count: int = 0
    skipped_count: int = 0

    @property
    def exposed_count(self) -> int:
        """Return the number of exposed descriptors."""
        return len(self.descriptors)


def build_catalog(
    config: Mapping[str, Any] | None,
    *,
    available_handlers: Iterable[str] | None = None,
) -> IntentCatalog:
    """Build a validated catalog from merged Home Assistant config.

    Invalid entries are skipped rather than making unrelated entries
    unavailable. ``available_handlers`` is optional so pure parser tests and
    environments that expose the handler registry lazily can still validate
    metadata. When provided, unknown handlers are skipped.
    """
    intents = _get_intents_mapping(config)
    handlers = set(available_handlers) if available_handlers is not None else None
    descriptors: list[IntentDescriptor] = []
    seen_tools: set[str] = set()
    skipped = 0

    for intent_name, raw_entry in intents.items():
        try:
            descriptor = _parse_descriptor(
                intent_name,
                raw_entry,
                available_handlers=handlers,
            )
            if not descriptor:
                skipped += 1
                continue
            if descriptor.tool_name in seen_tools:
                raise CatalogValidationError("duplicate generated tool name")
            seen_tools.add(descriptor.tool_name)
            descriptors.append(descriptor)
        except (CatalogValidationError, TypeError, ValueError) as err:
            _LOGGER.warning(
                "Skipping local Assist intent: intent=%s reason=%s",
                intent_name,
                type(err).__name__,
            )
            skipped += 1

    descriptors.sort(key=lambda item: (-item.priority, item.tool_name))
    return IntentCatalog(
        descriptors=tuple(descriptors),
        declared_count=len(intents),
        skipped_count=skipped,
    )


def tool_name_for_intent(intent_name: str) -> str:
    """Return a stable tool name for an Assist intent name."""
    snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", intent_name).lower()
    snake_name = re.sub(r"[^a-z0-9_]+", "_", snake_name).strip("_")
    return f"local_assist_{snake_name}"


def _get_intents_mapping(config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, Mapping):
        raise CatalogValidationError("integration config must be a mapping")

    raw_config: Any = config
    if "intents" not in raw_config and "llm_local_intents" in raw_config:
        raw_config = raw_config["llm_local_intents"]
    if not isinstance(raw_config, Mapping):
        raise CatalogValidationError("integration config must be a mapping")

    raw_intents = raw_config.get("intents", {})
    if not isinstance(raw_intents, Mapping):
        raise CatalogValidationError("intents must be a mapping")
    return raw_intents


def _parse_descriptor(
    intent_name: Any,
    raw_entry: Any,
    *,
    available_handlers: set[str] | None,
) -> IntentDescriptor | None:
    if not isinstance(intent_name, str) or not _INTENT_NAME_RE.fullmatch(intent_name):
        raise CatalogValidationError("invalid intent name")
    if available_handlers is not None and intent_name not in available_handlers:
        raise CatalogValidationError("unknown intent handler")
    if not isinstance(raw_entry, Mapping):
        raise CatalogValidationError("intent metadata must be a mapping")
    expose = raw_entry.get("expose", True)
    if not isinstance(expose, bool):
        raise CatalogValidationError("expose must be boolean")
    if not expose:
        return None

    description = raw_entry.get("description")
    examples = raw_entry.get("examples")
    if not isinstance(description, str) or not description.strip():
        raise CatalogValidationError("description is required")
    if not isinstance(examples, (list, tuple)):
        raise CatalogValidationError("examples must be a list")
    if not examples or any(
        not isinstance(example, str) or not example.strip() for example in examples
    ):
        raise CatalogValidationError("at least one example is required")
    clean_examples = tuple(example.strip() for example in examples)

    priority = raw_entry.get("priority", 50)
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise CatalogValidationError("priority must be an integer")

    category = raw_entry.get("category")
    if category is not None and (not isinstance(category, str) or not category.strip()):
        raise CatalogValidationError("category must be a non-empty string")
    notes = raw_entry.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise CatalogValidationError("notes must be a string")

    raw_slots = raw_entry.get("slots", {})
    if not isinstance(raw_slots, Mapping):
        raise CatalogValidationError("slots must be a mapping")
    slots = tuple(_parse_slot(name, value) for name, value in raw_slots.items())

    return IntentDescriptor(
        intent_name=intent_name,
        tool_name=tool_name_for_intent(intent_name),
        description=description.strip(),
        examples=clean_examples,
        priority=priority,
        category=category.strip() if isinstance(category, str) else None,
        notes=notes,
        slots=slots,
    )


def _parse_slot(name: Any, raw_slot: Any) -> SlotSpec:
    if not isinstance(name, str) or not name or not isinstance(raw_slot, Mapping):
        raise CatalogValidationError("invalid slot metadata")
    slot_type = raw_slot.get("type", "string")
    if slot_type not in _SUPPORTED_SLOT_TYPES:
        raise CatalogValidationError("unsupported slot type")

    required = raw_slot.get("required", True)
    if not isinstance(required, bool):
        raise CatalogValidationError("required must be boolean")

    minimum = raw_slot.get("minimum")
    maximum = raw_slot.get("maximum")
    if minimum is not None and (
        isinstance(minimum, bool) or not isinstance(minimum, (int, float))
    ):
        raise CatalogValidationError("minimum must be numeric")
    if maximum is not None and (
        isinstance(maximum, bool) or not isinstance(maximum, (int, float))
    ):
        raise CatalogValidationError("maximum must be numeric")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise CatalogValidationError("minimum cannot exceed maximum")
    if slot_type not in {"integer", "number"} and (minimum is not None or maximum is not None):
        raise CatalogValidationError("numeric bounds require a numeric slot")

    enum = raw_slot.get("enum")
    enum_values: tuple[Any, ...] | None = None
    enum_items: tuple[Any, ...] | None = None
    if enum is not None:
        if isinstance(enum, Mapping):
            if not enum:
                raise CatalogValidationError("enum cannot be empty")
            enum_items = tuple(enum.keys())
            enum_values = tuple(enum.values())
        elif isinstance(enum, (list, tuple)) and enum:
            enum_items = tuple(enum)
        else:
            raise CatalogValidationError("enum must be a non-empty list or mapping")

        for value in enum_items:
            _validate_slot_type(slot_type, value)
        if enum_values is not None:
            for value in enum_values:
                if not _is_json_value(value):
                    raise CatalogValidationError("enum internal values must be JSON values")

    return SlotSpec(
        name=name,
        type=slot_type,
        required=required,
        minimum=minimum,
        maximum=maximum,
        enum=enum_items,
        enum_values=enum_values,
    )


def _validate_slot_type(slot_type: str, value: Any) -> None:
    if slot_type == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
        raise CatalogValidationError("enum value has wrong integer type")
    if slot_type == "number" and (
        isinstance(value, bool) or not isinstance(value, (int, float))
    ):
        raise CatalogValidationError("enum value has wrong number type")
    if slot_type == "string" and not isinstance(value, str):
        raise CatalogValidationError("enum value has wrong string type")
    if slot_type == "boolean" and not isinstance(value, bool):
        raise CatalogValidationError("enum value has wrong boolean type")


def _is_json_value(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool, list, dict))
