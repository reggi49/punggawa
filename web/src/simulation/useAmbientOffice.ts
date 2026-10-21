/**
 * useAmbientOffice.ts
 * React hook connecting the ambient life simulation engine to OfficeScene.
 * Accurately decouples genuine AI job state from background office life,
 * applying realistic office behaviors, collision-free waypoint locomotion,
 * and context-aware social discussions.
 */
import { useEffect, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { WorkerId, ActualAgentState, AmbientActivityType, CharacterAction } from '../types';
import { AmbientOfficeSimulator, WorkerAmbientState } from './ambientScheduler';
import { getHumanStatus } from '../utils/statusLabels';
import { WORKSTATION_CONFIG, BAYZERO_SEAT_ANCHOR } from '../config/layoutAnchors';

export interface CharacterVisualState {
  id: WorkerId;
  targetPos: [number, number, number];
  targetRotY: number;
  action: CharacterAction;
  isSeated: boolean;
  isActive: boolean; // True ONLY when actively running real AI job
  actualState: ActualAgentState;
  ambientActivity: AmbientActivityType;
  ambientLabel: string;
  socialRole: 'speaker' | 'listener' | null;
}

export function useAmbientOffice(
  currentNode: string,
  status: string = 'idle',
  details: Record<string, any> = {},
  threadId: string = '',
  connected: boolean = true,
  isDegraded: boolean = false
) {
  const simulatorRef = useRef<AmbientOfficeSimulator | null>(null);
  if (!simulatorRef.current) {
    simulatorRef.current = new AmbientOfficeSimulator();
  }
  const simulator = simulatorRef.current;

  // 1. Determine Actual Real Agent States from LangGraph Event Stream
  const taskType =
    details.action_type ||
    details.task_type ||
    (threadId.toLowerCase().includes('dongeng') ? 'dongeng' : 'article');

  const isDongengPipeline =
    taskType === 'dongeng' ||
    currentNode === 'curate_node' ||
    currentNode === 'render_cover_node' ||
    currentNode === 'post_cms_node';

  const isIdle =
    currentNode === 'IDLE' ||
    currentNode === 'idle_coffee' ||
    currentNode === 'STREAM_INIT';

  const isSOPNode = currentNode === 'sop_validator_node';
  const isAwaitingApproval =
    currentNode === 'await_approval' ||
    status === 'waiting_approval';
  const isFailed =
    currentNode === 'failed_node' ||
    status === 'failed' ||
    status === 'blocked';
  const isComplete =
    currentNode === 'publish_node' ||
    currentNode === 'complete_node' ||
    currentNode === 'post_cms_node';

  // Synchronize actual state into the simulator
  useEffect(() => {
    if (!connected) {
      // Offline scenario
      simulator.updateActualState('stark', 'Offline');
      simulator.updateActualState('usagi', 'Offline');
      simulator.updateActualState('bayzero', 'Offline');
      return;
    }

    if (isDegraded) {
      // Microservice Outage: Stark rushes to the server cluster to troubleshoot & inspect!
      const serverTargetPos: [number, number, number] = [5.0, 0, -0.45];
      const serverTargetRotY = Math.PI / 2; // Facing East (+X) directly towards the server racks
      simulator.updateActualState('stark', 'Blocked', serverTargetPos, serverTargetRotY, 'confused_scratch');
      simulator.updateActualState('usagi', 'Idle');
      simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
      return;
    }

    if (isIdle) {
      simulator.updateActualState('stark', 'Idle');
      simulator.updateActualState('usagi', 'Idle');
      simulator.updateActualState('bayzero', 'Idle');
    } else if (isFailed) {
      // Blocked / Failure state
      if (isDongengPipeline) {
        simulator.updateActualState('usagi', 'Blocked', WORKSTATION_CONFIG.usagi.seatWorldPosition, WORKSTATION_CONFIG.usagi.seatWorldRotationY, 'confused_scratch');
        simulator.updateActualState('stark', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
      } else {
        simulator.updateActualState('stark', 'Blocked', WORKSTATION_CONFIG.stark.seatWorldPosition, WORKSTATION_CONFIG.stark.seatWorldRotationY, 'confused_scratch');
        simulator.updateActualState('usagi', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
      }
    } else if (isAwaitingApproval) {
      // Waiting for human approval
      if (isDongengPipeline) {
        simulator.updateActualState('usagi', 'Waiting', WORKSTATION_CONFIG.usagi.seatWorldPosition, WORKSTATION_CONFIG.usagi.seatWorldRotationY, 'observing');
        simulator.updateActualState('stark', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
      } else {
        simulator.updateActualState('stark', 'Waiting', WORKSTATION_CONFIG.stark.seatWorldPosition, WORKSTATION_CONFIG.stark.seatWorldRotationY, 'observing');
        simulator.updateActualState('usagi', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
      }
    } else if (isSOPNode) {
      // SOP Validation phase: Bay-Zero works at central table, active author waits
      simulator.updateActualState('bayzero', 'Working', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'inspecting_sop');
      if (isDongengPipeline) {
        simulator.updateActualState('usagi', 'Waiting', WORKSTATION_CONFIG.usagi.seatWorldPosition, WORKSTATION_CONFIG.usagi.seatWorldRotationY, 'observing');
        simulator.updateActualState('stark', 'Idle');
      } else {
        simulator.updateActualState('stark', 'Waiting', WORKSTATION_CONFIG.stark.seatWorldPosition, WORKSTATION_CONFIG.stark.seatWorldRotationY, 'observing');
        simulator.updateActualState('usagi', 'Idle');
      }
    } else if (isDongengPipeline) {
      // Dongeng pipeline: Usagi works, Stark and Bay-Zero are Idle
      let usagiTaskPos: [number, number, number] = WORKSTATION_CONFIG.usagi.seatWorldPosition;
      let usagiTaskRotY = WORKSTATION_CONFIG.usagi.seatWorldRotationY;
      let usagiTaskAction: CharacterAction = 'intense_typing';

      if (currentNode === 'ingest_node') {
        usagiTaskPos = WORKSTATION_CONFIG.usagi.seatWorldPosition;
        usagiTaskRotY = WORKSTATION_CONFIG.usagi.seatWorldRotationY;
        usagiTaskAction = 'looking_monitor';
      } else if (currentNode === 'render_cover_node' || currentNode === 'thumbnail_node') {
        usagiTaskPos = [-3.6, 0, -2.7];
        usagiTaskRotY = 0.35;
        usagiTaskAction = 'drawing_canvas';
      } else if (isComplete) {
        usagiTaskPos = WORKSTATION_CONFIG.usagi.seatWorldPosition;
        usagiTaskRotY = Math.PI * 0.8;
        usagiTaskAction = 'success_celebration';
      }

      simulator.updateActualState('usagi', 'Working', usagiTaskPos, usagiTaskRotY, usagiTaskAction);
      simulator.updateActualState('stark', 'Idle');
      simulator.updateActualState('bayzero', 'Idle');
    } else {
      // Article pipeline: Stark works, Usagi and Bay-Zero are Idle
      let starkTaskPos: [number, number, number] = WORKSTATION_CONFIG.stark.seatWorldPosition;
      let starkTaskRotY = WORKSTATION_CONFIG.stark.seatWorldRotationY;
      let starkTaskAction: CharacterAction = 'intense_typing';

      if (currentNode === 'ingest_node') {
        starkTaskPos = WORKSTATION_CONFIG.stark.seatWorldPosition;
        starkTaskRotY = WORKSTATION_CONFIG.stark.seatWorldRotationY;
        starkTaskAction = 'looking_monitor';
      } else if (currentNode === 'scrape_node') {
        starkTaskPos = [-2.2, 0, -3.8];
        starkTaskRotY = 0;
        starkTaskAction = 'searching_archive';
      } else if (currentNode === 'thumbnail_node') {
        starkTaskPos = [-3.6, 0, -2.7];
        starkTaskRotY = 0.35;
        starkTaskAction = 'drawing_canvas';
      } else if (isComplete) {
        starkTaskPos = WORKSTATION_CONFIG.stark.seatWorldPosition;
        starkTaskRotY = Math.PI * 0.8;
        starkTaskAction = 'success_celebration';
      }

      simulator.updateActualState('stark', 'Working', starkTaskPos, starkTaskRotY, starkTaskAction);
      simulator.updateActualState('usagi', 'Idle');
      simulator.updateActualState('bayzero', 'Idle');
    }
  }, [currentNode, status, isDongengPipeline, isIdle, isSOPNode, isAwaitingApproval, isFailed, isComplete, connected, isDegraded]);

  // Visual state hook updated efficiently on animation tick
  const [characterStates, setCharacterStates] = useState<Record<WorkerId, CharacterVisualState>>(() => ({
    stark: buildVisualState('stark', simulator.getWorkerState('stark'), currentNode, isDegraded),
    usagi: buildVisualState('usagi', simulator.getWorkerState('usagi'), currentNode, isDegraded),
    bayzero: buildVisualState('bayzero', simulator.getWorkerState('bayzero'), currentNode, isDegraded),
    clara: buildVisualState('clara', simulator.getWorkerState('clara'), currentNode, isDegraded),
  }));

  const lastUpdateRef = useRef<number>(0);

  // Drive simulation tick in animation loop
  useFrame((_, delta) => {
    const now = Date.now();
    simulator.tick(now, delta);

    // Throttle state emission to ~12 FPS for smooth, efficient React updates
    if (now - lastUpdateRef.current >= 80) {
      lastUpdateRef.current = now;

      setCharacterStates({
        stark: buildVisualState('stark', simulator.getWorkerState('stark'), currentNode, isDegraded),
        usagi: buildVisualState('usagi', simulator.getWorkerState('usagi'), currentNode, isDegraded),
        bayzero: buildVisualState('bayzero', simulator.getWorkerState('bayzero'), currentNode, isDegraded),
        clara: buildVisualState('clara', simulator.getWorkerState('clara'), currentNode, isDegraded),
      });
    }
  });

  return characterStates;
}

/**
 * Helper translating ambient state to character props
 */
function buildVisualState(
  id: WorkerId,
  amb: WorkerAmbientState,
  currentNode: string,
  isDegraded: boolean = false
): CharacterVisualState {
  const isOutageStark = id === 'stark' && isDegraded;
  const isWorking = amb.actualState === 'Working' || isOutageStark;

  // Humanized ambient activity description
  let ambientLabel = 'Santai di Meja';
  switch (amb.ambientActivity) {
    case 'LookingAtMonitor':
      ambientLabel = 'Memeriksa Monitor 💻';
      break;
    case 'LookingAround':
      ambientLabel = 'Mengamati Suasana Kantor 👀';
      break;
    case 'Stretching':
      ambientLabel = 'Peregangan Badan 🧘';
      break;
    case 'VisitingCoffeeCorner':
      ambientLabel = 'Rehat di Coffee Corner ☕';
      break;
    case 'ReadingOrInspecting':
      ambientLabel = 'Mengecek Dokumentasi 📋';
      break;
    case 'CasualConversation':
      ambientLabel = amb.socialRole === 'speaker' ? 'Berbicara Santai 💬' : 'Mendengarkan Cerita 👂';
      break;
    case 'Walking':
      ambientLabel = 'Melangkah ke Area Lain 🚶';
      break;
    case 'ReturningToDesk':
      ambientLabel = 'Kembali ke Meja Kerja 🪑';
      break;
    case 'StandingIdle':
      ambientLabel = isOutageStark ? 'Investigasi Server ⚠️' : 'Berdiri di Area Santai 🌿';
      break;
    default:
      ambientLabel = 'Santai di Meja ☕';
  }

  // Handle special actual states
  if (isOutageStark) {
    ambientLabel = 'Investigasi Server ⚠️';
  } else if (amb.actualState === 'Blocked') {
    ambientLabel = 'Terblokir / Investigasi ⚠️';
  } else if (amb.actualState === 'Waiting') {
    ambientLabel = 'Standby Menunggu Approval ⏳';
  } else if (amb.actualState === 'Offline') {
    ambientLabel = 'Dormant / Offline 🔌';
  }

  return {
    id,
    targetPos: amb.targetPosition,
    targetRotY: amb.targetRotationY,
    action: amb.characterAction,
    isSeated: isOutageStark ? false : (isWorking ? (amb.targetPosition[2] > 0.6 && amb.targetPosition[2] < 1.0) : amb.isSeated),
    isActive: isWorking, // True for running AI task or active outage investigation
    actualState: amb.actualState,
    ambientActivity: amb.ambientActivity,
    ambientLabel: isOutageStark ? 'Investigasi Server ⚠️' : (isWorking ? getHumanStatus(currentNode).label : ambientLabel),
    socialRole: amb.socialRole,
  };
}
