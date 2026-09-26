"""NCPC-02 direct PostgreSQL identity and operational-data guards."""

from collections.abc import Sequence

from alembic import op

revision: str = "8f5be12c7e91"
down_revision: str | None = "11ec987dd3e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE products ADD CONSTRAINT ck_products_public_id_prefix CHECK (public_id ~ '^PRD-[A-Za-z0-9_-]+$')")
    op.execute("ALTER TABLE variants ADD CONSTRAINT ck_variants_public_id_prefix CHECK (public_id ~ '^VAR-[A-Za-z0-9_-]+$')")
    op.execute("ALTER TABLE products ADD CONSTRAINT ck_products_merged_not_self CHECK (superseded_by_id IS NULL OR superseded_by_id <> id)")
    op.execute("ALTER TABLE variants ADD CONSTRAINT ck_variants_merged_not_self CHECK (superseded_by_id IS NULL OR superseded_by_id <> id)")
    op.execute("""
    CREATE FUNCTION ncpc_reject_tradeflow_operational_data() RETURNS trigger AS $$
    DECLARE has_forbidden boolean;
    BEGIN
      WITH RECURSIVE nodes(value) AS (
        SELECT to_jsonb(NEW)
        UNION ALL SELECT e.value FROM nodes n CROSS JOIN LATERAL jsonb_each(n.value) e WHERE jsonb_typeof(n.value) = 'object'
        UNION ALL SELECT e.value FROM nodes n CROSS JOIN LATERAL jsonb_array_elements(n.value) e WHERE jsonb_typeof(n.value) = 'array'
      )
      SELECT EXISTS (
        SELECT 1 FROM nodes n CROSS JOIN LATERAL jsonb_object_keys(n.value) k
        WHERE jsonb_typeof(n.value) = 'object'
          AND regexp_replace(lower(k), '[^a-z]', '', 'g') IN
          ('availability','batches','cost','costprice','expenses','margin','maxstock','price','profit','quantityremaining','revenue','sales','sellingprice','stock','supplier','unitcost')
      ) INTO has_forbidden;
      IF has_forbidden THEN RAISE EXCEPTION 'TradeFlow-owned operational data is forbidden in NCPC'; END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    for table in ("products", "variants", "aliases", "barcode_claims", "proposed_changes", "audit_events", "publication_entries"):
        op.execute(f"CREATE TRIGGER trg_ncpc_reject_operational_{table} BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION ncpc_reject_tradeflow_operational_data()")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in ("products", "variants", "aliases", "barcode_claims", "proposed_changes", "audit_events", "publication_entries"):
        op.execute(f"DROP TRIGGER trg_ncpc_reject_operational_{table} ON {table}")
    op.execute("DROP FUNCTION ncpc_reject_tradeflow_operational_data()")
    for constraint, table in (("ck_variants_merged_not_self", "variants"), ("ck_products_merged_not_self", "products"), ("ck_variants_public_id_prefix", "variants"), ("ck_products_public_id_prefix", "products")):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {constraint}")
