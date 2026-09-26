# NCPC service — Sprint 02.2–02.8

This service is the new NCPC identity authority. It coexists with the legacy
Apps Script catalogue while migration and adapter work remain separate.

It owns canonical product/variant identity, barcode and alias provenance,
submissions, review decisions, immutable publication snapshots, identity
relationships, business coverage, and Ntheemba trust ceilings. It must never
store a business's price, cost, stock, live availability, sales, suppliers, or
shop configuration.

## Local development

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/pytest
.venv/bin/uvicorn ncpc_service.api:app --reload --port 8080
```

For PostgreSQL 16, copy `.env.example`, set a real bootstrap token, and run
`docker compose up --build`. The bootstrap token is hashed before persistence.

## Contract boundary

- Public catalogue reads return identity fields only.
- Business writes are bearer-authenticated, tenant-bound, and idempotent.
- Admin review and publication require explicit scopes.
- TradeFlow products remain operational if this service is unavailable.
- Sprint 02.9 will add the real TradeFlow adapter; this package stops at 02.8.

See `../docs/sprint-02/02.2-02.8-implementation.md` and `docs/API.md`.
