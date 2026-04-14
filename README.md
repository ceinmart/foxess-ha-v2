# FoxESS HA v2

Custom integration for Home Assistant based on locally versioned FoxESS Open API schemas.

## Scope of this MVP

- Config flow in 3 steps.
- Multi-device setup under one API key.
- Variable discovery per device.
- Dynamic polling expression per device (`5h-19h:1m;5m` format).
- Sensor entities generated from discovered variables.
- HACS-compatible package structure.

## Repository structure

```text
foxess-ha-v2/
  hacs.json
  custom_components/
    foxess_ha_v2/
      __init__.py
      manifest.json
      config_flow.py
      coordinator.py
      api.py
      sensor.py
      diagnostics.py
      const.py
      polling.py
      strings.json
      translations/
      data/
        api.2026-04-02/
```

## Notes

- FoxESS API schemas are embedded from local project artifacts.
- API key is masked in diagnostics output.
- This package is designed to evolve incrementally after MVP validation.

## Debug logging (Home Assistant)

To increase integration logs during troubleshooting, add this block in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.foxess_ha_v2: debug
```
