# Compatibility contract

## Must preserve

- Stable existing `PRD-*` and `VAR-*` identities and the Product-to-Variant
  relationship. Never remint an ID because a name changes or a merge occurs.
- Identity-only public candidate results: IDs, names, brand, pack/size,
  identifiers, aliases, matching metadata and catalogue version are safe;
  price, cost, stock, availability, supplier, batches, sales and financial data
  are not NCPC output.
- Published-and-active filtering for normal consumer search; drafts/candidates
  must not leak into customer-facing results.
- Candidate read API aliases: `action` or `api`, `candidates`/`search`, exact
  `barcode`, bounded `limit`, no-match as a successful empty result, and safe
  operational errors for candidate search.
- Standard TradeFlow local identity is `(shop_id, business_product_id)`;
  `ncpcMapping` is optional and a local product must work without NCPC.
- TradeFlow mapping carries at least product ID, variant ID, catalogue/release
  version and linking audit metadata; it may not overwrite business facts.

## May migrate through an adapter

- `ncpc-candidate-search-v1` envelope and field casing can be served by a future
  adapter while preserving its documented semantics and public allowlist.
- `LocalApprovedReleaseNcpcClient` can be replaced by a future NCPC client only
  after a contract exists for its seven methods, authenticated caller identity,
  idempotency, safe failures and versioning.
- Legacy `IDN-*` identifiers and older JSON `BAR-*` barcode records can map to
  one Barcode domain entity while legacy references remain resolvable.
- Existing release export payloads may be transformed to immutable publication
  snapshots; consumers must retain the version/snapshot they used.

## Should deprecate

- The local `server.mjs` API and JSON `catalog-v1` as production contracts.
- Fake/local TradeFlow submission/correction IDs as proof of NCPC acceptance.
- Any use of a loaded release cache as NCPC's source of truth.
- Raw `ProductCandidates.rawPayload` as the long-term proposal model.

## Internal-only legacy behavior

Apps Script admin RPCs, IndexedDB cache, Sheet table names, sequence counters,
research import job mechanics and `ReleaseItems` storage are implementation
details. They are not downstream API commitments.

## Authentication expectations

Read routes currently have no documented client authentication. The sole write
route checks a shared script property token and accepts a caller-provided
business ID. A future service must replace that with authenticated principal,
authorization and tenant-scoped submission authority; no caller may edit another
business's coverage or submission.
