# NCPC source reconciliation - initial trusted catalogue

Status: `INSPECTED / RECONCILIATION_INPUT_ONLY / NO_UNVERIFIED_PROMOTION`

## Purpose

This ledger records every available local Sechelanji/NCPC source inspected for
the initial seed. It keeps source authority separate from the decision to
publish a particular identity. No TradeFlow operational field is imported.

| Source | Fingerprint | What it establishes | Disposition |
| --- | --- | --- | --- |
| `Sechelanji_NCPC_Publication_Ready_Catalogue.xlsx` | manifest `b1d280b814a326506e55307c58341d321e54827b8d3444a31f27607bbd0bb749` | current, structured physical identity decisions | published only under Class A/Class B rules; Class C held |
| `Sechelanji_Trading_TradeFlow_Catalogue_Review_Updated.pdf` | `F6FC175D...F31688437` | 226 owner-review lines and physical-review context | identity corroboration only; units/cost/selling price excluded |
| `Sechelanji_Trading_TradeFlow_Catalogue_Review_Final.pdf` | `402B27A6...6DFFBFDA5A` | 227 corrected owner-review lines and explicit unresolved labels | identity corroboration only; unresolved pack/brand/unit stays held |
| `NCPC_Phase41_Product_Catalogue.pdf` | `F565DF3F...065F02D304` | 1,221 product / 2,214 variant historical draft catalogue | reconciliation only; `pack size pending` families are not promoted |
| `Canonical Product Catalogue Research and Expansion Report.pdf` | `06DD766F...0ECFD2A247` | historical expansion research | research only; no direct promotion without current authoritative evidence |
| `zambia-source-ledger.json` | `CF8EBA36...EB8D7A827` | 11 source references, including official/gov/retailer evidence tiers | source discovery and corroboration; authority tier applied per claim |
| `zambia-research-import.json` | `B09FDA5D...020316B710` | five draft research bundles | reconciliation only; explicit no-GTIN/pack warnings retained |
| `ntheemba-central-catalogue-retail-zambia.json` | `9A706711...4AF29A82F5` | ten draft retail bundles, seven brands, three manufacturers | reconciliation only; no draft automatically published |

### Additional Downloads inventory

The following discovered sources were also fingerprinted and classified. They
are earlier/operational review material, import tooling, or duplicate copies;
none is a new authoritative identity source for this seed.

| Source | Fingerprint | Disposition |
| --- | --- | --- |
| `Sechelanji_Trading_Stock_List_Review_NDS.pdf` | `819FCA22...4CAC0E4CF` | physical-review corroboration only; operational columns excluded |
| `Sechelanji_Trading_Stock_List_Review_Text_Only_NDS.pdf` | `944C9133...9FD63F246` | text extraction counterpart; corroboration only |
| `Sechelanji_Trading_Stock_and_Pricing_Review_NDS.pdf` | `6D4BBD8B...864A1EC6AD` | operational review; no price/stock/cost import |
| `Sechelanji_Trading_Stock_and_Pricing_Review_NDS_Beverages_Expanded.pdf` | `39FF789F...E5EE9B8C8` | expanded review; exact identities already reconciled or held |
| `Sechelanji_Trading_TradeFlow_Catalogue_Review.pdf` and `(1)` | `5A49F102...658E20522` | identical prior review copies; no additional import |
| `NCPC_v2.8_TradeFlow_Reviewed_Submissions.zip` | `16704B49...1A891C8D` | historical submission tooling; not a publication authority |
| `NCPC_Code_v2.5/2.7` and `NCPC_INSTALL.md` | inventoried locally | historical implementation reference; no identity promotion |
| `stock_extraction_with_barcode_research.xlsx` | `03A658DF...C1181646` | 62 photo-derived stock rows, 34 barcode candidates, 28 unresolved; contains price/stock fields and explicitly requires a physical scan before import | operational/research input only; no row, barcode, price, stock, or source URL is promoted by this seed |
| `NTheemba_NCPC_Sprint_02.2-02.8.zip` | `3F67A8CE...CBE1E710` | archived NCPC source-tree snapshot | inventory only; archive was listed but not executed or imported, and current checked-out source is authoritative |

## Result

All currently available local Sechelanji/NCPC artefacts named in this ledger
were inventoried and given an explicit non-promotion or seed disposition. The
trusted seed remains bounded to 164 products: 160 exact variants, eight
product-only families, and 40 Class-C source holds plus the `P057` barcode
reconciliation. The source review discovered no basis to infer a barcode,
promote a Phase41 pack-pending family, or copy price, cost, stock, supplier,
or local SKU data into NCPC. No connected Google Drive resource was available
in this run, so no Drive artifact is asserted as inspected or reconciled.

The official Trade Kings source is the one current online source promoted into
this seed. It supports the persisted `Boom` brand to `Trade Kings Group`
`MANUFACTURER` relationship and the barcode-less Boom 20 g pouch identity.

## Follow-up rule

The remaining research bundles are a controlled candidate queue. A row may
enter a later manifest only after its exact PRD/VAR (or explicit product-only
family), Zambia relevance, claim-level source, and conflict result are recorded.
