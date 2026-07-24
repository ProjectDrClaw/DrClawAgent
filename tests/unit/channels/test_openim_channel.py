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
    detect_bot_mentioned,
    parse_file_meta,
    parse_picture_meta,
    parse_text_content,
    parse_video_meta,
    should_handle_inbound,
)
from qwenpaw.app.channels.openim.client import (
    OpenIMClient,
    derive_ws_url,
    ws_gateway_addr,
)
from qwenpaw.app.channels.openim.constants import (
    CONTENT_TYPE_AT_TEXT,
    CONTENT_TYPE_FILE,
    CONTENT_TYPE_PICTURE,
    CONTENT_TYPE_SOUND,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_VIDEO,
)
from qwenpaw.app.channels.openim.ws_client import (
    OpenIMWSRunner,
    normalize_ws_message,
)
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


class TestOpenIMFromConfigDisplayConfig:
    """合并上游 ChannelDisplayConfig 后，from_config 须能被 ChannelManager 调用。"""

    def test_from_config_accepts_display_config(self):
        from types import SimpleNamespace

        from qwenpaw.app.channels.renderer import ChannelDisplayConfig

        async def _noop_process(_request):
            yield  # pragma: no cover

        cfg = SimpleNamespace(
            enabled=True,
            api_url="http://example.com:10002",
            app_id="bot1",
            app_secret="secret",
            bot_prefix="",
            ws_url="ws://example.com:10001",
            admin_user_id="imAdmin",
            platform_id=7,
            dm_policy="open",
            group_policy="open",
            allow_from=[],
            deny_message="",
            require_mention=False,
            access_control_dm=False,
            access_control_group=False,
            share_session_in_group=False,
            show_thinking=True,
            show_tool_calls=True,
            show_tool_results=True,
        )
        display = ChannelDisplayConfig.from_config(
            cfg,
            show_tool_details=True,
        )
        ch = OpenIMChannel.from_config(
            process=_noop_process,
            config=cfg,
            display_config=display,
            no_text_debounce=True,
        )
        assert ch.enabled is True
        assert ch._display_config.show_tool_details is True

    def test_init_rejects_legacy_show_tool_details_kwarg(self):
        """旧 kwargs 不应再传给 BaseChannel，避免静默初始化失败。"""
        with pytest.raises(TypeError):
            _make_channel(show_tool_details=True)


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

    def test_video_meta(self):
        url, duration, snap, vtype = parse_video_meta(
            {
                "videoUrl": "https://cdn.example/a.mp4",
                "duration": 8,
                "snapshotUrl": "https://cdn.example/a.jpg",
                "videoType": "video/mp4",
            },
        )
        assert url.endswith("a.mp4")
        assert duration == 8
        assert snap.endswith("a.jpg")
        assert vtype == "video/mp4"


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

    def test_accept_video(self):
        body = {
            "sendID": "user1",
            "recvID": "drclaw_bot",
            "sessionType": 1,
            "contentType": CONTENT_TYPE_VIDEO,
            "content": {"videoUrl": "https://cdn.example/a.mp4"},
        }
        assert should_handle_inbound(body, app_id="drclaw_bot")

    def test_accept_group_text(self):
        body = {
            "sendID": "user1",
            "recvID": "",
            "groupID": "g1",
            "sessionType": 2,
            "contentType": CONTENT_TYPE_TEXT,
            "content": {"content": "群消息"},
        }
        assert should_handle_inbound(body, app_id="drclaw_bot")

    def test_accept_at_text(self):
        body = {
            "sendID": "user1",
            "groupID": "g1",
            "sessionType": 2,
            "contentType": CONTENT_TYPE_AT_TEXT,
            "content": {
                "text": "@助手 帮忙",
                "atUserList": ["drclaw_bot"],
            },
            "atUserIDList": ["drclaw_bot"],
        }
        assert should_handle_inbound(body, app_id="drclaw_bot")

    def test_reject_group_without_id(self):
        body = {
            "sendID": "user1",
            "sessionType": 2,
            "contentType": CONTENT_TYPE_TEXT,
            "content": {"content": "x"},
        }
        assert not should_handle_inbound(body, app_id="drclaw_bot")

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


