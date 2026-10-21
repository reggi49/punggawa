import React, { useState, useCallback } from 'react';
import { useEventStream } from './hooks/useEventStream';
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
        onSimulateNode={setSimulatedNode}
        onReconnect={reconnect}
      />
    </div>
  );
}

export default App;
