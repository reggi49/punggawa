import React, { useState, useCallback } from 'react';
import { useEventStream } from './hooks/useEventStream';
import { useServicesHealth } from './hooks/useServicesHealth';
import { OfficeCanvas } from './components/OfficeCanvas';
import { HUDOverlay } from './components/HUDOverlay';
import { CharacterVisualState } from './simulation/useAmbientOffice';
import { WorkerId } from './types';

export function App() {
  const {
    currentNode,
    threadId,
    status,
    message,
    details,
    logs,
    connected,
    setSimulatedNode,
    reconnect,
  } = useEventStream();

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

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', overflow: 'hidden' }}>
      {/* 3D Office Isometric World with Multi-Agent Team */}
      <OfficeCanvas
        currentNode={currentNode}
        status={status}
        message={message}
        details={details}
        threadId={threadId}
        connected={connected}
        isDegraded={isDegraded}
        healthData={healthData}
        onCharacterStatesChange={handleCharacterStatesChange}
      />

      {/* Multi-Agent Dashboard & HUD Overlay */}
      <HUDOverlay
        currentNode={currentNode}
        threadId={threadId}
        status={status}
        message={message}
        details={details}
        logs={logs}
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
      />
    </div>
  );
}

export default App;