class TestDetectBotMentioned:
    def test_at_user_list(self):
        body = {
            "atUserIDList": ["drclaw_bot"],
            "content": {},
        }
        assert detect_bot_mentioned(body, app_id="drclaw_bot")

    def test_at_all(self):
        body = {
            "content": {"atUserList": ["AtAllTag"], "text": "@所有人"},
        }
        assert detect_bot_mentioned(body, app_id="drclaw_bot")

    def test_not_mentioned(self):
        body = {
            "atUserIDList": ["other"],
            "content": {"text": "hi"},
        }
        assert not detect_bot_mentioned(body, app_id="drclaw_bot")


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

    def test_ws_inbound_group_with_mention(self):
        ch = _make_channel(require_mention=True)
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        assert ch.enqueue_inbound(
            {
                "sendID": "user1",
                "groupID": "g1",
                "sessionType": 2,
                "contentType": CONTENT_TYPE_AT_TEXT,
                "content": {
                    "text": "@助手 hi",
                    "atUserList": ["drclaw_bot"],
                    "atUsersInfo": [
                        {
                            "atUserID": "drclaw_bot",
                            "groupNickname": "助手",
                        },
                    ],
                },
                "atUserIDList": ["drclaw_bot"],
                "serverMsgID": "mg1",
            },
        )
        assert captured[0]["meta"]["is_group"] is True
        assert captured[0]["meta"]["bot_mentioned"] is True
        assert captured[0]["session_id"] == "openim:group:g1:user1"
        assert "助手" not in captured[0]["text"]

    def test_ws_inbound_group_shared_session(self):
        ch = _make_channel(require_mention=False, share_session_in_group=True)
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        assert ch.enqueue_inbound(
            {
                "sendID": "user1",
                "groupID": "g1",
                "sessionType": 2,
                "contentType": CONTENT_TYPE_TEXT,
                "content": {"content": "群共享"},
                "serverMsgID": "mg-share",
            },
        )
        assert captured[0]["session_id"] == "openim:group:g1"

    def test_ws_inbound_group_require_mention_drop(self):
        ch = _make_channel(require_mention=True)
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        assert not ch.enqueue_inbound(
            {
                "sendID": "user1",
                "groupID": "g1",
                "sessionType": 2,
                "contentType": CONTENT_TYPE_TEXT,
                "content": {"content": "无人@"},
                "serverMsgID": "mg2",
            },
        )
        assert not captured

    def test_ws_inbound_video(self):
        ch = _make_channel()
        captured: list[Any] = []
        ch.set_enqueue(captured.append)

        def _no_download(_url, _msg_id="", _video_type=""):
            return None

        ch._download_video_to_local = (  # type: ignore[method-assign]
            _no_download
        )
        assert ch.enqueue_inbound(
            {
                "sendID": "user1",
                "recvID": "drclaw_bot",
                "sessionType": 1,
                "contentType": CONTENT_TYPE_VIDEO,
                "content": {
                    "videoUrl": "https://cdn.example/v.mp4",
                    "duration": 12,
                },
                "serverMsgID": "mv1",
            },
        )
        # 下载失败时仍保留 VideoContent，便于 media_hook 兜底
        assert captured[0]["content_parts"][0].type == ContentType.VIDEO
        assert captured[0]["meta"]["duration"] == 12

    def test_ws_inbound_sound_localizes(self, tmp_path, monkeypatch):
        """语音入站应落盘为本地路径（对齐飞书）。"""
        ch = _make_channel(workspace_dir=tmp_path)
        local = tmp_path / "openim_ws" / "media" / "ms1_audio.m4a"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(b"voice-bytes")

        def _fake_download(url, _msg_id="", _sound_type=""):
            assert url.startswith("https://")
            return str(local)

        monkeypatch.setattr(ch, "_download_sound_to_local", _fake_download)
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        assert ch.enqueue_inbound(
            {
                "sendID": "user1",
                "recvID": "drclaw_bot",
                "sessionType": 1,
                "contentType": CONTENT_TYPE_SOUND,
                "content": {
                    "sourceUrl": "https://cdn.example/a.m4a",
                    "duration": 3,
                    "soundType": "m4a",
                },
                "serverMsgID": "ms1",
            },
        )
        part = captured[0]["content_parts"][0]
        assert part.type == ContentType.AUDIO
        assert part.data == str(local)
        assert captured[0]["meta"]["duration"] == 3

    def test_ws_inbound_video_localizes_as_file(self, tmp_path, monkeypatch):
        """视频入站应落盘并改为 FileContent（对齐飞书 media）。"""
        ch = _make_channel(workspace_dir=tmp_path)
        local = tmp_path / "openim_ws" / "media" / "mv1_video.mp4"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(b"video-bytes")

        def _fake_download(url, _msg_id="", _video_type=""):
            assert url.startswith("https://")
            return str(local)

        monkeypatch.setattr(ch, "_download_video_to_local", _fake_download)
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        assert ch.enqueue_inbound(
            {
                "sendID": "user1",
                "recvID": "drclaw_bot",
                "sessionType": 1,
                "contentType": CONTENT_TYPE_VIDEO,
                "content": {
                    "videoUrl": "https://cdn.example/v.mp4",
                    "duration": 12,
                    "videoType": "mp4",
                },
                "serverMsgID": "mv1",
            },
        )
        part = captured[0]["content_parts"][0]
        assert part.type == ContentType.FILE
        assert part.file_url == str(local)
        assert captured[0]["meta"]["duration"] == 12

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

    def test_ws_inbound_file_localizes(self, tmp_path, monkeypatch):
        """文件入站应落盘为本地 FileContent（对齐飞书）。"""
        ch = _make_channel(workspace_dir=tmp_path)
        local = tmp_path / "openim_ws" / "media" / "file-1_file.pdf"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(b"%PDF")

        def _fake_download(
            url,
            _msg_id="",
            kind="media",
            _type_hint="",
            _default_ext="bin",
            _filename_hint="",
        ):
            assert url.startswith("https://")
            assert kind == "file"
            return str(local)

        monkeypatch.setattr(ch, "_download_media_to_local", _fake_download)
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
        assert part.file_url == str(local)
        assert part.filename == "doc.pdf"

    def test_ws_inbound_file_keeps_remote_on_download_fail(self):
        ch = _make_channel()
        captured: list[Any] = []
        ch.set_enqueue(captured.append)
        ch._download_media_to_local = (  # type: ignore[method-assign]
            lambda *a, **k: None
        )
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
                "serverMsgID": "file-2",
            },
        )
        part = captured[0]["content_parts"][0]
        assert part.type == ContentType.FILE
        assert part.file_url.endswith("doc.pdf")
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
    runner.send_text_sync.assert_called_once_with(
        "user1",
        "[BOT]hello",
        group_id="",
        session_type=None,
    )


