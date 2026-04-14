"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from __future__ import annotations

import hashlib
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import (
    FoxessApiAuthError,
    FoxessApiClient,
    FoxessApiRequestError,
    extract_scalar_variable_names,
)
from .const import (
    API_BASE_URL,
    CONF_ACCESS_COUNT_SNAPSHOT,
    CONF_API_BASE_URL,
    CONF_API_VERSION_FOLDER,
    CONF_DEVICE_SN,
    CONF_DEVICE_TYPE,
    CONF_DEVICES,
    CONF_ENTRY_LABEL,
    CONF_FRIENDLY_NAME,
    CONF_HAS_BATTERY,
    CONF_HAS_PV,
    CONF_POLLING_EXPRESSION,
    CONF_PRODUCT_TYPE,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    CONF_SUPPORTED_VARIABLES,
    CONF_VARIABLE_CATALOG,
    DEFAULT_POLLING_EXPRESSION,
    DOMAIN,
    SCHEMA_VERSION_FOLDER,
)
from .polling import estimate_calls_per_day, parse_polling_expression

STEP_SELECT_DEVICES = "select_devices"
STEP_DEVICE_SETTINGS = "device_settings"
FIELD_SELECTED_DEVICES = "selected_devices"
FIELD_DEVICE_NAME_PREFIX = "device_name__"
FIELD_DEVICE_POLL_PREFIX = "device_poll__"


def _mask_api_key(api_key: str) -> str:
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"


def _field_name_for_device(device_sn: str) -> str:
    return f"{FIELD_DEVICE_NAME_PREFIX}{device_sn}"


def _field_poll_for_device(device_sn: str) -> str:
    return f"{FIELD_DEVICE_POLL_PREFIX}{device_sn}"


