# NTheemba Central Product Catalogue (NCPC) Apps Script Integration Guide

This guide describes the current NCPC v2 Apps Script edition in this folder.
It is a standalone catalogue administration app backed by Google Sheets. It is
not currently a REST API service for TradeFlow or NTheemba.

NCPC owns approved shared product identity and catalogue facts. It never owns a
business's stock, cost, selling price, supplier, batches, sales, revenue, margin,
or profit.

## Current App Shape

The current Apps Script project contains:

- `Code.gs`: NCPC v2 backend functions, schema creation, import jobs, review
  flows, release creation, and catalogue export.
- `Index.html`: standalone NCPC admin UI using `google.script.run`.
- Google Sheets database tables created by `initializeNcpcSystem()`.
- Script properties such as `NCPC_DATABASE_SPREADSHEET_ID`,
  `NCPC_INITIALIZED_SCHEMA_VERSION`, and `NCPC_CATALOGUE_VERSION`.

The live script shown during the workspace audit is initialized with schema
`ncpc-2.0` and already has a database spreadsheet ID. Treat that database as
stateful. Do not reset, reinitialize destructively, import into it, or deploy a
new script version without explicit approval for the intended environment.

## Trust Boundary

NCPC is the authority for:

- product families
- product variants
- identifiers and barcodes
- categories and catalogue domains
- brands and organizations
- public/shared descriptions
- evidence and sources
- admin-uploaded or admin-linked digital assets
- reviewed publication status
- release/export snapshots

TradeFlow is the authority for:

- business-owned inventory
- stock quantity
- selling price
- purchase cost
- supplier and delivery history
- reorder thresholds
- batches and movements
- estimated profit, margin, revenue, and expense reporting
- business-specific product names and notes

NTheemba may use NCPC to understand product identity, but it must use TradeFlow
for tenant-specific availability, stock, price, and business policies.

## Current Integration Status

The v2 Apps Script code does not implement `doPost`, API keys, `?action=...`
routes, incremental `changes`, or bulk lookup endpoints. Earlier documents that
describe those endpoints are stale and must not be used as an implementation
contract.

The current supported downstream path is:

1. NCPC admin creates or imports catalogue records.
2. Imported records stay draft or candidate-gated.
3. Admin reviews, verifies, and publishes approved products/variants.
4. Admin creates a catalogue release.
5. Admin exports the catalogue JSON.
6. TradeFlow and NTheemba consume only approved release/export data.

This keeps integrations quota-friendly and avoids calling NCPC on every
TradeFlow screen load or WhatsApp message.

## NCPC v2 Admin Functions

The admin UI calls Apps Script functions directly through `google.script.run`.
The important current functions are:

| Area | Function |
| --- | --- |
| Initialization | `initializeNcpcSystem()` |
| Bootstrap | `getNcpcBootstrap()` |
| Search | `searchNcpcCatalogue(query, filters, page, pageSize)` |
| Product detail | `getNcpcProduct(productId)` |
| Product editing | `saveNcpcProductBundle(bundle)` |
| Publication | `publishNcpcProduct(productId, notes)` |
| Withdrawal | `withdrawNcpcProduct(productId, notes)` |
| Sources | `saveNcpcSource(data)` |
| Evidence | `addNcpcEvidence(data)` |
| Reviews | `getNcpcReviewQueue(filters)`, `resolveNcpcReview(reviewId, resolution, notes)` |
| Barcode verification | `submitBarcodeForVerification(data)`, `resolveBarcodeVerification(queueId, decision, notes)` |
| Imports | `createNcpcImportJob(...)`, `appendNcpcImportItems(...)`, `processNcpcImportBatch(...)` |
| Releases | `createNcpcRelease(releaseName, description)` |
| Export | `exportNcpcCatalogue(options)` |

These are admin/internal callable functions, not a public external API.

## Research Manifest Imports

NCPC v2 supports research manifests with schema:

```text
apps-script-research-import-v1
```

The current import workflow is job-based:

1. Open the NCPC Apps Script web app.
2. Go to Imports.
3. Select an NCPC research manifest JSON file.
4. The UI creates an import job with `createNcpcImportJob(...)`.
5. The UI queues bundles in chunks with `appendNcpcImportItems(...)`.
6. The UI processes queued items in batches with `processNcpcImportBatch(...)`.
7. Failed items can be retried and incomplete jobs can be resumed.

Do not use the old `previewResearchCatalogueJson(...)` or
`importResearchCatalogueJson(...)` functions for NCPC v2 planning. They are not
the current Apps Script integration surface.

