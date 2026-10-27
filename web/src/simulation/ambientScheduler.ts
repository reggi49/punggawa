/**
 * ambientScheduler.ts
 * Persistent, believable ambient life simulation scheduler for Punggawa 3D Office.
 * Coordinates realistic workplace behaviors (seated work, stretching, looking around,
 * walking to coffee corner/lounge/server rack, and occasional social interactions).
 *
 * Runs 100% locally with zero LLM/API requests, strictly decoupled from real AI task state.
 */
import * as THREE from 'three';
import { WorkerId, AmbientActivityType, ActualAgentState, CharacterAction } from '../types';
import { OfficePOI, OFFICE_POIS, buildSafePath } from './officeNavigation';

export interface WorkerAmbientState {
  id: WorkerId;
  actualState: ActualAgentState;
  ambientActivity: AmbientActivityType;

  // Spatial & Movement
  currentPosition: [number, number, number];
  targetPosition: [number, number, number];
  targetRotationY: number;
  isSeated: boolean;

  // Waypoint Pathfinding
  pathQueue: [number, number, number][];
  destinationPOI: OfficePOI | null;

  // Timing & Cooldowns
  activityStartTime: number;
  activityDuration: number;
  cooldowns: Record<string, number>; // POI or activity ID -> timestamp when allowed
  recentActivities: AmbientActivityType[]; // History of last activities to prevent immediate repeats

  // Social Interaction
  socialPartnerId: WorkerId | null;
  socialRole: 'speaker' | 'listener' | null;
  lastRoleSwapTime?: number;

  // Visual Character Action for Rigging
  characterAction: CharacterAction;

  // Task Target state when moving towards work or blocked spot
  taskTargetPos?: [number, number, number] | null;
  taskTargetRotY?: number;
  taskAction?: CharacterAction;
}

export class AmbientOfficeSimulator {
  private workers: Record<WorkerId, WorkerAmbientState>;
  private lastGlobalTick: number = 0;

  constructor() {
    const now = Date.now();
    this.lastGlobalTick = now;

    // Initial Staggered Offsets so characters never act simultaneously
    this.workers = {
      stark: {
        id: 'stark',
        actualState: 'Idle',
        ambientActivity: 'SeatedIdle',
        currentPosition: [...OFFICE_POIS.stark_desk.position],
        targetPosition: [...OFFICE_POIS.stark_desk.position],
        targetRotationY: OFFICE_POIS.stark_desk.rotationY,
        isSeated: true,
        pathQueue: [],
        destinationPOI: OFFICE_POIS.stark_desk,
        activityStartTime: now,
        activityDuration: 14000, // Starts with 14s seated idle
        cooldowns: { social: now + 25000, coffee: 0, server: 0, easel: 0, lounge: 0 },
        recentActivities: ['SeatedIdle'],
        socialPartnerId: null,
        socialRole: null,
        characterAction: 'idle_coffee',
      },
      usagi: {
        id: 'usagi',
        actualState: 'Idle',
        ambientActivity: 'LookingAtMonitor',
        currentPosition: [...OFFICE_POIS.usagi_desk.position],
        targetPosition: [...OFFICE_POIS.usagi_desk.position],
        targetRotationY: OFFICE_POIS.usagi_desk.rotationY,
        isSeated: true,
        pathQueue: [],
        destinationPOI: OFFICE_POIS.usagi_desk,
        activityStartTime: now,
        activityDuration: 20000, // Starts with 20s looking at monitor
        cooldowns: { social: now + 40000, coffee: 0, server: 0, easel: 0, lounge: 0 },
        recentActivities: ['LookingAtMonitor'],
        socialPartnerId: null,
        socialRole: null,
        characterAction: 'looking_monitor',
      },
      bayzero: {
        id: 'bayzero',
        actualState: 'Idle',
        ambientActivity: 'LookingAround',
        currentPosition: [...OFFICE_POIS.bayzero_desk.position],
        targetPosition: [...OFFICE_POIS.bayzero_desk.position],
        targetRotationY: OFFICE_POIS.bayzero_desk.rotationY,
        isSeated: true,
        pathQueue: [],
        destinationPOI: OFFICE_POIS.bayzero_desk,
        activityStartTime: now,
        activityDuration: 26000, // Starts with 26s looking around
        cooldowns: { social: now + 55000, coffee: 0, server: 0, easel: 0, lounge: 0 },
        recentActivities: ['LookingAround'],
        socialPartnerId: null,
        socialRole: null,
        characterAction: 'looking_around',
      },
      scout: {
        id: 'scout',
        actualState: 'Idle',
        ambientActivity: 'LookingAtMonitor',
        currentPosition: [...OFFICE_POIS.scout_desk.position],
        targetPosition: [...OFFICE_POIS.scout_desk.position],
        targetRotationY: OFFICE_POIS.scout_desk.rotationY,
        isSeated: true,
        pathQueue: [],
        destinationPOI: OFFICE_POIS.scout_desk,
        activityStartTime: now,
        activityDuration: 24000,
        cooldowns: { social: now + 60000, coffee: 0, server: 0, easel: 0, lounge: 0 },
        recentActivities: ['LookingAtMonitor'],
        socialPartnerId: null,
        socialRole: null,
        characterAction: 'looking_monitor',
      },
    };
  }

