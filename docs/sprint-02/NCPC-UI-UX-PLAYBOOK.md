# NCPC UI/UX Playbook

Version: 1.0 — usability refactor baseline (2026-09-12)

## Product principle

**The backend may speak NCPC. The user interface must speak ordinary language.**

NCPC can keep precise domain terms, identifiers, review states, publication snapshots, source references and API contracts internally. A normal catalogue operator should only see the concepts required to complete the task safely.

The interface is for catalogue staff, reviewers and administrators who may have little or no technical training. It must not require knowledge of PRD/VAR IDs, API clients, runtime architecture, JSON payloads or database terminology.

## Preserve the existing visual identity

The service-aligned NCPC UI remains the design baseline:

- deep NDS navy navigation shell;
- cyan active-navigation indicator;
- signal violet primary actions;
- white/light operational workspace;
- Manrope for UI text;
- Barlow Condensed for the NCPC brand mark;
- green for trusted/success states;
- gold for attention/review states;
- red reserved for errors or destructive outcomes.

This refactor changes language and information hierarchy. It is not a visual redesign.

## Help language system

NCPC uses three separate guidance signals. They must never be interchangeable.

### `?` — What does this mean?

Use for a local concept that may be unfamiliar.

Examples:

- Barcode `?`
- Size / Product Option `?`
- Other names `?`
- Sources & Proof `?`

Rules:

- neutral tone;
- 1–3 short sentences;
- explain the concept, not the backend implementation;
- clickable/tappable and keyboard reachable;
- must have an accessible label;
- never means error.

### `!` — Pay attention before continuing

Use when the user must understand a consequence, conflict or risk before acting.

Examples:

- Publish Catalogue `!`
- Possible duplicate/barcode conflict `!`
- destructive/reject action warnings where needed.

Rules:

- use sparingly;
- explain the consequence and the safe next action;
- gold/attention styling by default;
- red is reserved for actual errors or destructive failure states.

### `Help` — How do I use this page?

Use at page level. It should explain:

- what this page is for;
- what the user can do here;
- the normal next step.

Page Help must not expose API, token or database details unless the user opens Technical details separately.

## Technical details

Engineering and audit data remain available through progressive disclosure:

`Technical details ▾`

Examples that belong here:

- Product/PRD IDs;
- Variant/VAR IDs;
- release/update version;
- source business/system IDs;
- source product references;
- API configuration;
- raw service responses;
- local integration environment variables.

Technical details are collapsed by default.

## Plain-language terminology

| Backend / previous UI term | User-facing term |
| --- | --- |
| Dashboard | Overview |
| Products & Resolver | Products |
| Product family | Product |
| Variant | Size / Product Option |
| PRD / VAR | Product ID / Product Option ID under Technical details |
| Human Review Queue | Needs Review |
| Reviews | Needs Review |
| Submissions | Suggested Changes |
| Duplicate Cases | Possible Duplicates |
| Publication | Publish Catalogue |
| Release | Catalogue Update |
| Publication rationale | Reason for publishing this update |
| Catalogue Coverage | Catalogue Progress |
| Integrations / API Clients | Connections |
| Evidence | Sources & Proof |
| Alias | Other name |
| Primary barcode | Barcode |
| Reviewer comment | Reason for your decision / Review note |
| APPROVE_NEW | Approve |
| NEEDS_MORE_INFORMATION | Ask for more information |
| REJECT | Reject |
| Candidate identity search | Product name or other name |
| Match reason | Why it matched |

Backend values and API payloads are not renamed internally.

## Navigation

### Overview
- Overview

### Catalogue
- Products
- Add Product

### Check & Approve
- Needs Review
- Suggested Changes
- Possible Duplicates
- Publish Catalogue

### Progress
- Catalogue Progress
- Connections

## Page rules

### Overview

Primary question: **What needs my attention?**

Show:

- product count if truthfully available;
- items needing review;
- published catalogue-update count;
- system status;
- a simple next-step workflow.

Do not explain NCPC architecture on the main screen.

### Products

Primary task: find a trusted product.

Search should accept ordinary names, other known names and barcodes. Technical ID search may remain supported by the backend without being promoted in the UI.

List columns:

- Product;
- Size / Product Option;
- Why it matched;
- Open action.

Product IDs do not belong in the default result table.

### Product Details

Primary hierarchy:

1. product name;
2. brand/category;
3. sizes/product options;
4. pack;
5. barcode;
6. other names;
7. suggest a change;
8. Sources & Proof;
9. Technical details.

