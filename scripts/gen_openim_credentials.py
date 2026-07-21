#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立脚本：OpenIM userID + 明文 Secret → App ID / App Secret。

仅依赖 Python 3 标准库，不依赖本仓库或第三方包。可复制到任意目录单独运行。

用法::

    python gen_openim_credentials.py 6208248507 openIM123
    python gen_openim_credentials.py 6208248507 openIM123 --verify

算法::

    App ID     = "cli_" + hex(uint64(userID), 16)     # 可逆
    App Secret = Base62_32( HMAC-CTR(plain) || MAC )  # 密钥由 App ID 派生
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import sys

# 与 DrClawAgent ``credentials.py`` 必须保持一致（改 pepper 会导致无法互通）

APP_ID_PREFIX = "cli_"
APP_ID_HEX_LEN = 16
APP_SECRET_LEN = 32
APP_SECRET_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
)
PLAIN_SECRET_MAX_BYTES = 18
SEAL_BODY_LEN = 19
SEAL_TAG_LEN = 4
SEAL_BLOB_LEN = SEAL_BODY_LEN + SEAL_TAG_LEN
USER_ID_MAX_UINT64 = (1 << 64) - 1
DEFAULT_PEPPER = "DrClaw/OpenIM/v1/app-secret-seal"


class SealError(ValueError):
    pass


def encode_app_id(user_id: str) -> str:
    raw = user_id.strip()
    if not raw.isdigit() or raw.startswith("0"):
        raise SealError(f"user_id 须为正整数且无前导 0，收到: {user_id!r}")
    n = int(raw)
    if n <= 0 or n > USER_ID_MAX_UINT64:
        raise SealError("user_id 超出 uint64 范围")
    return f"{APP_ID_PREFIX}{n:0{APP_ID_HEX_LEN}x}"


def decode_app_id(app_id: str) -> str:
    raw = app_id.strip().lower()
    hex_part = raw[len(APP_ID_PREFIX) :]
    if not (
        raw.startswith(APP_ID_PREFIX)
        and len(hex_part) == APP_ID_HEX_LEN
        and all(c in "0123456789abcdef" for c in hex_part)
    ):
        raise SealError(f"非法 App ID: {app_id!r}")
    n = int(hex_part, 16)
    uid = str(n)
    if encode_app_id(uid) != raw:
        raise SealError("App ID 无法还原为 OpenIM userID")
    return uid


def _key_material(app_id: str, pepper: str) -> tuple[bytes, bytes]:
    key = hmac.new(
        pepper.encode("utf-8"),
        app_id.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    nonce = hmac.new(
        key,
        b"ctr-nonce:" + app_id.encode("utf-8"),
        hashlib.sha256,
    ).digest()[:16]
    return key, nonce


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(
            key,
            nonce + counter.to_bytes(4, "big"),
            hashlib.sha256,
        ).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _xor(data: bytes, ks: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, ks))


def _bytes_to_b62(data: bytes, width: int) -> str:
    n = int.from_bytes(data, "big")
    chars = ["0"] * width
    base = len(APP_SECRET_ALPHABET)
    for i in range(width):
        n, rem = divmod(n, base)
        chars[width - 1 - i] = APP_SECRET_ALPHABET[rem]
    if n:
        raise SealError("密文过长，无法编码为 32 位 App Secret")
    return "".join(chars)


def _b62_to_bytes(text: str, nbytes: int) -> bytes:
    n = 0
    base = len(APP_SECRET_ALPHABET)
    for ch in text:
        idx = APP_SECRET_ALPHABET.find(ch)
        if idx < 0:
            raise SealError("App Secret 含非法字符")
        n = n * base + idx
    return n.to_bytes(nbytes, "big")


def seal_app_secret(
    plain_secret: str,
    app_id: str,
    pepper: str = DEFAULT_PEPPER,
) -> str:
    plain = plain_secret.encode("utf-8")
    if not plain:
        raise SealError("secret 不能为空")
    if len(plain) > PLAIN_SECRET_MAX_BYTES:
        raise SealError(f"secret 最长 {PLAIN_SECRET_MAX_BYTES} 字节")
    key, nonce = _key_material(app_id, pepper)
    body = (
        bytes([len(plain)])
        + plain
        + (b"\0" * (PLAIN_SECRET_MAX_BYTES - len(plain)))
    )
    ct = _xor(body, _keystream(key, nonce, len(body)))
    tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()[:SEAL_TAG_LEN]
    return _bytes_to_b62(ct + tag, APP_SECRET_LEN)


def open_app_secret(
    sealed: str,
    app_id: str,
    pepper: str = DEFAULT_PEPPER,
) -> str:
    sealed = sealed.strip()
    if len(sealed) != APP_SECRET_LEN or any(
        c not in APP_SECRET_ALPHABET for c in sealed
    ):
        raise SealError("App Secret 须为 32 位字母数字")
    key, nonce = _key_material(app_id, pepper)
    blob = _b62_to_bytes(sealed, SEAL_BLOB_LEN)
    ct, tag = blob[:SEAL_BODY_LEN], blob[SEAL_BODY_LEN:]
    expect = hmac.new(key, nonce + ct, hashlib.sha256).digest()[:SEAL_TAG_LEN]
    if not hmac.compare_digest(tag, expect):
        raise SealError("解密失败（App ID 不匹配或 Secret 损坏）")
    body = _xor(ct, _keystream(key, nonce, len(ct)))
    length = body[0]
    if length > PLAIN_SECRET_MAX_BYTES:
        raise SealError("密文长度非法")
    return body[1 : 1 + length].decode("utf-8")


def seal_credentials(
    user_id: str,
    plain_secret: str,
    pepper: str = DEFAULT_PEPPER,
) -> tuple[str, str]:
    app_id = encode_app_id(user_id)
    return app_id, seal_app_secret(plain_secret, app_id, pepper=pepper)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "OpenIM userID + 明文 Secret → App ID / App Secret"
            "（纯标准库，可独立运行）"
        ),
    )
    parser.add_argument("user_id", help="OpenIM 数字 userID，如 6208248507")
    parser.add_argument("secret", help="明文 Secret，如 openIM123")
    parser.add_argument(
        "--pepper",
        default=DEFAULT_PEPPER,
        help="密钥胡椒（默认与 DrClawAgent 一致，勿随意更改）",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="生成后解密校验",
    )
    args = parser.parse_args(argv)

    try:
        app_id, app_secret = seal_credentials(
            args.user_id,
            args.secret,
            pepper=args.pepper,
        )
        openim_uid = decode_app_id(app_id)
    except SealError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"OpenIM userID: {openim_uid}")
    print(f"App ID:        {app_id}")
    print(f"App Secret:    {app_secret}")

    if args.verify:
        try:
            opened = open_app_secret(app_secret, app_id, pepper=args.pepper)
        except SealError as exc:
            print(f"verify: FAIL ({exc})", file=sys.stderr)
            return 2
        ok = opened == args.secret
        print(f"verify decrypt: {opened!r} ({'OK' if ok else 'FAIL'})")
        return 0 if ok else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
