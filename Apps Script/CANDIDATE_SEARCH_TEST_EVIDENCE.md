# Candidate Search Contract v1 — Local Evidence

Date: 2026-08-22

## Passed local checks

| Check | Command | Result |
| --- | --- | --- |
| Candidate contract scenarios | `node --preserve-symlinks-main scripts/test-candidate-search-contract.mjs` | Passed: barcode, alias/typo, size warning, draft/unpublished exclusion, no-match, direct and route-level safe errors, invalid limit, schema/version, private-field exclusion, forced public filters, diversity. |
| Apps Script syntax | `Get-Content -Raw 'Apps Script\\Code.gs' \| node --check` | Passed (exit 0). |
| Existing catalogue seed validation | `node scripts/validate-catalog.mjs` | Passed: 2 documents. |

The candidate test evaluates the actual `Code.gs` candidate-search functions in
an isolated in-memory fixture. It proves the public response behavior without
creating, importing, publishing, or changing any spreadsheet record.

## Deployment-only verification not performed

- No Apps Script deployment or web-app publication was performed.
- No production/test spreadsheet was initialized, read, changed, or exported.
- The deployed web-app routes still need a non-production deployment test for
  HTTP JSON serialization, parameter handling, permissions, and the actual
  published-data fixture.
- A real published product and published active variant must be verified in the
  target NCPC database before downstream consumers rely on the route.
