import { useState, useEffect, useRef, useCallback } from 'react';
import { apiClient } from '@/api/client';
import type { Run, RunStreamEvent, StreamParams } from '@/api/types';

type RunsListParams = StreamParams & {
  from?: string;
  to?: string;
};

type UseRunsStreamOptions = {
  initialFetchParams?: RunsListParams;
  maxRuns?: number;
};

const DEFAULT_MAX_RUNS = 50;

function upsertRun(list: Run[], incoming: Run, limit: number): Run[] {
  const index = list.findIndex((run) => run.id === incoming.id);
  if (index === -1) {
    return [incoming, ...list].slice(0, limit);
  }
  const next = [...list];
  next[index] = { ...next[index], ...incoming };
  return next;
}

export function useRunsStream(streamParams: StreamParams = {}, options: UseRunsStreamOptions = {}) {
  const { initialFetchParams, maxRuns = DEFAULT_MAX_RUNS } = options;
  const [runs, setRuns] = useState<Run[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const streamRef = useRef<{ close: () => void } | null>(null);

  const initialAgentId = initialFetchParams?.agentId;
  const initialStatus = initialFetchParams?.status;
  const initialFrom = initialFetchParams?.from;
  const initialTo = initialFetchParams?.to;
  const streamAgentId = streamParams.agentId;
  const streamStatus = streamParams.status;

  const connect = useCallback(async () => {
    const fetchParams: RunsListParams = {
      agentId: initialAgentId ?? streamAgentId,
      status: initialStatus ?? streamStatus,
      from: initialFrom,
      to: initialTo,
    };
    const streamFilter: StreamParams = {
      agentId: streamAgentId,
      status: streamStatus,
    };

    setIsConnected(false);
    setError(null);

    streamRef.current?.close();
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }

    try {
      const initialRuns = await apiClient.runs.list(fetchParams);
      setRuns(initialRuns);
    } catch (fetchError) {
      console.error('Failed to fetch initial runs', fetchError);
      setError('Failed to fetch initial runs');
      setRuns([]);
    }

    const stream = apiClient.runs.stream(streamFilter, {
      onOpen: () => {
        setIsConnected(true);
        setError(null);
      },
      onMessage: (event: RunStreamEvent) => {
        const runData = event.data;
        setRuns((previous) => {
          switch (event.type) {
            case 'start':
              return [runData, ...previous].slice(0, maxRuns);
            case 'update':
            case 'complete':
            case 'error':
            default:
              return upsertRun(previous, runData, maxRuns);
          }
        });
      },
      onError: () => {
        setError('Connection error');
        setIsConnected(false);

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Reconnecting runs stream...');
          connect();
        }, 5000);
      },
      onClose: () => {
        setIsConnected(false);
      },
    });

    streamRef.current = stream;
  }, [
    initialAgentId,
    initialStatus,
    initialFrom,
    initialTo,
    maxRuns,
    streamAgentId,
    streamStatus,
  ]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      streamRef.current?.close();
    };
  }, [connect]);

  return { runs, isConnected, error };
}
