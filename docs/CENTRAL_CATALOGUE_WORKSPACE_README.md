# Ntheemba Central Catalogue

This directory is the versioned, shared product-knowledge foundation for
TradeFlow and Ntheemba. It contains catalog facts only; it does not own a
business's stock, cost, selling price, supplier, batches, movements, or profit.

## What is here

- `Apps Script/` contains the current NCPC v2 Google Apps Script catalogue
  administration app. It is the edition currently used for NCPC planning.
- `schema/catalog-v1.schema.json` defines the published catalog document.
- `schema/business-product-link-v1.schema.json` defines the small private link a
  TradeFlow product may keep after importing a catalog variant.
- `seeds/` contains the first deliberately small, reviewable catalog data for
  Retail & Grocery and Salon & Beauty.
- `scripts/validate-catalog.mjs` performs dependency-free structural,
  reference, ID, barcode, and duplicate validation.

## Validate the seed data

Run from this directory:

```powershell
node scripts/validate-catalog.mjs
```

To validate another catalog document, provide its path:

```powershell
node scripts/validate-catalog.mjs path\to\catalog.json
```

## Run the local API and Builder

This local API/builder is an older development prototype. It remains useful for
lightweight local experiments, but it is not the current NCPC Apps Script
edition and must not be treated as the production integration contract.

```powershell
npm start
```

Open `http://localhost:4173`. The development API serves the Builder and
provides `GET /api/catalogue`, `GET /api/search?q=...`, `POST /api/candidates`,
and `POST /api/variants/:variantId/review`. Its first change creates
`data/catalogue-v1.json`; this local file is intentionally ignored from source
control and is not a substitute for a production database, authentication, or
authorization layer.

Run the isolated API workflow test with `npm test`. It creates and removes its
own temporary local catalog data.

## NCPC Apps Script import workflow

The Apps Script catalogue has its own normalized data model. Use the master
research manifest in `research/ntheemba-central-catalogue-retail-zambia.json`,
not the older local-prototype schema, when preparing data for
`Central Catalogue/Apps Script/Code.gs`. The earlier
`research/zambia-research-import.json` is an initial working manifest retained
for traceability; do not import it after the master file.

Each product bundle records a source-ID list that must resolve in
`research/zambia-source-ledger.json`. Numeric manufacturer barcodes are added
only after package-level evidence; otherwise a blank Ntheemba-generated CODE128
entry asks Apps Script to create a stable internal barcode during import.

Run `npm run validate` before importing. Then review the manifest and use the
NCPC v2 Apps Script web app's Imports screen. The current Apps Script importer
creates an import job, queues manifest bundles, and processes them in resumable
batches. It creates shared catalogue records as drafts or candidates; it does
not set local business prices, stock, suppliers, or batches.

For larger NCC research manifests, validate and simulate before Apps Script
import:

```powershell
node scripts/validate-apps-script-research-import.mjs path\to\manifest.json
node scripts/simulate-apps-script-import.mjs path\to\manifest.json
```

Large manifests should be imported through the NCPC v2 job workflow:

1. `createNcpcImportJob(...)`
2. `appendNcpcImportItems(...)`
3. `processNcpcImportBatch(...)`

The Apps Script UI handles those calls from the Imports screen. Records remain
draft/review gated until NCPC admin approval.

## Integration boundary

TradeFlow and Ntheemba should consume approved NCPC releases/exports, not draft
imports or candidate records. Catalogue search and barcode lookup may suggest a
variant to the TradeFlow owner after approved catalogue data has been synced or
cached. After selection, TradeFlow copies only shared facts and saves a private
link of the form described by `business-product-link-v1.schema.json`. The owner
still provides local cost, selling price, opening stock, stock thresholds, and
supplier details. No catalog import changes stock, creates a sale, or deducts
inventory.

Ntheemba uses a catalog variant to understand a requested product. It must use
the business's existing public catalogue allowlist and live TradeFlow inventory
to determine whether that business offers the item, at what price, and in what
quantity.

See `Apps Script/INTEGRATION.md` for the current NCPC v2 integration plan.

## ID rules

The older local prototype uses prefixes such as `BT-`, `MFG-`, `BAR-`, and
`MED-`. The NCPC v2 Apps Script edition uses its own table prefixes such as
`DOM-`, `CAT-`, `ORG-`, `BRD-`, `PRD-`, `VAR-`, `IDN-`, `AST-`, `REV-`, `IMP-`,
and `REL-`. Do not translate IDs by display name after publication.

IDs are opaque, uppercase, stable identifiers. They must never be regenerated
from a display name after publication. Retire records with `status: "retired"`
and retain their IDs; use `replaced_by_id` where an approved replacement exists.

- `BT-...` business type
- `CAT-...` category
- `MFG-...` manufacturer
- `BRD-...` brand
- `PRD-...` product family
- `VAR-...` sellable product variant
- `BAR-...` barcode record
- `MED-...` media record

Human-readable names may change. References between systems use the IDs.

## Publishing workflow

1. Add or revise seed records with source and verification details.
2. Run the validator and resolve every error.
3. Review duplicates, barcode ownership, source rights, and media suitability.
4. Publish approved records to the future catalog service.
5. Never overwrite business-specific data during a later catalog refresh.
