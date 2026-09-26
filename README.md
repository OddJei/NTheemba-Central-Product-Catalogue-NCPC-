# Sprint 02.0-02.1 NCPC baseline and domain design

## Repository purpose

This repository is the public evidence and showcase copy of the NTheemba
Central Product Catalogue (NCPC). It was created so the catalogue identity
authority, domain design, API boundary and validation material can be viewed
independently while remaining part of the wider Ntheemba Digital Services
platform.

Parent platform: [NTheemba Platform](https://github.com/OddJei/NTheemba-Platform)

NCPC owns shared product identity and approved publication identity. It does
not own a business's private price, stock, supplier, availability or policy
facts; those remain in TradeFlow and other authoritative business systems.

Status: `DOCUMENTED / NO RUNTIME OR APPLICATION CHANGE`

This directory is the evidence package for the user-scoped Sprint 02.0 and
02.1 pass completed on 2026-09-02. It inspects the active NCPC Apps Script
edition, the older local prototype/schema, and the Standard TradeFlow adapter
surface. It deliberately does not introduce a database, web API, cache,
deployment, data migration, or integration.

The design boundary is simple: NCPC owns identity and coverage references;
TradeFlow owns business facts. A coverage reference is not stock, price, or
availability.

Documents:

- [Legacy baseline](legacy-baseline.md)
- [Field mapping](field-mapping.md)
- [Compatibility contract](compatibility-contract.md)
- [Migration risks](migration-risks.md)
- [Domain model](domain-model.md)
- [Lifecycle model](lifecycle-model.md)
- [Domain invariants](domain-invariants.md)
- [Legacy-to-domain map](legacy-to-domain-map.md)
- [Open decisions and scenario validation](open-decisions.md)

`READY FOR PHASE 02.2` means the domain is sufficiently specified to design a
provider-specific persistence model when the sprint gate permits it. It is not
approval to bypass the still-pending Sprint 01 owner runtime review.
