---
name: QA_source_index
description: "将用户问题中的主题、关键词映射到 Dr.Claw 文档路径与常见源码入口，减少盲目搜索。适用于 QA Agent 在回答安装、配置、环境变量、OpenIM、CLI 等问题时快速选定要读的文件。"
metadata:
  builtin_skill_version: "1.4"
  qwenpaw:
    emoji: "🗂️"
    requires: {}
---

# 文档与源码速查

回答 **安装、配置、行为原理** 类问题时，先 **按关键词归类**，再按下表 **打开 1～2 个最可能命中的路径** 阅读，避免长时间无目的遍历。

## 使用步骤

1. 从用户问题中提取主题（对照下表左列或同类词）。
2. 解析 **`$DRCLAW_ROOT`**：以 `which drclaw` 或 `which qwenpaw` 得到可执行路径；若为 `…/.drclaw/bin/drclaw`（或兼容的 `.qwenpaw/bin/qwenpaw`）则源码根为其上三级目录（与 **guidance** skill 一致）；否则结合用户给出的安装路径判断。
3. 先解析 **`$DOCS_DIR`**：执行 `python3 -c "from qwenpaw.constant import DOCS_DIR; print(DOCS_DIR or '')" 2>/dev/null`。若返回有效路径则直接使用；否则 fallback 到 `$DRCLAW_ROOT/docs/`。
4. **先读文档**，仍不足再读表中 **源码入口**。

## 主题 / 关键词 → 优先文档与源码

当前仓库 `docs/` 以运维文档为主。优先按下表阅读：

| 主题或关键词（示例） | 优先文档（`$DOCS_DIR/`） | 常见源码入口（相对 `$DRCLAW_ROOT`） |
|---------------------|--------------------------|-------------------------------------|
| 安装、依赖、首次使用、init | `README.md`、仓库根 `README_zh.md` | `src/qwenpaw/cli/`、`pyproject.toml`、`scripts/install.*` |
| 配置、config.json、环境变量、`DRCLAW_*` | `DRCLAW_ENV_zh.md` | `src/qwenpaw/constant.py`、`src/qwenpaw/env_resolve.py`、`src/qwenpaw/config/config.py` |
| OpenIM、IM 机器人、频道联调 | `DRCLAW_OPENIM_CHANNEL_zh.md` | `src/qwenpaw/app/channels/openim/` |
| 定制、迁移、品牌、私有化改造 | `DRCLAW_CUSTOMIZATION_PLAN_zh.md` | 按文档章节对应路径 |
| 文档索引 | `README.md`（docs 目录） | `docs/` |
| 技能、SKILL、skill_pool | （无专题 md 时直接读源码） | `src/qwenpaw/agents/skill_system/`、`src/qwenpaw/agents/skills/` |
| MCP、插件 | （无专题 md 时直接读源码） | `src/qwenpaw/app/routers/`、`plugins/` |
| 多智能体、工作区、agent | （无专题 md 时直接读源码） | `src/qwenpaw/app/routers/agents.py`、`src/qwenpaw/app/migration.py` |
| 记忆、MEMORY | （无专题 md 时直接读源码） | `src/qwenpaw/agents/memory/` |
| 控制台、前端 | （无专题 md 时直接读源码） | `console/` |
| 命令行、子命令 | `README_zh.md` | `src/qwenpaw/cli/` |
| 频道、会话 | OpenIM 见上；其它频道读源码 | `src/qwenpaw/app/channels/` |
| 模型、API Key | `DRCLAW_ENV_zh.md` + 源码 | `src/qwenpaw/providers/`、`src/qwenpaw/config/config.py` |
| 桌面客户端、Tauri | （无专题 md 时直接读源码） | `console/src-tauri/`、`scripts/pack-tauri/` |

## 约定

- 优先使用 `qwenpaw.constant` 中的 `DOCS_DIR`，失败时 fallback 到 `$DRCLAW_ROOT/docs/`。
- CLI 入口为 **`drclaw`**（Python 包名仍为 `qwenpaw`）；用户数据目录优先 **`~/.drclaw`**（`DRCLAW_WORKING_DIR`）。
- 表中 **源码入口** 为起点；应用 `read_file` 或局部 `grep` 缩小到具体符号。

## 注意

- 本 skill **不替代** `read_file`：锁定候选路径后应立即读取并核对。
- 若某路径在本地不存在，以已安装文档或用户提供的根目录为准，并明确告知依据路径。
