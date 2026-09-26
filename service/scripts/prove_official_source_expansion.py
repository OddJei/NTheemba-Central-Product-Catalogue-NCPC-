#!/usr/bin/env python3
"""Prove the currently configured local NCPC official-source expansion release."""
from __future__ import annotations

from sqlalchemy import func, select

from ncpc_service.catalogue import CatalogueService
from ncpc_service.database import SessionFactory
from ncpc_service.enums import SnapshotState
from ncpc_service.models import BarcodeClaim, BusinessCoverage, PublicationEntry, PublicationSnapshot

FORBIDDEN = {"selling_price", "cost_price", "stock", "availability", "supplier", "business_id", "max_stock", "restock"}
QUERIES = [
    "Coca-Cola Original Taste",
    "Zambia's Pride Natbake",
    "Vaseline Blue Seal Original Petroleum Jelly",
    "Boom Force Scouring Cleanser",
    "Whitespoon Household Sugar",
    "Sona Beauty Soap",
    "7UP Lemon-Lime Soft Drink",
]

with SessionFactory() as session:
    snapshot = session.scalar(select(PublicationSnapshot).where(PublicationSnapshot.state == SnapshotState.PUBLISHED))
    assert snapshot is not None
    entries = session.scalars(select(PublicationEntry).where(PublicationEntry.snapshot_id == snapshot.id)).all()
    variants = [entry for entry in entries if entry.variant_id is not None]
    product_only = [entry for entry in entries if entry.variant_id is None]
    barcode_variants = set(session.scalars(select(BarcodeClaim.variant_id).where(BarcodeClaim.active.is_(True))).all())
    barcodeless = sum(entry.variant_id not in barcode_variants for entry in variants)
    leaks = [entry for entry in entries if set(entry.payload) & FORBIDDEN]
    coverage = session.scalar(select(func.count()).select_from(BusinessCoverage))
    assert not leaks
    assert coverage == 0
    assert barcodeless > 0
    service = CatalogueService(session)
    for query in QUERIES:
        hits = service.search_candidates(query=query, limit=20)
        assert hits, query
    print({
        "release": snapshot.public_id,
        "version": snapshot.version,
        "public_identities": len(entries),
        "variants": len(variants),
        "product_only": len(product_only),
        "barcodeless_variants": barcodeless,
        "business_coverage": coverage,
        "forbidden_payload_leaks": len(leaks),
        "queries_proved": QUERIES,
    })
