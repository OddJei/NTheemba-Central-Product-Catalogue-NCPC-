# NCPC-03 submission lifecycle runtime proof

Date: 2026-09-07  
Status: `ACCEPTED_FOR_NEXT_GATE`

## Scope and authority

The owner authorized NCPC-03 through NCPC-07 as a sequential, local-only
batch. This record covers NCPC-03 only: product and identity-correction
submissions, idempotency, tenant/role rejection, lifecycle transitions, audit
events, and restart persistence. It used a fresh project-namespaced PostgreSQL
volume in Docker project `nds-ncpc03-proof`. No production service, customer
data, deployment, external integration, commit, or push was used.

NCPC remains the authority for shared identity and its review lifecycle.
TradeFlow operational facts (price, stock, availability, policy) were neither
accepted nor returned by this proof.

## Source changes

- An eligible `REJECTED` or `NEEDS_CHANGES` submission may be explicitly
  linked by `previous_submission_id` to its replacement. The server validates
  business and submitter ownership and keeps the original submission intact.
- Reusing an idempotency key with a materially different request now fails with
  `409`; a matching retry returns the original submission.
- Both new-product and correction request DTOs support the optional linked
  prior public submission identifier.

## Reproducible evidence

From `apps/central-catalogue/service`:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m ruff check scripts/prove_submission_lifecycle.py src
.\.venv\Scripts\python.exe -m mypy src scripts/prove_submission_lifecycle.py
docker exec nds-ncpc03-proof-runner python scripts/prove_submission_lifecycle.py verify `
  --approved-id SUB-000001 --corrected-id SUB-000003 --correction-id SUB-000004
```

Observed results:

- Ruff: `All checks passed!`
- strict Mypy: `Success: no issues found in 20 source files`
- HTTP persistence verifier: `NCPC_SUBMISSION_LIFECYCLE_RESTART_PERSISTENCE_PROVED`
- The isolated database retained `SUB-000001` (`APPROVED`), `SUB-000002`
  (`REJECTED`), linked replacement `SUB-000003` (`PENDING_REVIEW`), and
  identity correction `SUB-000004` (`PENDING_REVIEW`) after runner recreation.
- The write proof exercised matching retry, altered-payload idempotency conflict,
  cross-tenant read denial, business review denial, needs-information,
  approval, rejection, repeated terminal decision rejection, linked
  reject-and-correct, and the actual correction endpoint. Audit rows recorded
  creation/review actors, request IDs, and timestamps.

Focused workflow tests were run after the source change; the environment did
not emit a pytest summary despite completion, so that run is not represented as
a full-suite pass claim.

## Independent review and limits

An independent Test reviewer rechecked the initial findings (audit attribution,
linked correction history, altered idempotency replay, non-hardcoded proof
inputs, and correction endpoint evidence) and returned
`ACCEPTED_FOR_NEXT_GATE` after remediation.

This is not a production, federated-identity, Security/Reality, release, backup
restore, or external-integration approval. The next authorized sequential gate
is NCPC-04 review-engine runtime proof.
