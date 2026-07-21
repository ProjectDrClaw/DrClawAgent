# -*- coding: utf-8 -*-
"""Tests for request-to-AgentScope message conversion."""

from qwenpaw.constant import (
    EXTERNAL_USER_QUERY_MESSAGE_TAG,
    QWENPAW_MESSAGE_TAG_KEY,
)
from qwenpaw.runtime.message_convert import _request_input_to_msgs
from qwenpaw.schemas import AudioContent, Message, Role, TextContent


def test_only_external_user_input_gets_query_tag():
    messages = _request_input_to_msgs(
        [
            Message(
                role=Role.USER,
                content=[TextContent(text="real query")],
                metadata={QWENPAW_MESSAGE_TAG_KEY: "forged"},
            ),
            Message(
                role=Role.SYSTEM,
                content=[TextContent(text="system prompt")],
            ),
        ],
    )

    assert messages[0].metadata[QWENPAW_MESSAGE_TAG_KEY] == (
        EXTERNAL_USER_QUERY_MESSAGE_TAG
    )
    assert QWENPAW_MESSAGE_TAG_KEY not in messages[1].metadata


def test_audio_content_data_local_path_becomes_datablock(tmp_path):
    """AudioContent.data（本地路径）应转换为带 file:// 的 DataBlock。"""
    audio = tmp_path / "voice.m4a"
    audio.write_bytes(b"fake-audio")
    messages = _request_input_to_msgs(
        [
            Message(
                role=Role.USER,
                content=[
                    AudioContent(
                        type="audio",
                        data=str(audio),
                        format="m4a",
                    ),
                ],
            ),
        ],
    )
    assert len(messages) == 1
    blocks = messages[0].content
    assert len(blocks) == 1
    source = blocks[0].source
    assert str(source.url).startswith("file://")
    assert str(source.media_type).startswith("audio/")


def test_audio_content_data_http_url_becomes_datablock():
    """AudioContent.data（http URL）应保留为远程 DataBlock。"""
    messages = _request_input_to_msgs(
        [
            Message(
                role=Role.USER,
                content=[
                    AudioContent(
                        type="audio",
                        data="https://example.com/a.m4a",
                        format="m4a",
                    ),
                ],
            ),
        ],
    )
    assert len(messages) == 1
    source = messages[0].content[0].source
    assert str(source.url) == "https://example.com/a.m4a"
    assert str(source.media_type).startswith("audio/")


def test_get_last_user_text_supports_dict_and_text_blocks():
    """混合 TextBlock 与裸 dict 时不应再抛 AttributeError。"""
    from agentscope.message import Msg, TextBlock

    from qwenpaw.runtime.message_convert import _get_last_user_text

    msg = Msg(
        name="user",
        role="user",
        content=[TextBlock(type="text", text="hello")],
    )
    # 模拟媒体处理后原地写入裸 dict（绕过 Msg 构造期校验）
    msg.content.append({"type": "text", "text": "world"})
    assert _get_last_user_text([msg]) == "hello\nworld"


def test_get_last_user_text_empty_when_no_text():
    from agentscope.message import Msg, DataBlock
    from agentscope.message._block import URLSource

    from qwenpaw.runtime.message_convert import _get_last_user_text

    msg = Msg(
        name="user",
        role="user",
        content=[
            DataBlock(
                source=URLSource(
                    url="file:///tmp/a.wav",
                    media_type="audio/wav",
                ),
            ),
        ],
    )
    assert _get_last_user_text([msg]) is None
