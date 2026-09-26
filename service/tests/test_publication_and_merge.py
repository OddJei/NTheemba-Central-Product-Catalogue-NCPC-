import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ncpc_service.enums import LifecycleState, SnapshotState, VisibilityScope
from ncpc_service.merge import MergeService
from ncpc_service.models import IdentityRelationship, PublicationEntry, PublicationSnapshot, Variant
from ncpc_service.publication import PublicationService
from ncpc_service.schemas import MergeVariantRequest
from ncpc_service.visibility import VisibilityService

from .helpers import create_approved_product, publish


def test_released_snapshot_entries_are_immutable(session: Session, principals):
    create_approved_product(
        session,
        principals["business_a"],
        principals["admin"],
        business_product_ref="TFP-IMMUTABLE",
        name="Immutable product",
        barcode="0999999999999",
    )
    publish(session, principals["admin"], "NCPC-IMMUTABLE-001")
    entry = session.scalar(select(PublicationEntry))
    assert entry is not None
    entry.payload = {**entry.payload, "canonical_name": "Tampered"}
    with pytest.raises(ValueError, match="immutable"):
        session.flush()
    session.rollback()


def test_merge_preserves_old_release_and_remaps_coverage(session: Session, principals):
    _, _, source_id = create_approved_product(
        session,
        principals["business_a"],
        principals["admin"],
        business_product_ref="TFP-MERGE-SOURCE",
        name="Duplicate Cola",
        barcode="0700000000001",
    )
    _, _, survivor_id = create_approved_product(
        session,
        principals["business_a"],
        principals["admin"],
        business_product_ref="TFP-MERGE-SURVIVOR",
        name="Canonical Cola",
        barcode="0700000000002",
    )
    old_release = publish(session, principals["admin"], "NCPC-MERGE-001")
    result = MergeService(session).merge_variant(
        source_id,
        MergeVariantRequest(
            surviving_variant_id=survivor_id,
            rationale="Duplicate identities confirmed",
            idempotency_key="merge-cola-001",
        ),
        principals["admin"],
    )
    session.commit()
    assert result.remapped_coverage_count == 1
    source = session.scalar(select(Variant).where(Variant.public_id == source_id))
    assert source is not None and source.lifecycle == LifecycleState.MERGED
    assert session.scalar(select(IdentityRelationship)) is not None
    assert (
        VisibilityService(session)
        .get("business-a", "shop-test:TFP-MERGE-SOURCE", principals["business_a"])
        .effective_visibility
        == VisibilityScope.WIDER_TRUSTED
    )

    new_release = PublicationService(session).publish(principals["admin"], requested_version="NCPC-MERGE-002")
    session.commit()
    assert new_release.content_hash != old_release.content_hash
    old = session.scalar(select(PublicationSnapshot).where(PublicationSnapshot.version == "NCPC-MERGE-001"))
    assert old is not None and old.state == SnapshotState.SUPERSEDED
    old_ids = {
        entry.payload["ncpc_variant_id"]
        for entry in session.scalars(select(PublicationEntry).where(PublicationEntry.snapshot_id == old.id))
    }
    assert source_id in old_ids


def test_publication_projects_flexible_json_to_identity_only_fields(session: Session, principals):
    _, _, variant_id = create_approved_product(
        session,
        principals["business_a"],
        principals["admin"],
        business_product_ref="TFP-PROJECTION",
        name="Projection Product",
        barcode="0888888888888",
    )
    variant = session.scalar(select(Variant).where(Variant.public_id == variant_id))
    assert variant is not None
    variant.pack_definition = {
        "primary_measure": {"value": 500, "unit": "ml", "cost": 4},
        "packaging": "bottle",
        "supplier": "Private Supplier",
        "stock": 99,
    }
    variant.attributes = {
        "flavour": "orange",
        "selling_price": 42,
        "cost_price": 20,
        "margin": 22,
        "supplier": "Private Supplier",
        "business_id": "business-a",
    }
    session.commit()

    publish(session, principals["admin"], "NCPC-PROJECTION-001")
    entry = session.scalar(select(PublicationEntry).where(PublicationEntry.variant_id == variant.id))
    assert entry is not None

    assert entry.payload["pack_definition"] == {
        "primary_measure": {"value": 500, "unit": "ml"},
        "packaging": "bottle",
    }
    assert entry.payload["attributes"] == {"flavour": "orange"}
    serialized = str(entry.payload).casefold()
    for forbidden in ("selling_price", "cost_price", "stock", "supplier", "margin", "business_id"):
        assert forbidden not in serialized