  /**
   * Synchronizes genuine AI job status from backend/LangGraph.
   * Cancels ambient wandering and returns the worker to their workstation if needed.
   */
  public updateActualState(
    workerId: WorkerId,
    newState: ActualAgentState,
    taskWorkstationPos?: [number, number, number],
    taskRotationY?: number,
    taskAction?: CharacterAction
  ) {
    const w = this.workers[workerId];
    if (!w) return;

    const previousState = w.actualState;
    w.actualState = newState;

    if (newState === 'Working') {
      // 1. CANCEL AMBIENT ACTIVITY IMMEDIATELY!
      if (w.socialPartnerId) {
        this.endSocialInteraction(workerId);
      }

      w.taskTargetPos = taskWorkstationPos ? [...taskWorkstationPos] : null;
      w.taskTargetRotY = taskRotationY;
      w.taskAction = taskAction || 'intense_typing';
      w.destinationPOI = null;

      if (taskWorkstationPos) {
        const destVec = new THREE.Vector3(...taskWorkstationPos);
        const currVec = new THREE.Vector3(...w.currentPosition);
        if (currVec.distanceTo(destVec) > 0.35) {
          const path = buildSafePath(w.currentPosition, taskWorkstationPos);
          if (path.length > 0) {
            w.pathQueue = path;
            w.ambientActivity = 'Walking';
            w.characterAction = 'walk_to_desk';
            w.targetPosition = [...w.pathQueue[0]];
            w.isSeated = false;
            return;
          }
        }
        w.pathQueue = [];
        w.targetPosition = [...taskWorkstationPos];
        w.currentPosition = [...taskWorkstationPos];
        if (taskRotationY !== undefined) {
          w.targetRotationY = taskRotationY;
        }
        w.characterAction = taskAction || 'intense_typing';
        w.isSeated = !taskAction || taskAction === 'intense_typing';
        w.ambientActivity = w.isSeated ? 'SeatedIdle' : 'StandingIdle';
      }
    } else if (newState === 'Blocked') {
      // 2. BLOCKED: Restrained confused / thinking posture or investigating server outage
      if (w.socialPartnerId) {
        this.endSocialInteraction(workerId);
      }
      if (taskWorkstationPos) {
        w.taskTargetPos = [...taskWorkstationPos];
        w.taskTargetRotY = taskRotationY !== undefined ? taskRotationY : Math.PI / 2;
        w.taskAction = taskAction || 'confused_scratch';
        w.destinationPOI = null;

        const destVec = new THREE.Vector3(...taskWorkstationPos);
        const currVec = new THREE.Vector3(...w.currentPosition);
        if (currVec.distanceTo(destVec) > 0.35) {
          const path = buildSafePath(w.currentPosition, taskWorkstationPos);
          if (path.length > 0) {
            w.pathQueue = path;
            w.ambientActivity = 'Walking';
            w.characterAction = 'walk_to_desk';
            w.targetPosition = [...w.pathQueue[0]];
            w.isSeated = false;
            return;
          }
        }
        w.pathQueue = [];
        w.targetPosition = [...taskWorkstationPos];
        w.currentPosition = [...taskWorkstationPos];
        w.targetRotationY = w.taskTargetRotY;
        w.characterAction = w.taskAction;
        w.isSeated = false;
        w.ambientActivity = 'StandingIdle';
      } else {
        const homeDesk = OFFICE_POIS[`${workerId}_desk`];
        if (homeDesk) {
          const destVec = new THREE.Vector3(...homeDesk.position);
          const currVec = new THREE.Vector3(...w.currentPosition);
          if (currVec.distanceTo(destVec) > 0.35) {
            const path = buildSafePath(w.currentPosition, homeDesk);
            if (path.length > 0) {
              w.pathQueue = path;
              w.ambientActivity = 'Walking';
              w.characterAction = 'walk_to_desk';
              w.targetPosition = [...w.pathQueue[0]];
              w.isSeated = false;
              w.destinationPOI = homeDesk;
              return;
            }
          }
          w.targetPosition = [...homeDesk.position];
          w.currentPosition = [...homeDesk.position];
          w.targetRotationY = homeDesk.rotationY;
        }
        w.pathQueue = [];
        w.isSeated = true;
        w.ambientActivity = 'SeatedIdle';
        w.characterAction = 'confused_scratch';
        w.destinationPOI = homeDesk || null;
      }
    } else if (newState === 'Waiting') {
      // 3. WAITING: Attentive observing at desk/podium, awaiting user approval or SOP
      if (w.socialPartnerId) {
        this.endSocialInteraction(workerId);
      }
      const homeDesk = OFFICE_POIS[`${workerId}_desk`];
      if (homeDesk) {
        const destVec = new THREE.Vector3(...homeDesk.position);
        const currVec = new THREE.Vector3(...w.currentPosition);
        if (currVec.distanceTo(destVec) > 0.35) {
          const path = buildSafePath(w.currentPosition, homeDesk);
          if (path.length > 0) {
            w.pathQueue = path;
            w.ambientActivity = 'Walking';
            w.characterAction = 'walk_to_desk';
            w.targetPosition = [...w.pathQueue[0]];
            w.isSeated = false;
            w.destinationPOI = homeDesk;
            return;
          }
        }
        w.targetPosition = [...homeDesk.position];
        w.currentPosition = [...homeDesk.position];
        w.targetRotationY = homeDesk.rotationY;
      }
      w.pathQueue = [];
      w.isSeated = true;
      w.ambientActivity = 'LookingAtMonitor';
      w.characterAction = 'observing';
      w.destinationPOI = homeDesk || null;
    } else if (newState === 'Offline') {
      // 4. OFFLINE: Low-power dormant posture at desk, strictly no social/breaks
      if (w.socialPartnerId) {
        this.endSocialInteraction(workerId);
      }
      w.pathQueue = [];
      const homeDesk = OFFICE_POIS[`${workerId}_desk`];
      if (homeDesk) {
        w.targetPosition = [...homeDesk.position];
        w.currentPosition = [...homeDesk.position];
        w.targetRotationY = homeDesk.rotationY;
      }
      w.isSeated = true;
      w.ambientActivity = 'SeatedIdle';
      w.characterAction = 'offline_rest';
      w.destinationPOI = homeDesk || null;
    } else if (previousState !== 'Idle' && newState === 'Idle') {
      // 5. Job or special state finished -> smoothly return to desk along safe path
      const homeDeskKey = `${workerId}_desk`;
      const homeDesk = OFFICE_POIS[homeDeskKey];
      if (homeDesk) {
        const destVec = new THREE.Vector3(...homeDesk.position);
        const currVec = new THREE.Vector3(...w.currentPosition);
        if (currVec.distanceTo(destVec) > 0.35) {
          const path = buildSafePath(w.currentPosition, homeDesk);
          if (path.length > 0) {
            w.pathQueue = path;
            w.ambientActivity = 'ReturningToDesk';
            w.characterAction = 'walk_to_desk';
            w.targetPosition = [...w.pathQueue[0]];
            w.isSeated = false;
            w.destinationPOI = homeDesk;
            return;
          }
        }
        w.targetPosition = [...homeDesk.position];
        w.currentPosition = [...homeDesk.position];
        w.targetRotationY = homeDesk.rotationY;
        w.isSeated = true;
        w.destinationPOI = homeDesk;
      }
      w.pathQueue = [];
      w.ambientActivity = 'SeatedIdle';
      w.activityStartTime = Date.now();
      w.activityDuration = 15000 + Math.random() * 8000;
      w.characterAction = 'idle_coffee';
      w.socialPartnerId = null;
      w.socialRole = null;
    }
  }

