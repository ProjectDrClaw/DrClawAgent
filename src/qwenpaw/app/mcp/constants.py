# -*- coding: utf-8 -*-
"""MCP 超时默认值（企业级 MCP 启动与工具执行可能较慢）。"""

from __future__ import annotations

from ...env_resolve import drclaw_env, get_env

# 默认 10 分钟；可通过环境变量覆盖（秒）
_DEFAULT_SECONDS = 600.0


def _env_timeout(suffix: str, default: float = _DEFAULT_SECONDS) -> float:
    raw = get_env(drclaw_env(suffix), "")
    if not raw or not raw.strip():
        return default
    try:
        value = float(raw.strip())
        return value if value > 0 else default
    except ValueError:
        return default


# 连接 / 重连 / 后台初始化
MCP_CONNECT_TIMEOUT_SECONDS = _env_timeout("MCP_CONNECT_TIMEOUT_SECONDS")

# stdio 读超时、HTTP SSE 读超时、工具执行超时
MCP_READ_TIMEOUT_SECONDS = _env_timeout("MCP_READ_TIMEOUT_SECONDS")

# close_all 整体等待、单客户端 lifecycle 关闭
MCP_CLOSE_TIMEOUT_SECONDS = _env_timeout("MCP_CLOSE_TIMEOUT_SECONDS")

# OAuth 元数据探测 HTTP 请求
MCP_OAUTH_HTTP_TIMEOUT_SECONDS = _env_timeout("MCP_OAUTH_HTTP_TIMEOUT_SECONDS")
