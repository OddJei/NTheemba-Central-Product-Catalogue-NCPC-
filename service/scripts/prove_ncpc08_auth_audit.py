"""Synthetic HTTP/PostgreSQL proof for the NCPC-08 local auth/audit gate."""

from __future__ import annotations

import hashlib
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg

DATABASE_URL = os.environ["NCPC_DATABASE_URL"].replace("+psycopg", "")
ADMIN_TOKEN = os.environ["NCPC_ADMIN_BOOTSTRAP_TOKEN"]
BUSINESS_TOKEN = "ncpc08-synthetic-business-token"
REVIEWER_TOKEN = "ncpc08-synthetic-reviewer-token"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request(path: str, token: str, *, body: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    value = Request(
        f"http://127.0.0.1:8080{path}",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Request-ID": "ncpc08-runtime-proof",
        },
        method="POST" if body is not None else "GET",
    )
    try:
        with urlopen(value, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def main() -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO api_clients (
                client_id, token_digest, role, business_id, scopes, active, created_at, updated_at
            )
            VALUES (%s, %s, 'BUSINESS', 'ncpc08-business', %s::jsonb, true, now(), now()),
                   (%s, %s, 'REVIEWER', NULL, %s::jsonb, true, now(), now())
            ON CONFLICT (client_id) DO UPDATE SET token_digest = EXCLUDED.token_digest,
                role = EXCLUDED.role, business_id = EXCLUDED.business_id, scopes = EXCLUDED.scopes,
                active = true, updated_at = now()
            """,
            (
                "ncpc08-business",
                digest(BUSINESS_TOKEN),
                json.dumps(["*", "submissions:write", "submissions:read", "coverage:read"]),
                "ncpc08-reviewer",
                digest(REVIEWER_TOKEN),
                json.dumps(["reviews:read", "reviews:decide", "publications:write"]),
            ),
        )

    denied, denied_body = request("/v1/admin/reviews", BUSINESS_TOKEN)
    assert denied == 403 and denied_body["error"]["code"] == "FORBIDDEN"
    accepted, submission = request(
        "/v1/submissions/products",
        BUSINESS_TOKEN,
        body={
            "business_id": "ncpc08-business",
            "business_product_ref": "NCPC08-HTTP-001",
            "idempotency_key": "ncpc08-http-submit-001",
            "canonical_name": "NCPC08 Runtime Synthetic Product",
            "actor_client_id": "bootstrap-admin",
        },
    )
    assert accepted == 201
    reviewer_status, _ = request("/v1/admin/reviews", REVIEWER_TOKEN)
    assert reviewer_status == 200
    publish_status, publish_body = request(
        "/v1/admin/publications",
        REVIEWER_TOKEN,
        body={"version": "NCPC08-NOT-ALLOWED", "rationale": "Reviewer must not publish"},
    )
    assert publish_status == 403 and publish_body["error"]["code"] == "FORBIDDEN"

    submission_id = submission["data"]["submission_id"]
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT actor_client_id, request_id, occurred_at
            FROM audit_events
            WHERE entity_kind = 'SUBMISSION' AND entity_id = %s AND event_type = 'SUBMISSION_CREATED'
            """,
            (submission_id,),
        )
        event = cursor.fetchone()
        assert event is not None
        assert event[0] == "ncpc08-business"
        assert event[1] == "ncpc08-runtime-proof"
        assert event[2] is not None
    print("NCPC08_AUTH_AUDIT_POSTGRES_PROVED")


if __name__ == "__main__":
    main()
