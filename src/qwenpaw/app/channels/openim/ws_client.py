# -*- coding: utf-8 -*-
# pylint: disable=too-many-return-statements,too-many-statements
"""OpenIM WebSocket runner（对齐 openim-sdk-core OpenIMWSSDK API）。"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from .client import ws_gateway_addr
from .constants import (
    INBOUND_CONTENT_TYPES,
    SESSION_TYPE_DM,
    WS_BACKOFF_FACTOR,
    WS_INITIAL_RETRY_DELAY,
    WS_MAX_RETRY_DELAY,
    WS_START_CONNECT_TIMEOUT_S,
)

logger = logging.getLogger(__name__)

try:
    from openim_sdk import OpenIMWSSDK, WSConfig  # type: ignore

    _HAS_OPENIM_SDK = True
except ImportError:  # pragma: no cover - optional dependency
    OpenIMWSSDK = None  # type: ignore[misc, assignment]
    WSConfig = None  # type: ignore[misc, assignment]
    _HAS_OPENIM_SDK = False


MessageHandler = Callable[[dict[str, Any]], None]
TokenProvider = Callable[[], str]


def openim_sdk_available() -> bool:
    return _HAS_OPENIM_SDK


def _picture_base_info(info: Any) -> Optional[dict[str, Any]]:
    if info is None:
        return None
    if isinstance(info, dict):
        return {
            "uuid": str(info.get("uuid") or ""),
            "type": str(info.get("type") or ""),
            "size": int(info.get("size") or 0),
            "width": int(info.get("width") or 0),
            "height": int(info.get("height") or 0),
            "url": str(info.get("url") or ""),
        }
    return {
        "uuid": str(getattr(info, "uuid", "") or ""),
        "type": str(getattr(info, "type", "") or ""),
        "size": int(getattr(info, "size", 0) or 0),
        "width": int(getattr(info, "width", 0) or 0),
        "height": int(getattr(info, "height", 0) or 0),
        "url": str(getattr(info, "url", "") or ""),
    }


def _normalize_content_obj(content_obj: Any) -> Any:
    """将 SDK content_obj 转为可入队的 dict；无法识别时返回 None。"""
    if content_obj is None:
        return None
    name = type(content_obj).__name__
    if name == "TextElem":
        return {"content": getattr(content_obj, "content", "") or ""}
    if name == "PictureElem":
        return {
            "sourcePath": str(getattr(content_obj, "source_path", "") or ""),
            "sourcePicture": _picture_base_info(
                getattr(content_obj, "source_picture", None),
            ),
            "bigPicture": _picture_base_info(
                getattr(content_obj, "big_picture", None),
            ),
            "snapshotPicture": _picture_base_info(
                getattr(content_obj, "snapshot_picture", None),
            ),
        }
    if name == "FileElem":
        return {
            "filePath": str(getattr(content_obj, "file_path", "") or ""),
            "uuid": str(getattr(content_obj, "uuid", "") or ""),
            "sourceUrl": str(getattr(content_obj, "source_url", "") or ""),
            "fileName": str(getattr(content_obj, "file_name", "") or ""),
            "fileSize": int(getattr(content_obj, "file_size", 0) or 0),
            "fileType": str(getattr(content_obj, "file_type", "") or ""),
        }
    if name == "SoundElem":
        return {
            "uuid": str(getattr(content_obj, "uuid", "") or ""),
            "soundPath": str(getattr(content_obj, "sound_path", "") or ""),
            "sourceUrl": str(getattr(content_obj, "source_url", "") or ""),
            "dataSize": int(getattr(content_obj, "data_size", 0) or 0),
            "duration": int(getattr(content_obj, "duration", 0) or 0),
            "soundType": str(getattr(content_obj, "sound_type", "") or ""),
        }
    return None


def normalize_ws_message(msg: Any) -> Optional[dict[str, Any]]:
    """将 SDK WSMessage / dict 规范为统一字段。"""
    if msg is None:
        return None

    # 优先走 openim-sdk-core WSMessage 属性
    if not isinstance(msg, dict):
        send_id = str(getattr(msg, "send_id", None) or "")
        recv_id = str(getattr(msg, "recv_id", None) or "")
        content = getattr(msg, "content", None)
        content_obj = getattr(msg, "content_obj", None)
        normalized_obj = _normalize_content_obj(content_obj)
        if normalized_obj is not None:
            content = normalized_obj
        elif content_obj is not None and hasattr(content_obj, "content"):
            # TextElem / 单测 MagicMock：仅有 .content
            content = {"content": getattr(content_obj, "content", "")}
        content_type = getattr(msg, "content_type", None)
        session_type = getattr(msg, "session_type", None)
        server_msg_id = getattr(msg, "server_msg_id", None)
        client_msg_id = getattr(msg, "client_msg_id", None)
        nickname = getattr(msg, "sender_nickname", None)
        raw = getattr(msg, "raw", None)
        if isinstance(raw, dict) and not send_id:
            return normalize_ws_message(raw)
    else:
        send_id = str(msg.get("sendID") or msg.get("send_id") or "")
        recv_id = str(msg.get("recvID") or msg.get("recv_id") or "")
        content = msg.get("content")
        content_type = msg.get("contentType", msg.get("content_type"))
        session_type = msg.get("sessionType", msg.get("session_type"))
        server_msg_id = msg.get("serverMsgID") or msg.get("server_msg_id")
        client_msg_id = msg.get("clientMsgID") or msg.get("client_msg_id")
        nickname = msg.get("senderNickname") or msg.get("sender_nickname")

    try:
        content_type_i = int(content_type or 0)
    except (TypeError, ValueError):
        content_type_i = 0
    try:
        session_type_i = int(session_type or SESSION_TYPE_DM)
    except (TypeError, ValueError):
        session_type_i = SESSION_TYPE_DM

    if not send_id:
        return None

    return {
        "sendID": send_id,
        "recvID": recv_id,
        "content": content,
        "contentType": content_type_i,
        "sessionType": session_type_i,
        "serverMsgID": server_msg_id,
        "clientMsgID": client_msg_id,
        "senderNickname": nickname,
    }


class OpenIMWSRunner:
    """后台登录循环；消息回调在 SDK 线程执行。"""

    def __init__(
        self,
        *,
        ws_url: str,
        api_url: str,
        data_dir: Path,
        robot_user_id: str,
        platform_id: int,
        on_message: MessageHandler,
        token_provider: TokenProvider,
    ) -> None:
        self.ws_url = ws_url
        self.api_url = api_url
        self.data_dir = Path(data_dir)
        self.robot_user_id = robot_user_id
        self.platform_id = int(platform_id or 7)
        self.on_message = on_message
        self.token_provider = token_provider
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._sdk: Any = None
        self._sdk_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._user_id: str = ""
        self._last_error: str = ""
        self._login_ok = False
        self._kicked = False

    @property
    def is_connected(self) -> bool:
        return self._connected_event.is_set() and self._login_ok

    @property
    def last_error(self) -> str:
        return self._last_error

    def start_background(self, user_id: str) -> None:
        if not _HAS_OPENIM_SDK:
            raise RuntimeError(
                "openim-sdk-core is not installed; "
                "it is a required dependency of qwenpaw. "
                "Reinstall the package and retry.",
            )
        self._user_id = user_id
        self._stop_event.clear()
        self._connected_event.clear()
        self._login_ok = False
        self._kicked = False
        self._last_error = ""
        self._thread = threading.Thread(
            target=self._run_forever,
            name="openim-ws",
            daemon=True,
        )
        self._thread.start()

    def wait_connected(
        self,
        timeout: float = WS_START_CONNECT_TIMEOUT_S,
    ) -> bool:
        """阻塞等待首次 connect_success + login。"""
        deadline = time.time() + max(timeout, 0.1)
        while time.time() < deadline:
            if self._stop_event.is_set():
                return False
            if self.is_connected:
                return True
            if self._kicked:
                return False
            remaining = deadline - time.time()
            self._connected_event.wait(timeout=min(0.5, max(remaining, 0.05)))
        return self.is_connected

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        self._connected_event.clear()
        self._login_ok = False
        sdk = None
        with self._sdk_lock:
            sdk = self._sdk
            self._sdk = None
        if sdk is not None:
            for name in ("logout", "stop"):
                fn = getattr(sdk, name, None)
                if callable(fn):
                    try:
                        fn()
                    except Exception:
                        logger.debug(
                            "openim ws sdk.%s failed",
                            name,
                            exc_info=True,
                        )
                    break
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("openim ws thread did not stop within timeout")
        self._thread = None

    def send_text_sync(self, recv_id: str, text: str) -> bool:
        """任意线程调用 SDK send_text；成功需拿到 ack。"""
        return self._sdk_send(
            "send_text",
            lambda sdk: sdk.send_text(text, recv_id=recv_id),
        )

    def send_image_sync(self, recv_id: str, image_path: str) -> bool:
        """本地路径发图。"""
        return self._sdk_send(
            "send_image",
            lambda sdk: sdk.send_image(image_path, recv_id=recv_id),
        )

    def send_image_by_url_sync(
        self,
        recv_id: str,
        source_url: str,
        *,
        width: int = 0,
        height: int = 0,
    ) -> bool:
        """公网 URL 发图。"""
        return self._sdk_send(
            "send_image_by_url",
            lambda sdk: sdk.send_image_by_url(
                source_url=source_url,
                width=int(width or 0),
                height=int(height or 0),
                recv_id=recv_id,
            ),
        )

    def send_file_sync(
        self,
        recv_id: str,
        file_path: str,
        *,
        file_name: str = "",
        file_type: str = "",
    ) -> bool:
        """本地路径发文件。"""
        return self._sdk_send(
            "send_file",
            lambda sdk: sdk.send_file(
                file_path,
                recv_id=recv_id,
                file_name=file_name or "",
                file_type=file_type or "",
            ),
        )

    def send_file_by_url_sync(
        self,
        recv_id: str,
        source_url: str,
        *,
        file_name: str = "",
        file_type: str = "",
    ) -> bool:
        """公网 URL 发文件。"""
        return self._sdk_send(
            "send_file_by_url",
            lambda sdk: sdk.send_file_by_url(
                source_url=source_url,
                file_name=file_name or "file",
                recv_id=recv_id,
                file_type=file_type or "",
            ),
        )

    def _sdk_send(self, method: str, call: Callable[[Any], Any]) -> bool:
        if not self.is_connected:
            return False
        with self._sdk_lock:
            sdk = self._sdk
        if sdk is None or not hasattr(sdk, method):
            return False
        with self._send_lock:
            try:
                ack = call(sdk)
            except Exception:
                logger.exception("openim ws %s failed", method)
                return False
        return self._ack_ok(ack)

    @staticmethod
    def _ack_ok(ack: Any) -> bool:
        if ack is None:
            return True
        if isinstance(ack, dict):
            return bool(
                ack.get("serverMsgID")
                or ack.get("clientMsgID")
                or ack.get("server_msg_id")
                or ack.get("client_msg_id"),
            )
        return True

    def _mark_connected(self) -> None:
        self._login_ok = True
        self._kicked = False
        self._last_error = ""
        self._connected_event.set()

    def _mark_disconnected(self, reason: str = "") -> None:
        self._login_ok = False
        self._connected_event.clear()
        if reason:
            self._last_error = reason

    def _handle_raw(self, msg: Any) -> None:
        normalized = normalize_ws_message(msg)
        if not normalized:
            return
        ctype = int(normalized.get("contentType") or 0)
        if ctype not in INBOUND_CONTENT_TYPES:
            return
        try:
            self.on_message(normalized)
        except Exception:
            logger.exception("openim ws on_message handler failed")

    def _fetch_token(self) -> str:
        token = (self.token_provider() or "").strip()
        if not token:
            raise RuntimeError("openim token_provider returned empty token")
        return token

    def _run_forever(self) -> None:
        retry_delay = WS_INITIAL_RETRY_DELAY
        gateway = ws_gateway_addr(self.ws_url)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        while not self._stop_event.is_set():
            sdk = None
            session_ok = False
            try:
                assert WSConfig is not None and OpenIMWSSDK is not None
                token = self._fetch_token()

                cfg = WSConfig(
                    ws_addr=gateway,
                    api_addr=self.api_url,
                    data_dir=str(self.data_dir),
                    platform_id=self.platform_id,
                    auto_sync_on_connect=True,
                    auto_sync_on_reconnect=True,
                    auto_reconnect=True,
                )

                def _on_connect_success() -> None:
                    self._mark_connected()
                    logger.info(
                        "openim WebSocket connected user=%s",
                        self._user_id,
                    )

                def _on_connect_failed(exc: Exception) -> None:
                    self._mark_disconnected(str(exc))
                    logger.warning("openim WebSocket connect failed: %s", exc)

                def _on_kicked() -> None:
                    self._kicked = True
                    self._mark_disconnected("kicked offline")
                    logger.error(
                        "openim WebSocket kicked offline user=%s",
                        self._user_id,
                    )
                    # 触发外层重连：停掉当前 SDK
                    with self._sdk_lock:
                        cur = self._sdk
                    if cur is not None:
                        try:
                            cur.logout()
                        except Exception:
                            logger.debug(
                                "openim logout after kick failed",
                                exc_info=True,
                            )

                def _on_error(exc: Exception) -> None:
                    self._last_error = str(exc)
                    logger.warning("openim WebSocket sdk error: %s", exc)

                sdk = OpenIMWSSDK(
                    cfg,
                    on_recv_new_message=self._handle_raw,
                    on_recv_offline_new_message=self._handle_raw,
                    on_connect_success=_on_connect_success,
                    on_connect_failed=_on_connect_failed,
                    on_kicked_offline=_on_kicked,
                    on_error=_on_error,
                )
                with self._sdk_lock:
                    self._sdk = sdk

                logger.info(
                    "openim WebSocket login gateway=%s user=%s platform=%s",
                    gateway,
                    self._user_id,
                    self.platform_id,
                )
                sdk.login(user_id=self._user_id, token=token)
                sdk.start()
                session_ok = True
                retry_delay = WS_INITIAL_RETRY_DELAY

                # SDK 内部 auto_reconnect；此处看守直到 stop / kicked
                while not self._stop_event.is_set() and not self._kicked:
                    if self._stop_event.wait(timeout=1.0):
                        break

            except Exception as exc:
                self._mark_disconnected(str(exc))
                if self._stop_event.is_set():
                    logger.debug("openim ws stopped during connect")
                else:
                    logger.exception(
                        "openim WebSocket failed, will reconnect",
                    )
            finally:
                self._mark_disconnected(self._last_error)
                with self._sdk_lock:
                    self._sdk = None
                if sdk is not None:
                    try:
                        sdk.logout()
                    except Exception:
                        logger.debug(
                            "openim ws cleanup logout failed",
                            exc_info=True,
                        )

            if self._stop_event.is_set():
                break
            if session_ok and not self._kicked:
                retry_delay = WS_INITIAL_RETRY_DELAY
            self._kicked = False
            logger.info(
                "openim WebSocket reconnecting in %.1fs...",
                retry_delay,
            )
            self._stop_event.wait(timeout=retry_delay)
            retry_delay = min(
                retry_delay * WS_BACKOFF_FACTOR,
                WS_MAX_RETRY_DELAY,
            )
            time.sleep(0.05)
