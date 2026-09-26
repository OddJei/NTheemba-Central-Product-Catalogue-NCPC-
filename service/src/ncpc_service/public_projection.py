"""Closed public projection for NCPC identity payloads.

NCPC owns canonical product identity only. Flexible review/import JSON must never become an
implicit public extension point for tenant price, stock, supplier, margin, or other business
facts. New publications and reads of older snapshots both pass through this projection.
"""

from __future__ import annotations

from typing import Any

_ATTRIBUTE_KEYS = frozenset(
    {
        "color",
        "colour",
        "flavor",
        "flavour",
        "form",
        "grade",
        "inventoryType",
        "material",
        "model",
        "packaging",
        "packagingType",
        "salesUnit",
        "scent",
        "size",
        "strength",
        "style",
        "unit",
        "variant",
    }
)
_PACK_SCALAR_KEYS = frozenset(
    {
        "count",
        "display_text",
        "packaging",
        "units_per_pack",
    }
)


def project_public_identity_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return only fields that are part of NCPC's public identity contract."""

    return {
        "ncpc_product_id": _text(payload.get("ncpc_product_id")),
        "ncpc_variant_id": _text(payload.get("ncpc_variant_id")),
        "canonical_name": _text(payload.get("canonical_name")),
        "variant_name": _text(payload.get("variant_name")),
        "brand": _optional_text(payload.get("brand")),
        "category": _optional_text(payload.get("category")),
        "pack_definition": _project_pack(payload.get("pack_definition")),
        "attributes": _project_attributes(payload.get("attributes")),
        "identifiers": _string_list(payload.get("identifiers")),
        "aliases": _string_list(payload.get("aliases")),
    }


def _project_pack(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    projected: dict[str, Any] = {}
    measure = value.get("primary_measure")
    if isinstance(measure, dict):
        unit = _optional_text(measure.get("unit"))
        raw_value = measure.get("value")
        if unit is not None and _is_scalar(raw_value):
            projected["primary_measure"] = {"value": raw_value, "unit": unit}
    for key in _PACK_SCALAR_KEYS:
        raw = value.get(key)
        if _is_scalar(raw) and raw not in (None, ""):
            projected[key] = raw
    return projected


def _project_attributes(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    projected: dict[str, Any] = {}
    for key in _ATTRIBUTE_KEYS:
        if key not in value:
            continue
        raw = value[key]
        if _is_scalar(raw):
            if raw not in (None, ""):
                projected[key] = raw
        elif isinstance(raw, list):
            safe = [item for item in raw if _is_scalar(item) and item not in (None, "")]
            if safe:
                projected[key] = safe
    return projected


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _text(item))]


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _text(value: object) -> str:
    return str(value or "").strip()


def _optional_text(value: object) -> str | None:
    text = _text(value)
    return text or None
