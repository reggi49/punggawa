import React, { useRef, useState, useEffect } from 'react';
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
  new THREE.Vector3(3.4, 0.06, -0.6), // Area dekat rak server & meja Usagi
  new THREE.Vector3(2.2, 0.06, 1.4),  // Koridor depan meja Usagi
  new THREE.Vector3(0.0, 0.06, 1.6),  // Koridor tengah depan meja meeting
  new THREE.Vector3(-2.2, 0.06, 1.4), // Koridor depan meja Kang Nulis
  new THREE.Vector3(-3.4, 0.06, -0.6), // Depan rak buku / kanvas seni
  new THREE.Vector3(-1.2, 0.06, -2.0), // Area sofa santai & coffee corner
  new THREE.Vector3(1.6, 0.06, -1.8),  // Lorong belakang meja meeting
];

export function JanitorDroid({ isCleaning = false }: JanitorDroidProps) {
  const droidRef = useRef<THREE.Group>(null);
  const sensorEyeRef = useRef<THREE.MeshStandardMaterial>(null);
  const dockLightRef = useRef<THREE.MeshStandardMaterial>(null);
  const brushLeftRef = useRef<THREE.Group>(null);
  const brushRightRef = useRef<THREE.Group>(null);

  const [droidState, setDroidState] = useState<DroidState>('DOCKED');
  const [waypointIdx, setWaypointIdx] = useState(0);

  // Timer pembersihan aktif (minimal 25 detik patroli menyapu keliling kantor)
  const activeCleaningUntil = useRef<number>(0);

  // Posisi droid yang dilacak
  const currentPos = useRef<THREE.Vector3>(DOCK_POSITION.clone());

  // Trigger pembersihan saat sinyal isCleaning aktif
  useEffect(() => {
    if (isCleaning) {
      activeCleaningUntil.current = Math.max(activeCleaningUntil.current, Date.now() + 25000);
      setDroidState('CLEANING');
    }
  }, [isCleaning]);

  useFrame((state, delta) => {
    const t = state.clock.getElapsedTime();
    const now = Date.now();
    const droid = droidRef.current;

    const shouldClean = isCleaning || now < activeCleaningUntil.current;

    // 1. Logika Transisi State
    if (shouldClean) {
      if (droidState === 'DOCKED' || droidState === 'RETURNING') {
        setDroidState('CLEANING');
      }
    } else {
      if (droidState === 'CLEANING') {
        setDroidState('RETURNING');
      }
    }

    // 2. Navigasi & Interpolasi Pergerakan Keliling Kantor
    if (droid) {
      let targetPos = DOCK_POSITION;

      if (droidState === 'CLEANING') {
        targetPos = CLEANING_WAYPOINTS[waypointIdx];
        const dist = currentPos.current.distanceTo(targetPos);

        // Jika sudah dekat waypoint, lanjut ke rute waypoint berikutnya
        if (dist < 0.35) {
          setWaypointIdx((prev) => (prev + 1) % CLEANING_WAYPOINTS.length);
        }
      } else if (droidState === 'RETURNING') {
        targetPos = DOCK_POSITION;
        const distToDock = currentPos.current.distanceTo(DOCK_POSITION);
        if (distToDock < 0.1) {
          currentPos.current.copy(DOCK_POSITION);
          setDroidState('DOCKED');
        }
      }

      if (droidState !== 'DOCKED') {
        // Kecepatan jelajah menyapu yang mantap & realistis
        const moveSpeed = Math.min(delta * 1.6, 0.09);
        currentPos.current.lerp(targetPos, moveSpeed);

        // Rotasi halus menghadap waypoint target
        const dir = new THREE.Vector3().subVectors(targetPos, currentPos.current);
        if (dir.lengthSq() > 0.001) {
          const targetAngle = Math.atan2(dir.x, dir.z);
          let diff = targetAngle - droid.rotation.y;
          while (diff < -Math.PI) diff += Math.PI * 2;
          while (diff > Math.PI) diff -= Math.PI * 2;
          droid.rotation.y += diff * Math.min(delta * 5.0, 1.0);
        }

        // Getar/wobble mekanis halus di sumbu Y (efek menyapu karpet/lantai)
        const wobble = Math.sin(t * 18) * 0.004;
        droid.position.set(currentPos.current.x, currentPos.current.y + wobble, currentPos.current.z);

        // Putaran sikat pembersih di bawah bumper
        if (brushLeftRef.current) brushLeftRef.current.rotation.y += delta * 18;
        if (brushRightRef.current) brushRightRef.current.rotation.y -= delta * 18;
      } else {
        // DOCKED: tetap tepat di docking station
        droid.position.copy(DOCK_POSITION);
        droid.rotation.y = THREE.MathUtils.damp(droid.rotation.y, DOCK_ROTATION, 4.0, delta);
      }
    }

    // 3. Efek Lampu Sensor Berdenyut (Pulsing Emissive)
    if (sensorEyeRef.current) {
      const pulse = 1.5 + Math.sin(t * 6) * 1.0;
      sensorEyeRef.current.emissiveIntensity = pulse;
      sensorEyeRef.current.color.set(droidState === 'CLEANING' ? '#06B6D4' : '#C49A6C');
      sensorEyeRef.current.emissive.set(droidState === 'CLEANING' ? '#06B6D4' : '#C49A6C');
    }

    // 4. Indikator Lampu Docking Station
    if (dockLightRef.current) {
      if (droidState === 'DOCKED') {
        dockLightRef.current.color.set('#8DA895');
        dockLightRef.current.emissive.set('#8DA895');
        dockLightRef.current.emissiveIntensity = 1.2;
      } else {
        // Berkedip saat robot sedang patroli menyapu
        const blink = Math.sin(t * 8) > 0 ? 2.0 : 0.4;
        dockLightRef.current.color.set('#06B6D4');
        dockLightRef.current.emissive.set('#06B6D4');
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
          <meshStandardMaterial color="#06B6D4" roughness={0.5} />
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

      {/* 2. JANITOR DROID (ROBOT VACUUM CLEANER BODY) */}
      <group ref={droidRef} position={[DOCK_POSITION.x, DOCK_POSITION.y, DOCK_POSITION.z]}>
        {/* Floating 3D Status Badge saat membersihkan */}
        {droidState !== 'DOCKED' && (
          <Html position={[0, 0.45, 0]} center distanceFactor={12} zIndexRange={[50, 0]}>
            <div
              className="punggawa-3d-badge"
              style={{
                background: 'rgba(244, 241, 234, 0.96)',
                border: '1.5px solid #06B6D4',
                boxShadow: '0 4px 14px rgba(6, 182, 212, 0.25)',
                color: '#1E293B',
                padding: '4px 10px',
                borderRadius: '14px',
                fontSize: '10.5px',
                fontWeight: 800,
                whiteSpace: 'nowrap',
                backdropFilter: 'blur(8px)',
                pointerEvents: 'none',
                userSelect: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  backgroundColor: droidState === 'CLEANING' ? '#06b6d4' : '#f59e0b',
                  display: 'inline-block',
                }}
              />
              <span>
                {droidState === 'CLEANING'
                  ? '🧹 Robot Vacuum • Menyapu Lantai Kantor'
                  : '🔌 Robot Vacuum • Kembali ke Dock'}
              </span>
            </div>
          </Html>
        )}

        {/* Silinder Badan Roomba (Dapat Diklik untuk Memulai Pembersihan Manual) */}
        <mesh
          position={[0, 0.06, 0]}
          castShadow
          receiveShadow
          onClick={(e) => {
            e.stopPropagation();
            activeCleaningUntil.current = Date.now() + 25000;
            setDroidState('CLEANING');
          }}
          onPointerOver={() => {
            document.body.style.cursor = 'pointer';
          }}
          onPointerOut={() => {
            document.body.style.cursor = 'auto';
          }}
        >
          <cylinderGeometry args={[0.35, 0.38, 0.12, 32]} />
          <meshStandardMaterial color="#5A5A5A" roughness={0.4} metalness={0.5} />
        </mesh>

        {/* Cincin Tepi (Teal Accent) */}
        <mesh position={[0, 0.06, 0]}>
          <cylinderGeometry args={[0.36, 0.39, 0.02, 32]} />
          <meshStandardMaterial color="#06B6D4" roughness={0.4} metalness={0.3} />
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
              color="#06B6D4"
              emissive="#06B6D4"
              emissiveIntensity={1.0}
            />
          </mesh>
        </group>

        {/* Mini Rotating Brushes (Kiri & Kanan Depan) */}
        <group ref={brushLeftRef} position={[-0.22, 0.01, 0.26]}>
          <mesh>
            <cylinderGeometry args={[0.08, 0.08, 0.015, 8]} />
            <meshStandardMaterial color="#222" roughness={0.8} />
          </mesh>
          {/* Bulu Sikat Pembersih */}
          {[0, 1.2, 2.4, 3.6, 4.8].map((angle, idx) => (
            <mesh key={`br-l-${idx}`} rotation={[0, angle, 0]} position={[0.04, 0, 0]}>
              <boxGeometry args={[0.08, 0.008, 0.01]} />
              <meshStandardMaterial color="#C49A6C" roughness={0.6} />
            </mesh>
          ))}
        </group>

        <group ref={brushRightRef} position={[0.22, 0.01, 0.26]}>
          <mesh>
            <cylinderGeometry args={[0.08, 0.08, 0.015, 8]} />
            <meshStandardMaterial color="#222" roughness={0.8} />
          </mesh>
          {[0, 1.2, 2.4, 3.6, 4.8].map((angle, idx) => (
            <mesh key={`br-r-${idx}`} rotation={[0, angle, 0]} position={[0.04, 0, 0]}>
              <boxGeometry args={[0.08, 0.008, 0.01]} />
              <meshStandardMaterial color="#C49A6C" roughness={0.6} />
            </mesh>
          ))}
        </group>
      </group>
    </group>
  );
}

