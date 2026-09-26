# Local NCPC to Ntheemba identity connection

Ntheemba is the client and NCPC is the published-identity resource server.
The connection is deliberately read-only: NCPC supplies canonical product
identity, variants, aliases, barcodes, brand, category and catalogue version.
Ntheemba must obtain price, stock, availability and business policy from the
tenant's TradeFlow/business integration.

## Local configuration

Set one long random value in the ignored local Compose environment file and
use the same value for both names below. Do not use the NCPC administrator
token and do not commit a value.

```text
NTHEEMBA_NCPC_API_TOKEN=<local-random-reader-token>
NCPC_NTHEEMBA_BOOTSTRAP_TOKEN=<same-local-random-reader-token>
```

The canonical root Compose stack already passes the NCPC value to the `ncpc`
service and to the `ntheemba-worker`. For the worker's local Docker-only HTTP
path it also sets:

```text
NTHEEMBA_ENVIRONMENT=development
NTHEEMBA_LOCAL_ACCEPTANCE_ENABLED=true
NTHEEMBA_NCPC_BASE_URL=http://ncpc:8080
```

The exact Docker hostname `ncpc` is the sole HTTP exception. Ntheemba rejects
localhost and private-IP destinations; staging and production require an
absolute HTTPS NCPC URL. The NCPC bootstrap principal has role `NTHEEMBA` and
can read `catalogue:read`, `coverage:read` and `discovery:read`; it cannot
submit, review, merge or publish.

## TradeFlow connection

TradeFlow is not a global NCPC setting. Ntheemba resolves a business-specific
integration from its durable PostgreSQL control plane. Each business record
needs its own approved HTTPS TradeFlow base URL, authentication reference
(never a token value in the UI), API version and enabled capabilities. Do not
reuse URLs or credentials across tenants. The local synthetic proof uses two
isolated TradeFlow stubs specifically to prove that tenant boundary.

The Ntheemba Admin Studio at `/dev/console` links to `/dev/pipeline` for local
queue/worker diagnostics. Both are development-only authenticated surfaces;
they do not authorize creating a real business, changing durable integration
configuration, or sending a customer message.

## Synthetic connection test

From `apps/ntheemba/bot`, use the pre-existing isolated proof stack after
supplying only synthetic local values:

```powershell
docker compose --env-file .env.ncpc-http-proof -f docker-compose.ncpc-http-proof.yml up --abort-on-container-exit --exit-code-from proof
```

The proof creates a synthetic published identity, reads it through
`HttpNCPCAdapter`, verifies bad-token and outage failures are safe, and proves
that price, stock and other operational fields are absent. A passing result is
`NTHEEMBA_NCPC_REAL_HTTP_SYNTHETIC_PROOF_PASSED`. This is local runtime proof,
not deployment or live integration approval.
