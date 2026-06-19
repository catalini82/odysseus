# Odysseus-Cata Baseline

## What is Odysseus-Cata?

Odysseus-Cata is a personal downstream branch of
[Odysseus](https://github.com/pewdiepie-archdaemon/odysseus), a self-hosted
AI assistant platform.  It carries small, documented patches on top of the
official `upstream/dev` branch so that a local Docker deployment can benefit
from targeted safety or operational improvements without diverging from the
main project.

Odysseus-Cata is **not** a fork — it is a tracking branch that rebases onto
upstream and cherry-picks a handful of patches that are either not yet
upstream or serve a specific local-deployment need.

## Branch Reference

| Field                | Value                                                                 |
|----------------------|-----------------------------------------------------------------------|
| Branch               | `odysseus-cata/dev`                                                   |
| Upstream base commit | `ed18192a8ebd235ce38826ee5428e53445ec2455` (upstream/dev)             |
| Cata HEAD            | `4988b1f`                                                             |
| Carried patches      | PATCH-001 — Startup deployment-safety guard                          |
| Runtime status       | Active in local Docker deployment (http loopback on port 7000)       |

## Philosophy

1. **Stay close to upstream.**  Rebase or sync regularly; carry only patches
   that provide clear, documented value.
2. **Small, documented patches.**  Every patch has a ledger entry, a
   dedicated doc, and an explicit review trigger.
3. **Gates over deletions.**  Prefer safety gates and guards over large code
   removals or invasive refactors.
4. **Selective upstream syncs.**  Each sync is recorded in
   `UPSTREAM_SYNC_LEDGER.md` with the upstream commit, carried patches,
   conflicts, and test results.
5. **Clean contribution workflow.**  Official upstream PR work lives in a
   separate repository and branch — Odysseus-Cata patches are local
   improvements only.

## Public / Private Boundary

- **No secrets in repo.**  Docs must not contain tokens, passwords, API
  keys, or exact environment variable values.
- **No private deployment details.**  Machine names, exact home paths, and
  internal network layouts stay out of this tree.
- **Separate contribution workflow.**  Upstream PRs are authored and tracked
  in the dedicated contribution repository, not in Odysseus-Cata.

## Directory Layout

```
docs/cata/
  BASELINE.md                                  ← this file
  PATCH_LEDGER.md                              ← master patch tracking table
  PATCH-001-startup-deployment-safety-guard.md ← PATCH-001 detail doc
  UPSTREAM_SYNC_LEDGER.md                      ← upstream sync history
```
