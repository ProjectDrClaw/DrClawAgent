---
name: QA_source_index
description: "Maps topics and keywords from user questions to Dr.Claw documentation paths and common source entry points. Intended for the QA Agent when answering installation, configuration, env vars, OpenIM, CLI, etc."
metadata:
  builtin_skill_version: "1.4"
  qwenpaw:
    emoji: "🗂️"
    requires: {}
---

# Docs and source quick index

For **install, config, and behavior** questions: classify by keyword, then open **1–2 most likely paths** instead of blind searching.

## Steps

1. Extract the topic from the user question (left column below).
2. Resolve **`$DRCLAW_ROOT`**: use `which drclaw` or `which qwenpaw`. If the path is `…/.drclaw/bin/drclaw` (or legacy `.qwenpaw/bin/qwenpaw`), the source root is three levels up (same as **guidance**); otherwise use the path the user provides.
3. Resolve **`$DOCS_DIR`**: `python3 -c "from qwenpaw.constant import DOCS_DIR; print(DOCS_DIR or '')" 2>/dev/null`. If empty, fallback to `$DRCLAW_ROOT/docs/`.
4. **Read docs first**, then the listed **source entry points**.

## Topic → docs and source

Repo `docs/` is ops-focused. Prefer:

| Topic / keywords | Prefer docs under `$DOCS_DIR/` | Source under `$DRCLAW_ROOT` |
|------------------|-------------------------------|----------------------------|
| Install, deps, first run, init | `README.md`, repo `README_zh.md` / `README.md` | `src/qwenpaw/cli/`, `pyproject.toml`, `scripts/install.*` |
| Config, config.json, env, `DRCLAW_*` | `DRCLAW_ENV_zh.md` | `src/qwenpaw/constant.py`, `src/qwenpaw/env_resolve.py`, `src/qwenpaw/config/config.py` |
| OpenIM, IM bot, channel setup | `DRCLAW_OPENIM_CHANNEL_zh.md` | `src/qwenpaw/app/channels/openim/` |
| Customization, migration, branding | `DRCLAW_CUSTOMIZATION_PLAN_zh.md` | follow doc sections |
| Docs index | `README.md` (in docs/) | `docs/` |
| Skills, skill_pool | (no dedicated md — read source) | `src/qwenpaw/agents/skill_system/`, `src/qwenpaw/agents/skills/` |
| MCP, plugins | (no dedicated md — read source) | `src/qwenpaw/app/routers/`, `plugins/` |
| Multi-agent, workspaces | (no dedicated md — read source) | `src/qwenpaw/app/routers/agents.py`, `src/qwenpaw/app/migration.py` |
| Memory | (no dedicated md — read source) | `src/qwenpaw/agents/memory/` |
| Console / frontend | (no dedicated md — read source) | `console/` |
| CLI, subcommands | `README.md` / `README_zh.md` | `src/qwenpaw/cli/` |
| Channels, sessions | OpenIM above; else source | `src/qwenpaw/app/channels/` |
| Models, API keys | `DRCLAW_ENV_zh.md` + source | `src/qwenpaw/providers/`, `src/qwenpaw/config/config.py` |
| Desktop / Tauri | (no dedicated md — read source) | `console/src-tauri/`, `scripts/pack-tauri/` |

## Conventions

- Prefer `DOCS_DIR` from `qwenpaw.constant`; fallback `$DRCLAW_ROOT/docs/`.
- CLI is **`drclaw`** (Python package name remains `qwenpaw`); data dir prefers **`~/.drclaw`** (`DRCLAW_WORKING_DIR`).
- Source paths are starting points — `read_file` / targeted `grep` next.

## Notes

- This skill does **not** replace `read_file`.
- If a path is missing locally, say so and use installed docs or a user-provided root.
