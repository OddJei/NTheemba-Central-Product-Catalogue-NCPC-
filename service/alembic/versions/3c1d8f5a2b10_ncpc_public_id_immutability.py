"""Enforce immutable public Product and Variant identities in PostgreSQL."""

from collections.abc import Sequence

from alembic import op

revision: str = "3c1d8f5a2b10"
down_revision: str | None = "9ae61d0b4f72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""
    CREATE FUNCTION ncpc_reject_public_id_change() RETURNS trigger AS $$
    BEGIN
      IF NEW.public_id <> OLD.public_id THEN
        RAISE EXCEPTION 'NCPC public identity is immutable';
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    for table in ("products", "variants"):
        op.execute(
            f"CREATE TRIGGER trg_ncpc_immutable_{table}_public_id "
            f"BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION ncpc_reject_public_id_change()"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in ("products", "variants"):
        op.execute(f"DROP TRIGGER trg_ncpc_immutable_{table}_public_id ON {table}")
    op.execute("DROP FUNCTION ncpc_reject_public_id_change()")
