# NCPC-01: Reality audit and proposed freeze baseline

Date: 2026-09-07

Status: `NCPC_POSTGRESQL_INVARIANTS_RUNTIME_PROVED`

## Scope and authority

This is a source-and-local-evidence audit of NCPC. NCPC-02 has been completed
against a synthetic, isolated local PostgreSQL volume; this does not deploy,
change customer data, or use production credentials.

NCPC remains authoritative only for shared Product/Variant identity, aliases,
barcode claims, review, publication and non-operational coverage visibility.
TradeFlow remains authoritative for tenant price, cost, stock, availability,
suppliers, orders, sales, batches, shops and policy.

Ntheemba N1-N24 is frozen at the separately recorded checkpoint
`NTHEEMBA_N1_N24_LOCAL_RUNTIME_PROVED_INDEPENDENT_REVIEW_ACCEPTED_EXTERNAL_RELEASE_GATES_PENDING`.
This audit does not authorize N25/N26, LLM, WhatsApp/WAHA, deployment, or a
cross-product runtime connection.

## Verified facts

| Area | Verified current state | Evidence and limitation |
| --- | --- | --- |
| New NCPC service | FastAPI service version `0.2.8` exists with SQLAlchemy models, Alembic revision `11ec987dd3e6`, service layer and authenticated `/v1` API. | Source inspected. The current runtime was not started in this audit. |
| Identity and database guards | Product/Variant IDs, alias target constraint, trusted-active barcode uniqueness, merge-survivor guards, and PostgreSQL immutable snapshot/audit triggers are implemented. | Migration inspected. PostgreSQL trigger behavior needs independent real-PostgreSQL workflow evidence. |
| Submission, review and publication | Idempotent submissions, review decisions, conflict-preserving barcode claims, merge/remap and immutable, identity-only publication snapshots are implemented. | Service and tests inspected. |
| API safety | Bearer principal/scopes, tenant binding, request IDs, safe envelopes, body limit and identity-only public DTOs are implemented. | API and tests inspected; no ingress/distributed rate-limit or production identity proof. |
| Local checks | `pytest`, Ruff and strict Mypy pass. | Run 2026-09-07 from `apps/central-catalogue/service`; source tests use local test persistence, not the Docker PostgreSQL workflow. |
| Local Docker | Prior repository evidence records healthy NCPC/PostgreSQL, migration revision and loopback health response. | Recorded in `Docs/roadmap/CURRENT_STATUS.md`; not re-run in this audit. Existing-volume credential recovery remains an owner action. |
| Operator UI | `apps/central-catalogue/index.html` is an Apps Script UI using `google.script.run`, not the new `/v1` service. | It cannot satisfy the requested service-aligned NCPC admin workflow without an adapter/replacement decision. |

## Gap matrix

| Planned iteration | Audit result | Proposed next gate |
| --- | --- | --- |
| NCPC-01 baseline audit | Complete for source/local evidence. | Owner accepts this baseline before implementation sequencing. |
| NCPC-02 real PostgreSQL invariant proof | Complete: expanded direct PostgreSQL write/restart proof passed at Alembic head `3c1d8f5a2b10`; independent Test review passed against the R4 stack. | Owner subsequently authorized NCPC-03 through NCPC-07. |
| NCPC-03 submission lifecycle | Complete for the named local-runtime scope; independent Test review accepted it for the next gate. | NCPC-04 review-engine runtime proof. |
| NCPC-04 review engine | Complete for the named local-runtime scope; independent Test re-review accepted it for the next gate. | NCPC-05 barcode/duplicate-conflict runtime proof. |
| NCPC-05 barcode/duplicate conflicts | Complete for the named local-runtime scope; independent Test re-review accepted it for the next gate. | NCPC-06 publication/catalogue runtime proof. |
| NCPC-06 publication/catalogue runtime | Implemented and source-tested; Docker health/migration evidence exists. | Reproducible real-stack publish/search/reconstruct workflow. |
| NCPC-07 service-aligned admin UI | Missing. Legacy Apps Script UI is a separate authority/model. | Architecture decision, then a UI that calls `/v1` and preserves server authority. |
| NCPC-08 operator auth/audit | Accepted for its named synthetic local scope after independent Test and Security/Reality re-review. | Federated production identity, ingress controls, and deployment approval remain external. |
| NCPC-09 PostgreSQL/Docker proof | Accepted for the bounded synthetic local scope after independent Test and Security/Reality review. | Backup/restore and production recovery remain external. |
| NCPC-10 failure/security/isolation proof | Accepted for the bounded synthetic local scope after independent Test and Security/Reality review. | Federated identity, ingress/rate controls, backup/restore, deployment, and external integrations remain external. |
| NCPC-11 end-to-end acceptance | Accepted for the bounded synthetic local scope after independent Test and Security/Reality review. | Federated identity, ingress/rate controls, backup/restore, deployment, and external integrations remain external. |
| NCPC-12 independent freeze review | Accepted: `NCPC_LOCAL_RUNTIME_PROVED / INDEPENDENT_REVIEW_ACCEPTED / EXTERNAL_RELEASE_GATES_PENDING`. | Separate owner authorization before Sprint-03; production release gates remain external. |

