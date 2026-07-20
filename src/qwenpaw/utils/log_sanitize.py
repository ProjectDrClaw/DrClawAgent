# -*- coding: utf-8 -*-
"""调试日志展示：缩短源码位置中的 Python 包路径前缀。"""

from __future__ import annotations

import os
import re

# 开发布局 src/qwenpaw/… 与 PyInstaller 打包布局 qwenpaw/…（/ 与 \ 均可）
_PACKAGE_PATH_IN_LOG = re.compile(
    r"(?:src[/\\])?(?:qwenpaw|drclaw)[/\\]",
    re.IGNORECASE,
)

# 从 pathname 开头去掉任意前缀直至包目录（含 _internal/qwenpaw/ 等）
_PACKAGE_PATH_PREFIX = re.compile(
    r"^(?:.*?[/\\])?(?:src[/\\])?(?:qwenpaw|drclaw)[/\\]",
    re.IGNORECASE,
)


def short_log_source_path(path: str) -> str:
    """将源码路径缩短为包内路径，例如 app/_app.py。"""
    if not path:
        return path
    normalized = path.replace("\\", "/")
    stripped = _PACKAGE_PATH_PREFIX.sub("", normalized)
    if not stripped:
        return path
    return stripped.replace("/", os.sep)


def sanitize_log_paths(text: str) -> str:
    """去掉调试日志正文中的 qwenpaw/drclaw 包路径前缀。"""
    if not text:
        return text
    return _PACKAGE_PATH_IN_LOG.sub("", text)
