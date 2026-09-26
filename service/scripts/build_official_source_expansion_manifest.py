#!/usr/bin/env python3
"""Build an owner-authorized NCPC official-source expansion manifest.

The builder is intentionally conservative:
- product identity may be published from authoritative official web evidence;
- exact variants are published only when the chosen official source establishes the pack;
- broad corporate/brand portfolio pages may publish only the product family;
- research barcodes are never promoted by this pass;
- unresolved exact-pack claims become normal review holds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

OFFICIAL_SOURCE_TYPES = {
    "manufacturer_official",
    "brand_owner_official",
    "bottler_official",
    "producer_official",
}

# Domains whose official public presence was revalidated during this pass.
DEFAULT_VALIDATED_DOMAINS = {
    "www.coca-cola.com",
    "zamsugar.co.zm",
    "nmc.co.zm",
    "www.tradekings.co.zm",
    "www.vaseline.com",
    "www.willowtongroup.com",
    "www.varunbeverages.com",
    "zambeefplc.com",
}

FRESH_REVALIDATED_URLS = {
    "https://www.coca-cola.com/xe/en/legal/terms-and-conditions-zambia-utc-promotion-2026",
    "https://www.coca-cola.com/xe/en/legal/terms-and-conditions-minute-maid-zambia",
    "https://nmc.co.zm/products/",
    "https://nmc.co.zm/prices/",
    "https://www.tradekings.co.zm/product/boom-force-scouring-cleanser/",
    "https://www.tradekings.co.zm/product/boom-washing-powder/",
    "https://www.tradekings.co.zm/product/romeo-beauty-soap/",
    "https://www.tradekings.co.zm/product/romeo-medicated/",
    "https://www.tradekings.co.zm/product/romeo-pink-and-white-beauty-soap/",
    "https://www.tradekings.co.zm/product/boom-bubble-plus-washing-powder/",
    "https://www.tradekings.co.zm/product/boom-auto-washing-powder/",
    "https://www.vaseline.com/za/en/p/vaseline-jelly-original.html/00000060014399",
    "https://www.vaseline.com/za/en/p/vaseline-jelly-cocoa.html/06001087377546",
    "https://www.vaseline.com/za/en/p/vaseline-jelly-vitamine.html/00000060014429",
    "https://www.vaseline.com/za/en/p/vaseline-jelly-aloe.html/00000060018885",
    "https://www.vaseline.com/za/en/p/vaseline-jelly-baby.html/06001087005647",
    "https://zamsugar.co.zm/our-products/",
    "https://zamsugar.co.zm/product/household-sugar/",
    "https://zamsugar.co.zm/product/brown-sugar/",
    "https://zamsugar.co.zm/product/refined-white-sugar/",
    "https://www.willowtongroup.com/pages/our-brands",
    "https://www.willowtongroup.com/pages/sona-soap",
    "https://www.willowtongroup.com/pages/allsome",
    "https://www.willowtongroup.com/pages/dlite",
    "https://www.varunbeverages.com/our-products/",
    "https://zambeefplc.com/our-brands/",
    "https://zambeefplc.com/",
}


def norm(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", text)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalized_url(url: str) -> str:
    return url.rstrip("/")


def source_score(source: dict, product_name: str) -> tuple[int, int, int]:
    title = norm(str(source.get("title", "")))
    url = str(source.get("url", ""))
    product_tokens = [token for token in re.findall(r"[a-z0-9]+", norm(product_name)) if len(token) >= 4]
    hits = sum(1 for token in product_tokens if token in title or token in norm(url))
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    exact_bonus = 1 if is_exact_pack_source(source) else 0
    return exact_bonus, hits, len(path_parts)


def is_exact_pack_source(source: dict) -> bool:
    """Whether the source shape is allowed to support exact VAR/pack publication."""
    url = str(source.get("url", ""))
    parsed = urlparse(url)
    domain, path = parsed.netloc, parsed.path.rstrip("/")

    if domain == "nmc.co.zm" and path in {"/products", "/prices"}:
        return True
    if domain == "www.vaseline.com" and "/za/en/p/" in path:
        return True
    if domain == "zamsugar.co.zm" and path.startswith("/product/"):
        return True
    if domain == "www.tradekings.co.zm" and path.startswith("/product/") and path != "/product":
        # Includes the legacy Boom Detergent Paste product-main-template route.
        return True
    if domain == "www.willowtongroup.com" and path.startswith("/pages/") and path not in {"/pages/our-brands", "/pages/company-overview"}:
        return True
    if domain == "www.coca-cola.com" and path in {
        "/xe/en/legal/terms-and-conditions-zambia-utc-promotion-2026",
        "/xe/en/legal/terms-and-conditions-minute-maid-zambia",
    }:
        return True
    return False


def measure_key(pack: dict) -> tuple[str, str] | None:
    primary = pack.get("primary_measure") or {}
    value, unit = primary.get("value"), primary.get("unit")
    if value in (None, "") or not unit:
        return None
    try:
        numeric = f"{float(value):g}"
    except (TypeError, ValueError):
        numeric = str(value).strip()
    return numeric, norm(str(unit))


def build_pack(variant: dict) -> dict:
    pack: dict = {}
    if variant.get("sizeValue") not in (None, "") and variant.get("sizeUnit"):
        pack["primary_measure"] = {"value": variant["sizeValue"], "unit": variant["sizeUnit"]}
    if variant.get("packagingType"):
        pack["packaging"] = variant["packagingType"]
    pack["display_text"] = variant["variantName"]
    return pack


def coca_source_supports_variant(source: dict, product_name: str, variant: dict) -> bool:
    url = normalized_url(str(source.get("url", "")))
    key = measure_key(build_pack(variant))
    packaging = norm(str(variant.get("packagingType") or ""))
    product_norm = norm(product_name)

    utc = "https://www.coca-cola.com/xe/en/legal/terms-and-conditions-zambia-utc-promotion-2026"
    mm = "https://www.coca-cola.com/xe/en/legal/terms-and-conditions-minute-maid-zambia"
    if url == normalized_url(utc):
        if key == ("500", "ml") and "pet" in packaging:
            return any(token in product_norm for token in ("coca-cola", "fanta", "sprite", "minute maid", "aquasavana"))
        if key == ("300", "ml") and ("glass" in packaging or "rgb" in norm(str(variant.get("variantName") or ""))):
            return any(token in product_norm for token in ("coca-cola", "fanta", "sprite"))
        return False
    if url == normalized_url(mm):
        return "minute maid" in product_norm and key == ("500", "ml") and "pet" in packaging
    return False


def source_supports_variant(source: dict, product_name: str, variant: dict) -> bool:
    if not is_exact_pack_source(source):
        return False
    if urlparse(str(source.get("url", ""))).netloc == "www.coca-cola.com":
        return coca_source_supports_variant(source, product_name, variant)
    return True


def load_existing(db_path: Path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    products = {
        norm(row["canonical_name"]): dict(row)
        for row in con.execute("select id, public_id, canonical_name, normalized_name, brand_id from products")
    }
    variants: dict[str, list[dict]] = defaultdict(list)
    for row in con.execute(
        "select p.normalized_name product_norm, v.id, v.public_id, v.canonical_name, v.pack_definition "
        "from variants v join products p on p.id=v.product_id"
    ):
        item = dict(row)
        try:
            item["pack_definition"] = json.loads(item["pack_definition"] or "{}")
        except json.JSONDecodeError:
            item["pack_definition"] = {}
        variants[row["product_norm"]].append(item)
    con.close()
    return products, variants


def choose_existing_variant(product_norm: str, candidate_pack: dict, product_variants: list[dict], official_measure_counts: Counter) -> str | None:
    """Map only when a pack measure is unique on both sides.

    This avoids silently treating a generic physical 500 g variant as the same
    identity as one of several official flavours/forms sharing 500 g.
    """
    key = measure_key(candidate_pack)
    if key is None or official_measure_counts[key] != 1:
        return None
    matches = [variant for variant in product_variants if measure_key(variant["pack_definition"]) == key]
    if len(matches) != 1:
        return None
    return str(matches[0]["public_id"])


def manifest_source(source: dict, phase41_created_at: str) -> dict:
    url = str(source.get("url") or "").strip()
    fresh = normalized_url(url) in {normalized_url(item) for item in FRESH_REVALIDATED_URLS}
    return {
        "source_key": str(source["id"]),
        "title": str(source.get("title") or source["id"]),
        "source_url": url or None,
        "source_type": str(source.get("sourceType") or "manufacturer_official"),
        "authority": "OFFICIAL",
        "accessed_at": "2026-09-12T04:30:00+02:00" if fresh else phase41_created_at,
        "notes": (
            "Official source freshly revalidated during the 2026-09-12 expansion pass."
            if fresh
            else "Official source preserved from the Phase41 Zambia research corpus; product identity was previously reviewed as official_exact."
        ),
    }


def evidence(source_id: str, claim_type: str, claim_value: str, notes: str) -> dict:
    return {
        "source_key": source_id,
        "claim_type": claim_type,
        "claim_value": claim_value,
        "evidence_tier": "OFFICIAL_EXACT",
        "confidence": "HIGH",
        "verification_status": "VERIFIED",
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase41", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw_bytes = args.phase41.read_bytes()
    phase41 = json.loads(raw_bytes.decode("utf-8"))
    source_map = {row["id"]: row for row in phase41.get("sources", [])}
    existing_products, existing_variants = load_existing(args.database)

    qualifying: list[tuple[dict, list[dict]]] = []
    for bundle in phase41.get("bundles", []):
        research = bundle.get("research") or {}
        inst = research.get("institutionExpansion") or {}
        confidence = research.get("fieldConfidence") or {}
        if bundle.get("product", {}).get("verificationStatus") != "reviewed":
            continue
        if inst.get("evidenceTier") != "official_exact" or "Zambia" not in str(inst.get("marketScope") or ""):
            continue
        if confidence.get("canonicalName") != "high" or confidence.get("variant") != "high":
            continue
        strong = []
        for source_id in research.get("sourceIds", []):
            source = source_map.get(source_id) or {}
            domain = urlparse(str(source.get("url", ""))).netloc
            if (
                source.get("authority") == "official"
                and source.get("sourceType") in OFFICIAL_SOURCE_TYPES
                and domain in DEFAULT_VALIDATED_DOMAINS
            ):
                strong.append(source)
        if strong:
            qualifying.append((bundle, strong))

    used_sources: dict[str, dict] = {}
    candidates: list[dict] = []
    product_only_candidates: list[dict] = []
    held: list[dict] = []
    matched_existing_variants = 0
    new_variant_candidates = 0
    product_only_count = 0
    exact_products = 0

    for bundle, strong_sources in qualifying:
        product = bundle["product"]
        product_name = str(product["globalName"]).strip()
        product_norm = norm(product_name)
        category = str((bundle.get("category") or {}).get("name") or "").strip()
        brand_name = str((bundle.get("brand") or {}).get("name") or "").strip()
        manufacturer_name = str(
            (bundle.get("brand") or {}).get("manufacturerName")
            or (bundle.get("manufacturer") or {}).get("name")
            or ""
        ).strip()
        aliases = [str(item).strip() for item in bundle.get("aliases", []) if str(item).strip()]
        variants = bundle.get("variants") or []

        measure_counts: Counter = Counter()
        for variant in variants:
            key = measure_key(build_pack(variant))
            if key is not None:
                measure_counts[key] += 1

        publishable_for_product = 0
        for index, variant in enumerate(variants, start=1):
            variant_name = str(variant.get("variantName") or "").strip()
            pack = build_pack(variant)
            if measure_key(pack) is None:
                held.append({
                    "source_ref": f"OFFICIAL:{product_name}:{index}",
                    "classification": "OFFICIAL_SOURCE_VARIANT_REVIEW",
                    "reason": "Reviewed research does not establish a precise numeric measure/pack for this variant; no detail was invented.",
                })
                continue

            supporting_sources = [
                source for source in strong_sources if source_supports_variant(source, product_name, variant)
            ]
            if not supporting_sources:
                held.append({
                    "source_ref": f"OFFICIAL:{product_name}:{variant_name}",
                    "classification": "OFFICIAL_SOURCE_VARIANT_REVIEW",
                    "reason": "No bounded authoritative source in this pass directly establishes this exact pack/variant; product-family evidence is not being stretched into a pack claim.",
                })
                continue

            best_source = max(supporting_sources, key=lambda source: source_score(source, product_name))
            source_id = str(best_source["id"])
            used_sources[source_id] = manifest_source(best_source, str(phase41.get("createdAt")))
            candidate = {
                "source_ref": f"OFFICIAL:{product_name}:{variant_name}",
                "classification": "CLASS_A_PUBLISH_OFFICIAL_SOURCE",
                "product": {
                    "canonical_name": product_name,
                    "category": category,
                    **({"brand": brand_name} if brand_name else {}),
                },
                "variant": {
                    "canonical_name": variant_name,
                    "pack_definition": pack,
                    "attributes": {"official_variant_label": variant_name},
                    "barcode": None,
                    "barcode_status": "PENDING_PHYSICAL_OR_GS1_VERIFICATION",
                },
                "aliases": [
                    {"display_text": alias, "alias_kind": "OFFICIAL_OR_RESEARCH_ALIAS", "source_key": source_id}
                    for alias in aliases
                ],
                "evidence": [
                    evidence(source_id, "canonical_name", product_name, "Official source establishes the canonical product identity."),
                    evidence(source_id, "variant_identity", variant_name, "Official source establishes this exact variant/pack."),
                    evidence(source_id, "pack_definition", json.dumps(pack, ensure_ascii=False, sort_keys=True), "Pack structure preserved from authoritative evidence."),
                    evidence(source_id, "market_presence_zambia", "Zambia", "Phase41 evidence scope and this publication pass establish Zambia relevance."),
                ],
                "decision_type": "INITIAL_OWNER_AUTHORIZED_PUBLICATION",
            }
            if brand_name:
                candidate["evidence"].append(evidence(source_id, "brand_identity", brand_name, "Official evidence establishes brand identity."))
            if manufacturer_name and brand_name:
                candidate["organization_relationship"] = {
                    "organization_name": manufacturer_name,
                    "relationship_type": "MANUFACTURER",
                    "source_key": source_id,
                }
                candidate["evidence"].append(evidence(source_id, "manufacturer_identity", manufacturer_name, "Official evidence establishes the manufacturer/brand-owner relationship used by this record."))

            match_id = choose_existing_variant(product_norm, pack, existing_variants.get(product_norm, []), measure_counts)
            if match_id:
                candidate["match_existing_variant_id"] = match_id
                matched_existing_variants += 1
            else:
                new_variant_candidates += 1

            candidates.append(candidate)
            publishable_for_product += 1

        if publishable_for_product:
            exact_products += 1
            continue

        # If the official sources establish the family but not an exact pack,
        # publish a family only when it is genuinely new and therefore cannot
        # conflict with an existing exact VAR lineage.
        ambiguous_family_markers = (
            "large bar", "small bar", "large bottle", "small bottle",
            "size to confirm", "variant unresolved", "variant 2", "multiple sizes",
        )
        family_is_clean = not any(marker in product_norm for marker in ambiguous_family_markers)
        if product_norm not in existing_products and family_is_clean:
            best_family_source = max(strong_sources, key=lambda source: source_score(source, product_name))
            source_id = str(best_family_source["id"])
            used_sources[source_id] = manifest_source(best_family_source, str(phase41.get("createdAt")))
            family = {
                "source_ref": f"OFFICIAL:{product_name}:PRODUCT_ONLY",
                "classification": "CLASS_B_PUBLISH_PRODUCT_HOLD_VARIANT",
                "product": {
                    "canonical_name": product_name,
                    "category": category,
                    **({"brand": brand_name} if brand_name else {}),
                },
                "aliases": [
                    {"display_text": alias, "alias_kind": "OFFICIAL_OR_RESEARCH_ALIAS", "source_key": source_id}
                    for alias in aliases
                ],
                "evidence": [
                    evidence(source_id, "canonical_name", product_name, "Authoritative official source establishes the product family."),
                    evidence(source_id, "market_presence_zambia", "Zambia", "Phase41 evidence establishes Zambia relevance; exact pack remains held."),
                ],
                "decision_type": "INITIAL_OWNER_AUTHORIZED_PUBLICATION",
            }
            if brand_name:
                family["evidence"].append(evidence(source_id, "brand_identity", brand_name, "Official evidence establishes brand identity."))
            if manufacturer_name and brand_name:
                family["organization_relationship"] = {
                    "organization_name": manufacturer_name,
                    "relationship_type": "MANUFACTURER",
                    "source_key": source_id,
                }
                family["evidence"].append(evidence(source_id, "manufacturer_identity", manufacturer_name, "Official evidence establishes manufacturer/brand-owner relationship."))
            product_only_candidates.append(family)
            product_only_count += 1
        else:
            held.append({
                "source_ref": f"OFFICIAL:{product_name}:PRODUCT_ONLY",
                "classification": "OFFICIAL_SOURCE_PRODUCT_ENRICHMENT_REVIEW",
                "reason": (
                    "Product-family publication was held because the normalized family name is itself pack/variant-like and needs cleanup before publication."
                    if not family_is_clean
                    else "Official evidence supports the product family, but the product already has exact variants; this pass does not replace or relabel those variants without exact-pack evidence."
                ),
            })

    used_source_ids = {item["source_key"] for candidate in candidates + product_only_candidates for item in candidate.get("evidence", [])}
    source_rows = [used_sources[source_id] for source_id in sorted(used_source_ids)]

    manifest = {
        "schema_version": "ncpc-initial-seed-manifest-v1",
        "source_fingerprint": hashlib.sha256(raw_bytes + args.database.read_bytes()).hexdigest(),
        "decision_type": "INITIAL_OWNER_AUTHORIZED_PUBLICATION",
        "actor_label": "NCPC official-source catalogue expansion / owner-authorized initial catalogue operation",
        "rationale": (
            "Expand the first NCPC catalogue using reviewed Zambia-relevant authoritative online evidence. "
            "Exact variants are published only when the bounded official source establishes the pack; broad official pages publish product families only. "
            "A missing barcode is not a publication blocker and no research GTIN is promoted by this pass."
        ),
        "sources": source_rows,
        "candidates": candidates,
        "product_only_candidates": product_only_candidates,
        "held_for_review": held,
        "summary": {
            "phase41_bundles_scanned": len(phase41.get("bundles", [])),
            "qualifying_official_exact_products": len(qualifying),
            "products_with_exact_variants": exact_products,
            "variant_candidates": len(candidates),
            "matched_existing_variants_for_enrichment": matched_existing_variants,
            "new_variant_candidates": new_variant_candidates,
            "product_only_candidates": product_only_count,
            "held_for_review": len(held),
            "source_count": len(source_rows),
            "barcodes_imported": 0,
            "validated_source_domains": sorted(DEFAULT_VALIDATED_DOMAINS),
        },
    }
    hash_input = {key: value for key, value in manifest.items() if key in {"schema_version", "source_fingerprint", "decision_type", "actor_label", "rationale", "sources", "candidates", "product_only_candidates", "held_for_review", "summary"}}
    manifest["manifest_hash"] = sha256_json(hash_input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"output": str(args.output), "manifest_hash": manifest["manifest_hash"], **manifest["summary"]}, indent=2))


if __name__ == "__main__":
    main()
