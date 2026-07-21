# -*- coding: utf-8 -*-
# pylint: disable=too-many-return-statements,too-many-instance-attributes
# pylint: disable=too-many-branches
"""OpenIM channel：出站 WS 收消息 + SDK 发消息。"""
from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import uuid4

from qwenpaw.schemas import (
    AudioContent,
    FileContent,
    ImageContent,
    TextContent,
    VideoContent,
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
    AT_ALL_TAG,
    CONTENT_TYPE_AT_TEXT,
    CONTENT_TYPE_FILE,
    CONTENT_TYPE_PICTURE,
    CONTENT_TYPE_SOUND,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_VIDEO,
    DEFAULT_MEDIA_DURATION_S,
    INBOUND_CONTENT_TYPES,
    INBOUND_SESSION_TYPES,
    PROCESSED_MSG_IDS_MAX,
    SESSION_TYPE_DM,
    SESSION_TYPE_GROUP,
    SESSION_TYPE_SUPER_GROUP,
    WS_START_CONNECT_TIMEOUT_S,
)
from .credentials import resolve_app_secret, resolve_identity
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


def parse_video_meta(content: Any) -> Tuple[str, int, str, str]:
    """解析视频 URL / 时长 / 封面 / 类型。"""
    obj = _as_content_dict(content)
    url = str(obj.get("videoUrl") or obj.get("video_url") or "").strip()
    duration = int(obj.get("duration") or 0)
    snapshot = str(
        obj.get("snapshotUrl") or obj.get("snapshot_url") or "",
    ).strip()
    video_type = str(
        obj.get("videoType") or obj.get("video_type") or "",
    ).strip()
    return url, duration, snapshot, video_type


def parse_at_text_content(content: Any) -> str:
    """解析 @文本消息正文。"""
    obj = _as_content_dict(content)
    if obj:
        text = obj.get("text")
        if text is not None:
            return str(text)
        if "content" in obj:
            return str(obj.get("content") or "")
    if isinstance(content, str):
        return content
    return ""


def _at_user_ids_from_content(content: Any) -> List[str]:
    obj = _as_content_dict(content)
    raw = obj.get("atUserList") or obj.get("at_user_list") or []
    if not isinstance(raw, list):
        return []
    return [str(v) for v in raw if v is not None and str(v)]


def detect_bot_mentioned(body: Dict[str, Any], *, app_id: str) -> bool:
    """判断消息是否 @ 了机器人（含 @全体）。"""
    if not app_id:
        return False
    at_list = [
        str(v)
        for v in (body.get("atUserIDList") or body.get("at_user_id_list") or [])
        if v is not None
    ]
    at_list.extend(_at_user_ids_from_content(body.get("content")))
    normalized = {x for x in at_list if x}
    if app_id in normalized or AT_ALL_TAG in normalized:
        return True
    obj = _as_content_dict(body.get("content"))
    if obj.get("isAtSelf") or obj.get("is_at_self"):
        return True
    return False


def strip_bot_at_text(text: str, content: Any, *, app_id: str) -> str:
    """去掉正文中对机器人的 @ 昵称占位。"""
    if not text:
        return ""
    result = text
    obj = _as_content_dict(content)
    infos = obj.get("atUsersInfo") or obj.get("at_users_info") or []
    if isinstance(infos, list):
        for info in infos:
            if not isinstance(info, dict):
                continue
            uid = str(info.get("atUserID") or info.get("at_user_id") or "")
            nick = str(
                info.get("groupNickname") or info.get("group_nickname") or "",
            ).strip()
            if uid == app_id and nick:
                result = result.replace(f"@{nick}", "")
    return result.strip()


def is_group_session(session_type: int) -> bool:
    return session_type in (SESSION_TYPE_GROUP, SESSION_TYPE_SUPER_GROUP)


