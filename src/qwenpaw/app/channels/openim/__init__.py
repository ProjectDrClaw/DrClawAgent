# -*- coding: utf-8 -*-
"""OpenIM channel package（出站 WebSocket）。"""
from .channel import (
    OpenIMChannel,
    build_inbound_parts,
    parse_file_meta,
    parse_picture_meta,
    parse_sound_meta,
    parse_text_content,
    should_handle_inbound,
)
from .client import derive_ws_url, ws_gateway_addr
from .ws_client import openim_sdk_available

__all__ = [
    "OpenIMChannel",
    "build_inbound_parts",
    "openim_sdk_available",
    "parse_file_meta",
    "parse_picture_meta",
    "parse_sound_meta",
    "parse_text_content",
    "should_handle_inbound",
    "derive_ws_url",
    "ws_gateway_addr",
]
