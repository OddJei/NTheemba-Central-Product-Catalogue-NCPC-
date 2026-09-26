# NCPC-11 Full Synthetic End-to-End Acceptance

Status: `NCPC_END_TO_END_SYNTHETIC_ACCEPTANCE_PROVED / ACCEPTED_FOR_NEXT_GATE`

## Scope and reproduction

This proof used the fresh, project-namespaced Docker Compose project
`ncpc11-e2e-proof-r7` and its isolated synthetic PostgreSQL volume. No
production system, live business data, secret, deployment, commit, push, or
TradeFlow/Ntheemba integration was used. Synthetic local proof principals were
created only to authenticate the test workflow; every product, submission,
review, coverage, merge, publication, and query operation used `/v1` service
routes. No product-state SQL was issued by the acceptance runner.

Reproduce from `apps/central-catalogue/service` with the two local proof Compose
files, a new project name, then:

```text
python scripts/seed_ncpc_runtime_proof_clients.py
python scripts/prove_ncpc11_end_to_end.py write
# restart only the ncpc container, retaining the named PostgreSQL volume
python scripts/prove_ncpc11_end_to_end.py verify
```

The fresh stack applied `5a8c2e9d7f41 (head)`.

## Validation boundary

Current source validation passed: 33 pytest tests (one upstream Starlette
deprecation warning), Ruff, strict Mypy, and compileall. The repository-local
SQLite development database is intentionally not asserted as migration-current:
it remains at the older `3c1d8f5a2b10` head. Alembic `current` and `check` were
instead run against the fresh r7 isolated PostgreSQL environment at
`5a8c2e9d7f41`; that is the authoritative migration validation for this Docker
proof. This distinction prevents a stale local SQLite file from being reported
as fresh PostgreSQL evidence.

## Proved workflow

- Same-origin Admin UI was served and its operator controls referenced
  server-authorized `/v1` routes.
- A Business A unknown product entered `PENDING_REVIEW`; idempotent retry
  returned the same submission.
- Business B was denied both the submission and Business A coverage.
- The Admin review created PRD/VAR identity, alias, and barcode claim. Before
  publication, customer-facing catalogue search did not expose it.
- Release `NCPC11-R1` enabled catalogue search and exact PRD/VAR verification.
  Coverage became `LINKED_APPROVED`; its business preference change remained
  tenant-authorized.
- A rejected submission could not transition to approval and did not become a
  published identity.
- A duplicate barcode produced an explicit `CONFLICTED` claim correlated with
  the original claim through one conflict group.
- Variant and product duplicate merges were idempotent; the merge audit record
  retained the historical source variant reference.
- A correction produced `NCPC11-R2`; the older R1 version, hash, and item count
  remained unchanged through the public read surface.
- Operational `location_projection.stock` was rejected with the safe v1
  `422 INVALID_REQUEST` envelope and was never persisted.
- After an application-only restart preserving the isolated PostgreSQL volume,
  the verifier emitted:

```text
NCPC_END_TO_END_SYNTHETIC_ACCEPTANCE_RESTART_PERSISTENCE_PROVED
```

## Defect remediated during acceptance

The workflow exposed an ambiguous ORM join in authorized
`GET /v1/admin/barcodes`, which produced a framework error when real barcode
rows existed. It was fixed by anchoring the query at `BarcodeClaim` with
explicit Variant and Product joins. `tests/test_api.py` now covers the
authorized filtered barcode listing and identity projection.

## Limits and next gate

Independent Test and Security/Reality review accepted this bounded synthetic
local proof on 2026-09-09. This is not production readiness.
Federated identity, secret management, ingress/rate limits, network policy,
backup/restore, production migrations/deployment, and external integration are
still release gates. Independent Test and Security/Reality review must accept
this evidence before NCPC-12 begins.
