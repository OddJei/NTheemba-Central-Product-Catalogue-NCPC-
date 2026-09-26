# Final NCPC domain model

## Boundary and ownership

```text
Product 1 --- * Variant 1 --- * Barcode
   |                 |
   * --- Alias       * --- BusinessCoverage --- external Business/Branch/Location references
   |
   * --- Submission --- * ProposedChange --- * Review / ReviewerDecision
   |
   * --- PublicationSnapshot (immutable)
```

NCPC owns canonical identity, identity quality, review and coverage references.
It does not own business price, cost, stock, current availability, sales,
expenses, POS, profitability or shop configuration. The Ntheemba business
registry remains canonical for business capability/profile and geography remains
outside NCPC; NCPC stores only opaque references/projections needed for coverage.

## Aggregates and entities

### Product

A Product is a canonical family: `PRD-*`, canonical name, optional Brand,
canonical Category assignment, lifecycle, created/changed attribution and a
normalization/search projection. It answers the conceptual identity, not a
specific purchasable package. Product owns product-level aliases and links to
variants. It may be unbranded where evidence warrants it.

### Variant

A Variant is exactly one Product's identifiable form: `VAR-*`, canonical
variant label, PackDefinition, optional identifying attributes (for example
flavour or colour), lifecycle and search projection. A variant, not a business
product, is the target of barcodes and coverage. It must never contain TradeFlow
operational price/stock data.

### Barcode

Barcode is a separate claim associated with one Variant: original text value,
normalised lookup value, optional symbology, provenance (`scanned`,
`manual_entry`, `ncpc_admin`, `generated`, `imported`), verification state,
active state, submitter/source reference and timestamps. It records a conflict
instead of silently reassigning a normalized collision. One variant may have
many barcode claims; one trusted active normalized barcode has at most one
trusted active Variant.

### Alias

Alias holds display text, normalized text, exactly one target (Product or
Variant), alias kind, optional language, source/provenance, approval state and
timestamps. Search observations/fuzzy strings are not aliases until approved.

### Brand and Category

Brand is a controlled reference entity with canonical and normalized name,
lifecycle and optional organization relationships. That avoids duplicated
brand spelling while staying lighter than a manufacturer-centric aggregate.
Category is a controlled, versioned NCPC taxonomy reference (with optional
parent), independent from a TradeFlow business's reporting category. Neither
is required to invent facts when unknown.

### PackDefinition

A value object owned by Variant: `primary_measure { value, unit }`, optional
`count`, optional `each_measure`, `packaging/form`, and preserved
`display_text`. Examples: `500 ml bottle`; `6 x 500 ml carton`; `1 kg sachet`.
It replaces a single ambiguous size field while allowing unknown components.

### Submission, ProposedChange and Review

Submission is one coherent proposal envelope: type (new product/variant,
barcode/alias addition, correction, possible duplicate, merge or general
correction), submitter/source, optional business/TradeFlow installation
reference, target entity when applicable, idempotency/request reference, state
and timestamps. It owns one or more ProposedChanges with structured field/path,
old value if known, proposed value and evidence/provenance. Review owns
reviewer decisions/comments/correction requests. Review does not mutate an
approved identity until an allowed decision applies the accepted proposal.

### BusinessCoverage

BusinessCoverage associates an NCPC Variant with an external `business_id` and
optional `branch_id`/shop ID. It retains source/link type, status, first linked,
last confirmed and optional opaque province/district/town/area projection IDs.
It means association only—never price, stock or live availability. A business
may manage only its own coverage and submissions.

### PublicationSnapshot and AuditEvent

The recommended publication model is **live catalogue plus immutable versioned
publication snapshots**. Approved canonical data can evolve live; publishing
creates immutable, content-addressed snapshot items/payload and audit event.
Consumers pin/cache a snapshot/version; rollback selects a prior snapshot rather
than mutating history. Audit requirements cover actor, time, old/new value,
source, decision and rationale for important identity changes.

## Visibility policy

Visibility is derived from explicit submission/review/publication state, not
contradictory booleans:

| State | TradeFlow operation | Ntheemba within business | Wider trusted discovery |
| --- | --- | --- | --- |
| Unsubmitted | unaffected | no | no |
| Submitted/pending review | unaffected | provisional | no |
| Approved and published | unaffected | yes | yes |
| Rejected | unaffected | no, until resubmitted | no |

This policy concerns an identity association/submission; it never asserts that
the business currently has stock. A future Ntheemba result still verifies
price/availability with TradeFlow.

## Duplicate and merge model

Duplicates create a reviewable relation, never automatic deletion. A merge
accepts a canonical survivor, marks the old Product/Variant `MERGED`, retains
its stable ID, records `superseded_by_id`, and makes lookup return a redirect
with historical trace. Existing Barcode/Alias/Coverage links are either retained
as history or explicitly moved through audited decisions. A merge cannot break
published snapshot content or overwrite a trusted barcode claim.
