import { readFile } from 'node:fs/promises';
import { basename, resolve } from 'node:path';

const files = process.argv.slice(2).map((file) => resolve(file));
if (!files.length) {
  console.error('Usage: node scripts/simulate-apps-script-import.mjs <manifest.json> [manifest.json...]');
  process.exit(1);
}

const protectedFields = new Set([
  'sellingprice', 'price', 'extractedprice', 'cost', 'costprice', 'unitcost',
  'stock', 'currentstock', 'openingstock', 'availablequantity',
  'quantityremaining', 'quantityonhand', 'maxstock', 'reorderlevel',
  'supplier', 'supplierid', 'suppliername', 'preferredsupplier', 'batches',
  'inventorybatches', 'stockentries', 'stockadjustments', 'revenue',
  'expenses', 'sales', 'profit', 'profitmargin', 'margin', 'inventoryvalue',
]);
const key = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');

function scanProtected(value, path, errors) {
  if (!value || typeof value !== 'object') return;
  if (Array.isArray(value)) {
    value.forEach((item, index) => scanProtected(item, `${path}[${index}]`, errors));
    return;
  }
  for (const [name, child] of Object.entries(value)) {
    if (protectedFields.has(key(name))) errors.push(`${path}.${name}`);
    scanProtected(child, `${path}.${name}`, errors);
  }
}

function normalizeBundle(bundle) {
  const product = bundle.product || {};
  const variants = (bundle.variants || []).map((variant) => ({
    variantName: variant.variantName,
    status: 'draft',
    barcodes: (variant.barcodes || [])
      .filter((barcode) => String(barcode?.barcodeValue || '').trim())
      .map((barcode) => ({
        barcodeValue: barcode.barcodeValue,
        verificationStatus: barcode.verificationStatus || 'unverified',
        status: 'draft',
      })),
    media: (variant.media || [])
      .filter((media) => String(media?.sourceUrl || '').trim())
      .map((media) => ({
        sourceUrl: media.sourceUrl,
        verificationStatus: media.verificationStatus || 'unverified',
        status: 'draft',
      })),
  }));
  return {
    globalName: product.globalName,
    categoryName: bundle.category?.name || '',
    status: 'draft',
    verificationStatus: product.verificationStatus === 'reviewed' || product.verificationStatus === 'verified' ? 'reviewed' : 'unverified',
    publicationGate: bundle.research?.publicationGate || '',
    barcodeStatus: bundle.research?.barcodeStatus || '',
    variants,
    aliases: bundle.aliases || [],
  };
}

const globalSeen = new Map();
for (const file of files) {
  const manifest = JSON.parse(await readFile(file, 'utf8'));
  const sources = new Set((manifest.sources || []).map((source) => source.id));
  const localSeen = new Map();
  const summary = {
    file: basename(file),
    schemaVersion: manifest.schemaVersion,
    manifestId: manifest.manifestId || '',
    bundles: 0,
    wouldImport: 0,
    localDuplicates: 0,
    crossManifestDuplicates: 0,
    variants: 0,
    aliases: 0,
    barcodes: 0,
    draftBarcodes: 0,
    media: 0,
    draftMedia: 0,
    reviewedProducts: 0,
    unverifiedProducts: 0,
    protectedFieldErrors: 0,
    missingSourceErrors: 0,
    gates: {},
  };
  for (const [index, bundle] of (manifest.bundles || []).entries()) {
    const protectedPaths = [];
    scanProtected(bundle, `bundles[${index}]`, protectedPaths);
    summary.protectedFieldErrors += protectedPaths.length;
    for (const sourceId of bundle.research?.sourceIds || []) {
      if (sources.size && !sources.has(sourceId)) summary.missingSourceErrors++;
    }
    const normalized = normalizeBundle(bundle);
    summary.bundles++;
    summary.variants += normalized.variants.length;
    summary.aliases += normalized.aliases.length;
    if (normalized.verificationStatus === 'reviewed') summary.reviewedProducts++;
    if (normalized.verificationStatus === 'unverified') summary.unverifiedProducts++;
    summary.gates[normalized.publicationGate || '(blank)'] = (summary.gates[normalized.publicationGate || '(blank)'] || 0) + 1;
    for (const variant of normalized.variants) {
      summary.barcodes += variant.barcodes.length;
      summary.draftBarcodes += variant.barcodes.filter((barcode) => barcode.status === 'draft').length;
      summary.media += variant.media.length;
      summary.draftMedia += variant.media.filter((media) => media.status === 'draft').length;
    }
    const productKey = key(`${normalized.categoryName}|${normalized.globalName}`);
    if (localSeen.has(productKey)) {
      summary.localDuplicates++;
      continue;
    }
    if (globalSeen.has(productKey)) {
      summary.crossManifestDuplicates++;
      localSeen.set(productKey, true);
      continue;
    }
    localSeen.set(productKey, true);
    globalSeen.set(productKey, file);
    summary.wouldImport++;
  }
  console.log(JSON.stringify(summary, null, 2));
}
