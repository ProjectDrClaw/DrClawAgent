# -*- coding: utf-8 -*-
"""OpenIM channel constants."""

from __future__ import annotations

# OpenIM 内容类型（与 openim-sdk-core ContentType 对齐）
CONTENT_TYPE_TEXT = 101
CONTENT_TYPE_PICTURE = 102
CONTENT_TYPE_SOUND = 103
CONTENT_TYPE_VIDEO = 104
CONTENT_TYPE_FILE = 105
CONTENT_TYPE_AT_TEXT = 106
CONTENT_TYPE_CUSTOM = 110

# App 自定义消息类型（与 DrClawApp CustomMessageType 对齐）
CUSTOM_TYPE_TOOL_GUARD_APPROVAL = 920
CUSTOM_TYPE_TOOL_CALL = 921
CUSTOM_TYPE_TOOL_RESULT = 922
CUSTOM_TYPE_THINKING = 923

# 入站：单聊/群聊文本、@文本、图片、语音、视频、文件
INBOUND_CONTENT_TYPES = frozenset(
    {
        CONTENT_TYPE_TEXT,
        CONTENT_TYPE_PICTURE,
        CONTENT_TYPE_SOUND,
        CONTENT_TYPE_VIDEO,
        CONTENT_TYPE_FILE,
        CONTENT_TYPE_AT_TEXT,
    },
)

SESSION_TYPE_DM = 1
SESSION_TYPE_GROUP = 2
SESSION_TYPE_SUPER_GROUP = 3

INBOUND_SESSION_TYPES = frozenset(
    {
        SESSION_TYPE_DM,
        SESSION_TYPE_GROUP,
        SESSION_TYPE_SUPER_GROUP,
    },
)

# OpenIM @全体成员约定标记
AT_ALL_TAG = "AtAllTag"

# admin / user token 提前刷新缓冲（秒）
TOKEN_REFRESH_SKEW_S = 300

DEFAULT_HTTP_TIMEOUT_S = 30.0

# WS 外层重连退避（SDK 内部也有 auto_reconnect）
WS_INITIAL_RETRY_DELAY = 1.0
WS_BACKOFF_FACTOR = 2.0
WS_MAX_RETRY_DELAY = 60.0

# 断连期间 warning 限频；持续断连超过此时长则重建 SDK 会话
WS_DISCONNECT_WARN_INTERVAL_S = 60.0
WS_STALE_DISCONNECT_S = 120.0

# start() 等待首次 connect_success 的超时
WS_START_CONNECT_TIMEOUT_S = 30.0

# 入站消息去重窗口
PROCESSED_MSG_IDS_MAX = 2000

# 出站语音/视频缺省时长（秒）；SDK 要求 duration > 0
DEFAULT_MEDIA_DURATION_S = 1
