# NCPC-09 Full PostgreSQL / Docker Recovery Proof

Status: `NCPC_FULL_POSTGRESQL_DOCKER_RECOVERY_PROVED / ACCEPTED_FOR_NEXT_GATE`

## Scope and authority

The owner authorized an isolated, synthetic Docker/PostgreSQL proof only. No
production service, live database, customer data, external integration,
credential, deployment, commit, push, volume deletion, or manual database
repair was used.

Working directory: `apps/central-catalogue/service`.

The proof project was `ncpc09-recovery-r4`. It uses the current source,
migrations, and scripts overlaid onto the cached local
`nds-ncpc03-proof-ncpc:latest` image through
`Dockerfile.ncpc08-local-proof` and `docker-compose.ncpc08-local-proof.yml`.
`pull_policy: never` avoids Docker Hub pulls. Its PostgreSQL named volume was
retained for every restart/recreate operation.

## Runtime evidence

After migration head `3c1d8f5a2b10` and synthetic proof-client seeding, the
fresh volume passed the existing end-to-end writes:

```text
NCPC_SUBMISSION_LIFECYCLE_WRITE_PROVED
NCPC_REVIEW_ENGINE_PROVED PRD-000002 VAR-000002
NCPC_CONFLICT_MERGE_RUNTIME_PROVED PRD-000003 VAR-000003 PRD-000004 VAR-000004
NCPC_PUBLICATION_CATALOGUE_RUNTIME_PROVED PRD-000007 VAR-000007
```

The application was recreated while retaining PostgreSQL, PostgreSQL was
restarted while the application reconnected, and then both containers were
stopped and started on the same named volume. After each recovery boundary the
following passed:

```text
NCPC_SUBMISSION_LIFECYCLE_RESTART_PERSISTENCE_PROVED
NCPC_CONFLICT_MERGE_RESTART_PERSISTENCE_PROVED
NCPC_PUBLICATION_CATALOGUE_RESTART_PERSISTENCE_PROVED
```

The final application recreation used the local `/health` probe and again
passed all three recovery verifiers. The host showed a short Uvicorn readiness
delay after a full stop/start; waiting for the health endpoint resolved it. It
was a startup timing observation, not data loss.

A direct read-only aggregate on the retained synthetic database found:

```text
products 7; variants 7; aliases 1; barcode_claims 6; submissions 18;
review_decisions 17; identity_relationships 2; business_coverages 14;
publication_snapshots 2; publication_entries 12; audit_events 83.

submissions: APPROVED 3, PENDING_REVIEW 3, PUBLISHED 9, REJECTED 2, WITHDRAWN 1
variants: ACTIVE 6, MERGED 1
barcode claims: CONFLICTED 3, VERIFIED_ACTIVE 3
```

This proves retained identities, aliases, barcode claims/conflicts, pending and
decided submissions/reviews, corrections, historical merge references,
BusinessCoverage, current publication/release reconstruction, audit history,
and safe idempotent merge replay. An approved submission may legitimately be
`PUBLISHED` after the later publication proof; the recovery verifier accepts
both terminal valid states.

## Source validation

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
No new upgrade operations detected.
```

## Limits and next gate

No backup/restore exercise was performed, so backup/restore truthfulness,
production recovery runbooks, production identity, ingress/network controls,
production migration, deployment, and external integration remain release
gates. Independent Test accepted this bounded result after rerunning focused
source checks (24 passed) and all three isolated recovery verifiers. Independent
Security/Reality accepted after inspecting the current-source cached overlay,
healthy isolated stack, scope boundary, authority protections, and residual
release gates; it reported no Critical or High finding. NCPC-10 may begin only
within the owner-authorized synthetic local scope.
