"""
Version: v0.1.6
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2
"""

import pytest

homeassistant = pytest.importorskip("homeassistant")

from custom_components.foxess_ha_v2.sensor import _classify_sensor
from custom_components.foxess_ha_v2.sensor import _coerce_numeric_sensor_value
from custom_components.foxess_ha_v2.sensor import _normalize_sensor_unit


def test_classify_sensor_power():
    device_class, state_class = _classify_sensor("pvPower", "W")
    assert str(device_class).endswith("power")
    assert str(state_class).endswith("measurement")


def test_classify_sensor_soc():
    device_class, state_class = _classify_sensor("SoC", "%")
    assert str(device_class).endswith("battery")
    assert str(state_class).endswith("measurement")


@pytest.mark.parametrize("unit", ["C", "degC", "Cel", "\u00b0C", "\u2103"])
def test_classify_sensor_temperature_units(unit):
    device_class, state_class = _classify_sensor("ambientTemp", unit)
    assert str(device_class).endswith("temperature")
    assert str(state_class).endswith("measurement")
    assert _normalize_sensor_unit(unit) == "\u00b0C"


@pytest.mark.parametrize("unit", [None, ""])
def test_classify_sensor_temperature_by_variable_name(unit):
    device_class, state_class = _classify_sensor("ambientTemperation", unit)
    assert str(device_class).endswith("temperature")
    assert str(state_class).endswith("measurement")
    assert _normalize_sensor_unit(unit, "ambientTemperation") == "\u00b0C"


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
