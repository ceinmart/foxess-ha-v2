"""
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:05:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\\tmp\\foxess-ha.v2
"""

from homeassistant.const import Platform

DOMAIN = "foxess_ha_v2"
PLATFORMS = [Platform.SENSOR]

API_BASE_URL = "https://www.foxesscloud.com"
API_LANG = "en"

SCHEMA_VERSION_FOLDER = "api.2026-04-02"
SCHEMA_BASE_DIR = "data"

ENDPOINT_DEVICE_LIST = "/op/v0/device/list"
ENDPOINT_VARIABLE_CATALOG = "/op/v0/device/variable/get"
ENDPOINT_REALTIME_QUERY = "/op/v1/device/real/query"
ENDPOINT_ACCESS_COUNT = "/op/v0/user/getAccessCount"

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

DEFAULT_POLLING_EXPRESSION = "5h-19h:1m;5m"
COORDINATOR_TICK_MINUTES = 1
ACCESS_COUNT_REFRESH_INTERVAL_MINUTES = 30
REQUEST_TIMEOUT_SECONDS = 20
REQUEST_VERIFY_SSL = False
