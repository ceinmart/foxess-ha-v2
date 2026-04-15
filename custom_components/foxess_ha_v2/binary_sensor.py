"""
Versao: v0.1.4b1
Data/hora de criacao: 2026-04-15 10:20:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_LAST_VALID_AT,
    ATTR_RESTORED,
    ATTR_SOURCE_TIMESTAMP,
    ATTR_STALE,
    CONF_DEVICE_SN,
    CONF_DEVICE_TYPE,
    CONF_DEVICES,
    CONF_FRIENDLY_NAME,
    CONF_HAS_BATTERY,
    CONF_PRODUCT_TYPE,
    CONF_STATION_NAME,
    DOMAIN,
)


def _build_device_info(entry_id: str, device_sn: str, device_cfg: dict) -> DeviceInfo:
    friendly_name = device_cfg.get(CONF_FRIENDLY_NAME) or device_sn
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}:{device_sn}")},
        name=friendly_name,
        manufacturer="FoxESS",
        model=device_cfg.get(CONF_DEVICE_TYPE) or device_cfg.get(CONF_PRODUCT_TYPE),
        serial_number=device_cfg.get(CONF_DEVICE_SN, device_sn),
        suggested_area=device_cfg.get(CONF_STATION_NAME),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    devices = entry.data.get(CONF_DEVICES, {})

    async_add_entities(
        [
            FoxessHasBatteryBinarySensor(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                device_sn=sn,
                device_cfg=device_cfg,
            )
            for sn, device_cfg in devices.items()
        ]
    )


class FoxessHasBatteryBinarySensor(CoordinatorEntity, RestoreEntity, BinarySensorEntity):
    """Reports battery capability without regressing to unknown after a valid read."""

    _attr_has_entity_name = True
    _attr_name = "Has battery"

    def __init__(self, *, coordinator, entry_id: str, device_sn: str, device_cfg: dict) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._device_sn = device_sn
        self._device_cfg = device_cfg
        self._attr_unique_id = f"{entry_id}:{device_sn}:detail:hasBattery"
        self._has_valid_state = False
        self._live_available = False
        self._last_valid_is_on: bool | None = None
        self._last_valid_at: str | None = None
        self._source_timestamp: str | None = None
        self._restored = False
        self._stale = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in (STATE_ON, STATE_OFF):
            self._has_valid_state = True
            self._last_valid_is_on = last_state.state == STATE_ON
            self._last_valid_at = last_state.attributes.get(ATTR_LAST_VALID_AT)
            self._source_timestamp = last_state.attributes.get(ATTR_SOURCE_TIMESTAMP)
            self._restored = True
            self._stale = True

        self._sync_from_live_data()

    def _sync_from_live_data(self) -> None:
        detail_by_sn = self.coordinator.data.get("device_detail_by_sn", {})
        detail = detail_by_sn.get(self._device_sn, {})
        raw_value = detail.get("hasBattery")
        source_timestamp = detail.get("_fetched_at")

        if raw_value is None:
            raw_value = self._device_cfg.get(CONF_HAS_BATTERY)
            source_timestamp = source_timestamp or self.coordinator.data.get("updated_at")

        self._live_available = isinstance(raw_value, bool)
        if self._live_available:
            self._has_valid_state = True
            self._last_valid_is_on = raw_value
            self._last_valid_at = self.coordinator.data.get("updated_at")
            self._source_timestamp = source_timestamp
            self._restored = False
            self._stale = False
        elif self._has_valid_state:
            self._stale = True

    def _handle_coordinator_update(self) -> None:
        self._sync_from_live_data()
        super()._handle_coordinator_update()

    @property
    def device_info(self) -> DeviceInfo:
        return _build_device_info(self._entry_id, self._device_sn, self._device_cfg)

    @property
    def available(self) -> bool:
        return self._live_available or self._has_valid_state

    @property
    def is_on(self) -> bool | None:
        if not self._has_valid_state:
            return None
        return self._last_valid_is_on

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "device_sn": self._device_sn,
            "detail_key": "hasBattery",
            ATTR_LAST_VALID_AT: self._last_valid_at,
            ATTR_SOURCE_TIMESTAMP: self._source_timestamp,
            ATTR_STALE: self._stale,
            ATTR_RESTORED: self._restored,
        }
