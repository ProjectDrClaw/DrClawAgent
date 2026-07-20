# Dr.Claw OpenIM 频道方案

> 定位：Flutter IM 为壳，医疗助手 = OpenIM **机器人账号**单聊；Agent 侧为 DrClawAgent（QwenPaw 2.0）**内置** `openim` Channel。
> 传输：机器人账号 **出站 WebSocket** 收发消息；仅要求 DrClawAgent → OpenIM 出网，无需公网回调 / Webhook。
> 依赖：`openim-sdk-core`（`pyproject.toml` 主依赖）。
> 参考：[`feishu/channel.py`](../src/qwenpaw/app/channels/feishu/channel.py)、[OpenIM 管理员 token](https://docs.openim.io/zh-Hans/restapi/apis/authenticationManagement/getAdminToken)、[openim-sdk-core](https://pypi.org/project/openim-sdk-core/)

---

## 1. 方案逻辑

### 1.1 结论

| 项 | 决定 |
|----|------|
| 产品形态 | App 用户私聊机器人，对话进入 Agent |
| Agent 接入 | 内置 Channel `openim`，运维与其它频道一致（Console / `agent.json`） |
| 收发 | 出站 WS 长连接；发消息仅 WS SDK，无 REST 降级 |
| 网络 | 仅 DrClawAgent → OpenIM；OpenIM → DrClawAgent **不需要** |
| App 主对话 | **禁止**直连 `/console/chat` SSE |
| 当前范围 | **单聊文本 + 图片 + 文件**；语音可入站；不流式；Flutter 零改动 |
| 机器人在线 | DrClawAgent **独占**登录 `app_id`（OpenIM 机器人 userID；勿在 App 再登同一号） |

### 1.2 目标

1. 本机/跨网开发只需 DrClawAgent 能访问 OpenIM，无需配置回调 URL。
2. `start()` 后台线程跑 WS；消息回调里 `_enqueue`；`stop()` 停连接与线程。
3. 医生在 Flutter 私聊机器人即可与 Agent 对话。

### 1.3 非目标（本阶段不做）

1. 流式打字机、视频消息、群聊 `@`。
2. 自动创建 OpenIM 机器人账号。
3. Flutter 独立 Agent Tab。
4. Webhook / HTTP 回调入站。

### 1.4 能力对照

| 维度 | 行为 |
|------|------|
| 入站 | 机器人出站连接 `msg_gateway` WS |
| 出站 | WS SDK `send_text` |
| `start()` | 起 WS 线程 + login + 心跳/重连 |
| 收消息 | `on_recv_new_message` → `_enqueue` |
| 发消息 | `async send()` → WS SDK |
| Console 必填 | `api_url` + `app_id` + `app_secret` |
| 公网回调 / HTTP router | 无 |
| 本地状态 | `workspace_dir/openim_ws`（SQLite 等，防多实例冲突） |

---

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│ DrClawApp                                                   │
│  登录 → 加好友(app_id) → 单聊发文本                           │
└────────────────────────────┬────────────────────────────────┘
                             │ OpenIM SDK（用户侧）
┌────────────────────────────▼────────────────────────────────┐
│ OpenIM Server                                               │
│  WS msg_gateway :10001   API :10002                         │
└────────────────────────────▲────────────────────────────────┘
                             │ 出站长连接（机器人 userID + token）
                             │ 发消息：WS SDK send
┌────────────────────────────┴────────────────────────────────┐
│ DrClawAgent — OpenIMChannel                                 │
│  start() → 后台线程：login → WS start → 重连                  │
│  on_recv → 过滤自回环 → _enqueue(native)                     │
│  consume → Agent → send()                                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 网络前置

| 方向 | 要求 |
|------|------|
| DrClawAgent → OpenIM API | 可达 `api_url`（如 `http://127.0.0.1:10002`） |
| DrClawAgent → OpenIM WS | 可达 `ws_url`（默认可由 API 主机推导为 `:10001`） |
| Flutter → OpenIM | 已有 `EnvConfig` |
| OpenIM → DrClawAgent | **不需要** |

---

## 3. 配置

Console / `agent.json` 填三项凭证即可启用；其余继承 `BaseChannelConfig`（`bot_prefix`、ACL 等）。高级项有服务端默认值，Console **不展示**。

### 3.1 `OpenIMConfig`

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `enabled` | bool | `false` | 是否启用 |
| `api_url` | str | `""` | **必填** API 根 |
| `app_id` | str | `""` | **必填**；OpenIM 机器人 userID |
| `app_secret` | str | `""` | **必填**；`share.yaml` 的 secret |
| `ws_url` | str | `""` | 可选；空则由 `api_url` 推导 |
| `admin_user_id` | str | `"imAdmin"` | 取管理员 token 的 userID |
| `platform_id` | int | `7` | 登录平台号（Linux） |
| `bot_prefix` 等 | | | 继承 `BaseChannelConfig` |

### 3.2 `agent.json` 示例

```json
{
  "channels": {
    "openim": {
      "enabled": true,
      "api_url": "http://127.0.0.1:10002",
      "app_id": "drclaw_bot",
      "app_secret": "your_share_yaml_secret"
    }
  }
}
```

如需覆盖默认行为，可在配置中补充 `ws_url`、`admin_user_id`、`platform_id`、`filter_tool_messages` 等（编辑 `agent.json` 即可，无需改 OpenIM `webhooks.yml`）。

### 3.3 环境变量（`from_env`）

| 变量 | 含义 |
|------|------|
| `OPENIM_CHANNEL_ENABLED` | `1` 启用 |
| `OPENIM_API_URL` | API 根 |
| `OPENIM_APP_ID` | 机器人 userID |
| `OPENIM_APP_SECRET` | share.yaml secret |
| `OPENIM_WS_URL` | 可选 WS 根 |
| `OPENIM_ADMIN_USER_ID` | 默认 `imAdmin` |
| `OPENIM_PLATFORM_ID` | 默认 `7` |
| `OPENIM_BOT_PREFIX` / `OPENIM_DM_POLICY` / `OPENIM_ALLOW_FROM` 等 | 与其它频道 ACL 同类 |

---

## 4. 协议与运行时

### 4.1 登录与 Token

1. `POST {api_url}/auth/get_admin_token`（`app_secret` + `admin_user_id`）
2. 用 admin 为机器人取 **用户 token**（`get_user_token`，`userID=app_id`，`platformID=platform_id`）
3. WS：`login(app_id, token)` → `start()`；等待首次 `on_connect_success`
4. 外层重连前经 `token_provider` **强制刷新** user token
5. `on_kicked_offline` → logout → 外层退避重连

入站按 `serverMsgID` / `clientMsgID` 去重；`health_check` 看真实 `is_connected`。

### 4.2 收消息 → native → 入队

回调在 **WS 线程**，轻量解析后 `_enqueue`：

```python
native = {
    "channel_id": "openim",
    "sender_id": send_id,          # 对方 userID
    "text": text,                  # 文本消息才有正文；媒体可为空
    "content_parts": [...],        # Text / Image / File / Audio
    "meta": {
        "session_type": 1,
        "content_type": 101|102|103|105,
        "server_msg_id": ...,
        "client_msg_id": ...,
    },
    "session_id": f"openim:dm:{send_id}",
}
self._enqueue(native)
```

过滤规则：

- 仅单聊（`sessionType=1`）
- 允许 `contentType`：`101` 文本、`102` 图片、`103` 语音、`105` 文件
- `send_id != app_id`（防自回环）
- 文本须非空；媒体须能解析出可访问 URL

`build_agent_request_from_native` 与现有 BaseChannel 路径复用。

### 4.3 发消息

**文本** `send(to_handle, text, meta)`：

1. WS SDK `send_text`
2. `bot_prefix` 拼在正文前
3. 未连接或发送失败直接报错，**不**走 REST

**媒体** `send_media` / `send_content_parts`：

1. 文本与媒体分开发送（不把 `[Image: url]` 拼进正文）
2. 图片：本地路径 → `send_image`；HTTP URL → `send_image_by_url`
3. 文件：本地路径 → `send_file`；HTTP URL → `send_file_by_url`
4. 语音出站：SDK 需 `duration`，当前按文件发送

### 4.4 WS 客户端

使用 PyPI `openim-sdk-core` 的 `OpenIMWSSDK`（gob + gzip + protobuf、心跳、重连）。联调探针：

```bash
# Windows PowerShell 示例
$env:OPENIM_API_URL="http://127.0.0.1:10002"
$env:OPENIM_WS_URL="ws://127.0.0.1:10001"
$env:OPENIM_APP_SECRET="your_share_yaml_secret"
$env:OPENIM_APP_ID="drclaw_bot"
$env:OPENIM_PLATFORM_ID="7"
# 可选：验证发消息
# $env:OPENIM_RECV_ID="对方userID"
python scripts/probe_openim_ws.py
```

### 4.5 生命周期

| 方法 | 行为 |
|------|------|
| `from_config` / `from_env` | 读配置，构造 client；**不**在构造时连网 |
| `async start` | 校验配置 → 取 token → 起 `_ws_thread` → `_run_ws_forever` |
| `async stop` | 设 stop flag → 关 SDK → join 线程 |
| `async send` | 仅当 enabled 且 WS 已连接 |

并发：WS 回调线程只 `enqueue`；Agent 消费在 ChannelManager 事件循环。

---

## 5. 代码结构

```
src/qwenpaw/app/channels/openim/
├── __init__.py
├── constants.py
├── client.py          # REST：仅 admin / user token
├── ws_client.py       # WS 封装（login / start / stop / send / on_message）
└── channel.py         # OpenIMChannel：start / stop / enqueue / send
```

| 主题 | 路径 |
|------|------|
| OpenIM Channel | `src/qwenpaw/app/channels/openim/` |
| BaseChannel | `src/qwenpaw/app/channels/base.py` |
| ChannelManager | `src/qwenpaw/app/channels/manager.py` |
| 配置 | `src/qwenpaw/config/config.py` → `OpenIMConfig` |
| doctor | `src/qwenpaw/cli/doctor_checks.py`（凭证完整性 + `openim_sdk`） |
| Console 表单 | `console/src/pages/Control/Channels/components/ChannelDrawer.tsx` |
| 探针 | `scripts/probe_openim_ws.py` |
| 单测 | `tests/unit/channels/test_openim_channel.py` |

---

## 6. Console

顶部说明：长连接收消息，无需公网回调。表单仅三项（英文标签）：

- `API URL`
- `App ID`
- `App Secret`

公共项（抽屉底部）：`enabled` / `bot_prefix` / filter / ACL。`ws_url`、`platform_id`、`admin_user_id` 不在 UI 暴露，走默认或 `agent.json`。

---

## 7. 范围与后续

| 阶段 | 内容 | 出口 |
|------|------|------|
| 当前 | 单聊文本 + 图片 + 文件收发；语音可入站；断线重连 | App 私聊文本/图片/文件可与 Agent 互通 |
| 后续 | 视频消息、语音原生出站（带 duration） | — |
| 后续 | 群聊 + `require_mention` | — |

---

## 8. 验证与排障

### 8.1 单元

- `parse_text_content` / 图片文件解析 / 自回环过滤
- mock `ws_client`：文本与媒体入队断言 `_enqueue`
- mock `send` / `send_media`：仅 WS SDK 路径

### 8.2 手工联调

1. OpenIM 创建机器人账号（**不要**用该号登录 Flutter）
2. Console 或 `agent.json` 填 `api_url` / `app_id` / `app_secret` 并启用
3. 启动 DrClawAgent，日志出现 WS connected / login ok
4. Flutter 用户加好友 → 发「你好」→ 收到 Agent 回复
5. 再测发图片 / 文件，确认 Agent 能收到并可回图或回文件
6. 断开再恢复 OpenIM 网络，确认自动重连后仍可聊

### 8.3 故障对照

| 现象 | 排查 |
|------|------|
| 无法 login | user token / `platform_id` / 机器人是否存在 |
| 连不上 WS | `ws_url` 或 API 主机推导、防火墙、路径是否含 `/msg_gateway` |
| 收不到消息 | 是否被踢下线；是否另一处登录了同一机器人 |
| 无限自聊 | 未过滤 `send_id == robot` |
| 能收不能发 | WS 是否在线；SDK `send_text` 日志 |

---

## 9. 安全与运维

- `app_secret`、user token 仅服务端；Flutter 不持有机器人 token
- 机器人账号 **单端在线**（DrClawAgent）
- `data_dir` 按 agent workspace 隔离
- ACL：`dm_policy` / `allow_from` 与其它 Channel 相同
- 回滚：`channels.openim.enabled=false`；不影响人–人 IM
