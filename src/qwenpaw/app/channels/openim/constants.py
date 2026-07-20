# -*- coding: utf-8 -*-
"""OpenIM channel constants."""

from __future__ import annotations

# OpenIM 内容类型（与 openim-sdk-core ContentType 对齐）
CONTENT_TYPE_TEXT = 101
CONTENT_TYPE_PICTURE = 102
CONTENT_TYPE_SOUND = 103
CONTENT_TYPE_VIDEO = 104
CONTENT_TYPE_FILE = 105

# M1：单聊文本 + 图片 + 文件 + 语音（入站）
INBOUND_CONTENT_TYPES = frozenset(
    {
        CONTENT_TYPE_TEXT,
        CONTENT_TYPE_PICTURE,
        CONTENT_TYPE_SOUND,
        CONTENT_TYPE_FILE,
    },
)

SESSION_TYPE_DM = 1

# admin / user token 提前刷新缓冲（秒）
TOKEN_REFRESH_SKEW_S = 300

DEFAULT_HTTP_TIMEOUT_S = 30.0

# WS 外层重连退避（SDK 内部也有 auto_reconnect）
WS_INITIAL_RETRY_DELAY = 1.0
WS_BACKOFF_FACTOR = 2.0
WS_MAX_RETRY_DELAY = 60.0

# start() 等待首次 connect_success 的超时
WS_START_CONNECT_TIMEOUT_S = 30.0

# 入站消息去重窗口
PROCESSED_MSG_IDS_MAX = 2000
