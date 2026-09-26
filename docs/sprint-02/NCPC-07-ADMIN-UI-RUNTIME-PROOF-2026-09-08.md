# NCPC-07 same-origin admin UI runtime proof

Status: `ACCEPTED_FOR_NEXT_GATE`.

The local `/admin` surface contains Dashboard, Review Queue, Review Workspace,
Catalogue Search, Product Detail, Variant Detail, Barcode Claims / Conflict
Review, Duplicate / Merge Review, Publications / Release History,
BusinessCoverage, and Audit. Browser automation in a disposable local Chrome
profile completed synthetic submission, review, approval, PRD/VAR retrieval,
publication, product/search retrieval, and variant verification; it emitted
`NCPC_SERVICE_ALIGNED_ADMIN_UI_RUNTIME_READY PRD-000004 VAR-000004`.

Desktop and mobile captures are under `apps/output/playwright/`. The browser is
a service client only: authorization and all identity/review/merge/publication
rules remain server-side. Local development authentication is explicitly not
federated production identity. Independent UI and Test reviews accepted this
local synthetic evidence.
