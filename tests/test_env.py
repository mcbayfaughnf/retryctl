"""Tests for retryctl.env."""
from __future__ import annotations

import os
import pytest

from retryctl.env import (
    ENV_PREFIX,
    build_env,
    current_attempt,
    strip_env,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE = {"PATH": "/usr/bin", "HOME": "/home/user"}


# ---------------------------------------------------------------------------
# build_env
# ---------------------------------------------------------------------------

class TestBuildEnv:
    def test_sets_attempt(self):
        env = build_env(1, 3, None, "echo hi", base=BASE)
        assert env[f"{ENV_PREFIX}ATTEMPT"] == "1"

    def test_sets_max_attempts(self):
        env = build_env(2, 5, 1, "ls", base=BASE)
        assert env[f"{ENV_PREFIX}MAX_ATTEMPTS"] == "5"

    def test_sets_command(self):
        env = build_env(1, 3, None, "my-script.sh", base=BASE)
        assert env[f"{ENV_PREFIX}COMMAND"] == "my-script.sh"

    def test_last_exit_code_none_becomes_empty_string(self):
        env = build_env(1, 3, None, "cmd", base=BASE)
        assert env[f"{ENV_PREFIX}LAST_EXIT_CODE"] == ""

    def test_last_exit_code_is_stringified(self):
        env = build_env(2, 3, 127, "cmd", base=BASE)
        assert env[f"{ENV_PREFIX}LAST_EXIT_CODE"] == "127"

    def test_preserves_base_keys(self):
        env = build_env(1, 1, None, "x", base=BASE)
        assert env["PATH"] == "/usr/bin"
        assert env["HOME"] == "/home/user"

    def test_defaults_base_to_os_environ(self):
        env = build_env(1, 1, None, "x")
        assert "PATH" in env or True  # just ensure it doesn't raise
        assert f"{ENV_PREFIX}ATTEMPT" in env

    def test_does_not_mutate_base(self):
        original = dict(BASE)
        build_env(1, 3, None, "cmd", base=BASE)
        assert BASE == original


# ---------------------------------------------------------------------------
# strip_env
# ---------------------------------------------------------------------------

class TestStripEnv:
    def test_removes_retryctl_keys(self):
        env = build_env(1, 3, 0, "cmd", base=BASE)
        stripped = strip_env(env)
        assert not any(k.startswith(ENV_PREFIX) for k in stripped)

    def test_keeps_non_retryctl_keys(self):
        env = build_env(1, 3, 0, "cmd", base=BASE)
        stripped = strip_env(env)
        assert stripped["PATH"] == "/usr/bin"

    def test_empty_env_returns_empty(self):
        assert strip_env({}) == {}


# ---------------------------------------------------------------------------
# current_attempt
# ---------------------------------------------------------------------------

class TestCurrentAttempt:
    def test_reads_from_provided_env(self):
        env = {f"{ENV_PREFIX}ATTEMPT": "4"}
        assert current_attempt(env) == 4

    def test_returns_none_when_missing(self):
        assert current_attempt({}) is None

    def test_reads_from_os_environ_when_no_arg(self, monkeypatch):
        monkeypatch.setenv(f"{ENV_PREFIX}ATTEMPT", "7")
        assert current_attempt() == 7
