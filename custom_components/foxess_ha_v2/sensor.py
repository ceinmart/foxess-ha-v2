"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import extract_realtime_variable_records
from .const import (
    CONF_DEVICE_SN,
    CONF_DEVICE_TYPE,
    CONF_DEVICES,
    CONF_FRIENDLY_NAME,
    CONF_PRODUCT_TYPE,
    CONF_STATION_NAME,
    CONF_SUPPORTED_VARIABLES,
    CONF_VARIABLE_CATALOG,
    DOMAIN,
)

_POWER_UNITS = {"W", "kW", "MW"}
_ENERGY_UNITS = {"Wh", "kWh", "MWh"}
_CURRENT_UNITS = {"A", "mA"}
_VOLTAGE_UNITS = {"V", "mV"}
_FREQUENCY_UNITS = {"Hz"}
_TEMPERATURE_UNITS = {"C", "degC", "Cel"}
_RESERVED_VARIABLE_FIELDS = {
    "deviceSN",
    "deviceSn",
    "sn",
    "name",
    "time",
    "unit",
    "value",
    "variable",
    "group",
    "group_label",
}


def _extract_variable_value(device_payload: dict[str, Any], variable: str) -> Any:
    records = extract_realtime_variable_records(device_payload)
    row = records.get(variable, {})
    if isinstance(row, dict):
        return row.get("value")
    return None


def _safe_sensor_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _classify_sensor(variable: str, unit: str | None) -> tuple[SensorDeviceClass | None, SensorStateClass | None]:
    normalized_unit = (unit or "").strip()
    lower_var = variable.lower()

    if normalized_unit in _POWER_UNITS:
        return SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT
    if normalized_unit in _ENERGY_UNITS:
        return SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING
    if normalized_unit in _CURRENT_UNITS:
        return SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT
    if normalized_unit in _VOLTAGE_UNITS:
        return SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT
    if normalized_unit in _FREQUENCY_UNITS:
        return SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT
    if normalized_unit in _TEMPERATURE_UNITS:
        return SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT

    if "soc" in lower_var:
        return SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT

    return None, None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    devices = entry.data.get(CONF_DEVICES, {})
    variable_catalog = entry.data.get(CONF_VARIABLE_CATALOG, {})

    entities: list[SensorEntity] = []
    for sn, device_cfg in devices.items():
        configured_variables = [
            variable
            for variable in device_cfg.get(CONF_SUPPORTED_VARIABLES, [])
            if isinstance(variable, str) and variable not in _RESERVED_VARIABLE_FIELDS
        ]

        runtime_payload = coordinator.data.get("realtime_by_sn", {}).get(sn, {})
        runtime_records = extract_realtime_variable_records(runtime_payload)

        runtime_variables = [
            variable for variable in sorted(runtime_records.keys()) if variable not in _RESERVED_VARIABLE_FIELDS
        ]
        catalog_variables = [
            variable for variable in sorted(variable_catalog.keys()) if variable not in _RESERVED_VARIABLE_FIELDS
        ]
        variables = configured_variables or runtime_variables or catalog_variables

        for variable in variables:
            variable_meta = variable_catalog.get(variable, {})
            if not isinstance(variable_meta, dict):
                variable_meta = {}
            else:
                variable_meta = dict(variable_meta)

            if variable in runtime_records:
                runtime_row = runtime_records[variable]
                if runtime_row.get("unit") and not variable_meta.get("unit"):
                    variable_meta["unit"] = runtime_row.get("unit")
                if runtime_row.get("name"):
                    labels = variable_meta.get("name", {})
                    if not isinstance(labels, dict):
                        labels = {}
                    labels.setdefault("en", runtime_row.get("name"))
                    variable_meta["name"] = labels

            entities.append(
                FoxessVariableSensor(
                    coordinator=coordinator,
                    entry_id=entry.entry_id,
                    device_sn=sn,
                    device_cfg=device_cfg,
                    variable=variable,
                    variable_meta=variable_meta,
                )
            )

    entities.append(FoxessRemainingAccessCountSensor(coordinator=coordinator, entry_id=entry.entry_id))
    async_add_entities(entities)


class FoxessVariableSensor(CoordinatorEntity, SensorEntity):
    """Sensor generated for each variable supported by a selected device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        *,
        coordinator,
        entry_id: str,
        device_sn: str,
        device_cfg: dict[str, Any],
        variable: str,
        variable_meta: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._device_sn = device_sn
        self._variable = variable
        self._device_cfg = device_cfg
        self._variable_meta = variable_meta

        self._attr_unique_id = f"{entry_id}:{device_sn}:{variable}"
        self._attr_name = self._build_entity_name()
        self._attr_native_unit_of_measurement = variable_meta.get("unit")
        device_class, state_class = _classify_sensor(variable, self._attr_native_unit_of_measurement)
        self._attr_device_class = device_class
        self._attr_state_class = state_class

    def _build_entity_name(self) -> str:
        labels = self._variable_meta.get("name", {})
        if isinstance(labels, dict):
            label = labels.get("en") or labels.get("en_US")
            if isinstance(label, str) and label.strip():
                return label.strip()
        return self._variable

    @property
    def device_info(self) -> DeviceInfo:
        friendly_name = self._device_cfg.get(CONF_FRIENDLY_NAME) or self._device_sn
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}:{self._device_sn}")},
            name=friendly_name,
            manufacturer="FoxESS",
            model=self._device_cfg.get(CONF_DEVICE_TYPE) or self._device_cfg.get(CONF_PRODUCT_TYPE),
            serial_number=self._device_cfg.get(CONF_DEVICE_SN, self._device_sn),
            suggested_area=self._device_cfg.get(CONF_STATION_NAME),
        )

    @property
    def available(self) -> bool:
        realtime_by_sn = self.coordinator.data.get("realtime_by_sn", {})
        return self.coordinator.last_update_success and self._device_sn in realtime_by_sn

    @property
    def native_value(self) -> Any:
        realtime_by_sn = self.coordinator.data.get("realtime_by_sn", {})
        payload = realtime_by_sn.get(self._device_sn, {})
        return _safe_sensor_value(_extract_variable_value(payload, self._variable))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "device_sn": self._device_sn,
            "variable": self._variable,
        }


class FoxessRemainingAccessCountSensor(CoordinatorEntity, SensorEntity):
    """Shows latest API remaining calls snapshot."""

    _attr_has_entity_name = True
    _attr_name = "API remaining calls"

    def __init__(self, *, coordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}:api_remaining_calls"
        self._entry_id = entry_id

    @property
    def native_value(self) -> Any:
        access_count = self.coordinator.data.get("access_count", {})
        return access_count.get("remaining")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        access_count = self.coordinator.data.get("access_count", {})
        return {"api_total_calls": access_count.get("total")}