  /**
   * Main Simulation Step: Called in React Three Fiber useFrame
   */
  public tick(currentTimeMs: number, delta: number) {
    // 1. Tab Pause / Inactivity Safeguard
    if (this.lastGlobalTick > 0 && currentTimeMs - this.lastGlobalTick > 8000) {
      const gap = currentTimeMs - this.lastGlobalTick;
      for (const w of Object.values(this.workers)) {
        w.activityStartTime += gap;
      }
    }
    this.lastGlobalTick = currentTimeMs;

    const safeDelta = Math.min(delta, 0.1);
    const walkingSpeed = 1.85; // units per second in world space

    for (const [idStr, w] of Object.entries(this.workers)) {
      const id = idStr as WorkerId;

      // 1. Waypoint Navigation along Path (Evaluates for ANY worker actively walking!)
      if (w.pathQueue.length > 0) {
        const currentTarget = new THREE.Vector3(...w.pathQueue[0]);
        const currentPosV = new THREE.Vector3(...w.currentPosition);
        const dist = currentPosV.distanceTo(currentTarget);

        const step = walkingSpeed * safeDelta;

        if (dist <= step || dist < 0.20) {
          // Reached current waypoint!
          w.currentPosition = [currentTarget.x, currentTarget.y, currentTarget.z];
          w.pathQueue.shift();

          if (w.pathQueue.length === 0) {
            // Arrived at final destination!
            this.handleArrivalAtTarget(w, currentTimeMs);
          } else {
            // Target next waypoint in line
            w.targetPosition = [...w.pathQueue[0]];
            w.isSeated = false;
            w.characterAction = 'walk_to_desk';
          }
        } else {
          // Step incrementally towards current waypoint
          const moveDir = new THREE.Vector3().subVectors(currentTarget, currentPosV).normalize();
          currentPosV.addScaledVector(moveDir, step);
          w.currentPosition = [currentPosV.x, currentPosV.y, currentPosV.z];
          w.targetPosition = [...w.pathQueue[0]];
          w.isSeated = false;
          w.characterAction = 'walk_to_desk';
        }
        continue;
      }

      // Real work or blocked/waiting/offline takes 100% priority over routine ambient behavior
      if (w.actualState !== 'Idle') {
        continue;
      }

      // 2. Active Social Interaction State
      if (w.ambientActivity === 'CasualConversation' && w.socialPartnerId) {
        const partner = this.workers[w.socialPartnerId];
        if (!partner || partner.actualState !== 'Idle') {
          this.endSocialInteraction(id);
          continue;
        }

        if (
          !w.lastRoleSwapTime ||
          currentTimeMs - w.lastRoleSwapTime > 6000
        ) {
          w.lastRoleSwapTime = currentTimeMs;
          if (w.socialRole === 'speaker') {
            w.socialRole = 'listener';
            partner.socialRole = 'speaker';
          } else {
            w.socialRole = 'speaker';
            partner.socialRole = 'listener';
          }
        }

        const elapsedSocial = currentTimeMs - w.activityStartTime;
        if (elapsedSocial >= w.activityDuration) {
          this.endSocialInteraction(id);
        }
        continue;
      }

      // 3. Evaluate Activity Timer Expiration for Stationary Idle
      const elapsed = currentTimeMs - w.activityStartTime;
      if (elapsed >= w.activityDuration) {
        this.selectNextAmbientActivity(w, currentTimeMs);
      }
    }
  }

