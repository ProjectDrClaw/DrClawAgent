# -*- coding: utf-8 -*-
"""Dr.Claw 禁用遥测：不收集、不上传任何使用数据。"""

from __future__ import annotations

from pathlib import Path

TELEMETRY_MARKER_FILE = ".telemetry_collected"


def is_telemetry_opted_out(_working_dir: Path) -> bool:
    """始终视为已退出遥测。"""
    return True


def has_telemetry_been_collected(_working_dir: Path) -> bool:
    """始终视为已处理，避免任何采集入口再次触发。"""
    return True


def mark_telemetry_collected(
    working_dir: Path,
    *,
    opted_out: bool = False,
) -> None:
    """无操作（兼容旧调用）。"""
    del working_dir, opted_out


def collect_and_upload_telemetry(working_dir: Path) -> bool:
    """不采集、不上传。"""
    del working_dir
    return False
