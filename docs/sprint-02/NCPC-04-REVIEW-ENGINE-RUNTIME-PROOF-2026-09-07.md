# NCPC-04 review engine runtime proof

Date: 2026-09-07  
Status: `ACCEPTED_FOR_NEXT_GATE`

The owner-authorized NCPC-04 gate ran on a fresh, project-namespaced
`nds-ncpc04-proof` PostgreSQL volume with current source mounted read-only into
the local runner. It created only synthetic principals and identity data.

The HTTP proof exercised business review denial, administrator `APPROVE_NEW`,
reviewer `MATCH_EXISTING`, `APPROVE_CORRECTION`, `NEEDS_MORE_INFORMATION` then
`WITHDRAW`, `REJECT`, and a repeated terminal decision rejection. Database
evidence showed exactly one canonical product/variant, the correction mutation,
and approved/matched/corrected, withdrawn, and rejected submissions. Canonical
creation/correction and review audits contain actor, timestamp, and correlated
non-null request IDs.

After recreating only the service runner on the same synthetic database,
`scripts/prove_review_engine.py --verify` emitted
`NCPC_REVIEW_ENGINE_RESTART_PERSISTENCE_PROVED`. Independent Test re-review
returned `ACCEPTED_FOR_NEXT_GATE`.

This is bounded local runtime evidence only. It does not approve production,
federated identity, release, deployment, external integration, commit, or push.
The next authorized gate is NCPC-05.
