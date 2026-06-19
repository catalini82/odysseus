"""Pin the deployment-safety guard from the 2026-06-07 hardening card.

`core.security_guards.check_deployment_safety` is the only thing
standing between an operator who sets ``APP_BIND=0.0.0.0`` and ``AUTH_
ENABLED=***`` in a fit of "I'll just expose this on the LAN for
testing" and the app happily serving admin-gated routes to the
internet. These tests pin its decision matrix.

The guard reads env vars but takes an optional env dict so each test
passes exactly the variables under test and never pollutes the parent
process environment.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.security_guards import (  # noqa: E402
    INSECURE_OVERRIDE_ENV,
    check_deployment_safety,
)


# ── helper ────────────────────────────────────────────────────────

def _call(env):
    """Invoke the guard with the supplied env dict and re-raise SystemExit
    with a captured exit code so the test can assert on it. Catching
    SystemExit directly in the test is fine too, but this keeps the
    assertion site uniform."""
    try:
        check_deployment_safety(env)
    except SystemExit as exc:
        return exc.code
    return None


# ── safe configurations (must NOT raise) ──────────────────────────

class TestSafeConfigurations:
    def test_default_empty_env_is_safe(self):
        # No env at all: APP_BIND defaults to 127.0.0.1, AUTH_ENABLED
        # defaults to true. Should never raise.
        assert _call({}) is None

    def test_loopback_ipv4_with_auth_on(self):
        assert _call({
            "APP_BIND": "127.0.0.1",
            "AUTH_ENABLED": "true",
            "LOCALHOST_BYPASS": "false",
        }) is None

    def test_loopback_ipv6_with_auth_on(self):
        assert _call({
            "APP_BIND": "::1",
            "AUTH_ENABLED": "true",
            "LOCALHOST_BYPASS": "false",
        }) is None

    def test_loopback_localhost_with_auth_on(self):
        assert _call({
            "APP_BIND": "localhost",
            "AUTH_ENABLED": "true",
            "LOCALHOST_BYPASS": "false",
        }) is None

    def test_empty_app_bind_defaults_to_loopback(self):
        # Mirrors `${APP_BIND:-127.0.0.1}` in docker-compose.yml.
        assert _call({"APP_BIND": ""}) is None

    def test_nonloopback_bind_with_auth_on_is_safe(self):
        # Exposing to LAN on purpose, but with auth on and bypass off.
        # That's a valid (if not recommended) deployment behind a
        # reverse proxy; the guard must NOT fire.
        assert _call({
            "APP_BIND": "0.0.0.0",
            "AUTH_ENABLED": "true",
            "LOCALHOST_BYPASS": "false",
        }) is None

    def test_loopback_with_localhost_bypass_does_not_refuse(self):
        # The existing app.py warning still fires at import time; the
        # guard itself only refuses when the bind is non-loopback. We
        # verify that contract here so a future refactor doesn't
        # accidentally tighten it into a refusal.
        assert _call({
            "APP_BIND": "127.0.0.1",
            "AUTH_ENABLED": "true",
            "LOCALHOST_BYPASS": "true",
        }) is None

    def test_loopback_with_auth_off_does_not_refuse(self):
        assert _call({
            "APP_BIND": "127.0.0.1",
            "AUTH_ENABLED": "false",
        }) is None

    def test_default_auth_is_treated_as_enabled(self):
        # The compose + app code default AUTH_ENABLED to "true" when the
        # var is unset. The guard must mirror that — non-loopback bind
        # with AUTH_ENABLED missing must be safe.
        assert _call({"APP_BIND": "0.0.0.0"}) is None


# ── unsafe configurations (must raise SystemExit 2) ───────────────

class TestUnsafeConfigurations:
    def test_nonloopback_with_auth_off_refuses(self):
        assert _call({
            "APP_BIND": "0.0.0.0",
            "AUTH_ENABLED": "false",
        }) == 2

    def test_nonloopback_with_localhost_bypass_refuses(self):
        assert _call({
            "APP_BIND": "0.0.0.0",
            "LOCALHOST_BYPASS": "true",
        }) == 2

    def test_nonloopback_with_both_unsafe_refuses(self):
        assert _call({
            "APP_BIND": "0.0.0.0",
            "AUTH_ENABLED": "false",
            "LOCALHOST_BYPASS": "true",
        }) == 2

    def test_lan_ip_with_auth_off_refuses(self):
        # 192.168.0.0/16 is a private LAN range — not loopback, the
        # same guard must fire.
        assert _call({
            "APP_BIND": "192.168.1.10",
            "AUTH_ENABLED": "false",
        }) == 2

    def test_hostname_bind_with_auth_off_refuses(self):
        # A hostname that isn't "localhost" is non-loopback as far as
        # this guard is concerned (we can't resolve DNS at import
        # time). Must fire.
        assert _call({
            "APP_BIND": "odysseus.local",
            "AUTH_ENABLED": "false",
        }) == 2

    def test_auth_enabled_capital_false_triggers(self):
        # Case-insensitive parsing: "False", "FALSE", " false " all
        # count as disabled.
        for value in ("False", "FALSE", "  false  "):
            assert _call({
                "APP_BIND": "0.0.0.0",
                "AUTH_ENABLED": value,
            }) == 2, f"failed for AUTH_ENABLED={value!r}"

    def test_localhost_bypass_capital_true_triggers(self):
        for value in ("True", "TRUE", "  true  "):
            assert _call({
                "APP_BIND": "0.0.0.0",
                "LOCALHOST_BYPASS": value,
            }) == 2, f"failed for LOCALHOST_BYPASS={value!r}"


# ── operator override (ODYSSEUS_ALLOW_INSECURE_DEPLOY) ────────────

class TestOverrideEscapeHatch:
    def test_override_allows_unsafe_combo(self):
        # Setting the override env var to "1" must let the app start
        # even with the dangerous combo. The guard still logs a
        # warning, but doesn't refuse.
        assert _call({
            "APP_BIND": "0.0.0.0",
            "AUTH_ENABLED": "false",
            INSECURE_OVERRIDE_ENV: "1",
        }) is None

    def test_override_only_allows_with_exact_value(self):
        # Anything other than "1" is treated as not-set. This pins
        # the contract so a typo like "true" or "yes" doesn't
        # accidentally become a backdoor.
        for value in ("", "0", "true", "yes", "True", "2", "ok"):
            assert _call({
                "APP_BIND": "0.0.0.0",
                "AUTH_ENABLED": "false",
                INSECURE_OVERRIDE_ENV: value,
            }) == 2, f"override unexpectedly accepted value {value!r}"


# ── integration: the real process env behaves like the safe default ─

class TestRealEnv:
    def test_real_os_environ_safe_default(self):
        # The host we're running on may or may not have APP_BIND set.
        # Either way, check_deployment_safety(env=None) must read
        # os.environ and refuse ONLY if a real unsafe combo is present.
        # The pytest host almost certainly has APP_BIND unset, so this
        # is the safe-default path. If the host IS exposed with auth
        # off the test environment itself is the regression.
        from core.security_guards import check_deployment_safety as real
        # Don't call real() directly — it would read the actual env. We
        # re-implement the no-arg call by passing os.environ explicitly,
        # which is the same code path the real invocation takes.
        try:
            real(env=os.environ)
        except SystemExit as exc:
            # SystemExit is acceptable only if the actual host env
            # genuinely has an unsafe combo. The test infra doesn't,
            # so this branch should be unreachable in normal CI. We
            # fail loudly if it is, because that means the test box
            # itself is in an unsafe state.
            pytest.fail(
                f"check_deployment_safety refused to start against the "
                f"real os.environ (exit {exc.code!r}). The test host is "
                f"in an unsafe deploy state: APP_BIND={os.environ.get('APP_BIND')!r}, "
                f"AUTH_ENABLED={os.environ.get('AUTH_ENABLED')!r}, "
                f"LOCALHOST_BYPASS={os.environ.get('LOCALHOST_BYPASS')!r}"
            )