## Proposed freeze baseline

Freeze the implementation baseline at:

```text
NCPC_POSTGRESQL_INVARIANTS_RUNTIME_PROVED
SERVICE_ALIGNED_ADMIN_UI_PENDING
FULL_POSTGRESQL_WORKFLOW_RECOVERY_PENDING
INDEPENDENT_SECURITY_REALITY_REVIEW_PENDING
EXTERNAL_RELEASE_GATES_PENDING
```

This deliberately does not claim `NCPC_LOCAL_RUNTIME_PROVED` for the whole
product. Health plus migration proves startup, not the complete durable
submission-to-publication workflow or recovery.

## Evidence run in this audit

Working directory: `apps/central-catalogue/service`

```text
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest
18 passed, 1 warning

.\.venv\Scripts\python.exe -m ruff check .
All checks passed!

.\.venv\Scripts\python.exe -m mypy src
Success: no issues found in 19 source files
```

## Risks and stop conditions

- Do not replace the legacy Apps Script UI by silently pointing it at the new
  service: its model and authorization path differ and need a boundary decision.
- Do not call a health endpoint, SQLite unit suite, or migration render proof of
  complete PostgreSQL persistence/recovery.
- Do not start service integration with TradeFlow or Ntheemba, use live data,
  or alter the active Sprint-01 owner runtime-review gate.
- Stop for an owner decision on admin UI hosting/authentication, any irreversible
  data migration, production identity, or any external connection.

## Orchestrated handoff

| Role | Responsibility before a final NCPC freeze |
| --- | --- |
| Architect / requirements owner | Accept the baseline and choose the service-aligned admin UI boundary. |
| NCPC implementation | Deliver one approved iteration at a time, beginning with the chosen next gate. |
| Test reviewer | Re-test source and real PostgreSQL evidence independently. |
| Security/Reality reviewer | Independently assess auth, audit, data isolation, recovery evidence and UI boundary. |
| Release gate owner | Retain external identity, secrets, backup/restore and deployment decisions. |

Next owner authorization was supplied for the bounded NCPC-03 through NCPC-07
local-only batch. NCPC-03 is accepted for the next gate; NCPC-04 is active.

## NCPC-02 accepted runtime evidence (2026-09-07)

The dedicated local-only Compose project `nds-ncpc02-proof-r4` used the fresh,
project-namespaced volume `nds-ncpc02-proof-r4_ncpc-proof-data`. Existing
NCPC/Ntheemba containers and volumes were not used, reset, or changed.

The direct `psycopg` proof intentionally bypassed API/domain parsing and
observed PostgreSQL reject invalid and mutable PRD/VAR identifiers, orphan
Variant ownership, Alias rows with both or neither target, duplicate
trusted-active barcode claims, Product/Variant self-merge, targetless or
duplicate active BusinessCoverage, nested TradeFlow operational JSON, released
publication entry/snapshot mutation or deletion, and audit mutation/deletion.
It preserved distinct trusted and `CONFLICTED` barcode claims, valid merge
survivors, an approved Alias, direct and submission-backed BusinessCoverage,
the immutable publication entry, and the append-only audit record. The proof
then restarted only R4's NCPC application container and verified all of those
persisted records.

Runtime commands and result:

```text
docker compose -p nds-ncpc02-proof-r4 -f docker-compose.runtime-proof.yml exec -T ncpc python scripts/prove_postgres_invariants.py write
NCPC_POSTGRESQL_INVARIANTS_WRITE_PROVED

docker compose -p nds-ncpc02-proof-r4 -f docker-compose.runtime-proof.yml restart ncpc
docker exec nds-ncpc02-proof-r4-ncpc-1 python scripts/prove_postgres_invariants.py verify
NCPC_POSTGRESQL_INVARIANTS_RESTART_PERSISTENCE_PROVED

docker compose -p nds-ncpc02-proof-r4 -f docker-compose.runtime-proof.yml exec -T ncpc alembic current
3c1d8f5a2b10 (head)
```

Source regression after the migration changes:

```text
pytest: 18 passed, 1 warning
ruff: all checks passed
mypy src: Success: no issues found in 19 source files
compileall: passed
alembic upgrade head (SQLite structural path): passed
```

An initial runtime attempt exposed an invalid recursive PostgreSQL trigger
query. It was repaired by migration `9ae61d0b4f72`; migration `3c1d8f5a2b10`
then added public Product/Variant identity immutability. The expanded proof
and its restart verification were independently accepted by the Test reviewer
against R4 only. This proves the named NCPC-02 local invariant scope, not the
remaining submission/review/publication recovery workflow, security review,
or any deployed environment.
