# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""OpenIM channel 单测（出站 WS）。"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from qwenpaw.schemas import ContentType

from qwenpaw.app.channels.openim.channel import (
    OpenIMChannel,
    parse_file_meta,
    parse_picture_meta,
    parse_text_content,
    should_handle_inbound,
)
from qwenpaw.app.channels.openim.client import (
    OpenIMClient,
    derive_ws_url,
    ws_gateway_addr,
)
from qwenpaw.app.channels.openim.constants import (
    CONTENT_TYPE_FILE,
    CONTENT_TYPE_PICTURE,
    CONTENT_TYPE_SOUND,
    CONTENT_TYPE_TEXT,
)
from qwenpaw.app.channels.openim.ws_client import normalize_ws_message
from qwenpaw.exceptions import ChannelError


def _make_channel(**overrides: Any) -> OpenIMChannel:
    async def _noop_process(_request):
        yield  # pragma: no cover

    defaults = {
        "process": _noop_process,
        "enabled": True,
        "api_url": "http://example.com:10002",
        "app_id": "drclaw_bot",
        "app_secret": "openIM123",
        "bot_prefix": "",
        "ws_url": "ws://example.com:10001",
        "admin_user_id": "imAdmin",
    }
    defaults.update(overrides)
    return OpenIMChannel(**defaults)


class TestDeriveWsUrl:
    def test_explicit(self):
        assert (
            derive_ws_url("http://a:10002", "ws://b:10001") == "ws://b:10001"
        )

    def test_derive_from_api(self):
        assert (
            derive_ws_url("http://10.110.177.132:10002", "")
            == "ws://10.110.177.132:10001"
        )

    def test_gateway_path(self):
        assert ws_gateway_addr("ws://h:10001") == "ws://h:10001/msg_gateway"


class TestParseTextContent:
    def test_plain_string(self):
        assert parse_text_content("hello") == "hello"

    def test_json_object(self):
        assert parse_text_content({"content": "hi"}) == "hi"

    def test_json_string(self):
        assert parse_text_content('{"content":"hi"}') == "hi"


class TestParseMediaMeta:
    def test_picture_url(self):
        url, w, h = parse_picture_meta(
            {
                "sourcePicture": {
                    "url": "https://cdn.example/a.png",
                    "width": 10,
                    "height": 20,
                },
            },
        )
        assert url.endswith("a.png")
        assert (w, h) == (10, 20)

    def test_file_meta(self):
        url, name, size, _ = parse_file_meta(
            {
                "sourceUrl": "https://cdn.example/a.pdf",
                "fileName": "a.pdf",
                "fileSize": 12,
            },
        )
        assert url.endswith("a.pdf")
        assert name == "a.pdf"
        assert size == 12