  /**
   * Final destination arrival handler across both tasks and ambient routines
   */
  private handleArrivalAtTarget(w: WorkerAmbientState, now: number) {
    if (w.actualState === 'Working') {
      if (w.taskTargetPos) {
        w.currentPosition = [...w.taskTargetPos];
        w.targetPosition = [...w.taskTargetPos];
      }
      if (w.taskTargetRotY !== undefined) {
        w.targetRotationY = w.taskTargetRotY;
      }
      w.characterAction = w.taskAction || 'intense_typing';
      w.isSeated = !w.taskAction || w.taskAction === 'intense_typing';
      w.ambientActivity = w.isSeated ? 'SeatedIdle' : 'StandingIdle';
      return;
    }

    if (w.actualState === 'Blocked') {
      if (w.taskTargetPos) {
        w.currentPosition = [...w.taskTargetPos];
        w.targetPosition = [...w.taskTargetPos];
      }
      if (w.taskTargetRotY !== undefined) {
        w.targetRotationY = w.taskTargetRotY;
      }
      w.characterAction = w.taskAction || 'confused_scratch';
      w.isSeated = false;
      w.ambientActivity = 'StandingIdle';
      return;
    }

    if (w.actualState === 'Waiting') {
      const homeDesk = OFFICE_POIS[`${w.id}_desk`];
      if (homeDesk) {
        w.currentPosition = [...homeDesk.position];
        w.targetPosition = [...homeDesk.position];
        w.targetRotationY = homeDesk.rotationY;
      }
      w.characterAction = 'observing';
      w.isSeated = true;
      w.ambientActivity = 'LookingAtMonitor';
      return;
    }

    // Default Idle POI arrival
    const poi = w.destinationPOI;
    if (!poi) {
      this.settleAtDesk(w, now);
      return;
    }
    this.handleArrivalAtPOI(w, now);
  }

