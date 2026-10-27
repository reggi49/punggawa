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
  BAYZERO_KANBAN_ANCHOR,
  SCOUT_SEAT_ANCHOR,
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
    currentNode === 'housekeeping' ||
    currentNode === 'housekeeping_node' ||
    details?.task_type === 'housekeeping' ||
    details?.action_type === 'housekeeping' ||
    threadId === 'system';

  // Determine dynamic spotlight focus
  const activeWorkerId = characters.stark.isActive
    ? 'stark'
    : characters.usagi.isActive
    ? 'usagi'
    : characters.bayzero.isActive
    ? 'bayzero'
    : characters.scout.isActive
    ? 'scout'
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

      {/* Bay-Zero / Kang Bos: Kanban Whiteboard Lead Auditor & Server Inspector */}
      <StylizedHumanoidCharacter
        id="bayzero"
        currentNode={currentNode}
        action={isDegraded ? 'confused_scratch' : (characters.bayzero.isActive ? characters.bayzero.action : 'kanban_pacing')}
        targetPos={isDegraded ? [5.0, 0, -0.45] : (characters.bayzero.isActive ? characters.bayzero.targetPos : BAYZERO_KANBAN_ANCHOR.position)}
        targetRotY={isDegraded ? Math.PI / 2 : (characters.bayzero.isActive ? characters.bayzero.targetRotY : BAYZERO_KANBAN_ANCHOR.rotationY)}
        message={characters.bayzero.isActive ? message : undefined}
        isActive={characters.bayzero.isActive}
        isSeated={false}
        socialRole={characters.bayzero.socialRole}
        actualState={characters.bayzero.actualState}
        ambientLabel={characters.bayzero.ambientLabel}
        badgeLabelOverride={isDegraded ? 'Investigasi Server ⚠️' : (characters.bayzero.isActive ? undefined : 'SOP Kanban')}
        dotColorOverride={isDegraded ? '#EF4444' : (characters.bayzero.isActive ? undefined : '#F59E0B')}
      />

      {/* Scout / Kang Kerja: Central Table Career Intelligence Lead (Seated Opposite Bay-Zero) */}
      <StylizedHumanoidCharacter
        id="scout"
        currentNode={currentNode}
        action={characters.scout.isActive ? characters.scout.action : 'looking_monitor'}
        targetPos={characters.scout.isActive ? characters.scout.targetPos : SCOUT_SEAT_ANCHOR.seatWorldPosition}
        targetRotY={characters.scout.isActive ? characters.scout.targetRotY : SCOUT_SEAT_ANCHOR.seatWorldRotationY}
        message={characters.scout.isActive ? message : undefined}
        isActive={characters.scout.isActive}
        isSeated={characters.scout.isActive ? characters.scout.isSeated : true}
        socialRole={characters.scout.socialRole}
        actualState={characters.scout.actualState}
        ambientLabel={characters.scout.ambientLabel}
        badgeLabelOverride={characters.scout.isActive ? undefined : 'Scouting'}
        dotColorOverride={characters.scout.isActive ? undefined : '#0D9488'}
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
