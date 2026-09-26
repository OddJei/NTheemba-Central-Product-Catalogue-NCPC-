"""NCPC-02 direct PostgreSQL invariant proof; synthetic local data only."""
# ruff: noqa: E501, E702
from __future__ import annotations

import argparse
import os

import psycopg

DSN = os.environ["NCPC_DATABASE_URL"].replace("+psycopg", "")


def expect_failure(cur: psycopg.Cursor[object], sql: str, params: tuple[object, ...] = ()) -> None:
    try:
        cur.execute(sql, params)
    except psycopg.Error:
        return
    raise AssertionError("expected PostgreSQL constraint/trigger rejection")


def write() -> None:
    with psycopg.connect(DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        assert cur.fetchone() == ("5a8c2e9d7f41",)
        # This proof is deliberately single-use in a fresh, project-namespaced
        # Compose volume.  It never cleans or resets an existing volume.
        cur.execute("INSERT INTO api_clients (client_id, token_digest, role, scopes, active, created_at, updated_at) VALUES ('proof-admin', repeat('a',64), 'ADMIN', '[]', true, now(), now())")
        product = "00000000-0000-0000-0000-000000000101"
        product2 = "00000000-0000-0000-0000-000000000102"
        variant = "00000000-0000-0000-0000-000000000201"
        variant2 = "00000000-0000-0000-0000-000000000202"
        base = "INSERT INTO products (id,public_id,canonical_name,normalized_name,lifecycle,approval_state,superseded_by_id,version,provenance,created_at,updated_at) VALUES (%s,%s,'Proof Product','proof product','ACTIVE','APPROVED',NULL,1,'{}',now(),now())"
        expect_failure(cur, base, ("00000000-0000-0000-0000-000000000100", "BAD-001"))
        cur.execute(base, (product, "PRD-PROOF-001")); cur.execute(base, (product2, "PRD-PROOF-002"))
        variant_sql = "INSERT INTO variants (id,public_id,product_id,canonical_name,normalized_name,pack_definition,attributes,lifecycle,approval_state,superseded_by_id,version,provenance,created_at,updated_at) VALUES (%s,%s,%s,'Proof Variant','proof variant','{}','{}','ACTIVE','APPROVED',NULL,1,'{}',now(),now())"
        expect_failure(cur, variant_sql, ("00000000-0000-0000-0000-000000000200", "BAD-001", product))
        expect_failure(cur, variant_sql, ("00000000-0000-0000-0000-000000000200", "VAR-ORPHAN", "00000000-0000-0000-0000-000000009999"))
        cur.execute(variant_sql, (variant, "VAR-PROOF-001", product)); cur.execute(variant_sql, (variant2, "VAR-PROOF-002", product2))
        expect_failure(cur, "UPDATE products SET public_id='PRD-TAMPER' WHERE id=%s", (product,))
        expect_failure(cur, "UPDATE variants SET public_id='VAR-TAMPER' WHERE id=%s", (variant,))
        expect_failure(cur, "INSERT INTO aliases (id,display_text,normalized_text,product_id,variant_id,alias_kind,state,source,provenance,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000301','Both','both',%s,%s,'COMMON','APPROVED','proof','{}',now(),now())", (product, variant))
        expect_failure(cur, "INSERT INTO aliases (id,display_text,normalized_text,alias_kind,state,source,provenance,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000302','Neither','neither','COMMON','APPROVED','proof','{}',now(),now())")
        cur.execute("INSERT INTO aliases (id,display_text,normalized_text,product_id,alias_kind,state,source,provenance,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000303','Proof','proof',%s,'COMMON','APPROVED','proof','{}',now(),now())", (product,))
        cur.execute("INSERT INTO barcode_claims (id,variant_id,original_value,normalized_value,state,source,provenance,active,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000401',%s,'001','001','VERIFIED_ACTIVE','proof','{}',true,now(),now())", (variant,))
        expect_failure(cur, "INSERT INTO barcode_claims (id,variant_id,original_value,normalized_value,state,source,provenance,active,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000402',%s,'001','001','VERIFIED_ACTIVE','proof','{}',true,now(),now())", (variant2,))
        cur.execute("INSERT INTO barcode_claims (id,variant_id,original_value,normalized_value,state,source,provenance,active,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000403',%s,'001','001','CONFLICTED','proof','{}',true,now(),now())", (variant2,))
        cur.execute("SELECT state, active FROM barcode_claims WHERE id='00000000-0000-0000-0000-000000000401'")
        assert cur.fetchone() == ("VERIFIED_ACTIVE", True)
        cur.execute("SELECT state, active FROM barcode_claims WHERE id='00000000-0000-0000-0000-000000000403'")
        assert cur.fetchone() == ("CONFLICTED", True)
        expect_failure(cur, "UPDATE products SET lifecycle='MERGED', superseded_by_id=id WHERE id=%s", (product,))
        expect_failure(cur, "UPDATE variants SET lifecycle='MERGED', superseded_by_id=id WHERE id=%s", (variant,))
        cur.execute("UPDATE products SET lifecycle='MERGED', superseded_by_id=%s WHERE id=%s", (product2, product))
        cur.execute("UPDATE variants SET lifecycle='MERGED', superseded_by_id=%s WHERE id=%s", (variant2, variant))
        cur.execute("SELECT superseded_by_id FROM products WHERE id=%s", (product,))
        assert cur.fetchone() == (product2,)
        cur.execute("SELECT superseded_by_id FROM variants WHERE id=%s", (variant,))
        assert cur.fetchone() == (variant2,)
        cur.execute("INSERT INTO submissions (id,public_id,submission_type,state,business_id,business_product_ref,source,submitter_client_id,idempotency_key,submitted_at,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000504','SUB-PROOF-001','NEW_PRODUCT','SUBMITTED','proof-business','P-2','proof','proof-admin','proof-submission-1',now(),now(),now())")
        expect_failure(cur, "INSERT INTO business_coverages (id,business_id,business_product_ref,state,exposure_preference,source,location_projection,active,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000501','proof-business','P-1','SUBMITTED_PENDING','WIDER','proof','{}',true,now(),now())")
        cur.execute("INSERT INTO business_coverages (id,business_id,business_product_ref,variant_id,state,exposure_preference,source,location_projection,active,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000502','proof-business','P-1',%s,'LINKED_APPROVED','WIDER','proof','{}',true,now(),now())", (variant,))
        expect_failure(cur, "INSERT INTO business_coverages (id,business_id,business_product_ref,variant_id,state,exposure_preference,source,location_projection,active,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000503','proof-business','P-1',%s,'LINKED_APPROVED','WIDER','proof','{}',true,now(),now())", (variant2,))
        cur.execute("INSERT INTO business_coverages (id,business_id,business_product_ref,submission_id,state,exposure_preference,source,location_projection,active,created_at,updated_at) VALUES ('00000000-0000-0000-0000-000000000505','proof-business','P-2','00000000-0000-0000-0000-000000000504','SUBMITTED_PENDING','WITHIN_BUSINESS','proof','{}',true,now(),now())")
        expect_failure(cur, "UPDATE products SET provenance='{\"price\": 7}' WHERE id=%s", (product,))
        expect_failure(cur, "UPDATE variants SET attributes='{\"nested\": {\"sellingPrice\": 7}}' WHERE id=%s", (variant,))
        expect_failure(cur, "UPDATE aliases SET provenance='{\"nested\": {\"supplier\": \"x\"}}' WHERE id='00000000-0000-0000-0000-000000000303'")
        expect_failure(cur, "UPDATE barcode_claims SET provenance='{\"nested\": {\"cost\": 7}}' WHERE id='00000000-0000-0000-0000-000000000401'")
        expect_failure(cur, "INSERT INTO proposed_changes (id,submission_id,field_path,proposed_value,evidence) VALUES ('00000000-0000-0000-0000-000000000506','00000000-0000-0000-0000-000000000504','/name','{\"nested\": {\"stock\": 7}}','{}')")
        cur.execute("INSERT INTO publication_snapshots (id,public_id,version,state,content_hash,item_count,created_by,created_at,published_at) VALUES ('00000000-0000-0000-0000-000000000601','PUB-PROOF-001','proof-1','PUBLISHED',repeat('b',64),1,'proof-admin',now(),now())")
        cur.execute("INSERT INTO publication_entries (id,snapshot_id,product_id,variant_id,product_version,variant_version,payload,content_hash) VALUES ('00000000-0000-0000-0000-000000000602','00000000-0000-0000-0000-000000000601',%s,%s,1,1,'{}',repeat('c',64))", (product, variant))
        expect_failure(cur, "UPDATE publication_entries SET payload='{\"x\":1}' WHERE id='00000000-0000-0000-0000-000000000602'")
        expect_failure(cur, "DELETE FROM publication_entries WHERE id='00000000-0000-0000-0000-000000000602'")
        expect_failure(cur, "UPDATE publication_snapshots SET version='tamper' WHERE id='00000000-0000-0000-0000-000000000601'")
        expect_failure(cur, "DELETE FROM publication_snapshots WHERE id='00000000-0000-0000-0000-000000000601'")
        cur.execute("INSERT INTO audit_events (id,event_type,entity_kind,entity_id,actor_client_id,new_value,occurred_at) VALUES ('00000000-0000-0000-0000-000000000701','PROOF','PRODUCT','PRD-PROOF-001','proof-admin','{}',now())")
        expect_failure(cur, "UPDATE audit_events SET event_type='TAMPER' WHERE id='00000000-0000-0000-0000-000000000701'")
        expect_failure(cur, "DELETE FROM audit_events WHERE id='00000000-0000-0000-0000-000000000701'")
    print("NCPC_POSTGRESQL_INVARIANTS_WRITE_PROVED")


def verify() -> None:
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT public_id, lifecycle, superseded_by_id FROM products WHERE id='00000000-0000-0000-0000-000000000101'")
        assert cur.fetchone() == ("PRD-PROOF-001", "MERGED", "00000000-0000-0000-0000-000000000102")
        cur.execute("SELECT public_id, lifecycle, superseded_by_id FROM variants WHERE id='00000000-0000-0000-0000-000000000201'")
        assert cur.fetchone() == ("VAR-PROOF-001", "MERGED", "00000000-0000-0000-0000-000000000202")
        cur.execute("SELECT count(*) FROM aliases WHERE id='00000000-0000-0000-0000-000000000303'")
        assert cur.fetchone() == (1,)
        cur.execute("SELECT count(*) FROM barcode_claims WHERE normalized_value='001' AND state IN ('VERIFIED_ACTIVE', 'CONFLICTED')")
        assert cur.fetchone() == (2,)
        cur.execute("SELECT count(*) FROM business_coverages WHERE id IN ('00000000-0000-0000-0000-000000000502','00000000-0000-0000-0000-000000000505')")
        assert cur.fetchone() == (2,)
        cur.execute("SELECT count(*) FROM publication_entries WHERE id='00000000-0000-0000-0000-000000000602'")
        assert cur.fetchone() == (1,)
        cur.execute("SELECT count(*) FROM audit_events WHERE id='00000000-0000-0000-0000-000000000701'")
        assert cur.fetchone() == (1,)
    print("NCPC_POSTGRESQL_INVARIANTS_RESTART_PERSISTENCE_PROVED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("phase", choices=("write", "verify")); args = parser.parse_args()
    (write if args.phase == "write" else verify)()
