# -*- coding: utf-8 -*-
"""Tauri sidecar environment variable helpers.

Keep this dependency-light: the Tauri entry imports it before qwenpaw.constant
has read import-time environment variables.
"""

import os

from qwenpaw.env_resolve import drclaw_env, get_env

DESKTOP_APP_ENV = drclaw_env("DESKTOP_APP")
DESKTOP_API_HOST_ENV = drclaw_env("DESKTOP_API_HOST")
DESKTOP_CORS_ORIGINS_ENV = drclaw_env("CORS_ORIGINS")
# 不含尾部空格；由 entry 打印时再拼空格
DESKTOP_READY_PREFIX = drclaw_env("BACKEND_READY")

DESKTOP_CORS_ORIGINS = (
    "tauri://localhost",
    "https://tauri.localhost",
    "http://tauri.localhost",
)


def ensure_desktop_cors_origins() -> None:
    origins = [
        origin.strip()
        for origin in get_env(DESKTOP_CORS_ORIGINS_ENV, "").split(",")
        if origin.strip()
    ]
    for origin in DESKTOP_CORS_ORIGINS:
        if origin not in origins:
            origins.append(origin)
    os.environ[DESKTOP_CORS_ORIGINS_ENV] = ",".join(origins)
