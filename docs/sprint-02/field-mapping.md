# Legacy field mapping

| Legacy field(s) | Current meaning/storage | Proposed domain concept | Preserve? | Notes |
| --- | --- | --- | --- | --- |
| `Products.id` / `ProductVariants.id` | v2 `PRD-*`/`VAR-*`, generated sequences | ProductId / VariantId | Yes | Stable opaque identity; never derive from name. |
| JSON `products.id`, `variants.id` | Older descriptive IDs | LegacyIdentityReference | Migrate with mapping | Do not assume equivalent formatting. |
| `canonicalName`, `variantName` | v2 display identity labels | Product.canonicalName, Variant.canonicalName | Yes | Normalize separately for search/duplicate signals. |
| `catalogueDomainId`, `categoryId`, JSON business type | Classification | CategoryAssignment | Redesign | NCPC taxonomy must not become TradeFlow reporting taxonomy. |
| `brandId`, Brands/Organizations | Brand and relationship records | Brand reference | Yes, simplify | Brand is controlled identity; manufacturer relation remains optional. |
| `sizeValue`, `sizeUnit`, `salesUnit`, `packagingType`, `inventoryType` | Variant physical clues | PackDefinition + Variant attributes | Redesign | Add count/inner measure/display text; no lone free-text size. |
| `Identifiers.identifierValue/type/isPrimary/sourceId` | Variant identifier | Barcode claim | Redesign | Text-preserving normalized value, symbology, source, verification and conflict state. |
| JSON `barcodes.value/kind/symbology` | Older barcode record | Barcode provenance/symbology | Preserve concept | Generated is provenance, never replacement for scanned value. |
| `ProductAliases.alias/productId/variantId/type/language` | Search alias | Alias | Redesign | Exactly one target; approved state and normalized uniqueness. |
| `verificationStatus`, `publicationStatus`, `status` | Independent mutable flags | Entity lifecycle + publication policy | Redesign | Replace contradictory booleans/flags with transition rules. |
| `ProductCandidates.rawPayload` | Small raw submission payload | Submission + ProposalChange | Redesign | Structured proposed changes, target, source and immutable review history. |
| `ReviewQueue`, `BarcodeVerificationQueue` | Work queues | Review / ReviewerDecision | Preserve concept | Queue is a projection, not authoritative lifecycle. |
| `InformationSources`, `CatalogueEvidence` | Source/evidence | Provenance + AuditEvent | Preserve concept | Attribute-level provenance where needed. |
| `CatalogueReleases`, `ReleaseItems` | Release with references | PublicationSnapshot | Redesign | Immutable payload/content hash, not only entity versions. |
| TradeFlow `ncpcMapping` | Per-business local link/version/public flag | BusinessCoverage reference | Adapter/migrate | TradeFlow retains local mapping; NCPC later records only association facts. |
| TradeFlow `NcpcPublishedCatalogue` | Loaded approved-release cache | Consumer cache | Deprecate as authority | May remain an adapter until future sync is approved. |
