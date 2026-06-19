"""Startup deployment-safety guard.

Called once at process start (see app.py) to refuse obviously unsafe
combinations of bind address + auth flags:

  * APP_BIND on a non-loopback interface + AUTH_ENABLED=false
      => publicly reachable with no authentication
  * APP_BIND on a non-loopback interface + LOCALHOST_BYPASS=true
      => publicly reachable with a side door for loopback callers
         (and tunneling services like cloudflared connect FROM loopback
         and so would inherit that bypass if the guard didn't fire)

When the unsafe combination is detected the guard logs a multi-line
error and raises SystemExit(2) UNLESS the operator has explicitly
acknowledged the risk by setting ODYSSEUS_ALLOW_INSECURE_DEPLOY=1.
The override exists so that deliberate reverse-proxy-fronted deployments
aren't blocked, but it's a manual opt-in, not a default.

`check_deployment_safety(env=None)` accepts an optional env dict for
testing. Real callers pass nothing and the function reads os.environ.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Mapping, Optional

logger = logging.getLogger(__name__)

# Bind addresses we treat as loopback-only. Matches the host-side
# docker compose port mapping: when APP_BIND is one of these, the only
# clients that can reach the app are local.
LOOPBACK_BINDS = frozenset({"127.0.0.1", "::1", "localhost", ""})

# Operator opt-in to skip the guard. Documented in the refusal banner.
INSECURE_OVERRIDE_ENV = "ODYSSEUS_ALLOW_INSECURE_DEPLOY"


def _resolve_bind(env: Mapping[str, str]) -> str:
    """Return the effective APP_BIND, defaulting to loopback when unset.

    Mirrors the docker-compose default ``${APP_BIND:-127.0.0.1}``: an
    empty / unset var means loopback-only.
    """
    return (env.get("APP_BIND") or "127.0.0.1").strip()


def _is_loopback_bind(bind: str) -> bool:
    return bind in LOOPBACK_BINDS


def _truthy(env_value: Optional[str]) -> bool:
    return str(env_value or "").strip().lower() == "true"


def _falsy(env_value: Optional[str]) -> bool:
    return str(env_value or "").strip().lower() == "false"


def check_deployment_safety(env: Optional[Mapping[str, str]] = None) -> None:
    """Raise SystemExit(2) on an unsafe (bind, auth) combo.

    Parameters
    ----------
    env:
        Optional mapping to read env-style values from. Defaults to
        ``os.environ``. Tests pass a plain dict.

    Raises
    ------
    SystemExit
        Exit code 2 when the deployment is unsafe and the operator has
        not set ``ODYSSEUS_ALLOW_INSECURE_DEPLOY=1``.
    """
    if env is None:
        env = os.environ

    app_bind = _resolve_bind(env)
    if _is_loopback_bind(app_bind):
        # Loopback bind: AUTH_ENABLED=false and LOCALHOST_BYPASS=true are
        # still logged as warnings (handled in app.py at the existing
        # warning site) but are not fatal — only the remote-reachable
        # combo is.
        return

    auth_enabled = not _falsy(env.get("AUTH_ENABLED"))  # default true
    localhost_bypass = _truthy(env.get("LOCALHOST_BYPASS"))

    unsafe_flags = []
    if not auth_enabled:
        unsafe_flags.append("AUTH_ENABLED=false")
    if localhost_bypass:
        unsafe_flags.append("LOCALHOST_BYPASS=true")

    if not unsafe_flags:
        # Non-loopback bind is intentional (reverse proxy / LAN), and
        # the operator has auth properly enabled. Nothing to refuse.
        return

    unsafe_summary = ", ".join(unsafe_flags)
    banner = (
        "\n"
        "============================================================\n"
        "ODYSSEUS REFUSES TO START — UNSAFE DEPLOYMENT COMBO\n"
        "============================================================\n"
        f"  APP_BIND            = {app_bind!r}\n"
        f"  Unsafe flags        = {unsafe_summary}\n"
        "  Why this is refused:\n"
        "    Exposing Odysseus to a non-loopback interface with auth\n"
        "    disabled (or with LOCALHOST_BYPASS on) is an unsafe-by-\n"
        "    default public deployment. AUTH_ENABLED=false lets any\n"
        "    caller reach admin-gated routes; LOCALHOST_BYPASS=true\n"
        "    lets a tunnel/proxy that loops back to localhost inherit\n"
        "    the bypass.\n"
        "  How to fix:\n"
        "    - Bind to 127.0.0.1 / ::1 (loopback only), OR\n"
        "    - Set AUTH_ENABLED=true AND LOCALHOST_BYPASS=false, OR\n"
        "    - Acknowledge the risk and override explicitly:\n"
        f"        {INSECURE_OVERRIDE_ENV}=1\n"
        "============================================================\n"
    )

    if env.get(INSECURE_OVERRIDE_ENV, "").strip() == "1":
        logger.warning(
            "ODYSSEUS_ALLOW_INSECURE_DEPLOY=1 set; starting with %s and "
            "APP_BIND=%r. YOU ARE ON THE HOOK FOR THIS DEPLOYMENT.",
            unsafe_summary, app_bind,
        )
        # Also dump the banner to stderr once so the operator sees it in
        # docker logs even if the log handler is filtered.
        print(banner, file=sys.stderr, flush=True)
        return

    # Hard refusal. logger.critical + stderr banner + SystemExit(2) so
    # docker compose logs the failure clearly and the process exits with
    # a non-zero code the supervisor can alert on.
    logger.critical("Refusing to start: %s with APP_BIND=%r", unsafe_summary, app_bind)
    print(banner, file=sys.stderr, flush=True)
    raise SystemExit(2)
