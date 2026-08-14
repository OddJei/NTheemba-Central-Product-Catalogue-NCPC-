import { readFile, readdir } from 'node:fs/promises';
import { basename, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(import.meta.dirname, '..');
const SEED_DIR = resolve(ROOT, 'seeds');
const ID = /^[A-Z]{2,8}-[A-Z0-9-]+$/;
const PREFIX = {
  business_types: 'BT-', categories: 'CAT-', manufacturers: 'MFG-', brands: 'BRD-',
  products: 'PRD-', variants: 'VAR-', barcodes: 'BAR-', media: 'MED-'
};

function fail(errors, file, message) { errors.push(`${basename(file)}: ${message}`); }
function required(value) { return typeof value === 'string' ? value.trim().length > 0 : value !== undefined && value !== null; }
function index(records, key) { return new Set((records || []).map((record) => record.id)); }

export function validateCatalogue(document, file = 'catalogue.json') {
  const errors = [];
  if (!document || typeof document !== 'object' || Array.isArray(document)) return [`${basename(file)}: root must be an object`];
  if (document.schema_version !== '1.0') fail(errors, file, 'schema_version must be 1.0');
  if (!/^CATALOG-[A-Z0-9-]+$/.test(document.catalogue_id || '')) fail(errors, file, 'catalogue_id must start with CATALOG-');
  for (const collection of Object.keys(PREFIX)) {
    if (!Array.isArray(document[collection])) { fail(errors, file, `${collection} must be an array`); continue; }
    const ids = new Set();
    for (const [position, record] of document[collection].entries()) {
      const label = `${collection}[${position}]`;
      if (!record || typeof record !== 'object') { fail(errors, file, `${label} must be an object`); continue; }
      if (!ID.test(record.id || '') || !record.id.startsWith(PREFIX[collection])) fail(errors, file, `${label}.id must use ${PREFIX[collection]}`);
      if (ids.has(record.id)) fail(errors, file, `duplicate ${collection} id ${record.id}`);
      ids.add(record.id);
    }
  }
  const businessTypes = index(document.business_types);
  const categories = index(document.categories);
  const manufacturers = index(document.manufacturers);
  const brands = index(document.brands);
  const products = index(document.products);
  const variants = index(document.variants);
  const media = index(document.media);
  const checkRef = (value, allowed, label) => { if (!allowed.has(value)) fail(errors, file, `${label} references missing ID ${value}`); };
  for (const [i, r] of (document.categories || []).entries()) {
    if (!required(r.name) || !required(r.status)) fail(errors, file, `categories[${i}] requires name and status`);
    checkRef(r.business_type_id, businessTypes, `categories[${i}].business_type_id`);
    if (r.parent_category_id) checkRef(r.parent_category_id, categories, `categories[${i}].parent_category_id`);
  }
  for (const [i, r] of (document.brands || []).entries()) checkRef(r.manufacturer_id, manufacturers, `brands[${i}].manufacturer_id`);
  for (const [i, r] of (document.products || []).entries()) {
    if (!required(r.name) || !required(r.status)) fail(errors, file, `products[${i}] requires name and status`);
    checkRef(r.business_type_id, businessTypes, `products[${i}].business_type_id`);
    checkRef(r.category_id, categories, `products[${i}].category_id`);
    if (r.brand_id) checkRef(r.brand_id, brands, `products[${i}].brand_id`);
  }
  for (const [i, r] of (document.variants || []).entries()) {
    if (!required(r.name) || !required(r.status) || !required(r.unit)) fail(errors, file, `variants[${i}] requires name, status and unit`);
    if (!['packaged', 'weight_based', 'volume_based', 'piece_based'].includes(r.inventory_type)) fail(errors, file, `variants[${i}].inventory_type is invalid`);
    if (r.size !== undefined && (!(typeof r.size === 'number') || r.size <= 0)) fail(errors, file, `variants[${i}].size must be a positive number`);
    checkRef(r.product_id, products, `variants[${i}].product_id`);
    if (r.media_id) checkRef(r.media_id, media, `variants[${i}].media_id`);
  }
  const barcodeValues = new Set();
  for (const [i, r] of (document.barcodes || []).entries()) {
    checkRef(r.variant_id, variants, `barcodes[${i}].variant_id`);
    if (!required(r.value)) fail(errors, file, `barcodes[${i}].value is required`);
    if (barcodeValues.has(r.value)) fail(errors, file, `duplicate barcode value ${r.value}`);
    barcodeValues.add(r.value);
    if (!['manufacturer', 'ntheemba_generated'].includes(r.kind)) fail(errors, file, `barcodes[${i}].kind is invalid`);
    if (!['EAN_13', 'EAN_8', 'UPC_A', 'CODE_128', 'QR'].includes(r.symbology)) fail(errors, file, `barcodes[${i}].symbology is invalid`);
    if (r.kind === 'ntheemba_generated' && !r.value.startsWith('NTH-')) fail(errors, file, `barcodes[${i}] generated values must start with NTH-`);
  }
  return errors;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const input = process.argv.slice(2);
  const paths = input.length ? input.map((path) => resolve(process.cwd(), path)) : (await readdir(SEED_DIR)).filter((name) => name.endsWith('.json')).map((name) => resolve(SEED_DIR, name));
  let errors = [];
  for (const file of paths) {
    try { errors = errors.concat(validateCatalogue(JSON.parse(await readFile(file, 'utf8')), file)); }
    catch (error) { errors.push(`${basename(file)}: ${error.message}`); }
  }
  if (errors.length) { console.error(`Catalog validation failed (${errors.length} error${errors.length === 1 ? '' : 's'}):\n- ${errors.join('\n- ')}`); process.exitCode = 1; }
  else console.log(`Catalog validation passed for ${paths.length} document${paths.length === 1 ? '' : 's'}.`);
}
