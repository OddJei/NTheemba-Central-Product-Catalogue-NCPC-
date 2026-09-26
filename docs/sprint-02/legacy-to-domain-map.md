# Legacy-to-domain map

| Legacy concept | Final concept | Action |
| --- | --- | --- |
| v2 `Products` row | Product | Migrate after ID/reference audit |
| v2 `ProductVariants` row | Variant + PackDefinition | Migrate structured fields; retain display text |
| v2/JSON identifier or barcode row | Barcode claim | Migrate with original text/provenance; conflict-check |
| `ProductAliases` row | Alias | Normalize and require one target/approval decision |
| `Brands`, organization relationships | Brand + optional organization provenance | Retain concept; remove duplicate spelling safely |
| `Categories`, domains/business types | Category taxonomy assignment | Reconcile taxonomy, do not copy TradeFlow categories |
| `ProductCandidates` raw payload | Submission + ProposedChange | Transform; preserve raw payload as audit attachment |
| `ReviewQueue` / barcode queue | Review work projection + decisions | Migrate decisions/history, not merely queue state |
| `CatalogueEvidence`/sources | Provenance and audit evidence | Retain with claim-level links |
| `CatalogueReleases`/`ReleaseItems` | PublicationSnapshot | Rebuild immutable snapshot payload where possible |
| JSON `catalog-v1`/seed records | Legacy import source | Preserve source and IDs; no automatic identity coalescing |
| TradeFlow `ncpcMapping` | BusinessCoverage candidate + adapter mapping | Reconcile only after both IDs verify; TradeFlow remains source for its link |
| `NcpcPublishedCatalogue` | Consumer cache | Retain temporarily behind adapter; not migrated as authority |

Rows that are malformed, orphaned, ambiguous, conflicting or contain protected
TradeFlow fields must be quarantined with a decision record, not silently cleaned.
