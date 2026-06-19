# PATCH-001 — Startup Deployment-Safety Guard

## Summary (noob-friendly)

When you run a web app on your own machine and expose it to your local
network (or the internet), it should **refuse to start** if authentication
is turned off.  This patch adds a startup check to Odysseus that catches
that mistake before the app even begins serving requests.  If you really
want to run without auth behind a reverse proxy, there is an explicit
opt-in override — but you have to choose it on purpose.

## Problem

Self-hosted apps can accidentally be exposed to a LAN or the public
internet when the operator:

- binds the app to `0.0.0.0` (all interfaces), and
- disables authentication (`AUTH_ENABLED=***, or
- enables the localhost bypass (`LOCALHOST_BYPASS=true`).

Odysseus upstream does not currently refuse startup for that combination.
The app starts silently and serves admin-gated routes to anyone on the
network.

## Solution

At startup — before the FastAPI app object is constructed — the guard
reads three environment variables and makes a decision:

1. `APP_BIND` — which network interface the app is bound to.
2. `AUTH_ENABLED` — whether authentication is on (default: `true`).
3. `LOCALHOST_BYPASS` — whether loopback callers skip auth
   (default: `false`).

If the combination is unsafe, the guard prints a detailed banner to stderr,
logs a critical message, and exits with code 2.

## Unsafe Combos Blocked

| `APP_BIND`         | `AUTH_ENABLED` | `LOCALHOST_BYPASS` | Result        |
|--------------------|----------------|--------------------|---------------|
| `0.0.0.0`          | `false`        | any                | **REFUSED**   |
| `0.0.0.0`          | any            | `true`             | **REFUSED**   |
| `0.0.0.0`          | `false`        | `true`             | **REFUSED**   |
| `192.168.x.x`      | `false`        | any                | **REFUSED**   |
| `<any hostname>`   | `false`        | any                | **REFUSED**   |

Non-loopback addresses include `0.0.0.0`, private LAN IPs, and any
hostname that is not `127.0.0.1`, `::1`, or `localhost`.

## Safe Combos (guard does not fire)

| `APP_BIND`         | `AUTH_ENABLED` | `LOCALHOST_BYPASS` | Result   |
|--------------------|----------------|--------------------|----------|
| `127.0.0.1`        | any            | any                | Allowed  |
| `::1`              | any            | any                | Allowed  |
| `localhost`        | any            | any                | Allowed  |
| *(unset/empty)*    | any            | any                | Allowed  |
| `0.0.0.0`          | `true`         | `false`            | Allowed  |

## Override

```
ODYSSEUS_ALLOW_INSECURE_DEPLOY=1
```

When set to the **exact** value `1`, the guard logs a warning and allows
startup even with an unsafe combination.  Any other value (`true`, `yes`,
`2`, etc.) is **not** accepted — this is intentional to prevent accidental
activation.

The override exists for operators who have placed Odysseus behind a reverse
proxy with its own authentication layer.  It should not be the default.

## Files Changed and Why

| File                                | Change                                                              |
|-------------------------------------|---------------------------------------------------------------------|
| `.dockerignore`                     | Added `.venv*/` glob to avoid copying local venv variants into image |
| `app.py`                            | Import and call `check_deployment_safety()` at module level, before |
|                                     | the FastAPI app is constructed                                      |
| `core/security_guards.py`           | **New file.**  Guard logic, loopback detection, refusal banner      |
| `docker-compose.yml`                | Propagate `APP_BIND` into the container environment so the guard    |
|                                     | sees the host-side bind address                                     |
| `tests/test_security_guards.py`     | **New file.**  28 targeted tests covering safe, unsafe, case        |
|                                     | sensitivity, and override behaviour                                 |

## Security Value

- **Prevents silent misconfiguration.**  The most common self-hosted
  foot-gun — expose to LAN with auth off — now fails loudly at startup.
- **Explicit opt-in for risky deployments.**  The override requires the
  operator to consciously accept the risk.
- **Startup-time enforcement.**  The check runs before any request is
  served, so there is no window where the app is reachable in an unsafe
  state.

## Remaining Gaps

- **Does not replace authentication.**  The guard only checks whether auth
  is enabled; it does not implement or strengthen auth itself.
- **Does not check HTTPS.**  Traffic encryption is not validated.
- **Does not validate token strength.**  Weak or default tokens are not
  detected.
- **Startup-only.**  Runtime changes to the bind address or auth state
  after startup are not guarded.
- **Does not cover every reverse-proxy misconfiguration.**  A properly
  authenticated proxy in front of an auth-off Odysseus instance is still
  blocked unless the override is set.

## Upstream Relationship

- The guard **complements** upstream runtime hardening (tool result
  wrapping, MCP owner boundaries, etc.) but does not replace it.
- Upstream did **not** have an equivalent startup guard as of commit
  `ed18192a8` (upstream/dev).
- If upstream adds a similar guard in the future, this patch should be
  evaluated for removal or adaptation.

## Test Status

| Check                                          | Result     |
|------------------------------------------------|------------|
| Targeted guard logic (28 tests, direct import) | All passed |
| Docker image rebuild                           | Successful |
| App responds on loopback (HTTP 302)            | Confirmed  |
| Full upstream test suite                       | Not yet run|

## Future Review

Revisit this patch whenever upstream changes:

- `app.py` startup sequence
- `docker-compose.yml` bind or auth env vars
- Authentication startup logic
- `AUTH_ENABLED` or `LOCALHOST_BYPASS` handling
- Deployment security documentation
