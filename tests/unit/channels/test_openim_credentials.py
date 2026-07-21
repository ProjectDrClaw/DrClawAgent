# -*- coding: utf-8 -*-
"""OpenIM 凭证：userID→App ID；App Secret = App ID 加密明文 Secret。"""
from __future__ import annotations

from qwenpaw.app.channels.openim.credentials import (
    decode_app_id,
    encode_app_id,
    is_app_id,
    is_app_secret,
    open_app_secret,
    resolve_app_secret,
    resolve_identity,
    seal_app_secret,
    seal_openim_credentials,
    verify_app_secret,
)


def test_userid_to_app_id():
    uid = "6208248507"
    app_id = encode_app_id(uid)
    assert app_id == "cli_00000001720a5abb"
    assert decode_app_id(app_id) == uid


def test_seal_openim123_with_app_id():
    uid = "6208248507"
    plain = "openIM123"
    app_id, sealed = seal_openim_credentials(uid, plain)
    assert app_id == "cli_00000001720a5abb"
    assert is_app_secret(sealed)
    assert sealed != plain
    assert open_app_secret(sealed, app_id) == plain
    assert open_app_secret(sealed, uid) == plain
    assert resolve_app_secret(app_id, sealed) == plain


def test_seal_roundtrip_same_for_numeric_or_encoded():
    plain = "openIM123"
    a = seal_app_secret(plain, "6208248507")
    b = seal_app_secret(plain, "cli_00000001720a5abb")
    assert a == b


def test_resolve_plaintext_legacy():
    assert resolve_app_secret("6208248507", "openIM123") == "openIM123"


def test_verify():
    app_id, sealed = seal_openim_credentials("6208248507", "openIM123")
    assert verify_app_secret(app_id, sealed, "openIM123")
    assert not verify_app_secret(app_id, sealed, "wrong")


def test_legacy_string_identity():
    uid, encoded = resolve_identity("drclaw_bot")
    assert uid == "drclaw_bot"
    assert is_app_id(encoded)
    sealed = seal_app_secret("openIM123", "drclaw_bot")
    assert open_app_secret(sealed, encoded) == "openIM123"
