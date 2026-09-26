from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .enums import AliasState, ApprovalState, BarcodeState, LifecycleState
from .errors import ConflictError
from .models import Alias, BarcodeClaim, Brand, Category, IdSequence, Product, Variant
from .normalization import normalize_barcode, normalize_text

PROTECTED_BUSINESS_FIELDS = {
    "availability",
    "batches",
    "cost",
    "costprice",
    "expenses",
    "margin",
    "maxstock",
    "price",
    "profit",
    "quantityremaining",
    "revenue",
    "sales",
    "sellingprice",
    "stock",
    "supplier",
    "unitcost",
}


@dataclass
class LegacyImportReport:
    products_created: int = 0
    variants_created: int = 0
    barcodes_created: int = 0
    aliases_created: int = 0
    skipped_existing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_legacy_export(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if payload.get("success") is True else payload
    if not isinstance(data, dict):
        raise ValueError("legacy export must be an object")
    schema_version = str(data.get("schemaVersion", ""))
    if schema_version not in {"ncpc-2.0", "2.0"}:
        raise ValueError("unsupported legacy NCPC schema version")
    _reject_business_fields(data)
    for key in ("products", "productVariants", "identifiers", "productAliases"):
        if not isinstance(data.get(key, []), list):
            raise ValueError(f"legacy field {key} must be an array")
    return data


def import_legacy_export(session: Session, payload: dict[str, Any]) -> LegacyImportReport:
    data = validate_legacy_export(payload)
    report = LegacyImportReport()
    published_only = data.get("publishedOnly") is True

    brands = {str(row.get("id")): row for row in data.get("brands", [])}
    categories = {str(row.get("id")): row for row in data.get("categories", [])}
    brand_entities: dict[str, Brand] = {}
    category_entities: dict[str, Category] = {}
    product_entities: dict[str, Product] = {}
    variant_entities: dict[str, Variant] = {}

    for row in data.get("products", []):
        public_id = str(row.get("id", "")).strip()
        if not public_id.startswith("PRD-"):
            report.warnings.append(f"skipped invalid product ID: {public_id or '<blank>'}")
            continue
        existing = session.scalar(select(Product).where(Product.public_id == public_id))
        if existing is not None:
            if normalize_text(existing.canonical_name) != normalize_text(str(row.get("canonicalName", ""))):
                raise ConflictError(f"legacy product ID conflicts with existing identity: {public_id}")
            product_entities[public_id] = existing
            report.skipped_existing.append(public_id)
            continue
        brand = _legacy_reference(session, row.get("brandId"), brands, brand_entities, Brand, "name")
        category = _legacy_reference(
            session, row.get("categoryId"), categories, category_entities, Category, "name"
        )
        canonical_name = str(row.get("canonicalName", "")).strip()
        if not canonical_name:
            report.warnings.append(f"skipped nameless product: {public_id}")
            continue
        product = Product(
            public_id=public_id,
            canonical_name=canonical_name,
            normalized_name=normalize_text(canonical_name),
            brand_id=brand.id if brand else None,
            category_id=category.id if category else None,
            lifecycle=_legacy_lifecycle(row.get("status")),
            approval_state=_legacy_approval(row, published_only),
            provenance={
                "migration_source": "apps_script_ncpc_v2",
                "catalogue_version": data.get("catalogueVersion"),
                "exported_at": data.get("exportedAt"),
            },
        )
        session.add(product)
        session.flush()
        product_entities[public_id] = product
        report.products_created += 1
        _advance_sequence(session, public_id)

    for row in data.get("productVariants", []):
        public_id = str(row.get("id", "")).strip()
        product_public_id = str(row.get("productId", "")).strip()
        parent_product = product_entities.get(product_public_id)
        if not public_id.startswith("VAR-") or parent_product is None:
            report.warnings.append(f"skipped invalid or orphan variant: {public_id or '<blank>'}")
            continue
        existing_variant = session.scalar(select(Variant).where(Variant.public_id == public_id))
        if existing_variant is not None:
            variant_entities[public_id] = existing_variant
            report.skipped_existing.append(public_id)
            continue
        variant_name = str(row.get("variantName") or parent_product.canonical_name).strip()
        legacy_variant = Variant(
            public_id=public_id,
            product_id=parent_product.id,
            canonical_name=variant_name,
            normalized_name=normalize_text(variant_name),
            pack_definition=_pack_definition(row),
            attributes={
                key: row[key]
                for key in ("salesUnit", "packagingType", "inventoryType")
                if row.get(key) not in (None, "")
            },
            lifecycle=_legacy_lifecycle(row.get("status")),
            approval_state=_legacy_approval(row, published_only),
            provenance={
                "migration_source": "apps_script_ncpc_v2",
                "catalogue_version": data.get("catalogueVersion"),
            },
        )
        session.add(legacy_variant)
        session.flush()
        variant_entities[public_id] = legacy_variant
        report.variants_created += 1
        _advance_sequence(session, public_id)

    for row in data.get("identifiers", []):
        barcode_variant = variant_entities.get(str(row.get("variantId", "")))
        value = str(row.get("identifierValue", "")).strip()
        if barcode_variant is None or not value:
            continue
        normalized = normalize_barcode(value)
        duplicate = session.scalar(
            select(BarcodeClaim).where(
                BarcodeClaim.variant_id == barcode_variant.id,
                BarcodeClaim.normalized_value == normalized,
            )
        )
        if duplicate is not None:
            continue
        trusted = published_only or normalize_text(str(row.get("verificationStatus", ""))) in {
            "approved",
            "verified",
        }
        trusted_owner = session.scalar(
            select(BarcodeClaim).where(
                BarcodeClaim.normalized_value == normalized,
                BarcodeClaim.state == BarcodeState.VERIFIED_ACTIVE,
                BarcodeClaim.active.is_(True),
            )
        )
        state = BarcodeState.VERIFIED_ACTIVE if trusted else BarcodeState.PENDING_VERIFICATION
        conflict_group_id = None
        if trusted and trusted_owner is not None and trusted_owner.variant_id != barcode_variant.id:
            state = BarcodeState.CONFLICTED
            conflict_group_id = trusted_owner.conflict_group_id or str(uuid.uuid4())
            trusted_owner.conflict_group_id = conflict_group_id
        session.add(
            BarcodeClaim(
                variant_id=barcode_variant.id,
                original_value=value,
                normalized_value=normalized,
                symbology=row.get("identifierType"),
                state=state,
                source="legacy_import",
                source_ref=str(row.get("id", "")) or None,
                provenance={"legacy_record": row, "published_export": published_only},
                conflict_group_id=conflict_group_id,
                active=_legacy_lifecycle(row.get("status")) == LifecycleState.ACTIVE,
            )
        )
        session.flush()
        report.barcodes_created += 1

    for row in data.get("productAliases", []):
        alias_product = product_entities.get(str(row.get("productId", "")))
        alias_variant = variant_entities.get(str(row.get("variantId", "")))
        alias_text = str(row.get("alias", "")).strip()
        if not alias_text or (alias_product is None and alias_variant is None):
            continue
        if alias_variant is not None:
            alias_product = None
        session.add(
            Alias(
                display_text=alias_text,
                normalized_text=normalize_text(alias_text),
                product_id=alias_product.id if alias_product else None,
                variant_id=alias_variant.id if alias_variant else None,
                alias_kind=str(row.get("type") or "COMMON"),
                language=row.get("language") or None,
                state=AliasState.APPROVED if published_only else AliasState.PROPOSED,
                source="legacy_import",
                provenance={"legacy_record_id": row.get("id")},
            )
        )
        report.aliases_created += 1
    session.flush()
    return report


def _reject_business_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = re.sub(r"[^a-z]", "", str(key).casefold())
            if normalized_key in PROTECTED_BUSINESS_FIELDS:
                raise ValueError(f"TradeFlow-owned field is forbidden in NCPC import: {path}.{key}")
            _reject_business_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_business_fields(child, f"{path}[{index}]")


def _legacy_reference[ReferenceEntity: (Brand, Category)](
    session: Session,
    reference: Any,
    rows: dict[str, dict[str, Any]],
    cache: dict[str, ReferenceEntity],
    model: type[ReferenceEntity],
    name_field: str,
) -> ReferenceEntity | None:
    reference_id = str(reference or "")
    if not reference_id or reference_id not in rows:
        return None
    if reference_id in cache:
        return cache[reference_id]
    name = str(rows[reference_id].get(name_field, "")).strip()
    if not name:
        return None
    normalized = normalize_text(name)
    entity = session.scalar(select(model).where(model.normalized_name == normalized))
    if entity is None:
        entity = model(canonical_name=name, normalized_name=normalized)
        session.add(entity)
        session.flush()
    cache[reference_id] = entity
    return entity


def _legacy_lifecycle(value: Any) -> LifecycleState:
    state = normalize_text(str(value or "active"))
    if state in {"retired", "inactive"}:
        return LifecycleState.RETIRED
    if state == "deprecated":
        return LifecycleState.DEPRECATED
    return LifecycleState.ACTIVE


def _legacy_approval(row: dict[str, Any], published_only: bool) -> ApprovalState:
    published = normalize_text(str(row.get("publicationStatus", ""))) == "published"
    return ApprovalState.APPROVED if published_only or published else ApprovalState.DRAFT


def _pack_definition(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if row.get("sizeValue") not in (None, "") and row.get("sizeUnit"):
        result["primary_measure"] = {
            "value": row["sizeValue"],
            "unit": row["sizeUnit"],
        }
    if row.get("packagingType"):
        result["packaging"] = row["packagingType"]
    display = " ".join(
        str(part).strip()
        for part in (row.get("sizeValue"), row.get("sizeUnit"), row.get("packagingType"))
        if part not in (None, "")
    )
    if display:
        result["display_text"] = display
    return result


def _advance_sequence(session: Session, public_id: str) -> None:
    match = re.fullmatch(r"([A-Z]+)-(\d+)", public_id)
    if not match:
        return
    namespace, numeric = match.group(1), int(match.group(2))
    row = session.get(IdSequence, namespace)
    if row is None:
        session.add(IdSequence(namespace=namespace, next_value=numeric + 1))
    elif row.next_value <= numeric:
        row.next_value = numeric + 1