class FoxessHaV2ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """FoxESS HA v2 config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._api_key: str = ""
        self._entry_label: str = ""
        self._discovered_devices: list[dict[str, Any]] = []
        self._selected_device_sns: list[str] = []
        self._variable_catalog: dict[str, Any] = {}
        self._variables_by_device: dict[str, list[str]] = {}
        self._access_count_snapshot: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = str(user_input[CONF_API_KEY]).strip()
            unique_ref = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]
            await self.async_set_unique_id(f"foxess:{unique_ref}")
            self._abort_if_unique_id_configured()

            api_client = FoxessApiClient(async_get_clientsession(self.hass), api_key)
            try:
                device_result = await api_client.async_list_devices()
            except FoxessApiAuthError:
                errors["base"] = "invalid_auth"
            except FoxessApiRequestError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                devices = device_result.get("devices", [])
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._api_key = api_key
                    self._entry_label = f"FoxESS ({_mask_api_key(api_key)})"
                    self._discovered_devices = devices
                    return await self.async_step_select_devices()

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_devices(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        options = self._device_option_map()

        if user_input is not None:
            selected = user_input.get(FIELD_SELECTED_DEVICES) or []
            if not selected:
                errors["base"] = "no_devices"
            else:
                self._selected_device_sns = list(selected)
                return await self.async_step_device_settings()

        schema = vol.Schema(
            {
                vol.Required(FIELD_SELECTED_DEVICES): cv.multi_select(options),
            }
        )
        return self.async_show_form(step_id=STEP_SELECT_DEVICES, data_schema=schema, errors=errors)

    async def async_step_device_settings(self, user_input: dict[str, Any] | None = None):
        selected_devices = self._selected_devices()
        try:
            await self._async_discover_variables_and_access_count()
        except FoxessApiAuthError:
            return self.async_show_form(
                step_id=STEP_DEVICE_SETTINGS,
                data_schema=self._build_device_settings_schema(selected_devices, defaults=user_input),
                errors={"base": "invalid_auth"},
            )
        except FoxessApiRequestError:
            return self.async_show_form(
                step_id=STEP_DEVICE_SETTINGS,
                data_schema=self._build_device_settings_schema(selected_devices, defaults=user_input),
                errors={"base": "cannot_connect"},
            )
        except Exception:
            return self.async_show_form(
                step_id=STEP_DEVICE_SETTINGS,
                data_schema=self._build_device_settings_schema(selected_devices, defaults=user_input),
                errors={"base": "unknown"},
            )
        errors: dict[str, str] = {}

        if user_input is not None:
            devices_cfg: dict[str, dict[str, Any]] = {}
            for device in selected_devices:
                sn = str(device.get("deviceSN"))
                name_field = _field_name_for_device(sn)
                poll_field = _field_poll_for_device(sn)
                friendly_name = str(user_input.get(name_field, "")).strip()
                polling_expression = str(user_input.get(poll_field, "")).strip()

                if not friendly_name:
                    errors[name_field] = "required"
                    continue

                try:
                    policy = parse_polling_expression(polling_expression)
                    estimated_calls = estimate_calls_per_day(policy)
                except ValueError:
                    errors[poll_field] = "invalid_polling_expression"
                    continue

                devices_cfg[sn] = {
                    CONF_DEVICE_SN: sn,
                    CONF_DEVICE_TYPE: device.get("deviceType"),
                    CONF_PRODUCT_TYPE: device.get("productType"),
                    CONF_STATION_ID: device.get("stationID"),
                    CONF_STATION_NAME: device.get("stationName"),
                    CONF_HAS_BATTERY: bool(device.get("hasBattery", False)),
                    CONF_HAS_PV: bool(device.get("hasPV", False)),
                    CONF_FRIENDLY_NAME: friendly_name,
                    CONF_POLLING_EXPRESSION: polling_expression,
                    CONF_SUPPORTED_VARIABLES: self._variables_by_device.get(sn, []),
                    "estimated_calls_24h": estimated_calls,
                }

            if not errors:
                return self.async_create_entry(
                    title=self._entry_label,
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_ENTRY_LABEL: self._entry_label,
                        CONF_API_BASE_URL: API_BASE_URL,
                        CONF_API_VERSION_FOLDER: SCHEMA_VERSION_FOLDER,
                        CONF_DEVICES: devices_cfg,
                        CONF_VARIABLE_CATALOG: self._variable_catalog,
                        CONF_ACCESS_COUNT_SNAPSHOT: self._access_count_snapshot,
                    },
                )

        schema = self._build_device_settings_schema(selected_devices, defaults=user_input)
        return self.async_show_form(step_id=STEP_DEVICE_SETTINGS, data_schema=schema, errors=errors)

    def _device_option_map(self) -> dict[str, str]:
        options: dict[str, str] = {}
        for device in self._discovered_devices:
            sn = str(device.get("deviceSN", "")).strip()
            if not sn:
                continue
            label = f"{device.get('deviceType', 'Unknown')} {sn}"
            station_name = device.get("stationName")
            if isinstance(station_name, str) and station_name.strip():
                label = f"{label} - {station_name.strip()}"
            options[sn] = label
        return options

    def _selected_devices(self) -> list[dict[str, Any]]:
        selected = set(self._selected_device_sns)
        return [device for device in self._discovered_devices if str(device.get("deviceSN")) in selected]

    async def _async_discover_variables_and_access_count(self) -> None:
        if self._variable_catalog:
            return

        api_client = FoxessApiClient(async_get_clientsession(self.hass), self._api_key)
        variable_response = await api_client.async_get_variable_catalog()
        self._variable_catalog = variable_response.get("variables", {})

        realtime_response = await api_client.async_query_realtime(self._selected_device_sns)
        by_sn = realtime_response.get("by_sn", {})

        missing_sns = [sn for sn in self._selected_device_sns if sn not in by_sn]
        for sn in missing_sns:
            single_response = await api_client.async_query_realtime([sn])
            single_by_sn = single_response.get("by_sn", {})
            if sn in single_by_sn:
                by_sn[sn] = single_by_sn[sn]

        for sn in self._selected_device_sns:
            payload = by_sn.get(sn, {})
            inferred = sorted(extract_scalar_variable_names(payload))
            if self._variable_catalog:
                inferred = [key for key in inferred if key in self._variable_catalog]
            if not inferred and self._variable_catalog:
                inferred = sorted(self._variable_catalog.keys())
            self._variables_by_device[sn] = sorted(set(inferred))

        access_response = await api_client.async_get_access_count()
        self._access_count_snapshot = {
            "total": access_response.get("total"),
            "remaining": access_response.get("remaining"),
        }

    def _build_device_settings_schema(
        self,
        selected_devices: list[dict[str, Any]],
        *,
        defaults: dict[str, Any] | None,
    ) -> vol.Schema:
        schema_fields: dict[Any, Any] = {}
        defaults = defaults or {}

        for device in selected_devices:
            sn = str(device.get("deviceSN"))
            model = str(device.get("deviceType") or "FoxESS")
            name_field = _field_name_for_device(sn)
            poll_field = _field_poll_for_device(sn)

            default_name = defaults.get(name_field) or f"{model} {sn}"
            default_poll = defaults.get(poll_field) or DEFAULT_POLLING_EXPRESSION

            schema_fields[vol.Required(name_field, default=default_name)] = str
            schema_fields[vol.Required(poll_field, default=default_poll)] = str

        return vol.Schema(schema_fields)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FoxessHaV2OptionsFlow(config_entry)


class FoxessHaV2OptionsFlow(config_entries.OptionsFlow):
    """Allows editing per-device names and polling expressions."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        devices = dict(self.config_entry.data.get(CONF_DEVICES, {}))

        if user_input is not None:
            for sn, device_cfg in devices.items():
                name_field = _field_name_for_device(sn)
                poll_field = _field_poll_for_device(sn)
                friendly_name = str(user_input.get(name_field, "")).strip()
                polling_expression = str(user_input.get(poll_field, "")).strip()

                if not friendly_name:
                    errors[name_field] = "required"
                    continue

                try:
                    policy = parse_polling_expression(polling_expression)
                    device_cfg["estimated_calls_24h"] = estimate_calls_per_day(policy)
                except ValueError:
                    errors[poll_field] = "invalid_polling_expression"
                    continue

                device_cfg[CONF_FRIENDLY_NAME] = friendly_name
                device_cfg[CONF_POLLING_EXPRESSION] = polling_expression

            if not errors:
                new_data = dict(self.config_entry.data)
                new_data[CONF_DEVICES] = devices
                self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        schema_fields: dict[Any, Any] = {}
        for sn, device_cfg in devices.items():
            friendly_name = device_cfg.get(CONF_FRIENDLY_NAME) or sn
            polling_expression = device_cfg.get(CONF_POLLING_EXPRESSION) or DEFAULT_POLLING_EXPRESSION
            schema_fields[vol.Required(_field_name_for_device(sn), default=friendly_name)] = str
            schema_fields[vol.Required(_field_poll_for_device(sn), default=polling_expression)] = str

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_fields), errors=errors)
