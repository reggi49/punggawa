/**
 * types.ts
 * Definisi tipe data multi-worker, status, dan payload event untuk Punggawa 3D Office.
 */
import { STATUS_LABELS, HumanStatusConfig } from './utils/statusLabels';
import {
  WORKSTATION_CONFIG,
  BAYZERO_SEAT_ANCHOR,
  CLARA_STAND_ANCHOR,
} from './config/layoutAnchors';

export type AgentNodeName =
  | 'IDLE'
  | 'ingest_node'
  | 'scrape_node'
  | 'draft_node'
  | 'thumbnail_node'
  | 'sop_validator_node'
  | 'publish_node'
  | 'failed_node'
  | 'complete_node'
  | 'processor_node'
  | 'curate_node'
  | 'render_cover_node'
  | 'post_cms_node'
  | 'trigger_notification_node'
  | 'ingest_job_node'
  | 'fetch_job_node'
  | 'evaluate_fit_node'
  | 'draft_application_node'
  | 'review_critique_node'
  | 'generate_prep_node'
  | 'save_job_node'
  | 'housekeeping'
  | 'housekeeping_node';

export interface AgentEventPayload {
  thread_id: string;
  node: string;
  status: string;
  message: string;
  timestamp: string;
  worker_id?: string;
  details?: {
    topic?: string;
    query?: string;
    task_id?: string;
    task_type?: 'article' | 'dongeng' | 'chat' | string;
    action_type?: 'article' | 'dongeng' | 'chat' | string;
    error?: string;
    original_node?: string;
    [key: string]: any;
  };
}

export type ActualAgentState = 'Working' | 'Idle' | 'Waiting' | 'Blocked' | 'Meeting' | 'Offline';

export interface MonitoredServiceStatus {
  id: string;
  name: string;
  url: string;
  status: 'healthy' | 'unhealthy';
  status_code: number | null;
  latency_ms: number;
  error: string | null;
  last_checked: number;
}

export interface ServicesHealthResponse {
  overall_status: 'healthy' | 'degraded';
  services: MonitoredServiceStatus[];
  timestamp: number;
}

export type AmbientActivityType =
  | 'SeatedIdle'
  | 'LookingAtMonitor'
  | 'LookingAround'
  | 'Stretching'
  | 'StandingIdle'
  | 'Walking'
  | 'VisitingCoffeeCorner'
  | 'ReadingOrInspecting'
  | 'CasualConversation'
  | 'ReturningToDesk';

export type CharacterAction =
  | 'idle_coffee'
  | 'walk_to_desk'
  | 'searching_archive'
  | 'intense_typing'
  | 'drawing_canvas'
  | 'inspecting_sop'
  | 'success_celebration'
  | 'confused_scratch'
  | 'observing'
  | 'looking_monitor'
  | 'looking_around'
  | 'stretching'
  | 'visiting_coffee'
  | 'casual_conversation'
  | 'offline_rest';

export type WorkerId = 'stark' | 'usagi' | 'bayzero' | 'clara';

export interface WorkerProfile {
  id: WorkerId;
  name: string;
  codeName: string;
  role: string;
  specialty: string;
  color: string;
  glowColor: string;
  badgeBg: string;
  deskPosition: [number, number, number];
  seatRotation: number;
}

export const WORKER_PROFILES: Record<WorkerId, WorkerProfile> = {
  stark: {
    id: 'stark',
    name: 'Stark',
    codeName: 'Tech Architect',
    role: 'Tech Architect & Writer',
    specialty: 'Artikel KodePintar & In-Depth Technical Guides',
    color: '#354A60',
    glowColor: '#C49A6C',
    badgeBg: 'rgba(53, 74, 96, 0.12)',
    deskPosition: WORKSTATION_CONFIG.stark.seatWorldPosition,
    seatRotation: WORKSTATION_CONFIG.stark.seatWorldRotationY,
  },
  usagi: {
    id: 'usagi',
    name: 'Usagi',
    codeName: 'Creative Curator',
    role: 'Dongeng & Media Curator',
    specialty: 'Kurasi YouTube, Cerita Rakyat & Visual Bogorstore',
    color: '#D98078',
    glowColor: '#8DA895',
    badgeBg: 'rgba(217, 128, 120, 0.12)',
    deskPosition: WORKSTATION_CONFIG.usagi.seatWorldPosition,
    seatRotation: WORKSTATION_CONFIG.usagi.seatWorldRotationY,
  },
  bayzero: {
    id: 'bayzero',
    name: 'Bay-Zero',
    codeName: 'System Inspector',
    role: 'SOP Auditor & Server Health Inspector',
    specialty: 'Quality Gate, Pengecekan Server & Uptime Microservices',
    color: '#8DA895',
    glowColor: '#30343A',
    badgeBg: 'rgba(141, 168, 149, 0.15)',
    deskPosition: BAYZERO_SEAT_ANCHOR.seatWorldPosition,
    seatRotation: BAYZERO_SEAT_ANCHOR.seatWorldRotationY,
  },
  clara: {
    id: 'clara',
    name: 'Clara',
    codeName: 'Career & Talent Lead',
    role: 'Talent & Career Strategist',
    specialty: 'Career-Ops, Loker Matching, ATS Resume & STAR+R Prep',
    color: '#D4A373',
    glowColor: '#F59E0B',
    badgeBg: 'rgba(212, 163, 115, 0.15)',
    deskPosition: CLARA_STAND_ANCHOR.worldPosition,
    seatRotation: CLARA_STAND_ANCHOR.worldRotationY,
  },
};

export interface NodeMetadata extends HumanStatusConfig {}

export const NODE_CONFIG_MAP: Record<string, NodeMetadata> = STATUS_LABELS;
