# Lifecycle model

## Submission lifecycle

```text
DRAFT -> SUBMITTED -> PENDING_REVIEW -> APPROVED -> PUBLISHED
              ^             |              |
              |             +-> NEEDS_CHANGES -+
              |             +-> REJECTED
              +------------------------------- (new corrected submission)
```

`SUBMITTED` records receipt; it advances promptly to `PENDING_REVIEW` once
validation accepts the envelope. `APPROVED` means catalogue authority accepted
the proposed identity/change; `PUBLISHED` means the accepted identity appears
in normal consumer catalogue snapshots. A rejected submission is terminal for
that submission; a correction creates a new submission linked to it.

Allowed: DRAFT→SUBMITTED, SUBMITTED→PENDING_REVIEW, PENDING_REVIEW→APPROVED /
NEEDS_CHANGES / REJECTED, NEEDS_CHANGES→SUBMITTED, APPROVED→PUBLISHED. Forbidden:
REJECTED→PUBLISHED, PUBLISHED→DRAFT, or direct mutation of a previously decided
proposal without a new audited submission.

## Product and Variant lifecycle

Both use `ACTIVE`, `DEPRECATED`, `MERGED`, `RETIRED`. A Variant also cannot be
`ACTIVE` when its parent is retired. Allowed transitions are ACTIVE→DEPRECATED /
MERGED / RETIRED; DEPRECATED→ACTIVE only by documented review; DEPRECATED or
MERGED→RETIRED. `MERGED` must name a surviving same-kind identity. No ordinary
hard delete exists; a bad draft may be administratively voided only if no
reference/audit/publication record depends on it.

## Barcode lifecycle

```text
PROPOSED -> PENDING_VERIFICATION -> VERIFIED_ACTIVE
                 |                       |
                 +-> CONFLICTED           +-> DEPRECATED / REPLACED
                 +-> REJECTED
```

Verification of a normalized collision creates/retains `CONFLICTED` with both
claims and reviewer evidence. It must not replace the existing trusted claim.
`REPLACED` preserves the old value and names the successor claim; `DEPRECATED`
removes it from normal lookup without destroying provenance.

## Publication lifecycle

An approved active identity is eligible for a new immutable snapshot. Snapshot
states are `CREATED -> PUBLISHED -> SUPERSEDED` (or `WITHDRAWN` for a consumer
withdrawal event). Historic published payloads are immutable. Live entity edits
cannot alter a past snapshot; a corrected publication creates a new version.
