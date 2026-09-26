# NCPC Official-Source Catalogue Expansion — 2026-09-12

Status: `LOCAL_DEVELOPMENT_PUBLICATION_PROVED / OWNER-AUTHORIZED INITIAL CATALOGUE EXPANSION / LIVE RELEASE NOT AUTHORIZED`

## Goal

Expand the already-published Sechelanji-backed NCPC catalogue using authoritative Zambia-relevant online evidence without making barcode availability a publication requirement. Product-family evidence is not stretched into an exact pack claim: exact VARs are published only where the bounded official source establishes the pack; broad corporate/brand pages create product-only publication records or review holds.

## Inputs actually used

- Baseline local development catalogue: `REL-000003` / `NCPC-20260910-163213-000003`.
- Existing published Sechelanji seed and its evidence/audit lineage.
- Connected Drive resource `NCPC_Phase41_FULL_Catalogue_Import.json` (1,221 bundles / 604 sources) as the normalized research corpus.
- Current official web revalidation on 2026-09-12 for the source domains below.
- The existing NCPC `InitialSeedService`, publication snapshots, evidence ledger, review/audit model and candidate search.

Validated official-source domains used by the bounded expansion:

- `nmc.co.zm`
- `www.coca-cola.com`
- `www.tradekings.co.zm`
- `www.varunbeverages.com`
- `www.vaseline.com`
- `www.willowtongroup.com`
- `zambeefplc.com`
- `zamsugar.co.zm`

Fresh source examples revalidated in this pass include Coca-Cola Beverages Zambia's 2026 promotion terms, National Milling's current products/prices pages, current Trade Kings product pages, Vaseline South Africa product pages, Zambia Sugar product pages, Willowton product pages, Varun Beverages' product portfolio and Zambeef's current brands page.

## Publication rules applied

1. `official_exact` + reviewed identity + Zambia market relevance is required for this pass.
2. Exact VAR publication additionally requires a bounded official source that directly supports the pack/variant.
3. Missing barcode does **not** block publication.
4. Research barcodes are not promoted by this pass (`barcodes_imported = 0`).
5. Broad official portfolio pages can publish a product family only; they cannot invent pack size.
6. Existing exact variants may be enriched only through an explicit `match_existing_variant_id` when the pack measure is uniquely reconcilable.
7. Ambiguous pack-like family names, conflicting brand identity, uncertain variants and unsupported pack claims are held for normal manual review.
8. No TradeFlow price, cost, stock, availability, supplier, local SKU or business coverage is created.

## Manifest result before application

| Measure | Count |
|---|---:|
| Phase41 bundles scanned | 1221 |
| Qualifying reviewed official-exact products | 143 |
| Products with at least one exact publishable VAR | 118 |
| Exact VAR candidates | 538 |
| Existing VARs explicitly matched for evidence enrichment | 4 |
| New VAR candidates | 534 |
| Product-only family candidates | 19 |
| Review holds | 52 |
| Official evidence sources persisted | 96 |
| Research barcodes imported | 0 |

Manifest hash: `bfc6991a3b2940ce39ec98d626422fe94e20fc39e2a524b0412991a5c6e1d87a`

The four development-copy `match_existing_variant_id` values were reconciled
against exact active canonical-local product/variant matches before canonical
application. The source fingerprint, evidence, candidates, holds and decision
were unchanged; only the target-local IDs and manifest hash changed.

## Applied local-development result

The manifest was applied to a copy of the existing `REL-000003` local development database through the same hash-checked `InitialSeedService.apply()` transaction. It produced `REL-000004`.

| Measure | Before | After | Net |
|---|---:|---:|---:|
| Products | 164 | 294 | +130 |
| Variants | 160 | 694 | +534 |
| Public identities | 168 | 721 | +553 |
| Public exact variants | 160 | 694 | +534 |
| Public product-only families | 8 | 27 | +19 |
| Published barcode-less variants | 1 | 535 | +534 |
| Evidence sources | 3 | 99 | +96 |
| Catalogue evidence claims | 658 | 3962 | +3304 |
| Business coverage rows | 0 | 0 | +0 |

Current local release: `REL-000004` / `NCPC-20260912-025025-000004`.

### High-value verified examples now public

