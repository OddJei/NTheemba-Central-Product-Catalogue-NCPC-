# NCPC UI Usability Refactor Validation — 2026-09-12

## Scope

Validated only the NCPC UI usability refactor. No backend/domain behavior was intentionally changed.

## Files changed

- `service/src/ncpc_service/admin.html`
- `service/tests/test_admin_usability.py` (new)
- `docs/sprint-02/NCPC-UI-UX-PLAYBOOK.md` (new)
- `docs/sprint-02/NCPC-UI-USABILITY-REFACTOR-2026-09-12.md` (new)
- this validation report

## Automated tests

Command:

```bash
cd apps/central-catalogue/service
PYTHONPATH=src python -m pytest -q
```

Result: the UI/auth/usability tests pass. The full suite still contains one pre-existing backend failure:

`tests/test_api.py::test_review_detail_exposes_identity_attributes_only`

The same exact test was executed against the untouched `apps(1).zip` baseline and failed before this refactor (`identity["brand"]` is `None` instead of `"Identity Brand"`). The UI refactor does not modify the submission/review backend code responsible for that assertion.

Focused UI/auth validation command:

```bash
PYTHONPATH=src python -m pytest -q \
  tests/test_admin_usability.py \
  tests/test_api.py::test_same_origin_admin_surface_is_served_without_embedded_business_rules \
  tests/test_ncpc08_auth_audit.py::test_missing_invalid_auth_and_admin_ui_do_not_expose_tokens
```

Result: **8 passed**.

Follow-up local-session UI guard: **9 passed**. The page now clears the entered local access value after `POST /admin/session`; subsequent UI API calls rely on the existing HttpOnly, SameSite session cookie and do not forward the access value.

JavaScript syntax validation:

```bash
node --check admin_script.js
```

Result: PASS.

## Rendered UI validation

The Browser plugin was not available in this environment. Regular Playwright with system Chromium was used as the permitted fallback.

Direct Chromium navigation to local loopback was blocked by the execution environment (`ERR_BLOCKED_BY_ADMINISTRATOR`). The FastAPI service itself was confirmed reachable with `curl`, so visual QA used the actual `admin.html` document loaded into Chromium. Network-dependent API data was not treated as live-browser proof.

Validated rendered states:

- Overview desktop
- Products desktop
- Barcode `?` help open
- Needs Review desktop
- Publish Catalogue `!` attention help open
- Products page Help on 390 px mobile
- explicit keyboard focus outline

Focus computed style:

`solid 3px rgb(0, 217, 255)`

## Interaction checks

PASS:

- sidebar page switching;
- Products page Help;
- barcode contextual `?` help;
- Publish Catalogue attention `!` help;
- Help dialog open/close;
- 390 px help dialog sizing;
- focus styling;
- Technical details disclosure markup;
- Local setup disclosure markup.

## Visual comparison against prior NCPC admin

Preserved:

- navy navigation shell;
- cyan active indicator;
- violet primary action family;
- light catalogue workspace;
- existing typography direction;
- familiar card/table structure.

Changed intentionally:

- engineering-first labels replaced with plain language;
- product IDs removed from default search tables;
- advanced/source/release identifiers moved under Technical details;
- local administrator token moved under Local setup;
- contextual help added;
- review decisions simplified;
- publication copy describes the consequence instead of internal release mechanics.

## Remaining risk

Because browser loopback navigation is restricted in this environment, a local developer should still perform one final real-runtime smoke pass after replacing the files:

1. open `/admin`;
2. connect local administrator access;
3. search/open a product;
4. inspect one real review;
5. preview Publish Catalogue without publishing;
6. check mobile or narrow viewport if practical.

This is runtime-evidence follow-up, not a known UI defect.
