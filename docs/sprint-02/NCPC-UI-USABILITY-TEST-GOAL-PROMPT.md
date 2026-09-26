GOAL — INDEPENDENTLY AUDIT THE NCPC NON-TECHNICAL UI REFACTOR

Do NOT redesign the UI and do NOT start by changing code.
Audit the implementation first and return PASS/FAIL findings.

The intended refactor preserves the existing NCPC backend and visual identity while making the admin UI usable by a non-technical catalogue operator.

SOURCE OF TRUTH

Inspect:
- apps/central-catalogue/service/src/ncpc_service/admin.html
- apps/central-catalogue/docs/sprint-02/NCPC-UI-UX-PLAYBOOK.md
- apps/central-catalogue/docs/sprint-02/NCPC-UI-USABILITY-REFACTOR-2026-09-12.md
- apps/central-catalogue/service/tests/test_admin_usability.py
- existing NCPC API/domain tests

DO NOT treat the Playbook as proof. Confirm the actual rendered UI.

==================================================
1. BACKEND REGRESSION GATE
==================================================

Run the NCPC test suite.

Compare any failure against the baseline if necessary.

Known baseline issue from the supplied pre-refactor apps(1).zip:
- tests/test_api.py::test_review_detail_exposes_identity_attributes_only
  expected brand "Identity Brand" but current backend returns None.

Do not attribute that failure to this UI refactor unless the refactor somehow changed backend behavior.

Confirm no review/publication/merge/domain rules were weakened.

==================================================
2. NAVIGATION LANGUAGE
==================================================

Verify the ordinary sidebar uses:
- Overview
- Products
- Add Product
- Needs Review
- Suggested Changes
- Possible Duplicates
- Publish Catalogue
- Catalogue Progress
- Connections

Confirm the ordinary navigation does NOT require understanding:
- Products & Resolver
- PRD / VAR
- Human Review Queue
- API Clients
- publication snapshots
- raw enum values

==================================================
3. HELP LANGUAGE SYSTEM
==================================================

Verify all three meanings from the Playbook are implemented distinctly:

? = What does this mean?
! = Pay attention before continuing
Help = How do I use this page?

Test with mouse and keyboard.

Required examples:
- Products page Help
- Barcode ?
- Size / Product Option ? or Sources & Proof ?
- Publish Catalogue !
- Possible Duplicates !

Confirm `!` is not used as the generic error symbol.

==================================================
4. TECHNICAL DETAILS / PROGRESSIVE DISCLOSURE
==================================================

Verify ordinary users do not see PRD/VAR/release/source identifiers as primary content.

Check that technical information is behind collapsed Technical details where appropriate:
- Product ID
- Product option ID
- catalogue update/release version
- source business/system ID
- source product reference
- connection environment variables
- raw service response

Confirm Local administrator access is under collapsed Local setup.

==================================================
5. PRODUCTS WORKFLOW
==================================================

Run:
Products -> search existing product -> open product detail.

Verify user-facing hierarchy:
- product
- size/product option
- brand/category
- pack
- barcode
- other names
- Suggest a Change
- Sources & Proof
- Technical details

Verify search result table does not foreground PRD/VAR IDs.

Verify text search and barcode search still call the existing catalogue API.

==================================================
6. ADD PRODUCT WORKFLOW
==================================================

Open Add Product.

Normal visible fields should be:
- Product name
- Brand
- Category
- Size / Product Option
- Barcode
- Other names

Technical source IDs should be under Technical details.

Submit a disposable/test product if the environment permits.

Confirm:
- it creates a submission/review workflow;
- it does NOT publish automatically;
- manual UI source references can be generated when advanced source fields are blank;
- no price, cost, stock, sales or availability fields were added.

==================================================
7. NEEDS REVIEW WORKFLOW
==================================================

Open Needs Review -> select a real test/review item.

Verify the normal view answers:
- What product is this?
- Why does it need review?
- What product information is proposed?
- What Sources & Proof are supplied?
- What decision can I make?

Decision labels must be:
- Approve
- Ask for more information
- Reject

Review/product/option IDs should be under Technical details.

Do not approve real production-like data just to test the screen. Use a disposable item or stop before final submit.

==================================================
8. POSSIBLE DUPLICATES
==================================================

Check by name and barcode.

Verify:
- result columns use plain language;
- technical IDs are secondary;
- the UI explicitly warns that a match is not permission to merge automatically.

==================================================
9. PUBLISH CATALOGUE
==================================================

Open Publish Catalogue.

Verify:
- ordinary copy explains the consequence of publishing;
- it states shop prices, stock, availability, sales and other business data are not published;
- `!` attention help explains the consequence;
- version/release mechanics are under Technical details;
- existing confirmation gate remains in place;
- do NOT actually publish unless using an isolated disposable environment.

==================================================
10. CONNECTIONS
==================================================

Verify the normal screen presents simple system status.

Ntheemba/NCPC token names, URLs and local proof commands must be under Technical connection details, not normal operator content.

==================================================
11. ACCESSIBILITY & RESPONSIVE QA
==================================================

Check desktop and approximately 390 px mobile width.

Verify:
- visible keyboard focus;
- logical tab order;
- ? and ! controls are keyboard reachable;
- Help dialog can be closed;
- dialog fits mobile viewport;
- sidebar/mobile nav remains usable;
- no major clipping or horizontal content loss.

==================================================
12. SECURITY / DATA BOUNDARY
==================================================

Confirm:
- no API/admin token is embedded in browser source;
- existing server-side auth/scopes remain unchanged;
- no TradeFlow-owned price/cost/stock/sales/availability facts are added to NCPC UI as catalogue truth;
- no automatic review approval or duplicate merge was introduced.

==================================================
FINAL REPORT
==================================================

Return:

A. OVERALL VERDICT — PASS / FAIL
B. BACKEND TEST RESULTS
C. UI WORKFLOWS TESTED
D. HELP SYSTEM — ?, !, Help
E. TECHNICAL-DISCLOSURE RESULT
F. DESKTOP/MOBILE RESULT
G. ACCESSIBILITY RESULT
H. SECURITY/DATA-BOUNDARY RESULT
I. CONFIRMED DEFECTS
J. BASELINE/ENVIRONMENT ISSUES
K. RECOMMENDED NEXT UI FIXES (only if genuinely required)

Do not call missing evidence a confirmed product defect. Distinguish implementation defects from environment limitations and baseline backend failures.
