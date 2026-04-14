"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

import pytest

homeassistant = pytest.importorskip("homeassistant")

from custom_components.foxess_ha_v2.config_flow import _field_name_for_device, _field_poll_for_device


def test_dynamic_field_names():
    assert _field_name_for_device("SN123") == "device_name__SN123"
    assert _field_poll_for_device("SN123") == "device_poll__SN123"
