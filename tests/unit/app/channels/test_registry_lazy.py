# -*- coding: utf-8 -*-
"""频道 registry 懒加载：启动路径不应 import 未启用频道。"""

from __future__ import annotations

import sys

from qwenpaw.app.channels.registry import (
    clear_builtin_channel_cache,
    get_channel_class,
    list_channel_keys,
)


def test_list_channel_keys_does_not_import_heavy_modules() -> None:
    """列举 key 不得触发 telegram 等重依赖模块 import。"""
    clear_builtin_channel_cache()
    # 清掉可能已被其它用例加载的模块，保证本断言有效
    for mod in list(sys.modules):
        if mod.startswith("qwenpaw.app.channels.telegram"):
            del sys.modules[mod]

    keys = list_channel_keys()
    assert "console" in keys
    assert "telegram" in keys
    assert "openim" in keys
    assert "qwenpaw.app.channels.telegram" not in sys.modules


def test_get_channel_class_loads_only_requested_builtin() -> None:
    """按需加载 console 时不应连带加载 telegram。"""
    clear_builtin_channel_cache()
    for mod in list(sys.modules):
        if mod.startswith("qwenpaw.app.channels.telegram"):
            del sys.modules[mod]

    cls = get_channel_class("console")
    assert cls is not None
    assert cls.channel == "console"
    assert "qwenpaw.app.channels.telegram" not in sys.modules