  /**
   * Decides what to do when a character arrives at their target POI
   */
  private handleArrivalAtPOI(w: WorkerAmbientState, now: number) {
    const poi = w.destinationPOI;
    if (!poi) {
      this.settleAtDesk(w, now);
      return;
    }

    w.currentPosition = [...poi.position];
    w.targetPosition = [...poi.position];
    w.targetRotationY = poi.rotationY;
    w.isSeated = poi.isSeated;
    w.activityStartTime = now;

    switch (poi.type) {
      case 'desk':
        this.settleAtDesk(w, now);
        break;

      case 'coffee':
        w.ambientActivity = 'VisitingCoffeeCorner';
        w.characterAction = 'visiting_coffee';
        w.activityDuration = 12000 + Math.random() * 5000;
        w.cooldowns.coffee = now + 65000; // 65s cooldown
        this.recordActivity(w, 'VisitingCoffeeCorner');
        break;

      case 'lounge':
        w.ambientActivity = 'SeatedIdle';
        w.characterAction = 'idle_coffee';
        w.activityDuration = 15000 + Math.random() * 7000;
        w.cooldowns.lounge = now + 75000;
        this.recordActivity(w, 'SeatedIdle');
        break;

      case 'server':
        w.ambientActivity = 'ReadingOrInspecting';
        w.characterAction = 'searching_archive';
        w.activityDuration = 13000 + Math.random() * 5000;
        w.cooldowns.server = now + 80000;
        this.recordActivity(w, 'ReadingOrInspecting');
        break;

      case 'easel':
        w.ambientActivity = 'ReadingOrInspecting';
        w.characterAction = 'drawing_canvas';
        w.activityDuration = 13000 + Math.random() * 5000;
        w.cooldowns.easel = now + 80000;
        this.recordActivity(w, 'ReadingOrInspecting');
        break;

      case 'social':
        w.ambientActivity = 'CasualConversation';
        w.characterAction = 'casual_conversation';
        w.activityDuration = 12000 + Math.random() * 4000;
        w.cooldowns.social = now + 85000;
        w.lastRoleSwapTime = now;
        this.recordActivity(w, 'CasualConversation');
        break;

      case 'lookout':
        w.ambientActivity = 'StandingIdle';
        w.characterAction = 'looking_around';
        w.activityDuration = 11000 + Math.random() * 5000;
        w.cooldowns.lookout = now + 65000;
        this.recordActivity(w, 'StandingIdle');
        break;

      default:
        this.settleAtDesk(w, now);
    }
  }

