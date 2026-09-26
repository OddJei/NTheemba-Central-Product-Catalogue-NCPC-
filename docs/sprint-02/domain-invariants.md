# Domain invariants

1. A Product ID and Variant ID are immutable stable identities; names are never identity.
2. Every Variant belongs to exactly one Product; moving it is a merge/supersession decision, not a silent foreign-key edit.
3. Barcode original and normalized values are strings; normalization never drops leading zeroes or overwrites the original.
4. A normalized trusted active barcode resolves to at most one trusted active Variant. Collisions are explicit conflict/review records.
5. A Barcode source/provenance and verification state accompany every claim; generated values never replace scanned values implicitly.
6. An Alias targets exactly one Product or Variant and is explicitly approved before normal canonical search use.
7. Pending is a first-class review state and is not equivalent to approved or published.
8. A rejected submission cannot reach publication without a subsequent valid corrected submission and review decision.
9. Publication snapshots are immutable; later edits cannot rewrite historical audit evidence.
10. Coverage means an association to a Variant, not availability, price, stock, cost or business policy.
11. TradeFlow can create and operate a business product without NCPC identity or NCPC uptime.
12. NCPC entities never store authoritative TradeFlow price, cost, stock, sales, supplier, profitability or configuration.
13. Business A cannot read/write Business B's non-public submissions, coverage or linked business reference through NCPC authorization.
14. Product/Variant lifecycle changes preserve references: retire/merge/deprecate rather than casually delete.
15. A merge records survivor/superseded identities and does not invalidate external historical references.
16. Category and Brand are NCPC references, not an instruction to overwrite local TradeFlow categories or names.
17. PackDefinition preserves known structured measurements and display text; unknown facts remain unknown.
18. Every material identity mutation is attributable to source/proposer, reviewer/actor, timestamp, old/new values and rationale.
19. A publication-ready consumer result must be both approved/published by policy and active; draft/candidate data is excluded.
20. Location references in coverage are non-authoritative discovery projections, not a competing business registry or Zambia geography master.
