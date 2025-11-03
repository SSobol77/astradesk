'use client';

// Re-export the non-src Button implementation located under `components/primitives`.
// This avoids pulling in extra runtime/dev dependencies (like class-variance-authority)
// into the TypeScript type-checker when the project is configured to include both
// `src/` and `components/` in the compile scope.
export { default } from '@/components/primitives/Button';
