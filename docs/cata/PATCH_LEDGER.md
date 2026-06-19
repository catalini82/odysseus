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

---

| Field               | PATCH-002                                                                 |
|---------------------|---------------------------------------------------------------------------|
| **Patch ID**        | PATCH-002                                                                 |
| **Name**            | Cookbook CUDA llama.cpp runtime                                           |
| **Commit**          | `9449715`                                                                 |
| **Status**          | Active                                                                    |
| **Upstream status** | Not present upstream as of `ed18192a8` (upstream/dev)                     |
| **Reason**          | Cookbook built llama.cpp CPU-only because the slim container lacked      |
|                     | nvcc and libcudart. pip CUDA wheels do not include the nvcc binary.      |
|                     | CUDA 12.x is incompatible with Debian Trixie glibc 2.41. Multi-stage     |
|                     | copy from nvidia/cuda:13.0.3-devel provides CUDA 13.0 tooling.           |
| **Files touched**   | `Dockerfile.cata-cuda` — new; multi-stage Dockerfile with CUDA 13.0      |
|                     | `docs/cata/PATCH-002-cookbook-cuda-llamacpp.md` — new; this detail doc   |
|                     | `docs/cata/PATCH_LEDGER.md` — updated; added PATCH-002 entry             |
|                     | `docker-compose.override.yml` — local-only; points build to Cata Docker  |
| **Risk**            | Medium.  Image size increase (~500-800 MB).  CUDA 13.0 version match     |
|                     | with host driver.  Upstream Dockerfile sync required when upstream       |
|                     | Dockerfile changes.                                                       |
| **Tests / checks**  | nvcc 13.0 inside container.  libcudart discoverable.  GGML_CUDA=ON.      |
|                     | llama-server logs show CUDA0 RTX 4090.  VRAM 5751 MiB during model       |
|                     | load.  App responds on loopback.                                          |
| **Next review**     | Every upstream sync that touches `Dockerfile` or CUDA-related Cookbook   |
| **trigger**         | code.  Also when upgrading NVIDIA driver or CUDA version.                |
| **Detail doc**      | [`PATCH-002-cookbook-cuda-llamacpp.md`](PATCH-002-cookbook-cuda-llamacpp.md) |
