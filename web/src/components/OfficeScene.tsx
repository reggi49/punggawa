import React, { useEffect } from 'react';
import { ContactShadows } from '@react-three/drei';
import { RoomEnvironment } from './RoomEnvironment';
import {
  StarkWorkstation,
  BayZeroWorkstation,
  UsagiWorkstation,
  ServerArchiveRack,
  ArtCanvasDisplay,
  CoffeeLounge,
  PottedPlantCollection,
} from './Furniture';
import { StylizedHumanoidCharacter } from './WorkerCharacter';
import { JanitorDroid } from './JanitorDroid';
import { useAmbientOffice, CharacterVisualState } from '../simulation/useAmbientOffice';
import { WorkerId, ServicesHealthResponse } from '../types';
import {
  WORKSTATION_CONFIG,
  BAYZERO_SEAT_ANCHOR,
  CLARA_STAND_ANCHOR,
} from '../config/layoutAnchors';

interface OfficeSceneProps {
  currentNode: string;
  status?: string;
  message: string;
  details?: Record<string, any>;
  threadId?: string;
  connected?: boolean;
  isDegraded?: boolean;
  healthData?: ServicesHealthResponse | null;
  onCharacterStatesChange?: (states: Record<WorkerId, CharacterVisualState>) => void;
}

export function OfficeScene({
  currentNode,
  status = 'idle',
  message,
  details = {},
  threadId = '',
  connected = true,
  isDegraded = false,
  healthData,
  onCharacterStatesChange,
}: OfficeSceneProps) {
  // Ambient Life Simulation Hook: coordinates realistic workplace activities and waypoint movement
  const characters = useAmbientOffice(currentNode, status, details, threadId, connected, isDegraded);

  useEffect(() => {
    if (onCharacterStatesChange) {
      onCharacterStatesChange(characters);
    }
  }, [characters, onCharacterStatesChange]);

  // Janitor Bot status
  const isHousekeepingActive =
    (currentNode === 'housekeeping' || currentNode === 'housekeeping_node') &&
    status !== 'completed';

  // Determine dynamic spotlight focus
  const activeWorkerId = characters.stark.isActive
    ? 'stark'
    : characters.usagi.isActive
    ? 'usagi'
    : characters.bayzero.isActive
    ? 'bayzero'
    : null;

  const activeFocusPos: [number, number, number] = isHousekeepingActive
    ? [2.8, 0, 1.8]
    : activeWorkerId
    ? characters[activeWorkerId].targetPos
    : [0, 0, 1.4];

  return (
    <group>
      {/* 1. Scandinavian Modern Office Architecture & Warm Natural Lighting */}
      <RoomEnvironment currentNode={currentNode} activeWorkerPos={activeFocusPos} />

      {/* 2. Office Workstations & Decor */}
      <StarkWorkstation currentNode={currentNode} />
      <BayZeroWorkstation currentNode={currentNode} />
      <UsagiWorkstation currentNode={currentNode} />

      <ServerArchiveRack currentNode={currentNode} isDegraded={isDegraded} healthData={healthData} />
      <ArtCanvasDisplay currentNode={currentNode} />
      <CoffeeLounge currentNode={currentNode} />

      {/* 3. Realistic Poly Haven Potted Plants (14 Placement Coordinates) */}
      <PottedPlantCollection />

      {/* 4. Janitor Droid (Automated Roomba Cleaner & Docking Station) */}
      <JanitorDroid isCleaning={isHousekeepingActive} />

      {/* 5. The 4 Stylized Humanoid Multi-Agent Workers (Shared Seat Anchors) */}
      {/* Stark: Left Desk Tech Architect */}
      <StylizedHumanoidCharacter
        id="stark"
        currentNode={currentNode}
        action={characters.stark.action}
        targetPos={characters.stark.targetPos}
        targetRotY={characters.stark.targetRotY}
        message={characters.stark.isActive ? message : undefined}
        isActive={characters.stark.isActive}
        isSeated={characters.stark.isSeated}
        socialRole={characters.stark.socialRole}
        actualState={characters.stark.actualState}
        ambientLabel={characters.stark.ambientLabel}
        badgeLabelOverride={characters.stark.isActive ? undefined : 'Fokus'}
        dotColorOverride={characters.stark.isActive ? undefined : '#22C55E'}
      />

      {/* Usagi: Right Desk Creative Curator */}
      <StylizedHumanoidCharacter
        id="usagi"
        currentNode={currentNode}
        action={characters.usagi.action}
        targetPos={characters.usagi.targetPos}
        targetRotY={characters.usagi.targetRotY}
        message={characters.usagi.isActive ? message : undefined}
        isActive={characters.usagi.isActive}
        isSeated={characters.usagi.isSeated}
        socialRole={characters.usagi.socialRole}
        actualState={characters.usagi.actualState}
        ambientLabel={characters.usagi.ambientLabel}
        badgeLabelOverride={characters.usagi.isActive ? undefined : 'Fokus'}
        dotColorOverride={characters.usagi.isActive ? undefined : '#22C55E'}
      />

      {/* Bay-Zero: Central Table SOP Auditor & Server Inspector */}
      <StylizedHumanoidCharacter
        id="bayzero"
        currentNode={currentNode}
        action={characters.bayzero.isActive ? characters.bayzero.action : 'casual_conversation'}
        targetPos={characters.bayzero.isActive ? characters.bayzero.targetPos : BAYZERO_SEAT_ANCHOR.seatWorldPosition}
        targetRotY={characters.bayzero.isActive ? characters.bayzero.targetRotY : BAYZERO_SEAT_ANCHOR.seatWorldRotationY}
        message={characters.bayzero.isActive ? message : undefined}
        isActive={characters.bayzero.isActive}
        isSeated={characters.bayzero.isActive ? characters.bayzero.isSeated : true}
        socialRole={characters.bayzero.isActive ? characters.bayzero.socialRole : 'listener'}
        actualState={characters.bayzero.actualState}
        ambientLabel={characters.bayzero.ambientLabel}
        badgeLabelOverride={isDegraded ? 'Investigasi Server ⚠️' : (characters.bayzero.isActive ? undefined : 'Meeting')}
        dotColorOverride={isDegraded ? '#EF4444' : (characters.bayzero.isActive ? undefined : '#F59E0B')}
      />

      {/* Clara: Central Table Editorial Partner (Standing with Coffee Mug in Discussion) */}
      <StylizedHumanoidCharacter
        id="clara"
        currentNode={currentNode}
        action="casual_conversation"
        targetPos={CLARA_STAND_ANCHOR.worldPosition}
        targetRotY={CLARA_STAND_ANCHOR.worldRotationY}
        isActive={false}
        isSeated={false}
        socialRole="speaker"
        holdingCoffeeMug={true}
        actualState="Meeting"
        badgeLabelOverride="Meeting"
        dotColorOverride="#F59E0B"
      />

      {/* 6. Floor Contact Shadows */}
      <ContactShadows
        position={[0, 0.02, 0]}
        opacity={0.45}
        scale={14}
        blur={2.2}
        far={3.5}
        color="#6B5B4B"
      />
    </group>
  );
}
