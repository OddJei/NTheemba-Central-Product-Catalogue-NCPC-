# Ntheemba Central Catalogue: Zambia Retail & Grocery Batch 001

## Scope and outcome

This batch processes the Retail & Grocery seed products in the Central
Catalogue Apps Script demo: Coca-Cola Original, Fanta Orange, and Tomatoes.
It then expands the confirmed Coca-Cola Beverages Zambia portfolio with
Coca-Cola No Sugar and Sprite. Salon & Beauty's Braiding Hair remains outside
this batch and is recorded as unresolved rather than mixed into the retail
master.

## Progress

| Measure | Count |
| --- | ---: |
| Seed products reviewed | 3 |
| Completed Retail & Grocery products | 10 |
| New products discovered | 7 |
| Manufacturers | 3 |
| Brands | 7 |
| Variants | 21 |
| Verified manufacturer barcodes | 0 |
| Products requiring package-barcode follow-up | 4 |
| Bulk product without a manufacturer barcode | 1 |
| Media URLs retained | 0 |
| Unresolved leads | 4 |

## Data-quality decisions

- The official Coca-Cola Zambia promotion confirms 500 ml Coca-Cola,
  Coca-Cola No Sugar, Fanta, and Sprite, and names Coca-Cola Beverages Zambia.
- ZPPA's Q4 2025 market index independently confirms disposable 500 ml
  Coke/Sprite/Fanta availability in Zambia.
- `5449000000996` was deliberately rejected for the Zambia 500 ml Coke
  variant: external barcode references identify it as a 330 ml can for the
  Belgium/Luxembourg market.
- No numeric barcode was invented. Every current variant has a `not_found`
  barcode record; the Apps Script importer creates an Ntheemba CODE128 only
  when the blank generated-barcode record is imported.
- No image URL was retained because this batch did not find a clean,
  exact-package source image. Retailer pages are cited as product evidence but
  are not misrepresented as permanent media assets.
- Trade Kings' official Boom product page confirms eight pouch and box variants
  for Boom Detergent Paste, adding a Zambia-based manufacturer expansion.
- The same official page identifies Boom Bubble Plus Washing Powder Original in
  a 1 kg jar, which is now a separate product rather than incorrectly merging
  it into detergent paste.

## Main sources

- [Coca-Cola Zambia 500 ml promotion](https://www.coca-cola.com/xe/en/legal/terms-and-conditions-zambia-scan-enjoy)
- [ZPPA Q4 2025 Market Price Index](https://www.zppa.org.zm/documents/20182/258675/Q4%2B2025%2BMPI.pdf/0f1f94cf-5d92-47db-9e17-b0b2c0c061b2)
- [Zambia Statistics Agency tomato kilogram reference](https://www.zamstats.gov.zm/national-average-prices-for-selected-products-september-2024/)
- [Fanta Orange 500 ml retailer listing for Zambia](https://www.ubuy.com.zm/product/D37O0FAG-fanta-orange-500ml)
- [Trade Kings Boom Detergent Paste](https://www.tradekings.co.zm/product/product-main-template/)

## Import and next batch

Validate the master with `npm run validate`, then call
`importResearchCatalogueJson(masterJsonText)` in the Central Catalogue Apps
Script project. The import creates drafts, not active catalog records.

The next batch should scan physical Zambia packages or obtain an official local
catalogue from the producer/distributor, then resolve the identified Dairy Gold
and Big Tree portfolios, followed by Mirinda, Pepsi, and 7UP one manufacturer
at a time.