  /**
   * Returns a character back to their home desk
   */
  private settleAtDesk(w: WorkerAmbientState, now: number) {
    const homeDesk = OFFICE_POIS[`${w.id}_desk`];
    if (homeDesk) {
      w.currentPosition = [...homeDesk.position];
      w.targetPosition = [...homeDesk.position];
      w.targetRotationY = homeDesk.rotationY;
      w.isSeated = true;
    }
    w.ambientActivity = 'SeatedIdle';
    w.characterAction = 'idle_coffee';
    w.destinationPOI = homeDesk || null;
    w.activityStartTime = now;
    w.activityDuration = 15000 + Math.random() * 10000;
    w.socialPartnerId = null;
    w.socialRole = null;
    this.recordActivity(w, 'SeatedIdle');
  }

  /**
   * Appends an activity to the worker's recent activity history
   */
  private recordActivity(w: WorkerAmbientState, act: AmbientActivityType) {
    if (!w.recentActivities) w.recentActivities = [];
    w.recentActivities.push(act);
    if (w.recentActivities.length > 4) {
      w.recentActivities.shift();
    }
  }

  /**
   * Weighted Ambient Activity Decision Engine.
   * Calibrated strictly to the target distribution:
   * - Seated idle or looking around: 50%
   * - Small posture adjustment or stretching: 18%
   * - Walking to an available point of interest: 15%
   * - Casual social interaction: 10%
   * - Another context-appropriate idle activity: 7%
   *
   * Includes recent history weighting & simultaneous movement limits.
   */
  private selectNextAmbientActivity(w: WorkerAmbientState, now: number) {
    const isAtDesk = w.destinationPOI?.type === 'desk' || (!w.destinationPOI && w.isSeated);

    // If currently away from desk (at Coffee / Lounge / Server / Lookout), the natural next step is returning to desk!
    if (!isAtDesk) {
      const homeDesk = OFFICE_POIS[`${w.id}_desk`];
      if (homeDesk) {
        w.ambientActivity = 'ReturningToDesk';
        w.characterAction = 'walk_to_desk';
        w.isSeated = false;
        w.destinationPOI = homeDesk;
        w.pathQueue = buildSafePath(w.currentPosition, homeDesk);
        w.activityStartTime = now;
        w.activityDuration = 30000; // Safe timeout
      } else {
        this.settleAtDesk(w, now);
      }
      return;
    }

    // Limit simultaneous movement: If another worker is currently walking, prefer staying at desk
    const isAnotherWorkerWalking = Object.values(this.workers).some(
      (other) =>
        other.id !== w.id &&
        (other.pathQueue.length > 0 ||
          other.ambientActivity === 'Walking' ||
          other.ambientActivity === 'ReturningToDesk')
    );

    const roll = Math.random();

    // 1. Casual Social Interaction (~10%)
    if (!isAnotherWorkerWalking && roll < 0.10 && this.canInitiateSocialInteraction(w, now)) {
      this.startSocialInteraction(w, now);
      return;
    }

    // 2. Walking to Nearby Point of Interest (~15%)
    if (!isAnotherWorkerWalking && roll >= 0.10 && roll < 0.25) {
      const availablePOI = this.pickSuitablePOI(w, now);
      if (availablePOI) {
        w.ambientActivity = 'Walking';
        w.characterAction = 'walk_to_desk';
        w.isSeated = false;
        w.destinationPOI = availablePOI;
        w.pathQueue = buildSafePath(w.currentPosition, availablePOI);
        w.activityStartTime = now;
        w.activityDuration = 30000;
        this.recordActivity(w, 'Walking');
        return;
      }
    }

    // 3. Desk In-Place Variations (Remaining ~75% of time)
    // Sub-distribution among eligible in-place behaviors:
    // - Seated idle or looking around: ~50% total
    //   -> SeatedIdle: ~28%
    //   -> LookingAround: ~22%
    // - Small posture adjustment or stretching: ~18% total
    //   -> Stretching: ~18%
    // - Another context-appropriate idle activity: ~7% total
    //   -> LookingAtMonitor: ~7%
    const deskRoll = Math.random();
    w.isSeated = true;
    w.activityStartTime = now;

    // Check recent history to prevent back-to-back repetitions
    const lastActivity = w.recentActivities[w.recentActivities.length - 1];

    if (deskRoll < 0.24 && lastActivity !== 'Stretching') {
      // ~18% stretching
      w.ambientActivity = 'Stretching';
      w.characterAction = 'stretching';
      w.activityDuration = 4500 + Math.random() * 2500;
    } else if (deskRoll < 0.33 && lastActivity !== 'LookingAtMonitor') {
      // ~7% looking at monitor / tech review
      w.ambientActivity = 'LookingAtMonitor';
      w.characterAction = 'looking_monitor';
      w.activityDuration = 8000 + Math.random() * 5000;
    } else if (deskRoll < 0.62 && lastActivity !== 'LookingAround') {
      // ~22% looking around office
      w.ambientActivity = 'LookingAround';
      w.characterAction = 'looking_around';
      w.activityDuration = 6000 + Math.random() * 4500;
    } else {
      // ~28% seated idle relax
      w.ambientActivity = 'SeatedIdle';
      w.characterAction = 'idle_coffee';
      w.activityDuration = 12000 + Math.random() * 8000;
    }

    this.recordActivity(w, w.ambientActivity);
  }

