/**
 * layoutAnchors.ts
 * Single Source of Truth for 3D Workstations and Meeting Layouts.
 * Ensures Chair Seat Cushion Position === Worker Character Hip Anchor.
 */

export const WORKSTATION_DIMENSIONS = {
  width: 1.8,
  height: 0.74,
  depth: 0.85,
  seatOffsetZ: 0.58, // Local Z offset from desk center to seat center
  chairSeatY: 0.45,
  workerHipY: 0.46,
};

export const WORKSTATION_CONFIG = {
  stark: {
    deskPosition: [-3.2, 0, 1.1] as [number, number, number],
    deskRotationY: 0,
    seatWorldPosition: [-3.2, 0, 1.68] as [number, number, number],
    seatWorldRotationY: Math.PI,
  },
  usagi: {
    deskPosition: [3.2, 0, 1.1] as [number, number, number],
    deskRotationY: 0,
    seatWorldPosition: [3.2, 0, 1.68] as [number, number, number],
    seatWorldRotationY: Math.PI,
  },
};

export const MEETING_ZONE_CONFIG = {
  center: [0, 0, -0.5] as [number, number, number],
  tableRadius: 1.05,
  tableHeight: 0.74,
  chairRadius: 1.28,
  carpetRadius: 1.85,
  bayZeroAngle: 0.45, // Radians (~25.8 degrees)
};

// Exact Bay-Zero World Seat Anchor (Identical to Chair 0)
const bzSin = Math.sin(MEETING_ZONE_CONFIG.bayZeroAngle);
const bzCos = Math.cos(MEETING_ZONE_CONFIG.bayZeroAngle);

export const BAYZERO_SEAT_ANCHOR = {
  localChairPosition: [
    bzSin * MEETING_ZONE_CONFIG.chairRadius,
    0,
    bzCos * MEETING_ZONE_CONFIG.chairRadius,
  ] as [number, number, number],
  localChairRotationY: MEETING_ZONE_CONFIG.bayZeroAngle + Math.PI,
  seatWorldPosition: [
    MEETING_ZONE_CONFIG.center[0] + bzSin * MEETING_ZONE_CONFIG.chairRadius,
    0,
    MEETING_ZONE_CONFIG.center[2] + bzCos * MEETING_ZONE_CONFIG.chairRadius,
  ] as [number, number, number],
  seatWorldRotationY: MEETING_ZONE_CONFIG.bayZeroAngle + Math.PI,
  laptopLocalPosition: [
    bzSin * 0.75,
    MEETING_ZONE_CONFIG.tableHeight + 0.005,
    bzCos * 0.75,
  ] as [number, number, number],
  laptopLocalRotationY: MEETING_ZONE_CONFIG.bayZeroAngle,
};

// Kang Bos (Bay-Zero) Kanban Whiteboard Stand Anchor (Standing in front of the board)
export const BAYZERO_KANBAN_ANCHOR = {
  position: [-3.55, 0, -2.55] as [number, number, number],
  rotationY: 3.49, // Facing towards the Kanban Whiteboard
};

// Scout World Seat Anchor (Identical to Meeting Chair 2, opposite Bay-Zero)
const scAngle = MEETING_ZONE_CONFIG.bayZeroAngle + Math.PI;
const scSin = Math.sin(scAngle);
const scCos = Math.cos(scAngle);

export const SCOUT_SEAT_ANCHOR = {
  localChairPosition: [
    scSin * MEETING_ZONE_CONFIG.chairRadius,
    0,
    scCos * MEETING_ZONE_CONFIG.chairRadius,
  ] as [number, number, number],
  localChairRotationY: scAngle + Math.PI,
  seatWorldPosition: [
    MEETING_ZONE_CONFIG.center[0] + scSin * MEETING_ZONE_CONFIG.chairRadius,
    0,
    MEETING_ZONE_CONFIG.center[2] + scCos * MEETING_ZONE_CONFIG.chairRadius,
  ] as [number, number, number],
  seatWorldRotationY: scAngle + Math.PI,
  laptopLocalPosition: [
    scSin * 0.75,
    MEETING_ZONE_CONFIG.tableHeight + 0.005,
    scCos * 0.75,
  ] as [number, number, number],
  laptopLocalRotationY: scAngle,
};

export const WORKSTATION_ANCHORS = {
  stark: WORKSTATION_CONFIG.stark,
  usagi: WORKSTATION_CONFIG.usagi,
  bayzero: {
    deskPosition: BAYZERO_KANBAN_ANCHOR.position,
    deskRotationY: BAYZERO_KANBAN_ANCHOR.rotationY,
    seatWorldPosition: BAYZERO_KANBAN_ANCHOR.position,
    seatWorldRotationY: BAYZERO_KANBAN_ANCHOR.rotationY,
  },
  scout: {
    deskPosition: MEETING_ZONE_CONFIG.center,
    deskRotationY: 0,
    seatWorldPosition: SCOUT_SEAT_ANCHOR.seatWorldPosition,
    seatWorldRotationY: SCOUT_SEAT_ANCHOR.seatWorldRotationY,
  },
};

