# Dr.Claw 环境变量参考

> 应用内配置读取顺序：**`DRCLAW_*` > `QWENPAW_*` > `COPAW_*`**
> 实现：`src/qwenpaw/env_resolve.py`（Python）、Docker `deploy/entrypoint.sh`（Shell）

新项目请统一使用 **`DRCLAW_*`**。从 QwenPaw / CoPaw 升级时可暂时保留旧变量名，无需一次性改完。

配置方式：

- 项目根目录 `.env`（启动时自动加载）
- 系统 / 进程环境变量
- Docker Compose / Kubernetes `environment`
- 控制台「环境变量」持久化（`~/.drclaw.secret/envs.json`，**不含**工作目录等受保护项）

---

## 1. 路径与核心

| 变量 | 说明 | 默认 |
|------|------|------|
| `DRCLAW_WORKING_DIR` | 工作目录（config、workspaces、技能池等） | 无 env 时：`~/.copaw` → `~/.qwenpaw` → **`~/.drclaw`** |
| `DRCLAW_SECRET_DIR` | 密钥与 envs.json | `{WORKING_DIR}.secret` |
| `DRCLAW_CONFIG_FILE` | 配置文件名 | `config.json` |
| `DRCLAW_BACKUP_DIR` | 备份目录 | `{WORKING_DIR}.backups` |
| `DRCLAW_JOBS_FILE` | 定时任务索引 | `jobs.json` |
| `DRCLAW_CHATS_FILE` | 会话索引 | `chats.json` |
| `DRCLAW_TOKEN_USAGE_FILE` | Token 用量 | `token_usage.json` |
| `DRCLAW_HEARTBEAT_FILE` | 心跳文件名 | `HEARTBEAT.md` |
| `DRCLAW_DEBUG_HISTORY_FILE` | 调试历史 | `debug_history.jsonl` |
| `DRCLAW_CONSOLE_STATIC_DIR` | 前端静态资源目录 | 自动探测 |
| `DRCLAW_RESTORE_LOCK_TIMEOUT_SECONDS` | 备份恢复锁等待（秒） | `300` |

---

## 2. 运行 / 日志 / 网络

| 变量 | 说明 | 默认 |
|------|------|------|
| `DRCLAW_LOG_LEVEL` | 日志级别 | `info` |
| `DRCLAW_RUNNING_IN_CONTAINER` | 容器模式 | `false`（Docker 镜像内置 `1`） |
| `DRCLAW_OPENAPI_DOCS` | 暴露 `/docs` | `false` |
| `DRCLAW_CORS_ORIGINS` | CORS 源，逗号分隔 | `*` |
| `DRCLAW_DESKTOP_PORT` | 桌面版固定后端端口（Tauri + Legacy `drclaw desktop`） | **`8088`** |
| `DRCLAW_DESKTOP_API_HOST` | 桌面版 API 监听地址（Tauri sidecar 与 Legacy 桌面；`127.0.0.1` 仅本机） | **`0.0.0.0`** |
| `DRCLAW_UPLOAD_MAX_SIZE_MB` | 上传大小上限（MB） | 无限制 |
| `DRCLAW_MODEL_PROVIDER_CHECK_TIMEOUT` | 模型提供商连通检测（秒） | `5` |
| `DRCLAW_PORT` | **Docker 专用**：supervisord 监听端口 | `8088` |

内部 / 热重载：

| 变量 | 说明 |
|------|------|
| `DRCLAW_RELOAD_MODE` | CLI `--reload` 时由进程设置 |
| `DRCLAW_DESKTOP_APP` | 桌面/Tauri 模式标记（打包启动脚本设置） |
| `DRCLAW_DESKTOP_PY_RUNTIME` | 桌面版 bundled Python 路径 |
| `DRCLAW_PLUGIN_SITE` | 插件依赖 site-packages |
| `DRCLAW_BACKEND_READY` | 桌面后端就绪 stdout 前缀（Tauri 解析） |

---

