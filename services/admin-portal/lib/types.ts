import type { Route } from 'next';

export type Breadcrumb = {
  label: string;
  href: Route | '#';
};

export type QuickCreateLink = {
  label: string;
  pathname: Route;
  query?: Record<string, string>;
};
