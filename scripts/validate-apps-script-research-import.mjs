import { readFile } from 'node:fs/promises';
import { resolve, basename } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const manifestPath = resolve(process.argv[2] || `${root}/research/ntheemba-central-catalogue-retail-zambia.json`);
const ledgerPath = process.argv[3] ? resolve(process.argv[3]) : resolve(`${root}/research/zambia-source-ledger.json`);
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
let externalLedger = null;
try {
  externalLedger = JSON.parse(await readFile(ledgerPath, 'utf8'));
} catch {
  externalLedger = null;
}

const errors = [];
const warnings = [];
const protectedFields = new Set([
  'sellingprice', 'price', 'extractedprice', 'cost', 'costprice', 'unitcost',
  'stock', 'currentstock', 'openingstock', 'availablequantity',
  'quantityremaining', 'quantityonhand', 'maxstock', 'reorderlevel',
  'supplier', 'supplierid', 'suppliername', 'preferredsupplier', 'batches',
  'inventorybatches', 'stockentries', 'stockadjustments', 'revenue',
  'expenses', 'sales', 'profit', 'profitmargin', 'margin', 'inventoryvalue',
]);
const requireText = (value, label) => {
  if (typeof value !== 'string' || !value.trim()) errors.push(`${label} is required.`);
};
const normal = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');

function scanProtected(value, label) {
  if (!value || typeof value !== 'object') return;
  if (Array.isArray(value)) {
    value.forEach((item, index) => scanProtected(item, `${label}[${index}]`));
    return;
  }
  for (const [key, child] of Object.entries(value)) {
    if (protectedFields.has(normal(key))) errors.push(`${label}.${key} is a protected TradeFlow/shop field and must not be in an NCC import bundle.`);
    scanProtected(child, `${label}.${key}`);
  }
}

function manifestSources() {
  if (Array.isArray(manifest.sources)) return new Set(manifest.sources.map((source) => source.id));
  if (externalLedger?.schemaVersion === 'zambia-catalogue-source-ledger-v1') {
    return new Set((externalLedger.sources || []).map((source) => source.id));
  }
  return new Set();
}

function validateBarcode(barcode, label) {
  const value = String(barcode.barcodeValue || '');
  if (!value) {
    if (barcode.verificationStatus && barcode.verificationStatus !== 'not_found') {
      warnings.push(`${label} blank barcode is marked ${barcode.verificationStatus}; importer will ignore blank barcode records.`);
    }
    return;
  }
  if (!/^[0-9]{8,14}$/.test(value) && !/^NTB/i.test(value)) {
    errors.push(`${label}.barcodeValue must be a numeric GTIN-like value or an NTB-generated value.`);
  }
  if (barcode.verificationStatus !== 'verified' && barcode.status === 'active') {
    warnings.push(`${label} is active but not verified; importer will keep it draft until physical/authoritative verification.`);
  }
}

if (manifest.schemaVersion !== 'apps-script-research-import-v1') errors.push('Unexpected import schemaVersion.');
if (!Array.isArray(manifest.bundles) || !manifest.bundles.length) errors.push('At least one import bundle is required.');
if (!manifest.market && manifest.country !== 'ZM') errors.push('Research manifest must specify market or country.');

const sources = manifestSources();
const names = new Set();
const sourceReferences = [];
let draftCount = 0;
let reviewedCount = 0;
let unverifiedCount = 0;
let barcodeCount = 0;
let mediaCount = 0;

