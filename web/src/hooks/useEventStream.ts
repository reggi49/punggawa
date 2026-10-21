import { useEffect, useRef, useState, useCallback } from 'react';
import { AgentEventPayload } from '../types';

export interface LogEntry {
  id: string;
  time: string;
  node: string;
  status: string;
  message: string;
  agent_name?: string;
  error?: string;
  result_url?: string;
  details?: Record<string, any>;
}

export function useEventStream(endpoint: string = '/api/stream') {
  const [currentNode, setCurrentNode] = useState<string>('IDLE');
  const [threadId, setThreadId] = useState<string>('system');
  const [status, setStatus] = useState<string>('idle');
  const [message, setMessage] = useState<string>('Kantor virtual siap. Menunggu tugas dari antrean.');
  const [details, setDetails] = useState<Record<string, any>>({});
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState<boolean>(false);
  const [lastHeartbeat, setLastHeartbeat] = useState<number>(Date.now());

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Tentukan URL stream (dukung port dinamis atau proxy vite relatif)
    const streamUrl = endpoint.startsWith('http')
      ? endpoint
      : endpoint;

    console.log(`[useEventStream] Connecting to SSE at ${streamUrl}...`);

    try {
      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        console.log('[useEventStream] Connected to SSE stream.');
        setConnected(true);
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      es.onmessage = (event) => {
        setLastHeartbeat(Date.now());
        if (!event.data || event.data.trim() === '') return;

        try {
          const payload: AgentEventPayload = JSON.parse(event.data);

          if (payload.node === 'STREAM_INIT' || payload.node === 'WS_INIT') {
            setConnected(true);
            return;
          }

          // Perbarui state reaktif
          if (payload.node) {
            setCurrentNode(payload.node);
          }
          if (payload.thread_id) {
            setThreadId(payload.thread_id);
          }
          if (payload.status) {
            setStatus(payload.status);
          }
          if (payload.message) {
            setMessage(payload.message);
          }
          if (payload.details) {
            setDetails(payload.details);
          }

          // Catat ke terminal log (maks 100 entri)
          const nowStr = new Date().toLocaleTimeString('id-ID', { hour12: false });
          const newLog: LogEntry = {
            id: `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
            time: nowStr,
            node: payload.node || 'UNKNOWN',
            status: payload.status || 'info',
            message: payload.message || '',
            agent_name: (payload as any).agent_name || payload.details?.agent_name,
            error: (payload as any).error || payload.details?.error,
            result_url: (payload as any).result_url || payload.details?.result_url || payload.details?.url,
            details: payload.details,
          };

          setLogs((prev) => [newLog, ...prev.slice(0, 99)]);
        } catch (err) {
          console.warn('[useEventStream] Failed to parse SSE payload:', err, event.data);
        }
      };

      es.onerror = (err) => {
        console.warn('[useEventStream] SSE Error, reconnecting in 3 seconds...', err);
        setConnected(false);
        es.close();
        eventSourceRef.current = null;

        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, 3000);
        }
      };
    } catch (e) {
      console.error('[useEventStream] Failed to instantiate EventSource:', e);
      setConnected(false);
      reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
    }
  }, [endpoint]);

  useEffect(() => {
    connect();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  // Manual trigger untuk visual testing semua animasi di frontend
  const setSimulatedNode = (nodeName: string, customMessage?: string) => {
    setCurrentNode(nodeName);
    setStatus('simulated');
    setMessage(customMessage || `Simulating node ${nodeName}`);
    const nowStr = new Date().toLocaleTimeString('id-ID', { hour12: false });
    setLogs((prev) => [
      {
        id: `sim-${Date.now()}`,
        time: nowStr,
        node: nodeName,
        status: 'simulated',
        message: customMessage || `Simulated node transition to ${nodeName}`,
      },
      ...prev.slice(0, 99),
    ]);
  };

  return {
    currentNode,
    threadId,
    status,
    message,
    details,
    logs,
    connected,
    lastHeartbeat,
    setSimulatedNode,
    reconnect: connect,
  };
}
