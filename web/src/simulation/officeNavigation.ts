/**
 * officeNavigation.ts
 * Lightweight, collision-free waypoint navigation system for Punggawa 3D Office.
 * Guarantees natural walking paths between desks, coffee lounge, server rack, and art easel
 * without characters clipping through furniture or walking into walls.
 */
import * as THREE from 'three';
import { WORKSTATION_CONFIG, BAYZERO_SEAT_ANCHOR } from '../config/layoutAnchors';

export interface OfficePOI {
  id: string;
  name: string;
  position: [number, number, number];
  rotationY: number;
  isSeated: boolean;
  type: 'desk' | 'lounge' | 'coffee' | 'server' | 'easel' | 'social' | 'lookout';
  assignedTo?: 'stark' | 'usagi' | 'bayzero';
}

export const OFFICE_POIS: Record<string, OfficePOI> = {
  // 1. Workstations (Desk Seats - Linked directly to Central Seat Anchors)
  stark_desk: {
    id: 'stark_desk',
    name: "Stark's Workstation",
    position: WORKSTATION_CONFIG.stark.seatWorldPosition,
    rotationY: WORKSTATION_CONFIG.stark.seatWorldRotationY,
    isSeated: true,
    type: 'desk',
    assignedTo: 'stark',
  },
  usagi_desk: {
    id: 'usagi_desk',
    name: "Usagi's Workstation",
    position: WORKSTATION_CONFIG.usagi.seatWorldPosition,
    rotationY: WORKSTATION_CONFIG.usagi.seatWorldRotationY,
    isSeated: true,
    type: 'desk',
    assignedTo: 'usagi',
  },
  bayzero_desk: {
    id: 'bayzero_desk',
    name: "Bay-Zero's Console",
    position: BAYZERO_SEAT_ANCHOR.seatWorldPosition,
    rotationY: BAYZERO_SEAT_ANCHOR.seatWorldRotationY,
    isSeated: true,
    type: 'desk',
    assignedTo: 'bayzero',
  },

  // 2. Coffee Corner & Lounge POIs
  coffee_counter: {
    id: 'coffee_counter',
    name: 'Coffee Counter',
    position: [3.2, 0, -2.7],
    rotationY: -Math.PI / 4,
    isSeated: false,
    type: 'coffee',
  },
  lounge_sofa_left: {
    id: 'lounge_sofa_left',
    name: 'Lounge Sofa (West)',
    position: [3.7, 0, -3.8],
    rotationY: 0,
    isSeated: true,
    type: 'lounge',
  },
  lounge_sofa_right: {
    id: 'lounge_sofa_right',
    name: 'Lounge Sofa (East)',
    position: [4.3, 0, -3.8],
    rotationY: 0,
    isSeated: true,
    type: 'lounge',
  },

  // 3. Technical Inspection POIs
  server_rack: {
    id: 'server_rack',
    name: 'Reference Library Shelving',
    position: [-2.2, 0, -3.8],
    rotationY: 0,
    isSeated: false,
    type: 'server',
  },
  art_easel: {
    id: 'art_easel',
    name: 'Presentation Whiteboard',
    position: [-3.6, 0, -2.7],
    rotationY: 0.35,
    isSeated: false,
    type: 'easel',
  },
  bayzero_podium: {
    id: 'bayzero_podium',
    name: 'SOP Inspection Podium',
    position: [-0.2, 0, 0.5],
    rotationY: Math.PI,
    isSeated: false,
    type: 'server',
    assignedTo: 'bayzero',
  },

  // 4. Social Interaction Hubs (Face-to-Face Meeting Spots)
  social_center_a: {
    id: 'social_center_a',
    name: 'Central Plaza (Left)',
    position: [-0.8, 0, 0.4],
    rotationY: Math.PI / 2, // Facing East towards Spot B
    isSeated: false,
    type: 'social',
  },
  social_center_b: {
    id: 'social_center_b',
    name: 'Central Plaza (Right)',
    position: [0.4, 0, 0.4],
    rotationY: -Math.PI / 2, // Facing West towards Spot A
    isSeated: false,
    type: 'social',
  },

  // 5. South Window / Lookout Area
  south_lookout: {
    id: 'south_lookout',
    name: 'South Floor Lookout',
    position: [1.2, 0, 2.6],
    rotationY: 0,
    isSeated: false,
    type: 'lookout',
  },
};

/**
 * Waypoint nodes in open corridors that guarantee collision-free travel
 */
interface NavNode {
  id: string;
  pos: THREE.Vector3;
  neighbors: string[];
}

