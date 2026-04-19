<!--
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\tmp\foxess-ha.v2\foxess-ha-v2
-->

# FoxESS HA v2

![FoxESS HA v2 logo](custom_components/foxess_ha_v2/brand/logo.png)

FoxESS HA v2 is a Home Assistant custom integration that connects to the FoxESS Cloud Open API, discovers every device available under one API key, and creates Home Assistant devices and entities dynamically from the variables that FoxESS actually exposes for each serial number. For project history, see the [changelog](./CHANGELOG.md) and the published [GitHub releases](https://github.com/ceinmart/foxess-ha-v2/releases).

## What this integration does

- Supports a config flow and HACS-compatible repository layout.
- Discovers multiple FoxESS devices from a single API key.
- Builds one Home Assistant device per FoxESS serial number.
- Creates sensor entities dynamically from the FoxESS variable catalog and live payloads.
- Adds detail entities such as device type, firmware version, capacity, status, and battery capability.
- Lets you configure a polling policy per device to balance freshness and API usage.
- Preserves the last valid value when FoxESS temporarily omits data, so entities do not fall back to `unknown` unnecessarily.

## Official FoxESS links

- FoxESS website: [https://www.fox-ess.com/](https://www.fox-ess.com/)
- FoxESS Cloud v1 / legacy web portal: [https://www.foxesscloud.com/login?redirect=%2F](https://www.foxesscloud.com/login?redirect=%2F)
- FoxESS Cloud v2 web portal: [https://www.foxesscloud.com/v2/login](https://www.foxesscloud.com/v2/login)
- FoxESS Cloud base URL used by this integration: [https://www.foxesscloud.com](https://www.foxesscloud.com)

## Installation

1. Add this repository to HACS as a custom repository of type `Integration`.
2. Download `FoxESS HA v2` from HACS.
3. Restart Home Assistant.
4. Go to `Settings > Devices & services`.
5. Add the `FoxESS HA v2` integration.
6. Paste your FoxESS Open API key when prompted.

## API key

This integration needs a FoxESS Open API key, not your account password.

The most reliable way to obtain that key is through the FoxESS Cloud v1 web portal:

1. Sign in to the legacy portal at [foxesscloud.com/login](https://www.foxesscloud.com/login?redirect=%2F).
2. Open the area where FoxESS exposes Open API access for your account.
3. Create or copy the API key.
4. Paste that key into the Home Assistant config flow.

At the time this README was updated on April 19, 2026, project validation still depended on the Cloud v1 interface for API key generation. The Cloud v2 portal was not exposing the same key-creation option during the latest documentation review. If FoxESS later adds that feature to Cloud v2, the integration should continue to work as long as the key is a valid Open API token.

## API base URL and endpoints used

Base URL:

- `https://www.foxesscloud.com`

Endpoints consulted by the integration:

| Method | Endpoint | Why it is used |
| --- | --- | --- |
| `POST` | `/op/v0/device/list` | Discover every device visible to the API key during setup. |
| `GET` | `/op/v1/device/detail` | Read static or slower-changing metadata such as device type, firmware version, capacity, status, and battery capability. |
| `GET` | `/op/v0/device/variable/get` | Load the FoxESS variable catalog so entities can use labels and units when available. |
| `POST` | `/op/v1/device/real/query` | Fetch live values for one or more device serial numbers. |
| `GET` | `/op/v0/user/getAccessCount` | Read the daily API quota snapshot, including remaining calls. |

The integration authenticates with the FoxESS Open API headers expected by the platform: `token`, `timestamp`, `signature`, and `lang`. The `signature` is generated from the request path, API key, and timestamp in the format currently expected by FoxESS.

## How devices are identified

FoxESS devices are identified by their serial number, exposed by FoxESS as `deviceSN`.

- During setup, `POST /op/v0/device/list` returns the candidate devices for the API key.
- The integration stores one configuration block per selected `deviceSN`.
- In Home Assistant, one device is created per selected serial number.
- Entity unique IDs are derived from the config entry ID plus the device serial number and either a variable name or a detail key.

In practice, `deviceSN` is the stable key that ties together discovery, live updates, detail lookups, entity registry IDs, and restored state.

## How entities are identified and generated

The entity model is intentionally dynamic because FoxESS does not expose the same variable set for every device.

During setup, the integration does the following:

1. Reads the global variable catalog from `GET /op/v0/device/variable/get`.
2. Reads live payloads from `POST /op/v1/device/real/query` for the devices selected in the config flow.
3. Merges both sources so the integration can keep FoxESS labels and units when they exist, while also learning variables that appear only in live payloads.
4. Stores the final supported variable list per device in the config entry.

At entity creation time, the integration generates:

- One sensor per supported live variable for each selected device.
- One detail sensor per selected device for `deviceType`, `masterVersion`, `capacity`, and `status`.
- One binary sensor per selected device for `hasBattery`.
- One integration-level sensor for the remaining FoxESS API calls.

Entity names follow this priority:

1. English label from the FoxESS variable catalog.
2. English label discovered in live payloads.
3. Raw FoxESS variable name as a safe fallback.

Entity classes are inferred from units and variable names when possible. For example, power units are mapped to power sensors, energy units to total-increasing energy sensors, and `runningState` / `status` are translated from FoxESS codes into readable enum values.

## How each device gets its available entities

Each selected device is configured independently.

- The config flow stores a friendly name for the device.
- The config flow stores a polling expression for the device.
- The integration stores the supported variable list for that exact serial number.
- At runtime, entities are created only from the variables associated with that device.

This matters because two FoxESS devices under the same account can expose different variable sets, different units, or different capabilities.

## Polling strategy and API call control

The integration is designed to reduce unnecessary API traffic instead of polling everything at the same rate.

Each device has a polling expression in the format:

- `5h-19h:1m;5m`

Meaning:

- Poll every `1` minute between `05:00` and `19:00`.
- Poll every `5` minutes outside that time window.

How polling is controlled internally:

- The coordinator wakes up once per minute.
- Each device is checked against its own polling policy.
- Only devices that are due are added to the next real-time request.
- Due devices are queried together in one grouped request whenever possible.
- If FoxESS omits one device from a grouped response, the integration retries that missing device individually.
- Device detail snapshots are refreshed less often than live telemetry.
- API quota data is refreshed on a slower schedule because it changes less frequently.

Current refresh behavior in the code:

- Coordinator tick: every `1` minute.
- Access-count refresh: every `30` minutes.
- Full device-detail snapshot refresh: every `60` minutes.
- Device-detail fallback refresh after missing realtime data: every `15` minutes.

## How to monitor the daily API budget

The integration creates a sensor named:

- `sensor.foxess_api_remaining_calls`

This sensor shows the remaining FoxESS API calls returned by `GET /op/v0/user/getAccessCount`.

Useful attributes on that sensor:

- `api_total_calls`: the quota size returned by FoxESS.
- `last_valid_at`: when Home Assistant last received a valid quota value.
- `source_timestamp`: when the integration recorded the current snapshot.
- `stale`: `true` when Home Assistant is showing the last good value because a fresh value was not available.
- `restored`: `true` when the current value was restored from Home Assistant state storage after a restart.

If you need to reduce API consumption, open the integration options and slow down the polling expression for one or more devices.

## How to find the last data timestamp from FoxESS Cloud

For live telemetry entities, the easiest way is to inspect any variable sensor and read the `source_timestamp` attribute.

- That attribute is populated from the FoxESS payload field named `time`.
- It represents the timestamp carried by FoxESS for that live data snapshot.
- `last_valid_at` is different: it tells you when Home Assistant accepted the value, not when FoxESS says the cloud snapshot was produced.

Important nuance:

- For variable sensors, `source_timestamp` comes from FoxESS live data.
- For detail entities such as `deviceType`, `status`, or `hasBattery`, FoxESS detail responses do not expose the same live-data timestamp, so `source_timestamp` reflects when the integration fetched the detail snapshot instead.

If an entity has `stale: true`, Home Assistant is currently holding the last valid value instead of a freshly received FoxESS value.

## Local API schema snapshot

This repository keeps a locally versioned FoxESS Open API schema snapshot under:

- `custom_components/foxess_ha_v2/data/api.2026-04-02/`

That snapshot is used as a stable project reference while the integration evolves, but runtime requests still go directly to the official FoxESS Cloud API endpoints listed above.

## Diagnostics and debug logging

- The API key is masked in diagnostics output.
- The integration keeps coordinator state available in diagnostics to help with troubleshooting.

To increase integration logs during troubleshooting, add this block to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.foxess_ha_v2: debug
```
