# NCPC-10 Security, Failure, and Tenant-Isolation Proof

Status: `NCPC_SECURITY_FAILURE_ISOLATION_PROVED / ACCEPTED_FOR_NEXT_GATE`

## Scope

Synthetic local Docker/PostgreSQL only. No production identity, Sheets, Apps
Script, customer data, external integration, deployment, commit, or push was
used.

## Remediated findings

- A false or absent `Content-Length` could bypass the original size guard. The
  service now bounds actual streamed request bytes before routing.
- `BusinessCoverage.location_projection` could hold TradeFlow operational data.
  Request validation and PostgreSQL migrations `4e7a91b2c6d3` and
  `5a8c2e9d7f41` reject operational keys, including nested price, cost, stock,
  availability, supplier, batch, sales, order, shop configuration, and policy.
- A PostgreSQL connection failure now returns a no-store v1 `503
  DATABASE_UNAVAILABLE` envelope rather than a framework error.

## Evidence

- Source tests cover malformed JSON, actual-body oversize with forged length,
  missing/wrong authority, forged tenant fields, cross-business submission and
  coverage read/write denial, operational payload rejection, and safe database
  outage mapping.
- Existing NCPC-05 proof exercises concurrent barcode collisions and durable
  merge replay. Existing PostgreSQL invariants prove publication and audit
  update/delete rejection. Existing NCPC-07 Admin UI proof confirms browser
  actions use server-authorized `/v1` endpoints.
- Fresh isolated project `ncpc10-independent-review` migrated from an empty,
  project-namespaced synthetic volume to `5a8c2e9d7f41 (head)`. Its direct
  invariant writer emitted `NCPC_POSTGRESQL_INVARIANTS_WRITE_PROVED`. A direct
  synthetic `BusinessCoverage` insert containing `stock` was rejected with
  `ERROR: TradeFlow-owned operational data is forbidden in NCPC`; the attempted
  row count remained zero. After an application-only container restart that
  preserved the named PostgreSQL volume, the direct verifier emitted
  `NCPC_POSTGRESQL_INVARIANTS_RESTART_PERSISTENCE_PROVED`.
- In the same fresh stack, stopping PostgreSQL caused
  `scripts/prove_ncpc10_database_outage.py` to emit
  `NCPC10_DATABASE_UNAVAILABLE_SAFE_FAILURE_PROVED`, before PostgreSQL was
  restarted. The existing independent `ncpc09-recovery-r4` proof separately
  recorded publication-catalogue restart persistence; it is supporting, not
  substitute, evidence for the fresh NCPC-10 stack.
- Final source validation passed: 32 tests, Ruff, strict Mypy, compileall, and
  Alembic check. The focused API adversarial suite passed 12 tests.

## Limits and next gate

Independent Test and Security/Reality review accepted this bounded synthetic
local proof on 2026-09-09. No production readiness is claimed. Production
federated identity, ingress/rate limits, network policy, backup/restore,
migration/deployment controls, and external integrations remain release gates.
NCPC-11 may proceed only under the same owner-authorized synthetic local
boundary.
