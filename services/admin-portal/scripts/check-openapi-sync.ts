#!/usr/bin/env tsx
import { existsSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const specPath = join(root, 'openapi', 'OpenAPI.yaml');
const generatedFiles = [
  join(root, 'openapi', 'openapi-types.d.ts'),
  join(root, 'openapi', 'openapi-client.ts'),
  join(root, 'openapi', 'paths-map.ts'),
];

if (!existsSync(specPath)) {
  console.error('OpenAPI specification not found at openapi/OpenAPI.yaml');
  process.exit(1);
}

const stale = generatedFiles.filter((file) => {
  if (!existsSync(file)) {
    console.error(`Generated file missing: ${file}`);
    return true;
  }
  const specTime = statSync(specPath).mtimeMs;
  const fileTime = statSync(file).mtimeMs;
  return fileTime < specTime;
});

if (stale.length > 0) {
  console.error('Generated OpenAPI artifacts are stale. Run `npm run openapi:gen`.');
  process.exit(1);
}

console.log('OpenAPI artifacts up-to-date.');
