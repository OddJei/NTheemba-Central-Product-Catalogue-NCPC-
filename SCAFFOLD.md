# Central Catalogue App

This app contains the controlled reusable catalogue system.

## Areas

- `Apps Script/`: Google Apps Script interface for catalogue workflows.
- `schema/`: versioned catalogue and business-link schemas.
- `seeds/`: curated starting records.
- `research/`: reviewed research/import material.
- `scripts/`: local validation and import simulation tools.
- `server.mjs`: local API/runtime entry point.
- `index.html`: local catalogue UI/prototype.

## Boundary

Canonical catalogue fields belong here. Business-specific price, stock, private description, and private business information belong to the business system and must not be silently overwritten.
