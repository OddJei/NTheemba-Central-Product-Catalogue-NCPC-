# Migration risks

| Risk | Evidence | Required handling before migration |
| --- | --- | --- |
| Duplicate/malformed PRD or VAR IDs | v2 and JSON prototype use different opaque/descriptive formats; no data extract inspected | Inventory every source ID, references and collisions; preserve a legacy-ID registry. |
| Barcode collision hidden by skip/reject | v2 save/import skips existing normalized identifier; queue rejects existing value | Import every claim, create conflict records, never silently choose a variant. |
| Leading zero/type loss | Sheets may coerce cells; code has no barcode-specific textual normalizer | Extract raw/display values, preserve original text, validate normalization separately. |
| Ambiguous alias ownership | `productId` and `variantId` are both optional in legacy rows | Quarantine rows with zero/both targets; obtain review decision. |
| Inconsistent lifecycle flags | `status`, verification, publication, review queue and candidate statuses are independent | Derive an auditable migration state; do not infer published from any one field. |
| Orphan records | Sheet rows lack enforced foreign keys | Detect missing Product, Variant, Brand, Category, Source and Release references. |
| Incomplete pack facts | Existing size/unit/packaging fields are optional and ambiguous | Retain display text and mark structured extraction confidence; do not invent measures. |
| Broken TradeFlow mappings | Local mapping expects valid PRD/VAR pair and release version | Reconcile by IDs, retain unmapped/error states, never match by name automatically. |
| Release non-reproducibility | Current export rebuilds live state | Capture or regenerate a signed immutable snapshot before consumer migration. |
| Tenant-data contamination | Import guards reject protected fields but historical payloads may contain them | Classify/redact/quarantine before ingestion; NCPC must not persist business facts. |

No production migration is authorized by this document.