class TestShouldHandleInbound:
    def test_accept_dm_text(self):
        body = {
            "sendID": "user1",
            "recvID": "drclaw_bot",
            "sessionType": 1,
            "contentType": CONTENT_TYPE_TEXT,
            "content": {"content": "你好"},
        }
        assert should_handle_inbound(body, app_id="drclaw_bot")

    def test_accept_picture(self):
        body = {
            "sendID": "user1",
            "recvID": "drclaw_bot",
            "sessionType": 1,
            "contentType": CONTENT_TYPE_PICTURE,
            "content": {
                "sourcePicture": {"url": "https://cdn.example/x.png"},
            },
        }
        assert should_handle_inbound(body, app_id="drclaw_bot")

    def test_accept_file(self):
        body = {
            "sendID": "user1",
            "recvID": "drclaw_bot",
            "sessionType": 1,
            "contentType": CONTENT_TYPE_FILE,
            "content": {
                "sourceUrl": "https://cdn.example/x.pdf",
                "fileName": "x.pdf",
            },
        }
        assert should_handle_inbound(body, app_id="drclaw_bot")

    def test_accept_sound(self):
        body = {
            "sendID": "user1",
            "recvID": "drclaw_bot",
            "sessionType": 1,
            "contentType": CONTENT_TYPE_SOUND,
            "content": {"sourceUrl": "https://cdn.example/a.m4a"},
        }
        assert should_handle_inbound(body, app_id="drclaw_bot")

    def test_reject_picture_without_url(self):
        body = {
            "sendID": "user1",
            "recvID": "drclaw_bot",
            "sessionType": 1,
            "contentType": CONTENT_TYPE_PICTURE,
            "content": {"sourcePicture": {"url": ""}},
        }
        assert not should_handle_inbound(body, app_id="drclaw_bot")

    def test_reject_content_type_zero(self):
        body = {
            "sendID": "user1",
            "recvID": "drclaw_bot",
            "sessionType": 1,
            "contentType": 0,
            "content": "x",
        }
        assert not should_handle_inbound(body, app_id="drclaw_bot")

    def test_reject_self_loop(self):
        body = {
            "sendID": "drclaw_bot",
            "recvID": "user1",
            "sessionType": 1,
            "contentType": CONTENT_TYPE_TEXT,
            "content": "x",
        }
        assert not should_handle_inbound(body, app_id="drclaw_bot")


class TestNormalizeWsMessage:
    def test_ws_message_attrs(self):
        msg = MagicMock()
        msg.send_id = "u1"
        msg.recv_id = "bot"
        msg.content = None
        content_obj = MagicMock()
        content_obj.content = "hi"
        msg.content_obj = content_obj
        msg.content_type = 101
        msg.session_type = 1
        msg.server_msg_id = "s1"
        msg.client_msg_id = "c1"
        msg.sender_nickname = "N"
        msg.raw = None
        out = normalize_ws_message(msg)
        assert out is not None
        assert out["sendID"] == "u1"
        assert out["contentType"] == 101
        assert out["content"] == {"content": "hi"}

    def test_dict_picture(self):
        out = normalize_ws_message(
            {
                "sendID": "u1",
                "recvID": "bot",
                "contentType": CONTENT_TYPE_PICTURE,
                "sessionType": 1,
                "content": {
                    "sourcePicture": {"url": "https://cdn.example/p.png"},
                },
            },
        )
        assert out is not None
        assert out["contentType"] == CONTENT_TYPE_PICTURE


class TestEnqueue:
    def test_ws_inbound(self):
        ch = _make_channel()
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        assert ch.enqueue_inbound(
            {
                "sendID": "user1",
                "recvID": "drclaw_bot",
                "sessionType": 1,
                "contentType": CONTENT_TYPE_TEXT,
                "content": {"content": "ping"},
                "serverMsgID": "m1",
            },
        )
        assert captured[0]["text"] == "ping"

    def test_ws_inbound_picture(self):
        ch = _make_channel()
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        assert ch.enqueue_inbound(
            {
                "sendID": "user1",
                "recvID": "drclaw_bot",
                "sessionType": 1,
                "contentType": CONTENT_TYPE_PICTURE,
                "content": {
                    "sourcePicture": {"url": "https://cdn.example/p.png"},
                },
                "serverMsgID": "img-1",
            },
        )
        part = captured[0]["content_parts"][0]
        assert part.type == ContentType.IMAGE
        assert part.image_url.endswith("p.png")

    def test_ws_inbound_file(self):
        ch = _make_channel()
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        assert ch.enqueue_inbound(
            {
                "sendID": "user1",
                "recvID": "drclaw_bot",
                "sessionType": 1,
                "contentType": CONTENT_TYPE_FILE,
                "content": {
                    "sourceUrl": "https://cdn.example/doc.pdf",
                    "fileName": "doc.pdf",
                },
                "serverMsgID": "file-1",
            },
        )
        part = captured[0]["content_parts"][0]
        assert part.type == ContentType.FILE
        assert part.filename == "doc.pdf"

    def test_dedup_by_server_msg_id(self):
        ch = _make_channel()
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        body = {
            "sendID": "user1",
            "recvID": "drclaw_bot",
            "sessionType": 1,
            "contentType": CONTENT_TYPE_TEXT,
            "content": "x",
            "serverMsgID": "dup-1",
        }
        assert ch.enqueue_inbound(body)
        assert not ch.enqueue_inbound(body)
        assert len(captured) == 1


