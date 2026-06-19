# PATCH-002 — Cookbook CUDA llama.cpp Runtime

## Problem

Cookbook's local model serving built llama.cpp CPU-only because CUDA build
tooling was missing inside the slim Odysseus container.

The upstream Dockerfile uses `python:3.14-slim` (Debian Trixie, GCC 14,
glibc 2.41) which includes no CUDA tooling. The container had NVIDIA driver
passthrough (nvidia-smi works, RTX 4090 visible) but lacked the userspace
CUDA compiler (`nvcc`) and runtime library (`libcudart.so`).

Cookbook's llama.cpp build script (`routes/cookbook_helpers.py`,
function `_append_llama_cpp_linux_accel_build_lines`) checks for `nvcc`
before enabling `-DGGML_CUDA=ON`. Without nvcc, it falls back to a
CPU-only CMake configure. Symptoms:

- `CMakeCache.txt` showed `GGML_CUDA:BOOL=OFF`
- llama-server logs: `warning: no usable GPU found`
- llama-server logs: `warning: llama.cpp was compiled without support for GPU offload`

### Why pip CUDA wheels alone are insufficient

The `nvidia-cuda-nvcc-cu12` pip wheel (all versions 12.0–12.9) only ships
`ptxas`, CUDA headers, and `libnvvm`. The actual `nvcc` compiler binary
is NOT included in any pip wheel. CMake requires `nvcc` to configure
CUDA as a compiler. Without it, `GGML_CUDA=ON` cannot be set.

### Why CUDA 12.x does not work

The base image `python:3.14-slim` is Debian Trixie with glibc 2.41 and
GCC 14. CUDA 12.4 and 12.8 both fail to compile against Trixie's glibc
headers:
- CUDA 12.4: rejects GCC 14 entirely (`unsupported GNU version`)
- CUDA 12.8: `noexcept` specification mismatch between glibc 2.41's
  `bits/mathcalls.h` and CUDA's `crt/math_functions.h`

CUDA 13.0 is the first version compatible with glibc 2.41's headers.

## Solution

A Cata-specific Dockerfile (`Dockerfile.cata-cuda`) adds CUDA 13.0 build
tooling via multi-stage copy from the official
`nvidia/cuda:13.0.3-devel-ubuntu22.04` image.

The multi-stage build copies only the targeted files needed:

- `bin/` — nvcc, ptxas, fatbinary, nvlink, and other CUDA tools
- `include/` — CUDA headers (cudacc.h, cuda_runtime.h, etc.)
- `nvvm/` — NVVM compiler (libnvvm.so, libdevice.10.bc)
- `lib64/libcudart.so*` — CUDA runtime shared library
- `lib64/libcudart_static.a` — CUDA runtime static library (needed by nvcc linker)
- `lib64/libcudadevrt.a` — CUDA device runtime static library (needed by nvcc linker)
- `lib64/libcublas.so*` — cuBLAS library (used by llama.cpp for matrix ops)
- `lib64/libcublasLt.so*` — cuBLAS lightweight runtime

No apt CUDA packages are installed. No full CUDA toolkit is installed.
The final image is the upstream Odysseus image plus a thin CUDA tooling
layer.

The local `docker-compose.override.yml` (not committed) points the
`odysseus` service build to `Dockerfile.cata-cuda` while preserving:

- `/home/cata/models:/models:ro` mount
- NVIDIA GPU DeviceRequests
- `NVIDIA_VISIBLE_DEVICES=all`
- `NVIDIA_DRIVER_CAPABILITIES=compute,utility`

## Scope

Local model serving / Cookbook only. Does not affect upstream code logic,
API routes, or other services.

## Files Changed

| File | Committed | Description |
|------|-----------|-------------|
| `Dockerfile.cata-cuda` | Yes (new) | Multi-stage Dockerfile: upstream + CUDA 13.0 tooling |
| `docker-compose.override.yml` | No (local-only) | Points build to `Dockerfile.cata-cuda` |
| `docs/cata/PATCH-002-cookbook-cuda-llamacpp.md` | Yes (new) | This document |
| `docs/cata/PATCH_LEDGER.md` | Yes (updated) | Added PATCH-002 entry |

No upstream source files were modified. The Cookbook's existing CUDA
detection logic in `routes/cookbook_helpers.py` works unchanged — it
already checks `command -v nvcc` and `/usr/local/cuda/lib64/libcudart.so`,
which are the paths provided by this Dockerfile.

## Runtime Requirements

- Docker NVIDIA GPU passthrough must be enabled (NVIDIA Container Toolkit).
- `/models` mount remains local-only (in `docker-compose.override.yml`).
- Host NVIDIA driver must support CUDA 13.0+ (current: 580.159.03 / CUDA 13.0 — compatible).

## Verification

1. `nvidia-smi` inside container — RTX 4090 visible (24 GiB VRAM)
2. `nvcc --version` inside container — CUDA 13.0, V13.0.88
3. `ldconfig -p | grep libcudart` — runtime library discoverable
4. CMakeCache.txt shows `GGML_CUDA:BOOL=ON` after Cookbook rebuild
5. llama-server logs: `CUDA0 : NVIDIA GeForce RTX 4090 (24080 MiB, 23668 MiB free)`
6. `CUDA : ARCHS = 890` — RTX 4090 sm_89 architecture compiled
7. `nvidia-smi` VRAM: 5751 MiB used during Qwen3.5-9B-Q4_K_M model load
8. No CPU-only warning in llama-server logs
9. App reachable at `http://127.0.0.1:7000/` (HTTP 302 login redirect)

## Upstream Relationship

- The upstream image is slim by design — no CUDA tooling is included.
- This is a Cata local-runtime customization, not an upstream bug fix.
- `Dockerfile.cata-cuda` replicates the upstream Dockerfile content in a
  clearly marked "UPSTREAM" section. When the upstream Dockerfile changes,
  that section must be updated. The CUDA section should remain stable.
- The `docker-compose.override.yml` is local-only (in `.git/info/exclude`)
  and contains machine-specific paths — it is never committed.
- `Dockerfile.cata-cuda` is committed as a Cata-specific file, safe for
  upstream sync review.

## Risks

- **Image size increase**: ~500–800 MB from CUDA 13.0 binaries, headers,
  and libraries copied from the devel image.
- **CUDA version compatibility**: nvcc 13.0 matches the host driver
  (CUDA 13.0). If future driver updates break this, bump the
  `nvidia/cuda:13.0.3-devel-ubuntu22.04` base in `Dockerfile.cata-cuda`.
- **Stale llama.cpp build cache**: the old CPU-only build at
  `~/llama.cpp/build` must be cleared before the first CUDA rebuild.
  Cookbook's build script already does `rm -rf build` before each
  configure, but the stale `~/bin/llama-server` symlink may need manual
  clearing.
- **Container rebuild required**: after any change to
  `Dockerfile.cata-cuda`, the Odysseus image must be rebuilt and the
  container recreated. Use:
  ```
  docker compose build odysseus && docker compose up -d odysseus
  ```
- **Upstream Dockerfile sync**: if the upstream `Dockerfile` changes,
  the "UPSTREAM" section in `Dockerfile.cata-cuda` must be updated to
  match. A mismatch could cause the Cata image to miss upstream fixes
  or deps.
- **CUDA 13.0 is newer than CUDA 12.x** wheels: if Cookbook installs
  pip packages that bundle CUDA 12.x runtime (e.g. vLLM), there may be
  a version mismatch. This only affects vLLM, not llama.cpp native builds.
