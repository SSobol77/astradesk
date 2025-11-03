import { apiBaseUrl, apiToken } from '@/lib/env';
import { resolveSimulationResponse, isSimulationModeEnabled } from '@/lib/simulation';
import type { ProblemDetail } from '@/api/types';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'OPTIONS' | 'HEAD';

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
    public readonly problem?: ProblemDetail,
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
  const simulationResponse = resolveSimulationResponse(path, method, body);
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

  const maxRetries = 3;
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url, { ...init, signal: AbortSignal.timeout(30000) });

      if (!response.ok) {
        let problem: ProblemDetail | undefined;
        const contentType = response.headers.get('content-type');
        if (contentType?.includes('application/problem+json')) {
          try {
            problem = await response.json() as ProblemDetail;
          } catch {
            // Ignore JSON parse error for problem details
          }
        }

        // Don't retry for client errors (4xx)
        if (response.status >= 400 && response.status < 500) {
          throw new ApiError(
            problem?.detail || response.statusText || `HTTP ${response.status}`,
            response.status,
            problem
          );
        }

        // For server errors, retry after delay
        if (attempt < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
          continue;
        }

        throw new ApiError(
          problem?.detail || response.statusText || `HTTP ${response.status}`,
          response.status,
          problem
        );
      }

      // Handle no-content responses
      if (response.status === 204) {
        return undefined as TResponse;
      }

      // Parse JSON response
      try {
        return await response.json() as TResponse;
      } catch (error) {
        throw new ApiError('Invalid JSON response from server', response.status);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      lastError = error as Error;
      if (attempt < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        continue;
      }
    }
  }

  throw new ApiError(
    lastError?.message || 'Network request failed after multiple retries',
    0
  );
}
