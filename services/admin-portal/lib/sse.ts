'use client';

import type { RunStreamEvent } from '@/api/types';
import { apiBaseUrl, apiToken } from '@/lib/env';

export type SseOptions<TData> = {
  path: string;
  onMessage: (data: TData) => void;
  onError?: (error: Event) => void;
  getToken?: () => string | Promise<string>;
  maxRetries?: number;
};

export function createSseStream({
  path,
  onMessage,
  onError,
  getToken,
  maxRetries = 5,
}: SseOptions<RunStreamEvent>) {
  let retries = 0;
  let eventSource: EventSource | null = null;
  let closed = false;

  const connect = async () => {
    const token = (await getToken?.()) ?? apiToken;
    const url = new URL(path, apiBaseUrl);
    eventSource = new EventSource(url, {
      withCredentials: false,
    });

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as RunStreamEvent;
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse SSE payload', error);
      }
    };

    eventSource.onerror = (event) => {
      onError?.(event);
      eventSource?.close();
      if (closed) {
        return;
      }
      if (retries >= maxRetries) {
        return;
      }
      const delay = Math.min(1000 * 2 ** retries, 15000);
      retries += 1;
      setTimeout(connect, delay);
    };

    // Inject Authorization header if the browser supports it via token query param.
    if (token) {
      eventSource.close();
      const authedUrl = new URL(path, apiBaseUrl);
      authedUrl.searchParams.set('token', token);
      eventSource = new EventSource(authedUrl);
    }
  };

  connect();

  return () => {
    closed = true;
    eventSource?.close();
  };
}
