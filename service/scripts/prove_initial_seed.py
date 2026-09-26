#!/usr/bin/env python3
"""Apply and prove an initial seed manifest against an empty isolated database."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import func, select

from ncpc_service.auth import Principal
from ncpc_service.catalogue import CatalogueService
from ncpc_service.database import SessionFactory, transaction
from ncpc_service.enums import PrincipalRole
from ncpc_service.initial_seed import InitialSeedService
from ncpc_service.models import ApiClient, BusinessCoverage, CatalogueEvidence, Product, PublicationEntry, ReviewCase, SeedBatch, Submission, Variant


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--query", default="Fanta Orange")
    parser.add_argument("--barcode-less-query", default="Boom Detergent Paste")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    principal = Principal("local-owner-authorized-seed", PrincipalRole.ADMIN, None, frozenset({"*"}))
    with SessionFactory() as session, transaction(session):
        if session.scalar(select(func.count()).select_from(Product)):
            raise SystemExit("refusing non-empty database; use a fresh isolated database")
        session.add(ApiClient(client_id=principal.client_id, token_digest=hashlib.sha256(b"local-proof-only").hexdigest(), role=PrincipalRole.ADMIN, business_id=None, scopes=["*"], active=True))
        result = InitialSeedService(session).apply(manifest, principal, request_id="local-seed-proof")
        candidates = CatalogueService(session).search_candidates(query=args.query)
        barcode_less_candidates = CatalogueService(session).search_candidates(query=args.barcode_less_query)
        barcode = manifest["candidates"][0]["variant"]["barcode"]
        barcode_hits = CatalogueService(session).search_candidates(barcode=barcode)
        held_refs = {row["source_ref"] for row in manifest.get("held_for_review", [])}
        returned_held_refs = {row["source_ref"] for row in result.held_conflicts}
        exact_held_hits = []
        for row in manifest.get("held_for_review", []):
            name = row["canonical_product_name"]
            for candidate in CatalogueService(session).search_candidates(query=name, limit=50):
                if candidate.canonical_name == name or candidate.variant_name == name:
                    exact_held_hits.append(name)
        serialized = " ".join(json.dumps(entry.payload, sort_keys=True) for entry in session.scalars(select(PublicationEntry)))
        forbidden = [key for key in ("selling_price", "cost_price", "stock", "supplier", "availability", "business_id") if key in serialized.casefold()]
        output = {
            "result": {
                "batch_id": result.batch_id,
                "publication_id": result.publication_id,
                "published_variants": result.published_variants,
                "published_product_families": result.published_product_families,
                "held_conflict_count": len(result.held_conflicts),
            },
            "products": session.scalar(select(func.count()).select_from(Product)),
            "variants": session.scalar(select(func.count()).select_from(Variant)),
            "publication_entries": session.scalar(select(func.count()).select_from(PublicationEntry)),
            "seed_batches": session.scalar(select(func.count()).select_from(SeedBatch)),
            "evidence_claims": session.scalar(select(func.count()).select_from(CatalogueEvidence)),
            "business_coverages": session.scalar(select(func.count()).select_from(BusinessCoverage)),
            "open_seed_reviews": session.scalar(
                select(func.count()).select_from(ReviewCase).join(Submission).where(
                    ReviewCase.state == "OPEN",
                    Submission.source == "owner_authorized_initial_seed",
                )
            ),
            "text_query_hits": len(candidates),
            "barcode_less_text_query_hits": len(barcode_less_candidates),
            "barcode_query_hits": len(barcode_hits),
            "forbidden_public_fields": forbidden,
            "manifest_hold_refs_returned": held_refs.issubset(returned_held_refs),
            "p057_conflict_returned": any(row["source_ref"] == "P057" for row in result.held_conflicts),
            "exact_held_identity_hits": exact_held_hits,
        }
        product_only_entries = session.scalar(
            select(func.count()).select_from(PublicationEntry).where(PublicationEntry.variant_id.is_(None))
        )
        output["product_only_publication_entries"] = product_only_entries
        if (
            not output["products"]
            or output["publication_entries"] != result.published_variants + result.published_product_families
            or product_only_entries != result.published_product_families
        ):
            raise SystemExit(f"unexpected seed counts: {output}")
        if not candidates or not barcode_less_candidates or len(barcode_hits) != 1 or forbidden or output["business_coverages"] or output["open_seed_reviews"] != len(result.held_conflicts) or not output["manifest_hold_refs_returned"] or not output["p057_conflict_returned"] or output["exact_held_identity_hits"]:
            raise SystemExit(f"seed proof failed: {output}")
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
