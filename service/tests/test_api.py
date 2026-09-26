from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ncpc_service.models import BusinessCoverage, PublicationEntry

from .conftest import ADMIN_TOKEN, BUSINESS_A_TOKEN, BUSINESS_B_TOKEN, NTHEEMBA_TOKEN


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Request-ID": "test-request-001"}


def test_health_is_public_and_catalogue_requires_auth(client: TestClient):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["data"]["api_version"] == "v1"
    rejected = client.get("/v1/catalogue/candidates?query=cola")
    assert rejected.status_code == 401
    assert rejected.json()["error"]["code"] == "UNAUTHORIZED"
    assert rejected.headers["X-Request-ID"]


def test_oversized_request_is_rejected_safely(client: TestClient):
    result = client.post(
        "/v1/tradeflow",
        content=b"{}",
        headers={**auth(ADMIN_TOKEN), "Content-Length": "1048577"},
    )
    assert result.status_code == 413
    assert result.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_business_submission_is_tenant_bound_and_idempotent(client: TestClient):
    body = {
        "business_id": "business-a",
        "business_product_ref": "shop-api:TFP-API-001",
        "shop_id": "shop-api",
        "idempotency_key": "api-submit-001",
        "canonical_name": "API Cola",
        "barcodes": [{"value": "0011223344556", "source": "scanned"}],
    }
    first = client.post("/v1/submissions/products", json=body, headers=auth(BUSINESS_A_TOKEN))
    assert first.status_code == 201
    second = client.post("/v1/submissions/products", json=body, headers=auth(BUSINESS_A_TOKEN))
    assert second.status_code == 201
    assert first.json()["data"]["submission_id"] == second.json()["data"]["submission_id"]

    wrong_business = client.post(
        "/v1/submissions/products",
        json={**body, "idempotency_key": "api-submit-002"},
        headers=auth(BUSINESS_B_TOKEN),
    )
    assert wrong_business.status_code == 403
    assert wrong_business.json()["error"]["code"] == "FORBIDDEN"


def test_shop_coverage_location_projection_is_safe_and_shop_bound(
    client: TestClient, session: Session
):
    body = {
        "business_id": "business-a",
        "business_product_ref": "shop-lusaka:TFP-API-003",
        "shop_id": "shop-lusaka",
        "idempotency_key": "api-shop-coverage-003",
        "canonical_name": "Shop Coverage Cola",
        "location_projection": {
            "country_id": "ZM",
            "province_name": "Lusaka",
            "district_id": "LUSAKA",
            "town_name": "Lusaka",
            "catalogue_version": "ZMB-V5",
        },
    }
    submitted = client.post("/v1/submissions/products", json=body, headers=auth(BUSINESS_A_TOKEN))
    assert submitted.status_code == 201
    coverage = session.query(BusinessCoverage).one()
    assert coverage.shop_id == "shop-lusaka"
    assert coverage.business_product_ref == "shop-lusaka:TFP-API-003"
    assert coverage.location_projection == body["location_projection"]

    for offset, unsafe_projection in enumerate(
        (
            {"area": "Private estate"},
            {"address_details": "12 Private Road"},
            {"stock": "99"},
            {"unknown_field": "not allowed"},
        ),
        start=4,
    ):
        unsafe_location = client.post(
            "/v1/submissions/products",
            json={
                **body,
                "idempotency_key": f"api-shop-coverage-00{offset}",
                "location_projection": unsafe_projection,
            },
            headers=auth(BUSINESS_A_TOKEN),
        )
        assert unsafe_location.status_code == 422

    mismatched_shop = client.post(
        "/v1/submissions/products",
        json={
            **body,
            "idempotency_key": "api-shop-coverage-005",
            "business_product_ref": "shop-kitwe:TFP-API-003",
        },
        headers=auth(BUSINESS_A_TOKEN),
    )
    assert mismatched_shop.status_code == 403

    missing_shop = client.post(
        "/v1/submissions/products",
        json={
            **body,
            "idempotency_key": "api-shop-coverage-007",
            "shop_id": None,
            "business_product_ref": "TFP-API-003",
        },
        headers=auth(BUSINESS_A_TOKEN),
    )
    assert missing_shop.status_code == 403

    spoofed_source = client.post(
        "/v1/submissions/products",
        json={
            **body,
            "idempotency_key": "api-shop-coverage-008",
            "business_product_ref": "shop-kitwe:TFP-API-003",
            "source": "manual",
        },
        headers=auth(BUSINESS_A_TOKEN),
    )
    assert spoofed_source.status_code == 403
    assert session.query(BusinessCoverage).count() == 1


def test_full_http_workflow_and_public_allowlist(client: TestClient, session: Session):
    submitted = client.post(
        "/v1/tradeflow",
        json={
            "action": "submitProduct",
            "data": {
                "business_id": "business-a",
                "business_product_ref": "shop-api:TFP-API-002",
                "shop_id": "shop-api",
                "idempotency_key": "api-full-flow-002",
                "canonical_name": "HTTP Cola",
                "variant_name": "HTTP Cola 500 ml",
                "brand": "HTTP Brand",
                "category": "Drinks",
                "pack_definition": {"primary_measure": {"value": 500, "unit": "ml"}},
                "barcodes": [{"value": "0000000000007", "source": "scanned"}],
            },
        },
        headers=auth(BUSINESS_A_TOKEN),
    )
    assert submitted.status_code == 200
    review_id = submitted.json()["data"]["review_id"]
    approved = client.post(
        f"/v1/admin/reviews/{review_id}/decisions",
        json={"outcome": "APPROVE_NEW", "rationale": "Verified in HTTP test"},
        headers=auth(ADMIN_TOKEN),
    )
    assert approved.status_code == 200
    published = client.post(
        "/v1/admin/publications",
            json={"version": "NCPC-API-001", "rationale": "Verified identity release for HTTP test"},
        headers=auth(ADMIN_TOKEN),
    )
    assert published.status_code == 201

    result = client.post(
        "/v1/tradeflow",
        json={"action": "searchCandidates", "data": {"barcode": "0000000000007"}},
        headers=auth(BUSINESS_A_TOKEN),
    )
    assert result.status_code == 200
    candidate = result.json()["data"]["candidates"][0]
    forbidden = ["cost", "stock", "supplier", "batch", "margin", "availability", "price"]
    lowered = str(candidate).casefold()
    assert all(word not in lowered for word in forbidden)
    assert session.query(PublicationEntry).count() == 1


def test_unknown_rpc_action_is_safe(client: TestClient):
    result = client.post(
        "/v1/tradeflow",
        json={"action": "deleteEverything", "data": {}},
        headers=auth(ADMIN_TOKEN),
    )
    assert result.status_code == 400
    assert result.json()["error"] == {"code": "UNKNOWN_ACTION", "message": "unknown action"}


def test_discovery_requires_ntheemba_principal(client: TestClient):
    business = client.post(
        "/v1/discovery/coverage/by-variants",
        json={"ncpc_variant_ids": ["VAR-000001"]},
        headers=auth(BUSINESS_A_TOKEN),
    )
    assert business.status_code == 403
    ntheemba = client.post(
        "/v1/discovery/coverage/by-variants",
        json={"ncpc_variant_ids": ["VAR-000001"]},
        headers=auth(NTHEEMBA_TOKEN),
    )
    assert ntheemba.status_code == 200
    assert ntheemba.json()["data"] == {"coverage": []}
