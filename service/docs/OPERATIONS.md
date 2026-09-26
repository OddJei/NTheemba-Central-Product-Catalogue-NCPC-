# Operations runbook

1. Provision PostgreSQL 16 with encrypted storage, backups, and a least-privileged
   NCPC application role.
2. Set `NCPC_DATABASE_URL` and a long random `NCPC_ADMIN_BOOTSTRAP_TOKEN` through
   the deployment secret store. Never commit the token.
3. Run `alembic upgrade head` and capture output.
4. Verify `/health`, then create durable per-business/Ntheemba/reviewer clients and
   remove bootstrap access according to the operator procedure.
5. Validate legacy exports with `scripts/import_legacy_export.py export.json`.
   Only after backup/reconciliation, repeat with `--apply`.
6. Create the first prospective immutable publication and record its hash/version.
7. Run the full tests against the deployed PostgreSQL service before adapter work.

Back up PostgreSQL before migration/import. Restore is database-level; publication
rollback means consumers select a prior snapshot, never editing its payload.
