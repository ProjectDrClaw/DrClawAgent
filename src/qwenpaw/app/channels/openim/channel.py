# -*- coding: utf-8 -*-
# pylint: disable=too-many-return-statements,too-many-instance-attributes
# pylint: disable=too-many-branches
"""OpenIM channel：出站 WS 收消息 + SDK 发消息。"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from qwenpaw.schemas import (
    AudioContent,
    FileContent,
    ImageContent,
    TextContent,
)

from ....config.config import OpenIMConfig as OpenIMChannelConfig
from ....exceptions import ChannelError
from ..base import (
    BaseChannel,
    ContentType,
    OnReplySent,
    OutgoingContentPart,
    ProcessHandler,
)
from ..utils import file_url_to_local_path
from .client import OpenIMClient, derive_ws_url
from .constants import (
    CONTENT_TYPE_FILE,
    CONTENT_TYPE_PICTURE,
    CONTENT_TYPE_SOUND,
    CONTENT_TYPE_TEXT,
    INBOUND_CONTENT_TYPES,
    PROCESSED_MSG_IDS_MAX,
    SESSION_TYPE_DM,
    WS_START_CONNECT_TIMEOUT_S,
)
from .ws_client import OpenIMWSRunner, openim_sdk_available

if TYPE_CHECKING:
    from qwenpaw.schemas import AgentRequest

logger = logging.getLogger(__name__)

# token_provider 在 WS 线程同步等待刷新的上限
DEFAULT_TOKEN_TIMEOUT_S = 30.0


def _as_content_dict(content: Any) -> Dict[str, Any]:
    if content is None:
        return {}
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        raw = content.strip()
        if raw.startswith("{") and raw.endswith("}"):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            if isinstance(obj, dict):
                return obj
        return {}
    return {}


def parse_text_content(content: Any) -> str:
    """从 OpenIM content 字段提取纯文本。"""
    if content is None:
        return ""
    if isinstance(content, dict):
        text = content.get("content")
        return str(text) if text is not None else ""
    if isinstance(content, str):
        raw = content.strip()
        if not raw:
            return ""
        if raw.startswith("{") and raw.endswith("}"):
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                return content
            if isinstance(obj, dict) and "content" in obj:
                return str(obj.get("content") or "")
        return content
    return str(content)


def parse_picture_meta(content: Any) -> Tuple[str, int, int]:
    """解析图片 URL 与宽高。"""
    obj = _as_content_dict(content)
    for key in (
        "sourcePicture",
        "source_picture",
        "bigPicture",
        "big_picture",
        "snapshotPicture",
        "snapshot_picture",
    ):
        pic = obj.get(key) or {}
        if not isinstance(pic, dict):
            continue
        url = str(pic.get("url") or "").strip()
        if url:
            return (
                url,
                int(pic.get("width") or 0),
                int(pic.get("height") or 0),
            )
    return "", 0, 0


def parse_file_meta(content: Any) -> Tuple[str, str, int, str]:
    """解析文件 URL / 名称 / 大小 / MIME。"""
    obj = _as_content_dict(content)
    url = str(obj.get("sourceUrl") or obj.get("source_url") or "").strip()
    name = str(obj.get("fileName") or obj.get("file_name") or "file").strip()
    size = int(obj.get("fileSize") or obj.get("file_size") or 0)
    file_type = str(obj.get("fileType") or obj.get("file_type") or "").strip()
    return url, name or "file", size, file_type


def parse_sound_meta(content: Any) -> Tuple[str, int, str]:
    """解析语音 URL / 时长 / 类型。"""
    obj = _as_content_dict(content)
    url = str(obj.get("sourceUrl") or obj.get("source_url") or "").strip()
    duration = int(obj.get("duration") or 0)
    sound_type = str(
        obj.get("soundType") or obj.get("sound_type") or "",
    ).strip()
    return url, duration, sound_type


def should_handle_inbound(
    body: Dict[str, Any],
    *,
    app_id: str,
) -> bool:
    """仅处理对端发给机器人的单聊文本/图片/文件/语音（过滤自回环）。"""
    if not app_id:
        return False
    send_id = str(body.get("sendID") or "")
    recv_id = str(body.get("recvID") or "")
    if not send_id or send_id == app_id:
        return False
    # WS 推送时 recv 可能为空或为机器人
    if recv_id and recv_id != app_id:
        return False
    try:
        session_type = int(body.get("sessionType") or SESSION_TYPE_DM)
    except (TypeError, ValueError):
        return False
    if session_type != SESSION_TYPE_DM:
        return False
    try:
        content_type = int(body.get("contentType") or 0)
    except (TypeError, ValueError):
        return False
    if content_type not in INBOUND_CONTENT_TYPES:
        return False
    content = body.get("content")
    if content_type == CONTENT_TYPE_TEXT:
        return bool(parse_text_content(content).strip())
    if content_type == CONTENT_TYPE_PICTURE:
        return bool(parse_picture_meta(content)[0])
    if content_type == CONTENT_TYPE_FILE:
        return bool(parse_file_meta(content)[0])
    if content_type == CONTENT_TYPE_SOUND:
        return bool(parse_sound_meta(content)[0])
    return False


def build_inbound_parts(
    content_type: int,
    content: Any,
) -> Tuple[str, List[Any]]:
    """按 contentType 构造 text + content_parts。"""
    if content_type == CONTENT_TYPE_TEXT:
        text = parse_text_content(content)
        return text, [TextContent(type=ContentType.TEXT, text=text)]
    if content_type == CONTENT_TYPE_PICTURE:
        url, _, _ = parse_picture_meta(content)
        return "", [
            ImageContent(type=ContentType.IMAGE, image_url=url),
        ]
    if content_type == CONTENT_TYPE_FILE:
        url, name, _, _ = parse_file_meta(content)
        return "", [
            FileContent(
                type=ContentType.FILE,
                file_url=url,
                filename=name,
            ),
        ]
    if content_type == CONTENT_TYPE_SOUND:
        url, _, sound_type = parse_sound_meta(content)
        fmt = sound_type or "audio"
        return "", [
            AudioContent(type=ContentType.AUDIO, data=url, format=fmt),
        ]
    return "", []


class OpenIMChannel(BaseChannel):
    """OpenIM 内置频道（出站 WebSocket）。"""

    channel = "openim"
    uses_manager_queue = True
    streaming_enabled = False

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool,
        api_url: str,
        app_id: str,
        app_secret: str,
        bot_prefix: str,
        ws_url: str = "",
        admin_user_id: str = "imAdmin",
        platform_id: int = 7,
        workspace_dir: Path | None = None,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
        filter_tool_messages: bool = False,
        no_text_debounce: bool = True,
        filter_thinking: bool = False,
        dm_policy: str = "open",
        group_policy: str = "open",
        allow_from: Optional[List[str]] = None,
        deny_message: str = "",
        require_mention: bool = False,
        access_control_dm: bool = False,
        access_control_group: bool = False,
    ):
        super().__init__(
            process,
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
            filter_tool_messages=filter_tool_messages,
            no_text_debounce=no_text_debounce,
            filter_thinking=filter_thinking,
            dm_policy=dm_policy,
            group_policy=group_policy,
            allow_from=allow_from,
            deny_message=deny_message,
            require_mention=require_mention,
            streaming_enabled=False,
            access_control_dm=access_control_dm,
            access_control_group=access_control_group,
        )
        self.enabled = enabled
        self.api_url = (api_url or "").rstrip("/")
        self.app_id = app_id or ""
        self.app_secret = app_secret or ""
        self.bot_prefix = bot_prefix or ""
        self.ws_url = derive_ws_url(self.api_url, ws_url or "")
        self.admin_user_id = admin_user_id or "imAdmin"
        self.platform_id = int(platform_id or 7)
        self._workspace_dir = (
            Path(workspace_dir).expanduser() if workspace_dir else None
        )
        self._client = OpenIMClient(
            api_url=self.api_url,
            secret=self.app_secret,
            admin_user_id=self.admin_user_id,
            platform_id=self.platform_id,
        )
        self._ws_runner: Optional[OpenIMWSRunner] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._processed_msg_ids: OrderedDict[str, None] = OrderedDict()

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "OpenIMChannel":
        allow_from_env = os.getenv("OPENIM_ALLOW_FROM", "")
        allow_from = (
            [s.strip() for s in allow_from_env.split(",") if s.strip()]
            if allow_from_env
            else []
        )
        return cls(
            process=process,
            enabled=os.getenv("OPENIM_CHANNEL_ENABLED", "0") == "1",
            api_url=os.getenv("OPENIM_API_URL", ""),
            app_id=os.getenv("OPENIM_APP_ID", ""),
            app_secret=os.getenv("OPENIM_APP_SECRET", ""),
            bot_prefix=os.getenv("OPENIM_BOT_PREFIX", ""),
            ws_url=os.getenv("OPENIM_WS_URL", ""),
            admin_user_id=os.getenv("OPENIM_ADMIN_USER_ID", "imAdmin"),
            platform_id=int(os.getenv("OPENIM_PLATFORM_ID", "7")),
            on_reply_sent=on_reply_sent,
            dm_policy=os.getenv("OPENIM_DM_POLICY", "open"),
            group_policy=os.getenv("OPENIM_GROUP_POLICY", "open"),
            allow_from=allow_from,
            deny_message=os.getenv("OPENIM_DENY_MESSAGE", ""),
            require_mention=os.getenv("OPENIM_REQUIRE_MENTION", "0") == "1",
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: OpenIMChannelConfig,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
        filter_tool_messages: bool = False,
        no_text_debounce: bool = True,
        filter_thinking: bool = False,
        workspace_dir: Path | None = None,
    ) -> "OpenIMChannel":
        return cls(
            process=process,
            enabled=config.enabled,
            api_url=config.api_url or "",
            app_id=config.app_id or "",
            app_secret=config.app_secret or "",
            bot_prefix=config.bot_prefix or "",
            ws_url=config.ws_url or "",
            admin_user_id=config.admin_user_id or "imAdmin",
            platform_id=int(config.platform_id or 7),
            workspace_dir=workspace_dir,
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
            filter_tool_messages=filter_tool_messages,
            no_text_debounce=no_text_debounce,
            filter_thinking=filter_thinking,
            dm_policy=config.dm_policy or "open",
            group_policy=config.group_policy or "open",
            allow_from=config.allow_from or [],
            deny_message=config.deny_message or "",
            require_mention=config.require_mention,
            access_control_dm=bool(
                getattr(config, "access_control_dm", False),
            ),
            access_control_group=bool(
                getattr(config, "access_control_group", False),
            ),
        )

    def resolve_session_id(
        self,
        sender_id: str,
        channel_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        return f"openim:dm:{sender_id}"

    def build_agent_request_from_native(
        self,
        native_payload: Any,
    ) -> "AgentRequest":
        payload = native_payload if isinstance(native_payload, dict) else {}
        channel_id = payload.get("channel_id") or self.channel
        sender_id = str(payload.get("sender_id") or "")
        meta = dict(payload.get("meta") or {})
        text = str(payload.get("text") or "")
        content_parts = payload.get("content_parts")
        if not content_parts:
            content_parts = [
                TextContent(type=ContentType.TEXT, text=text or " "),
            ]
        session_id = payload.get("session_id") or self.resolve_session_id(
            sender_id,
            meta,
        )
        request = self.build_agent_request_from_user_content(
            channel_id=channel_id,
            sender_id=sender_id,
            session_id=session_id,
            content_parts=content_parts,
            channel_meta=meta,
        )
        setattr(request, "channel_meta", meta)
        return request

    def _data_dir(self) -> Path:
        base = self._workspace_dir
        if base is None and self._workspace is not None:
            base = Path(self._workspace.workspace_dir)
        if base is None:
            base = Path.cwd() / ".openim_ws"
        return Path(base) / "openim_ws"

    def _remember_msg_id(self, msg_id: str) -> bool:
        """记录消息 ID；若已处理过则返回 False。"""
        if not msg_id:
            return True
        if msg_id in self._processed_msg_ids:
            return False
        self._processed_msg_ids[msg_id] = None
        while len(self._processed_msg_ids) > PROCESSED_MSG_IDS_MAX:
            self._processed_msg_ids.popitem(last=False)
        return True

    def _token_provider(self) -> str:
        """供 WS 线程调用：在事件循环中强制刷新 user token。"""
        loop = self._loop
        if loop is None or not loop.is_running():
            raise RuntimeError("openim event loop is not available for token")
        fut = asyncio.run_coroutine_threadsafe(
            self._client.get_user_token(self.app_id, force=True),
            loop,
        )
        return fut.result(timeout=DEFAULT_TOKEN_TIMEOUT_S)

    def _on_ws_message(self, body: Dict[str, Any]) -> None:
        self.enqueue_inbound(body)

    def enqueue_inbound(self, body: Dict[str, Any]) -> bool:
        """规范化入站载荷并入队（WS 回调）。"""
        if not self.enabled:
            return False
        if not should_handle_inbound(body, app_id=self.app_id):
            return False
        msg_id = str(
            body.get("serverMsgID") or body.get("clientMsgID") or "",
        )
        if not self._remember_msg_id(msg_id):
            logger.debug("openim skip duplicate msg_id=%s", msg_id)
            return False
        send_id = str(body.get("sendID") or "")
        try:
            content_type = int(body.get("contentType") or 0)
        except (TypeError, ValueError):
            return False
        text, content_parts = build_inbound_parts(
            content_type,
            body.get("content"),
        )
        if not content_parts:
            return False
        meta = {
            "recv_id": str(body.get("recvID") or self.app_id),
            "session_type": int(
                body.get("sessionType") or SESSION_TYPE_DM,
            ),
            "content_type": content_type,
            "server_msg_id": body.get("serverMsgID"),
            "client_msg_id": body.get("clientMsgID"),
            "sender_nickname": body.get("senderNickname"),
        }
        native = {
            "channel_id": self.channel,
            "sender_id": send_id,
            "text": text,
            "content_parts": content_parts,
            "meta": meta,
            "session_id": self.resolve_session_id(send_id, meta),
        }
        if self._enqueue is None:
            logger.warning("openim: enqueue callback not set")
            return False
        self._enqueue(native)
        return True

    async def start(self) -> None:
        if not self.enabled:
            logger.info("openim channel disabled")
            return
        if not self.api_url or not self.app_id or not self.app_secret:
            raise ChannelError(
                channel_name="openim",
                message=(
                    "openim requires api_url, app_id, and app_secret "
                    "when enabled"
                ),
            )

        self._loop = asyncio.get_running_loop()
        await self._client.start()

        if not openim_sdk_available():
            raise ChannelError(
                channel_name="openim",
                message=(
                    "OpenIM WebSocket requires openim-sdk-core, "
                    "which should be installed with qwenpaw. "
                    "Reinstall the package and retry."
                ),
            )
        if not self.ws_url:
            raise ChannelError(
                channel_name="openim",
                message="openim ws_url is empty and could not be derived",
            )

        # 预热一次 token，尽早暴露凭证错误
        await self._client.get_user_token(self.app_id)

        self._ws_runner = OpenIMWSRunner(
            ws_url=self.ws_url,
            api_url=self.api_url,
            data_dir=self._data_dir(),
            robot_user_id=self.app_id,
            platform_id=self.platform_id,
            on_message=self._on_ws_message,
            token_provider=self._token_provider,
        )
        self._ws_runner.start_background(user_id=self.app_id)

        connected = await asyncio.to_thread(
            self._ws_runner.wait_connected,
            WS_START_CONNECT_TIMEOUT_S,
        )
        if not connected:
            detail = self._ws_runner.last_error or "timeout waiting connect"
            await self.stop()
            raise ChannelError(
                channel_name="openim",
                message=f"openim WebSocket connect failed: {detail}",
            )

        logger.info(
            "openim channel started (ws) app_id=%s api=%s ws=%s",
            self.app_id,
            self.api_url,
            self.ws_url,
        )

    async def stop(self) -> None:
        if self._ws_runner is not None:
            await asyncio.to_thread(self._ws_runner.stop)
            self._ws_runner = None
        await self._client.stop()
        self._loop = None
        logger.info("openim channel stopped")

    def _resolve_recv_id(self, to_handle: str) -> str:
        recv_id = to_handle
        if ":" in to_handle and to_handle.startswith("openim:"):
            recv_id = to_handle.split(":")[-1]
        return recv_id

    def _require_runner(self) -> OpenIMWSRunner:
        runner = self._ws_runner
        if runner is None or not runner.is_connected:
            raise ChannelError(
                channel_name="openim",
                message="openim WebSocket is not connected",
            )
        return runner

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return
        recv_id = self._resolve_recv_id(to_handle)
        body = f"{self.bot_prefix}{text}" if self.bot_prefix else text
        if not body.strip():
            return

        runner = self._require_runner()
        ok = await asyncio.to_thread(runner.send_text_sync, recv_id, body)
        if not ok:
            raise ChannelError(
                channel_name="openim",
                message=f"openim WebSocket send_text failed recv={recv_id}",
            )

    async def send_content_parts(
        self,
        to_handle: str,
        parts: List[OutgoingContentPart],
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """文本与媒体分开发送，避免把媒体 URL 拼进正文。"""
        if not self.enabled:
            return
        text_parts: List[str] = []
        media_parts: List[OutgoingContentPart] = []
        for part in parts:
            part_type = getattr(part, "type", None)
            if part_type == ContentType.TEXT and getattr(part, "text", None):
                text_parts.append(part.text or "")
            elif part_type == ContentType.REFUSAL and getattr(
                part,
                "refusal",
                None,
            ):
                text_parts.append(part.refusal or "")
            elif part_type in (
                ContentType.IMAGE,
                ContentType.VIDEO,
                ContentType.AUDIO,
                ContentType.FILE,
            ):
                media_parts.append(part)
        body = "\n".join(text_parts).strip()
        if body:
            await self.send(to_handle, body, meta)
        for media in media_parts:
            await self.send_media(to_handle, media, meta)

    async def send_media(
        self,
        to_handle: str,
        part: OutgoingContentPart,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """通过 WS SDK 发送图片 / 文件（语音无时长时按文件发送）。"""
        if not self.enabled:
            return
        recv_id = self._resolve_recv_id(to_handle)
        runner = self._require_runner()
        part_type = getattr(part, "type", None)

        if part_type == ContentType.IMAGE:
            url = str(getattr(part, "image_url", "") or "").strip()
            if not url:
                return
            local = file_url_to_local_path(url) or ""
            if local and Path(local).is_file():
                ok = await asyncio.to_thread(
                    runner.send_image_sync,
                    recv_id,
                    local,
                )
            else:
                ok = await asyncio.to_thread(
                    runner.send_image_by_url_sync,
                    recv_id,
                    url,
                )
            if not ok:
                raise ChannelError(
                    channel_name="openim",
                    message=f"openim send_image failed recv={recv_id}",
                )
            return

        if part_type == ContentType.FILE:
            url = str(
                getattr(part, "file_url", None)
                or getattr(part, "file_id", None)
                or "",
            ).strip()
            name = str(getattr(part, "filename", "") or "file")
            if not url:
                return
            local = file_url_to_local_path(url) or ""
            if local and Path(local).is_file():
                ok = await asyncio.to_thread(
                    runner.send_file_sync,
                    recv_id,
                    local,
                    file_name=name,
                )
            else:
                ok = await asyncio.to_thread(
                    runner.send_file_by_url_sync,
                    recv_id,
                    url,
                    file_name=name,
                )
            if not ok:
                raise ChannelError(
                    channel_name="openim",
                    message=f"openim send_file failed recv={recv_id}",
                )
            return

        if part_type == ContentType.AUDIO:
            # SDK send_sound 需要 duration；无可靠时长时退化为文件发送
            url = str(getattr(part, "data", "") or "").strip()
            if not url:
                return
            name = f"audio.{getattr(part, 'format', None) or 'bin'}"
            local = file_url_to_local_path(url) or ""
            if local and Path(local).is_file():
                ok = await asyncio.to_thread(
                    runner.send_file_sync,
                    recv_id,
                    local,
                    file_name=name,
                )
            else:
                ok = await asyncio.to_thread(
                    runner.send_file_by_url_sync,
                    recv_id,
                    url,
                    file_name=name,
                )
            if not ok:
                raise ChannelError(
                    channel_name="openim",
                    message=(
                        f"openim send_audio(as file) failed recv={recv_id}"
                    ),
                )
            return

        logger.debug("openim send_media skip unsupported type=%s", part_type)

    async def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "channel": self.channel,
                "status": "disabled",
                "detail": "OpenIM channel is disabled.",
            }
        runner = self._ws_runner
        if runner is None:
            return {
                "channel": self.channel,
                "status": "unhealthy",
                "detail": "OpenIM WebSocket runner is not started",
            }
        if not runner.is_connected:
            detail = runner.last_error or "not connected"
            return {
                "channel": self.channel,
                "status": "unhealthy",
                "detail": f"OpenIM WebSocket disconnected: {detail}",
            }
        return {
            "channel": self.channel,
            "status": "healthy",
            "detail": "OpenIM WebSocket long connection is active.",
        }
