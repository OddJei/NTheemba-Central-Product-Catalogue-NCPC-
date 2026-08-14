import { access, rm } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createCandidate, readCatalogue, reviewVariant } from '../server.mjs';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const dataFile = join(root, 'data', 'catalogue-v1.json');
try {
  try { await access(dataFile); throw Error('Remove data/catalogue-v1.json before running the isolated API smoke test.'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const before = await readCatalogue();
  const candidate = await createCandidate({
    product_name: 'Validation Tea', variant_name: 'Validation Tea 250 ml bottle',
    category_id: 'CAT-RETAIL-BEVERAGES', inventory_type: 'packaged', unit: 'ml', size: 250,
    barcode: 'NTH-VALIDATION-TEA-250ML'
  });
  await reviewVariant(candidate.variant_id, 'approve');
  const after = await readCatalogue();
  const variant = after.variants.find(item => item.id === candidate.variant_id);
  if (after.products.length !== before.products.length + 1 || variant?.status !== 'published') throw Error('Candidate review workflow failed.');
  console.log(`API smoke test passed: ${candidate.variant_id}`);
} finally {
  await rm(dataFile, { force: true });
}
