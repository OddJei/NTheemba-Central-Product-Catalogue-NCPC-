# NCPC UI Usability Refactor — 2026-09-12

## Goal

Refactor the existing service-aligned NCPC admin UI for non-technical catalogue users without replacing the working UI architecture or changing NCPC domain/API authority.

## Changed surface

Primary UI file:

`apps/central-catalogue/service/src/ncpc_service/admin.html`

Playbook:

`apps/central-catalogue/docs/sprint-02/NCPC-UI-UX-PLAYBOOK.md`

## Main changes

- preserved the navy/violet/cyan service-aligned visual system;
- simplified navigation and page names;
- added page-level Help controls;
- added contextual `?` concept help;
- added `!` consequence/attention help;
- added a reusable help dialog;
- added explicit keyboard focus styles;
- moved local administrator token controls under Local setup;
- exchanges local administrator access for the existing short-lived HttpOnly session, then clears the browser input before later admin requests;
- moved PRD/VAR/release/source IDs and raw responses under Technical details;
- simplified product search and product detail rendering;
- simplified Add Product and auto-generates local manual source references when advanced fields are blank;
- simplified review list/detail language and decisions;
- simplified duplicate checking;
- simplified publication language while preserving the publication API and confirmation gate;
- simplified Connections while keeping environment/API details available under Technical connection details.

## Not changed

- NCPC PostgreSQL/domain model;
- review decision semantics;
- publication eligibility rules;
- product/variant identifiers;
- catalogue search API;
- submission/correction APIs;
- authentication scopes;
- data-boundary rules;
- TradeFlow/Ntheemba backend contracts.

## Safety

No automatic review approval, duplicate merge, publication bypass or fabricated catalogue evidence was added.

## Search contract correction (2026-09-12)

The Products UI now requests at most 50 results, matching the enforced
`/v1/catalogue/candidates` API limit. This restores product-name and barcode
searches that previously failed client-side with HTTP 422 because the UI asked
for 100 results. No catalogue data, publication state, or API rule changed.

## Known API limitation surfaced truthfully

The released product read endpoint currently exposes trusted released identity data but does not expose detailed evidence-source records. The Product Details UI therefore explains that Sources & Proof are reviewed before publication but are not yet exposed by that read endpoint. It does not fabricate source data.
