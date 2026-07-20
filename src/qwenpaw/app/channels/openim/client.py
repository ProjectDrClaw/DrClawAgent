# -*- coding: utf-8 -*-
"""OpenIM REST client：仅用于获取 admin / user token（WS 登录）。"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Optional
from urllib.parse import urlparse, urlunparse

import httpx

from .constants import DEFAULT_HTTP_TIMEOUT_S, TOKEN_REFRESH_SKEW_S

logger = logging.getLogger(__name__)


def derive_ws_url(api_url: str, ws_url: str = "") -> str:
    """解析 WS 根地址；ws_url 为空时从 api_url 推导主机并使用 10001 端口。"""
    if (ws_url or "").strip():
        return ws_url.strip().rstrip("/")
    parsed = urlparse((api_url or "").strip())
    if not parsed.hostname:
        return ""
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = f"{parsed.hostname}:10001"
    return urlunparse((scheme, netloc, "", "", "", ""))


def ws_gateway_addr(ws_url: str) -> str:
    """缺少 /msg_gateway 时自动补全。"""
    base = (ws_url or "").rstrip("/")
    if not base:
        return ""
    if base.endswith("/msg_gateway"):
        return base
    return f"{base}/msg_gateway"


class OpenIMClient:
    """OpenIM API 客户端：仅换 token，不负责发消息。"""

    def __init__(
        self,
        api_url: str,
        secret: str,
        admin_user_id: str = "imAdmin",
        platform_id: int = 7,
        timeout: float = DEFAULT_HTTP_TIMEOUT_S,
    ) -> None:
        self.api_url = (api_url or "").rstrip("/")
        self.secret = secret or ""
        self.admin_user_id = admin_user_id or "imAdmin"
        self.platform_id = int(platform_id or 7)
        self._timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None
        self._admin_token: str = ""
        self._admin_expire_at: float = 0.0
        self._user_token: str = ""
        self._user_expire_at: float = 0.0
        self._user_token_uid: str = ""

    async def start(self) -> None:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout)

    async def stop(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._admin_token = ""
        self._admin_expire_at = 0.0
        self._user_token = ""
        self._user_expire_at = 0.0
        self._user_token_uid = ""

    def _ensure_http(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError("OpenIMClient not started")
        return self._http

    @staticmethod
    def _operation_id() -> str:
        return str(int(time.time() * 1000)) + "-" + uuid.uuid4().hex[:8]

    async def get_admin_token(self, *, force: bool = False) -> str:
        now = time.time()
        if (
            not force
            and self._admin_token
            and now < self._admin_expire_at - TOKEN_REFRESH_SKEW_S
        ):
            return self._admin_token

        if not self.api_url or not self.secret:
            raise ValueError("OpenIM api_url and secret are required")

        http = self._ensure_http()
        url = f"{self.api_url}/auth/get_admin_token"
        headers = {"operationID": self._operation_id()}
        body = {"secret": self.secret, "userID": self.admin_user_id}
        resp = await http.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        err_code = data.get("errCode", -1)
        if err_code != 0:
            raise RuntimeError(
                f"get_admin_token failed: errCode={err_code} "
                f"errMsg={data.get('errMsg')} errDlt={data.get('errDlt')}",
            )
        payload = data.get("data") or {}
        token = payload.get("token") or ""
        if not token:
            raise RuntimeError("get_admin_token returned empty token")
        expire_s = int(payload.get("expireTimeSeconds") or 0)
        self._admin_token = token
        self._admin_expire_at = now + max(expire_s, 60)
        return token

    async def get_user_token(
        self,
        user_id: str,
        *,
        force: bool = False,
    ) -> str:
        """获取机器人用户 token，供 WS 登录。"""
        now = time.time()
        if (
            not force
            and self._user_token
            and self._user_token_uid == user_id
            and now < self._user_expire_at - TOKEN_REFRESH_SKEW_S
        ):
            return self._user_token

        admin = await self.get_admin_token()
        http = self._ensure_http()
        url = f"{self.api_url}/auth/get_user_token"
        headers = {
            "operationID": self._operation_id(),
            "token": admin,
        }
        body = {"platformID": self.platform_id, "userID": user_id}
        resp = await http.post(url, json=body, headers=headers)
        if resp.status_code == 401:
            admin = await self.get_admin_token(force=True)
            headers["token"] = admin
            headers["operationID"] = self._operation_id()
            resp = await http.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        err_code = data.get("errCode", -1)
        if err_code != 0:
            raise RuntimeError(
                f"get_user_token failed: errCode={err_code} "
                f"errMsg={data.get('errMsg')} errDlt={data.get('errDlt')}",
            )
        payload = data.get("data") or {}
        token = payload.get("token") or ""
        if not token:
            raise RuntimeError("get_user_token returned empty token")
        expire_s = int(payload.get("expireTimeSeconds") or 0)
        self._user_token = token
        self._user_token_uid = user_id
        self._user_expire_at = now + max(expire_s, 60)
        return token