## 3. 认证（Dr.Claw 默认开启）

| 变量 | 说明 | Dr.Claw 默认 |
|------|------|-------------|
| `DRCLAW_AUTH_ENABLED` | 是否启用 Web 登录 | **`true`** |
| `DRCLAW_AUTH_USERNAME` | 自动注册管理员用户名 | — |
| `DRCLAW_AUTH_PASSWORD` | 自动注册管理员密码 | — |
| `DRCLAW_KEYRING_ACCOUNT` | 系统钥匙串账户名 | 按工作目录推导 |

---

## 4. MCP 超时（企业级默认 600 秒）

| 变量 | 说明 |
|------|------|
| `DRCLAW_MCP_CONNECT_TIMEOUT_SECONDS` | 连接 / 重连 / 后台初始化 |
| `DRCLAW_MCP_READ_TIMEOUT_SECONDS` | stdio/SSE 读、**MCP 工具执行** |
| `DRCLAW_MCP_CLOSE_TIMEOUT_SECONDS` | 关闭客户端 / `close_all` |
| `DRCLAW_MCP_OAUTH_HTTP_TIMEOUT_SECONDS` | MCP OAuth HTTP |

---

## 5. LLM 限流与重试

| 变量 | 默认 |
|------|------|
| `DRCLAW_LLM_MAX_RETRIES` | `3` |
| `DRCLAW_LLM_BACKOFF_BASE` | `1.0` |
| `DRCLAW_LLM_BACKOFF_CAP` | `10.0` |
| `DRCLAW_LLM_MAX_CONCURRENT` | `10` |
| `DRCLAW_LLM_MAX_QPM` | `600` |
| `DRCLAW_LLM_RATE_LIMIT_PAUSE` | `5.0` |
| `DRCLAW_LLM_RATE_LIMIT_JITTER` | `1.0` |
| `DRCLAW_LLM_ACQUIRE_TIMEOUT` | `300` |

---

## 6. 工具守卫 / 技能安全

| 变量 | 说明 |
|------|------|
| `DRCLAW_TOOL_GUARD_ENABLED` | 启用工具守卫 |
| `DRCLAW_TOOL_GUARD_TOOLS` | 允许的工具 |
| `DRCLAW_TOOL_GUARD_DENIED_TOOLS` | 拒绝的工具 |
| `DRCLAW_TOOL_GUARD_AUTO_DENIED_RULES` | 自动拒绝规则 |
| `DRCLAW_TOOL_GUARD_APPROVAL_TIMEOUT_SECONDS` | 审批等待（默认 300s） |
| `DRCLAW_TOOL_GUARD_APPROVAL_HEARTBEAT_INTERVAL` | 审批 SSE 心跳（默认 15s） |
| `DRCLAW_SKILL_SCAN_MODE` | 技能扫描：`block` / `warn` / `off` |

技能运行时注入：

- `DRCLAW_SKILL_CONFIG_<SKILL_NAME>` — 完整 JSON 配置（大写、非字母转 `_`）

---

## 7. 记忆 / 浏览器 / 通道

| 变量 | 说明 |
|------|------|
| `DRCLAW_MEMORY_COMPACT_KEEP_RECENT` | 记忆压缩保留条数（默认 3） |
| `DRCLAW_MEMORY_COMPACT_RATIO` | 压缩比例（默认 0.7） |
| `DRCLAW_BROWSER_USE_DEFAULT` | 默认启用 browser_use |
| `DRCLAW_ENABLED_CHANNELS` | IM 通道白名单（逗号分隔） |
| `DRCLAW_DISABLED_CHANNELS` | IM 通道黑名单 |

IM 通道另有独立前缀（如 `TELEGRAM_*`、`FEISHU_*`），不在 `DRCLAW_*` 范围内。

Playwright：

- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`
- `PLAYWRIGHT_BROWSERS_PATH`

---

## 8. 技能 Hub / 市场

| 变量 | 说明 |
|------|------|
| `DRCLAW_SKILLS_HUB_BASE_URL` | Hub API 根 |
| `DRCLAW_SKILLS_HUB_*_PATH` | search / version / detail / file |
| `DRCLAW_SKILLS_HUB_HTTP_TIMEOUT` | HTTP 超时（默认 30s） |
| `DRCLAW_GITHUB_CACHE_TTL` | GitHub 缓存 TTL |
| `GITHUB_TOKEN` / `GH_TOKEN` | 拉取私有仓库 |

---

## 9. 常用第三方 API Key

| 变量 | 用途 |
|------|------|
| `OPENAI_API_KEY` | OpenAI |
| `DASHSCOPE_API_KEY` | 通义 / DashScope |
| `ANTHROPIC_API_KEY` | Anthropic |
| `OLLAMA_HOST` | Ollama 地址 |
| `LANGFUSE_SECRET_KEY` | Langfuse 观测 |

---

## 10. Docker / Compose 示例

`docker-compose.yml`：

```yaml
environment:
  - DRCLAW_AUTH_ENABLED=true
  - DRCLAW_AUTH_USERNAME=admin
  - DRCLAW_AUTH_PASSWORD=your-password
  - DRCLAW_MCP_READ_TIMEOUT_SECONDS=3600
```

构建镜像：

```bash
DRCLAW_DISABLED_CHANNELS=imessage,voice bash scripts/docker_build.sh drclaw:latest
docker run -p 8088:8088 \
  -e DRCLAW_PORT=8088 \
  -v ./drclaw-data:/app/working \
  drclaw:latest
```

---

## 11. 本地开发示例

PowerShell：

```powershell
$env:DRCLAW_WORKING_DIR = "D:\drclaw-data"
$env:DRCLAW_AUTH_ENABLED = "true"
$env:DRCLAW_LOG_LEVEL = "debug"
$env:DRCLAW_MCP_CONNECT_TIMEOUT_SECONDS = "1800"
drclaw app
```

`.env` 文件（项目根目录）：

```env
DRCLAW_WORKING_DIR=D:/drclaw-data
DRCLAW_AUTH_ENABLED=true
DRCLAW_MCP_READ_TIMEOUT_SECONDS=3600
```

---

## 12. 打包 / 桌面版

| 场景 | 变量 |
|------|------|
| macOS `.app` 启动器 | `DRCLAW_DESKTOP_APP`、`DRCLAW_LOG_LEVEL` |
| Windows 便携包 `.bat` | `DRCLAW_LOG_LEVEL`（回退 `QWENPAW_LOG_LEVEL`） |
| Tauri 注入子进程 | `DRCLAW_DESKTOP_APP`、`DRCLAW_DESKTOP_PY_RUNTIME` |

---

## 13. 代码中使用

```python
from qwenpaw.env_resolve import get_env, drclaw_env, set_env, pop_env

get_env("DRCLAW_WORKING_DIR")           # 自动回退 QWENPAW_/COPAW_
drclaw_env("WORKING_DIR")               # → "DRCLAW_WORKING_DIR"
set_env("RELOAD_MODE", "1")             # 写入 DRCLAW_RELOAD_MODE
```

`EnvVarLoader`（`constant.py`）传入 `DRCLAW_*` 键名即可，内部同样走上述解析链。

---

## 14. 未迁移项（刻意保留）

以下 **不是** 应用运行时 `DRCLAW_*` 配置，或已由安装脚本另行约定：

- `DRCLAW_HOME` — 脚本安装目录（默认 `~/.drclaw`；兼容 `QWENPAW_HOME` / `COPAW_HOME`）
- `QWENPAW_VERSION` — NSIS 打包编译常量
- `QWENPAW_PET_*` — qwenpaw-pet 插件自有变量
- `QWENPAW_INTEGRATION_COVERAGE` — 集成测试覆盖率开关
- IM 通道 `TELEGRAM_*`、`FEISHU_*` 等

仓库 `docs/` 以 Dr.Claw 运维文档为准（`DRCLAW_*`）。
