# -*- coding: utf-8 -*-
"""Channel registry: built-in + plugin-registered channels.

Built-in channel modules are imported lazily on first use. Eagerly importing
every channel (telegram, wecom, openim, …) blocks the event loop for tens of
seconds during workspace start and keeps ``/api/healthz`` at 503 past the
integration-test readiness timeout.
"""

from __future__ import annotations

import importlib
import logging
import threading
from typing import TYPE_CHECKING

from .base import BaseChannel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_BUILTIN_SPECS: dict[str, tuple[str, str]] = {
    "imessage": (".imessage", "IMessageChannel"),
    "discord": (".discord_", "DiscordChannel"),
    "dingtalk": (".dingtalk", "DingTalkChannel"),
    "feishu": (".feishu", "FeishuChannel"),
    "qq": (".qq", "QQChannel"),
    "telegram": (".telegram", "TelegramChannel"),
    "mattermost": (".mattermost", "MattermostChannel"),
    "mqtt": (".mqtt", "MQTTChannel"),
    "console": (".console", "ConsoleChannel"),
    "matrix": (".matrix", "MatrixChannel"),
    "slack": (".slack", "SlackChannel"),
    "voice": (".voice", "VoiceChannel"),
    "sip": (".sip", "SIPChannel"),
    "wecom": (".wecom", "WecomChannel"),
    "xiaoyi": (".xiaoyi", "XiaoYiChannel"),
    "yuanbao": (".yuanbao", "YuanbaoChannel"),
    "wechat": (".wechat", "WeChatChannel"),
    "onebot": (".onebot", "OneBotChannel"),
    "openim": (".openim", "OpenIMChannel"),
}

# Required channels must load; failures are raised, not skipped.
_REQUIRED_CHANNEL_KEYS: frozenset[str] = frozenset({"console"})

# Per-key cache: missing = not attempted; None = load failed (optional).
_BUILTIN_CHANNEL_CACHE: dict[str, type[BaseChannel] | None] = {}
_BUILTIN_CHANNEL_CACHE_LOCK = threading.Lock()

BUILTIN_CHANNEL_KEYS = frozenset(_BUILTIN_SPECS.keys())


def _load_one_builtin_channel(key: str) -> type[BaseChannel] | None:
    """Import and validate one built-in channel class."""
    spec = _BUILTIN_SPECS.get(key)
    if spec is None:
        return None
    module_name, class_name = spec
    try:
        mod = importlib.import_module(module_name, package=__package__)
        cls = getattr(mod, class_name)
        if not (
            isinstance(cls, type)
            and issubclass(cls, BaseChannel)
            and cls is not BaseChannel
        ):
            raise TypeError(
                f"{module_name}.{class_name} is not a BaseChannel subtype",
            )
        return cls
    except Exception:
        if key in _REQUIRED_CHANNEL_KEYS:
            logger.error(
                'failed to load required built-in channel "%s"',
                key,
                exc_info=True,
            )
            raise
        logger.debug(
            "built-in channel unavailable: %s",
            key,
            exc_info=True,
        )
        return None


def get_channel_class(key: str) -> type[BaseChannel] | None:
    """Return one channel class, importing the built-in module on demand."""
    plugin_channels = _get_plugin_channels()
    if key in plugin_channels and key not in _BUILTIN_SPECS:
        return plugin_channels[key]

    if key not in _BUILTIN_SPECS:
        return plugin_channels.get(key)

    with _BUILTIN_CHANNEL_CACHE_LOCK:
        if key in _BUILTIN_CHANNEL_CACHE:
            return _BUILTIN_CHANNEL_CACHE[key]
        cls = _load_one_builtin_channel(key)
        _BUILTIN_CHANNEL_CACHE[key] = cls
        return cls


def list_channel_keys() -> tuple[str, ...]:
    """Return known channel keys without importing channel modules."""
    keys = list(_BUILTIN_SPECS.keys())
    for key in _get_plugin_channels():
        if key not in _BUILTIN_SPECS:
            keys.append(key)
    return tuple(keys)


def _get_cached_builtin_channels() -> dict[str, type[BaseChannel]]:
    """Eagerly load all built-in channels (CLI / doctor paths)."""
    out: dict[str, type[BaseChannel]] = {}
    for key in _BUILTIN_SPECS:
        cls = get_channel_class(key)
        if cls is not None:
            out[key] = cls
    return out


def clear_builtin_channel_cache() -> None:
    """Reset built-in channel cache. Primarily for tests."""
    with _BUILTIN_CHANNEL_CACHE_LOCK:
        _BUILTIN_CHANNEL_CACHE.clear()


def _get_plugin_channels() -> dict[str, type[BaseChannel]]:
    """Return channel classes registered via the plugin system."""
    try:
        from ...plugins.registry import PluginRegistry

        registry = PluginRegistry()
        return {
            key: reg.channel_class
            for key, reg in registry.get_registered_channels().items()
        }
    except ImportError:
        logger.debug("plugin channel discovery skipped (not installed)")
        return {}
    except Exception:
        logger.warning(
            "plugin channel discovery failed",
            exc_info=True,
        )
        return {}


def get_channel_registry() -> dict[str, type[BaseChannel]]:
    """Built-in + plugin-registered channels (eager load).

    Prefer :func:`list_channel_keys` + :func:`get_channel_class` on the
    workspace startup path so disabled channels are never imported.
    """
    out = _get_cached_builtin_channels()
    for key, ch_cls in _get_plugin_channels().items():
        if key in out:
            logger.warning(
                "Plugin channel '%s' skipped: key already exists in "
                "built-in channels",
                key,
            )
            continue
        out[key] = ch_cls
    return out
