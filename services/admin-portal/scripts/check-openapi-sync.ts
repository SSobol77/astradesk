#!/usr/bin/env tsx
import { existsSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const scriptDir = dirname(__filename);

function findRepoRoot(startDir: string): string {
  let current = startDir;
  while (true) {
    if (existsSync(join(current, '.git'))) {
      return current;
    }
    const parent = resolve(current, '..');
    if (parent === current) {
      throw new Error(`Unable to locate repository root from ${startDir}`);
    }
    current = parent;
  }
}

const repoRoot = findRepoRoot(scriptDir);
const adminPortalRoot = resolve(scriptDir, '..');

const overridePath = process.env.ASTRA_OPENAPI_SPEC;
const specPath = overridePath
  ? resolve(repoRoot, overridePath)
  : resolve(repoRoot, 'openapi/astradesk-admin.v1.yaml');

if (!existsSync(specPath)) {
  console.error('OpenAPI specification not found.');
  console.error('Checked:', specPath);
  console.error('Set ASTRA_OPENAPI_SPEC to override the spec location (relative to repo root or absolute).');
  process.exit(1);
}

const generatedFiles = [join(adminPortalRoot, 'src', 'api', 'types.gen.ts')];

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