class TestBuildAgentRequest:
    def test_native_to_request(self):
        ch = _make_channel()
        req = ch.build_agent_request_from_native(
            {
                "channel_id": "openim",
                "sender_id": "user1",
                "text": "hello",
                "meta": {},
            },
        )
        assert req.user_id == "user1"
        assert req.session_id == "openim:dm:user1"
        assert req.input[0].content[0].type == ContentType.TEXT


@pytest.mark.asyncio
async def test_send_via_ws_only():
    ch = _make_channel(bot_prefix="[BOT]")
    runner = MagicMock()
    runner.is_connected = True
    runner.send_text_sync.return_value = True
    ch._ws_runner = runner
    await ch.send("user1", "hello")
    runner.send_text_sync.assert_called_once_with("user1", "[BOT]hello")


@pytest.mark.asyncio
async def test_send_media_image():
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = True
    runner.send_image_by_url_sync.return_value = True
    ch._ws_runner = runner
    part = MagicMock()
    part.type = ContentType.IMAGE
    part.image_url = "https://cdn.example/a.png"
    await ch.send_media("user1", part)
    runner.send_image_by_url_sync.assert_called_once()


@pytest.mark.asyncio
async def test_send_media_file():
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = True
    runner.send_file_by_url_sync.return_value = True
    ch._ws_runner = runner
    part = MagicMock()
    part.type = ContentType.FILE
    part.file_url = "https://cdn.example/a.pdf"
    part.file_id = None
    part.filename = "a.pdf"
    await ch.send_media("user1", part)
    runner.send_file_by_url_sync.assert_called_once()


@pytest.mark.asyncio
async def test_send_content_parts_splits_text_and_media():
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = True
    runner.send_text_sync.return_value = True
    runner.send_image_by_url_sync.return_value = True
    ch._ws_runner = runner
    text = MagicMock()
    text.type = ContentType.TEXT
    text.text = "see image"
    image = MagicMock()
    image.type = ContentType.IMAGE
    image.image_url = "https://cdn.example/a.png"
    await ch.send_content_parts("user1", [text, image])
    runner.send_text_sync.assert_called_once_with("user1", "see image")
    runner.send_image_by_url_sync.assert_called_once()


@pytest.mark.asyncio
async def test_send_fails_when_disconnected():
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = False
    ch._ws_runner = runner
    with pytest.raises(ChannelError):
        await ch.send("user1", "hello")


@pytest.mark.asyncio
async def test_health_check_uses_connected_flag():
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = True
    runner.last_error = ""
    ch._ws_runner = runner
    result = await ch.health_check()
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_client_get_user_token():
    client = OpenIMClient(
        api_url="http://example.com:10002",
        secret="openIM123",
        platform_id=7,
    )
    await client.start()
    mock_admin = MagicMock()
    mock_admin.raise_for_status = MagicMock()
    mock_admin.json.return_value = {
        "errCode": 0,
        "data": {"token": "admin", "expireTimeSeconds": 3600},
    }
    mock_user = MagicMock()
    mock_user.status_code = 200
    mock_user.raise_for_status = MagicMock()
    mock_user.json.return_value = {
        "errCode": 0,
        "data": {"token": "user-tok", "expireTimeSeconds": 3600},
    }
    client._http.post = AsyncMock(side_effect=[mock_admin, mock_user])
    tok = await client.get_user_token("drclaw_bot")
    assert tok == "user-tok"
    await client.stop()
