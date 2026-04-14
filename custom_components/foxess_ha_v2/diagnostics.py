"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .const import DOMAIN


def _mask_secret(secret: str | None) -> str:
    if not secret:
        return ""
    if len(secret) <= 4:
        return "*" * len(secret)
    return f"{'*' * (len(secret) - 4)}{secret[-4:]}"


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
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
