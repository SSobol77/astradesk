#!/usr/bin/env tsx
import { existsSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const specPath = join(root, 'openapi', 'OpenAPI.yaml');

if (!existsSync(specPath)) {
  console.error('openapi/OpenAPI.yaml is missing. Add the source specification before generating.');
  process.exit(1);
}

const specMtime = statSync(specPath).mtime.toISOString();

console.log('OpenAPI generation placeholder');
console.log('--------------------------------');
console.log('Spec path:', specPath);
console.log('Last modified:', specMtime);
console.log('TODO: integrate OpenAPI code generation pipeline here.');
