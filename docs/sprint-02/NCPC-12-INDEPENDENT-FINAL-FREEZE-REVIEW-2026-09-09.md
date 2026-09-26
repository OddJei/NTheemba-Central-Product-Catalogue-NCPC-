# NCPC-12 Independent Final Freeze Review

Status: `NCPC_LOCAL_RUNTIME_PROVED / INDEPENDENT_REVIEW_ACCEPTED / EXTERNAL_RELEASE_GATES_PENDING`

## Decision requested

Determine whether NCPC is complete as a standalone, synthetic local-runtime
foundation. This review cannot confer production readiness or authorize
Sprint-03 implementation.

## Evidence ledger

| Gate | Local result and evidence |
| --- | --- |
| NCPC-01 / 02 | Legacy/domain/provider-independent foundation documented in the Sprint 02 baseline. |
| NCPC-03 | Submission lifecycle runtime proof accepted: `NCPC-03-SUBMISSION-LIFECYCLE-RUNTIME-PROOF-2026-09-07.md`. |
| NCPC-04 | Review engine runtime proof accepted: `NCPC-04-REVIEW-ENGINE-RUNTIME-PROOF-2026-09-07.md`. |
| NCPC-05 | Barcode conflict and duplicate/merge runtime proof accepted: `NCPC-05-CONFLICT-MERGE-RUNTIME-PROOF-2026-09-08.md`. |
| NCPC-06 | Publication/catalogue runtime proof accepted: `NCPC-06-PUBLICATION-CATALOGUE-RUNTIME-PROOF-2026-09-08.md`. |
| NCPC-07 | Same-origin service-aligned Admin UI proof accepted: `NCPC-07-ADMIN-UI-RUNTIME-PROOF-2026-09-08.md`. |
| NCPC-08 | Local admin auth, role ceiling, tenant, and audit proof accepted: `NCPC-08-ADMIN-AUTH-AUDIT-HARDENING-2026-09-08.md`. |
| NCPC-09 | Fresh Docker/PostgreSQL recovery and durable-state proof accepted: `NCPC-09-FULL-POSTGRESQL-DOCKER-RECOVERY-PROOF-2026-09-08.md`. |
| NCPC-10 | Failure, operational-data boundary, and tenant-isolation proof accepted: `NCPC-10-SECURITY-FAILURE-ISOLATION-PROOF-2026-09-08.md`. |
| NCPC-11 | Fresh r7 HTTP/Admin-UI end-to-end workflow and application-restart persistence accepted: `NCPC-11-END-TO-END-SYNTHETIC-ACCEPTANCE-2026-09-09.md`. |

## Current architectural result

NCPC owns product/variant identity, aliases, barcode claims, submissions,
reviews, publication, and non-operational BusinessCoverage references.
TradeFlow-owned price, cost, stock, availability, suppliers, batches, orders,
shops, sales, and policy are rejected at application validation and PostgreSQL
boundaries. Admin UI is a same-origin client; `/v1` remains the sole authority.

The complete synthetic service lifecycle is demonstrated: business submission,
pending review, authorized decision, stable PRD/VAR creation, barcode conflict
recording, identity merge history, immutable release evolution, public
catalogue search and exact verification, coverage visibility, audit history,
cross-business denial, and restart persistence.

## Migrations and database proof

Fresh isolated PostgreSQL applied this ordered chain:

```text
11ec987dd3e6
8f5be12c7e91
9ae61d0b4f72
3c1d8f5a2b10
4e7a91b2c6d3
5a8c2e9d7f41 (head)
```

The r7 environment passed Alembic `current` and `check` at head, direct
PostgreSQL invariant/restart proof from prior gates, and NCPC-11 E2E restart
persistence. The workspace-local SQLite development DB remains stale at
`3c1d8f5a2b10`; it is explicitly not used as current migration evidence.

## Defect discovered and remediated

NCPC-11 found that authorized `GET /v1/admin/barcodes` could raise a framework
error after real barcode rows existed, because ORM joins were ambiguous. The
query now explicitly joins `BarcodeClaim -> Variant -> Product`; a regression
test asserts the authorized filtered projection. No data migration was needed.

## Final checks

- Full pytest: 33 passed; one upstream Starlette deprecation warning.
- Ruff: passed.
- Strict Mypy: passed.
- Compileall: passed.
- Fresh r7 PostgreSQL: migration head and Alembic check passed.
- NCPC-11 synthetic service/Admin-UI workflow: completed.
- r7 application-only restart verifier:
  `NCPC_END_TO_END_SYNTHETIC_ACCEPTANCE_RESTART_PERSISTENCE_PROVED`.

## External release gates still pending

- Federated production identity and production secret management.
- Deployment-specific ingress/rate limiting and external network policy.
- Production backup/restore and production migration/deployment procedure.
- Approved non-production or production environment validation.
- Any TradeFlow/Ntheemba integration, live Sheets, Apps Script, customer data,
  production credentials, commit, and push.

## Required independent conclusion

If independent Test and Security/Reality reviewers find no unresolved Critical
or High issue, record exactly:

```text
NCPC_LOCAL_RUNTIME_PROVED
INDEPENDENT_REVIEW_ACCEPTED
EXTERNAL_RELEASE_GATES_PENDING
```

Only then recommend `SPRINT-03 — TRADEFLOW <-> NCPC INTEGRATION` as the next
owner gate, and stop pending separate owner authorization.

## Independent final conclusion

On 2026-09-09, independent Test and Security/Reality review each accepted the
freeze with no unresolved Critical or High finding. The final conclusion is:

```text
NCPC_LOCAL_RUNTIME_PROVED
INDEPENDENT_REVIEW_ACCEPTED
EXTERNAL_RELEASE_GATES_PENDING
```

Recommendation: `SPRINT-03 — TRADEFLOW <-> NCPC INTEGRATION` is the next owner
gate only. It is not authorized by this freeze, and no implementation,
deployment, commit, push, external integration, or production action follows
from this document.
