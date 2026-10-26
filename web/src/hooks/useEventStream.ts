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
  timestamp?: string;
  created_at?: string;
  date?: string;
  display_time?: string;
}

export function useEventStream(endpoint: string = '/api/stream') {
  const [currentNode, setCurrentNode] = useState<string>('IDLE');
  const [threadId, setThreadId] = useState<string>('system');
  const [status, setStatus] = useState<string>('idle');
  const [message, setMessage] = useState<string>('Kantor virtual siap. Menunggu tugas dari antrean.');
  const [details, setDetails] = useState<Record<string, any>>({});
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loadingLogs, setLoadingLogs] = useState<boolean>(false);
  const [connected, setConnected] = useState<boolean>(false);
  const [lastHeartbeat, setLastHeartbeat] = useState<number>(Date.now());

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Ambil riwayat log eksekusi dari database PostgreSQL agar persisten di setiap sesi & device
  const fetchHistoricalLogs = useCallback(async () => {
    setLoadingLogs(true);
    try {
      const res = await fetch('/api/logs?limit=100');
      if (res.ok) {
        const data = await res.json();
        if (data && Array.isArray(data.logs)) {
          setLogs(data.logs.map((item: any) => ({
            id: item.id || `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
            time: item.time || (item.timestamp ? new Date(item.timestamp).toLocaleTimeString('id-ID', { hour12: false }) : '-'),
            node: item.node || 'UNKNOWN',
            status: item.status || 'info',
            message: item.message || '',
            agent_name: item.agent_name,
            error: item.error || item.details?.error,
            result_url: item.result_url || item.details?.result_url || item.details?.url,
            details: item.details,
            timestamp: item.timestamp || item.created_at,
            created_at: item.created_at,
            date: item.date,
            display_time: item.display_time,
          })));
        }
      }
    } catch (err) {
      console.warn('[useEventStream] Gagal memuat riwayat log persisten:', err);
    } finally {
      setLoadingLogs(false);
    }
  }, []);

  useEffect(() => {
    fetchHistoricalLogs();
  }, [fetchHistoricalLogs]);

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

          // Jangan catat event IDLE rutin ke daftar log agar tidak membanjiri riwayat pengerjaan tugas
          if (payload.node === 'IDLE' && payload.status === 'idle') {
            return;
          }

          // Catat ke terminal log (maks 150 entri)
          const logId = (payload as any).id || payload.details?.log_id || `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
          const nowStr = new Date().toLocaleTimeString('id-ID', { hour12: false });
          const newLog: LogEntry = {
            id: logId,
            time: nowStr,
            node: payload.node || 'UNKNOWN',
            status: payload.status || 'info',
            message: payload.message || '',
            agent_name: (payload as any).agent_name || payload.details?.agent_name,
            error: (payload as any).error || payload.details?.error,
            result_url: (payload as any).result_url || payload.details?.result_url || payload.details?.url,
            details: payload.details,
            timestamp: payload.timestamp || new Date().toISOString(),
          };

          setLogs((prev) => {
            if (prev.some((l) => l.id === newLog.id)) {
              return prev;
            }
            return [newLog, ...prev.slice(0, 149)];
          });
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
      ...prev.slice(0, 149),
    ]);
  };

  return {
    currentNode,
    threadId,
    status,
    message,
    details,
    logs,
    loadingLogs,
    refreshLogs: fetchHistoricalLogs,
    connected,
    lastHeartbeat,
    setSimulatedNode,
    reconnect: connect,
  };
}
