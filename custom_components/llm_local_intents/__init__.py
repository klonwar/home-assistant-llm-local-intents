"""The LLM Local Intents integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant

from .catalog import IntentCatalog, build_catalog
from .const import DOMAIN
from .intent_adapter import get_registered_handlers


_LOGGER = logging.getLogger(__name__)
_CATALOG_KEY = "catalog"
_CONFIG_KEY = "config"
_GENERATION_KEY = "generation"
_UNSUB_KEY = "unsubscribe_reload"


CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): dict},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up LLM Local Intents from merged YAML configuration."""
    if not hasattr(hass, "data"):
        hass.data = {}
    state = hass.data.setdefault(DOMAIN, {})
    state[_CONFIG_KEY] = config

    await _async_rebuild_catalog(hass, config, state=state, initial=True)
    _register_reload_listener(hass, state)
    return True


async def async_reload(hass: HomeAssistant, config: dict | None = None) -> bool:
    """Rebuild and atomically publish the catalog for tests and reload hooks."""
    if not hasattr(hass, "data"):
        hass.data = {}
    state = hass.data.setdefault(DOMAIN, {})
    source_config = config if config is not None else state.get(_CONFIG_KEY, {})
    return await _async_rebuild_catalog(hass, source_config, state=state)


def get_catalog(hass: HomeAssistant) -> IntentCatalog:
    """Return the current immutable catalog snapshot."""
    state = getattr(hass, "data", {}).get(DOMAIN, {})
    return state.get(_CATALOG_KEY, IntentCatalog())


async def _async_rebuild_catalog(
    hass: HomeAssistant,
    config: dict,
    *,
    state: dict[str, Any],
    initial: bool = False,
) -> bool:
    """Build a new snapshot and publish it only after validation succeeds."""
    _LOGGER.info("Loading local Assist catalog")
    try:
        handlers = get_registered_handlers(hass)
        catalog = build_catalog(config, available_handlers=handlers)
    except Exception as err:  # Keep a working snapshot on reload failures.
        _LOGGER.error(
            "Local Assist catalog load failed: exception=%s", type(err).__name__
        )
        if initial and _CATALOG_KEY not in state:
            state[_CATALOG_KEY] = IntentCatalog()
            state[_GENERATION_KEY] = 0
        return False

    generation = int(state.get(_GENERATION_KEY, 0)) + 1
    state[_CATALOG_KEY] = catalog
    state[_CONFIG_KEY] = config
    state[_GENERATION_KEY] = generation
    _LOGGER.info(
        "Loaded local Assist catalog: generation=%s declared=%s exposed=%s skipped=%s",
        generation,
        catalog.declared_count,
        catalog.exposed_count,
        catalog.skipped_count,
    )
    return True


def _register_reload_listener(hass: HomeAssistant, state: dict[str, Any]) -> None:
    """Subscribe to HA's standard config-update event when available."""
    if _UNSUB_KEY in state:
        return
    bus = getattr(hass, "bus", None)
    listen = getattr(bus, "async_listen", None)
    if listen is None:
        return
    try:
        from homeassistant.core import EVENT_CORE_CONFIG_UPDATE
    except ImportError:
        return

    async def _on_config_update(_event: Any) -> None:
        try:
            from homeassistant.helpers.reload import async_integration_yaml_config

            fresh_config = await async_integration_yaml_config(
                hass,
                DOMAIN,
                raise_on_failure=True,
            )
        except ImportError:
            fresh_config = state.get(_CONFIG_KEY, {})
        except Exception as err:
            _LOGGER.error(
                "Local Assist catalog reload config lookup failed: exception=%s",
                type(err).__name__,
            )
            return

        await async_reload(hass, fresh_config or {})

    state[_UNSUB_KEY] = listen(EVENT_CORE_CONFIG_UPDATE, _on_config_update)
