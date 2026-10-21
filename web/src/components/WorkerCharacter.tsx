import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html, RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import { WorkerId, WORKER_PROFILES, CharacterAction, ActualAgentState } from '../types';
import { getHumanStatus } from '../utils/statusLabels';

interface CharacterProps {
  id: WorkerId;
  currentNode: string;
  action: CharacterAction;
  targetPos: [number, number, number];
  targetRotY: number;
  message?: string;
  isActive: boolean;
  isSeated?: boolean;
  socialRole?: 'speaker' | 'listener' | null;
  actualState?: ActualAgentState;
  ambientLabel?: string;
  badgeLabelOverride?: string;
  dotColorOverride?: string;
  holdingCoffeeMug?: boolean;
}

export function StylizedHumanoidCharacter({
  id,
  currentNode,
  action,
  targetPos,
  targetRotY,
  message,
  isActive,
  isSeated = false,
  socialRole = null,
  actualState = 'Idle',
  ambientLabel,
  badgeLabelOverride,
  dotColorOverride,
  holdingCoffeeMug = false,
}: CharacterProps) {
  // Root & World Tracking
  const rootRef = useRef<THREE.Group>(null);
  const currentWorldPos = useRef(new THREE.Vector3(...targetPos));

  // Humanoid Rig References
  const pelvisRef = useRef<THREE.Group>(null);
  const chestRef = useRef<THREE.Group>(null);
  const headRef = useRef<THREE.Group>(null);

  // Arms
  const leftShoulderRef = useRef<THREE.Group>(null);
  const leftElbowRef = useRef<THREE.Group>(null);
  const rightShoulderRef = useRef<THREE.Group>(null);
  const rightElbowRef = useRef<THREE.Group>(null);

  // Legs
  const leftHipRef = useRef<THREE.Group>(null);
  const leftKneeRef = useRef<THREE.Group>(null);
  const rightHipRef = useRef<THREE.Group>(null);
  const rightKneeRef = useRef<THREE.Group>(null);

  const profile = WORKER_PROFILES[id];
  const humanStatus = getHumanStatus(currentNode);

  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime() + (id === 'stark' ? 0 : id === 'usagi' ? 1.6 : 3.2);
    const root = rootRef.current;
    if (!root) return;

    // 1. Locomotion Lerp & Movement Detection
    const targetVec = new THREE.Vector3(...targetPos);
    const distToTarget = currentWorldPos.current.distanceTo(targetVec);
    const isMoving = distToTarget > 0.14;

    // Interpolasi posisi dunia
    const moveLerpSpeed = isMoving ? Math.min(delta * 4.5, 0.15) : Math.min(delta * 6.0, 0.2);
    currentWorldPos.current.lerp(targetVec, moveLerpSpeed);
    root.position.copy(currentWorldPos.current);

    // Rotasi menghadap arah gerak saat melangkah, atau arah target saat tiba
    let desiredAngle = targetRotY;
    if (isMoving) {
      const moveDir = new THREE.Vector3().subVectors(targetVec, currentWorldPos.current);
      if (moveDir.lengthSq() > 0.001) {
        desiredAngle = Math.atan2(moveDir.x, moveDir.z);
      }
    }

    let diffRot = desiredAngle - root.rotation.y;
    while (diffRot < -Math.PI) diffRot += Math.PI * 2;
    while (diffRot > Math.PI) diffRot -= Math.PI * 2;
    root.rotation.y += diffRot * Math.min(delta * 6.0, 1.0);

    // 2. Hierarchical Animation State Machine
    const pelvis = pelvisRef.current;
    const chest = chestRef.current;
    const head = headRef.current;
    const leftShoulder = leftShoulderRef.current;
    const leftElbow = leftElbowRef.current;
    const rightShoulder = rightShoulderRef.current;
    const rightElbow = rightElbowRef.current;
    const leftHip = leftHipRef.current;
    const leftKnee = leftKneeRef.current;
    const rightHip = rightHipRef.current;
    const rightKnee = rightKneeRef.current;

    if (
      !pelvis ||
      !chest ||
      !head ||
      !leftShoulder ||
      !leftElbow ||
      !rightShoulder ||
      !rightElbow ||
      !leftHip ||
      !leftKnee ||
      !rightHip ||
      !rightKnee
    ) {
      return;
    }

    // A. MODE BERJALAN NYATA (Walk Cycle)
    if (isMoving) {
      const walkSpeed = 9.0;
      const walkCycle = t * walkSpeed;

      // Bobbing naik-turun pinggul alami
      pelvis.position.y = THREE.MathUtils.lerp(
        pelvis.position.y,
        0.88 + Math.abs(Math.sin(walkCycle)) * 0.05,
        delta * 10
      );

      // Dada condong sedikit ke depan saat melangkah
      chest.rotation.x = THREE.MathUtils.lerp(chest.rotation.x, 0.08, delta * 8);
      chest.rotation.y = Math.sin(walkCycle) * 0.06;
      head.rotation.x = -0.05;
      head.rotation.y = 0;

      // Kaki mengayun dari pinggul
      const legSwing = Math.sin(walkCycle) * 0.65;
      leftHip.rotation.x = legSwing;
      rightHip.rotation.x = -legSwing;

      // Lutut menekuk wajar saat kaki mengayun ke belakang
      leftKnee.rotation.x = Math.max(0, -legSwing * 1.1);
      rightKnee.rotation.x = Math.max(0, legSwing * 1.1);

      // Ayunan tangan berlawanan arah dengan kaki (counter-swing natural)
      leftShoulder.rotation.x = -legSwing * 0.7;
      leftShoulder.rotation.z = 0.15;
      leftElbow.rotation.x = 0.25 + Math.max(0, legSwing * 0.4);

      rightShoulder.rotation.x = legSwing * 0.7;
      rightShoulder.rotation.z = -0.15;
      rightElbow.rotation.x = 0.25 + Math.max(0, -legSwing * 0.4);
      return;
    }

    // B. MODE DUDUK DI KURSI KERJA (Seated Workstation)
    if (isSeated) {
      // 1. Tinggi dudukan kursi (chairSeatY = 0.45 unit). Kunci posisi Y pinggul pada y = 0.46
      pelvis.position.y = THREE.MathUtils.lerp(pelvis.position.y, 0.46, delta * 12);
      // Jangan geser posisi Z lokal pinggul (tetap 0 di tengah bantalan)
      pelvis.position.z = THREE.MathUtils.lerp(pelvis.position.z, 0, delta * 12);

      // 2. Paha (upperLeg) berotasi -Math.PI / 2 (90 derajat lurus ke depan dari pinggul)
      leftHip.rotation.x = THREE.MathUtils.lerp(leftHip.rotation.x, -Math.PI / 2, delta * 12);
      rightHip.rotation.x = THREE.MathUtils.lerp(rightHip.rotation.x, -Math.PI / 2, delta * 12);
      leftHip.rotation.y = 0;
      rightHip.rotation.y = 0;
      leftHip.rotation.z = 0;
      rightHip.rotation.z = 0;

      // 3. Lutut/Betis (lowerLeg) berotasi +Math.PI / 2 (lurus vertikal ke bawah menuju lantai)
      leftKnee.rotation.x = THREE.MathUtils.lerp(leftKnee.rotation.x, Math.PI / 2, delta * 12);
      rightKnee.rotation.x = THREE.MathUtils.lerp(rightKnee.rotation.x, Math.PI / 2, delta * 12);
      leftKnee.rotation.y = 0;
      rightKnee.rotation.y = 0;
      leftKnee.rotation.z = 0;
      rightKnee.rotation.z = 0;

      chest.rotation.x = 0.08; // Punggung bersandar tegak alami pada sandaran kursi di z = -0.22

      if (action === 'intense_typing') {
        // Mengetik di keyboard: Lengan atas -0.45, lengan bawah -1.1 menyentuh keyboard (y = 0.76)
        const typeSpeed = 22.0;
        head.rotation.x = 0.18;
        head.rotation.y = Math.sin(t * 10) * 0.03;

        leftShoulder.rotation.x = THREE.MathUtils.lerp(leftShoulder.rotation.x, -0.45, delta * 12);
        leftShoulder.rotation.z = 0.16;
        leftElbow.rotation.x = THREE.MathUtils.lerp(
          leftElbow.rotation.x,
          -1.1 + Math.sin(t * typeSpeed) * 0.04,
          delta * 12
        );

        rightShoulder.rotation.x = THREE.MathUtils.lerp(rightShoulder.rotation.x, -0.45, delta * 12);
        rightShoulder.rotation.z = -0.16;
        rightElbow.rotation.x = THREE.MathUtils.lerp(
          rightElbow.rotation.x,
          -1.1 + Math.cos(t * typeSpeed) * 0.04,
          delta * 12
        );
      } else if (action === 'looking_monitor' || action === 'inspecting_sop') {
        // Memeriksa layar monitor / laptop dengan teliti
        head.rotation.x = 0.2;
        head.rotation.y = Math.sin(t * 0.8) * 0.05;

        leftShoulder.rotation.x = THREE.MathUtils.lerp(leftShoulder.rotation.x, -0.45, delta * 10);
        leftShoulder.rotation.z = 0.16;
        leftElbow.rotation.x = THREE.MathUtils.lerp(leftElbow.rotation.x, -1.05, delta * 10);

        rightShoulder.rotation.x = THREE.MathUtils.lerp(rightShoulder.rotation.x, -0.45, delta * 10);
        rightShoulder.rotation.z = -0.16;
        rightElbow.rotation.x = THREE.MathUtils.lerp(
          rightElbow.rotation.x,
          -1.05 + Math.sin(t * 3) * 0.03,
          delta * 10
        );
      } else if (action === 'casual_conversation') {
        // Duduk menyimak percakapan di meja meeting
        head.rotation.x = 0.06 + (Math.sin(t * 2.5) > 0.6 ? 0.06 : 0);
        head.rotation.y = Math.sin(t * 1.0) * 0.08;

        leftShoulder.rotation.x = THREE.MathUtils.lerp(leftShoulder.rotation.x, -0.4, delta * 8);
        leftShoulder.rotation.z = 0.15;
        leftElbow.rotation.x = THREE.MathUtils.lerp(leftElbow.rotation.x, -0.9, delta * 8);

        rightShoulder.rotation.x = THREE.MathUtils.lerp(rightShoulder.rotation.x, -0.4, delta * 8);
        rightShoulder.rotation.z = -0.15;
        rightElbow.rotation.x = THREE.MathUtils.lerp(rightElbow.rotation.x, -0.9, delta * 8);
      } else if (action === 'looking_around') {
        // Menoleh ke sekitar ruangan kantor secara santai
        head.rotation.x = 0.05 + Math.cos(t * 0.6) * 0.06;
        head.rotation.y = Math.sin(t * 0.7) * 0.45;

        leftShoulder.rotation.x = THREE.MathUtils.lerp(leftShoulder.rotation.x, -0.45, delta * 8);
        leftShoulder.rotation.z = 0.16;
        leftElbow.rotation.x = THREE.MathUtils.lerp(leftElbow.rotation.x, -1.05, delta * 8);

        rightShoulder.rotation.x = THREE.MathUtils.lerp(rightShoulder.rotation.x, -0.45, delta * 8);
        rightShoulder.rotation.z = -0.16;
        rightElbow.rotation.x = THREE.MathUtils.lerp(rightElbow.rotation.x, -1.05, delta * 8);
      } else if (action === 'stretching') {
        // Meregangkan badan (kedua tangan terangkat ke belakang/atas, dada membusung)
        head.rotation.x = -0.2;
        head.rotation.y = 0;
        chest.rotation.x = -0.12;

        leftShoulder.rotation.x = THREE.MathUtils.lerp(leftShoulder.rotation.x, -1.9, delta * 6);
        leftShoulder.rotation.z = 0.38;
        leftElbow.rotation.x = 0.4;

        rightShoulder.rotation.x = THREE.MathUtils.lerp(rightShoulder.rotation.x, -1.9, delta * 6);
        rightShoulder.rotation.z = -0.38;
        rightElbow.rotation.x = 0.4;
      } else if (action === 'idle_coffee') {
        // Duduk santai memegang kopi di meja
        head.rotation.x = 0.05;
        head.rotation.y = Math.sin(t * 1.2) * 0.15;

        leftShoulder.rotation.x = -0.45;
        leftShoulder.rotation.z = 0.16;
        leftElbow.rotation.x = -1.0;

        const sipCycle = Math.sin(t * 1.5);
        rightShoulder.rotation.x = THREE.MathUtils.lerp(
          rightShoulder.rotation.x,
          sipCycle > 0.6 ? -0.85 : -0.45,
          delta * 6
        );
        rightShoulder.rotation.z = -0.2;
        rightElbow.rotation.x = THREE.MathUtils.lerp(
          rightElbow.rotation.x,
          sipCycle > 0.6 ? -1.8 : -1.0,
          delta * 6
        );
      } else if (action === 'confused_scratch') {
        // Bingung menggaruk kepala saat error
        head.rotation.y = Math.sin(t * 7) * 0.3;
        head.rotation.x = 0.15;

        leftShoulder.rotation.x = -0.45;
        leftElbow.rotation.x = -1.0;

        rightShoulder.rotation.x = -2.1;
        rightShoulder.rotation.z = -0.6;
        rightElbow.rotation.x = 1.6 + Math.sin(t * 14) * 0.15;
      } else {
        // Seated Observing / Standby
        head.rotation.x = 0.05;
        head.rotation.y = Math.sin(t * 1.2) * 0.12;

        leftShoulder.rotation.x = THREE.MathUtils.lerp(leftShoulder.rotation.x, -0.45, delta * 8);
        leftShoulder.rotation.z = 0.16;
        leftElbow.rotation.x = THREE.MathUtils.lerp(leftElbow.rotation.x, -1.05, delta * 8);

        rightShoulder.rotation.x = THREE.MathUtils.lerp(rightShoulder.rotation.x, -0.45, delta * 8);
        rightShoulder.rotation.z = -0.16;
        rightElbow.rotation.x = THREE.MathUtils.lerp(rightElbow.rotation.x, -1.05, delta * 8);
      }
      return;
    }

    // C. MODE BERDIRI AKTIF (Standing & Actions)
    pelvis.position.y = THREE.MathUtils.lerp(pelvis.position.y, 0.88, delta * 8);
    leftHip.rotation.x = THREE.MathUtils.lerp(leftHip.rotation.x, 0, delta * 8);
    rightHip.rotation.x = THREE.MathUtils.lerp(rightHip.rotation.x, 0, delta * 8);
    leftKnee.rotation.x = THREE.MathUtils.lerp(leftKnee.rotation.x, 0, delta * 8);
    rightKnee.rotation.x = THREE.MathUtils.lerp(rightKnee.rotation.x, 0, delta * 8);

    if (action === 'searching_archive') {
      // Memeriksa rak server / arsip
      head.rotation.y = Math.sin(t * 2.2) * 0.35;
      head.rotation.x = 0.15 + Math.cos(t * 1.5) * 0.1;
      chest.rotation.x = 0.08;

      rightShoulder.rotation.x = -1.1 + Math.sin(t * 4) * 0.2;
      rightShoulder.rotation.z = -0.2;
      rightElbow.rotation.x = 0.7;

      leftShoulder.rotation.x = -0.5 + Math.cos(t * 3) * 0.15;
      leftShoulder.rotation.z = 0.2;
      leftElbow.rotation.x = 0.6;
    } else if (action === 'drawing_canvas') {
      // Melukis di Easel / Kanvas Seni
      head.rotation.x = -0.05;
      head.rotation.y = Math.sin(t * 1.8) * 0.1;
      chest.rotation.x = 0.04;

      rightShoulder.rotation.x = -1.2 + Math.sin(t * 4) * 0.25;
      rightShoulder.rotation.y = Math.cos(t * 4) * 0.25;
      rightShoulder.rotation.z = -0.15;
      rightElbow.rotation.x = 0.6;

      leftShoulder.rotation.x = -0.2;
      leftShoulder.rotation.z = 0.2;
      leftElbow.rotation.x = 0.3;
    } else if (action === 'inspecting_sop') {
      // Memegang clipboard audit & checklist
      head.rotation.x = 0.28 + Math.sin(t * 2) * 0.08;
      head.rotation.y = Math.sin(t * 1.2) * 0.06;
      chest.rotation.x = 0.06;

      // Tangan kiri memegang clipboard hologram
      leftShoulder.rotation.x = -0.9;
      leftShoulder.rotation.z = 0.3;
      leftElbow.rotation.x = 1.1;

      // Tangan kanan memeriksa checklist
      rightShoulder.rotation.x = -0.8 + Math.sin(t * 5) * 0.15;
      rightShoulder.rotation.z = -0.2;
      rightElbow.rotation.x = 1.0;
    } else if (action === 'visiting_coffee') {
      // Berdiri santai di coffee corner memegang cangkir
      head.rotation.x = 0.05;
      head.rotation.y = Math.sin(t * 1.0) * 0.15;
      chest.rotation.x = 0.02;

      // Tangan kiri rileks di samping
      leftShoulder.rotation.x = 0.1;
      leftShoulder.rotation.z = 0.12;
      leftElbow.rotation.x = 0.2;

      // Tangan kanan memegang cangkir kopi, sesekali menyeruput
      const sip = Math.sin(t * 1.4);
      rightShoulder.rotation.x = THREE.MathUtils.lerp(
        rightShoulder.rotation.x,
        sip > 0.6 ? -1.25 : -0.75,
        delta * 6
      );
      rightShoulder.rotation.z = -0.22;
      rightElbow.rotation.x = THREE.MathUtils.lerp(
        rightElbow.rotation.x,
        sip > 0.6 ? 1.4 : 0.85,
        delta * 6
      );
    } else if (action === 'casual_conversation') {
      // Percakapan santai tatap muka antar dua pekerja (diferensiasi speaker vs listener)
      if (socialRole === 'listener') {
        // Mode Mendengarkan: Mengangguk teratur, tangan rileks menyimak
        const nod = Math.sin(t * 2.5) > 0.5 ? 0.09 : 0;
        head.rotation.x = 0.08 + nod;
        head.rotation.y = Math.sin(t * 1.0) * 0.08;
        chest.rotation.x = 0.02;

        rightShoulder.rotation.x = -0.3;
        rightShoulder.rotation.z = -0.15;
        rightElbow.rotation.x = 0.6;

        leftShoulder.rotation.x = -0.3;
        leftShoulder.rotation.z = 0.15;
        leftElbow.rotation.x = 0.6;
      } else {
        // Mode Berbicara: Kepala ekspresif, tangan kanan gestur berbicara
        head.rotation.x = 0.08 + Math.sin(t * 3.5) * 0.05;
        head.rotation.y = Math.sin(t * 1.5) * 0.1;
        chest.rotation.x = 0.04;

        rightShoulder.rotation.x = -0.75 + Math.sin(t * 3.0) * 0.2;
        rightShoulder.rotation.z = -0.18;
        rightElbow.rotation.x = 0.95 + Math.cos(t * 3.0) * 0.18;

        leftShoulder.rotation.x = -0.25;
        leftShoulder.rotation.z = 0.14;
        leftElbow.rotation.x = 0.45;
      }
    } else if (action === 'offline_rest') {
      // Mode Offline / Dormant: Kepala tertunduk rileks, tubuh tenang tidak aktif
      head.rotation.x = 0.22;
      head.rotation.y = 0;
      chest.rotation.x = 0.05;

      leftShoulder.rotation.x = 0.15;
      leftShoulder.rotation.z = 0.1;
      leftElbow.rotation.x = 0.25;

      rightShoulder.rotation.x = 0.15;
      rightShoulder.rotation.z = -0.1;
      rightElbow.rotation.x = 0.25;
    } else if (action === 'stretching') {
      // Meregangkan badan sambil berdiri
      head.rotation.x = -0.2;
      head.rotation.y = 0;
      chest.rotation.x = -0.1;

      leftShoulder.rotation.x = THREE.MathUtils.lerp(leftShoulder.rotation.x, -2.0, delta * 6);
      leftShoulder.rotation.z = 0.35;
      leftElbow.rotation.x = 0.35;

      rightShoulder.rotation.x = THREE.MathUtils.lerp(rightShoulder.rotation.x, -2.0, delta * 6);
      rightShoulder.rotation.z = -0.35;
      rightElbow.rotation.x = 0.35;
    } else if (action === 'looking_around') {
      // Berdiri santai mengamati area kantor
      head.rotation.x = 0.06;
      head.rotation.y = Math.sin(t * 0.7) * 0.45;
      chest.rotation.x = 0.02;

      leftShoulder.rotation.x = 0.08;
      leftShoulder.rotation.z = 0.12;
      leftElbow.rotation.x = 0.2;

      rightShoulder.rotation.x = 0.08;
      rightShoulder.rotation.z = -0.12;
      rightElbow.rotation.x = 0.2;
    } else if (action === 'success_celebration') {
      // Melompat gembira dengan kedua tangan terangkat ke atas!
      const hop = Math.abs(Math.sin(t * 7)) * 0.12;
      pelvis.position.y = 0.88 + hop;
      head.rotation.x = -0.2;
      head.rotation.y = Math.sin(t * 3) * 0.1;

      leftShoulder.rotation.x = THREE.MathUtils.lerp(leftShoulder.rotation.x, -2.5, delta * 10);
      leftShoulder.rotation.z = 0.45;
      leftElbow.rotation.x = 0.3;

      rightShoulder.rotation.x = THREE.MathUtils.lerp(rightShoulder.rotation.x, -2.5, delta * 10);
      rightShoulder.rotation.z = -0.45;
      rightElbow.rotation.x = 0.3;
    } else {
      // Standing Observing
      head.rotation.x = 0.05;
      head.rotation.y = Math.sin(t * 1.2) * 0.1;
      chest.rotation.x = 0;

      leftShoulder.rotation.x = 0.1;
      leftShoulder.rotation.z = 0.12;
      leftElbow.rotation.x = 0.2;

      rightShoulder.rotation.x = 0.1;
      rightShoulder.rotation.z = -0.12;
      rightElbow.rotation.x = 0.2;
    }
  });

  return (
    <group ref={rootRef} position={targetPos}>
      {/* 3D Floating Minimalist Dark Glass Pill Badge */}
      {(() => {
        let showPill = false;
        let dotColor = '#22C55E';
        let badgeLabel = 'Fokus';

        if (badgeLabelOverride) {
          showPill = true;
          dotColor = dotColorOverride || '#F59E0B';
          badgeLabel = badgeLabelOverride;
        } else if (isActive) {
          showPill = true;
          const isError = currentNode === 'failed_node';
          const isAudit = currentNode === 'sop_validator_node';
          const isMeeting = isAudit || action === 'casual_conversation' || socialRole !== null;

          if (isError) {
            dotColor = '#EF4444';
            badgeLabel = 'Error';
          } else if (isMeeting) {
            dotColor = '#F59E0B';
            badgeLabel = 'Meeting';
          } else if (id === 'usagi' && (currentNode === 'curate_node' || currentNode === 'render_cover_node')) {
            dotColor = '#22C55E';
            badgeLabel = 'Curate';
          } else if (id === 'stark' && (currentNode === 'draft_node' || currentNode === 'processor_node')) {
            dotColor = '#22C55E';
            badgeLabel = 'Fokus';
          } else {
            dotColor = '#22C55E';
            badgeLabel = humanStatus.label || 'Fokus';
          }
        } else if (actualState === 'Blocked') {
          showPill = true;
          dotColor = '#EF4444';
          badgeLabel = 'Blocked';
        } else if (actualState === 'Waiting') {
          showPill = true;
          dotColor = '#F59E0B';
          badgeLabel = 'Waiting';
        } else if (ambientLabel && (action === 'idle_coffee' || action === 'casual_conversation' || action === 'searching_archive')) {
          showPill = true;
          dotColor = action === 'casual_conversation' ? '#F59E0B' : '#38BDF8';
          badgeLabel = action === 'casual_conversation' ? 'Meeting' : ambientLabel;
        }

        if (!showPill) return null;

        const workerProfile = WORKER_PROFILES[id];
        const workerName = workerProfile?.name || (id === 'bayzero' ? 'Bay-Zero' : id === 'clara' ? 'Clara' : id);

        return (
          <Html position={[0, isSeated ? 1.62 : 2.05, 0]} center distanceFactor={14} zIndexRange={[50, 0]}>
            <div
              className="punggawa-3d-badge"
              style={{
                background: 'rgba(26, 30, 38, 0.92)',
                border: '1px solid rgba(255, 255, 255, 0.18)',
                borderRadius: '20px',
                padding: '3px 11px',
                fontSize: '11px',
                color: '#F4F1EA',
                boxShadow: '0 4px 14px rgba(0, 0, 0, 0.3)',
                backdropFilter: 'blur(8px)',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                whiteSpace: 'nowrap',
                pointerEvents: 'none',
                userSelect: 'none',
                letterSpacing: '0.01em',
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: dotColor,
                  boxShadow: `0 0 6px ${dotColor}`,
                  display: 'inline-block',
                  flexShrink: 0,
                }}
              />
              <span style={{ fontWeight: 700, color: '#FFFFFF', letterSpacing: '0.01em' }}>
                {workerName}
              </span>
              <span style={{ opacity: 0.35, fontSize: '9px', margin: '0 1px' }}>•</span>
              <span style={{ fontWeight: 500, color: '#CBD5E1' }}>
                {badgeLabel}
              </span>
            </div>
          </Html>
        );
      })()}

      {/* =========================================================================
          HUMANOID ANATOMY HIERARCHY — ZERO BOX PRIMITIVES / SMOOTH ARCHVIZ SILHOUETTES
         ========================================================================= */}
      {/* 1. PELVIS / HIPS (Pusat Sendi Pinggul) */}
      <group ref={pelvisRef} position={[0, 0.88, 0]}>
        {/* Celana Kantor / Office Chinos (Rounded Organic Volume) */}
        <RoundedBox radius={0.06} smoothness={5} args={[0.31, 0.17, 0.22]} position={[0, 0, 0]} castShadow receiveShadow>
          <meshStandardMaterial
            color={id === 'stark' ? '#262930' : id === 'usagi' ? '#324254' : id === 'clara' ? '#2C3539' : '#2E333D'}
            roughness={0.7}
          />
        </RoundedBox>
        {/* Belt */}
        <RoundedBox radius={0.012} smoothness={2} args={[0.32, 0.035, 0.23]} position={[0, 0.06, 0]}>
          <meshStandardMaterial color="#1E2024" roughness={0.6} />
        </RoundedBox>
        {/* Belt Buckle */}
        <RoundedBox radius={0.008} smoothness={2} args={[0.06, 0.04, 0.02]} position={[0, 0.06, 0.118]}>
          <meshStandardMaterial color="#D4AF37" roughness={0.3} metalness={0.8} />
        </RoundedBox>

        {/* 2. DADA & TORSO (Spine & Chest) */}
        <group ref={chestRef} position={[0, 0.14, 0]}>
          {/* Kemeja / Sweater Kantor (Rounded Soft Bevel) */}
          <RoundedBox radius={0.075} smoothness={5} args={[0.36, 0.33, 0.23]} position={[0, 0.16, 0]} castShadow receiveShadow>
            <meshStandardMaterial
              color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
              roughness={0.75}
              metalness={0.0}
            />
          </RoundedBox>

          {/* Natural Rounded Shoulders */}
          <mesh position={[-0.18, 0.27, 0]} castShadow>
            <sphereGeometry args={[0.075, 12, 12]} />
            <meshStandardMaterial
              color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
              roughness={0.75}
            />
          </mesh>
          <mesh position={[0.18, 0.27, 0]} castShadow>
            <sphereGeometry args={[0.075, 12, 12]} />
            <meshStandardMaterial
              color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
              roughness={0.75}
            />
          </mesh>

          {/* Kerah Baju / Knit Torus Ring */}
          <mesh position={[0, 0.32, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.065, 0.022, 10, 20]} />
            <meshStandardMaterial
              color={id === 'stark' ? '#262930' : id === 'usagi' ? '#EFE9DF' : id === 'clara' ? '#A85A42' : '#4B535E'}
              roughness={0.8}
            />
          </mesh>

          {/* Leher Manusia Prosedural */}
          <mesh position={[0, 0.36, 0]} castShadow>
            <cylinderGeometry args={[0.048, 0.052, 0.08, 14]} />
            <meshStandardMaterial
              color={id === 'usagi' ? '#E8B8A0' : id === 'clara' ? '#ECC5B0' : '#D4A57A'}
              roughness={0.6}
            />
          </mesh>

          {/* 3. KEPALA & WAJAH MANUSIA (Human Head Rig) */}
          <group ref={headRef} position={[0, 0.44, 0]}>
            <mesh position={[0, 0.07, 0]} castShadow>
              <sphereGeometry args={[0.115, 18, 18]} />
              <meshStandardMaterial
                color={id === 'usagi' ? '#E8B8A0' : id === 'clara' ? '#ECC5B0' : '#D4A57A'}
                roughness={0.6}
              />
            </mesh>

            {/* RAGAM GAYA RAMBUT MANUSIA MENURUT PERSONA */}
            {id === 'stark' && (
              <group position={[0, 0.09, 0]}>
                <mesh position={[0, 0.05, -0.01]} castShadow>
                  <sphereGeometry args={[0.12, 16, 16, 0, Math.PI * 2, 0, Math.PI / 1.7]} />
                  <meshStandardMaterial color="#1e293b" roughness={0.7} />
                </mesh>
                <mesh position={[0.02, 0.06, 0.08]} rotation={[0.2, 0.1, -0.15]} castShadow>
                  <capsuleGeometry args={[0.038, 0.12, 8, 10]} />
                  <meshStandardMaterial color="#111827" roughness={0.7} />
                </mesh>
                <mesh position={[0, -0.01, 0.1]}>
                  <RoundedBox radius={0.01} smoothness={2} args={[0.18, 0.04, 0.02]}>
                    <meshStandardMaterial
                      color="#8B6914"
                      roughness={0.4}
                      metalness={0.2}
                      transparent
                      opacity={0.82}
                    />
                  </RoundedBox>
                </mesh>
              </group>
            )}

            {id === 'usagi' && (
              <group position={[0, 0.09, 0]}>
                <mesh position={[0, 0.05, -0.01]} castShadow>
                  <sphereGeometry args={[0.12, 16, 16, 0, Math.PI * 2, 0, Math.PI / 1.7]} />
                  <meshStandardMaterial color="#facc15" roughness={0.6} />
                </mesh>
                <mesh position={[-0.1, -0.02, 0.05]} rotation={[0, 0, 0.1]} castShadow>
                  <capsuleGeometry args={[0.025, 0.12, 6, 8]} />
                  <meshStandardMaterial color="#facc15" roughness={0.6} />
                </mesh>
                <mesh position={[0.1, -0.02, 0.05]} rotation={[0, 0, -0.1]} castShadow>
                  <capsuleGeometry args={[0.025, 0.12, 6, 8]} />
                  <meshStandardMaterial color="#facc15" roughness={0.6} />
                </mesh>
                <group position={[0, 0.06, -0.12]} rotation={[-0.3, 0, 0]}>
                  <mesh castShadow>
                    <sphereGeometry args={[0.035, 8, 8]} />
                    <meshStandardMaterial color="#D98078" roughness={0.5} />
                  </mesh>
                  <mesh position={[0, -0.12, 0]} castShadow>
                    <capsuleGeometry args={[0.035, 0.18, 8, 10]} />
                    <meshStandardMaterial color="#facc15" roughness={0.6} />
                  </mesh>
                </group>
                <mesh position={[0, -0.01, 0.1]}>
                  <RoundedBox radius={0.01} smoothness={2} args={[0.18, 0.04, 0.02]}>
                    <meshStandardMaterial
                      color="#C49A6C"
                      roughness={0.3}
                      metalness={0.2}
                      transparent
                      opacity={0.85}
                    />
                  </RoundedBox>
                </mesh>
              </group>
            )}

            {id === 'bayzero' && (
              <group position={[0, 0.09, 0]}>
                <mesh position={[0, 0.05, -0.01]} castShadow>
                  <sphereGeometry args={[0.12, 16, 16, 0, Math.PI * 2, 0, Math.PI / 1.7]} />
                  <meshStandardMaterial color="#94a3b8" roughness={0.5} />
                </mesh>
                <mesh position={[0.02, 0.07, 0.06]} rotation={[0.2, 0.1, 0]} castShadow>
                  <capsuleGeometry args={[0.036, 0.11, 8, 10]} />
                  <meshStandardMaterial color="#64748b" roughness={0.5} />
                </mesh>
                <mesh position={[0.04, -0.01, 0.1]}>
                  <RoundedBox radius={0.008} smoothness={2} args={[0.07, 0.04, 0.02]}>
                    <meshStandardMaterial
                      color="#5A5A5A"
                      roughness={0.3}
                      metalness={0.4}
                      transparent
                      opacity={0.85}
                    />
                  </RoundedBox>
                </mesh>
              </group>
            )}

            {id === 'clara' && (
              <group position={[0, 0.09, 0]}>
                <mesh position={[0, 0.05, -0.01]} castShadow>
                  <sphereGeometry args={[0.12, 16, 16, 0, Math.PI * 2, 0, Math.PI / 1.7]} />
                  <meshStandardMaterial color="#6B4226" roughness={0.65} />
                </mesh>
                <mesh position={[-0.08, -0.01, 0.04]} rotation={[0, 0, 0.15]} castShadow>
                  <capsuleGeometry args={[0.03, 0.14, 6, 8]} />
                  <meshStandardMaterial color="#6B4226" roughness={0.65} />
                </mesh>
                <mesh position={[0.08, -0.01, 0.04]} rotation={[0, 0, -0.15]} castShadow>
                  <capsuleGeometry args={[0.03, 0.14, 6, 8]} />
                  <meshStandardMaterial color="#6B4226" roughness={0.65} />
                </mesh>
              </group>
            )}
          </group>

          {/* 4. LENGAN KIRI LENGKAP (Shoulder -> Upper Arm -> Elbow -> Forearm -> Hand) */}
          <group ref={leftShoulderRef} position={[-0.22, 0.26, 0]}>
            {/* Lengan Atas (Capsule Geometry - Zero Sharp Edges) */}
            <mesh position={[0, -0.13, 0]} castShadow>
              <capsuleGeometry args={[0.046, 0.18, 8, 12]} />
              <meshStandardMaterial
                color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
                roughness={0.75}
              />
            </mesh>

            {/* Sendi Siku Kiri Smooth Sphere */}
            <group ref={leftElbowRef} position={[0, -0.26, 0]}>
              <mesh castShadow>
                <sphereGeometry args={[0.042, 10, 10]} />
                <meshStandardMaterial
                  color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
                  roughness={0.75}
                />
              </mesh>

              {/* Lengan Bawah (Forearm) */}
              <mesh position={[0, -0.11, 0]} castShadow>
                <capsuleGeometry args={[0.040, 0.16, 8, 12]} />
                <meshStandardMaterial
                  color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
                  roughness={0.75}
                />
              </mesh>

              {/* Telapak Tangan Kiri Stylized Humanoid */}
              <group position={[0, -0.23, 0]}>
                <mesh castShadow>
                  <capsuleGeometry args={[0.032, 0.04, 8, 10]} />
                  <meshStandardMaterial
                    color={id === 'usagi' ? '#E8B8A0' : id === 'clara' ? '#ECC5B0' : '#D4A57A'}
                    roughness={0.6}
                  />
                </mesh>
                <mesh position={[-0.02, 0.01, 0.01]} rotation={[0.3, 0, -0.4]} castShadow>
                  <capsuleGeometry args={[0.012, 0.024, 6, 8]} />
                  <meshStandardMaterial
                    color={id === 'usagi' ? '#E8B8A0' : id === 'clara' ? '#ECC5B0' : '#D4A57A'}
                    roughness={0.6}
                  />
                </mesh>
              </group>

              {/* Clipboard saat Bay-Zero Inspeksi */}
              {id === 'bayzero' && action === 'inspecting_sop' && (
                <mesh position={[0, -0.28, 0.12]} rotation={[0.4, 0, 0]}>
                  <RoundedBox radius={0.01} smoothness={2} args={[0.18, 0.26, 0.02]}>
                    <meshStandardMaterial
                      color="#E8E4DA"
                      roughness={0.6}
                      metalness={0.0}
                    />
                  </RoundedBox>
                </mesh>
              )}
            </group>
          </group>

          {/* 5. LENGAN KANAN LENGKAP (Shoulder -> Upper Arm -> Elbow -> Forearm -> Hand) */}
          <group ref={rightShoulderRef} position={[0.22, 0.26, 0]}>
            {/* Lengan Atas (Capsule Geometry) */}
            <mesh position={[0, -0.13, 0]} castShadow>
              <capsuleGeometry args={[0.046, 0.18, 8, 12]} />
              <meshStandardMaterial
                color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
                roughness={0.75}
              />
            </mesh>

            {/* Sendi Siku Kanan Smooth Sphere */}
            <group ref={rightElbowRef} position={[0, -0.26, 0]}>
              <mesh castShadow>
                <sphereGeometry args={[0.042, 10, 10]} />
                <meshStandardMaterial
                  color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
                  roughness={0.75}
                />
              </mesh>

              {/* Lengan Bawah (Forearm) */}
              <mesh position={[0, -0.11, 0]} castShadow>
                <capsuleGeometry args={[0.040, 0.16, 8, 12]} />
                <meshStandardMaterial
                  color={id === 'stark' ? '#363B44' : id === 'usagi' ? '#FAF6F0' : id === 'clara' ? '#C26D53' : '#646F7E'}
                  roughness={0.75}
                />
              </mesh>

              {/* Telapak Tangan Kanan Stylized Humanoid */}
              <group position={[0, -0.23, 0]}>
                <mesh castShadow>
                  <capsuleGeometry args={[0.032, 0.04, 8, 10]} />
                  <meshStandardMaterial
                    color={id === 'usagi' ? '#E8B8A0' : id === 'clara' ? '#ECC5B0' : '#D4A57A'}
                    roughness={0.6}
                  />
                </mesh>
                <mesh position={[0.02, 0.01, 0.01]} rotation={[0.3, 0, 0.4]} castShadow>
                  <capsuleGeometry args={[0.012, 0.024, 6, 8]} />
                  <meshStandardMaterial
                    color={id === 'usagi' ? '#E8B8A0' : id === 'clara' ? '#ECC5B0' : '#D4A57A'}
                    roughness={0.6}
                  />
                </mesh>
              </group>

              {/* Props Tangan Kanan: Cangkir Kopi di IDLE & Coffee Corner */}
              {(action === 'idle_coffee' || action === 'visiting_coffee' || holdingCoffeeMug) && (
                <group position={[0, -0.3, 0.06]} rotation={[-0.2, 0, 0]}>
                  <mesh castShadow>
                    <cylinderGeometry args={[0.035, 0.03, 0.07, 10]} />
                    <meshStandardMaterial color="#D4C5A9" roughness={0.3} />
                  </mesh>
                </group>
              )}

              {/* Props Tangan Kanan: Stylus Pen saat Menggambar Cover */}
              {action === 'drawing_canvas' && (
                <mesh position={[0, -0.3, 0.06]} rotation={[0.7, 0, 0]}>
                  <cylinderGeometry args={[0.008, 0.004, 0.16, 8]} />
                  <meshStandardMaterial color="#4A4A4A" roughness={0.4} />
                </mesh>
              )}
            </group>
          </group>
        </group>

        {/* 6. KAKI KIRI LENGKAP (Hip -> Thigh -> Knee -> Shin -> Shoe) */}
        <group ref={leftHipRef} position={[-0.1, -0.04, 0]}>
          {/* Paha Kiri (Capsule) */}
          <mesh position={[0, -0.19, 0]} castShadow>
            <capsuleGeometry args={[0.055, 0.28, 8, 12]} />
            <meshStandardMaterial
              color={id === 'stark' ? '#262930' : id === 'usagi' ? '#324254' : id === 'clara' ? '#2C3539' : '#2E333D'}
              roughness={0.7}
            />
          </mesh>

          {/* Sendi Lutut Kiri Smooth Sphere */}
          <group ref={leftKneeRef} position={[0, -0.4, 0]}>
            <mesh castShadow>
              <sphereGeometry args={[0.05, 10, 10]} />
              <meshStandardMaterial
                color={id === 'stark' ? '#262930' : id === 'usagi' ? '#324254' : id === 'clara' ? '#2C3539' : '#2E333D'}
                roughness={0.7}
              />
            </mesh>

            {/* Betis Kiri (Shin & Calf Capsule) */}
            <mesh position={[0, -0.17, 0]} castShadow>
              <capsuleGeometry args={[0.046, 0.26, 8, 12]} />
              <meshStandardMaterial
                color={id === 'stark' ? '#262930' : id === 'usagi' ? '#324254' : id === 'clara' ? '#2C3539' : '#2E333D'}
                roughness={0.7}
              />
            </mesh>

            {/* Sepatu Modern Ergonomis Kiri (Rounded Sole + Rounded Upper) */}
            <group position={[0, -0.36, 0.05]}>
              <RoundedBox radius={0.018} smoothness={3} args={[0.082, 0.028, 0.19]} position={[0, -0.015, 0]} castShadow>
                <meshStandardMaterial
                  color={id === 'usagi' ? '#FFFFFF' : '#22252A'}
                  roughness={0.6}
                />
              </RoundedBox>
              <mesh position={[0, 0.012, 0.01]} rotation={[0.2, 0, 0]} castShadow>
                <capsuleGeometry args={[0.038, 0.11, 8, 12]} />
                <meshStandardMaterial
                  color={id === 'usagi' ? '#FAF6F0' : id === 'stark' ? '#1A1D22' : id === 'clara' ? '#3E2723' : '#2C2620'}
                  roughness={0.5}
                />
              </mesh>
            </group>
          </group>
        </group>

        {/* 7. KAKI KANAN LENGKAP (Hip -> Thigh -> Knee -> Shin -> Shoe) */}
        <group ref={rightHipRef} position={[0.1, -0.04, 0]}>
          {/* Paha Kanan (Capsule) */}
          <mesh position={[0, -0.19, 0]} castShadow>
            <capsuleGeometry args={[0.055, 0.28, 8, 12]} />
            <meshStandardMaterial
              color={id === 'stark' ? '#262930' : id === 'usagi' ? '#324254' : id === 'clara' ? '#2C3539' : '#2E333D'}
              roughness={0.7}
            />
          </mesh>

          {/* Sendi Lutut Kanan Smooth Sphere */}
          <group ref={rightKneeRef} position={[0, -0.4, 0]}>
            <mesh castShadow>
              <sphereGeometry args={[0.05, 10, 10]} />
              <meshStandardMaterial
                color={id === 'stark' ? '#262930' : id === 'usagi' ? '#324254' : id === 'clara' ? '#2C3539' : '#2E333D'}
                roughness={0.7}
              />
            </mesh>

            {/* Betis Kanan (Shin & Calf Capsule) */}
            <mesh position={[0, -0.17, 0]} castShadow>
              <capsuleGeometry args={[0.046, 0.26, 8, 12]} />
              <meshStandardMaterial
                color={id === 'stark' ? '#262930' : id === 'usagi' ? '#324254' : id === 'clara' ? '#2C3539' : '#2E333D'}
                roughness={0.7}
              />
            </mesh>

            {/* Sepatu Modern Ergonomis Kanan (Rounded Sole + Rounded Upper) */}
            <group position={[0, -0.36, 0.05]}>
              <RoundedBox radius={0.018} smoothness={3} args={[0.082, 0.028, 0.19]} position={[0, -0.015, 0]} castShadow>
                <meshStandardMaterial
                  color={id === 'usagi' ? '#FFFFFF' : '#22252A'}
                  roughness={0.6}
                />
              </RoundedBox>
              <mesh position={[0, 0.012, 0.01]} rotation={[0.2, 0, 0]} castShadow>
                <capsuleGeometry args={[0.038, 0.11, 8, 12]} />
                <meshStandardMaterial
                  color={id === 'usagi' ? '#FAF6F0' : id === 'stark' ? '#1A1D22' : id === 'clara' ? '#3E2723' : '#2C2620'}
                  roughness={0.5}
                />
              </mesh>
            </group>
          </group>
        </group>
      </group>
    </group>
  );
}

/**
 * Backward compatibility alias
 */
export const ProceduralChibiCharacter = StylizedHumanoidCharacter;

export function WorkerCharacter({
  currentNode,
  message,
}: {
  currentNode: string;
  message: string;
}) {
  const humanStatus = getHumanStatus(currentNode);
  return (
    <StylizedHumanoidCharacter
      id="stark"
      currentNode={currentNode}
      action={humanStatus.action}
      targetPos={[-3.2, 0, 1.65]}
      targetRotY={Math.PI}
      message={message}
      isActive={true}
      isSeated={true}
    />
  );
}
