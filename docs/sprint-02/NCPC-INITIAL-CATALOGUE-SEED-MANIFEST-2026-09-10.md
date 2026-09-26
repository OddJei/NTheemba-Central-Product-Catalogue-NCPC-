# NCPC initial catalogue seed manifest

Status: `LOCAL_DEVELOPMENT_PUBLICATION_PROVED / INDEPENDENT_TEST_AND_SECURITY_ACCEPTED / LIVE_RELEASE_NOT_AUTHORIZED`

## Current-state correction (REL-000003)

The current local development release is `REL-000003`, not the older
`REL-000002` proof described below: it has 164 products, 160 exact variants,
eight Class-B product-only identities, 658 evidence claims, 49 open reviews,
and zero BusinessCoverage. The database is at `a4e9b2c7d6f3`; `Boom` has the
source-linked `Trade Kings Group` `MANUFACTURER` relationship. The eight former
barcode-less identity-only rows are now published as product-only families,
not held; the remaining manifest holds are 40 Class-C rows plus the `P057`
barcode reconciliation. See `NCPC-SOURCE-RECONCILIATION-2026-09-10.md` for the
complete local source inventory and dispositions.

Source: `C:\Users\SMART PC\Downloads\Sechelanji_NCPC_Publication_Ready_Catalogue.xlsx`

Machine-readable artifact: `apps/central-catalogue/seeds/sechelanji-initial-publication-v1.json`

## Measured result

| Measure | Count |
| --- | ---: |
| Products published | 164 |
| Class-A variants proposed for publication | 161 |
| Variants published after exact PRD/VAR de-duplication | 160 |
| Class-B product families published without a VAR | 8 |
| Current public identities (variants + product families) | 168 |
| Proposed variants with one physical-package barcode | 160 |
| Proposed variants without barcode | 1 |
| Published variants without barcode | 1 |
| Published identities supported by physical-package evidence | 167 |
| Published variants supported by official online evidence | 1 |
| Published variants supported by both evidence types | 0 |
| Class-B product-family holds | 0 |
| Class-C review holds | 40 |
| Barcode duplicates within Class A | 0 |
| Verified-barcode conflicts/reconciliation holds | 1 |
| Duplicate/merge candidates held | 1 |

Manifest hash: `b1d280b814a326506e55307c58341d321e54827b8d3444a31f27607bbd0bb749`.

The manifest is generated from the source fingerprint and does not vary merely
because it was regenerated. It contains only product identity, category,
barcode claim, provenance, and review-state information; it excludes prices,
costs, stock, availability, local SKU, suppliers, and all TradeFlow facts.

## Completion-audit scope gaps

This report proves the bounded Sechelanji workbook and one official Trade Kings
candidate seed. The companion source-reconciliation ledger inventories every
currently available local Sechelanji/NCPC artifact and records its explicit
seed or non-promotion disposition. No connected Google Drive resource was
available during this run, so no Drive artifact is claimed as inspected. The
current model persists a first-class
organization and an evidence-backed brand-to-organization relationship.
Class-B product-only publication is now
implemented: eight exact families resolve through search with no invented VAR,
pack, or barcode; their future variant detail remains an ordinary review task.

## Evidence and decision handling

Each Class-A candidate has physical-package claims for canonical/variant
identity and Zambia market observation, plus its exact barcode claim. The
pending seed path records the owner-authorized decision type
`INITIAL_OWNER_AUTHORIZED_PUBLICATION`; it must not pretend that a named human
reviewer made the decision. The eight barcode-less workbook rows are published
as Class-B product families: they intentionally have no invented variant, pack,
or barcode.

The 40 explicit workbook uncertainties are in the manifest's
`held_for_review` section. Application creates a normal open
ReviewCase for every one of them. No barcode has been inferred, reassigned, or
silently merged.

## Application gate

