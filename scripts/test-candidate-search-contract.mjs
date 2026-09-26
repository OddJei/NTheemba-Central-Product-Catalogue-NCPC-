import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const sourcePath = join(root, 'Apps Script', 'Code.gs');
const source = await readFile(sourcePath, 'utf8');
const context = { Logger: { log() {} }, console, isFinite };
vm.createContext(context);
vm.runInContext(source, context, { filename: sourcePath });

const records = {
  Products: [
    { id: 'PRD-COCA', canonicalName: 'Coca-Cola', brandId: 'BRD-COCA', publicationStatus: 'published', status: 'active', sellingPrice: 99, stock: 8, supplierName: 'Private supplier' },
    { id: 'PRD-DRAFT', canonicalName: 'Draft Cola', brandId: '', publicationStatus: 'draft', status: 'active' }
  ],
  ProductVariants: [
    { id: 'VAR-COCA-500', productId: 'PRD-COCA', variantName: '500 ml bottle', sizeValue: 500, sizeUnit: 'ml', salesUnit: 'bottle', publicationStatus: 'published', status: 'active' },
    { id: 'VAR-COCA-330', productId: 'PRD-COCA', variantName: '330 ml can', sizeValue: 330, sizeUnit: 'ml', salesUnit: 'can', publicationStatus: 'published', status: 'active' },
    { id: 'VAR-UNPUBLISHED', productId: 'PRD-COCA', variantName: '2 L bottle', sizeValue: 2, sizeUnit: 'l', salesUnit: 'bottle', publicationStatus: 'draft', status: 'active' },
    { id: 'VAR-DRAFT', productId: 'PRD-DRAFT', variantName: '500 ml bottle', sizeValue: 500, sizeUnit: 'ml', salesUnit: 'bottle', publicationStatus: 'published', status: 'active' }
  ],
  Identifiers: [
    { id: 'IDN-COCA', variantId: 'VAR-COCA-500', identifierType: 'EAN13', identifierValue: '5449000000996', isPrimary: true, status: 'active' },
    { id: 'IDN-UNPUBLISHED', variantId: 'VAR-UNPUBLISHED', identifierType: 'EAN13', identifierValue: '2222222222222', isPrimary: true, status: 'active' },
    { id: 'IDN-DRAFT', variantId: 'VAR-DRAFT', identifierType: 'EAN13', identifierValue: '9999999999999', isPrimary: true, status: 'active' }
  ],
  ProductAliases: [
    { id: 'ALS-COCA', productId: 'PRD-COCA', variantId: '', alias: 'Coke', status: 'active' },
    { id: 'ALS-DRAFT', productId: 'PRD-DRAFT', variantId: '', alias: 'Draft Coke', status: 'active' }
  ],
  Brands: [{ id: 'BRD-COCA', name: 'Coca-Cola', status: 'active' }]
};

context.initializeNcpcSystem = () => ({ success: true });
context.rows_ = table => records[table] || [];
context.getCatalogueVersion_ = () => 42;
context.nowIso_ = () => '2026-08-22T00:00:00.000Z';
context.ContentService = {
  MimeType: { JSON: 'application/json' },
  createTextOutput(text) { return { text, setMimeType() { return this; } }; }
};

function search(query, options) {
  return context.findNcpcCandidates(query, options || {});
}

const barcode = search('5449000000996', { barcodeOnly: true });
assert.equal(barcode.success, true);
assert.equal(barcode.data.candidates[0].variantId, 'VAR-COCA-500');
assert.ok(barcode.data.candidates[0].matchReasons.includes('identifier_exact'));

const typo = search('cokee');
assert.equal(typo.success, true);
assert.equal(typo.data.candidates[0].variantId, 'VAR-COCA-500');
assert.ok(typo.data.candidates[0].matchReasons.includes('fuzzy_spelling_match'));

const alias = search('Coke');
assert.equal(alias.success, true);
assert.ok(alias.data.candidates.some(candidate => candidate.matchReasons.includes('alias_exact')));

