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
import { WORKSTATION_CONFIG, BAYZERO_SEAT_ANCHOR, SCOUT_SEAT_ANCHOR } from '../config/layoutAnchors';

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
    (threadId.toLowerCase().includes('dongeng')
      ? 'dongeng'
      : threadId.toLowerCase().includes('job')
      ? 'career_ops'
      : 'article');

  const isDongengPipeline =
    taskType === 'dongeng' ||
    currentNode === 'curate_node' ||
    currentNode === 'render_cover_node' ||
    currentNode === 'post_cms_node';

  const isJobPipeline =
    taskType === 'career_ops' ||
    currentNode.startsWith('job_') ||
    currentNode.includes('job') ||
    threadId?.includes('job') ||
    details?.pipeline === 'career_ops' ||
    details?.role === 'career_intelligence';

  const isIdle =
    currentNode === 'IDLE' ||
    currentNode === 'idle_coffee' ||
    currentNode === 'STREAM_INIT';

  const isHousekeeping =
    currentNode === 'housekeeping' ||
    currentNode === 'housekeeping_node' ||
    details?.task_type === 'housekeeping' ||
    details?.action_type === 'housekeeping' ||
    threadId === 'system';

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
      simulator.updateActualState('scout', 'Offline');
      return;
    }

    if (isDegraded) {
      // Microservice Outage: Bay-Zero (SOP Auditor & Lead Inspector) rushes to the server cluster to troubleshoot & inspect!
      const serverTargetPos: [number, number, number] = [5.0, 0, -0.45];
      const serverTargetRotY = Math.PI / 2; // Facing East (+X) directly towards the server racks
      simulator.updateActualState('bayzero', 'Blocked', serverTargetPos, serverTargetRotY, 'confused_scratch');
      simulator.updateActualState('stark', 'Idle');
      simulator.updateActualState('usagi', 'Idle');
      simulator.updateActualState('scout', 'Idle');
      return;
    }

    if (isHousekeeping) {
      // Pembersihan sistem adalah tugas Robot Vacuum Cleaner (Janitor Droid).
      // Seluruh agen kru tetap santai di meja masing-masing (duduk tenang).
      simulator.updateActualState('stark', 'Idle');
      simulator.updateActualState('usagi', 'Idle');
      simulator.updateActualState('bayzero', 'Idle');
      simulator.updateActualState('scout', 'Idle');
      return;
    }

    if (isIdle) {
      simulator.updateActualState('stark', 'Idle');
      simulator.updateActualState('usagi', 'Idle');
      simulator.updateActualState('bayzero', 'Idle');
      simulator.updateActualState('scout', 'Idle');
    } else if (isFailed) {
      // Blocked / Failure state
      if (isJobPipeline) {
        simulator.updateActualState('scout', 'Blocked', SCOUT_SEAT_ANCHOR.seatWorldPosition, SCOUT_SEAT_ANCHOR.seatWorldRotationY, 'confused_scratch');
        simulator.updateActualState('stark', 'Idle');
        simulator.updateActualState('usagi', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
      } else if (isDongengPipeline) {
        simulator.updateActualState('usagi', 'Blocked', WORKSTATION_CONFIG.usagi.seatWorldPosition, WORKSTATION_CONFIG.usagi.seatWorldRotationY, 'confused_scratch');
        simulator.updateActualState('stark', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
        simulator.updateActualState('scout', 'Idle');
      } else {
        simulator.updateActualState('stark', 'Blocked', WORKSTATION_CONFIG.stark.seatWorldPosition, WORKSTATION_CONFIG.stark.seatWorldRotationY, 'confused_scratch');
        simulator.updateActualState('usagi', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
        simulator.updateActualState('scout', 'Idle');
      }
    } else if (isAwaitingApproval) {
      // Waiting for human approval
      if (isJobPipeline) {
        simulator.updateActualState('scout', 'Waiting', SCOUT_SEAT_ANCHOR.seatWorldPosition, SCOUT_SEAT_ANCHOR.seatWorldRotationY, 'observing');
        simulator.updateActualState('stark', 'Idle');
        simulator.updateActualState('usagi', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
      } else if (isDongengPipeline) {
        simulator.updateActualState('usagi', 'Waiting', WORKSTATION_CONFIG.usagi.seatWorldPosition, WORKSTATION_CONFIG.usagi.seatWorldRotationY, 'observing');
        simulator.updateActualState('stark', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
        simulator.updateActualState('scout', 'Idle');
      } else {
        simulator.updateActualState('stark', 'Waiting', WORKSTATION_CONFIG.stark.seatWorldPosition, WORKSTATION_CONFIG.stark.seatWorldRotationY, 'observing');
        simulator.updateActualState('usagi', 'Idle');
        simulator.updateActualState('bayzero', 'Waiting', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'observing');
        simulator.updateActualState('scout', 'Idle');
      }
    } else if (isSOPNode) {
      // SOP Validation phase: Bay-Zero works at central table, active author waits
      simulator.updateActualState('bayzero', 'Working', BAYZERO_SEAT_ANCHOR.seatWorldPosition, BAYZERO_SEAT_ANCHOR.seatWorldRotationY, 'inspecting_sop');
      if (isJobPipeline) {
        simulator.updateActualState('scout', 'Waiting', SCOUT_SEAT_ANCHOR.seatWorldPosition, SCOUT_SEAT_ANCHOR.seatWorldRotationY, 'observing');
        simulator.updateActualState('stark', 'Idle');
        simulator.updateActualState('usagi', 'Idle');
      } else if (isDongengPipeline) {
        simulator.updateActualState('usagi', 'Waiting', WORKSTATION_CONFIG.usagi.seatWorldPosition, WORKSTATION_CONFIG.usagi.seatWorldRotationY, 'observing');
        simulator.updateActualState('stark', 'Idle');
        simulator.updateActualState('scout', 'Idle');
      } else {
        simulator.updateActualState('stark', 'Waiting', WORKSTATION_CONFIG.stark.seatWorldPosition, WORKSTATION_CONFIG.stark.seatWorldRotationY, 'observing');
        simulator.updateActualState('usagi', 'Idle');
        simulator.updateActualState('scout', 'Idle');
      }
    } else if (isJobPipeline) {
      // Career Intelligence pipeline: Scout works at seat opposite Bay-Zero
      let scoutTaskPos: [number, number, number] = SCOUT_SEAT_ANCHOR.seatWorldPosition;
      let scoutTaskRotY = SCOUT_SEAT_ANCHOR.seatWorldRotationY;
      let scoutTaskAction: CharacterAction = 'intense_typing';

      if (currentNode === 'job_scrape_node' || currentNode === 'job_scrape') {
        scoutTaskAction = 'looking_monitor';
      } else if (isComplete) {
        scoutTaskRotY = Math.PI * 0.8;
        scoutTaskAction = 'success_celebration';
      }

      simulator.updateActualState('scout', 'Working', scoutTaskPos, scoutTaskRotY, scoutTaskAction);
      simulator.updateActualState('stark', 'Idle');
      simulator.updateActualState('usagi', 'Idle');
      simulator.updateActualState('bayzero', 'Idle');
    } else if (isDongengPipeline) {
      // Dongeng pipeline: Usagi works, Stark, Scout and Bay-Zero are Idle
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
      simulator.updateActualState('scout', 'Idle');
    } else {
      // Article pipeline: Stark works, Usagi, Scout and Bay-Zero are Idle
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
      simulator.updateActualState('scout', 'Idle');
    }
  }, [currentNode, status, isDongengPipeline, isJobPipeline, isIdle, isSOPNode, isAwaitingApproval, isFailed, isComplete, connected, isDegraded]);

  // Visual state hook updated efficiently on animation tick
  const [characterStates, setCharacterStates] = useState<Record<WorkerId, CharacterVisualState>>(() => ({
    stark: buildVisualState('stark', simulator.getWorkerState('stark'), currentNode, isDegraded),
    usagi: buildVisualState('usagi', simulator.getWorkerState('usagi'), currentNode, isDegraded),
    bayzero: buildVisualState('bayzero', simulator.getWorkerState('bayzero'), currentNode, isDegraded),
    scout: buildVisualState('scout', simulator.getWorkerState('scout'), currentNode, isDegraded),
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
        scout: buildVisualState('scout', simulator.getWorkerState('scout'), currentNode, isDegraded),
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
  const isOutageBayZero = id === 'bayzero' && isDegraded;
  const isWorking = amb.actualState === 'Working' || isOutageBayZero;

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
      ambientLabel = isOutageBayZero ? 'Investigasi Server ⚠️' : 'Berdiri di Area Santai 🌿';
      break;
    default:
      ambientLabel = 'Santai di Meja ☕';
  }

  // Handle special actual states
  if (isOutageBayZero) {
    ambientLabel = 'Investigasi Server ⚠️';
  } else if (amb.actualState === 'Blocked') {
    ambientLabel = 'Terblokir / Investigasi ⚠️';
  } else if (amb.actualState === 'Waiting') {
    ambientLabel = 'Standby Menunggu Approval ⏳';
  } else if (amb.actualState === 'Offline') {
    ambientLabel = 'Dormant / Offline 🔌';
  }

  const isHousekeeping =
    currentNode === 'housekeeping' ||
    currentNode === 'housekeeping_node';

  // Aksi yang mewajibkan karakter berdiri:
  const isStandingAction =
    amb.characterAction === 'drawing_canvas' ||
    amb.characterAction === 'searching_archive' ||
    amb.characterAction === 'walk_to_desk' ||
    amb.characterAction === 'visiting_coffee' ||
    amb.ambientActivity === 'Walking' ||
    amb.ambientActivity === 'ReturningToDesk' ||
    amb.ambientActivity === 'StandingIdle' ||
    isOutageBayZero;

  // Jika sedang bekerja di meja workstation, karakter selalu duduk rapi di kursinya
  const isSeated = isStandingAction ? false : (isWorking ? true : amb.isSeated);

  let displayLabel = ambientLabel;
  if (isOutageBayZero) {
    displayLabel = 'Investigasi Server ⚠️';
  } else if (isWorking && !isHousekeeping) {
    displayLabel = getHumanStatus(currentNode).label;
  }

  return {
    id,
    targetPos: amb.targetPosition,
    targetRotY: amb.targetRotationY,
    action: amb.characterAction,
    isSeated,
    isActive: isWorking, // True for running AI task or active outage investigation
    actualState: amb.actualState,
    ambientActivity: amb.ambientActivity,
    ambientLabel: displayLabel,
    socialRole: amb.socialRole,
  };
}