Before application, the seed service must reconcile every row against the
target isolated database by normalized PRD/VAR identity and barcode; conflicts
must become ReviewCases. Only the exact manifest hash may enter the publication
snapshot. The proof must show candidate text/barcode resolution, exclusion of
held rows, and identity-only public projection, then receive independent Test
and Security/Reality review.

No Google Drive/Sheet write, deployment, or external integration has occurred
for this manifest.

## Exact local application operation

There is deliberately no unauthenticated bulk-import HTTP endpoint. Application
is the authenticated `InitialSeedService.apply()` transaction, which validates
the manifest hash before any mutation and writes PRD/VAR, evidence, review,
audit, batch, and manifest-bounded publication records atomically.

For the isolated PostgreSQL proof only, the exact operation was:

```powershell
docker compose -p ncpc-seed-proof-r2 -f docker-compose.runtime-proof.yml up -d
docker cp ..\seeds\sechelanji-initial-publication-v1.json ncpc-seed-proof-r2-ncpc-1:/tmp/sechelanji-initial-publication-v1.json
docker compose -p ncpc-seed-proof-r2 -f docker-compose.runtime-proof.yml exec -T ncpc python scripts/prove_initial_seed.py /tmp/sechelanji-initial-publication-v1.json
```

This is not an instruction to apply the manifest to an existing draft, target,
or live database. Target application requires a separately authorized run using
the same service path, a target reconciliation report, and deployment controls.

## Isolated local application proof

Result: `SUPERSEDED_BASELINE_LOCAL_SEED_PROOF`.

Against a fresh SQLite database migrated to `b7c4d2e9f1a3`, the application
created 156 PRDs, published 159 VARs and stored 636 evidence claims in one
manifest-bound release. Source row `P057` was correctly held because it
resolved to an already-selected PRD/VAR; it was not duplicated or silently
merged. Text search returned Fanta candidates, exact barcode lookup returned
one hit, no BusinessCoverage rows were created, and the publication projection
contained none of the tested TradeFlow fields (`selling_price`, `cost_price`,
`stock`, `supplier`, `availability`, `business_id`). This is isolated local
SQLite proof only; it is not a live NCPC publication or release.

## Isolated PostgreSQL persistence proof

Result: `LOCAL_POSTGRESQL_SEED_PROVED / SUPPLIED_RUNTIME_EVIDENCE_ACCEPTED`.

The fresh `ncpc-seed-proof-r5` Docker project migrated to
`c9d1e4f7a2b6`, then applied the same manifest into PostgreSQL. It produced
156 PRDs, 160 publication entries, 642 evidence claims, zero business coverage
rows, and 49 open seed ReviewCases: the 48 deliberate workbook holds plus
`P057`, whose divergent barcode for the same normalized variant requires
reconciliation. After the NCPC container was restarted, direct database reads
still returned 156 products, 160 entries, and 49 open seed reviews. This stack
has a separately named Docker volume and no host port,
Sheet, Drive, production service, or existing local catalogue volume.

## Independent gates

Independent Test accepted the local test gate: the six focused seed/publication
tests cover manifest-only release, barcode collision quarantine, durable
evidence/decision/audit records, open conflict reviews, idempotent replay, and
zero seed-created BusinessCoverage. The reviewer did not rerun the Docker
proof, so the PostgreSQL result above remains supplied runtime evidence.

The final enrichment re-review reran those six tests and accepted direct proof
that an altered manifest preserves the original `SeedBatchItem` batch/review
lineage, leaves submissions and open holds unchanged, deduplicates the original
evidence, adds one deliberate alias exactly once, retains two historical
snapshots, and resolves the approved alias in current candidate search.

Independent Security/Reality accepted the package for the next bounded gate:
the manifest hash is verified before mutation, owner authorization is explicit
and non-human-labelled, publication is limited to manifest VAR IDs, evidence
is FK-backed, conflicts become reviews, and the public projection is
allowlisted. This is not production acceptance. Deployed owner identity,
target-database reconciliation, operational deployment controls, and explicit
live-release authority remain required.

