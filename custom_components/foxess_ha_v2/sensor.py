"""
Versao: v0.1.4b1
Data/hora de criacao: 2026-04-15 10:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import extract_realtime_variable_records
from .const import (
    ATTR_LAST_VALID_AT,
    ATTR_RESTORED,
    ATTR_SOURCE_TIMESTAMP,
    ATTR_STALE,
    CONF_DEVICE_SN,
    CONF_DEVICE_TYPE,
    CONF_DEVICES,
    CONF_FRIENDLY_NAME,
    CONF_PRODUCT_TYPE,
    CONF_STATION_NAME,
    CONF_SUPPORTED_VARIABLES,
    CONF_VARIABLE_CATALOG,
    DOMAIN,
    REMAINING_CALLS_SUGGESTED_OBJECT_ID,
    REMAINING_CALLS_UNIQUE_ID_SUFFIX,
)
from .value_mappings import (
    DEVICE_STATUS_OPTIONS,
    RUNNING_STATE_OPTIONS,
    coerce_int_code,
    map_device_status,
    map_running_state,
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
_COMMON_STATE_ATTRS = {ATTR_LAST_VALID_AT, ATTR_SOURCE_TIMESTAMP, ATTR_STALE, ATTR_RESTORED}
_DEVICE_DETAIL_SENSOR_DESCRIPTIONS: tuple[tuple[str, str, str | None], ...] = (
    ("deviceType", "Device type", None),
    ("masterVersion", "Master version", None),
    ("capacity", "Capacity", "kW"),
    ("status", "Status", None),
)


def _safe_sensor_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# Versao: v0.1.4
# Data/hora de criacao: 2026-04-18 20:57:26
# Criado por: Codex / OpenAI
# Projeto/Pasta: C:\tmp\foxess-ha.v2\foxess-ha-v2
def _coerce_numeric_sensor_value(value: Any) -> int | float | None:
    """Return a finite numeric value for HA sensor state, or None when invalid."""

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return int(value) if value.is_integer() else value

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            numeric_value = float(candidate)
        except ValueError:
            return None
        if not math.isfinite(numeric_value):
            return None
        return int(numeric_value) if numeric_value.is_integer() else numeric_value

    return None


def _build_device_info(entry_id: str, device_sn: str, device_cfg: dict[str, Any]) -> DeviceInfo:
    friendly_name = device_cfg.get(CONF_FRIENDLY_NAME) or device_sn
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}:{device_sn}")},
        name=friendly_name,
        manufacturer="FoxESS",
        model=device_cfg.get(CONF_DEVICE_TYPE) or device_cfg.get(CONF_PRODUCT_TYPE),
        serial_number=device_cfg.get(CONF_DEVICE_SN, device_sn),
        suggested_area=device_cfg.get(CONF_STATION_NAME),
    )


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

        for detail_key, entity_name, native_unit in _DEVICE_DETAIL_SENSOR_DESCRIPTIONS:
            entities.append(
                FoxessDeviceDetailSensor(
                    coordinator=coordinator,
                    entry_id=entry.entry_id,
                    device_sn=sn,
                    device_cfg=device_cfg,
                    detail_key=detail_key,
                    entity_name=entity_name,
                    native_unit=native_unit,
                )
            )

    entities.append(FoxessRemainingAccessCountSensor(coordinator=coordinator, entry_id=entry.entry_id))
    async_add_entities(entities)


class FoxessRestoringSensor(CoordinatorEntity, RestoreSensor, SensorEntity):
    """Coordinator-backed sensor that preserves the last valid value."""

    _attr_has_entity_name = True

    def __init__(self, *, coordinator, entry_id: str, device_sn: str, device_cfg: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._device_sn = device_sn
        self._device_cfg = device_cfg
        self._has_valid_state = False
        self._live_available = False
        self._last_valid_native_value: Any = None
        self._last_valid_at: str | None = None
        self._source_timestamp: str | None = None
        self._restored = False
        self._stale = False
        self._extra_state_attrs: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        last_sensor_data = await self.async_get_last_sensor_data()
        if last_sensor_data is not None and last_sensor_data.native_value is not None:
            restored_value = self._normalize_restored_value(last_sensor_data.native_value)
            if restored_value is not None:
                self._has_valid_state = True
                self._last_valid_native_value = restored_value
                if last_sensor_data.native_unit_of_measurement is not None:
                    self._attr_native_unit_of_measurement = last_sensor_data.native_unit_of_measurement
                attrs = last_state.attributes if last_state is not None else {}
                self._last_valid_at = attrs.get(ATTR_LAST_VALID_AT)
                self._source_timestamp = attrs.get(ATTR_SOURCE_TIMESTAMP)
                self._restored = True
                self._stale = True
                self._extra_state_attrs = {
                    key: value for key, value in attrs.items() if key not in _COMMON_STATE_ATTRS
                }

        self._sync_from_live_data()

    def _normalize_restored_value(self, value: Any) -> Any:
        return _safe_sensor_value(value)

    def _get_live_state(self) -> tuple[bool, Any, str | None, str | None, dict[str, Any]]:
        raise NotImplementedError

    def _sync_from_live_data(self) -> None:
        valid, native_value, native_unit, source_timestamp, extra_attrs = self._get_live_state()
        self._live_available = valid

        if valid:
            self._has_valid_state = True
            self._last_valid_native_value = native_value
            if native_unit is not None:
                self._attr_native_unit_of_measurement = native_unit
            self._last_valid_at = self.coordinator.data.get("updated_at")
            self._source_timestamp = source_timestamp
            self._restored = False
            self._stale = False
            self._extra_state_attrs = extra_attrs
        elif self._has_valid_state:
            self._stale = True

    @property
    def device_info(self) -> DeviceInfo:
        return _build_device_info(self._entry_id, self._device_sn, self._device_cfg)

    @property
    def available(self) -> bool:
        return self._live_available or self._has_valid_state

    @property
    def native_value(self) -> Any:
        if not self._has_valid_state:
            return None
        return self._last_valid_native_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = dict(self._extra_state_attrs)
        attrs[ATTR_LAST_VALID_AT] = self._last_valid_at
        attrs[ATTR_SOURCE_TIMESTAMP] = self._source_timestamp
        attrs[ATTR_STALE] = self._stale
        attrs[ATTR_RESTORED] = self._restored
        return attrs

    def _handle_coordinator_update(self) -> None:
        self._sync_from_live_data()
        super()._handle_coordinator_update()


class FoxessVariableSensor(FoxessRestoringSensor):
    """Sensor generated for each variable supported by a selected device."""

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
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            device_sn=device_sn,
            device_cfg=device_cfg,
        )
        self._variable = variable
        self._variable_meta = variable_meta

        self._attr_unique_id = f"{entry_id}:{device_sn}:{variable}"
        self._attr_name = self._build_entity_name()
        self._attr_native_unit_of_measurement = variable_meta.get("unit")

        if self._variable == "runningState":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(RUNNING_STATE_OPTIONS)
            self._attr_native_unit_of_measurement = None
        else:
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

    def _normalize_restored_value(self, value: Any) -> Any:
        if self._variable == "runningState":
            return map_running_state(value)
        return _safe_sensor_value(value)

    def _get_live_state(self) -> tuple[bool, Any, str | None, str | None, dict[str, Any]]:
        realtime_by_sn = self.coordinator.data.get("realtime_by_sn", {})
        payload = realtime_by_sn.get(self._device_sn, {})
        records = extract_realtime_variable_records(payload)
        row = records.get(self._variable)

        if not isinstance(row, dict):
            return False, None, None, None, {"device_sn": self._device_sn, "variable": self._variable}

        raw_value = row.get("value")
        source_timestamp = row.get("time") or payload.get("time")
        native_unit = row.get("unit") or self._variable_meta.get("unit")
        extra_attrs: dict[str, Any] = {
            "device_sn": self._device_sn,
            "variable": self._variable,
        }

        if self._variable == "runningState":
            code = coerce_int_code(raw_value)
            mapped_value = map_running_state(raw_value)
            extra_attrs["running_state_code"] = code
            return mapped_value is not None, mapped_value, None, source_timestamp, extra_attrs

        if raw_value is None:
            return False, None, native_unit, source_timestamp, extra_attrs

        return True, _safe_sensor_value(raw_value), native_unit, source_timestamp, extra_attrs


class FoxessDeviceDetailSensor(FoxessRestoringSensor):
    """Static/detail sensor populated from /op/v1/device/detail."""

    def __init__(
        self,
        *,
        coordinator,
        entry_id: str,
        device_sn: str,
        device_cfg: dict[str, Any],
        detail_key: str,
        entity_name: str,
        native_unit: str | None,
    ) -> None:
        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            device_sn=device_sn,
            device_cfg=device_cfg,
        )
        self._detail_key = detail_key
        self._attr_unique_id = f"{entry_id}:{device_sn}:detail:{detail_key}"
        self._attr_name = entity_name
        self._attr_native_unit_of_measurement = native_unit

        if self._detail_key == "status":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(DEVICE_STATUS_OPTIONS)
            self._attr_native_unit_of_measurement = None

    def _normalize_restored_value(self, value: Any) -> Any:
        if self._detail_key == "status":
            return map_device_status(value)
        return _safe_sensor_value(value)

    def _get_config_fallback(self) -> Any:
        if self._detail_key == "deviceType":
            return self._device_cfg.get(CONF_DEVICE_TYPE)
        return None

    def _get_live_state(self) -> tuple[bool, Any, str | None, str | None, dict[str, Any]]:
        detail_by_sn = self.coordinator.data.get("device_detail_by_sn", {})
        detail = detail_by_sn.get(self._device_sn, {})
        source_timestamp = detail.get("_fetched_at")
        raw_value = detail.get(self._detail_key)

        if raw_value is None:
            raw_value = self._get_config_fallback()
            source_timestamp = source_timestamp or self.coordinator.data.get("updated_at")

        extra_attrs: dict[str, Any] = {
            "device_sn": self._device_sn,
            "detail_key": self._detail_key,
        }

        if self._detail_key == "status":
            code = coerce_int_code(raw_value)
            mapped_value = map_device_status(raw_value)
            extra_attrs["status_code"] = code
            return mapped_value is not None, mapped_value, None, source_timestamp, extra_attrs

        if raw_value is None:
            return False, None, self._attr_native_unit_of_measurement, source_timestamp, extra_attrs

        return (
            True,
            _safe_sensor_value(raw_value),
            self._attr_native_unit_of_measurement,
            source_timestamp,
            extra_attrs,
        )


class FoxessRemainingAccessCountSensor(CoordinatorEntity, RestoreSensor, SensorEntity):
    """Shows latest API remaining calls snapshot and preserves the last valid value."""

    _attr_has_entity_name = True
    _attr_name = "FoxESS API remaining calls"
    _attr_suggested_object_id = REMAINING_CALLS_SUGGESTED_OBJECT_ID
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, *, coordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}:{REMAINING_CALLS_UNIQUE_ID_SUFFIX}"
        self._entry_id = entry_id
        self._has_valid_state = False
        self._live_available = False
        self._last_valid_native_value: Any = None
        self._last_valid_at: str | None = None
        self._source_timestamp: str | None = None
        self._restored = False
        self._stale = False
        self._api_total_calls: Any = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        last_sensor_data = await self.async_get_last_sensor_data()
        if last_sensor_data is not None and last_sensor_data.native_value is not None:
            restored_value = _coerce_numeric_sensor_value(last_sensor_data.native_value)
            if restored_value is not None:
                self._has_valid_state = True
                self._last_valid_native_value = restored_value
                attrs = last_state.attributes if last_state is not None else {}
                self._api_total_calls = attrs.get("api_total_calls")
                self._last_valid_at = attrs.get(ATTR_LAST_VALID_AT)
                self._source_timestamp = attrs.get(ATTR_SOURCE_TIMESTAMP)
                self._restored = True
                self._stale = True

        self._sync_from_live_data()

    def _sync_from_live_data(self) -> None:
        access_count = self.coordinator.data.get("access_count", {})
        remaining = _coerce_numeric_sensor_value(access_count.get("remaining"))
        self._live_available = remaining is not None

        if remaining is not None:
            self._has_valid_state = True
            self._last_valid_native_value = remaining
            self._api_total_calls = access_count.get("total")
            self._last_valid_at = self.coordinator.data.get("updated_at")
            self._source_timestamp = self.coordinator.data.get("updated_at")
            self._restored = False
            self._stale = False
        elif self._has_valid_state:
            self._stale = True

    def _handle_coordinator_update(self) -> None:
        self._sync_from_live_data()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return self._live_available or self._has_valid_state

    @property
    def native_value(self) -> Any:
        if not self._has_valid_state:
            return None
        return self._last_valid_native_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "api_total_calls": self._api_total_calls,
            ATTR_LAST_VALID_AT: self._last_valid_at,
            ATTR_SOURCE_TIMESTAMP: self._source_timestamp,
            ATTR_STALE: self._stale,
            ATTR_RESTORED: self._restored,
        }
