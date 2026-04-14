"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FoxessApiClient
from .const import DOMAIN, PLATFORMS
from .coordinator import FoxessDataUpdateCoordinator

LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, {})
    LOGGER.debug("FoxESS HA v2 async_setup complete")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    LOGGER.debug("Setting up FoxESS entry_id=%s title=%s", entry.entry_id, entry.title)
    api_key = entry.data[CONF_API_KEY]
    session = async_get_clientsession(hass)
    api_client = FoxessApiClient(session=session, api_key=api_key)
    coordinator = FoxessDataUpdateCoordinator(hass, api_client, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api_client": api_client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    LOGGER.debug("FoxESS entry_id=%s setup complete", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    LOGGER.debug("Unloading FoxESS entry_id=%s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    LOGGER.debug("Reloading FoxESS entry_id=%s", entry.entry_id)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Placeholder migration hook for future schema updates."""
    return True
