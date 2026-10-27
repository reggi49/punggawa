import React, { useState, useCallback, Suspense, lazy } from 'react';
import { useEventStream } from './hooks/useEventStream';
import { useServicesHealth } from './hooks/useServicesHealth';
import { HUDOverlay } from './components/HUDOverlay';
import { MobileDashboard } from './components/MobileDashboard';
import { OfficeLoadingScreen } from './components/OfficeLoadingScreen';
import { CharacterVisualState } from './simulation/useAmbientOffice';
import { WorkerId } from './types';
import { useDeviceMode } from './utils/device';

// Lazy load 3D Office Canvas to eliminate initial bundle bloat & asset freezing
const OfficeCanvas = lazy(() => import('./components/OfficeCanvas'));

export function App() {
  const {
    currentNode,
    threadId,
    status,
    message,
    details,
    logs,
    loadingLogs,
    refreshLogs,
    connected,
    setSimulatedNode,
    reconnect,
  } = useEventStream();

  const { viewMode, setViewMode, isMobile, isEffective2D } = useDeviceMode();

  const [characterStates, setCharacterStates] = useState<Record<WorkerId, CharacterVisualState> | null>(null);

  const handleCharacterStatesChange = useCallback((states: Record<WorkerId, CharacterVisualState>) => {
    setCharacterStates(states);
  }, []);

  const latestEvent = logs[0];
  const {
    healthData,
    isDegraded,
    isRechecking,
    isDismissed: isAlertDismissed,
    dismissAlert,
    recheck: recheckHealth,
  } = useServicesHealth(latestEvent);

  // If in 2D Mode (default on mobile screens or toggled by user), render lightweight 2D Dashboard
  if (isEffective2D) {
    return (
      <MobileDashboard
        currentNode={currentNode}
        threadId={threadId}
        status={status}
        message={message}
        details={details}
        logs={logs}
        loadingLogs={loadingLogs}
        onRefreshLogs={refreshLogs}
        connected={connected}
        characterStates={characterStates}
        healthData={healthData}
        isDegraded={isDegraded}
        isRechecking={isRechecking}
        onSwitchTo3D={() => setViewMode('3d')}
        onSimulateNode={setSimulatedNode}
        onReconnect={reconnect}
        onRecheckHealth={recheckHealth}
      />
    );
  }

  // Otherwise, render full 3D Office with Progressive Suspense Fallback
  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', overflow: 'hidden' }}>
      <Suspense fallback={<OfficeLoadingScreen onSwitchTo2D={isMobile ? () => setViewMode('2d') : undefined} />}>
        {/* 3D Office Isometric World with Multi-Agent Team */}
        <OfficeCanvas
          currentNode={currentNode}
          status={status}
          message={message}
          details={details}
          threadId={threadId}
          connected={connected}
          isDegraded={isDegraded}
          isMobile={isMobile}
          healthData={healthData}
          onCharacterStatesChange={handleCharacterStatesChange}
        />
      </Suspense>

      {/* Multi-Agent Dashboard & HUD Overlay */}
      <HUDOverlay
        currentNode={currentNode}
        threadId={threadId}
        status={status}
        message={message}
        details={details}
        logs={logs}
        loadingLogs={loadingLogs}
        onRefreshLogs={refreshLogs}
        connected={connected}
        characterStates={characterStates}
        healthData={healthData}
        isDegraded={isDegraded}
        isRechecking={isRechecking}
        isAlertDismissed={isAlertDismissed}
        onDismissAlert={dismissAlert}
        onRecheckHealth={recheckHealth}
        onSimulateNode={setSimulatedNode}
        onReconnect={reconnect}
        isMobile={isMobile}
        onSwitchTo2D={isMobile ? () => setViewMode('2d') : undefined}
      />
    </div>
  );
}

export default App;