  /**
   * Checks if an idle agent can initiate a casual discussion with another idle agent
   */
  private canInitiateSocialInteraction(initiator: WorkerAmbientState, now: number): boolean {
    if (initiator.actualState !== 'Idle') return false;
    if (initiator.cooldowns.social && initiator.cooldowns.social > now) return false;
    if (initiator.socialPartnerId) return false;
    if (initiator.pathQueue.length > 0) return false;

    // Check if anyone else is already in a social interaction
    const isAnySocialActive = Object.values(this.workers).some((w) => !!w.socialPartnerId);
    if (isAnySocialActive) return false;

    // Find another eligible idle worker
    const otherWorkers = Object.values(this.workers).filter(
      (candidate) =>
        candidate.id !== initiator.id &&
        candidate.actualState === 'Idle' &&
        (!candidate.cooldowns.social || candidate.cooldowns.social <= now) &&
        !candidate.socialPartnerId &&
        candidate.pathQueue.length === 0 &&
        (!candidate.destinationPOI || candidate.destinationPOI.type === 'desk')
    );

    return otherWorkers.length > 0;
  }

  /**
   * Coordinates a two-character casual meeting at the central plaza
   */
  private startSocialInteraction(initiator: WorkerAmbientState, now: number) {
    const candidates = Object.values(this.workers).filter(
      (candidate) =>
        candidate.id !== initiator.id &&
        candidate.actualState === 'Idle' &&
        (!candidate.cooldowns.social || candidate.cooldowns.social <= now) &&
        !candidate.socialPartnerId &&
        candidate.pathQueue.length === 0 &&
        (!candidate.destinationPOI || candidate.destinationPOI.type === 'desk')
    );

    if (candidates.length === 0) return;
    const partner = candidates[Math.floor(Math.random() * candidates.length)];

    // Target positions facing each other at Central Plaza
    const spotA = OFFICE_POIS.social_center_a;
    const spotB = OFFICE_POIS.social_center_b;

    // Setup Initiator (Speaker)
    initiator.socialPartnerId = partner.id;
    initiator.socialRole = 'speaker';
    initiator.lastRoleSwapTime = now;
    initiator.destinationPOI = spotA;
    initiator.ambientActivity = 'Walking';
    initiator.characterAction = 'walk_to_desk';
    initiator.isSeated = false;
    initiator.pathQueue = buildSafePath(initiator.currentPosition, spotA);
    initiator.cooldowns.social = now + 90000;
    this.recordActivity(initiator, 'Walking');

    // Setup Partner (Listener)
    partner.socialPartnerId = initiator.id;
    partner.socialRole = 'listener';
    partner.lastRoleSwapTime = now;
    partner.destinationPOI = spotB;
    partner.ambientActivity = 'Walking';
    partner.characterAction = 'walk_to_desk';
    partner.isSeated = false;
    partner.pathQueue = buildSafePath(partner.currentPosition, spotB);
    partner.cooldowns.social = now + 90000;
    this.recordActivity(partner, 'Walking');
  }