The final local re-review also accepted the single barcode-less official
candidate. It is discoverable by text search, has six claim-level evidence
rows, and was not inferred from a barcode. The fresh PostgreSQL r5 counts and
restart persistence were accepted as supplied runtime evidence by both
independent reviewers; neither approval authorizes deployment or a live target
mutation.

## Configured local development catalogue publication

The configured `apps/central-catalogue/service/ncpc-dev.db` was read first and
contained zero products, variants, and publication entries. It was migrated to
`c9d1e4f7a2b6` and then seeded through the same hash-checked service
transaction. Direct local reads now show 156 products, 160 variants, 160
publication entries, 642 evidence claims, zero BusinessCoverage rows, and 49
open seed reviews. Candidate text queries return both Fanta and the official
barcode-less Boom identity; exact barcode `6009652780142` returns one result.
This is the published local development catalogue. It is not a remote/live
catalogue, deployment, Sheet, Drive, or production operation.

A later local-only enrichment manifest reused immutable first-seed review and
variant lineage, then added the evidence-backed `Boom` Brand, `Blue Boom`
alias, and verified `Boom` -> `Trade Kings Group` -> `MANUFACTURER`
relationship. The current snapshot is `REL-000003` with 168 public identities:
160 exact variants and eight intentional product-only families. `Blue Boom`
resolves to the Boom product family through the current public candidate search.

## Current isolated PostgreSQL proof (r7)

On 2026-09-11, the current service image was built from this working tree and
run with a new named PostgreSQL volume and the isolated `172.16.247.0/24`
network (no host port). Its startup migration reached `a4e9b2c7d6f3`. The
exact manifest `b1d280b814a326506e55307c58341d321e54827b8d3444a31f27607bbd0bb749`
was applied through `prove_initial_seed.py`; a repeat correctly refused the
now non-empty proof database. Direct PostgreSQL reads reported 164 products,
160 variants, 168 publication entries, eight product-only entries, 658
evidence claims, 41 open owner-authorized seed reviews, and zero
`BusinessCoverage` rows. The persisted relationship was `Boom` -> `Trade
Kings Group` -> `MANUFACTURER` with `VERIFIED` status.

The script's successful initial transaction includes manifest-hash validation,
all manifest-hold/P057 quarantine checks, absence of exact held identities from
candidate search, a single exact barcode response, and the public-field
allowlist check. Both the application and PostgreSQL containers were then
restarted; PostgreSQL returned to accepting connections, application startup
completed, and the direct database counts and relationship were unchanged.
This is isolated local runtime evidence only. It is not a deployment, a live
catalogue publication, a Sheet/Drive operation, or release authorization.

## Canonical local promotion and proof cleanup (2026-09-11)

After explicit owner authorization, the same approved manifest was applied to
canonical local `nds-local-ncpc` PostgreSQL. The pre-existing legacy catalogue
was retained (it contained 1,221 products and 2,014 DRAFT variants); the seed
promoted only exact manifest identity matches under the owner-authorized
decision, while barcode conflicts remain held. Canonical migration reached
`a4e9b2c7d6f3`; direct reads show 1,363 products, 2,173 variants, `REL-000001`
with 168 public identities (160 variants and eight product-only families), 658
seed evidence claims, zero `BusinessCoverage`, and `Boom` -> `Trade Kings
Group` -> `MANUFACTURER` as `VERIFIED`. The canonical API returned HTTP 200
from `/health` and Docker health became healthy.

Per DEC-2026-09-11-001, proof projects `ncpc-seed-proof-r1` through `r7`, their
containers, volumes, networks, local images, temporary SQLite proof databases,
and build logs were removed after canonical verification. Source, migrations,
tests, manifest, and evidence documents remain. This is a canonical local
operation only; it does not authorize external deployment or live Sheet/Drive
mutation.
