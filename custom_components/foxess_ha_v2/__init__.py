"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2

Home Assistant entry points for setting up and unloading the FoxESS integration.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .api import FoxessApiClient
from .const import (
    DOMAIN,
    LEGACY_REMAINING_CALLS_ENTITY_ID,
    PLATFORMS,
    REMAINING_CALLS_ENTITY_ID,
    REMAINING_CALLS_UNIQUE_ID_SUFFIX,
)
from .coordinator import FoxessDataUpdateCoordinator

LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Initialize the integration domain storage."""

    hass.data.setdefault(DOMAIN, {})
    LOGGER.debug("FoxESS HA v2 async_setup complete")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one FoxESS config entry and perform its first refresh."""

    hass.data.setdefault(DOMAIN, {})
    LOGGER.debug("Setting up FoxESS entry_id=%s title=%s", entry.entry_id, entry.title)
    api_key = entry.data[CONF_API_KEY]
    session = async_get_clientsession(hass)
    api_client = FoxessApiClient(session=session, api_key=api_key)
    coordinator = FoxessDataUpdateCoordinator(hass, api_client, entry)
    await _async_migrate_remaining_calls_entity_id(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api_client": api_client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    LOGGER.debug("FoxESS entry_id=%s setup complete", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one FoxESS config entry and its platforms."""

    LOGGER.debug("Unloading FoxESS entry_id=%s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload an existing FoxESS config entry."""

    LOGGER.debug("Reloading FoxESS entry_id=%s", entry.entry_id)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


def _get_remaining_calls_entity_id_update(
    current_entity_id: str | None,
    *,
    target_entity_exists: bool,
) -> dict[str, str] | None:
    """Return the registry update needed to rename the legacy remaining-calls entity."""

    if current_entity_id != LEGACY_REMAINING_CALLS_ENTITY_ID or target_entity_exists:
        return None
    return {"new_entity_id": REMAINING_CALLS_ENTITY_ID}


async def _async_migrate_remaining_calls_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rename the legacy remaining-calls entity_id to the FoxESS-prefixed id."""

    entity_registry = er.async_get(hass)
    current_entity_id = entity_registry.async_get_entity_id(
        SENSOR_DOMAIN,
        DOMAIN,
        f"{entry.entry_id}:{REMAINING_CALLS_UNIQUE_ID_SUFFIX}",
    )
    target_entity_exists = entity_registry.async_get(REMAINING_CALLS_ENTITY_ID) is not None
    update_data = _get_remaining_calls_entity_id_update(
        current_entity_id,
        target_entity_exists=target_entity_exists,
    )
    if update_data is None:
        if current_entity_id == LEGACY_REMAINING_CALLS_ENTITY_ID and target_entity_exists:
            LOGGER.warning(
                "Skipping remaining calls entity rename for entry_id=%s because %s already exists",
                entry.entry_id,
                REMAINING_CALLS_ENTITY_ID,
            )
        return

    # Keep the migration narrow so existing entity history survives the rename.
    entity_registry.async_update_entity(
        current_entity_id,
        **update_data,
    )
    LOGGER.debug(
        "Renamed remaining calls entity for entry_id=%s to %s",
        entry.entry_id,
        REMAINING_CALLS_ENTITY_ID,
    )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Placeholder migration hook for future schema updates."""
    return True
