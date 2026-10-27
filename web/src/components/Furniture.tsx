import React, { useMemo, useRef, Suspense } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF, RoundedBox, Clone, Html } from '@react-three/drei';
import * as THREE from 'three';
import {
  WORKSTATION_CONFIG,
  MEETING_ZONE_CONFIG,
  BAYZERO_SEAT_ANCHOR,
  SCOUT_SEAT_ANCHOR,
} from '../config/layoutAnchors';
import { ServicesHealthResponse } from '../types';

interface FurnitureProps {
  currentNode: string;
  isDegraded?: boolean;
  healthData?: ServicesHealthResponse | null;
}

// =========================================================================
// SCANDINAVIAN TARGET COLOR PALETTES
// =========================================================================
const OAK_PALETTE = {
  wood: { color: '#C89D66', roughness: 0.62, metalness: 0.0 },
  metal: { color: '#2B3038', roughness: 0.45, metalness: 0.8 },
  _defaultMat: { color: '#F4F1EA', roughness: 0.7, metalness: 0.0 },
};

const RUG_WARM_GREY = {
  carpet: { color: '#DCD6CB', roughness: 0.94, metalness: 0.0 },
  carpetDarker: { color: '#CCC5B8', roughness: 0.94, metalness: 0.0 },
};

const RUG_SAGE_GREEN = {
  carpet: { color: '#5A735E', roughness: 0.92, metalness: 0.0 },
  carpetDarker: { color: '#4E6552', roughness: 0.92, metalness: 0.0 },
};

const RUG_LIGHT_SAND = {
  carpet: { color: '#E5DFD4', roughness: 0.94, metalness: 0.0 },
  carpetDarker: { color: '#D6CEBF', roughness: 0.94, metalness: 0.0 },
};

/**
 * High-End Scandinavian Ergonomic Office Chair (Quaternius Asset)
 * Real curved backrest, lumbar cushion, 5-star caster base, gas-lift, and ergonomic armrests.
 */
export function ErgonomicOfficeChair({
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  scale = 1.0,
}: {
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: number;
}) {
  const chairModel = useGLTF('/assets/models/furniture/office-chair.glb');

  return (
    <group position={position} rotation={rotation} scale={[scale, scale, scale]}>
      <Clone object={chairModel.scene} />
    </group>
  );
}

/**
 * Custom Curved Ultrawide Monitor Display
 * Cylindrical curved screen with glowing code/document UI and aluminum stand.
 */
export function CurvedUltrawideMonitor({
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  scale = 1,
  emissiveColor = '#8DA895',
  emissiveIntensity = 0.6,
  isWorking = false,
}: {
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: number;
  emissiveColor?: string;
  emissiveIntensity?: number;
  isWorking?: boolean;
}) {
  const R = 1.6; // 1600R realistic curvature radius
  const arcSpan = 0.58; // ~33 degrees arc (approx 0.95m screen width)
  const thetaStart = Math.PI - arcSpan / 2; // Centered at Math.PI, concave towards +Z (user)
  const screenH = 0.36; // 36cm height for 49" ultrawide display
  const screenMatRef = useRef<THREE.MeshStandardMaterial>(null);
  const rgbLightRef = useRef<THREE.PointLight>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (screenMatRef.current) {
      if (isWorking) {
        // Dynamic RGB rainbow cycle + vivid screen flicker
        const hue = (t * 0.95 + 0.3) % 1.0;
        const color = new THREE.Color().setHSL(hue, 1.0, 0.6);
        const flicker = 2.2 + Math.sin(t * 22.0) * 0.7 + (Math.sin(t * 43.0) > 0.4 ? 0.8 : 0);
        screenMatRef.current.emissive.copy(color);
        screenMatRef.current.emissiveIntensity = flicker;
        if (rgbLightRef.current) {
          rgbLightRef.current.color.copy(color);
          rgbLightRef.current.intensity = flicker * 0.6;
        }
      } else {
        // Continuous ambient cyber scanline pulse & subtle flicker even in idle
        const idlePulse = 1.35 + Math.sin(t * 6.0) * 0.4 + (Math.sin(t * 19.0) > 0.6 ? 0.35 : 0);
        const idleHue = (0.42 + Math.sin(t * 0.5) * 0.06) % 1.0; // Shifting between green and cyan
        const idleColor = new THREE.Color().setHSL(idleHue, 0.85, 0.55);
        screenMatRef.current.emissive.copy(idleColor);
        screenMatRef.current.emissiveIntensity = idlePulse;
        if (rgbLightRef.current) {
          rgbLightRef.current.intensity = idlePulse * 0.35;
          rgbLightRef.current.color.copy(idleColor);
        }
      }
    }
  });

  return (
    <group position={position} rotation={rotation} scale={[scale, scale, scale]}>
      {/* 1. Aluminum Stand Base (Behind the screen, resting flat on desk) */}
      <mesh position={[0, 0.008, -0.06]} castShadow>
        <cylinderGeometry args={[0.13, 0.15, 0.016, 24]} />
        <meshStandardMaterial color="#2E333D" metalness={0.75} roughness={0.3} />
      </mesh>

      {/* 2. Vertical Aluminum Support Arm (Mounted behind display) */}
      <mesh position={[0, 0.18, -0.06]} rotation={[-0.05, 0, 0]} castShadow>
        <boxGeometry args={[0.042, 0.34, 0.032]} />
        <meshStandardMaterial color="#94A3B8" metalness={0.85} roughness={0.25} />
      </mesh>

      {/* 3. VESA Mounting Bracket Joint */}
      <mesh position={[0, 0.22, -0.03]}>
        <boxGeometry args={[0.10, 0.10, 0.02]} />
        <meshStandardMaterial color="#1E2228" roughness={0.4} />
      </mesh>

      {/* 4. Outer Dark Charcoal Housing Bezel (6mm behind glowing screen) */}
      <mesh position={[0, 0.22, R - 0.006]}>
        <cylinderGeometry args={[R, R, screenH + 0.02, 32, 1, true, thetaStart - 0.01, arcSpan + 0.02]} />
        <meshStandardMaterial color="#1C1F24" roughness={0.35} metalness={0.6} side={THREE.DoubleSide} />
      </mesh>

      {/* 5. Glowing Curved Ultrawide Screen Panel (Concave curve facing Usagi) */}
      <mesh position={[0, 0.22, R]}>
        <cylinderGeometry args={[R, R, screenH, 32, 1, true, thetaStart, arcSpan]} />
        <meshStandardMaterial
          ref={screenMatRef}
          color="#0B132B"
          emissive={emissiveColor}
          emissiveIntensity={emissiveIntensity}
          roughness={0.18}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Dynamic RGB Screen Glow */}
      <pointLight ref={rgbLightRef} position={[0, 0.24, 0.2]} color={emissiveColor} intensity={0.2} distance={1.2} decay={2} />
    </group>
  );
}

/**
 * Reusable Interactive RGB Laptop dengan layar kelap-kelip dinamis
 */
