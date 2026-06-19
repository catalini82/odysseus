# Odysseus-Cata Upstream Sync Ledger

This file records every upstream sync performed on the `odysseus-cata/dev`
branch.  Each entry documents what upstream state was merged, which patches
were carried forward, whether conflicts occurred, and what checks passed.

---

## Sync Record — 2026-06-19 (Initial Baseline)

| Field                      | Value                                                                  |
|----------------------------|------------------------------------------------------------------------|
| **Date**                   | 2026-06-19                                                             |
| **Source branch**          | `upstream/dev`                                                         |
| **Upstream base commit**   | `ed18192a8ebd235ce38826ee5428e53445ec2455`                             |
| **Previous local base**    | `6ccd4500d7057c8afbb52f2ce75ec8e7adfcb1d7`                             |
| **Preserved snapshot**     | Tag: `odysseus-cata-v0.1-pre-sync`                                    |
|                            | Branch: `odysseus-cata/patches`                                        |
| **New branch**             | `odysseus-cata/dev`                                                    |
| **Carried patches**        | PATCH-001 (startup deployment-safety guard)                            |
| **Result**                 | Hardening patch applied cleanly via cherry-pick.  Committed as         |
|                            | `4988b1f`.  Pushed to origin.  Docker image rebuilt.  Local app        |
|                            | responds on loopback (HTTP 302 login redirect).                        |
| **Conflicts**              | None during cherry-pick.                                               |
| **Tests / checks**         | Targeted guard logic checks passed (28/28).  Docker rebuild            |
|                            | successful.  App responds on loopback.                                 |
| **Decision notes**         | Upstream was ~40 commits ahead of previous local base.  The hardening  |
|                            | patch is orthogonal to upstream changes (new files + targeted edits).  |
|                            | Cherry-pick was clean; no adaptation required.                         |

---

## Template for Future Syncs

```markdown
## Sync Record — YYYY-MM-DD

| Field                      | Value                                           |
|----------------------------|-------------------------------------------------|
| **Date**                   | YYYY-MM-DD                                      |
| **Starting Cata commit**   | `abcdef1`                                       |
| **New upstream commit**    | `fedcba9` (upstream/dev)                        |
| **Carried patches**        | PATCH-001, PATCH-002 (list IDs)                 |
| **Conflicts**              | None / list conflicted files and resolution     |
| **Tests**                  | Targeted checks passed / list failures          |
| **Runtime result**         | Docker rebuilt / HTTP status / any regressions  |
| **Decision notes**         | Why this sync was done; any patches dropped or  |
|                            | adapted; anything to watch next time            |
```
