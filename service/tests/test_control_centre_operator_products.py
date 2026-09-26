from sqlalchemy.orm import Session

from ncpc_service.auth import Principal

from .conftest import ADMIN_TOKEN
from .helpers import create_approved_product, publish


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_product_list_and_detail_support_plain_language_central_ui(
    client, session: Session, principals: dict[str, Principal]
) -> None:
    _submission_id, product_id, variant_id = create_approved_product(
        session,
        principals["business_a"],
        principals["admin"],
        business_product_ref="central-ui-demo",
        name="Central UI Demo Drink",
        barcode="6001000000007",
    )
    publish(session, principals["admin"], "REL-CENTRAL-UI")

    listed = client.get("/v1/admin/products?query=Central%20UI", headers=auth(ADMIN_TOKEN))
    assert listed.status_code == 200
    items = listed.json()["data"]["products"]
    assert len(items) == 1
    assert items[0]["ncpc_product_id"] == product_id
    assert items[0]["variant_count"] == 1
    assert items[0]["published_variant_count"] == 1
    assert items[0]["barcode_count"] == 1
    assert items[0]["published"] is True

    detail = client.get(f"/v1/admin/products/{product_id}", headers=auth(ADMIN_TOKEN))
    assert detail.status_code == 200
    payload = detail.json()["data"]
    assert payload["ncpc_product_id"] == product_id
    assert payload["published"] is True
    assert payload["release_version"] == "REL-CENTRAL-UI"
    assert payload["variants"][0]["ncpc_variant_id"] == variant_id
    assert payload["variants"][0]["barcodes"][0]["value"] == "6001000000007"

    rendered = str(payload).lower()
    for forbidden in ("sellingprice", "costprice", "stock", "revenue", "profit"):
        assert forbidden not in rendered


def test_admin_product_operator_projection_requires_authentication(client) -> None:
    assert client.get("/v1/admin/products").status_code == 401
    assert client.get("/v1/admin/products/PRD-000001").status_code == 401