export function InteractiveRGBLaptop({
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  isWorking = false,
  defaultEmissive = '#38BDF8',
  scale = 1.15,
}: {
  position?: [number, number, number];
  rotation?: [number, number, number];
  isWorking?: boolean;
  defaultEmissive?: string;
  scale?: number;
}) {
  const laptopModel = useGLTF('/assets/models/props/laptop.glb');
  const screenMatRef = useRef<THREE.MeshStandardMaterial>(null);
  const lightRef = useRef<THREE.PointLight>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (screenMatRef.current) {
      if (isWorking) {
        // Dynamic RGB cycling + rapid hacker terminal flicker
        const hue = (t * 1.15) % 1.0;
        const color = new THREE.Color().setHSL(hue, 1.0, 0.6);
        const flicker = 2.4 + Math.sin(t * 22.0) * 0.7 + (Math.sin(t * 47.0) > 0.4 ? 0.8 : 0);
        screenMatRef.current.emissive.copy(color);
        screenMatRef.current.emissiveIntensity = flicker;
        if (lightRef.current) {
          lightRef.current.color.copy(color);
          lightRef.current.intensity = flicker * 0.75;
        }
      } else {
        // Continuous animated cyber kelap-kelip & breathing pulse even in idle
        const idlePulse = 1.35 + Math.sin(t * 7.0) * 0.4 + (Math.sin(t * 23.0) > 0.5 ? 0.45 : 0);
        const idleHue = (0.54 + Math.sin(t * 0.6) * 0.08) % 1.0; // Shifting cyber cyan / teal
        const idleColor = new THREE.Color().setHSL(idleHue, 0.95, 0.55);
        screenMatRef.current.emissive.copy(idleColor);
        screenMatRef.current.emissiveIntensity = idlePulse;
        if (lightRef.current) {
          lightRef.current.intensity = idlePulse * 0.4;
          lightRef.current.color.copy(idleColor);
        }
      }
    }
  });

  return (
    <group position={position} rotation={rotation} scale={[scale, scale, scale]}>
      <Clone object={laptopModel.scene} />
      {/* Dynamic Glowing RGB Screen Pane */}
      <mesh position={[0, 0.148, -0.103]} rotation={[-0.32, 0, 0]}>
        <planeGeometry args={[0.26, 0.165]} />
        <meshStandardMaterial
          ref={screenMatRef}
          color="#0B132B"
          emissive={defaultEmissive}
          emissiveIntensity={1.3}
          roughness={0.15}
          side={THREE.DoubleSide}
        />
      </mesh>
      {/* Real-time RGB Glow Casting onto Table and Keyboard */}
      <pointLight
        ref={lightRef}
        position={[0, 0.16, 0.05]}
        color={defaultEmissive}
        intensity={0.4}
        distance={0.95}
        decay={2}
      />
    </group>
  );
}

/**
 * 1. Stark's Tech Writer Workstation (Foreground-Left: x = -3.2, z = 1.3)
 */
