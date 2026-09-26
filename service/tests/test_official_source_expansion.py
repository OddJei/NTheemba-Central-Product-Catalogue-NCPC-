import pytest
from sqlalchemy import select

from ncpc_service.catalogue import CatalogueService
from ncpc_service.enums import ApprovalState, LifecycleState
from ncpc_service.errors import ConflictError
from ncpc_service.initial_seed import InitialSeedService
from ncpc_service.models import CatalogueEvidence, Product, SeedBatch, Variant
from ncpc_service.normalization import normalize_text
from ncpc_service.publication import sha256_json


def _manifest(*, existing_variant_id: str | None = None):
    manifest = {
        "schema_version": "ncpc-initial-seed-manifest-v1",
        "source_fingerprint": "official-source-fixture",
        "decision_type": "INITIAL_OWNER_AUTHORIZED_PUBLICATION",
        "actor_label": "NCPC official-source catalogue expansion / owner-authorized initial catalogue operation",
        "rationale": "Official manufacturer evidence establishes identity; barcode verification remains separate.",
        "sources": [{
            "source_key": "official",
            "title": "Official product page",
            "source_url": "https://example.invalid/product",
            "source_type": "manufacturer_official",
            "authority": "OFFICIAL",
            "accessed_at": "2026-09-12T04:30:00+02:00",
            "notes": "fixture",
        }],
        "candidates": [{
            "source_ref": "OFFICIAL:Fixture Product:500 ml bottle",
            "classification": "CLASS_A_PUBLISH_OFFICIAL_SOURCE",
            "product": {"canonical_name": "Fixture Product", "brand": "Fixture Brand"},
            "variant": {
                "canonical_name": "500 ml bottle",
                "pack_definition": {"primary_measure": {"value": 500, "unit": "ml"}, "packaging": "bottle"},
                "attributes": {},
                "barcode": None,
                "barcode_status": "PENDING_PHYSICAL_OR_GS1_VERIFICATION",
            },
            "evidence": [
                {"source_key": "official", "claim_type": "canonical_name", "claim_value": "Fixture Product", "evidence_tier": "OFFICIAL_EXACT", "confidence": "HIGH", "verification_status": "VERIFIED"},
                {"source_key": "official", "claim_type": "variant_identity", "claim_value": "500 ml bottle", "evidence_tier": "OFFICIAL_EXACT", "confidence": "HIGH", "verification_status": "VERIFIED"},
            ],
            "decision_type": "INITIAL_OWNER_AUTHORIZED_PUBLICATION",
            **({"match_existing_variant_id": existing_variant_id} if existing_variant_id else {}),
        }],
        "product_only_candidates": [],
        "held_for_review": [],
        "summary": {"barcodes_imported": 0},
    }
    manifest["manifest_hash"] = sha256_json(manifest)
    return manifest


def test_official_source_manifest_publishes_barcodeless_identity_and_retains_rationale(session, principals):
    manifest = _manifest()
    result = InitialSeedService(session).apply(manifest, principals["admin"])
    session.commit()

    assert result.published_variants == 1
    batch = session.scalar(select(SeedBatch).where(SeedBatch.public_id == result.batch_id))
    assert batch is not None and "Official manufacturer evidence" in batch.rationale
    hit = CatalogueService(session).search_candidates(query="Fixture Product")[0]
    assert hit.canonical_name == "Fixture Product"
    assert hit.identifiers == []
    evidence = session.scalars(select(CatalogueEvidence)).all()
    assert {item.evidence_tier for item in evidence} == {"OFFICIAL_EXACT"}


def test_official_source_manifest_rejects_a_tampered_rationale(session, principals):
    manifest = _manifest()
    manifest["rationale"] = "This change was not part of the owner-approved manifest."

    with pytest.raises(ConflictError, match="manifest hash"):
        InitialSeedService(session).apply(manifest, principals["admin"])


def test_official_source_expansion_can_enrich_exact_existing_variant_without_duplication(session, principals):
    brandless_product = Product(
        public_id="PRD-EXISTING",
        canonical_name="Fixture Product",
        normalized_name=normalize_text("Fixture Product"),
        lifecycle=LifecycleState.ACTIVE,
        approval_state=ApprovalState.APPROVED,
        provenance={"fixture": True},
    )
    session.add(brandless_product); session.flush()
    existing_variant = Variant(
        public_id="VAR-EXISTING",
        product_id=brandless_product.id,
        canonical_name="Fixture Product 500 ml",
        normalized_name=normalize_text("Fixture Product 500 ml"),
        pack_definition={"primary_measure": {"value": 500, "unit": "ml"}},
        attributes={}, lifecycle=LifecycleState.ACTIVE,
        approval_state=ApprovalState.APPROVED, provenance={"fixture": True},
    )
    session.add(existing_variant); session.commit()

    manifest = _manifest(existing_variant_id="VAR-EXISTING")
    InitialSeedService(session).apply(manifest, principals["admin"])
    session.commit()

    assert session.query(Variant).filter(Variant.product_id == brandless_product.id).count() == 1
    refreshed_variant = session.get(Variant, existing_variant.id)
    assert refreshed_variant is not None
    assert refreshed_variant.approval_state == ApprovalState.APPROVED
    refreshed = session.get(Product, brandless_product.id)
    assert refreshed is not None
    session.refresh(refreshed)
    assert refreshed.brand is not None
    assert refreshed.brand.canonical_name == "Fixture Brand"
    hit = CatalogueService(session).search_candidates(query="Fixture Product")[0]
    assert hit.ncpc_variant_id == "VAR-EXISTING"
