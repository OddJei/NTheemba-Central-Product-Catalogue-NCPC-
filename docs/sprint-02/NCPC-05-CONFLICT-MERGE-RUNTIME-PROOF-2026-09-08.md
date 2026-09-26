# NCPC-05 barcode, duplicate, and merge runtime proof

Date: 2026-09-08  
Status: `ACCEPTED_FOR_NEXT_GATE`

Fresh isolated PostgreSQL project `nds-ncpc05-proof` exercised synchronized
competing barcode approvals. PostgreSQL transaction-scoped advisory locking on
the normalized barcode now serializes the empty-claim check and insert: the
proof retained one `VERIFIED_ACTIVE` claim and two `CONFLICTED` claims for the
same leading-zero barcode, rather than returning a uniqueness failure.

The proof also retained duplicate Product/Variant proposals as
`PENDING_REVIEW`; required an explicit Variant merge before a constrained
Product-shell merge; retained historical PRD/VAR source records as `MERGED`;
remapped source `BusinessCoverage`; rejected self-merge; and recorded merge
actor/request audit entries. The service runner was recreated on the same
synthetic volume and the verifier emitted
`NCPC_CONFLICT_MERGE_RESTART_PERSISTENCE_PROVED`.

Focused merge tests and the full NCPC pytest suite passed (21 tests). An
independent Test re-review returned `ACCEPTED_FOR_NEXT_GATE`. This is local
synthetic evidence only, not a production, release, or federated-identity
approval. The next authorized gate is NCPC-06.
