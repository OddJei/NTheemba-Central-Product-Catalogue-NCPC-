# NCPC-08 Admin Auth / Audit Hardening

Status: `NCPC_ADMIN_AUTH_AUDIT_HARDENING_PROVED / ACCEPTED_FOR_NEXT_GATE`

## Scope and authority

Owner authorization permits NCPC-08 only, using synthetic local configuration.
No federated identity, deployment, production secret, customer data, TradeFlow
integration, commit, or push was used.

## Implemented hardening

- `Principal.require_scope` now applies a non-bypassable role ceiling before
  assigned scopes. A BUSINESS or NTHEEMBA client cannot become an operator by
  receiving `*` or an accidental operator scope in a local client record.
- REVIEWER may read/decide reviews and merge identities, but cannot publish;
  ADMIN is the only local role permitted to publish.
- Audit actor remains `principal.client_id`, never a request field. Barcode
  conflicts now create an actor/request-correlated audit event.
- Publication and BusinessCoverage preference changes require a rationale and
  store it in the append-only audit event. The local Admin UI sends a
  publication rationale but continues to call only server-authorized `/v1` APIs.
- Independent Test and Security/Reality review found missing audit events for
  coverage lifecycle mutations. The remediation records individual coverage
  creation, review-state, link, publication-promotion, and variant-remap events
  with the server principal, request correlation, timestamp, and available
  decision rationale. Product merge now persists its operation and returns the
  same result for a durable idempotent replay.

## Evidence

Working directory: `apps/central-catalogue/service`

```text
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest
27 passed, 1 warning

.\.venv\Scripts\python.exe -m ruff check src tests scripts
All checks passed!

.\.venv\Scripts\python.exe -m mypy --strict src
Success: no issues found in 19 source files

.\.venv\Scripts\python.exe -m compileall -q src tests scripts
passed

.\.venv\Scripts\alembic.exe check
passed
```

`tests/test_ncpc08_auth_audit.py` directly proves missing/invalid auth, an
over-scoped business token, reviewer publication denial, forged actor input,
request correlation, required publication rationale, and absence of test tokens
from the Admin UI and error responses.
`tests/test_workflow.py` proves coverage creation, review linking, and
publication promotion each have their own audit record; `test_publication_and_merge.py`
proves product-merge replay returns the original result.

## Runtime limitation and next gate

The initial Docker Hub resolution failed with a TLS handshake timeout. The
proof then used a local-only overlay based on the cached
`nds-ncpc03-proof-ncpc:latest` NCPC runtime image, copying the current source,
migrations and proof scripts with `PYTHONPATH=/app/src`. It does not pull from
Docker Hub or use a prior proof volume.

The separately named `ncpc08-auth` project started current source against a
fresh project-namespaced PostgreSQL volume. After migration readiness was
directly confirmed at Alembic head `3c1d8f5a2b10`, the following passed:

```text
NCPC_POSTGRESQL_INVARIANTS_WRITE_PROVED
NCPC_POSTGRESQL_INVARIANTS_RESTART_PERSISTENCE_PROVED
NCPC08_AUTH_AUDIT_POSTGRES_PROVED
```

The runtime proof verifies a business client with an accidental `*` scope is
denied admin review access; a reviewer can read reviews but cannot publish; a
forged request actor is ignored; and the persisted audit event contains the
authenticated actor, request ID, and database timestamp. The application
container was restarted while retaining the isolated PostgreSQL volume before
the invariant persistence verification.

This is local synthetic runtime evidence only. Independent Test and
Security/Reality re-review each accepted the result after directly rerunning
the persistence and auth/audit verifiers against the live isolated stack. The
exit is `NCPC_ADMIN_AUTH_AUDIT_HARDENING_PROVED`; NCPC-09 may proceed only
under its separately authorized synthetic local recovery scope.

## Independent re-review

Independent Test and Security/Reality re-review accepted the remediated
source/local scope on 2026-09-08. Each reran the focused coverage-audit and
product-merge replay tests; Test also reran the full 27-test suite, Ruff,
strict Mypy, compileall, and Alembic check. Each then directly reran the
isolated Docker/PostgreSQL persistence and HTTP auth/audit proof. Therefore
the iteration carries `NCPC_ADMIN_AUTH_AUDIT_HARDENING_PROVED /
ACCEPTED_FOR_NEXT_GATE`; NCPC-09 was permitted to proceed under the separate
owner authorization.

Production federated identity, secrets infrastructure, ingress/rate limits,
network policy, backup/restore, migration, and deployment remain external
release gates.
