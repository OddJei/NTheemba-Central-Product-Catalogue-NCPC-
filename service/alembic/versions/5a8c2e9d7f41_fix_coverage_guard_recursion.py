"""Correct recursive traversal in the NCPC-10 operational-data guard."""

from collections.abc import Sequence

from alembic import op

revision: str = "5a8c2e9d7f41"
down_revision: str | None = "4e7a91b2c6d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""
    CREATE OR REPLACE FUNCTION ncpc_reject_tradeflow_operational_data() RETURNS trigger AS $$
    DECLARE has_forbidden boolean;
    BEGIN
      WITH RECURSIVE nodes(value) AS (
        SELECT to_jsonb(NEW)
        UNION ALL
        SELECT child.value FROM nodes n CROSS JOIN LATERAL (
          SELECT value FROM jsonb_each(n.value) WHERE jsonb_typeof(n.value) = 'object'
          UNION ALL
          SELECT value FROM jsonb_array_elements(n.value) WHERE jsonb_typeof(n.value) = 'array'
        ) child
      )
      SELECT EXISTS (
        SELECT 1 FROM nodes n CROSS JOIN LATERAL jsonb_object_keys(n.value) k
        WHERE jsonb_typeof(n.value) = 'object'
          AND regexp_replace(lower(k), '[^a-z]', '', 'g') IN
          ('availability','batches','cost','costprice','expenses','margin','maxstock',
           'operationalpolicy','orders','policy','price','profit','quantityremaining',
           'revenue','sales','sellingprice','shop','shopconfig','stock','supplier','unitcost')
      ) INTO has_forbidden;
      IF has_forbidden THEN
        RAISE EXCEPTION 'TradeFlow-owned operational data is forbidden in NCPC';
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    pass
