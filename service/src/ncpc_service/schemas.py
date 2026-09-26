from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ExposurePreference, ReviewOutcome, VisibilityScope
from .normalization import normalize_barcode

OPERATIONAL_KEY_NAMES = frozenset({
    "availability", "batches", "cost", "costprice", "expenses", "margin", "maxstock",
    "operationalpolicy", "orders", "policy", "price", "profit", "quantityremaining",
    "revenue", "sales", "sellingprice", "shop", "shopconfig", "stock", "supplier", "unitcost",
})


def reject_operational_keys(value: Any) -> Any:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = "".join(character for character in key.lower() if character.isalpha())
            if normalized_key in OPERATIONAL_KEY_NAMES:
                raise ValueError("TradeFlow-owned operational data is forbidden in NCPC")
            reject_operational_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            reject_operational_keys(nested)
    return value

SAFE_COVERAGE_LOCATION_KEYS = frozenset(
    {
        "country_id",
        "country_name",
        "province_id",
        "province_name",
        "district_id",
        "district_name",
        "town_id",
        "town_name",
        "catalogue_version",
    }
)


class ApiEnvelope[T](BaseModel):
    version: str = "v1"
    request_id: str
    success: bool
    data: T | None = None
    error: dict[str, str] | None = None


class BarcodeInput(BaseModel):
    value: str = Field(min_length=1, max_length=128)
    symbology: str | None = Field(default=None, max_length=32)
    source: str = Field(default="manual_entry", max_length=64)
    source_ref: str | None = Field(default=None, max_length=256)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("value")
    @classmethod
    def preserve_barcode(cls, value: str) -> str:
        return normalize_barcode(value)

    @field_validator("evidence")
    @classmethod
    def reject_tradeflow_operational_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        return reject_operational_keys(value)


class AliasInput(BaseModel):
    text: str = Field(min_length=1, max_length=320)
    kind: str = Field(default="COMMON", max_length=64)
    language: str | None = Field(default=None, max_length=16)
    source: str = Field(default="manual_entry", max_length=64)


class NewProductSubmissionRequest(BaseModel):
    business_id: str = Field(min_length=1, max_length=128)
    business_product_ref: str = Field(min_length=1, max_length=128)
    shop_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=128)
    canonical_name: str = Field(min_length=1, max_length=320)
    variant_name: str | None = Field(default=None, max_length=320)
    brand: str | None = Field(default=None, max_length=240)
    category: str | None = Field(default=None, max_length=240)
    pack_definition: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    barcodes: list[BarcodeInput] = Field(default_factory=list, max_length=20)
    aliases: list[AliasInput] = Field(default_factory=list, max_length=30)
    source: str = Field(default="tradeflow", max_length=64)
    location_projection: dict[str, Any] = Field(default_factory=dict)
    exposure_preference: ExposurePreference = ExposurePreference.WIDER

    @field_validator("pack_definition", "attributes")
    @classmethod
    def reject_tradeflow_operational_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        return reject_operational_keys(value)

    @field_validator("location_projection")
    @classmethod
    def allow_only_safe_coverage_location(cls, value: dict[str, Any]) -> dict[str, str]:
        unexpected = set(value) - SAFE_COVERAGE_LOCATION_KEYS
        if unexpected:
            raise ValueError(
                "location_projection contains unsupported fields: "
                + ", ".join(sorted(unexpected))
            )

        projection: dict[str, str] = {}
        for key, raw_value in value.items():
            if not isinstance(raw_value, str):
                raise ValueError(f"location_projection.{key} must be text")
            normalized = raw_value.strip()
            if normalized:
                projection[key] = normalized
        return projection


class ExistingVariantCoverageLinkRequest(BaseModel):
    business_product_ref: str = Field(min_length=1, max_length=128)
    shop_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=128)
    ncpc_product_id: str = Field(pattern=r"^PRD-[A-Za-z0-9_-]+$")
    ncpc_variant_id: str = Field(pattern=r"^VAR-[A-Za-z0-9_-]+$")
    source: str = Field(default="tradeflow", max_length=64)
    location_projection: dict[str, Any] = Field(default_factory=dict)
    exposure_preference: ExposurePreference = ExposurePreference.WIDER

    @field_validator("location_projection")
    @classmethod
    def allow_only_safe_coverage_location(cls, value: dict[str, Any]) -> dict[str, str]:
        unexpected = set(value) - SAFE_COVERAGE_LOCATION_KEYS
        if unexpected:
            raise ValueError(
                "location_projection contains unsupported fields: "
                + ", ".join(sorted(unexpected))
            )
        projection: dict[str, str] = {}
        for key, raw_value in value.items():
            if not isinstance(raw_value, str):
                raise ValueError(f"location_projection.{key} must be text")
            normalized = raw_value.strip()
            if normalized:
                projection[key] = normalized
        return projection

