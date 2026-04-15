"""
Versao: v0.1.4b1
Data/hora de criacao: 2026-04-15 09:30:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from __future__ import annotations

from typing import Any

DEVICE_STATUS_MAP: dict[int, str] = {
    1: "online",
    2: "breakdown",
    3: "offline",
}

RUNNING_STATE_MAP: dict[int, str] = {
    160: "self-test",
    161: "waiting",
    162: "checking",
    163: "on-grid",
    164: "off-grid",
    165: "fault",
    166: "permanent-fault",
    167: "standby",
    168: "upgrading",
    169: "fct",
    170: "illegal",
}

DEVICE_STATUS_OPTIONS = tuple(DEVICE_STATUS_MAP.values())
RUNNING_STATE_OPTIONS = tuple(RUNNING_STATE_MAP.values())


def coerce_int_code(value: Any) -> int | None:
    """Normalize API enum-like values into integers when possible."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and (stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit())):
            return int(stripped)
    return None


def _map_enum_value(value: Any, mapping: dict[int, str]) -> str | None:
    code = coerce_int_code(value)
    if code is not None:
        return mapping.get(code)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def map_device_status(value: Any) -> str | None:
    """Translate the FoxESS device detail status code into text."""

    return _map_enum_value(value, DEVICE_STATUS_MAP)


def map_running_state(value: Any) -> str | None:
    """Translate the FoxESS realtime runningState code into text."""

    return _map_enum_value(value, RUNNING_STATE_MAP)
