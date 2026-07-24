# Dr.Claw 定制说明

> 本文描述 **DrClawAgent** 相对上游 QwenPaw 已落地的品牌与私有化能力。
> 配套工程：`DrClawApp`（Flutter + OpenIM）、`DrClawBusiness`（业务中心）。

相关文档：

| 文档 | 说明 |
|------|------|
| [环境变量](./DRCLAW_ENV_zh.md) | 环境变量与路径 |
| [OpenIM 频道](./DRCLAW_OPENIM_CHANNEL_zh.md) | OpenIM 频道运维与联调 |
| 本文 | 品牌与私有化能力总览 |

---

## 1. 产品定位与运行时

| 项 | 说明 |
|----|------|
| 定位 | 全医疗场景的医务人员专属 AI 助手，面向私有化部署 |
| 产品名 | Dr.Claw（`PROJECT_NAME = DrClaw`） |
| 版本 | `2.0.0` |
| Python 包名 | 仍为 `qwenpaw`（import / pip / Skill metadata 不变） |
| CLI | **`drclaw`**（与 `qwenpaw` / `copaw` 同入口） |
| 工作目录 | 默认 `~/.drclaw`；若本机已有 `~/.copaw` / `~/.qwenpaw` 则沿用 |
| 环境变量 | 优先 `DRCLAW_*`；兼容只读 `QWENPAW_*` / `COPAW_*` |
| 插件兼容 | 保留 `window.QwenPaw.*`、Skill metadata 键 `qwenpaw` 等 |

---

## 2. Console 品牌与私有化 UI

| 项 | 说明 |
|----|------|
| 主色 | `#2657C9` |
| 默认语言 | 中文（`zh`） |
| 浏览器标题 | `Dr.Claw Console` |
| 登录页 | 医疗风 `pages/Login/drclaw/`；Auth 键 `drclaw_auth_*`（不存 role） |
| Header | 本地 Logo + 版本号；无社区外链 / 自动更新检测 |
| 频道 / ACP 帮助 | 文档按钮默认隐藏 |
| 侧栏临时隐藏 | 「应用」「插件管理」（路由保留，`visible: false`） |
| 静态资源 | 本地 logo / login / avatar / favicon |

---

## 3. 基础设施

### 3.1 遥测

- `utils/telemetry.py`：**空实现**（不采集、不上传）
- 保留同名 API，避免调用方报错

### 3.2 认证

- **单用户** Auth（不做多用户 / 角色隔离）
- `DRCLAW_AUTH_ENABLED` 默认 `true`

### 3.3 MCP

- 连接 / 读 / 关闭 / OAuth 相关超时默认 **600s**
- 可用 `DRCLAW_MCP_*` 覆盖

### 3.4 备份

- 备份 ID 前缀 `drclaw-…`
- 恢复锁 `.drclaw_restore.lock`（兼容旧锁文件名）

---

## 4. OpenIM 频道

- 内置频道键：`openim`（出站 WebSocket）
- Console 配置：`api_url` / `app_id` / `app_secret`
- 对接 `DrClawApp`：单聊 / 群聊（`require_mention`、`share_session_in_group`）
- 消息类型：文本、@文本、图片、语音、视频、文件
- 运维细节见 [DRCLAW_OPENIM_CHANNEL_zh.md](./DRCLAW_OPENIM_CHANNEL_zh.md)

**不做**：流式打字机、交互卡片、自动开机器人账号、App 直连 Console SSE 作主对话。

---

## 5. 聊天体验

### 5.1 运行时身份文案

注入系统上下文（`app/chats/utils.py`）：

- About：`You operate in Dr.Claw, a dedicated AI assistant for medical staff across all clinical scenarios.`
- GitHub / Docs：指向 `ProjectDrClaw/DrClawAgent`

### 5.2 助手头像与昵称

- 默认 Agent：昵称 `Dr.Claw`，头像 `/avatar.png`
- 其它 Agent：显示名 + 主题色首字母头像
- `welcome.avatar` / `nick` 置空，气泡身份由 `ChatAgentIdentityHeader` 渲染，避免与 SDK 内置头像重复
- 欢迎页：`AgentWelcomeSurface` 单独传头像

