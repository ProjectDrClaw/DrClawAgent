# -*- coding: utf-8 -*-
"""Tests for DRCLAW / QWENPAW / COPAW env resolution."""

from __future__ import annotations

import pytest

from qwenpaw.env_resolve import drclaw_env, get_env, pop_env, set_env


@pytest.fixture(autouse=True)
def _clear_test_env(monkeypatch):
    for key in list(__import__("os").environ):
        if key.startswith(("DRCLAW_TEST_", "QWENPAW_TEST_", "COPAW_TEST_")):
            monkeypatch.delenv(key, raising=False)


def test_drclaw_env_normalizes_prefix():
    assert drclaw_env("WORKING_DIR") == "DRCLAW_WORKING_DIR"
    assert drclaw_env("QWENPAW_WORKING_DIR") == "DRCLAW_WORKING_DIR"


def test_get_env_drclaw_priority(monkeypatch):
    monkeypatch.setenv("DRCLAW_TEST_FOO", "drclaw")
    monkeypatch.setenv("QWENPAW_TEST_FOO", "qwenpaw")
    monkeypatch.setenv("COPAW_TEST_FOO", "copaw")
    assert get_env("DRCLAW_TEST_FOO") == "drclaw"


def test_get_env_qwenpaw_fallback(monkeypatch):
    monkeypatch.delenv("DRCLAW_TEST_FOO", raising=False)
    monkeypatch.setenv("QWENPAW_TEST_FOO", "qwenpaw")
    monkeypatch.setenv("COPAW_TEST_FOO", "copaw")
    assert get_env("DRCLAW_TEST_FOO") == "qwenpaw"


def test_get_env_copaw_fallback(monkeypatch):
    monkeypatch.delenv("DRCLAW_TEST_FOO", raising=False)
    monkeypatch.delenv("QWENPAW_TEST_FOO", raising=False)
    monkeypatch.setenv("COPAW_TEST_FOO", "copaw")
    assert get_env("DRCLAW_TEST_FOO") == "copaw"


def test_set_and_pop_env(monkeypatch):
    monkeypatch.setenv("QWENPAW_TEST_BAR", "legacy")
    set_env("TEST_BAR", "new")
    assert get_env("DRCLAW_TEST_BAR") == "new"
    pop_env("TEST_BAR")
    assert get_env("DRCLAW_TEST_BAR", "") == ""
    assert get_env("QWENPAW_TEST_BAR", "") == ""