export function StarkWorkstation({ currentNode }: FurnitureProps) {
  const codeScreenRef = useRef<THREE.MeshStandardMaterial>(null);
  const termScreenRef = useRef<THREE.MeshStandardMaterial>(null);
  const rgbLightRef = useRef<THREE.PointLight>(null);
  const keyboardModel = useGLTF('/assets/models/props/computer-keyboard.glb');
  const mouseModel = useGLTF('/assets/models/props/computer-mouse.glb');
  const deskLampModel = useGLTF('/assets/models/props/lamp-desk.glb');

  const isWriting =
    currentNode === 'draft_node' ||
    currentNode === 'processor_node' ||
    currentNode === 'ingest_node' ||
    currentNode === 'enrich_sources_node' ||
    currentNode === 'scrape_node' ||
    currentNode === 'ingest_trend_node';
  const isFailed = currentNode === 'failed_node';
  const isDone = currentNode === 'publish_node' || currentNode === 'complete_node';

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (codeScreenRef.current) {
      if (isFailed) {
        codeScreenRef.current.emissive.set('#EF4444');
        codeScreenRef.current.emissiveIntensity = Math.sin(t * 16) > 0 ? 0.8 : 0.15;
        if (termScreenRef.current) {
          termScreenRef.current.emissive.set('#EF4444');
          termScreenRef.current.emissiveIntensity = Math.sin(t * 16) > 0 ? 0.8 : 0.15;
        }
        if (rgbLightRef.current) {
          rgbLightRef.current.color.set('#EF4444');
          rgbLightRef.current.intensity = Math.sin(t * 16) > 0 ? 0.6 : 0.1;
        }
      } else if (isWriting) {
        // VIBRANT RGB HACKER/DEVELOPER MONITOR FLICKER
        const hue1 = (t * 1.1) % 1.0;
        const hue2 = (hue1 + 0.35) % 1.0;
        const color1 = new THREE.Color().setHSL(hue1, 1.0, 0.6);
        const color2 = new THREE.Color().setHSL(hue2, 1.0, 0.6);
        const flicker1 = 2.4 + Math.sin(t * 22.0) * 0.7 + (Math.sin(t * 47.0) > 0.4 ? 0.8 : 0);
        const flicker2 = 2.2 + Math.cos(t * 19.0) * 0.7 + (Math.cos(t * 41.0) > 0.4 ? 0.8 : 0);

        codeScreenRef.current.emissive.copy(color1);
        codeScreenRef.current.emissiveIntensity = flicker1;
        if (termScreenRef.current) {
          termScreenRef.current.emissive.copy(color2);
          termScreenRef.current.emissiveIntensity = flicker2;
        }
        if (rgbLightRef.current) {
          rgbLightRef.current.color.copy(color1);
          rgbLightRef.current.intensity = flicker1 * 0.6;
        }
      } else if (isDone) {
        codeScreenRef.current.emissive.set('#10B981');
        codeScreenRef.current.emissiveIntensity = 1.2;
        if (termScreenRef.current) {
          termScreenRef.current.emissive.set('#10B981');
          termScreenRef.current.emissiveIntensity = 1.2;
        }
        if (rgbLightRef.current) {
          rgbLightRef.current.color.set('#10B981');
          rgbLightRef.current.intensity = 0.5;
        }
      } else {
        // Continuous animated cyber glow & terminal pulse in standby/idle
        const idlePulse1 = 1.35 + Math.sin(t * 7.5) * 0.4 + (Math.sin(t * 23.0) > 0.5 ? 0.45 : 0);
        const idlePulse2 = 1.30 + Math.cos(t * 8.5) * 0.38 + (Math.cos(t * 29.0) > 0.5 ? 0.45 : 0);
        codeScreenRef.current.emissive.set('#38BDF8');
        codeScreenRef.current.emissiveIntensity = idlePulse1;
        if (termScreenRef.current) {
          termScreenRef.current.emissive.set('#818CF8');
          termScreenRef.current.emissiveIntensity = idlePulse2;
        }
        if (rgbLightRef.current) {
          rgbLightRef.current.color.set('#38BDF8');
          rgbLightRef.current.intensity = idlePulse1 * 0.35;
        }
      }
    }
  });

  return (
    <group position={WORKSTATION_CONFIG.stark.deskPosition} rotation={[0, WORKSTATION_CONFIG.stark.deskRotationY, 0]}>
      {/* Textured Rectangular Area Rug */}
      <mesh position={[0, 0.003, 0.25]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[2.4, 2.0]} />
        <meshStandardMaterial color="#DCD6CB" roughness={0.92} />
      </mesh>

      {/* Main Solid Oak Desk with Rounded Bevels (Width: 1.8, Height: 0.74, Depth: 0.85) */}
      <group position={[0, 0, 0]}>
        {/* Solid Oak Desktop */}
        <RoundedBox radius={0.025} smoothness={4} args={[1.8, 0.045, 0.85]} position={[0, 0.7175, 0]} castShadow receiveShadow>
          <meshStandardMaterial color="#C89D66" roughness={0.58} />
        </RoundedBox>
        {/* Steel Desk Frame & Corner Legs */}
        {[-0.82, 0.82].map((x, i) => (
          <group key={`leg-s-${i}`}>
            <mesh position={[x, 0.3475, 0.36]} castShadow>
              <boxGeometry args={[0.045, 0.695, 0.045]} />
              <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
            </mesh>
            <mesh position={[x, 0.3475, -0.36]} castShadow>
              <boxGeometry args={[0.045, 0.695, 0.045]} />
              <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
            </mesh>
            <mesh position={[x, 0.04, 0]}>
              <boxGeometry args={[0.045, 0.035, 0.76]} />
              <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Perforated Acoustic Pegboard Screen Divider behind desk */}
      <RoundedBox radius={0.02} smoothness={3} args={[1.8, 0.44, 0.025]} position={[0, 0.96, -0.42]} castShadow>
        <meshStandardMaterial color="#D4A574" roughness={0.85} />
      </RoundedBox>

      {/* Under-desk Pedestal Drawers: Local [-0.62, 0.34, 0] and [0.62, 0.34, 0] */}
      {/* Left Charcoal Pedestal */}
      <group position={[-0.62, 0.34, 0]}>
        <RoundedBox radius={0.02} smoothness={3} args={[0.34, 0.64, 0.65]} position={[0, 0, 0]} castShadow>
          <meshStandardMaterial color="#30353D" roughness={0.6} />
        </RoundedBox>
      </group>
      {/* Right Clean White Pedestal */}
      <group position={[0.62, 0.34, 0]}>
        <RoundedBox radius={0.02} smoothness={3} args={[0.34, 0.64, 0.65]} position={[0, 0, 0]} castShadow>
          <meshStandardMaterial color="#F4F1EA" roughness={0.7} />
        </RoundedBox>
      </group>

      {/* Dual Code Monitors on Desk (Facing +Z towards the chair) */}
      {/* Monitor 1 (Left IDE Screen) */}
      <group position={[-0.30, 0.74, -0.22]} rotation={[0, 0.12, 0]}>
        <RoundedBox radius={0.015} smoothness={3} args={[0.56, 0.36, 0.025]} position={[0, 0.22, 0]} castShadow>
          <meshStandardMaterial color="#1C1F24" roughness={0.3} metalness={0.5} />
        </RoundedBox>
        <mesh position={[0, 0.22, 0.014]}>
          <planeGeometry args={[0.53, 0.33]} />
          <meshStandardMaterial
            ref={codeScreenRef}
            color="#0A0E17"
            emissive="#38BDF8"
            emissiveIntensity={1.3}
            roughness={0.15}
            side={THREE.DoubleSide}
          />
        </mesh>
        {/* Monitor Stand */}
        <mesh position={[0, 0.08, -0.04]}>
          <cylinderGeometry args={[0.016, 0.016, 0.16, 10]} />
          <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
        </mesh>
        <mesh position={[0, 0.005, 0]}>
          <boxGeometry args={[0.18, 0.01, 0.14]} />
          <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
        </mesh>
      </group>

      {/* Monitor 2 (Right Terminal Screen) */}
      <group position={[0.30, 0.74, -0.22]} rotation={[0, -0.12, 0]}>
        <RoundedBox radius={0.015} smoothness={3} args={[0.56, 0.36, 0.025]} position={[0, 0.22, 0]} castShadow>
          <meshStandardMaterial color="#1C1F24" roughness={0.3} metalness={0.5} />
        </RoundedBox>
        <mesh position={[0, 0.22, 0.014]}>
          <planeGeometry args={[0.53, 0.33]} />
          <meshStandardMaterial
            ref={termScreenRef}
            color="#0F172A"
            emissive="#64748B"
            emissiveIntensity={1.2}
            roughness={0.15}
            side={THREE.DoubleSide}
          />
        </mesh>
        {/* Monitor Stand */}
        <mesh position={[0, 0.08, -0.04]}>
          <cylinderGeometry args={[0.016, 0.016, 0.16, 10]} />
          <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
        </mesh>
        <mesh position={[0, 0.005, 0]}>
          <boxGeometry args={[0.18, 0.01, 0.14]} />
          <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
        </mesh>
      </group>

      {/* Dynamic Screen RGB Projection Light */}
      <pointLight ref={rgbLightRef} position={[0, 0.98, -0.05]} color="#38BDF8" intensity={0.25} distance={1.2} decay={2} />

      {/* Real Kenney Keyboard & Mouse at [0, 0.745, 0.18] */}
      <group position={[0, 0.745, 0.18]}>
        <Clone object={keyboardModel.scene} scale={[1.15, 1.15, 1.15]} position={[-0.14, 0, 0]} />
        <Clone object={mouseModel.scene} scale={[1.15, 1.15, 1.15]} position={[0.22, 0, 0]} />
      </group>

      {/* Real Kenney Desk Lamp at [-0.68, 0.74, -0.18] */}
      <group position={[-0.68, 0.74, -0.18]}>
        <Clone object={deskLampModel.scene} scale={[1.2, 1.2, 1.2]} />
        <pointLight position={[0, 0.28, 0]} intensity={0.45} color="#FFE6BD" distance={1.8} decay={2} />
      </group>

      {/* Ergonomic Office Chair: Exact Local Anchor [0, 0, 0.58] and Math.PI rotation */}
      <ErgonomicOfficeChair position={[0, 0, 0.58]} rotation={[0, Math.PI, 0]} scale={1.05} />
    </group>
  );
}

/**
 * 2. Usagi's Creative Curation Workstation (Foreground-Right: x = 3.2, z = 1.1)
 */
export function UsagiWorkstation({ currentNode }: FurnitureProps) {
  const keyboardModel = useGLTF('/assets/models/props/computer-keyboard.glb');
  const mouseModel = useGLTF('/assets/models/props/computer-mouse.glb');
  const deskLampModel = useGLTF('/assets/models/props/lamp-desk.glb');

  const isCurating =
    currentNode === 'curate_node' ||
    currentNode === 'render_cover_node' ||
    currentNode === 'post_cms_node';

  return (
    <group position={WORKSTATION_CONFIG.usagi.deskPosition} rotation={[0, WORKSTATION_CONFIG.usagi.deskRotationY, 0]}>
      {/* Textured Rectangular Area Rug */}
      <mesh position={[0, 0.003, 0.25]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[2.4, 2.0]} />
        <meshStandardMaterial color="#DCD6CB" roughness={0.92} />
      </mesh>

      {/* Main Solid Oak Desk with Rounded Bevels (Width: 1.8, Height: 0.74, Depth: 0.85) */}
      <group position={[0, 0, 0]}>
        <RoundedBox radius={0.025} smoothness={4} args={[1.8, 0.045, 0.85]} position={[0, 0.7175, 0]} castShadow receiveShadow>
          <meshStandardMaterial color="#C89D66" roughness={0.58} />
        </RoundedBox>
        {[-0.82, 0.82].map((x, i) => (
          <group key={`leg-u-${i}`}>
            <mesh position={[x, 0.3475, 0.36]} castShadow>
              <boxGeometry args={[0.045, 0.695, 0.045]} />
              <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
            </mesh>
            <mesh position={[x, 0.3475, -0.36]} castShadow>
              <boxGeometry args={[0.045, 0.695, 0.045]} />
              <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
            </mesh>
            <mesh position={[x, 0.04, 0]}>
              <boxGeometry args={[0.045, 0.035, 0.76]} />
              <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
            </mesh>
          </group>
        ))}
      </group>

      {/* Perforated Acoustic Pegboard Screen Divider behind desk */}
      <RoundedBox radius={0.02} smoothness={3} args={[1.8, 0.44, 0.025]} position={[0, 0.96, -0.42]} castShadow>
        <meshStandardMaterial color="#D4A574" roughness={0.85} />
      </RoundedBox>

      {/* Under-desk Pedestal Drawers (Both Clean White) */}
      <group position={[-0.62, 0.34, 0]}>
        <RoundedBox radius={0.02} smoothness={3} args={[0.34, 0.64, 0.65]} position={[0, 0, 0]} castShadow>
          <meshStandardMaterial color="#F4F1EA" roughness={0.7} />
        </RoundedBox>
      </group>
      <group position={[0.62, 0.34, 0]}>
        <RoundedBox radius={0.02} smoothness={3} args={[0.34, 0.64, 0.65]} position={[0, 0, 0]} castShadow>
          <meshStandardMaterial color="#F4F1EA" roughness={0.7} />
        </RoundedBox>
      </group>

      {/* Curved Ultrawide Monitor Display at [0, 0.74, -0.22] (Facing +Z towards the chair) */}
      <CurvedUltrawideMonitor
        position={[-0.08, 0.74, -0.22]}
        emissiveColor={isCurating ? '#D98078' : '#8DA895'}
        emissiveIntensity={0.6}
        isWorking={isCurating}
        scale={0.92}
      />

      {/* Angled Companion Interactive RGB Laptop */}
      <InteractiveRGBLaptop
        position={[0.55, 0.745, -0.05]}
        rotation={[0, -0.25, 0]}
        isWorking={isCurating}
        defaultEmissive="#D98078"
        scale={0.95}
      />

      {/* Real Kenney Keyboard & Mouse */}
      <group position={[-0.08, 0.745, 0.18]}>
        <Clone object={keyboardModel.scene} scale={[1.15, 1.15, 1.15]} position={[-0.14, 0, 0]} />
        <Clone object={mouseModel.scene} scale={[1.15, 1.15, 1.15]} position={[0.22, 0, 0]} />
      </group>

      {/* Real Kenney Task Lamp */}
      <group position={[-0.68, 0.74, -0.18]}>
        <Clone object={deskLampModel.scene} scale={[1.2, 1.2, 1.2]} />
        <pointLight position={[0, 0.28, 0]} intensity={0.45} color="#FFE6BD" distance={1.8} decay={2} />
      </group>

      {/* Ergonomic Office Chair: Exact Local Anchor [0, 0, 0.58] and Math.PI rotation */}
      <ErgonomicOfficeChair position={[0, 0, 0.58]} rotation={[0, Math.PI, 0]} scale={1.05} />
    </group>
  );
}

/**
 * 3. Bay-Zero's Central Meeting & Review Area (Single Group Center: [0, 0, -0.5])
 */
export function BayZeroWorkstation({ currentNode }: FurnitureProps) {
  const isAudit = currentNode === 'sop_validator_node';
  const isJobTask =
    currentNode.startsWith('job_') ||
    currentNode.includes('fit_node') ||
    currentNode.includes('draft_application') ||
    currentNode.includes('generate_prep') ||
    currentNode.includes('review_critique');
  const chairModel = useGLTF('/models/modern_arm_chair_01/modern_arm_chair_01.gltf');

  return (
    <group position={MEETING_ZONE_CONFIG.center}>
      {/* 1. Concentric Olive Green Circular Woven Rug (Pusat [0, 0.01, 0]) */}
      <mesh position={[0, 0.01, 0]} receiveShadow>
        <cylinderGeometry args={[MEETING_ZONE_CONFIG.carpetRadius, MEETING_ZONE_CONFIG.carpetRadius, 0.005, 48]} />
        <meshStandardMaterial color="#5A735E" roughness={0.92} />
      </mesh>

      {/* 2. Round Solid Oak Meeting Table (Pusat [0, 0, 0], Radius: 1.05, Height: 0.74) */}
      <group position={[0, 0, 0]}>
        {/* Table Top Disc */}
        <mesh position={[0, MEETING_ZONE_CONFIG.tableHeight - 0.0225, 0]} castShadow receiveShadow>
          <cylinderGeometry args={[MEETING_ZONE_CONFIG.tableRadius, MEETING_ZONE_CONFIG.tableRadius, 0.045, 48]} />
          <meshStandardMaterial color="#C89D66" roughness={0.58} />
        </mesh>
        {/* 4 Angled Sturdy Oak Legs at radius 0.55 */}
        {[0, 1, 2, 3].map((i) => {
          const angle = (i * Math.PI) / 2 + Math.PI / 4;
          const x = Math.sin(angle) * 0.55;
          const z = Math.cos(angle) * 0.55;
          return (
            <mesh
              key={`tbl-leg-${i}`}
              position={[x, 0.3475, z]}
              rotation={[Math.cos(angle) * 0.1, 0, -Math.sin(angle) * 0.1]}
              castShadow
            >
              <cylinderGeometry args={[0.038, 0.026, 0.695, 16]} />
              <meshStandardMaterial color="#A87D46" roughness={0.6} />
            </mesh>
          );
        })}
      </group>

      {/* 3. 4 Scandinavian Meeting Bucket Chairs (Radius r = 1.28 facing center [0, 0, 0]) */}
      {[0, 1, 2, 3].map((i) => {
        const angle = MEETING_ZONE_CONFIG.bayZeroAngle + (i * Math.PI) / 2;
        const x = Math.sin(angle) * MEETING_ZONE_CONFIG.chairRadius;
        const z = Math.cos(angle) * MEETING_ZONE_CONFIG.chairRadius;
        const rotY = angle + Math.PI;
        return (
          <group key={`mtg-chair-${i}`} position={[x, 0, z]} rotation={[0, rotY, 0]}>
            <Clone object={chairModel.scene} scale={[1.2, 1.2, 1.2]} />
          </group>
        );
      })}

      {/* 4. Kang Bos (Bay-Zero) Interactive RGB Review Laptop directly in front of Chair 0 */}
      <InteractiveRGBLaptop
        position={BAYZERO_SEAT_ANCHOR.laptopLocalPosition}
        rotation={[0, BAYZERO_SEAT_ANCHOR.laptopLocalRotationY, 0]}
        isWorking={isAudit}
        defaultEmissive="#8DA895"
      />

      {/* 5. Kang Kerja (Scout) Interactive RGB Career Intelligence Laptop directly in front of Chair 2 */}
      <InteractiveRGBLaptop
        position={SCOUT_SEAT_ANCHOR.laptopLocalPosition}
        rotation={[0, SCOUT_SEAT_ANCHOR.laptopLocalRotationY, 0]}
        isWorking={isJobTask}
        defaultEmissive="#0D9488"
      />

      {/* Table Accessories (Coffee Mug) */}
      <group
        position={[
          Math.sin(MEETING_ZONE_CONFIG.bayZeroAngle - 0.35) * 0.65,
          MEETING_ZONE_CONFIG.tableHeight + 0.04,
          Math.cos(MEETING_ZONE_CONFIG.bayZeroAngle - 0.35) * 0.65,
        ]}
      >
        <mesh castShadow>
          <cylinderGeometry args={[0.035, 0.03, 0.08, 12]} />
          <meshStandardMaterial color="#FFFFFF" roughness={0.3} />
        </mesh>
      </group>
    </group>
  );
}

/**
 * 4. Upper-Right Lounge (Coffee & Rest Area: x = 3.8, z = -3.4)
 */
export function CoffeeLounge({ currentNode }: FurnitureProps) {
  const sofaModel = useGLTF('/assets/models/furniture/sofa-02.glb');
  const coffeeTableModel = useGLTF('/models/coffee_table_round_01/coffee_table_round_01.gltf');
  const floorLampModel = useGLTF('/assets/models/props/lamp-floor.glb');
  const pillowModel = useGLTF('/assets/models/props/pillow.glb');
  const pillowBlueModel = useGLTF('/assets/models/props/pillow-blue.glb');

  return (
    <group position={[3.8, 0, -3.4]}>
      {/* Circular Light Sand Woven Rug */}
      <mesh position={[0, 0.003, 0]} receiveShadow>
        <cylinderGeometry args={[1.35, 1.35, 0.005, 36]} />
        <meshStandardMaterial color="#E5DFD4" roughness={0.94} />
      </mesh>

      {/* Plush Quaternius Lounge Sofa in Slate Navy Fabric */}
      <group position={[0.2, 0, -0.35]} rotation={[0, -0.22, 0]}>
        <Clone object={sofaModel.scene} scale={[0.55, 0.55, 0.55]} />
        {/* Soft Decorative Throw Pillows */}
        <group position={[-0.55, 0.36, 0.1]} rotation={[0.2, 0.1, 0]}>
          <Clone object={pillowModel.scene} scale={[1.2, 1.2, 1.2]} />
        </group>
        <group position={[0.55, 0.36, 0.1]} rotation={[0.2, -0.1, 0]}>
          <Clone object={pillowBlueModel.scene} scale={[1.2, 1.2, 1.2]} />
        </group>
      </group>

      {/* Poly Haven Round Wooden Coffee Table */}
      <group position={[-0.4, 0, 0.4]}>
        <Clone object={coffeeTableModel.scene} scale={[1.1, 1.1, 1.1]} />
      </group>

      {/* Modern Floor Lamp with Warm Lighting */}
      <group position={[1.35, 0, -0.9]}>
        <Clone object={floorLampModel.scene} scale={[1.65, 1.65, 1.65]} />
        <pointLight position={[0, 1.45, 0]} intensity={0.65} color="#FFF0D4" distance={2.8} decay={2} />
      </group>
    </group>
  );
}

/**
 * 5. Upper-Left Presentation & Shelving Area (x = -3.8, z = -3.4)
 */
export function ArtCanvasDisplay({ currentNode }: FurnitureProps) {
  const bookcaseModel = useGLTF('/assets/models/furniture/bookcase-books.glb');

  return (
    <group position={[-3.8, 0, -3.4]}>
      {/* Textured Rectangular Area Rug */}
      <mesh position={[0, 0.003, 0.4]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[2.4, 1.8]} />
        <meshStandardMaterial color="#DCD6CB" roughness={0.92} />
      </mesh>

      {/* Large Mobile Presentation Kanban Whiteboard on Wheeled Steel Frame */}
      <group position={[-0.2, 0, 0]} rotation={[0, 0.35, 0]}>
        {/* Main Board Surface with Glossy White Enamel */}
        <RoundedBox radius={0.02} smoothness={3} args={[1.75, 1.15, 0.03]} position={[0, 1.35, 0]} castShadow receiveShadow>
          <meshStandardMaterial color="#FFFFFF" roughness={0.2} metalness={0.05} />
        </RoundedBox>
        {/* Outer Aluminum Bezel Frame */}
        <mesh position={[0, 1.35, 0]}>
          <boxGeometry args={[1.79, 1.19, 0.025]} />
          <meshStandardMaterial color="#334155" roughness={0.35} metalness={0.8} />
        </mesh>

        {/* Kanban Board Header Bar */}
        <mesh position={[0, 1.83, 0.017]}>
          <planeGeometry args={[1.68, 0.09]} />
          <meshStandardMaterial color="#0F172A" roughness={0.4} />
        </mesh>

        {/* Kanban Column Dividers (3 vertical lines dividing into 4 columns) */}
        {[-0.42, 0.0, 0.42].map((x, idx) => (
          <mesh key={`kanban-col-div-${idx}`} position={[x, 1.33, 0.017]}>
            <planeGeometry args={[0.008, 0.88]} />
            <meshStandardMaterial color="#CBD5E1" roughness={0.5} />
          </mesh>
        ))}

        {/* Column 1: BACKLOG / TO DO (Sticky Notes) */}
        <mesh position={[-0.63, 1.62, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#FBBF24" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[-0.63, 1.40, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#F59E0B" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[-0.63, 1.18, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#FDE047" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>

        {/* Column 2: IN PROGRESS (Tech Writing & Scouting Cards) */}
        <mesh position={[-0.21, 1.58, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#38BDF8" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[-0.21, 1.35, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#0284C7" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>

        {/* Column 3: SOP AUDIT / REVIEW (Kang Bos Primary Audit Target Cards) */}
        <mesh position={[0.21, 1.60, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#FB7185" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0.21, 1.38, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#E11D48" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0.21, 1.15, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#FDA4AF" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>

        {/* Column 4: DONE / PUBLISHED (Success Cards) */}
        <mesh position={[0.63, 1.62, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#34D399" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0.63, 1.40, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#10B981" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0.63, 1.18, 0.018]}>
          <planeGeometry args={[0.18, 0.16]} />
          <meshStandardMaterial color="#059669" roughness={0.6} side={THREE.DoubleSide} />
        </mesh>

        {/* Aluminum Dry-Erase Marker Tray & Markers at Bottom */}
        <group position={[0, 0.77, 0.04]}>
          {/* Tray */}
          <mesh castShadow>
            <boxGeometry args={[1.68, 0.025, 0.07]} />
            <meshStandardMaterial color="#64748B" metalness={0.8} roughness={0.3} />
          </mesh>
          {/* 3 Dry-Erase Markers (Black, Blue, Red) */}
          <mesh position={[-0.3, 0.02, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.01, 0.01, 0.13, 8]} />
            <meshStandardMaterial color="#0F172A" roughness={0.4} />
          </mesh>
          <mesh position={[-0.12, 0.02, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.01, 0.01, 0.13, 8]} />
            <meshStandardMaterial color="#2563EB" roughness={0.4} />
          </mesh>
          <mesh position={[0.06, 0.02, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.01, 0.01, 0.13, 8]} />
            <meshStandardMaterial color="#DC2626" roughness={0.4} />
          </mesh>
          {/* Eraser */}
          <mesh position={[0.3, 0.025, 0]}>
            <boxGeometry args={[0.12, 0.035, 0.05]} />
            <meshStandardMaterial color="#1E293B" roughness={0.7} />
          </mesh>
        </group>

        {/* Steel Stand Legs & Casters */}
        <mesh position={[-0.7, 0.65, 0]} castShadow>
          <boxGeometry args={[0.04, 1.3, 0.04]} />
          <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
        </mesh>
        <mesh position={[0.7, 0.65, 0]} castShadow>
          <boxGeometry args={[0.04, 1.3, 0.04]} />
          <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
        </mesh>
        <mesh position={[0, 0.35, 0]}>
          <boxGeometry args={[1.44, 0.03, 0.03]} />
          <meshStandardMaterial color="#2B3038" roughness={0.4} metalness={0.8} />
        </mesh>
      </group>

      {/* Real Quaternius Oak Bookshelf with Books */}
      <group position={[1.6, 0, -0.9]} rotation={[0, 0, 0]}>
        <Clone object={bookcaseModel.scene} scale={[0.58, 0.58, 0.58]} />
      </group>
    </group>
  );
}

/**
 * 6. Realistic Poly Haven Potted Plants Collection
 * Clones high-detail .glb/.gltf plant meshes across 14 strategic points.
 */
export function PottedPlantCollection() {
  const plant1 = useGLTF('/models/potted_plant_01/potted_plant_01.gltf');
  const plant2 = useGLTF('/models/potted_plant_02/potted_plant_02.gltf');
  const plant4 = useGLTF('/models/potted_plant_04/potted_plant_04.gltf');

  // 14 Placement coordinates across the Scandinavian office
  const placements = [
    // 1. Lower-left corner near cutaway wall
    { model: plant1, pos: [-5.8, 0, 4.8], scale: 1.1, rot: [0, 0.4, 0] },
    // 2. Beside Stark's desk left
    { model: plant2, pos: [-4.6, 0, 1.5], scale: 1.2, rot: [0, 1.2, 0] },
    // 3. Behind Stark's divider screen
    { model: plant4, pos: [-4.6, 0, -0.2], scale: 1.3, rot: [0, 2.1, 0] },
    // 4. Upper-left presentation area near whiteboard
    { model: plant1, pos: [-5.2, 0, -2.4], scale: 1.05, rot: [0, 0.8, 0] },
    // 5. Beside the tall bookshelf
    { model: plant2, pos: [-2.8, 0, -5.2], scale: 1.15, rot: [0, 1.5, 0] },
    // 6. Beside the window credenza left
    { model: plant4, pos: [-2.4, 0, -5.2], scale: 1.25, rot: [0, 0.2, 0] },
    // 7. Beside the window credenza right
    { model: plant2, pos: [2.4, 0, -5.2], scale: 1.2, rot: [0, 2.8, 0] },
    // 8. Between credenza and lounge slat wall
    { model: plant1, pos: [3.2, 0, -5.2], scale: 1.2, rot: [0, 1.1, 0] },
    // 9. Beside the velvet sofa left
    { model: plant4, pos: [2.4, 0, -3.2], scale: 1.25, rot: [0, 0.5, 0] },
    // 10. Beside the velvet sofa right
    { model: plant1, pos: [5.6, 0, -3.2], scale: 1.1, rot: [0, 2.3, 0] },
    // 11. Beside Usagi's desk right
    { model: plant2, pos: [4.6, 0, 1.5], scale: 1.2, rot: [0, 1.7, 0] },
    // 12. In front of Usagi's desk
    { model: plant4, pos: [4.6, 0, 2.8], scale: 1.15, rot: [0, 0.9, 0] },
    // 13. Left front cutaway planter pedestal
    { model: plant2, pos: [-1.4, 0.72, 5.4], scale: 0.85, rot: [0, 0.3, 0] },
    // 14. Right front cutaway planter pedestal
    { model: plant2, pos: [1.4, 0.72, 5.4], scale: 0.85, rot: [0, 1.8, 0] },
  ];

  return (
    <group>
      {placements.map((p, i) => (
        <group key={`plant-${i}`} position={p.pos as [number, number, number]} rotation={p.rot as [number, number, number]}>
          <Clone object={p.model.scene} scale={[p.scale, p.scale, p.scale]} />
        </group>
      ))}
    </group>
  );
}

/**
 * 7. Maintenance & Storage Archive (Discreet Bin)
 */
/**
 * 7. Scandinavian High-Tech Server Rack & Microservice Archive
 * Features triple server towers (Keselip-API, Kataku-API & Dongeng-API),
 * rotated 90 degrees with back against the right wall and front facing the room,
 * with dynamic LED strips, local point light, and real-time floating nameplates.
 */
interface SingleServerRackProps {
  position: [number, number, number];
  rotation?: [number, number, number];
  serviceId: string;
  serviceName: string;
  endpointDisplay: string;
  isDegraded: boolean;
  statusCode?: number | null;
  latencyMs?: number;
  error?: string | null;
  ledPhaseOffset?: number;
  badgeY?: number;
  isTopPriority?: boolean;
}

function SingleServerRack({
  position,
  rotation = [0, -Math.PI / 2, 0],
  serviceName,
  endpointDisplay,
  isDegraded,
  statusCode,
  latencyMs,
  error,
  ledPhaseOffset = 0,
  badgeY = 1.55,
  isTopPriority = false,
}: SingleServerRackProps) {
  const ledMatRef = useRef<THREE.MeshStandardMaterial>(null);
  const pointLightRef = useRef<THREE.PointLight>(null);
  const hologramWireRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (isDegraded) {
      // Fast flashing red LED (10 rad/s)
      const blink = Math.sin(t * 10 + ledPhaseOffset) > 0;
      if (ledMatRef.current) {
        ledMatRef.current.color.set(blink ? '#EF4444' : '#450A0A');
        ledMatRef.current.emissive.set(blink ? '#EF4444' : '#1F0505');
        ledMatRef.current.emissiveIntensity = blink ? 3.0 : 0.2;
      }
      if (pointLightRef.current) {
        pointLightRef.current.color.set('#EF4444');
        pointLightRef.current.intensity = blink ? 1.8 : 0.1;
      }
      if (hologramWireRef.current) {
        hologramWireRef.current.rotation.y = t * 1.5;
        hologramWireRef.current.rotation.x = Math.sin(t * 2) * 0.2;
      }
    } else {
      // Calm green breathing LED
      const breath = 0.8 + 0.3 * Math.sin(t * 2 + ledPhaseOffset);
      if (ledMatRef.current) {
        ledMatRef.current.color.set('#10B981');
        ledMatRef.current.emissive.set('#10B981');
        ledMatRef.current.emissiveIntensity = 1.2 * breath;
      }
      if (pointLightRef.current) {
        pointLightRef.current.color.set('#10B981');
        pointLightRef.current.intensity = 0.5 * breath;
      }
    }
  });

  return (
    <group position={position} rotation={rotation}>
      {/* Server Tower Chassis (Sleek dark obsidian) */}
      <RoundedBox radius={0.025} smoothness={3} args={[0.50, 1.35, 0.50]} position={[0, 0.68, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#1A1E26" roughness={0.35} metalness={0.8} />
      </RoundedBox>

      {/* Front Perforated Grill / Tinted Smoked Glass Panel */}
      <mesh position={[0, 0.68, 0.255]}>
        <planeGeometry args={[0.44, 1.24]} />
        <meshStandardMaterial
          color="#0F1216"
          roughness={0.1}
          metalness={0.9}
          transparent
          opacity={0.7}
        />
      </mesh>

      {/* Server Blades inside cabinet */}
      {[0.28, 0.54, 0.80, 1.06].map((y, idx) => (
        <group key={`blade-${idx}`} position={[0, y, 0.10]}>
          {/* Blade Unit */}
          <mesh castShadow>
            <boxGeometry args={[0.42, 0.20, 0.34]} />
            <meshStandardMaterial color="#242A35" roughness={0.5} metalness={0.65} />
          </mesh>

          {/* Drive Bay Horizontal Dividers */}
          <mesh position={[0, 0, 0.172]}>
            <boxGeometry args={[0.38, 0.015, 0.01]} />
            <meshStandardMaterial color="#3A4250" roughness={0.4} metalness={0.8} />
          </mesh>

          {/* Brushed Aluminum Handles */}
          <mesh position={[-0.18, 0, 0.175]}>
            <boxGeometry args={[0.014, 0.12, 0.02]} />
            <meshStandardMaterial color="#94A3B8" roughness={0.2} metalness={0.9} />
          </mesh>
          <mesh position={[0.18, 0, 0.175]}>
            <boxGeometry args={[0.014, 0.12, 0.02]} />
            <meshStandardMaterial color="#94A3B8" roughness={0.2} metalness={0.9} />
          </mesh>
        </group>
      ))}

      {/* LED Status Indicator Strips */}
      <group position={[0, 0, 0.258]}>
        {[-0.13, -0.065, 0, 0.065, 0.13].map((x, i) => (
          <React.Fragment key={`led-col-${i}`}>
            {[0.32, 0.58, 0.84, 1.10].map((y, j) => (
              <mesh key={`led-${i}-${j}`} position={[x, y, 0]}>
                <boxGeometry args={[0.014, 0.012, 0.005]} />
                <meshStandardMaterial
                  ref={i === 0 && j === 0 ? ledMatRef : undefined}
                  color={isDegraded ? '#EF4444' : '#10B981'}
                  emissive={isDegraded ? '#EF4444' : '#10B981'}
                  emissiveIntensity={isDegraded ? 2.5 : 1.2}
                  roughness={0.2}
                />
              </mesh>
            ))}
          </React.Fragment>
        ))}
      </group>

      {/* LED Point Light cast onto floor and wall */}
      <pointLight
        ref={pointLightRef}
        position={[0, 0.75, 0.42]}
        color={isDegraded ? '#EF4444' : '#10B981'}
        intensity={isDegraded ? 1.8 : 0.5}
        distance={3.0}
        decay={2}
      />

      {/* Top Floating Hologram Badge with Server Name & Real-time Status */}
      <group position={[0, badgeY, 0]}>
        {/* 3D Wireframe Diamond when degraded */}
        {isDegraded && (
          <mesh ref={hologramWireRef} position={[0, 0.08, 0]}>
            <octahedronGeometry args={[0.20, 0]} />
            <meshStandardMaterial
              color="#EF4444"
              emissive="#EF4444"
              emissiveIntensity={isTopPriority ? 3.0 : 2.0}
              wireframe
            />
          </mesh>
        )}

        {/* 2D Billboard Hologram Badge with Service Name & Dynamic Z-Index */}
        <Html
          center
          distanceFactor={11}
          position={[0, isDegraded ? 0.14 : 0, 0]}
          zIndexRange={isTopPriority ? [99999, 90000] : isDegraded ? [8000, 5000] : [100, 10]}
          style={{
            zIndex: isTopPriority ? 99999 : isDegraded ? 5000 : 10,
            pointerEvents: 'none',
          }}
        >
          {isDegraded ? (
            <div
              className="punggawa-3d-badge"
              style={{
                background: isTopPriority ? 'rgba(220, 20, 60, 0.98)' : 'rgba(185, 28, 28, 0.96)',
                border: isTopPriority ? '2px solid #FFFFFF' : '1.5px solid #F87171',
                borderRadius: '8px',
                padding: isTopPriority ? '6px 14px' : '5px 12px',
                color: '#FFFFFF',
                fontSize: isTopPriority ? '11.5px' : '10.5px',
                fontWeight: 900,
                letterSpacing: '0.04em',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
                boxShadow: isTopPriority
                  ? '0 0 35px rgba(239, 68, 68, 1), 0 0 20px rgba(255, 255, 255, 0.8), 0 6px 20px rgba(0,0,0,0.6)'
                  : '0 0 20px rgba(239, 68, 68, 0.85), 0 0 10px rgba(239, 68, 68, 0.5)',
                whiteSpace: 'nowrap',
                userSelect: 'none',
                textShadow: '0 1px 3px rgba(0,0,0,0.7)',
                animation: isTopPriority ? 'pulse 0.7s infinite' : 'pulse 1s infinite',
                transform: isTopPriority ? 'scale(1.12)' : undefined,
                transformOrigin: 'center center',
                pointerEvents: 'none',
                zIndex: isTopPriority ? 99999 : isDegraded ? 5000 : 10,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ fontSize: isTopPriority ? '13px' : '12px' }}>⚠️</span>
                <span>{serviceName}</span>
                <span
                  style={{
                    fontSize: '9px',
                    background: 'rgba(0, 0, 0, 0.35)',
                    padding: '1px 5px',
                    borderRadius: '4px',
                    color: '#FCA5A5',
                  }}
                >
                  {statusCode ? `HTTP ${statusCode}` : 'DOWN'}
                </span>
              </div>
              <div style={{ fontSize: '9px', color: '#FEE2E2', fontWeight: 700 }}>
                {error ? (error.length > 26 ? error.slice(0, 26) + '...' : error) : 'Service Unreachable'}
              </div>
            </div>
          ) : (
            <div
              className="punggawa-3d-badge"
              style={{
                background: 'rgba(15, 23, 42, 0.92)',
                border: '1px solid rgba(16, 185, 129, 0.6)',
                borderRadius: '7px',
                padding: '3px 8px',
                color: '#ECFDF5',
                fontSize: '10px',
                fontWeight: 800,
                letterSpacing: '0.03em',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '2px',
                boxShadow: '0 0 12px rgba(16, 185, 129, 0.3)',
                whiteSpace: 'nowrap',
                userSelect: 'none',
                opacity: 0.95,
                pointerEvents: 'none',
                zIndex: 10,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: '#10B981',
                    boxShadow: '0 0 6px #10B981',
                  }}
                />
                <span style={{ color: '#F8FAFC', fontWeight: 900 }}>{serviceName}</span>
                <span style={{ color: '#34D399', fontSize: '9px', fontWeight: 700 }}>200 OK</span>
              </div>
              <div style={{ fontSize: '8px', color: '#6EE7B7', fontWeight: 600 }}>
                ⚡ {latencyMs || 250}ms • {endpointDisplay}
              </div>
            </div>
          )}
        </Html>
      </group>
    </group>
  );
}

export function ServerArchiveRack({ currentNode, isDegraded = false, healthData }: FurnitureProps) {
  // Count degraded services to determine if only 1 service has error
  const degradedList = (healthData?.services || []).filter((s) => s.status !== 'healthy');
  const isSingleDegraded = degradedList.length === 1;

  // Extract real-time status for Keselip-API
  const srvKeselip = healthData?.services?.find((s) => s.id === 'keselip');
  const isKeselipDegraded = srvKeselip ? srvKeselip.status !== 'healthy' : isDegraded;
  const keselipCode = srvKeselip?.status_code;
  const keselipLatency = srvKeselip?.latency_ms;
  const keselipError = srvKeselip?.error;
  const isKeselipTop = isKeselipDegraded && isSingleDegraded;

  // Extract real-time status for Kataku-API
  const srvKataku = healthData?.services?.find((s) => s.id === 'kataku');
  const isKatakuDegraded = srvKataku ? srvKataku.status !== 'healthy' : isDegraded;
  const katakuCode = srvKataku?.status_code;
  const katakuLatency = srvKataku?.latency_ms;
  const katakuError = srvKataku?.error;
  const isKatakuTop = isKatakuDegraded && isSingleDegraded;

  // Extract real-time status for Dongeng-API
  const srvDongeng = healthData?.services?.find((s) => s.id === 'dongeng');
  const isDongengDegraded = srvDongeng ? srvDongeng.status !== 'healthy' : isDegraded;
  const dongengCode = srvDongeng?.status_code;
  const dongengLatency = srvDongeng?.latency_ms;
  const dongengError = srvDongeng?.error;
  const isDongengTop = isDongengDegraded && isSingleDegraded;

  return (
    <group>
      {/* Server Tower 1: Keselip-API (Back against right wall X=6.34, Z=-1.75) */}
      <SingleServerRack
        position={[6.34, 0, -1.75]}
        rotation={[0, -Math.PI / 2, 0]}
        serviceId="keselip"
        serviceName="Keselip-API"
        endpointDisplay="keselipapi"
        isDegraded={isKeselipDegraded}
        isTopPriority={isKeselipTop}
        statusCode={keselipCode}
        latencyMs={keselipLatency}
        error={keselipError}
        ledPhaseOffset={0}
        badgeY={1.58}
      />

      {/* Server Tower 2: Kataku-API (Back against right wall X=6.34, Z=-0.45, Center) */}
      <SingleServerRack
        position={[6.34, 0, -0.45]}
        rotation={[0, -Math.PI / 2, 0]}
        serviceId="kataku"
        serviceName="Kataku-API"
        endpointDisplay="katakuapi"
        isDegraded={isKatakuDegraded}
        isTopPriority={isKatakuTop}
        statusCode={katakuCode}
        latencyMs={katakuLatency}
        error={katakuError}
        ledPhaseOffset={1.5}
        badgeY={1.58}
      />

      {/* Server Tower 3: Dongeng-API (Back against right wall X=6.34, Z=0.85) */}
      <SingleServerRack
        position={[6.34, 0, 0.85]}
        rotation={[0, -Math.PI / 2, 0]}
        serviceId="dongeng"
        serviceName="Dongeng-API"
        endpointDisplay="agoose/posts"
        isDegraded={isDongengDegraded}
        isTopPriority={isDongengTop}
        statusCode={dongengCode}
        latencyMs={dongengLatency}
        error={dongengError}
        ledPhaseOffset={3.0}
        badgeY={1.58}
      />
    </group>
  );
}

/**
 * Backward compatibility exports
 */
export const DeskWorkstation = StarkWorkstation;
export const SOPReviewPod = BayZeroWorkstation;
export const StorageArchiveCabinet = ServerArchiveRack;

// Preload all models
useGLTF.preload('/assets/models/furniture/office-chair.glb');
useGLTF.preload('/assets/models/furniture/sofa-02.glb');
useGLTF.preload('/assets/models/furniture/bookcase-books.glb');
useGLTF.preload('/assets/models/props/computer-keyboard.glb');
useGLTF.preload('/assets/models/props/computer-mouse.glb');
useGLTF.preload('/assets/models/props/lamp-desk.glb');
useGLTF.preload('/assets/models/props/lamp-floor.glb');
useGLTF.preload('/assets/models/props/laptop.glb');
useGLTF.preload('/assets/models/props/pillow.glb');
useGLTF.preload('/assets/models/props/pillow-blue.glb');
useGLTF.preload('/models/modern_arm_chair_01/modern_arm_chair_01.gltf');
useGLTF.preload('/models/coffee_table_round_01/coffee_table_round_01.gltf');
useGLTF.preload('/models/potted_plant_01/potted_plant_01.gltf');
useGLTF.preload('/models/potted_plant_02/potted_plant_02.gltf');
useGLTF.preload('/models/potted_plant_04/potted_plant_04.gltf');
