import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ncpc_service.enums import BarcodeState
from ncpc_service.legacy_import import import_legacy_export, validate_legacy_export
from ncpc_service.models import BarcodeClaim, Product, Variant


def legacy_payload():
    return {
        "schemaVersion": "ncpc-2.0",
        "catalogueVersion": 470,
        "publishedOnly": True,
        "brands": [{"id": "BRD-1", "name": "Legacy Brand"}],
        "categories": [{"id": "CAT-1", "name": "Drinks"}],
        "products": [
            {
                "id": "PRD-000042",
                "canonicalName": "Legacy Cola",
                "brandId": "BRD-1",
                "categoryId": "CAT-1",
                "publicationStatus": "published",
                "status": "active",
            }
        ],
        "productVariants": [
            {
                "id": "VAR-000077",
                "productId": "PRD-000042",
                "variantName": "Legacy Cola 500 ml",
                "sizeValue": "500",
                "sizeUnit": "ml",
                "packagingType": "bottle",
                "publicationStatus": "published",
                "status": "active",
            }
        ],
        "identifiers": [
            {
                "id": "IDN-1",
                "variantId": "VAR-000077",
                "identifierValue": "0012345678901",
                "identifierType": "EAN13",
                "status": "active",
            }
        ],
        "productAliases": [
            {"id": "ALS-1", "productId": "PRD-000042", "alias": "Old Cola", "status": "active"}
        ],
    }


def test_legacy_import_preserves_ids_and_leading_zeroes(session: Session):
    report = import_legacy_export(session, legacy_payload())
    session.commit()
    assert report.products_created == 1
    assert session.scalar(select(Product.public_id)) == "PRD-000042"
    assert session.scalar(select(Variant.public_id)) == "VAR-000077"
    claim = session.scalar(select(BarcodeClaim))
    assert claim is not None and claim.original_value == "0012345678901"


def test_legacy_import_rejects_tradeflow_business_facts():
    payload = legacy_payload()
    payload["products"][0]["sellingPrice"] = 25
    with pytest.raises(ValueError, match="forbidden"):
        validate_legacy_export(payload)


def test_legacy_barcode_collision_is_preserved_for_review(session: Session):
    payload = legacy_payload()
    payload["products"].append(
        {
            "id": "PRD-000043",
            "canonicalName": "Other Cola",
            "publicationStatus": "published",
            "status": "active",
        }
    )
    payload["productVariants"].append(
        {
            "id": "VAR-000078",
            "productId": "PRD-000043",
            "variantName": "Other Cola 500 ml",
            "publicationStatus": "published",
            "status": "active",
        }
    )
    payload["identifiers"].append(
        {
            "id": "IDN-2",
            "variantId": "VAR-000078",
            "identifierValue": "0012345678901",
            "status": "active",
        }
    )
    import_legacy_export(session, payload)
    session.commit()
    claims = session.scalars(select(BarcodeClaim)).all()
    assert sum(claim.state == BarcodeState.VERIFIED_ACTIVE for claim in claims) == 1
    assert sum(claim.state == BarcodeState.CONFLICTED for claim in claims) == 1
