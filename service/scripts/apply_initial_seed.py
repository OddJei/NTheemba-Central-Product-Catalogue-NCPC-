#!/usr/bin/env python3
"""Apply a hash-checked owner-authorized seed to a canonical NCPC database."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

from ncpc_service.auth import Principal
from ncpc_service.database import SessionFactory, transaction
from ncpc_service.enums import PrincipalRole
from ncpc_service.initial_seed import InitialSeedService
from ncpc_service.models import ApiClient


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--request-id", required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    principal = Principal("local-owner-authorized-seed", PrincipalRole.ADMIN, None, frozenset({"*"}))
    with SessionFactory() as session, transaction(session):
        if session.get(ApiClient, principal.client_id) is None:
            session.add(ApiClient(
                client_id=principal.client_id,
                token_digest=hashlib.sha256(b"local-canonical-seed-audit-principal").hexdigest(),
                role=PrincipalRole.ADMIN,
                business_id=None,
                scopes=["*"],
                active=True,
            ))
        result = InitialSeedService(session).apply(manifest, principal, request_id=args.request_id)
    print(json.dumps({
        "batch_id": result.batch_id,
        "publication_id": result.publication_id,
        "published_variants": result.published_variants,
        "published_product_families": result.published_product_families,
        "held_conflicts": result.held_conflicts,
    }, indent=2))


if __name__ == "__main__":
    main()
