# Open decisions and scenario validation

## Genuine open decisions

| Decision | Options | Recommendation | Consequence |
| --- | --- | --- | --- |
| Barcode normalization | exact-only; trim only; symbology-specific canonicalization | Preserve original string, trim outer whitespace, apply only documented symbology-safe normalization | Requires a formal per-symbology rule before migration. |
| Historic release reconstruction | trust release references; export current state; recover archived payloads | Treat existing releases as reference-only unless an exact payload is retained; start immutable snapshots prospectively | Historic exports may not be reproducible. |
| Coverage confirmation authority | NCPC self-declared; TradeFlow-signed; Ntheemba registry-mediated | Use a future authenticated TradeFlow/business assertion while Ntheemba remains canonical registry | Requires S03 contract and authorization design. |
| Category governance | flat controlled list; hierarchical curated taxonomy | Hierarchical curated NCPC taxonomy with versioning | Needs owner stewardship policy, not database design. |

## Required scenario walkthroughs

| Scenario | Domain representation and result |
| --- | --- |
| 1. Approved Coca-Cola 500ml | Product `PRD-X` and Variant `VAR-Y` are ACTIVE; an approved/published snapshot contains them. A TradeFlow local product optionally maps/records coverage to `VAR-Y`; its price and stock remain in TradeFlow. |
| 2. Unknown FreshBake Sweet Biscuits 100g | TradeFlow remains operational. A Submission proposes a new Product/Variant with PackDefinition `100 g`; state is PENDING_REVIEW, enabling only provisional within-business visibility. No trusted wider discovery. |
| 3. Barcode collision `6001234567890` | New Barcode claim is PENDING_VERIFICATION then CONFLICTED against the existing trusted Variant. Existing barcode resolution remains intact; reviewer decides with evidence. |
| 4. Coca Cola 500m correction | A correction Submission targets the existing Product/Variant and contains a ProposedChange from the observed text to `Coca-Cola Original 500ml`. Approved canonical data is unchanged until decision/publication. |
| 5. Duplicate Product | Reviewer selects survivor, marks duplicate MERGED with `superseded_by_id`; prior PRD/VAR references stay resolvable and snapshots remain historic. |
| 6. Coverage | Two BusinessCoverage records reference `VAR-123`, one for each external business/branch. Neither record contains price, stock or availability. |
| 7. Rejected submission | Submission is REJECTED; TradeFlow local product survives, canonical catalogue stays unchanged, Ntheemba visibility is unavailable, and a linked corrected submission may restart review. |

## Readiness

`READY FOR PHASE 02.2` for schema-design input only: the aggregate boundaries,
state machines, compatibility surface, risks and unknowns are explicit. It does
not authorize Phase 02.2 implementation, a migration, deployment or any
TradeFlow/Ntheemba connection. Sprint 01's owner runtime gate remains separate.
