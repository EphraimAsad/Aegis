/**
 * WebSocket hook for real-time job updates.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export interface JobUpdate {
  type: 'job_update';
  job_id: number;
  data: {
    status: string;
    progress: number;
    message?: string;
    result?: Record<string, unknown>;
  };
}

export interface WSMessage {
  type: string;
  job_id?: number;
  message?: string;
  data?: Record<string, unknown>;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseJobWebSocketOptions {
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect delay in ms */
  reconnectDelay?: number;
  /** Maximum reconnect attempts */
  maxReconnectAttempts?: number;
}

interface UseJobWebSocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Subscribe to a job's updates */
  subscribe: (jobId: number) => void;
  /** Unsubscribe from a job's updates */
  unsubscribe: (jobId: number) => void;
  /** Latest job updates by job ID */
  jobUpdates: Map<number, JobUpdate['data']>;
  /** Last error message */
  error: string | null;
  /** Manually connect */
  connect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
}

export function useJobWebSocket(
  options: UseJobWebSocketOptions = {}
): UseJobWebSocketReturn {
  const {
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [jobUpdates, setJobUpdates] = useState<Map<number, JobUpdate['data']>>(
    new Map()
  );
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const subscribedJobsRef = useRef<Set<number>>(new Set());

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus('connecting');
    setError(null);

    try {
      const ws = new WebSocket(`${WS_BASE_URL}/api/v1/ws/jobs`);

      ws.onopen = () => {
        setStatus('connected');
        reconnectAttemptsRef.current = 0;

        // Re-subscribe to all previously subscribed jobs
        subscribedJobsRef.current.forEach((jobId) => {
          ws.send(JSON.stringify({ action: 'subscribe', job_id: jobId }));
        });
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);

          if (message.type === 'job_update' && message.job_id !== undefined) {
            setJobUpdates((prev) => {
              const updated = new Map(prev);
              updated.set(message.job_id!, message.data as JobUpdate['data']);
              return updated;
            });
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        setStatus('disconnected');
        wsRef.current = null;

        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          setTimeout(connect, reconnectDelay);
        }
      };

      ws.onerror = () => {
        setStatus('error');
        setError('WebSocket connection failed');
      };

      wsRef.current = ws;
    } catch (e) {
      setStatus('error');
      setError('Failed to create WebSocket connection');
    }
  }, [autoReconnect, reconnectDelay, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, []);

  const subscribe = useCallback((jobId: number) => {
    subscribedJobsRef.current.add(jobId);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'subscribe', job_id: jobId }));
    }
  }, []);

  const unsubscribe = useCallback((jobId: number) => {
    subscribedJobsRef.current.delete(jobId);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'unsubscribe', job_id: jobId }));
    }

    setJobUpdates((prev) => {
      const updated = new Map(prev);
      updated.delete(jobId);
      return updated;
    });
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    status,
    subscribe,
    unsubscribe,
    jobUpdates,
    error,
    connect,
    disconnect,
  };
}

/**
 * Hook to subscribe to a specific job's updates.
 */
export function useJobStatus(jobId: number | null) {
  const { status, subscribe, unsubscribe, jobUpdates } = useJobWebSocket();

  useEffect(() => {
    if (jobId !== null) {
      subscribe(jobId);
      return () => unsubscribe(jobId);
    }
  }, [jobId, subscribe, unsubscribe]);

  return {
    connectionStatus: status,
    jobStatus: jobId !== null ? jobUpdates.get(jobId) : undefined,
  };
}
