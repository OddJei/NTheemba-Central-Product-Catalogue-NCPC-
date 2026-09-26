# NCPC Apps Script Workspace Audit

Date: 2026-08-14

## Scope

Workspace Apps Script edition under `Central Catalogue/Apps Script/`.

## Result

- Replaced the older Apps Script prototype with the user's NCPC v2 standalone Apps Script edition.
- `Code.gs` now uses `NCPC_APP`, version `2.0.0`, and schema `ncpc-2.0`.
- `Index.html` now matches the NCPC v2 standalone admin UI.
- NCPC v2 includes job-based resumable imports through `ImportJobs` and `ImportItems`.
- NCPC v2 includes evidence, review queues, barcode verification, releases, and published-catalogue export.
- Added an explicit protected TradeFlow field guard before research bundles are queued or processed.

## Verification

- Attached `Code.gs` parsed before replacement.
- Attached `Index.html` inline JavaScript parsed before replacement.
- Workspace `Code.gs` parsed after replacement.
- Workspace `Index.html` inline JavaScript parsed after replacement.
- Direct local guard probe confirmed protected TradeFlow fields such as `selling_price` are blocked.

## Remaining Gates

- No Apps Script deployment was performed.
- No live spreadsheet was initialized or modified.
- `INTEGRATION.md` still needs a v2 rewrite because it was written around the older Apps Script prototype.