### 5.3 QA Agent

已移除内置 QA Agent（含 `qa` 模板与 `md_files/qa`）。若旧配置里仍有 `DRCLAW_QA_Agent_0.2` 等 profile，可在 Console 中手动删除。

---

## 6. 语音转写

| 项 | 说明 |
|----|------|
| 入口 | 设置 → 语音转写 |
| 后端 | `disabled` / `whisper_api` / `local_whisper` |
| 行为 | **严格按 Console 配置**：`disabled` 不转写；`whisper_api` / `local_whisper` 成功后把语音替换为文本再给模型 |
| Whisper API | 选用已配置的 OpenAI 兼容提供商（含内网 SenseVoice 等） |
| 转写模型 | Console 可配置 `transcription_model`（如 `SenseVoiceSmall`） |
| API | `GET/PUT /workspace/transcription-model` |
| 本地 Whisper | 需 `ffmpeg` + `openai-whisper`（`pip install '.[whisper]'`） |

---

## 7. 桌面端与 Docker

### 7.1 桌面（Tauri）

| 项 | 值 |
|----|-----|
| 产品名 | Dr.Claw Desktop |
| identifier | `io.drclaw.desktop` |
| 默认端口 | 8088 |
| 环境变量 | `DRCLAW_DESKTOP_*`、`DRCLAW_BACKEND_READY` 等 |
| 打包 | `DrClaw-Setup-*.exe` 等 |

无内置公网自动更新检测（Header / 桌面 updater 已收敛）。

### 7.2 Docker / Compose

| 项 | 值 |
|----|-----|
| 服务 / 容器名 | `drclaw` |
| 默认镜像 | `drclaw:latest`（发布可用 `ghcr.io/{owner}/drclaw`） |
| 数据卷 | `./drclaw-data`、`./drclaw-secrets`、`./drclaw-backups` |
| 入口 | `drclaw init` / `drclaw app` |
| 环境 | `DRCLAW_*`（含 Auth、工作目录、端口） |

可选 profile：`sensevoice`、数据库、`drclaw-business` 等（见 `docker-compose.yml`）。

---

## 8. CI 与工程面

### 8.1 保留的工作流

- 质量：`tests`、`frontend-tests`、`e2e-smoke`、`e2e-integration`、`pre-commit`、`npm-format`
- 发布：`docker-release`、`desktop-release`、`release-verify`

### 8.2 已移除（私有化不需要）

社区欢迎 Bot、官网部署、公开 PyPI、插件 OSS 市场发布、CodeQL、Dependabot、fork 验包、夜间全量等。

### 8.3 文档与网站

- 运维文档集中在 `docs/`
- 无 `website/` 目录

---

## 9. 明确不做

| 项 | 说明 |
|----|------|
| 多用户 | 无 users / role / 用户管理页 / 按角色过滤 Agent 或会话 |
| 公网社区发布 | 无官网自动发布、无公开插件 CDN 流水线 |
| OpenIM 扩展 | 流式打字机、交互卡片等（见第 4 节「不做」） |
| 应用市场默认入口 | 侧栏「应用 / 插件管理」临时隐藏 |

---

## 10. 关键路径速查

| 主题 | 路径 |
|------|------|
| 常量 / 工作目录 | `src/qwenpaw/constant.py`、`env_resolve.py` |
| 遥测 | `src/qwenpaw/utils/telemetry.py` |
| OpenIM | `src/qwenpaw/app/channels/openim/` |
| 聊天身份 | `console/src/pages/Chat/chatAgentIdentity.ts`、`HostBubbles.tsx` |
| 语音转写 | `src/qwenpaw/agents/utils/audio_transcription.py`、`console/.../VoiceTranscription/` |
| 主题色 | `console/src/App.tsx` |
| 菜单 | `console/src/layouts/registry/builtinMenu.ts` |
| Compose | `docker-compose.yml`、`deploy/` |
| CI | `.github/workflows/` |
