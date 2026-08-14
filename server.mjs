/** Local development API for the Central Catalogue. Not a production deployment. */
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { dirname, extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateCatalogue } from './scripts/validate-catalog.mjs';

const root = dirname(fileURLToPath(import.meta.url));
const dataFile = join(root, 'data', 'catalogue-v1.json');
const seedDir = join(root, 'seeds');
const json = (res, status, value) => { res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(value)); };
const idFor = (prefix, value) => `${prefix}-${value.toUpperCase().replace(/[^A-Z0-9]+/g, '-').replace(/(^-|-$)/g, '').slice(0, 42)}-${Date.now().toString(36).toUpperCase()}`;
const uniqueById = (records) => [...new Map(records.map(record => [record.id, record])).values()];

async function exists(path) { try { await access(path); return true; } catch { return false; } }
export async function readCatalogue() {
  if (await exists(dataFile)) return JSON.parse(await readFile(dataFile, 'utf8'));
  const files = ['retail-grocery-v1.json', 'salon-beauty-v1.json'];
  const seeds = await Promise.all(files.map(async file => JSON.parse(await readFile(join(seedDir, file), 'utf8'))));
  const fields = ['business_types', 'categories', 'manufacturers', 'brands', 'products', 'variants', 'barcodes', 'media'];
  return Object.fromEntries([
    ['schema_version', '1.0'], ['catalogue_id', 'CATALOG-NTHEEMBA-LOCAL-01'], ['status', 'review'],
    ...fields.map(field => [field, uniqueById(seeds.flatMap(seed => seed[field] || []))])
  ]);
}
export async function saveCatalogue(catalogue) { const errors = validateCatalogue(catalogue, dataFile); if (errors.length) throw Error(`Catalog validation failed: ${errors.join('; ')}`); await mkdir(dirname(dataFile), { recursive: true }); await writeFile(dataFile, `${JSON.stringify(catalogue, null, 2)}\n`, 'utf8'); }
function findDuplicate(catalogue, value) {
  const normal = text => text.toLowerCase().replace(/[^a-z0-9]+/g, '');
  return catalogue.products.some(product => product.category_id === value.category_id && normal(product.name) === normal(value.product_name)) ||
    catalogue.variants.some(variant => normal(variant.name) === normal(value.variant_name)) ||
    (value.barcode && catalogue.barcodes.some(barcode => barcode.value === value.barcode));
}
export async function createCandidate(value) {
  const catalogue = await readCatalogue();
  const category = catalogue.categories.find(item => item.id === value.category_id);
  if (!category || !value.product_name?.trim() || !value.variant_name?.trim() || !value.unit?.trim()) throw Error('Product name, variant name, category, and unit are required.');
  if (findDuplicate(catalogue, value)) throw Error('A possible duplicate already exists.');
  const productId = idFor('PRD', value.product_name), variantId = idFor('VAR', value.variant_name);
  catalogue.products.push({ id: productId, name: value.product_name.trim(), business_type_id: category.business_type_id, category_id: category.id, status: 'review', description: 'Submitted for catalog review.' });
  catalogue.variants.push({ id: variantId, name: value.variant_name.trim(), product_id: productId, inventory_type: value.inventory_type || 'packaged', unit: value.unit.trim(), status: 'review', ...(value.size ? { size: Number(value.size) } : {}) });
  if (value.barcode?.trim()) catalogue.barcodes.push({ id: idFor('BAR', value.barcode), variant_id: variantId, value: value.barcode.trim(), kind: value.barcode.startsWith('NTH-') ? 'ntheemba_generated' : 'manufacturer', symbology: value.barcode.startsWith('NTH-') ? 'CODE_128' : 'EAN_13', verification_status: 'unverified' });
  await saveCatalogue(catalogue); return { product_id: productId, variant_id: variantId, status: 'review' };
}
export async function reviewVariant(variantId, action) {
  if (!['approve', 'reject'].includes(action)) throw Error('Action must be approve or reject.');
  const catalogue = await readCatalogue(), variant = catalogue.variants.find(item => item.id === variantId);
  if (!variant) throw Error('Variant not found.');
  variant.status = action === 'approve' ? 'published' : 'retired';
  const product = catalogue.products.find(item => item.id === variant.product_id); if (product) product.status = variant.status;
  await saveCatalogue(catalogue); return variant;
}
function staticFile(pathname) { const cleaned = normalize(pathname === '/' ? 'index.html' : pathname.slice(1)); return cleaned.startsWith('..') ? null : join(root, cleaned); }
const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    if (req.method === 'GET' && url.pathname === '/api/catalogue') return json(res, 200, await readCatalogue());
    if (req.method === 'GET' && url.pathname === '/api/search') { const catalogue = await readCatalogue(), q = (url.searchParams.get('q') || url.searchParams.get('barcode') || '').toLowerCase(); const matching = catalogue.variants.filter(v => [v.id, v.name, ...(catalogue.barcodes.filter(b => b.variant_id === v.id).map(b => b.value))].join(' ').toLowerCase().includes(q)); return json(res, 200, { results: matching }); }
    if (req.method === 'POST' && url.pathname === '/api/candidates') { let body = ''; for await (const chunk of req) body += chunk; return json(res, 201, await createCandidate(JSON.parse(body))); }
    const review = url.pathname.match(/^\/api\/variants\/([^/]+)\/review$/); if (req.method === 'POST' && review) { let body = ''; for await (const chunk of req) body += chunk; return json(res, 200, await reviewVariant(decodeURIComponent(review[1]), JSON.parse(body).action)); }
    if (req.method === 'GET') { const file = staticFile(url.pathname); if (!file) return json(res, 404, { error: 'Not found' }); const type = extname(file) === '.html' ? 'text/html; charset=utf-8' : extname(file) === '.json' ? 'application/json; charset=utf-8' : 'text/plain; charset=utf-8'; res.writeHead(200, { 'content-type': type }); return res.end(await readFile(file)); }
    return json(res, 404, { error: 'Not found' });
  } catch (error) { return json(res, error instanceof SyntaxError ? 400 : 422, { error: error.message }); }
});
if (process.argv[1] === fileURLToPath(import.meta.url)) server.listen(process.env.PORT || 4173, () => console.log('Central Catalogue running at http://localhost:4173'));
export { server };
