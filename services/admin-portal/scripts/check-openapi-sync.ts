#!/usr/bin/env tsx
import { existsSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const specPath = join(root, 'OpenAPI.yaml');
const generatedFiles = [join(root, 'src', 'api', 'types.gen.ts')];

if (!existsSync(specPath)) {
  console.error('OpenAPI specification not found at OpenAPI.yaml');
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
