<!--
Versao: v0.1.0
Data/hora de criacao: 2026-04-14 16:35:00
Criado por: Codex / OpenAI
Projeto/Pasta: C:\tmp\foxess-ha.v2
-->

# FoxESS HA v2 - Checklist de release e teste real

## 1) Antes do push

- Confirmar estrutura na raiz do repositorio:
  - `hacs.json`
  - `custom_components/foxess_ha_v2/`
- Confirmar `manifest.json` com links reais do repo e `codeowners`.
- Confirmar que `data/api.2026-04-02/` esta presente na integracao.
- Confirmar que nao ha arquivos temporarios versionados (`__pycache__`, `*.pyc`).

## 2) Publicacao no GitHub

- Criar repositorio: `https://github.com/ceinmart/foxess-ha-v2`
- Fazer push da pasta `foxess-ha-v2` como raiz do repositorio.
- Validar no GitHub que a arvore esta correta.

## 3) Instalacao via HACS

- Em HACS: `Custom repositories` -> adicionar `https://github.com/ceinmart/foxess-ha-v2`
- Tipo: `Integration`
- Instalar a integracao `FoxESS HA v2`
- Reiniciar o Home Assistant

## 4) Teste funcional no Home Assistant

- Ir em `Settings > Devices & Services > Add Integration > FoxESS HA v2`
- Passo 1: informar API key
- Passo 2: selecionar devices
- Passo 3: definir nome e polling
- Validar:
  - criacao da config entry
  - criacao de devices
  - criacao de sensores
  - atualizacao periodica dos sensores

## 5) Teste de pos-configuracao

- Abrir engrenagem da integracao (options flow)
- Alterar nomes/polling
- Confirmar reload sem perder entidades
- Verificar se `diagnostics` mascara API key

## 6) Criterios de aceite para primeira release

- Fluxo de configuracao concluido sem erro
- Sensores atualizando
- Sem vazamento de segredo em logs/diagnostics
- Estrutura HACS reconhecida e instalavel
