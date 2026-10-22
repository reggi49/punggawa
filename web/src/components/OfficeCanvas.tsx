import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, SoftShadows, Environment } from '@react-three/drei';
import { EffectComposer, N8AO, Bloom, ToneMapping } from '@react-three/postprocessing';
import { ToneMappingMode } from 'postprocessing';
import { OfficeScene } from './OfficeScene';
import { CharacterVisualState } from '../simulation/useAmbientOffice';
import { WorkerId, ServicesHealthResponse } from '../types';

interface OfficeCanvasProps {
  currentNode: string;
  status?: string;
  message: string;
  details?: Record<string, any>;
  threadId?: string;
  connected?: boolean;
  isDegraded?: boolean;
  isMobile?: boolean;
  healthData?: ServicesHealthResponse | null;
  onCharacterStatesChange?: (states: Record<WorkerId, CharacterVisualState>) => void;
}

export function OfficeCanvas({
  currentNode,
  status = 'idle',
  message,
  details = {},
  threadId = '',
  connected = true,
  isDegraded = false,
  isMobile = false,
  healthData,
  onCharacterStatesChange,
}: OfficeCanvasProps) {
  return (
    <div
      className="canvas-container-root"
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        zIndex: 0,
        isolation: 'isolate',
      }}
    >
      <Canvas
        shadows={isMobile ? false : 'soft'}
        dpr={isMobile ? [1, 1.15] : [1, 2]}
        camera={{
          position: [0.8, 9.5, 13.5],
          fov: 36,
          near: 0.1,
          far: 100,
        }}
        gl={{
          antialias: !isMobile,
          powerPreference: isMobile ? 'low-power' : 'high-performance',
          toneMapping: 4, /* ACESFilmicToneMapping */
          toneMappingExposure: 1.05,
        }}
      >
        {/* ArchViz Realistic Soft Contact Shadows - Disabled on mobile to preserve battery & FPS */}
        {!isMobile && <SoftShadows size={35} samples={20} focus={0.5} />}

        {/* Warm off-white architectural background */}
        <color attach="background" args={['#2A2D34']} />
        {/* Subtle atmospheric fog for depth */}
        <fog attach="fog" args={['#2A2D34', 35, 75]} />

        {/* Realistic Poly Haven HDRI Environment reflections & soft bounce */}
        <Environment
          files="/assets/hdri/small-empty-room-3.hdr"
          background={false}
          environmentIntensity={isMobile ? 0.45 : 0.65}
        />

        <Suspense fallback={null}>
          <OfficeScene
            currentNode={currentNode}
            status={status}
            message={message}
            details={details}
            threadId={threadId}
            connected={connected}
            isDegraded={isDegraded}
            healthData={healthData}
            onCharacterStatesChange={onCharacterStatesChange}
          />
        </Suspense>

        {/* ArchViz Cinematic Post-Processing Pipeline: skipped on mobile to prevent GPU thermal throttling */}
        {!isMobile ? (
          <EffectComposer multisampling={4}>
            <N8AO
              aoRadius={0.8}
              intensity={2.5}
              distanceFalloff={0.5}
              quality="high"
            />
            <Bloom
              intensity={0.25}
              luminanceThreshold={1.1}
              mipmapBlur
            />
            <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
          </EffectComposer>
        ) : (
          <EffectComposer multisampling={0}>
            <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
          </EffectComposer>
        )}

        {/* Isometric-like orbit with comfortable tilt */}
        <OrbitControls
          makeDefault
          target={[0, 0.6, 0]}
          maxPolarAngle={Math.PI / 2.25}
          minPolarAngle={Math.PI / 10}
          minDistance={8}
          maxDistance={25}
          enableDamping
          dampingFactor={isMobile ? 0.12 : 0.07}
          rotateSpeed={isMobile ? 0.8 : 0.6}
          zoomSpeed={isMobile ? 0.9 : 0.8}
        />
      </Canvas>
    </div>
  );
}

export default OfficeCanvas;
