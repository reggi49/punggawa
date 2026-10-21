import React, { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';

interface JanitorDroidProps {
  isCleaning?: boolean;
}

type DroidState = 'DOCKED' | 'CLEANING' | 'RETURNING';

const DOCK_POSITION = new THREE.Vector3(4.6, 0.06, -0.2);
const DOCK_ROTATION = -Math.PI / 2;

const CLEANING_WAYPOINTS = [
  new THREE.Vector3(3.2, 0.06, -0.4),
  new THREE.Vector3(1.8, 0.06, 0.5),
  new THREE.Vector3(0.0, 0.06, 0.8),
  new THREE.Vector3(-1.8, 0.06, 0.5),
  new THREE.Vector3(-2.8, 0.06, -0.5),
  new THREE.Vector3(0.0, 0.06, -2.2),
  new THREE.Vector3(2.5, 0.06, -2.0),
];

export function JanitorDroid({ isCleaning = false }: JanitorDroidProps) {
  const droidRef = useRef<THREE.Group>(null);
  const sensorEyeRef = useRef<THREE.MeshStandardMaterial>(null);
  const dockLightRef = useRef<THREE.MeshStandardMaterial>(null);
  const brushLeftRef = useRef<THREE.Group>(null);
  const brushRightRef = useRef<THREE.Group>(null);

  const [droidState, setDroidState] = useState<DroidState>('DOCKED');
  const [waypointIdx, setWaypointIdx] = useState(0);

  // Posisi droid yang dilacak
  const currentPos = useRef<THREE.Vector3>(DOCK_POSITION.clone());

  useFrame((state, delta) => {
    const t = state.clock.getElapsedTime();
    const droid = droidRef.current;

    // 1. Logika Transisi State
    if (isCleaning) {
      if (droidState === 'DOCKED' || droidState === 'RETURNING') {
        setDroidState('CLEANING');
      }
    } else {
      if (droidState === 'CLEANING') {
        setDroidState('RETURNING');
      }
    }

    // 2. Navigasi & Interpolasi Pergerakan
    if (droid) {
      let targetPos = DOCK_POSITION;

      if (droidState === 'CLEANING') {
        targetPos = CLEANING_WAYPOINTS[waypointIdx];
        const dist = currentPos.current.distanceTo(targetPos);

        // Jika sudah dekat waypoint, lanjut ke waypoint berikutnya
        if (dist < 0.25) {
          setWaypointIdx((prev) => (prev + 1) % CLEANING_WAYPOINTS.length);
        }
      } else if (droidState === 'RETURNING') {
        targetPos = DOCK_POSITION;
        const distToDock = currentPos.current.distanceTo(DOCK_POSITION);
        if (distToDock < 0.08) {
          currentPos.current.copy(DOCK_POSITION);
          setDroidState('DOCKED');
        }
      }

      if (droidState !== 'DOCKED') {
        // Kecepatan gerak santai
        const moveSpeed = Math.min(delta * 1.4, 0.08);
        currentPos.current.lerp(targetPos, moveSpeed);

        // Rotasi menghadap waypoint target
        const dir = new THREE.Vector3().subVectors(targetPos, currentPos.current);
        if (dir.lengthSq() > 0.001) {
          const targetAngle = Math.atan2(dir.x, dir.z);
          let diff = targetAngle - droid.rotation.y;
          while (diff < -Math.PI) diff += Math.PI * 2;
          while (diff > Math.PI) diff -= Math.PI * 2;
          droid.rotation.y += diff * Math.min(delta * 5.0, 1.0);
        }

        // Getar/wobble mekanis halus di sumbu Y
        const wobble = Math.sin(t * 18) * 0.004;
        droid.position.set(currentPos.current.x, currentPos.current.y + wobble, currentPos.current.z);

        // Putaran sikat pembersih
        if (brushLeftRef.current) brushLeftRef.current.rotation.y += delta * 15;
        if (brushRightRef.current) brushRightRef.current.rotation.y -= delta * 15;
      } else {
        // DOCKED: tetap tepat di dock
        droid.position.copy(DOCK_POSITION);
        droid.rotation.y = THREE.MathUtils.damp(droid.rotation.y, DOCK_ROTATION, 4.0, delta);
      }
    }

    // 3. Efek Lampu Sensor Berdenyut (Pulsing Emissive)
    if (sensorEyeRef.current) {
      const pulse = 1.5 + Math.sin(t * 6) * 1.0;
      sensorEyeRef.current.emissiveIntensity = pulse;
      sensorEyeRef.current.color.set(droidState === 'CLEANING' ? '#8DA895' : '#C49A6C');
      sensorEyeRef.current.emissive.set(droidState === 'CLEANING' ? '#8DA895' : '#C49A6C');
    }

    // 4. Indikator Lampu Docking Station
    if (dockLightRef.current) {
      if (droidState === 'DOCKED') {
        dockLightRef.current.color.set('#8DA895');
        dockLightRef.current.emissive.set('#8DA895');
        dockLightRef.current.emissiveIntensity = 1.2;
      } else {
        // Berkedip saat patroli keluar
        const blink = Math.sin(t * 8) > 0 ? 2.0 : 0.4;
        dockLightRef.current.color.set('#C49A6C');
        dockLightRef.current.emissive.set('#C49A6C');
        dockLightRef.current.emissiveIntensity = blink;
      }
    }
  });

  return (
    <group>
      {/* 1. DOCKING STATION PAD (Dekat Rak Server) */}
      <group position={[DOCK_POSITION.x, 0.02, DOCK_POSITION.z]}>
        {/* Base Pad Persegi Pipih */}
        <mesh position={[0, 0.02, 0]} receiveShadow>
          <boxGeometry args={[0.8, 0.04, 0.8]} />
          <meshStandardMaterial color="#4A4A4A" roughness={0.6} metalness={0.3} />
        </mesh>
        {/* Dock Border Line */}
        <mesh position={[0, 0.041, 0]}>
          <boxGeometry args={[0.82, 0.005, 0.82]} />
          <meshStandardMaterial color="#8DA895" roughness={0.5} />
        </mesh>
        {/* Dock Indicator Light */}
        <mesh position={[0, 0.05, -0.32]}>
          <boxGeometry args={[0.2, 0.02, 0.05]} />
          <meshStandardMaterial
            ref={dockLightRef}
            color="#8DA895"
            emissive="#8DA895"
            emissiveIntensity={1.2}
          />
        </mesh>
      </group>

      {/* 2. JANITOR DROID (ROOMBA BODY) */}
      <group ref={droidRef} position={[DOCK_POSITION.x, DOCK_POSITION.y, DOCK_POSITION.z]}>
        {/* Floating 3D Status Badge saat membersihkan */}
        {droidState !== 'DOCKED' && (
          <Html position={[0, 0.45, 0]} center distanceFactor={12} zIndexRange={[50, 0]}>
            <div
              className="punggawa-3d-badge"
              style={{
                background: 'rgba(244, 241, 234, 0.94)',
                border: '1.5px solid #8DA895',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                color: '#30343A',
                padding: '3px 8px',
                borderRadius: '12px',
                fontSize: '10px',
                fontWeight: 800,
                whiteSpace: 'nowrap',
                backdropFilter: 'blur(8px)',
                pointerEvents: 'none',
                userSelect: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>🧹 Menyapu DB...</span>
            </div>
          </Html>
        )}

        {/* Silinder Badan Roomba */}
        <mesh position={[0, 0.06, 0]} castShadow receiveShadow>
          <cylinderGeometry args={[0.35, 0.38, 0.12, 32]} />
          <meshStandardMaterial color="#5A5A5A" roughness={0.4} metalness={0.5} />
        </mesh>

        {/* Cincin Tepi (Warm Accent) */}
        <mesh position={[0, 0.06, 0]}>
          <cylinderGeometry args={[0.36, 0.39, 0.02, 32]} />
          <meshStandardMaterial color="#8DA895" roughness={0.4} metalness={0.3} />
        </mesh>

        {/* Bumper Depan */}
        <mesh position={[0, 0.05, 0.28]} castShadow>
          <boxGeometry args={[0.42, 0.08, 0.12]} />
          <meshStandardMaterial color="#4A4A4A" roughness={0.5} metalness={0.3} />
        </mesh>

        {/* Sensor Dome di Bagian Atas */}
        <group position={[0, 0.13, 0]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.1, 0.12, 0.04, 16]} />
            <meshStandardMaterial color="#3A3A3A" metalness={0.7} roughness={0.3} />
          </mesh>
          {/* Mata Lampu Sensor */}
          <mesh position={[0, 0.02, 0.08]}>
            <sphereGeometry args={[0.025, 12, 12]} />
            <meshStandardMaterial
              ref={sensorEyeRef}
              color="#8DA895"
              emissive="#8DA895"
              emissiveIntensity={1.0}
            />
          </mesh>
        </group>

        {/* Mini Rotating Brushes (Kiri & Kanan Depan) */}
        <group ref={brushLeftRef} position={[-0.22, 0.01, 0.26]}>
          <mesh>
            <cylinderGeometry args={[0.06, 0.06, 0.01, 6]} />
            <meshStandardMaterial color="#6B6B6B" roughness={0.5} metalness={0.2} />
          </mesh>
        </group>
        <group ref={brushRightRef} position={[0.22, 0.01, 0.26]}>
          <mesh>
            <cylinderGeometry args={[0.06, 0.06, 0.01, 6]} />
            <meshStandardMaterial color="#6B6B6B" roughness={0.5} metalness={0.2} />
          </mesh>
        </group>
      </group>
    </group>
  );
}