@pytest.mark.asyncio
async def test_send_group_text():
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = True
    runner.send_text_sync.return_value = True
    ch._ws_runner = runner
    await ch.send(
        "openim:group:g1",
        "hello",
        meta={"is_group": True, "group_id": "g1"},
    )
    runner.send_text_sync.assert_called_once_with(
        "",
        "hello",
        group_id="g1",
        session_type=3,  # App 工作群默认超级群
    )


@pytest.mark.asyncio
async def test_send_group_text_uses_inbound_session_type():
    """入站 sessionType=3 时应原样出站，避免发到普通群 2。"""
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = True
    runner.send_text_sync.return_value = True
    ch._ws_runner = runner
    await ch.send(
        "openim:group:g1",
        "hello",
        meta={
            "is_group": True,
            "group_id": "g1",
            "session_type": 3,
        },
    )
    runner.send_text_sync.assert_called_once_with(
        "",
        "hello",
        group_id="g1",
        session_type=3,
    )


def test_resolve_send_target_strips_per_user_suffix():
    ch = _make_channel()
    recv, group = ch._resolve_send_target(
        "openim:group:g1:user9",
        meta={"is_group": True},
    )
    assert recv == ""
    assert group == "g1"


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
async def test_send_media_audio_sound():
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = True
    runner.send_sound_by_url_sync.return_value = True
    ch._ws_runner = runner
    part = MagicMock()
    part.type = ContentType.AUDIO
    part.data = "https://cdn.example/a.ogg"
    part.format = "ogg"
    part.duration = None
    await ch.send_media("user1", part, meta={"duration": 3})
    runner.send_sound_by_url_sync.assert_called_once()
    kwargs = runner.send_sound_by_url_sync.call_args.kwargs
    assert kwargs["duration"] == 3


