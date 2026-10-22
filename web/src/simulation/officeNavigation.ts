/**
 * officeNavigation.ts
 * Lightweight, collision-free waypoint navigation system for Punggawa 3D Office.
 * Guarantees natural walking paths between desks, coffee lounge, server rack, and art easel
 * without characters clipping through furniture or walking into walls.
 */
import * as THREE from 'three';
import { WORKSTATION_CONFIG, BAYZERO_SEAT_ANCHOR, SCOUT_SEAT_ANCHOR } from '../config/layoutAnchors';

export interface OfficePOI {
  id: string;
  name: string;
  position: [number, number, number];
  rotationY: number;
  isSeated: boolean;
  type: 'desk' | 'lounge' | 'coffee' | 'server' | 'easel' | 'social' | 'lookout';
  assignedTo?: 'stark' | 'usagi' | 'bayzero' | 'scout';
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
  scout_desk: {
    id: 'scout_desk',
    name: "Scout's Station",
    position: SCOUT_SEAT_ANCHOR.seatWorldPosition,
    rotationY: SCOUT_SEAT_ANCHOR.seatWorldRotationY,
    isSeated: true,
    type: 'desk',
    assignedTo: 'scout',
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
    name: 'Datacenter Server Cluster',
    position: [5.0, 0, -0.45],
    rotationY: Math.PI / 2, // Facing East (+X) towards the servers
    isSeated: false,
    type: 'server',
  },
  reference_library: {
    id: 'reference_library',
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
  // 1. South Main Open Corridor (Behind desks along Z = 2.45, completely open and unobstructed)
  corridor_far_west: {
    id: 'corridor_far_west',
    pos: new THREE.Vector3(-4.6, 0, 2.45),
    neighbors: ['corridor_west'],
  },
  corridor_west: {
    id: 'corridor_west',
    pos: new THREE.Vector3(-3.2, 0, 2.45),
    neighbors: ['corridor_far_west', 'stark_chair', 'corridor_center_west'],
  },
  corridor_center_west: {
    id: 'corridor_center_west',
    pos: new THREE.Vector3(-1.6, 0, 2.45),
    neighbors: ['corridor_west', 'corridor_center', 'aisle_west_south'],
  },
  corridor_center: {
    id: 'corridor_center',
    pos: new THREE.Vector3(0, 0, 2.45),
    neighbors: ['corridor_center_west', 'corridor_center_east', 'lookout_node'],
  },
  corridor_center_east: {
    id: 'corridor_center_east',
    pos: new THREE.Vector3(1.6, 0, 2.45),
    neighbors: ['corridor_center', 'corridor_east', 'aisle_east_south'],
  },
  corridor_east: {
    id: 'corridor_east',
    pos: new THREE.Vector3(3.2, 0, 2.45),
    neighbors: ['corridor_center_east', 'usagi_chair', 'corridor_far_east'],
  },
  corridor_far_east: {
    id: 'corridor_far_east',
    pos: new THREE.Vector3(4.6, 0, 2.45),
    neighbors: ['corridor_east'],
  },

  // 2. Desk Seat Backing Nodes (The ONLY connection into chairs, moving strictly south out of desk)
  stark_chair: {
    id: 'stark_chair',
    pos: new THREE.Vector3(-3.2, 0, 1.72),
    neighbors: ['corridor_west'],
  },
  usagi_chair: {
    id: 'usagi_chair',
    pos: new THREE.Vector3(3.2, 0, 1.72),
    neighbors: ['corridor_east'],
  },

  // 3. West Safe Bypass Aisle (X = -2.0, completely clears the meeting table and Stark desk)
  aisle_west_south: {
    id: 'aisle_west_south',
    pos: new THREE.Vector3(-2.0, 0, 1.8),
    neighbors: ['corridor_center_west', 'aisle_west_mid'],
  },
  aisle_west_mid: {
    id: 'aisle_west_mid',
    pos: new THREE.Vector3(-2.0, 0, 0.7),
    neighbors: ['aisle_west_south', 'aisle_west_table', 'social_west'],
  },
  aisle_west_table: {
    id: 'aisle_west_table',
    pos: new THREE.Vector3(-2.0, 0, -0.5),
    neighbors: ['aisle_west_mid', 'aisle_west_north'],
  },
  aisle_west_north: {
    id: 'aisle_west_north',
    pos: new THREE.Vector3(-2.0, 0, -2.0),
    neighbors: ['aisle_west_table', 'cross_north_west', 'library_node', 'easel_node'],
  },

  // 4. East Safe Bypass Aisle (X = +2.0, completely clears the meeting table and Usagi desk)
  aisle_east_south: {
    id: 'aisle_east_south',
    pos: new THREE.Vector3(2.0, 0, 1.8),
    neighbors: ['corridor_center_east', 'aisle_east_mid'],
  },
  aisle_east_mid: {
    id: 'aisle_east_mid',
    pos: new THREE.Vector3(2.0, 0, 0.7),
    neighbors: ['aisle_east_south', 'aisle_east_table', 'social_east'],
  },
  aisle_east_table: {
    id: 'aisle_east_table',
    pos: new THREE.Vector3(2.0, 0, -0.45),
    neighbors: ['aisle_east_mid', 'aisle_east_north', 'server_corridor_west'],
  },
  aisle_east_north: {
    id: 'aisle_east_north',
    pos: new THREE.Vector3(2.0, 0, -2.0),
    neighbors: ['aisle_east_table', 'cross_north_east', 'coffee_node', 'lounge_node'],
  },

  // 5. North Cross Corridor (North of Meeting Table)
  cross_north_west: {
    id: 'cross_north_west',
    pos: new THREE.Vector3(-1.0, 0, -2.0),
    neighbors: ['aisle_west_north', 'cross_north_center'],
  },
  cross_north_center: {
    id: 'cross_north_center',
    pos: new THREE.Vector3(0, 0, -2.0),
    neighbors: ['cross_north_west', 'cross_north_east'],
  },
  cross_north_east: {
    id: 'cross_north_east',
    pos: new THREE.Vector3(1.0, 0, -2.0),
    neighbors: ['cross_north_center', 'aisle_east_north'],
  },

  // 6. Datacenter Server Racks Approach (Along Z = -0.45 from X = 2.0 to X = 5.0)
  server_corridor_west: {
    id: 'server_corridor_west',
    pos: new THREE.Vector3(3.6, 0, -0.45),
    neighbors: ['aisle_east_table', 'server_approach'],
  },
  server_approach: {
    id: 'server_approach',
    pos: new THREE.Vector3(5.0, 0, -0.45),
    neighbors: ['server_corridor_west'],
  },

  // 7. Coffee Corner & Lounge Sofas
  coffee_node: {
    id: 'coffee_node',
    pos: new THREE.Vector3(3.2, 0, -2.7),
    neighbors: ['aisle_east_north', 'lounge_node'],
  },
  lounge_node: {
    id: 'lounge_node',
    pos: new THREE.Vector3(3.8, 0, -3.5),
    neighbors: ['coffee_node', 'aisle_east_north'],
  },

  // 8. Presentation Whiteboard & Reference Library
  easel_node: {
    id: 'easel_node',
    pos: new THREE.Vector3(-3.6, 0, -2.7),
    neighbors: ['aisle_west_north'],
  },
  library_node: {
    id: 'library_node',
    pos: new THREE.Vector3(-2.2, 0, -3.6),
    neighbors: ['aisle_west_north'],
  },

  // 9. Central Social Spots (Safe open spaces)
  social_west: {
    id: 'social_west',
    pos: new THREE.Vector3(-0.8, 0, 0.6),
    neighbors: ['aisle_west_mid'],
  },
  social_east: {
    id: 'social_east',
    pos: new THREE.Vector3(0.4, 0, 0.6),
    neighbors: ['aisle_east_mid'],
  },

  // 10. South Window Lookout
  lookout_node: {
    id: 'lookout_node',
    pos: new THREE.Vector3(1.2, 0, 2.5),
    neighbors: ['corridor_center'],
  },
};

/**
 * Finds the nearest NavNode to a given world coordinate
 */
function findNearestNavNode(pos: THREE.Vector3): string {
  // Special prioritized matching for desk chairs to enforce entering/exiting via chair rear
  const dStarkChair = pos.distanceToSquared(new THREE.Vector3(-3.2, 0, 1.68));
  if (dStarkChair < 0.25) return 'stark_chair';

  const dUsagiChair = pos.distanceToSquared(new THREE.Vector3(3.2, 0, 1.68));
  if (dUsagiChair < 0.25) return 'usagi_chair';

  const dServer = pos.distanceToSquared(new THREE.Vector3(5.0, 0, -0.45));
  if (dServer < 0.35) return 'server_approach';

  let nearestId = 'corridor_center';
  let minDistSq = Infinity;

  for (const [id, node] of Object.entries(NAV_GRAPH)) {
    // Skip chair nodes for arbitrary positions to prevent unwanted path snaps through chairs
    if ((id === 'stark_chair' || id === 'usagi_chair') && (dStarkChair >= 0.25 && dUsagiChair >= 0.25)) {
      continue;
    }
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
 * Prevents walking directly through desks, conference table, or walls.
 */
export function buildSafePath(
  startPos: [number, number, number] | THREE.Vector3,
  destination: OfficePOI | [number, number, number]
): [number, number, number][] {
  const startV = startPos instanceof THREE.Vector3 ? startPos : new THREE.Vector3(...startPos);
  const destPos: [number, number, number] =
    Array.isArray(destination) ? destination : destination.position;
  const endV = new THREE.Vector3(...destPos);

  // If already at destination (within 0.25 units), no intermediate waypoints needed
  if (startV.distanceTo(endV) < 0.25) {
    return [destPos];
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
  if (
    waypoints.length === 0 ||
    new THREE.Vector3(...waypoints[waypoints.length - 1]).distanceTo(endV) > 0.1
  ) {
    waypoints.push(destPos);
  }

  return waypoints;
}