- Coca-Cola Original Taste — 300 ml returnable glass bottle and 500 ml PET bottle. The 1 L research variant was deliberately **held** because the bounded Coca-Cola Zambia source used in this pass did not directly establish 1 L.
- Coca-Cola Zero Sugar — 500 ml PET bottle.
- Sprite — 300 ml returnable glass bottle and 500 ml PET bottle.
- Aquasavana Water — 500 ml PET bottle.
- Minute Maid Mango Juice Drink — 500 ml PET bottle.
- Minute Maid Tropical Juice Drink — 500 ml PET bottle.
- Zambia's Pride Natbake — 50 kg and 10 kg bags, plus the broader current National Milling product/pack range supported by the official product catalogue.
- Whitespoon Household Sugar / Brown Sugar / Refined White Sugar — official Zambia Sugar pack families where exact page evidence exists.
- Vaseline Blue Seal Original, Aloe Fresh, Baby Soft, Cocoa Butter and Vitamin E petroleum-jelly variants supported by current brand-owner pages.
- Boom Force Scouring Cleanser, Boom Bubble Plus, Boom Auto and many other exact Trade Kings product-page variants.
- Willowton product families/variants where exact current product pages support pack claims, including Sona Beauty Soap and Allsome rice.

### Product-only families intentionally published

These are useful searchable NCPC products whose broad official evidence establishes the family but whose exact pack was not proven strongly enough in this bounded pass:

- BigTree Castor Sugar
- BigTree Icing Sugar
- BigTree Original Corn Flakes
- Binto Instant Noodles
- Twin Cows Full Cream Milk
- Amazon Fizz Wizz Pops
- Amazon Monsta Pops
- Amazon Pops
- Bang Bang Ball Gums
- Bullet Detergent Paste
- 7UP Lemon-Lime Soft Drink
- Mirinda Orange
- Mountain Dew Citrus Soft Drink
- Master Pork Smoked Back Bacon
- Zamchick IQF Mixed Chicken Portions
- Zammilk Butter
- Zammilk Fresh Milk
- Zammilk Mabisi Lacto Fermented Milk
- Zammilk Smooth Yoghurt

## Safety / boundary proof

The current publication contains `721` public identities: `694` VAR entries and `27` product-only entries. `535` published variants have no barcode claim and still resolve through candidate search. BusinessCoverage remains `0`. Public payload scans found no TradeFlow operational fields in the release.

## Tests

Focused expansion + publication tests pass:

```text
PYTHONPATH=src python -m pytest -q tests/test_official_source_expansion.py tests/test_publication_and_merge.py
.......... [100%]
```

The complete repository suite still has one **pre-existing** failure in `tests/test_api.py::test_review_detail_exposes_identity_attributes_only` where a TradeFlow submission review detail returns `brand = null`. The exact same test fails in the untouched uploaded `apps(1).zip`, proving this regression was not introduced by the official-source expansion.

## Files added/changed

- `research/NCPC_Phase41_FULL_Catalogue_Import.json` (materialized Drive snapshot used by this pass)
- `service/scripts/build_official_source_expansion_manifest.py`
- `seeds/official-source-expansion-v1.json`
- `service/src/ncpc_service/initial_seed.py` (backward-compatible expansion rationale, explicit existing-VAR matching, brand enrichment/conflict guard)
- `service/tests/test_official_source_expansion.py`
- `docs/sprint-02/NCPC-OFFICIAL-SOURCE-EXPANSION-SOURCE-LEDGER-2026-09-12.csv`
- this report
- `service/ncpc-dev.db` now represents the expanded local development `REL-000004` snapshot.

## Canonical-local publication (2026-09-12)

Owner authorization applied the reconciled, hash-checked manifest to the
canonical local NCPC PostgreSQL database. `SEED-000002` created immutable
`REL-000002` (`NCPC-20260912-214531-000002`). The release contains 706 public
identities: 698 exact variants and the eight previously published product-only
families. The 538 exact-candidate seed items were applied; the 19 new
product-only candidates were held because their canonical products already
have variants, and all existing normal holds were retained.

Canonical post-application invariants: 1,363 products, 2,180 variants, 99
evidence sources, 3,886 evidence claims, zero BusinessCoverage rows, and 1,333
open review cases. The four reconciled variants are active and approved. NCPC
was restarted after application; `REL-000002` persisted and `/health` returned
HTTP 200.

The verifier now accepts both the historic seed hash shape and the current
rationale-bound shape used by the expansion builder; a tampered rationale is
rejected. Explicit existing-variant matching now promotes only an exact,
active draft match and never re-parents it. Focused seed/publication tests:
`11 passed`.

This is canonical-local publication evidence only. It does not publish to a
remote endpoint, Google Sheet, Google Drive, Apps Script, TradeFlow, or any
production environment.

## Deployment boundary

This is **not** a live/remote NCPC deployment. No production database, Google Sheet, Drive file, Apps Script deployment or live endpoint was mutated. The local worktree/database is ready for a separate explicit target reconciliation and deployment gate.
