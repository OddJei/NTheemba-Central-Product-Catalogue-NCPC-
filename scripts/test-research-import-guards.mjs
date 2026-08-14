import assert from 'node:assert/strict';

const protectedFields = new Set([
  'sellingprice', 'price', 'extractedprice', 'cost', 'costprice', 'unitcost',
  'stock', 'currentstock', 'openingstock', 'availablequantity',
  'quantityremaining', 'quantityonhand', 'maxstock', 'reorderlevel',
  'supplier', 'supplierid', 'suppliername', 'preferredsupplier', 'batches',
  'inventorybatches', 'stockentries', 'stockadjustments', 'revenue',
  'expenses', 'sales', 'profit', 'profitmargin', 'margin', 'inventoryvalue',
]);
const key = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');

function protectedPaths(value, path = 'bundle', paths = []) {
  if (!value || typeof value !== 'object') return paths;
  if (Array.isArray(value)) {
    value.forEach((item, index) => protectedPaths(item, `${path}[${index}]`, paths));
    return paths;
  }
  for (const [name, child] of Object.entries(value)) {
    if (protectedFields.has(key(name))) paths.push(`${path}.${name}`);
    protectedPaths(child, `${path}.${name}`, paths);
  }
  return paths;
}

function clampResearchBundle(bundle) {
  const product = bundle.product || {};
  return {
    status: 'draft',
    verificationStatus: product.verificationStatus === 'reviewed' || product.verificationStatus === 'verified' ? 'reviewed' : 'unverified',
    variants: (bundle.variants || []).map((variant) => ({
      status: 'draft',
      barcodes: (variant.barcodes || []).map((barcode) => ({ ...barcode, status: 'draft' })),
      media: (variant.media || []).map((media) => ({ ...media, status: 'draft' })),
    })),
  };
}

const unsafe = {
  product: { globalName: 'Unsafe Product', selling_price: 10, maxStock: 50 },
  variants: [
    {
      variantName: 'Unsafe Product 1 pack',
      unit_cost: 4,
      supplier_id: 'SUP-1',
      available_quantity: 9,
      inventoryBatches: [],
    },
  ],
};
assert.deepEqual(protectedPaths(unsafe), [
  'bundle.product.selling_price',
  'bundle.product.maxStock',
  'bundle.variants[0].unit_cost',
  'bundle.variants[0].supplier_id',
  'bundle.variants[0].available_quantity',
  'bundle.variants[0].inventoryBatches',
]);

const clamped = clampResearchBundle({
  product: { globalName: 'Reviewed Product', status: 'active', verificationStatus: 'verified' },
  variants: [
    {
      variantName: 'Reviewed Product 1 pack',
      status: 'active',
      barcodes: [{ barcodeValue: '6000000000000', status: 'active', verificationStatus: 'verified' }],
      media: [{ sourceUrl: 'https://example.test/image.jpg', status: 'active', verificationStatus: 'verified' }],
    },
  ],
});
assert.equal(clamped.status, 'draft');
assert.equal(clamped.verificationStatus, 'reviewed');
assert.equal(clamped.variants[0].status, 'draft');
assert.equal(clamped.variants[0].barcodes[0].status, 'draft');
assert.equal(clamped.variants[0].media[0].status, 'draft');

console.log('Research import guard tests passed: protected fields reject and research statuses clamp to draft.');
