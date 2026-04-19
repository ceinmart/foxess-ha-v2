"""
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\\tmp\\foxess-ha.v2\\foxess-ha-v2

Shared constants for the FoxESS HA v2 integration.
"""

from homeassistant.const import Platform

# Integration metadata.
DOMAIN = "foxess_ha_v2"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

# FoxESS Open API settings.
API_BASE_URL = "https://www.foxesscloud.com"
API_LANG = "en"

SCHEMA_VERSION_FOLDER = "api.2026-04-02"
SCHEMA_BASE_DIR = "data"

# Endpoints currently used by the integration runtime.
ENDPOINT_DEVICE_LIST = "/op/v0/device/list"
ENDPOINT_DEVICE_DETAIL = "/op/v1/device/detail"
ENDPOINT_VARIABLE_CATALOG = "/op/v0/device/variable/get"
ENDPOINT_REALTIME_QUERY = "/op/v1/device/real/query"
ENDPOINT_ACCESS_COUNT = "/op/v0/user/getAccessCount"

# Config entry keys.
CONF_API_KEY = "api_key"
CONF_DEVICES = "devices"
CONF_VARIABLE_CATALOG = "variable_catalog"
CONF_ACCESS_COUNT_SNAPSHOT = "access_count_snapshot"
CONF_ENTRY_LABEL = "entry_label"
CONF_API_VERSION_FOLDER = "api_version_folder"
CONF_API_BASE_URL = "api_base_url"

CONF_DEVICE_SN = "device_sn"
CONF_DEVICE_TYPE = "device_type"
CONF_PRODUCT_TYPE = "product_type"
CONF_STATION_ID = "station_id"
CONF_STATION_NAME = "station_name"
CONF_HAS_BATTERY = "has_battery"
CONF_HAS_PV = "has_pv"
CONF_FRIENDLY_NAME = "friendly_name"
CONF_POLLING_EXPRESSION = "polling_expression"
CONF_SUPPORTED_VARIABLES = "supported_variables"

# Runtime tuning.
DEFAULT_POLLING_EXPRESSION = "5h-19h:1m;5m"
COORDINATOR_TICK_MINUTES = 1
ACCESS_COUNT_REFRESH_INTERVAL_MINUTES = 30
DEVICE_DETAIL_REFRESH_INTERVAL_MINUTES = 60
DEVICE_DETAIL_FALLBACK_REFRESH_INTERVAL_MINUTES = 15
REQUEST_TIMEOUT_SECONDS = 20
REQUEST_VERIFY_SSL = False

# Entity metadata.
REMAINING_CALLS_UNIQUE_ID_SUFFIX = "api_remaining_calls"
REMAINING_CALLS_SUGGESTED_OBJECT_ID = "foxess_api_remaining_calls"
REMAINING_CALLS_ENTITY_ID = f"sensor.{REMAINING_CALLS_SUGGESTED_OBJECT_ID}"
LEGACY_REMAINING_CALLS_ENTITY_ID = "sensor.api_remaining_calls"

# Shared entity attributes used to explain value freshness and restore status.
ATTR_LAST_VALID_AT = "last_valid_at"
ATTR_SOURCE_TIMESTAMP = "source_timestamp"
ATTR_STALE = "stale"
ATTR_RESTORED = "restored"
