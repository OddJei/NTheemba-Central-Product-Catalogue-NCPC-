"""Seed only synthetic bearer clients required by isolated NCPC proof scripts."""

from __future__ import annotations

import hashlib
import json
import os

import psycopg

DATABASE_URL = os.environ["NCPC_DATABASE_URL"].replace("+psycopg", "")

CLIENTS = (
    (
        "business-a",
        "ncpc03-business-a-token-local-only",
        "BUSINESS",
        "business-a",
        ["catalogue:read", "submissions:read", "submissions:write", "coverage:read", "coverage:write"],
    ),
    (
        "business-b",
        "ncpc03-business-b-token-local-only",
        "BUSINESS",
        "business-b",
        ["catalogue:read", "submissions:read", "submissions:write", "coverage:read", "coverage:write"],
    ),
    (
        "ncpc04-business",
        "ncpc04-business-token-local-only",
        "BUSINESS",
        "ncpc04-business",
        ["catalogue:read", "submissions:read", "submissions:write", "coverage:read", "coverage:write"],
    ),
    (
        "ncpc04-reviewer",
        "ncpc04-reviewer-token-local-only",
        "REVIEWER",
        None,
        ["catalogue:read", "reviews:read", "reviews:decide", "identities:merge", "publications:read"],
    ),
    (
        "ncpc05-business",
        "ncpc05-business-token-local-only",
        "BUSINESS",
        "ncpc05-business",
        ["catalogue:read", "submissions:read", "submissions:write", "coverage:read", "coverage:write"],
    ),
    (
        "ncpc06-business",
        "ncpc06-business-token-local-only",
        "BUSINESS",
        "ncpc06-business",
        ["catalogue:read", "submissions:read", "submissions:write", "coverage:read", "coverage:write"],
    ),
    (
        "ncpc11-business-a",
        "ncpc11-business-a-token-local-only",
        "BUSINESS",
        "ncpc11-business-a",
        ["catalogue:read", "submissions:read", "submissions:write", "coverage:read", "coverage:write"],
    ),
    (
        "ncpc11-business-b",
        "ncpc11-business-b-token-local-only",
        "BUSINESS",
        "ncpc11-business-b",
        ["catalogue:read", "submissions:read", "submissions:write", "coverage:read", "coverage:write"],
    ),
    ("ncpc06-reader", "ncpc06-reader-token-local-only", "NTHEEMBA", None, ["catalogue:read"]),
)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def main() -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection, connection.cursor() as cursor:
        for client_id, token, role, business_id, scopes in CLIENTS:
            cursor.execute(
                """
                INSERT INTO api_clients (
                    client_id, token_digest, role, business_id, scopes, active, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, true, now(), now())
                ON CONFLICT (client_id) DO UPDATE SET token_digest = EXCLUDED.token_digest,
                    role = EXCLUDED.role, business_id = EXCLUDED.business_id, scopes = EXCLUDED.scopes,
                    active = true, updated_at = now()
                """,
                (client_id, token_digest(token), role, business_id, json.dumps(scopes)),
            )
    print("NCPC_RUNTIME_PROOF_CLIENTS_SEEDED")


if __name__ == "__main__":
    main()