class CorrectionSubmissionRequest(BaseModel):
    business_id: str = Field(min_length=1, max_length=128)
    business_product_ref: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=128)
    ncpc_product_id: str | None = Field(default=None, pattern=r"^PRD-[A-Za-z0-9_-]+$")
    ncpc_variant_id: str = Field(pattern=r"^VAR-[A-Za-z0-9_-]+$")
    changes: dict[str, Any] = Field(min_length=1)
    evidence: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="tradeflow", max_length=64)

    @field_validator("changes", "evidence")
    @classmethod
    def reject_tradeflow_operational_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        return reject_operational_keys(value)


class ReviewDecisionRequest(BaseModel):
    outcome: ReviewOutcome
    rationale: str = Field(min_length=3, max_length=4000)
    matched_variant_id: str | None = Field(default=None, pattern=r"^VAR-[A-Za-z0-9_-]+$")
    canonical_name: str | None = Field(default=None, max_length=320)
    variant_name: str | None = Field(default=None, max_length=320)
    brand: str | None = Field(default=None, max_length=240)
    category: str | None = Field(default=None, max_length=240)
    pack_definition: dict[str, Any] | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("pack_definition", "evidence")
    @classmethod
    def reject_tradeflow_operational_data(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return reject_operational_keys(value)


class PublicationRequest(BaseModel):
    version: str | None = Field(default=None, min_length=3, max_length=64)
    rationale: str = Field(min_length=3, max_length=4000)


class VerifyVariantRequest(BaseModel):
    ncpc_product_id: str = Field(pattern=r"^PRD-[A-Za-z0-9_-]+$")
    ncpc_variant_id: str = Field(pattern=r"^VAR-[A-Za-z0-9_-]+$")
    release_version: str | None = Field(default=None, max_length=64)


class TradeFlowRpcRequest(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    data: dict[str, Any] = Field(default_factory=dict)


class ExposurePreferenceRequest(BaseModel):
    preference: ExposurePreference


class MergeVariantRequest(BaseModel):
    surviving_variant_id: str = Field(pattern=r"^VAR-[A-Za-z0-9_-]+$")
    rationale: str = Field(min_length=3, max_length=4000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class CoverageLookupRequest(BaseModel):
    ncpc_variant_ids: list[str] = Field(min_length=1, max_length=50)

    @field_validator("ncpc_variant_ids")
    @classmethod
    def validate_variant_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("variant IDs must be unique")
        for value in values:
            if not value.startswith("VAR-") or len(value) > 32:
                raise ValueError("invalid NCPC variant ID")
        return values


class CandidateDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ncpc_product_id: str
    ncpc_variant_id: str
    canonical_name: str
    variant_name: str
    brand: str | None
    category: str | None
    pack_definition: dict[str, Any]
    attributes: dict[str, Any]
    identifiers: list[str]
    aliases: list[str]
    catalogue_version: str
    release_version: str
    match_type: str


class VariantDto(BaseModel):
    ncpc_product_id: str
    ncpc_variant_id: str
    canonical_name: str
    variant_name: str
    brand: str | None
    category: str | None
    pack_definition: dict[str, Any]
    attributes: dict[str, Any]
    identifiers: list[str]
    aliases: list[str]
    catalogue_version: str
    release_version: str


class SubmissionStatusDto(BaseModel):
    submission_id: str
    state: str
    business_id: str | None
    business_product_ref: str | None
    ncpc_product_id: str | None = None
    ncpc_variant_id: str | None = None
    review_id: str | None = None
    submitted_at: datetime
    decided_at: datetime | None
    published_at: datetime | None


class CoverageLinkDto(BaseModel):
    business_id: str
    business_product_ref: str
    shop_id: str
    state: str
    ncpc_product_id: str
    ncpc_variant_id: str
    exposure_preference: ExposurePreference
    location_projection: dict[str, str]


class ReviewDto(BaseModel):
    review_id: str
    submission_id: str
    reason: str
    state: str
    submission_state: str
    business_id: str | None
    business_product_ref: str | None
    changes: list[dict[str, Any]]


class PublicationDto(BaseModel):
    snapshot_id: str
    version: str
    state: str
    content_hash: str
    item_count: int
    created_at: datetime
    published_at: datetime | None


class VisibilityDto(BaseModel):
    business_id: str
    business_product_ref: str
    coverage_state: str | None
    business_preference: str
    trust_ceiling: VisibilityScope
    effective_visibility: VisibilityScope
    provisional: bool
    trusted: bool
    ncpc_variant_id: str | None
    release_version: str | None


class MergeResultDto(BaseModel):
    source_variant_id: str
    surviving_variant_id: str
    relationship: str
    remapped_coverage_count: int


class DiscoveryCoverageDto(BaseModel):
    business_id: str
    business_product_ref: str
    shop_id: str | None
    ncpc_variant_id: str
    visibility: VisibilityScope
    location_projection: dict[str, Any]
    release_version: str
