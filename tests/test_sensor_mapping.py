"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:20:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

import pytest

homeassistant = pytest.importorskip("homeassistant")

from custom_components.foxess_ha_v2.sensor import _classify_sensor


def test_classify_sensor_power():
    device_class, state_class = _classify_sensor("pvPower", "W")
    assert str(device_class).endswith("power")
    assert str(state_class).endswith("measurement")


def test_classify_sensor_soc():
    device_class, state_class = _classify_sensor("SoC", "%")
    assert str(device_class).endswith("battery")
    assert str(state_class).endswith("measurement")
