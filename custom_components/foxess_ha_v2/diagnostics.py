"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2

Diagnostics helpers for exposing safe runtime data to Home Assistant support tools.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .const import DOMAIN


def _mask_secret(secret: str | None) -> str:
    """Mask secrets before they are returned through diagnostics."""

    if not secret:
        return ""
    if len(secret) <= 4:
        return "*" * len(secret)
    return f"{'*' * (len(secret) - 4)}{secret[-4:]}"


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return redacted diagnostics for a FoxESS config entry."""

    redacted_data = deepcopy(dict(entry.data))
    if CONF_API_KEY in redacted_data:
        redacted_data[CONF_API_KEY] = _mask_secret(redacted_data[CONF_API_KEY])

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    coordinator_state = coordinator.data if coordinator else {}

    return {
        "entry_id": entry.entry_id,
        "entry_title": entry.title,
        "entry_data": redacted_data,
        "coordinator_state": coordinator_state,
    }