const NAV_GRAPH: Record<string, NavNode> = {
  // Main East-West Corridor (South of Desks)
  corridor_west: {
    id: 'corridor_west',
    pos: new THREE.Vector3(-3.2, 0, 2.4),
    neighbors: ['corridor_center', 'stark_approach'],
  },
  corridor_center: {
    id: 'corridor_center',
    pos: new THREE.Vector3(0, 0, 2.4),
    neighbors: ['corridor_west', 'corridor_east', 'aisle_center_mid', 'lookout_node'],
  },
  corridor_east: {
    id: 'corridor_east',
    pos: new THREE.Vector3(3.2, 0, 2.4),
    neighbors: ['corridor_center', 'usagi_approach', 'lookout_node'],
  },

  // Desk Approaches
  stark_approach: {
    id: 'stark_approach',
    pos: new THREE.Vector3(-3.2, 0, 1.65),
    neighbors: ['corridor_west', 'aisle_west_north'],
  },
  usagi_approach: {
    id: 'usagi_approach',
    pos: new THREE.Vector3(3.2, 0, 1.65),
    neighbors: ['corridor_east', 'aisle_east_north'],
  },
  bayzero_approach: {
    id: 'bayzero_approach',
    pos: new THREE.Vector3(0.18, 0, 0.5),
    neighbors: ['aisle_center_mid'],
  },

  // Lookout
  lookout_node: {
    id: 'lookout_node',
    pos: new THREE.Vector3(1.2, 0, 2.6),
    neighbors: ['corridor_east', 'corridor_center'],
  },

  // North-South Central Aisle (between desks and leading towards meeting table)
  aisle_center_mid: {
    id: 'aisle_center_mid',
    pos: new THREE.Vector3(0, 0, 0.6),
    neighbors: ['corridor_center', 'bayzero_approach', 'aisle_center_north', 'aisle_west_north', 'aisle_east_north'],
  },
  aisle_center_north: {
    id: 'aisle_center_north',
    pos: new THREE.Vector3(0, 0, -2.0),
    neighbors: ['aisle_center_mid', 'lounge_entry', 'library_entry'],
  },

  // Side Aisles around desks
  aisle_west_north: {
    id: 'aisle_west_north',
    pos: new THREE.Vector3(-1.8, 0, -0.4),
    neighbors: ['stark_approach', 'aisle_center_mid', 'library_entry', 'easel_approach'],
  },
  aisle_east_north: {
    id: 'aisle_east_north',
    pos: new THREE.Vector3(1.8, 0, -0.4),
    neighbors: ['usagi_approach', 'aisle_center_mid', 'lounge_entry'],
  },

  // Lounge & Coffee Entry
  lounge_entry: {
    id: 'lounge_entry',
    pos: new THREE.Vector3(3.2, 0, -2.6),
    neighbors: ['aisle_east_north', 'aisle_center_north'],
  },

  // Library & Whiteboard Entry
  library_entry: {
    id: 'library_entry',
    pos: new THREE.Vector3(-2.2, 0, -2.6),
    neighbors: ['aisle_west_north', 'aisle_center_north'],
  },
  easel_approach: {
    id: 'easel_approach',
    pos: new THREE.Vector3(-3.6, 0, -2.6),
    neighbors: ['library_entry', 'aisle_west_north'],
  },
  server_approach: {
    id: 'server_approach',
    pos: new THREE.Vector3(-2.2, 0, -3.6),
    neighbors: ['library_entry'],
  },
};

/**
 * Finds the nearest NavNode to a given world coordinate
 */
function findNearestNavNode(pos: THREE.Vector3): string {
  let nearestId = 'corridor_center';
  let minDistSq = Infinity;

  for (const [id, node] of Object.entries(NAV_GRAPH)) {
    const dSq = pos.distanceToSquared(node.pos);
    if (dSq < minDistSq) {
      minDistSq = dSq;
      nearestId = id;
    }
  }
  return nearestId;
}

/**
 * Breadth-First Search (BFS) pathfinder through NAV_GRAPH
 */
function bfsPath(startNodeId: string, endNodeId: string): string[] {
  if (startNodeId === endNodeId) return [startNodeId];

  const queue: string[][] = [[startNodeId]];
  const visited = new Set<string>([startNodeId]);

  while (queue.length > 0) {
    const path = queue.shift()!;
    const current = path[path.length - 1];

    if (current === endNodeId) {
      return path;
    }

    const node = NAV_GRAPH[current];
    if (!node) continue;

    for (const neighborId of node.neighbors) {
      if (!visited.has(neighborId)) {
        visited.add(neighborId);
        queue.push([...path, neighborId]);
      }
    }
  }

  return [startNodeId, endNodeId];
}

/**
 * Calculates a smooth, safe sequence of waypoints from start to target POI.
 * Prevents walking directly through desks or walls.
 */
export function buildSafePath(
  startPos: [number, number, number] | THREE.Vector3,
  destinationPOI: OfficePOI
): [number, number, number][] {
  const startV = startPos instanceof THREE.Vector3 ? startPos : new THREE.Vector3(...startPos);
  const endV = new THREE.Vector3(...destinationPOI.position);

  // If already at destination (within 0.25 units), no intermediate waypoints needed
  if (startV.distanceTo(endV) < 0.25) {
    return [destinationPOI.position];
  }

  const startNavId = findNearestNavNode(startV);
  const endNavId = findNearestNavNode(endV);

  const nodePathIds = bfsPath(startNavId, endNavId);
  const waypoints: [number, number, number][] = [];

  for (const nId of nodePathIds) {
    const navNode = NAV_GRAPH[nId];
    if (navNode) {
      waypoints.push([navNode.pos.x, navNode.pos.y, navNode.pos.z]);
    }
  }

  // Final destination
  waypoints.push(destinationPOI.position);

  return waypoints;
}