def should_handle_inbound(
    body: Dict[str, Any],
    *,
    app_id: str,
) -> bool:
    """处理对端发给机器人的单聊/群聊文本、@文本、图片、语音、视频、文件。"""
    if not app_id:
        return False
    send_id = str(body.get("sendID") or "")
    recv_id = str(body.get("recvID") or "")
    group_id = str(body.get("groupID") or body.get("group_id") or "")
    if not send_id or send_id == app_id:
        return False
    try:
        session_type = int(body.get("sessionType") or SESSION_TYPE_DM)
    except (TypeError, ValueError):
        return False
    if session_type not in INBOUND_SESSION_TYPES:
        return False
    if is_group_session(session_type):
        if not group_id:
            return False
    else:
        # 单聊：recv 为空或为机器人
        if recv_id and recv_id != app_id:
            return False
    try:
        content_type = int(body.get("contentType") or 0)
    except (TypeError, ValueError):
        return False
    if content_type not in INBOUND_CONTENT_TYPES:
        return False
    content = body.get("content")
    if content_type in (CONTENT_TYPE_TEXT, CONTENT_TYPE_AT_TEXT):
        text = (
            parse_at_text_content(content)
            if content_type == CONTENT_TYPE_AT_TEXT
            else parse_text_content(content)
        )
        return bool(text.strip()) or content_type == CONTENT_TYPE_AT_TEXT
    if content_type == CONTENT_TYPE_PICTURE:
        return bool(parse_picture_meta(content)[0])
    if content_type == CONTENT_TYPE_FILE:
        return bool(parse_file_meta(content)[0])
    if content_type == CONTENT_TYPE_SOUND:
        return bool(parse_sound_meta(content)[0])
    if content_type == CONTENT_TYPE_VIDEO:
        return bool(parse_video_meta(content)[0])
    return False