  /**
   * Safely terminates a social interaction and returns both characters to their desks
   */
  public endSocialInteraction(workerId: WorkerId) {
    const w = this.workers[workerId];
    if (!w) return;

    const partnerId = w.socialPartnerId;
    w.socialPartnerId = null;
    w.socialRole = null;

    if (partnerId) {
      const partner = this.workers[partnerId];
      if (partner) {
        partner.socialPartnerId = null;
        partner.socialRole = null;
        if (partner.actualState === 'Idle') {
          this.settleAtDesk(partner, Date.now());
        }
      }
    }

    if (w.actualState === 'Idle') {
      this.settleAtDesk(w, Date.now());
    }
  }

  /**
   * Selects an available Point of Interest tailored to character persona
   * Checks cooldowns and POI occupancy to prevent multiple characters crowding one spot.
   */
  private pickSuitablePOI(w: WorkerAmbientState, now: number): OfficePOI | null {
    const allPOIList = [
      OFFICE_POIS.coffee_counter,
      OFFICE_POIS.lounge_sofa_left,
      OFFICE_POIS.lounge_sofa_right,
      OFFICE_POIS.server_rack,
      OFFICE_POIS.art_easel,
      OFFICE_POIS.south_lookout,
    ];

    // Filter POIs that are not on cooldown AND not occupied by another character
    const checkCooldown = (key: string) => !w.cooldowns[key] || w.cooldowns[key] <= now;
    const isOccupied = (poiId: string) =>
      Object.values(this.workers).some(
        (other) => other.id !== w.id && other.destinationPOI?.id === poiId
      );

    const candidates = allPOIList.filter((poi) => {
      if (isOccupied(poi.id)) return false;
      return checkCooldown(poi.type);
    });

    if (candidates.length === 0) return null;

    // Role-specific affinities
    if (w.id === 'stark') {
      // Tech writer loves Server Rack & Coffee
      const starkFavs = candidates.filter((c) => c.type === 'server' || c.type === 'coffee');
      if (starkFavs.length > 0 && Math.random() < 0.7) {
        return starkFavs[Math.floor(Math.random() * starkFavs.length)];
      }
    } else if (w.id === 'usagi') {
      // Curator loves Art Easel & Coffee Lounge
      const usagiFavs = candidates.filter((c) => c.type === 'easel' || c.type === 'coffee' || c.type === 'lounge');
      if (usagiFavs.length > 0 && Math.random() < 0.75) {
        return usagiFavs[Math.floor(Math.random() * usagiFavs.length)];
      }
    } else if (w.id === 'bayzero') {
      // Quality lead loves Server Rack & Lookout
      const bayzeroFavs = candidates.filter((c) => c.type === 'server' || c.type === 'lookout');
      if (bayzeroFavs.length > 0 && Math.random() < 0.7) {
        return bayzeroFavs[Math.floor(Math.random() * bayzeroFavs.length)];
      }
    }

    return candidates[Math.floor(Math.random() * candidates.length)];
  }

  /**
   * Retrieves live simulation state for a worker
   */
  public getWorkerState(id: WorkerId): WorkerAmbientState {
    return this.workers[id];
  }

  /**
   * Retrieves all workers' live simulation states
   */
  public getAllWorkers(): Record<WorkerId, WorkerAmbientState> {
    return this.workers;
  }
}