@pytest.mark.asyncio
async def test_send_media_video():
    ch = _make_channel()
    runner = MagicMock()
    runner.is_connected = True
    runner.send_video_by_url_sync.return_value = True
    ch._ws_runner = runner
    part = MagicMock()
    part.type = ContentType.VIDEO
    part.video_url = "https://cdn.example/a.mp4"
    part.duration = None
    await ch.send_media("user1", part)
    runner.send_video_by_url_sync.assert_called_once()
    kwargs = runner.send_video_by_url_sync.call_args.kwargs
    assert kwargs["duration"] == 1


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
    runner.send_text_sync.assert_called_once_with(
        "user1",
        "see image",
        group_id="",
        session_type=None,
    )
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


class TestSilentReconnectLogging:
    """断连日志应静默：首断 info，中间 debug，限频 warning。"""

    def _runner(self, tmp_path):
        return OpenIMWSRunner(
            ws_url="ws://example.com:10001",
            api_url="http://example.com:10002",
            data_dir=tmp_path,
            robot_user_id="bot",
            platform_id=7,
            on_message=lambda _m: None,
            token_provider=lambda: "tok",
        )

    def test_first_disconnect_after_connect_is_info(self, tmp_path, caplog):
        import logging

        runner = self._runner(tmp_path)
        runner._ever_connected = True
        with caplog.at_level(
            logging.DEBUG,
            logger="qwenpaw.app.channels.openim.ws_client",
        ):
            runner._mark_disconnected("net down")
            runner._log_disconnect_event("connect_failed", "net down")
        assert any(
            "reconnecting silently" in r.message for r in caplog.records
        )
        assert not any(
            r.levelno >= logging.WARNING and "still down" in r.message
            for r in caplog.records
        )

    def test_repeat_disconnect_is_debug_within_interval(
        self,
        tmp_path,
        caplog,
    ):
        import logging
        import time

        runner = self._runner(tmp_path)
        runner._ever_connected = True
        now = time.time()
        runner._disconnected_since = now
        runner._last_disconnect_log_at = now  # 刚记过首断
        with caplog.at_level(
            logging.DEBUG,
            logger="qwenpaw.app.channels.openim.ws_client",
        ):
            runner._log_disconnect_event("sdk_error", "again")
        assert any(r.levelno == logging.DEBUG for r in caplog.records)
        assert not any(r.levelno >= logging.WARNING for r in caplog.records)

    def test_reconnect_success_logs_reconnected(self, tmp_path, caplog):
        import logging

        runner = self._runner(tmp_path)
        runner._ever_connected = True
        runner._disconnected_since = 1.0
        runner._login_ok = False
        with caplog.at_level(
            logging.INFO,
            logger="qwenpaw.app.channels.openim.ws_client",
        ):
            runner._mark_connected()
        assert any("reconnected" in r.message for r in caplog.records)
        assert runner.is_connected
        assert runner._disconnected_since is None