const sizeMismatch = search('Coke 1 L');
assert.equal(sizeMismatch.success, true);
assert.ok(sizeMismatch.data.candidates.every(candidate => candidate.warnings.includes('Requested size does not match this variant.')));

const draft = search('9999999999999', { barcodeOnly: true });
assert.equal(draft.success, true);
assert.equal(draft.data.status, 'no_match');
assert.equal(draft.data.candidates.length, 0);

const unpublishedVariant = search('2222222222222', { barcodeOnly: true });
assert.equal(unpublishedVariant.success, true);
assert.equal(unpublishedVariant.data.status, 'no_match');
assert.equal(unpublishedVariant.data.candidates.length, 0);

const empty = search('');
assert.equal(empty.success, true);
assert.equal(empty.data.status, 'no_match');
assert.equal(empty.data.candidates.length, 0);

const noMatch = search('unlisted item');
assert.equal(noMatch.success, true);
assert.equal(noMatch.data.status, 'no_match');
assert.equal(noMatch.data.candidates.length, 0);

context.rows_ = () => { throw new Error('Spreadsheet secret detail'); };
const safeFailure = search('Coke');
assert.equal(safeFailure.success, false);
assert.equal(safeFailure.errorCode, 'CANDIDATE_SEARCH_FAILED');
assert.equal(safeFailure.message, 'Candidate search is temporarily unavailable.');
assert.equal(safeFailure.data.status, 'error');
assert.equal(safeFailure.data.contractVersion, 'ncpc-candidate-search-v1');
assert.ok(!safeFailure.message.includes('secret'));
context.rows_ = table => records[table] || [];

const invalidLimit = search('Coke', { limit: 'not-a-number' });
assert.equal(invalidLimit.success, true);
assert.ok(invalidLimit.data.candidates.length > 0);

const contract = search('Coke');
assert.equal(contract.data.contractVersion, 'ncpc-candidate-search-v1');
assert.equal(contract.data.catalogueVersion, 42);
assert.equal(contract.catalogueVersion, 42);
assert.ok(contract.data.candidates.every(candidate => ['productId', 'variantId', 'canonicalName', 'variantName', 'confidence', 'matchReasons', 'warnings', 'score'].every(key => key in candidate)));
assert.ok(contract.data.candidates.every(candidate => !('sellingPrice' in candidate) && !('stock' in candidate) && !('supplierName' in candidate)));
assert.ok(contract.data.candidates.filter(candidate => candidate.productId === 'PRD-COCA').length <= 2);

context.initializeNcpcSystem = () => { throw new Error('Spreadsheet authorization detail'); };
const routeFailure = context.handleNcpcReadApi_({ parameter: { q: 'Coke' } }, 'candidates');
const routeFailurePayload = JSON.parse(routeFailure.text);
assert.equal(routeFailurePayload.success, false);
assert.equal(routeFailurePayload.errorCode, 'CANDIDATE_SEARCH_FAILED');
assert.equal(routeFailurePayload.message, 'Candidate search is temporarily unavailable.');
assert.equal(routeFailurePayload.data.status, 'error');
assert.ok(!routeFailurePayload.message.includes('authorization'));
context.initializeNcpcSystem = () => ({ success: true });

let publicOptions;
context.findNcpcCandidates = (_query, options) => {
  publicOptions = options;
  return { success: true, data: { contractVersion: 'ncpc-candidate-search-v1', status: 'ok', candidates: [] } };
};
const publicRoute = context.handleNcpcReadApi_({ parameter: { q: 'Coke', publishedOnly: 'false', activeOnly: 'false' } }, 'candidates');
assert.equal(JSON.parse(publicRoute.text).success, true);
assert.deepEqual({ ...publicOptions }, { limit: undefined, publishedOnly: true, activeOnly: true });

console.log('Candidate search contract tests passed: barcode, alias/typo, size warning, draft/unpublished exclusion, no-match, safe errors, invalid limit, schema/version, private-field exclusion, public filters, diversity.');
