<!--
Version: v0.1.4
Created at: 2026-04-19 10:13:52 -03:00
Created by: Codex / OpenAI
Project/Folder: C:\tmp\foxess-ha.v2\foxess-ha-v2
-->

# FoxESS HA v2 - Release and live-test checklist

## 1. Before pushing

- Confirm the repository root contains:
  - `hacs.json`
  - `custom_components/foxess_ha_v2/`
- Confirm `manifest.json` contains the real repository links and `codeowners`.
- Confirm `data/api.2026-04-02/` is present inside the integration.
- Confirm no temporary files are tracked (`__pycache__`, `*.pyc`).

## 2. GitHub publication

- Create the repository: `https://github.com/ceinmart/foxess-ha-v2`
- Push the `foxess-ha-v2` folder as the repository root.
- Validate on GitHub that the repository tree is correct.

## 3. HACS installation

- In HACS, open `Custom repositories` and add `https://github.com/ceinmart/foxess-ha-v2`
- Set the repository type to `Integration`
- Install the `FoxESS HA v2` integration
- Restart Home Assistant

## 4. Functional test in Home Assistant

- Go to `Settings > Devices & Services > Add Integration > FoxESS HA v2`
- Step 1: provide the API key
- Step 2: select the devices
- Step 3: define the friendly name and polling policy
- Validate:
  - config entry creation
  - device creation
  - sensor creation
  - periodic sensor updates

## 5. Post-configuration test

- Open the integration settings (options flow)
- Change names or polling expressions
- Confirm the integration reloads without losing entities
- Verify that `diagnostics` masks the API key

## 6. Acceptance criteria for the first release

- Configuration flow completes without errors
- Sensors are updating
- No secret leakage appears in logs or diagnostics
- HACS structure is recognized and installable
