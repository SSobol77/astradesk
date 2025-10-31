import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

class MockEventSource {
  public static instances: MockEventSource[] = [];

  public onmessage: ((event: MessageEvent) => void) | null = null;

  public onerror: ((event: Event) => void) | null = null;

  public readonly close = vi.fn();

  constructor(public readonly url: string) {
    MockEventSource.instances.push(this);
  }
}

describe('createSseStream', () => {
  let originalEventSource: typeof EventSource | undefined;

  beforeEach(() => {
    MockEventSource.instances = [];
    originalEventSource = globalThis.EventSource;
    globalThis.EventSource = MockEventSource as unknown as typeof EventSource;
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:4000';
    process.env.ASTRADESK_API_TOKEN = '';
    vi.resetModules();
    vi.useFakeTimers();
  });

  afterEach(() => {
    if (originalEventSource) {
      globalThis.EventSource = originalEventSource;
    }
  });

  it('reconnects after errors and emits messages', async () => {
    const { createSseStream } = await import('@/lib/sse');
    const onMessage = vi.fn();
    const onError = vi.fn();

    const dispose = createSseStream({ path: '/runs/stream', onMessage, onError });

    expect(MockEventSource.instances.length).toBe(1);

    const first = MockEventSource.instances[0];
    first.onerror?.(new Event('error'));

    // First reconnect after 1000ms
    vi.advanceTimersByTime(1000);

    expect(MockEventSource.instances.length).toBeGreaterThan(1);

    const latest = MockEventSource.instances.at(-1)!;
    latest.onmessage?.({ data: JSON.stringify({ id: 'run-1' }) } as MessageEvent);

    expect(onMessage).toHaveBeenCalledWith(expect.objectContaining({ id: 'run-1' }));

    dispose();
    expect(latest.close).toHaveBeenCalled();
  });
});
