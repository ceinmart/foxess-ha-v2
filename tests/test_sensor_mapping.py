"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2
"""

import pytest

homeassistant = pytest.importorskip("homeassistant")

from custom_components.foxess_ha_v2.sensor import _classify_sensor
from custom_components.foxess_ha_v2.sensor import _coerce_numeric_sensor_value


def test_classify_sensor_power():
    device_class, state_class = _classify_sensor("pvPower", "W")
    assert str(device_class).endswith("power")
    assert str(state_class).endswith("measurement")


def test_classify_sensor_soc():
    device_class, state_class = _classify_sensor("SoC", "%")
    assert str(device_class).endswith("battery")
    assert str(state_class).endswith("measurement")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (321, 321),
        (321.0, 321),
        (321.5, 321.5),
        ("321", 321),
        ("321.0", 321),
        ("321.5", 321.5),
        ("  321  ", 321),
        ("NaN", None),
        ("abc", None),
        (True, None),
        (None, None),
    ],
)
def test_coerce_numeric_sensor_value(raw, expected):
    assert _coerce_numeric_sensor_value(raw) == expected
