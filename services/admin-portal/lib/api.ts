import { apiBaseUrl, apiToken } from '@/lib/env';
import { resolveSimulationResponse, isSimulationModeEnabled } from '@/lib/simulation';
import type { ErrorResponse } from '@/openapi/openapi-types';

type HttpMethod = 'GET' | 'POST' | 'PUT';

type ApiRequestConfig<TBody> = {
  path: string;
  method: HttpMethod;
  searchParams?: Record<string, string | number | boolean | undefined>;
  body?: TBody;
  headers?: HeadersInit;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly problem?: ErrorResponse,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiFetch<TResponse, TBody = unknown>({
  path,
  method,
  searchParams,
  body,
  headers,
}: ApiRequestConfig<TBody>): Promise<TResponse> {
  const simulationResponse = resolveSimulationResponse(path, method);
  if (simulationResponse !== undefined) {
    return simulationResponse as TResponse;
  }

  const url = new URL(path, apiBaseUrl);

  if (searchParams) {
    const params = new URLSearchParams();
    Object.entries(searchParams)
      .filter(([, value]) => value !== undefined && value !== null && value !== '')
      .forEach(([key, value]) => params.append(key, String(value)));
    if (Array.from(params.entries()).length > 0) {
      url.search = params.toString();
    }
  }

  const init: RequestInit & { next?: { revalidate?: number } } = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(apiToken ? { Authorization: `Bearer ${apiToken}` } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    cache:
      method === 'GET'
        ? isSimulationModeEnabled()
          ? 'force-cache'
          : 'no-store'
        : 'no-cache',
  };

  if (isSimulationModeEnabled() && method === 'GET') {
    init.next = { revalidate: 60 };
  }

  const response = await fetch(url, init);

  if (!response.ok) {
    let problem: ErrorResponse | undefined;
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/problem+json')) {
      try {
        problem = (await response.json()) as ErrorResponse;
      } catch (error) {
        problem = undefined;
      }
    }
    const message = problem?.detail || `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, problem);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  const text = await response.text();
  if (!text) {
    return undefined as TResponse;
  }

  try {
    return JSON.parse(text) as TResponse;
  } catch (error) {
    // The endpoint might not return JSON (e.g., NDJSON export). In that case, return raw text.
    return text as TResponse;
  }
}
