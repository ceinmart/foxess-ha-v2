<!--
Version: v0.1.5
Created at: 2026-04-20 10:08:02 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\tmp\foxess-ha.v2\foxess-ha-v2
-->

# Changelog

Entries are listed in descending order, newest first, grouped by version and release type.

## Series v0.1.5

### Releases

#### v0.1.5 - 2026-04-20
Type: Official release.

- docs: rewrite the public README in English with installation, API, entity, polling, quota, and timestamp guidance.
- docs: add Python docstrings and targeted inline comments so the integration is easier to review and maintain.
- fix(i18n): move integration title and flow strings to `translations/*.json` and remove `strings.json` for better custom-integration compatibility.
- fix(security): enable TLS certificate verification by default for FoxESS API requests.
- fix(api): improve transport-layer error messages for TLS certificate and SSL handshake failures.

## Series v0.1.4

### Releases

#### v0.1.4 - 2026-04-18
Type: Official release.

- fix(sensor): `sensor.foxess_api_remaining_calls` now persists numeric values only (`int`/`float`) for cleaner chart history.
- fix(sensor): if the API returns a non-numeric `remaining` value, it is discarded and the last valid value is kept.

### Pre-releases

#### v0.1.4b4 - 2026-04-17
Type: Pre-release.

- fix: use minute-bucket polling to avoid skipped 1m API calls.
- fix(options-flow): align HA options flow creation API.

#### v0.1.4b3 - 2026-04-17
Type: Pre-release.

- fix: rename remaining calls sensor for foxess.

#### v0.1.4b2 - 2026-04-15
Type: Pre-release.

- fix(options-flow): use OptionsFlow base config_entry handling.

#### v0.1.4b1 - 2026-04-15
Type: Pre-release.

- fix: satisfy hassfest manifest sorting and config schema.
- feat: add official FoxESS brand assets.
- feat: add prerelease workflow, device detail entities, and never-unknown states.
