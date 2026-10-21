import { useState, useEffect, useCallback } from 'react';
import { ServicesHealthResponse } from '../types';

export function useServicesHealth(sseEvent?: any) {
  const [healthData, setHealthData] = useState<ServicesHealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRechecking, setIsRechecking] = useState<boolean>(false);
  const [isDismissed, setIsDismissed] = useState<boolean>(false);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/services/health');
      if (res.ok) {
        const data: ServicesHealthResponse = await res.json();
        setHealthData(data);
      }
    } catch (err) {
      console.warn('[useServicesHealth] Failed to fetch services health:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const recheck = useCallback(async () => {
    setIsRechecking(true);
    try {
      const res = await fetch('/api/services/health/check', { method: 'POST' });
      if (res.ok) {
        const data: ServicesHealthResponse = await res.json();
        setHealthData(data);
        setIsDismissed(false); // Reset dismissal on manual recheck
      }
    } catch (err) {
      console.error('[useServicesHealth] Failed to trigger health re-check:', err);
    } finally {
      setIsRechecking(false);
    }
  }, []);

  // Initial fetch and 60-second periodic polling
  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 60000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  // Listen for realtime SSE uptime_alert events
  useEffect(() => {
    if (sseEvent && sseEvent.node === 'uptime_alert') {
      if (sseEvent.details?.health) {
        setHealthData(sseEvent.details.health);
        setIsDismissed(false);
      } else {
        fetchHealth();
      }
    }
  }, [sseEvent, fetchHealth]);

  const isDegraded = healthData?.overall_status === 'degraded';

  return {
    healthData,
    isDegraded,
    isLoading,
    isRechecking,
    isDismissed,
    dismissAlert: () => setIsDismissed(true),
    fetchHealth,
    recheck,
  };
}