If a read endpoint does not expose source evidence, say so truthfully. Never invent proof.

### Add Product

Normal visible fields:

- Product name;
- Brand;
- Category;
- Size / Product Option;
- Barcode;
- Other names.

Source system IDs and source references are advanced metadata and belong under Technical details. Manual UI entries may use generated internal source references rather than forcing a non-technical operator to understand them.

Saving a product sends it for review; it does not publish immediately.

### Needs Review

Primary questions:

- What product is this?
- Why does it need review?
- What information is being proposed?
- What proof supports it?
- What decision should I make?

Decision labels:

- Approve;
- Ask for more information;
- Reject.

A reason for the decision remains required by the backend where applicable.

Review IDs, product IDs and option IDs belong under Technical details.

### Possible Duplicates

A match is evidence to compare records, not permission to merge.

The UI must explicitly warn that similar names and barcodes can still refer to different products or packs.

### Publish Catalogue

The main message must explain the consequence in normal language:

> Publishing makes approved product information available to systems that use NCPC.

Also state clearly that prices, stock, sales, availability and other shop facts are not published by NCPC.

Release/version fields are Technical details.

### Catalogue Progress

Show only truthful data exposed by the current APIs/data. Unknown coverage must remain unknown rather than being fabricated.

### Connections

Normal view shows system names and simple status such as Connected / Needs attention.

Tokens, URLs, environment variables and synthetic proof commands belong under Technical connection details.

## Local development authentication

The local administrator token is a development concern, not a normal catalogue concept.

It lives under collapsed **Local setup** in the sidebar.

Normal copy should say **Administrator access**, not “bearer token”, “API token” or equivalent engineering language.

Production authentication is a separate product decision and is not designed by this local UI refactor.

## Status language

Prefer:

- Needs review
- Approved
- Draft
- Published
- Previous
- Rejected
- Conflict
- Connected
- Needs attention

Avoid exposing raw enum values when a plain-language label exists.

## Accessibility

- every button and input must be keyboard reachable;
- custom help controls need accessible labels;
- `:focus-visible` must be visibly distinct;
- Help dialog must support keyboard focus and Escape/Close behavior;
- color cannot be the only indicator of state;
- tap targets for `?` and `!` controls must remain usable on mobile;
- page Help must remain reachable at small widths;
- technical disclosure uses semantic `<details>/<summary>` where practical.

## Responsive behavior

Desktop keeps the existing sidebar shell.

On narrow/mobile layouts:

- navigation becomes a horizontal scroll rail using the existing pattern;
- tables that cannot collapse safely may scroll horizontally;
- review tables use stacked rows where already supported;
- Help dialog fits inside the viewport;
- product option metadata collapses to one column.

## Data-boundary rule

NCPC UI may display shared identity/catalogue information. It must not begin storing or presenting TradeFlow-owned shop facts as NCPC truth, including:

- selling price;
- cost price;
- stock;
- sales;
- expenses;
- availability;
- supplier settings;
- business policies.

## Refactor decision log

### 2026-09-12 — Usability refactor

Decision: preserve the existing NCPC visual system and backend/API contracts, but simplify user-facing language and hierarchy.

Reason: the existing UI is visually coherent and operational; the main usability barrier is technical terminology and engineering-first presentation.

Implemented:

- Dashboard → Overview;
- Products & Resolver → Products;
- Human Review Queue → Needs Review;
- Submissions → Suggested Changes;
- Duplicate Cases → Possible Duplicates;
- Publication → Publish Catalogue;
- Catalogue Coverage → Catalogue Progress;
- Integrations / API Clients → Connections;
- page-level Help;
- contextual `?` definitions;
- contextual `!` attention warnings;
- Technical details progressive disclosure;
- collapsed Local setup;
- plain-language product/search/review/publication rendering;
- explicit focus-visible treatment.

Backend mapping and review/publication safety rules remain unchanged.

## Definition of Done for future NCPC UI changes

A UI change is complete only when:

- backend/API authority is preserved;
- user-facing language has been reviewed for non-technical users;
- `?`, `!`, and Help follow this playbook;
- technical fields are hidden unless necessary;
- empty/loading/error states are understandable;
- keyboard focus is visible;
- desktop and mobile layouts are checked;
- automated tests pass or unrelated baseline failures are documented;
- the rendered UI is inspected;
- this playbook is updated when the change affects language, flow, components or guidance.
