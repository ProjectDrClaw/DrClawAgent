#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenIM 出站 WS 探针：admin/user token → login → connect → 可选 send。

用法示例：

  set OPENIM_API_URL=http://10.110.177.132:10002
  set OPENIM_WS_URL=ws://10.110.177.132:10001
  set OPENIM_APP_SECRET=openIM123
  set OPENIM_APP_ID=drclaw_bot
  python scripts/probe_openim_ws.py

可选：
  OPENIM_ADMIN_USER_ID=imAdmin
  OPENIM_PLATFORM_ID=7
  OPENIM_RECV_ID=<对端 userID>   # 设置后会尝试 send_text
  OPENIM_WAIT_S=8                # 连接后等待秒数
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import httpx

try:
    from openim_sdk import OpenIMWSSDK, WSConfig
except ImportError:
    print(
        "ERROR: openim-sdk-core 未安装（应为 qwenpaw 必装依赖）。" + "请重新安装 qwenpaw 后重试。",
        file=sys.stderr,
    )
    sys.exit(2)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def _operation_id() -> str:
    return str(int(time.time() * 1000)) + "-" + uuid.uuid4().hex[:8]


def derive_ws_url(api_url: str, ws_url: str) -> str:
    if ws_url:
        return ws_url.rstrip("/")
    from urllib.parse import urlparse, urlunparse

    p = urlparse(api_url)
    if not p.hostname:
        return ""
    scheme = "wss" if p.scheme == "https" else "ws"
    return urlunparse((scheme, f"{p.hostname}:10001", "", "", "", ""))


def ws_gateway(ws_url: str) -> str:
    base = ws_url.rstrip("/")
    if base.endswith("/msg_gateway"):
        return base
    return f"{base}/msg_gateway"


def get_admin_token(
    client: httpx.Client,
    api_url: str,
    secret: str,
    admin_user_id: str,
) -> str:
    url = f"{api_url}/auth/get_admin_token"
    resp = client.post(
        url,
        headers={"operationID": _operation_id()},
        json={"secret": secret, "userID": admin_user_id},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errCode", -1) != 0:
        raise RuntimeError(f"get_admin_token failed: {data}")
    token = (data.get("data") or {}).get("token") or ""
    if not token:
        raise RuntimeError("get_admin_token returned empty token")
    return token


def get_user_token(
    client: httpx.Client,
    api_url: str,
    admin_token: str,
    user_id: str,
    platform_id: int,
) -> str:
    url = f"{api_url}/auth/get_user_token"
    resp = client.post(
        url,
        headers={
            "operationID": _operation_id(),
            "token": admin_token,
        },
        json={"platformID": platform_id, "userID": user_id},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errCode", -1) != 0:
        raise RuntimeError(f"get_user_token failed: {data}")
    token = (data.get("data") or {}).get("token") or ""
    if not token:
        raise RuntimeError("get_user_token returned empty token")
    return token


def main() -> int:  # pylint: disable=too-many-statements
    api_url = _env("OPENIM_API_URL", "http://127.0.0.1:10002").rstrip("/")
    ws_url = derive_ws_url(api_url, _env("OPENIM_WS_URL"))
    secret = _env("OPENIM_APP_SECRET")
    app_id = _env("OPENIM_APP_ID", "drclaw_bot")
    admin_user_id = _env("OPENIM_ADMIN_USER_ID", "imAdmin")
    platform_id = int(_env("OPENIM_PLATFORM_ID", "7") or "7")
    recv_id = _env("OPENIM_RECV_ID")
    wait_s = float(_env("OPENIM_WAIT_S", "8") or "8")

    if not api_url or not secret or not app_id:
        print("ERROR: OPENIM_API_URL / OPENIM_APP_SECRET / OPENIM_APP_ID 必填")
        return 2

    gateway = ws_gateway(ws_url)
    print(f"[probe] api={api_url}")
    print(f"[probe] ws={gateway}")
    print(f"[probe] app_id={app_id} platform_id={platform_id}")

    # 1) REST tokens
    try:
        with httpx.Client(timeout=30.0) as http:
            print("[probe] get_admin_token ...")
            admin_token = get_admin_token(
                http,
                api_url,
                secret,
                admin_user_id,
            )
            print("[probe] get_admin_token OK")
            print("[probe] get_user_token ...")
            user_token = get_user_token(
                http,
                api_url,
                admin_token,
                app_id,
                platform_id,
            )
            print("[probe] get_user_token OK")
    except httpx.HTTPError as exc:
        print(f"[probe] FAIL REST: {exc}")
        resp = getattr(exc, "response", None)
        if resp is not None:
            print(
                f"[probe] status={resp.status_code} body={resp.text[:500]!r}",
            )
        print(
            "[probe] 请确认 OpenIM API 可达，且 secret/admin_user_id 正确。",
        )
        return 1

    # 2) WS login + connect
    connected = threading.Event()
    errors: list[str] = []
    received: list[str] = []

    def on_connect_success() -> None:
        print("[probe] on_connect_success")
        connected.set()

    def on_connect_failed(exc: Exception) -> None:
        msg = f"connect_failed: {exc}"
        print(f"[probe] {msg}")
        errors.append(msg)

    def on_error(exc: Exception) -> None:
        msg = f"sdk_error: {exc}"
        print(f"[probe] {msg}")
        errors.append(msg)

    def on_kicked() -> None:
        print("[probe] kicked_offline")
        errors.append("kicked_offline")

    def on_msg(msg: object) -> None:
        send_id = getattr(msg, "send_id", None) or ""
        ctype = getattr(msg, "content_type", None)
        content_obj = getattr(msg, "content_obj", None)
        text = getattr(content_obj, "content", None) if content_obj else None
        line = f"recv send_id={send_id} content_type={ctype} text={text!r}"
        print(f"[probe] {line}")
        received.append(line)

    data_dir = Path(tempfile.mkdtemp(prefix="openim_probe_"))
    print(f"[probe] data_dir={data_dir}")

    sdk = OpenIMWSSDK(
        WSConfig(
            ws_addr=gateway,
            api_addr=api_url,
            data_dir=str(data_dir),
            platform_id=platform_id,
            auto_sync_on_connect=True,
            auto_reconnect=False,
        ),
        on_recv_new_message=on_msg,
        on_recv_offline_new_message=on_msg,
        on_connect_success=on_connect_success,
        on_connect_failed=on_connect_failed,
        on_kicked_offline=on_kicked,
        on_error=on_error,
    )

    try:
        print("[probe] login ...")
        sdk.login(user_id=app_id, token=user_token)
        print("[probe] start ...")
        sdk.start()
        if not connected.wait(timeout=20.0):
            print("[probe] FAIL: wait connect_success timeout")
            if errors:
                print("[probe] errors:", "; ".join(errors))
            return 1
        print("[probe] CONNECTED")

        if recv_id:
            print(f"[probe] send_text -> {recv_id} ...")
            ack = sdk.send_text(
                f"[probe] hello from openim probe {int(time.time())}",
                recv_id=recv_id,
            )
            print(f"[probe] send ack={ack!r}")
        else:
            print("[probe] skip send (set OPENIM_RECV_ID to test send)")

        print(f"[probe] wait {wait_s}s for inbound ...")
        time.sleep(wait_s)
        print(f"[probe] received={len(received)}")
        print("[probe] OK")
        return 0
    except Exception as exc:
        print(f"[probe] FAIL: {exc}")
        return 1
    finally:
        try:
            sdk.logout()
        except Exception as exc:
            print(f"[probe] logout warn: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