## Import Safety Rules

Research imports must remain review-gated:

- official exact records can create draft products and draft variants
- institution-linked records can create draft products and draft variants
- market pack-size hypotheses become `ProductCandidates` and `ReviewQueue`
  entries instead of published catalogue records
- imported products and variants must not be considered usable downstream until
  reviewed and published
- protected TradeFlow fields are rejected before queueing and again before
  processing

Protected fields include local price, stock, cost, supplier, batches, sales,
revenue, expenses, profit, margin, and inventory value.

## Large JSON Readiness

The 100, 570, and 3213 bundle research files are valid readiness fixtures for
NCPC v2 because they use `apps-script-research-import-v1`.

Use them in this order:

1. Validate locally with `scripts/validate-apps-script-research-import.mjs`.
2. Test the first 100 bundle file in a duplicate/test NCPC database.
3. Inspect `ImportJobs`, `ImportItems`, `Products`, `ProductVariants`,
   `ProductCandidates`, `ReviewQueue`, `Identifiers`, `InformationSources`, and
   `CatalogueEvidence`.
4. Confirm no protected TradeFlow fields are stored.
5. Confirm records remain draft/candidate-gated.
6. Only then test the 570 and 3213 bundle files.

Do not import the 3213 bundle file into a live/stateful NCPC database without a
backup/export, duplicate check, and explicit approval.

## Release And Export Contract

TradeFlow and NTheemba should integrate against releases, not drafts or import
jobs.

`createNcpcRelease(releaseName, description)` snapshots products and variants
whose `publicationStatus` is `published` and `status` is `active`.

`exportNcpcCatalogue({ publishedOnly: true })` returns the downstream catalogue
payload. The payload includes:

- `schemaVersion`
- `catalogueId`
- `catalogueVersion`
- `exportedAt`
- `publishedOnly`
- domains and categories
- organizations and organization roles
- brands and brand relationships
- products
- product variants
- identifiers
- aliases
- digital assets
- product-organization relationships
- information sources
- catalogue evidence
- releases

Downstream systems must store the release/catalogue version they consumed and
must not treat unreleased draft data as approved catalogue data.

## TradeFlow Sync Direction

TradeFlow should eventually add a product-tab action such as `Sync to NCPC`.
That action should link a local business product to an approved NCPC
product/variant/identifier. It should not turn the entire NCPC catalogue into
TradeFlow inventory.

Recommended TradeFlow local link fields:

```json
{
  "ncpcProductId": "PRD-000001",
  "ncpcVariantId": "VAR-000001",
  "ncpcIdentifierId": "IDN-000001",
  "ncpcCatalogueVersion": 470,
  "ncpcReleaseVersion": "NCPC-20260814-120000",
  "linkedAt": "2026-08-14T10:00:00.000Z"
}
```

TradeFlow may cache approved shared display facts such as the NCPC canonical
name, variant name, barcode, image URL, and category for usability. TradeFlow
must still keep and protect local business facts separately.

## NTheemba Search Direction

NTheemba should use NCPC for product identity and recognition:

1. Search the approved NCPC release/cache for likely product matches.
2. Resolve product, variant, barcode, alias, and image facts.
3. Ask TradeFlow whether the target business actually carries that mapped item.
4. Use TradeFlow's stock, price, and business policies when answering users.

This avoids repeated NCPC calls for every WhatsApp message. NTheemba can use a
cached NCPC release/search index and call TradeFlow for live tenant facts.

## Future API Work

A future NCPC external API may expose search, barcode lookup, release download,
candidate submission, and delta checks. That must be specified separately before
implementation.

Minimum requirements for that future API:

- server-side authentication
- per-client permissions
- request validation
- replay/idempotency protection for submissions
- rate limiting or quota controls
- audit events
- no exposure of draft/private records
- no acceptance of TradeFlow private inventory or financial fields
- tenant-safe caller identity
- documented error contract

Until that API exists, do not build TradeFlow or NTheemba against the stale
`?action=...&apiKey=...` contract.

## Operational Gates

Before live import, release, or downstream integration:

- confirm the target NCPC database is test, staging, or production
- back up/export the target spreadsheet
- validate the manifest locally
- test with a duplicate NCPC database first
- review duplicate and candidate behavior
- publish only reviewed products and variants
- create a release
- export published data
- record the release version consumed by TradeFlow/NTheemba
- complete independent security/reality review for production use

