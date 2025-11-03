import { type ClassValue, clsx } from 'clsx';

// Lightweight className concat helper used across `src/` code. We avoid pulling in
// `tailwind-merge` here to keep the build simple in environments where that
// package may not be installed. Using `clsx` is sufficient for our usage.
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}