# -*- coding: utf-8 -*-
"""遥测已禁用：接口保持兼容，行为为空操作。"""
from __future__ import annotations

from pathlib import Path

from qwenpaw.utils.telemetry import (
    TELEMETRY_MARKER_FILE,
    collect_and_upload_telemetry,
    has_telemetry_been_collected,
    is_telemetry_opted_out,
    mark_telemetry_collected,
)


def test_telemetry_always_opted_out(tmp_path: Path) -> None:
    assert is_telemetry_opted_out(tmp_path) is True


def test_telemetry_always_collected(tmp_path: Path) -> None:
    assert has_telemetry_been_collected(tmp_path) is True


def test_collect_returns_false_and_writes_nothing(tmp_path: Path) -> None:
    assert collect_and_upload_telemetry(tmp_path) is False
    assert not (tmp_path / TELEMETRY_MARKER_FILE).exists()


def test_mark_is_noop(tmp_path: Path) -> None:
    mark_telemetry_collected(tmp_path, opted_out=True)
    assert not (tmp_path / TELEMETRY_MARKER_FILE).exists()
