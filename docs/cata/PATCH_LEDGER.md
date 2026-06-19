# Odysseus-Cata Patch Ledger

This file tracks every patch carried by the `odysseus-cata/dev` branch.
Each patch has a dedicated detail document in `docs/cata/`.

---

| Field               | PATCH-001                                                                 |
|---------------------|---------------------------------------------------------------------------|
| **Patch ID**        | PATCH-001                                                                 |
| **Name**            | Startup deployment-safety guard                                           |
| **Commit**          | `4988b1f`                                                                 |
| **Status**          | Active                                                                    |
| **Upstream status** | Not present upstream as of `ed18192a8` (upstream/dev)                     |
| **Reason**          | Prevent unsafe startup when the app is bound to a non-loopback address   |
|                     | with `AUTH_ENABLED=false` or `LOCALHOST_BYPASS=true`.  The upstream      |
|                     | project does not currently refuse startup for that combination.          |
| **Files touched**   | `.dockerignore` — minor glob fix (`+.venv*/`)                            |
|                     | `app.py` — import and call `check_deployment_safety()` at startup        |
|                     | `core/security_guards.py` — new module; guard logic and refusal banner   |
|                     | `docker-compose.yml` — propagate `APP_BIND` into the container env       |
|                     | `tests/test_security_guards.py` — new module; 28 targeted guard tests    |
| **Risk**            | Low-medium.  Startup/deployment behaviour only.  Possible false positive  |
|                     | for intentionally auth-off reverse-proxy deployments; mitigated by the   |
|                     | explicit override (`ODYSSEUS_ALLOW_INSECURE_DEPLOY=1`).                  |
| **Tests / checks**  | Targeted guard logic checks passed (28/28).  Docker image rebuilt.       |
|                     | App responds on loopback (HTTP 302 login redirect).  Full upstream       |
|                     | test suite not yet run.                                                  |
| **Next review**     | Every upstream sync that touches `app.py`, `docker-compose.yml`, auth    |
| **trigger**         | startup, bind behaviour, `AUTH_ENABLED`, `LOCALHOST_BYPASS`, or          |
|                     | deployment documentation.                                                |
| **Detail doc**      | [`PATCH-001-startup-deployment-safety-guard.md`](PATCH-001-startup-deployment-safety-guard.md) |
