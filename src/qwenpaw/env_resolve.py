# -*- coding: utf-8 -*-
"""应用环境变量解析：``DRCLAW_*`` 优先，兼容 ``QWENPAW_*`` 与 ``COPAW_*``。"""

from __future__ import annotations

import os

_ENV_PREFIXES = ("DRCLAW_", "QWENPAW_", "COPAW_")


def env_suffix(key: str) -> str | None:
    """从 ``DRCLAW_FOO`` / ``QWENPAW_FOO`` / ``COPAW_FOO`` 提取 ``FOO``。"""
    for prefix in _ENV_PREFIXES:
        if key.startswith(prefix):
            return key[len(prefix) :]
    return None


def drclaw_env(name: str) -> str:
    """返回规范环境变量名 ``DRCLAW_<name>``（*name* 可带或不带前缀）。"""
    suffix = env_suffix(name)
    if suffix is None:
        suffix = name
    return f"DRCLAW_{suffix}"


def get_env(key: str, default: str = "") -> str:
    """按 DRCLAW → QWENPAW → COPAW 顺序读取环境变量。"""
    suffix = env_suffix(key)
    if suffix is None:
        return os.environ.get(key, default)
    for prefix in _ENV_PREFIXES:
        full = prefix + suffix
        if full in os.environ:
            return os.environ[full]
    return default


def set_env(key: str, value: str) -> None:
    """写入规范 ``DRCLAW_*`` 键。"""
    os.environ[drclaw_env(key)] = value


def pop_env(key: str) -> str | None:
    """移除 DRCLAW / QWENPAW / COPAW 三个别名中的全部匹配项。"""
    suffix = env_suffix(key) or key
    removed: str | None = None
    for prefix in _ENV_PREFIXES:
        full = prefix + suffix
        if full in os.environ:
            removed = os.environ.pop(full)
    return removed