for (const [index, bundle] of (manifest.bundles || []).entries()) {
  const at = `bundles[${index}]`;
  scanProtected(bundle, at);
  requireText(bundle.businessType?.name, `${at}.businessType.name`);
  requireText(bundle.category?.name, `${at}.category.name`);
  requireText(bundle.product?.globalName, `${at}.product.globalName`);
  requireText(bundle.product?.productType, `${at}.product.productType`);
  if (bundle.product?.status !== 'draft') errors.push(`${at} must import as draft, never directly as active.`);
  if (bundle.product?.verificationStatus === 'verified') errors.push(`${at} cannot enter NCC as verified from a bulk research manifest.`);
  if (bundle.product?.verificationStatus === 'reviewed') reviewedCount++;
  if (bundle.product?.verificationStatus === 'unverified') unverifiedCount++;
  if (bundle.product?.status === 'draft') draftCount++;
  const key = normal(`${bundle.category?.name}|${bundle.product?.globalName}`);
  if (names.has(key)) warnings.push(`${at} duplicates a product/category bundle; importer will skip the later duplicate.`);
  names.add(key);

  if (!Array.isArray(bundle.variants) || !bundle.variants.length) errors.push(`${at} needs at least one variant.`);
  for (const [variantIndex, variant] of (bundle.variants || []).entries()) {
    const variantAt = `${at}.variants[${variantIndex}]`;
    ['variantName', 'salesUnit', 'packagingType', 'inventoryType'].forEach((field) => requireText(variant[field], `${variantAt}.${field}`));
    if (variant.sizeValue !== undefined && variant.sizeValue !== '' && (typeof variant.sizeValue !== 'number' || variant.sizeValue <= 0)) {
      errors.push(`${variantAt}.sizeValue must be a positive number when provided.`);
    }
    if ((variant.sizeValue === undefined || variant.sizeValue === '' || variant.sizeValue === null) && !variant.sizeUnit) {
      warnings.push(`${variantAt} has no confirmed size; importer will keep the draft record for admin review.`);
    }
    for (const [barcodeIndex, barcode] of (variant.barcodes || []).entries()) {
      barcodeCount++;
      validateBarcode(barcode, `${variantAt}.barcodes[${barcodeIndex}]`);
    }
    for (const [mediaIndex, media] of (variant.media || []).entries()) {
      mediaCount++;
      if (media.sourceUrl && !/^https:/.test(media.sourceUrl)) errors.push(`${variantAt}.media[${mediaIndex}].sourceUrl must use HTTPS.`);
      if (media.status === 'active' && media.verificationStatus !== 'verified') warnings.push(`${variantAt}.media[${mediaIndex}] is active but not verified; importer will keep it draft.`);
    }
  }

  const bundleSourceIds = bundle.research?.sourceIds || [];
  if (!bundleSourceIds.length) errors.push(`${at} needs at least one research source ID.`);
  for (const id of bundleSourceIds) {
    sourceReferences.push(id);
    if (sources.size && !sources.has(id)) errors.push(`${at} references unknown source ${id}.`);
  }
  if (manifest.sources) {
    const gate = bundle.research?.publicationGate || '';
    if (!gate) warnings.push(`${at} has no research.publicationGate.`);
  } else if (!Array.isArray(bundle.sources) || !bundle.sources.length) {
    errors.push(`${at} needs product-level source records when the manifest has no top-level sources list.`);
  }
}

if (externalLedger?.schemaVersion === 'zambia-catalogue-source-ledger-v1') {
  for (const [index, source] of (externalLedger.sources || []).entries()) {
    const at = `sources[${index}]`;
    requireText(source.id, `${at}.id`);
    requireText(source.url, `${at}.url`);
    if (!/^https:/.test(source.url || '')) errors.push(`${at}.url must use HTTPS.`);
  }
}

const summary = {
  manifest: basename(manifestPath),
  bundles: manifest.bundles?.length || 0,
  draftCount,
  reviewedCount,
  unverifiedCount,
  sources: sources.size,
  sourceReferences: sourceReferences.length,
  barcodeCount,
  mediaCount,
  warnings: warnings.length,
};

if (errors.length) {
  console.error(`Research import validation failed (${errors.length}):\n- ${errors.join('\n- ')}`);
  if (warnings.length) console.error(`Warnings (${warnings.length}):\n- ${warnings.slice(0, 30).join('\n- ')}`);
  process.exitCode = 1;
} else {
  console.log(`Research import validation passed: ${JSON.stringify(summary)}`);
  if (warnings.length) console.log(`Warnings (${warnings.length}):\n- ${warnings.slice(0, 30).join('\n- ')}`);
}
