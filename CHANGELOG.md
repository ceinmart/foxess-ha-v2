<!--
Versao: v0.1.4
Data/hora de criacao: 2026-04-18 20:57:26
Criado por: Codex / OpenAI
Projeto/Pasta: C:\tmp\foxess-ha.v2\foxess-ha-v2
-->

# Changelog

Ordem de exibicao: decrescente (mais recente primeiro), com separacao por versao/release/pre-release.

## Serie v0.1.4

### Releases

#### v0.1.4 - 2026-04-18
Tipo: Release oficial.

- fix(sensor): `sensor.foxess_api_remaining_calls` agora persiste somente valor numerico (`int`/`float`) para melhor historico em grafico.
- fix(sensor): se a API retornar `remaining` nao numerico, o valor e descartado e o ultimo valor valido e mantido.

### Pre-releases

#### v0.1.4b4 - 2026-04-17
Tipo: Pre-release.

- fix: use minute-bucket polling to avoid skipped 1m API calls.
- fix(options-flow): align HA options flow creation API.

#### v0.1.4b3 - 2026-04-17
Tipo: Pre-release.

- fix: rename remaining calls sensor for foxess.

#### v0.1.4b2 - 2026-04-15
Tipo: Pre-release.

- fix(options-flow): use OptionsFlow base config_entry handling.

#### v0.1.4b1 - 2026-04-15
Tipo: Pre-release.

- fix: satisfy hassfest manifest sorting and config schema.
- feat: add official FoxESS brand assets.
- feat: add prerelease workflow, device detail entities, and never-unknown states.
