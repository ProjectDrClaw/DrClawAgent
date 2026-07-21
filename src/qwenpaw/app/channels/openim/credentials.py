# -*- coding: utf-8 -*-
"""OpenIM 凭证编解码：数字 userID ↔ App ID；App Secret = 用 App ID 加密的明文 Secret。

算法与 ``scripts/gen_openim_credentials.py`` 保持一致（仅标准库）。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import string
from typing import Optional, Tuple

USER_ID_MIN_DIGITS = 1
USER_ID_MAX_DIGITS = 20
USER_ID_DEFAULT_DIGITS = 10
USER_ID_MAX_UINT64 = (1 << 64) - 1

# App ID：cli_ + 16 位小写 hex（由数字 userID 可逆编码）
APP_ID_PREFIX = "cli_"
APP_ID_HEX_LEN = 16

# App Secret：密封后固定 32 位字母数字
APP_SECRET_LEN = 32
APP_SECRET_ALPHABET = string.ascii_letters + string.digits
_PLAIN_SECRET_MAX_BYTES = 18
_SEAL_BODY_LEN = 19
_SEAL_TAG_LEN = 4
_SEAL_BLOB_LEN = _SEAL_BODY_LEN + _SEAL_TAG_LEN

_DEFAULT_PEPPER = "DrClaw/OpenIM/v1/app-secret-seal"
_PEPPER_ENV = "DRCLAW_OPENIM_CREDENTIAL_PEPPER"

_OPENIM_UID_RE = re.compile(r"^[1-9]\d*$")
_APP_ID_RE = re.compile(
    rf"^{re.escape(APP_ID_PREFIX)}[0-9a-f]{{{APP_ID_HEX_LEN}}}$",
)
_APP_SECRET_RE = re.compile(rf"^[A-Za-z0-9]{{{APP_SECRET_LEN}}}$")


class SecretSealError(ValueError):
    """App Secret 密封/解封失败。"""


def _pepper() -> str:
    env = (os.getenv(_PEPPER_ENV) or "").strip()
    return env or _DEFAULT_PEPPER


def is_openim_user_id(value: str) -> bool:
    raw = (value or "").strip()
    if not raw or not _OPENIM_UID_RE.fullmatch(raw):
        return False
    try:
        return 0 < int(raw) <= USER_ID_MAX_UINT64
    except ValueError:
        return False


def is_app_id(value: str) -> bool:
    """是否为 ``cli_`` + 16 小写 hex 的 App ID。"""
    return bool(value and _APP_ID_RE.fullmatch(value.strip().lower()))


def is_app_secret(value: str) -> bool:
    """是否为 32 位字母数字 App Secret。"""
    return bool(value and _APP_SECRET_RE.fullmatch(value.strip()))


# 兼容旧名
is_openim_app_id = is_openim_user_id


def encode_app_id(openim_user_id: str) -> str:
    """OpenIM 数字 userID → App ID（可逆）。"""
    raw = (openim_user_id or "").strip()
    if not raw:
        raise ValueError("openim_user_id is empty")
    if is_app_id(raw):
        return raw.lower()
    if not is_openim_user_id(raw):
        raise ValueError(
            f"openim_user_id must be a positive decimal integer, got {raw!r}",
        )
    n = int(raw)
    return f"{APP_ID_PREFIX}{n:0{APP_ID_HEX_LEN}x}"


def decode_app_id(app_id_or_uid: str) -> str:
    """App ID 或数字 userID → OpenIM 数字 userID。"""
    raw = (app_id_or_uid or "").strip()
    if not raw:
        raise ValueError("app_id_or_uid is empty")
    lower = raw.lower()
    if is_app_id(lower):
        n = int(lower[len(APP_ID_PREFIX) :], 16)
        if n <= 0 or n > USER_ID_MAX_UINT64:
            raise ValueError("app_id out of openim user_id range")
        uid = str(n)
        if encode_app_id(uid) != lower:
            raise ValueError("app_id is not a reversible openim encoding")
        return uid
    if is_openim_user_id(raw):
        return raw
    return raw


# 兼容旧名
to_openim_user_id = decode_app_id


def normalize_app_id(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        if is_app_id(raw) or is_openim_user_id(raw):
            return encode_app_id(
                decode_app_id(raw) if is_app_id(raw) else raw,
            )
    except ValueError:
        pass
    return raw


def resolve_identity(app_id_or_uid: str) -> Tuple[str, str]:
    """``(openim_user_id, encoded_app_id)``。"""
    raw = (app_id_or_uid or "").strip()
    if not raw:
        raise ValueError("app_id_or_uid is empty")
    if is_app_id(raw) or is_openim_user_id(raw):
        uid = decode_app_id(raw)
        return uid, encode_app_id(uid)
    digest = hashlib.sha256(f"openim-uid:{raw}".encode("utf-8")).hexdigest()
    encoded = f"{APP_ID_PREFIX}{digest[:APP_ID_HEX_LEN]}"
    return raw, encoded


def _resolve_encoded_app_id(app_id: str) -> str:
    raw = (app_id or "").strip()
    if not raw:
        raise ValueError("app_id is empty")
    try:
        return resolve_identity(raw)[1]
    except ValueError:
        return normalize_app_id(raw) or raw


def _seal_key_material(encoded_app_id: str, pepper: str) -> Tuple[bytes, bytes]:
    key = hmac.new(
        pepper.encode("utf-8"),
        encoded_app_id.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    nonce = hmac.new(
        key,
        b"ctr-nonce:" + encoded_app_id.encode("utf-8"),
        hashlib.sha256,
    ).digest()[:16]
    return key, nonce


def _hmac_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
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


def _xor_bytes(data: bytes, keystream: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, keystream))


def _bytes_to_b62(data: bytes, width: int) -> str:
    n = int.from_bytes(data, "big")
    chars = ["0"] * width
    for i in range(width):
        n, rem = divmod(n, len(APP_SECRET_ALPHABET))
        chars[width - 1 - i] = APP_SECRET_ALPHABET[rem]
    if n:
        raise SecretSealError("sealed payload too large for App Secret width")
    return "".join(chars)


def _b62_to_bytes(text: str, nbytes: int) -> bytes:
    n = 0
    for ch in text:
        idx = APP_SECRET_ALPHABET.find(ch)
        if idx < 0:
            raise SecretSealError("invalid App Secret character")
        n = n * len(APP_SECRET_ALPHABET) + idx
    return n.to_bytes(nbytes, "big")


def seal_app_secret(
    plain_secret: str,
    app_id: str,
    *,
    pepper: Optional[str] = None,
) -> str:
    """用 App ID 加密明文 Secret → 32 位 App Secret。"""
    plain = (plain_secret or "").encode("utf-8")
    if not plain:
        raise SecretSealError("plain_secret is empty")
    if len(plain) > _PLAIN_SECRET_MAX_BYTES:
        raise SecretSealError(
            f"plain_secret exceeds {_PLAIN_SECRET_MAX_BYTES} bytes",
        )
    encoded_id = _resolve_encoded_app_id(app_id)
    key, nonce = _seal_key_material(
        encoded_id,
        pepper if pepper is not None else _pepper(),
    )
    body = (
        bytes([len(plain)])
        + plain
        + (b"\0" * (_PLAIN_SECRET_MAX_BYTES - len(plain)))
    )
    ct = _xor_bytes(body, _hmac_keystream(key, nonce, len(body)))
    tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()[:_SEAL_TAG_LEN]
    return _bytes_to_b62(ct + tag, APP_SECRET_LEN)


def open_app_secret(
    sealed_secret: str,
    app_id: str,
    *,
    pepper: Optional[str] = None,
) -> str:
    """用 App ID 解密 App Secret → 明文 Secret。"""
    sealed = (sealed_secret or "").strip()
    if not is_app_secret(sealed):
        raise SecretSealError("sealed_secret must be 32-char [A-Za-z0-9]")
    encoded_id = _resolve_encoded_app_id(app_id)
    key, nonce = _seal_key_material(
        encoded_id,
        pepper if pepper is not None else _pepper(),
    )
    blob = _b62_to_bytes(sealed, _SEAL_BLOB_LEN)
    ct, tag = blob[:_SEAL_BODY_LEN], blob[_SEAL_BODY_LEN:]
    expect = hmac.new(key, nonce + ct, hashlib.sha256).digest()[:_SEAL_TAG_LEN]
    if not hmac.compare_digest(tag, expect):
        raise SecretSealError("App Secret MAC mismatch (wrong App ID or corrupt)")
    body = _xor_bytes(ct, _hmac_keystream(key, nonce, len(ct)))
    length = body[0]
    if length > _PLAIN_SECRET_MAX_BYTES:
        raise SecretSealError("invalid sealed plaintext length")
    return body[1 : 1 + length].decode("utf-8")


def seal_openim_credentials(
    openim_user_id: str,
    plain_secret: str,
    *,
    pepper: Optional[str] = None,
) -> Tuple[str, str]:
    """``(App ID, App Secret)``：userID 编码 + Secret 加密。"""
    app_id = encode_app_id(openim_user_id)
    return app_id, seal_app_secret(plain_secret, app_id, pepper=pepper)


def derive_app_secret(
    app_id: str,
    plain_secret: str = "",
    *,
    pepper: Optional[str] = None,
) -> str:
    if not (plain_secret or "").strip():
        raise SecretSealError(
            "derive_app_secret requires plain_secret; "
            "use seal_app_secret(plain, app_id)",
        )
    return seal_app_secret(plain_secret, app_id, pepper=pepper)


def generate_app_secret(
    app_id: str,
    plain_secret: str,
    *,
    pepper: Optional[str] = None,
) -> str:
    return seal_app_secret(plain_secret, app_id, pepper=pepper)


def generate_openim_user_id(
    *,
    digits: int = USER_ID_DEFAULT_DIGITS,
    rng: secrets.SystemRandom | None = None,
) -> str:
    width = max(USER_ID_MIN_DIGITS, min(USER_ID_MAX_DIGITS, int(digits or 10)))
    pick = rng or secrets
    lo = 10 ** (width - 1) if width > 1 else 1
    hi = min(10**width, USER_ID_MAX_UINT64 + 1)
    return str(lo + pick.randbelow(hi - lo))


def generate_app_id(
    *,
    digits: int = USER_ID_DEFAULT_DIGITS,
    rng: secrets.SystemRandom | None = None,
) -> str:
    return encode_app_id(generate_openim_user_id(digits=digits, rng=rng))


def generate_credentials(
    plain_secret: str,
    *,
    pepper: Optional[str] = None,
    digits: int = USER_ID_DEFAULT_DIGITS,
    rng: secrets.SystemRandom | None = None,
) -> Tuple[str, str]:
    app_id = generate_app_id(digits=digits, rng=rng)
    return app_id, seal_app_secret(plain_secret, app_id, pepper=pepper)


def resolve_app_secret(
    app_id: str,
    app_secret: str = "",
    *,
    pepper: Optional[str] = None,
) -> str:
    raw = (app_secret or "").strip()
    if not raw:
        raise SecretSealError("app_secret is empty")
    if is_app_secret(raw):
        try:
            return open_app_secret(raw, app_id, pepper=pepper)
        except SecretSealError:
            return raw
    return raw


def verify_app_secret(
    app_id: str,
    app_secret: str,
    plain_secret: str,
    *,
    pepper: Optional[str] = None,
) -> bool:
    try:
        opened = resolve_app_secret(app_id, app_secret, pepper=pepper)
    except SecretSealError:
        return False
    return hmac.compare_digest(opened, (plain_secret or "").strip())


def credentials_format_report(
    app_id: str,
    app_secret: str,
) -> dict[str, bool | str]:
    raw = (app_id or "").strip()
    secret = (app_secret or "").strip()
    openim_uid = ""
    encoded_id = ""
    opened = ""
    sealed_ok = False
    try:
        openim_uid, encoded_id = resolve_identity(raw)
    except ValueError:
        encoded_id = raw
    if is_app_secret(secret) and encoded_id:
        try:
            opened = open_app_secret(secret, encoded_id)
            sealed_ok = True
        except SecretSealError:
            pass
    return {
        "app_id": raw,
        "openim_user_id": openim_uid,
        "encoded_app_id": encoded_id,
        "app_id_openim_numeric": is_openim_user_id(raw),
        "app_id_encoded": is_app_id(raw) or is_app_id(encoded_id),
        "app_secret_encoded": is_app_secret(secret),
        "app_secret_sealed": sealed_ok,
        "opened_secret_len": len(opened),
        "aligned": bool(encoded_id) and is_app_id(encoded_id) and sealed_ok,
    }