def build_inbound_parts(
    content_type: int,
    content: Any,
    *,
    app_id: str = "",
) -> Tuple[str, List[Any]]:
    """按 contentType 构造 text + content_parts。"""
    if content_type == CONTENT_TYPE_TEXT:
        text = parse_text_content(content)
        return text, [TextContent(type=ContentType.TEXT, text=text)]
    if content_type == CONTENT_TYPE_AT_TEXT:
        text = parse_at_text_content(content)
        if app_id:
            text = strip_bot_at_text(text, content, app_id=app_id)
        if not text.strip():
            text = " "
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
    if content_type == CONTENT_TYPE_VIDEO:
        url, _, _, _ = parse_video_meta(content)
        return "", [
            VideoContent(type=ContentType.VIDEO, video_url=url),
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
        share_session_in_group: bool = False,
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
        # 配置可填数字 userID 或编码后的 App ID；SDK 登录用 OpenIM userID
        raw_id = (app_id or "").strip()
        if raw_id:
            self.app_id, self.encoded_app_id = resolve_identity(raw_id)
        else:
            self.app_id = ""
            self.encoded_app_id = ""
        self.app_secret = resolve_app_secret(
            self.encoded_app_id or self.app_id,
            app_secret or "",
        )
        self.bot_prefix = bot_prefix or ""
        self.ws_url = derive_ws_url(self.api_url, ws_url or "")
        self.admin_user_id = admin_user_id or "imAdmin"
        self.platform_id = int(platform_id or 7)
        self.share_session_in_group = bool(share_session_in_group)
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
            share_session_in_group=(
                os.getenv("OPENIM_SHARE_SESSION_IN_GROUP", "0") == "1"
            ),
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
            share_session_in_group=bool(
                getattr(config, "share_session_in_group", False),
            ),
        )

    def resolve_session_id(
        self,
        sender_id: str,
        channel_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        meta = channel_meta or {}
        if meta.get("is_group"):
            group_id = str(meta.get("group_id") or "")
            if self.share_session_in_group:
                return f"openim:group:{group_id}"
            return f"openim:group:{group_id}:{sender_id}"
        return f"openim:dm:{sender_id}"

    def get_to_handle_from_request(self, request: "AgentRequest") -> str:
        meta = getattr(request, "channel_meta", None) or {}
        if meta.get("is_group"):
            return f"openim:group:{meta.get('group_id', '')}"
        return str(
            meta.get("sender_id")
            or getattr(request, "user_id", "")
            or "",
        )

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

    def _media_dir(self) -> Path:
        path = self._data_dir() / "media"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _download_media_to_local(
        self,
        url: str,
        *,
        msg_id: str = "",
        kind: str = "media",
        type_hint: str = "",
        default_ext: str = "bin",
    ) -> Optional[str]:
        """下载远程媒体到本地 media_dir（对齐飞书落盘后再入队）。"""
        raw = (url or "").strip()
        if not raw:
            return None
        if os.path.isfile(raw):
            return raw
        if raw.startswith("file://"):
            local = urllib.request.url2pathname(urlparse(raw).path)
            return local if os.path.isfile(local) else None

        ext = ""
        if type_hint:
            if "/" in type_hint:
                ext = type_hint.rsplit("/", 1)[-1]
            else:
                ext = type_hint.lstrip(".")
        if not ext:
            path_name = urlparse(raw).path
            guessed = mimetypes.guess_extension(
                mimetypes.guess_type(path_name)[0] or "",
            )
            if guessed:
                ext = guessed.lstrip(".")
            else:
                suffix = Path(path_name).suffix.lstrip(".")
                ext = suffix or default_ext
        safe_id = "".join(c for c in (msg_id or uuid4().hex) if c.isalnum())[
            :32
        ] or uuid4().hex
        dest = self._media_dir() / f"{safe_id}_{kind}.{ext}"
        try:
            urllib.request.urlretrieve(raw, dest)  # noqa: S310
            if dest.is_file() and dest.stat().st_size > 0:
                return str(dest.resolve())
            logger.warning("openim %s download empty: %s", kind, raw[:120])
            return None
        except Exception:
            logger.exception(
                "openim %s download failed url=%s",
                kind,
                raw[:120],
            )
            return None

    def _download_sound_to_local(
        self,
        url: str,
        *,
        msg_id: str = "",
        sound_type: str = "",
    ) -> Optional[str]:
        return self._download_media_to_local(
            url,
            msg_id=msg_id,
            kind="audio",
            type_hint=sound_type,
            default_ext="m4a",
        )

    def _download_video_to_local(
        self,
        url: str,
        *,
        msg_id: str = "",
        video_type: str = "",
    ) -> Optional[str]:
        return self._download_media_to_local(
            url,
            msg_id=msg_id,
            kind="video",
            type_hint=video_type,
            default_ext="mp4",
        )

    def _localize_audio_parts(
        self,
        content_parts: List[Any],
        *,
        msg_id: str = "",
    ) -> List[Any]:
        """将远程语音 URL 落盘为本地路径。"""
        out: List[Any] = []
        for part in content_parts:
            if getattr(part, "type", None) != ContentType.AUDIO:
                out.append(part)
                continue
            data = getattr(part, "data", None)
            fmt = str(getattr(part, "format", "") or "")
            if not isinstance(data, str) or not data.strip():
                out.append(part)
                continue
            local = self._download_sound_to_local(
                data.strip(),
                msg_id=msg_id,
                sound_type=fmt,
            )
            if local:
                out.append(
                    AudioContent(
                        type=ContentType.AUDIO,
                        data=local,
                        format=fmt or "audio",
                    ),
                )
            else:
                # 下载失败仍保留原 URL，交由 media_hook 再试
                out.append(part)
        return out

    def _localize_video_parts(
        self,
        content_parts: List[Any],
        *,
        msg_id: str = "",
        video_type: str = "",
    ) -> List[Any]:
        """将远程视频落盘，并按飞书方式改为 FileContent。"""
        out: List[Any] = []
        for part in content_parts:
            if getattr(part, "type", None) != ContentType.VIDEO:
                out.append(part)
                continue
            url = getattr(part, "video_url", None)
            if not isinstance(url, str) or not url.strip():
                out.append(part)
                continue
            local = self._download_video_to_local(
                url.strip(),
                msg_id=msg_id,
                video_type=video_type,
            )
            if local:
                out.append(
                    FileContent(
                        type=ContentType.FILE,
                        file_url=local,
                        filename=Path(local).name,
                    ),
                )
            else:
                out.append(part)
        return out

    def _localize_file_parts(
        self,
        content_parts: List[Any],
        *,
        msg_id: str = "",
    ) -> List[Any]:
        """将远程文件落盘为本地 FileContent（对齐飞书）。"""
        out: List[Any] = []
        for part in content_parts:
            if getattr(part, "type", None) != ContentType.FILE:
                out.append(part)
                continue
            url = getattr(part, "file_url", None)
            name = str(getattr(part, "filename", None) or "file").strip() or "file"
            if not isinstance(url, str) or not url.strip():
                out.append(part)
                continue
            type_hint = Path(name).suffix.lstrip(".")
            local = self._download_media_to_local(
                url.strip(),
                msg_id=msg_id,
                kind="file",
                type_hint=type_hint,
                default_ext="bin",
            )
            if local:
                out.append(
                    FileContent(
                        type=ContentType.FILE,
                        file_url=local,
                        filename=name if name != "file" else Path(local).name,
                    ),
                )
            else:
                out.append(part)
        return out

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
            session_type = int(body.get("sessionType") or SESSION_TYPE_DM)
        except (TypeError, ValueError):
            return False
        group_id = str(body.get("groupID") or body.get("group_id") or "")
        is_group = is_group_session(session_type)
        bot_mentioned = detect_bot_mentioned(body, app_id=self.app_id)
        meta = {
            "recv_id": str(body.get("recvID") or self.app_id),
            "session_type": session_type,
            "content_type": content_type,
            "server_msg_id": body.get("serverMsgID"),
            "client_msg_id": body.get("clientMsgID"),
            "sender_nickname": body.get("senderNickname"),
            "sender_id": send_id,
            "is_group": is_group,
            "group_id": group_id if is_group else "",
            "bot_mentioned": bot_mentioned,
        }
        if content_type == CONTENT_TYPE_SOUND:
            _, duration, _ = parse_sound_meta(body.get("content"))
            if duration > 0:
                meta["duration"] = duration
            video_type = ""
        elif content_type == CONTENT_TYPE_VIDEO:
            _, duration, snapshot, video_type = parse_video_meta(
                body.get("content"),
            )
            if duration > 0:
                meta["duration"] = duration
            if snapshot:
                meta["snapshot_url"] = snapshot
        else:
            video_type = ""
        if not self._check_group_mention(is_group, meta):
            logger.debug(
                "openim skip group message without mention group=%s",
                group_id,
            )
            return False
        text, content_parts = build_inbound_parts(
            content_type,
            body.get("content"),
            app_id=self.app_id,
        )
        if not content_parts:
            return False
        if content_type == CONTENT_TYPE_SOUND:
            content_parts = self._localize_audio_parts(
                content_parts,
                msg_id=msg_id,
            )
        elif content_type == CONTENT_TYPE_VIDEO:
            content_parts = self._localize_video_parts(
                content_parts,
                msg_id=msg_id,
                video_type=video_type,
            )
        elif content_type == CONTENT_TYPE_FILE:
            content_parts = self._localize_file_parts(
                content_parts,
                msg_id=msg_id,
            )
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

    def _resolve_send_target(
        self,
        to_handle: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """返回 (recv_id, group_id)；群聊只填 group_id。"""
        meta = meta or {}
        handle = to_handle or ""
        if (
            meta.get("is_group")
            or handle.startswith("openim:group:")
            or handle.startswith("group:")
        ):
            raw = (
                str(meta.get("group_id") or "")
                or handle.removeprefix("openim:group:")
                or handle.removeprefix("group:")
            )
            # share_session=false 时 handle 可能是 openim:group:{gid}:{uid}
            group_id = raw.split(":", 1)[0] if raw else ""
            return "", group_id
        recv_id = self._resolve_recv_id(handle)
        if not recv_id:
            recv_id = str(meta.get("sender_id") or "")
        return recv_id, ""

    @staticmethod
    def _resolve_session_type(
        meta: Optional[Dict[str, Any]],
        *,
        group_id: str = "",
    ) -> Optional[int]:
        """解析出站 sessionType。

        App 建群为工作群（超级群 sessionType=3）；SDK 在未传时默认普通群 2，
        会导致群成员收不到机器人回复。群聊优先用入站 meta，缺省用超级群 3。
        """
        meta = meta or {}
        raw = meta.get("session_type")
        if raw is not None:
            try:
                st = int(raw)
            except (TypeError, ValueError):
                st = None
            else:
                if group_id:
                    if st in (SESSION_TYPE_GROUP, SESSION_TYPE_SUPER_GROUP):
                        return st
                elif st == SESSION_TYPE_DM:
                    return st
        if group_id:
            return SESSION_TYPE_SUPER_GROUP
        return SESSION_TYPE_DM if meta else None

    @staticmethod
    def _media_duration(
        meta: Optional[Dict[str, Any]],
        part: Any = None,
    ) -> int:
        """解析出站媒体时长；缺省用 DEFAULT_MEDIA_DURATION_S。"""
        candidates = []
        if meta:
            for key in (
                "duration",
                "media_duration",
                "video_duration",
                "sound_duration",
            ):
                if meta.get(key) is not None:
                    candidates.append(meta.get(key))
        if part is not None:
            candidates.append(getattr(part, "duration", None))
        for raw in candidates:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
        return DEFAULT_MEDIA_DURATION_S

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
        recv_id, group_id = self._resolve_send_target(to_handle, meta)
        body = f"{self.bot_prefix}{text}" if self.bot_prefix else text
        if not body.strip():
            return
        if not recv_id and not group_id:
            raise ChannelError(
                channel_name="openim",
                message="openim send target missing recv_id/group_id",
            )

        runner = self._require_runner()
        session_type = self._resolve_session_type(meta, group_id=group_id)
        ok = await asyncio.to_thread(
            runner.send_text_sync,
            recv_id,
            body,
            group_id=group_id,
            session_type=session_type,
        )
        if not ok:
            raise ChannelError(
                channel_name="openim",
                message=(
                    "openim WebSocket send_text failed "
                    f"recv={recv_id} group={group_id} "
                    f"session_type={session_type}"
                ),
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
        """通过 WS SDK 发送图片 / 文件 / 语音 / 视频。"""
        if not self.enabled:
            return
        recv_id, group_id = self._resolve_send_target(to_handle, meta)
        if not recv_id and not group_id:
            raise ChannelError(
                channel_name="openim",
                message="openim send_media target missing recv_id/group_id",
            )
        runner = self._require_runner()
        part_type = getattr(part, "type", None)
        duration = self._media_duration(meta, part)
        session_type = self._resolve_session_type(meta, group_id=group_id)

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
                    group_id=group_id,
                    session_type=session_type,
                )
            else:
                ok = await asyncio.to_thread(
                    runner.send_image_by_url_sync,
                    recv_id,
                    url,
                    group_id=group_id,
                    session_type=session_type,
                )
            if not ok:
                raise ChannelError(
                    channel_name="openim",
                    message=(
                        f"openim send_image failed "
                        f"recv={recv_id} group={group_id} "
                        f"session_type={session_type}"
                    ),
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
                    group_id=group_id,
                    session_type=session_type,
                )
            else:
                ok = await asyncio.to_thread(
                    runner.send_file_by_url_sync,
                    recv_id,
                    url,
                    file_name=name,
                    group_id=group_id,
                    session_type=session_type,
                )
            if not ok:
                raise ChannelError(
                    channel_name="openim",
                    message=(
                        f"openim send_file failed "
                        f"recv={recv_id} group={group_id} "
                        f"session_type={session_type}"
                    ),
                )
            return

        if part_type == ContentType.AUDIO:
            url = str(getattr(part, "data", "") or "").strip()
            if not url:
                return
            sound_type = str(getattr(part, "format", "") or "")
            local = file_url_to_local_path(url) or ""
            if local and Path(local).is_file():
                ok = await asyncio.to_thread(
                    runner.send_sound_sync,
                    recv_id,
                    local,
                    duration=duration,
                    sound_type=sound_type,
                    group_id=group_id,
                    session_type=session_type,
                )
            else:
                ok = await asyncio.to_thread(
                    runner.send_sound_by_url_sync,
                    recv_id,
                    url,
                    duration=duration,
                    sound_type=sound_type,
                    group_id=group_id,
                    session_type=session_type,
                )
            if not ok:
                raise ChannelError(
                    channel_name="openim",
                    message=(
                        f"openim send_sound failed "
                        f"recv={recv_id} group={group_id} "
                        f"session_type={session_type}"
                    ),
                )
            return

        if part_type == ContentType.VIDEO:
            url = str(getattr(part, "video_url", "") or "").strip()
            if not url:
                return
            snapshot = str((meta or {}).get("snapshot_url") or "")
            local = file_url_to_local_path(url) or ""
            if local and Path(local).is_file():
                ok = await asyncio.to_thread(
                    runner.send_video_sync,
                    recv_id,
                    local,
                    duration=duration,
                    snapshot_path=snapshot
                    if snapshot and Path(snapshot).is_file()
                    else "",
                    group_id=group_id,
                    session_type=session_type,
                )
            else:
                ok = await asyncio.to_thread(
                    runner.send_video_by_url_sync,
                    recv_id,
                    url,
                    duration=duration,
                    snapshot_url=snapshot,
                    group_id=group_id,
                    session_type=session_type,
                )
            if not ok:
                raise ChannelError(
                    channel_name="openim",
                    message=(
                        f"openim send_video failed "
                        f"recv={recv_id} group={group_id} "
                        f"session_type={session_type}"
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
