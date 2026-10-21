import React, { useMemo } from 'react';
import { useTexture, RoundedBox } from '@react-three/drei';
import * as THREE from 'three';

interface RoomEnvironmentProps {
  currentNode: string;
  activeWorkerPos?: [number, number, number];
}

// Scandinavian Color Constants matching Target Reference
const OAK_COLOR = '#C89D66';          // Warm honey oak
const OAK_DARK = '#9E7444';           // Deep oak
const WALL_OFFWHITE = '#F4F1EA';      // Soft off-white
const WALL_WARM_GREY = '#E8E4DA';     // Warm grey plaster
const BASEBOARD_COLOR = '#D8D4CA';    // Baseboard trim
const STEEL_BLACK = '#262A30';        // Matte black steel mullions & track lights
const CAPPING_CHARCOAL = '#2B3038';   // Low cutaway wall capping
const DAYLIGHT_COLOR = '#FFF6E5';     // Warm sun daylight
const SKY_COLOR = '#C2DCF0';          // Fresh daylight sky
const MAT_GREY = '#383D45';           // Entrance doormat

/**
 * Large Nature Landscape Artwork (Back Wall Focal Point)
 * Replaces the tree spheres with a majestic, high-resolution landscape painting.
 */
function BackWallPainting({
  position = [0, 1.85, -5.68],
  width = 4.6,
  height = 1.8,
  texture,
}: {
  position?: [number, number, number];
  width?: number;
  height?: number;
  texture: THREE.Texture;
}) {
  const frameT = 0.05;

  return (
    <group position={position}>
      {/* High-Resolution Landscape Canvas Painting */}
      <mesh position={[0, 0, 0.015]} receiveShadow>
        <planeGeometry args={[width, height]} />
        <meshStandardMaterial
          map={texture}
          roughness={0.45}
          metalness={0.0}
        />
      </mesh>

      {/* Gallery Accent Lighting for the Landscape Artwork */}
      <pointLight position={[-1.2, height / 2 + 0.2, 0.6]} intensity={0.65} color="#FFF2DB" distance={3.5} decay={2} />
      <pointLight position={[1.2, height / 2 + 0.2, 0.6]} intensity={0.65} color="#FFF2DB" distance={3.5} decay={2} />

      {/* Gallery Outer Perimeter Frame (Matte Black Steel) */}
      <mesh position={[0, height / 2, 0.02]} castShadow>
        <boxGeometry args={[width + frameT * 2, frameT, 0.05]} />
        <meshStandardMaterial color={STEEL_BLACK} roughness={0.4} metalness={0.8} />
      </mesh>
      <mesh position={[0, -height / 2, 0.02]} castShadow>
        <boxGeometry args={[width + frameT * 2, frameT, 0.05]} />
        <meshStandardMaterial color={STEEL_BLACK} roughness={0.4} metalness={0.8} />
      </mesh>
      <mesh position={[-width / 2, 0, 0.02]} castShadow>
        <boxGeometry args={[frameT, height, 0.05]} />
        <meshStandardMaterial color={STEEL_BLACK} roughness={0.4} metalness={0.8} />
      </mesh>
      <mesh position={[width / 2, 0, 0.02]} castShadow>
        <boxGeometry args={[frameT, height, 0.05]} />
        <meshStandardMaterial color={STEEL_BLACK} roughness={0.4} metalness={0.8} />
      </mesh>

      {/* Frame Lower Accent Sill (Solid Natural Oak) */}
      <mesh position={[0, -height / 2 - 0.03, 0.04]} castShadow receiveShadow>
        <boxGeometry args={[width + 0.15, 0.04, 0.12]} />
        <meshStandardMaterial color={OAK_COLOR} roughness={0.6} />
      </mesh>
    </group>
  );
}

/**
 * Long Low Sideboard / Credenza underneath the Back Window (with RoundedBox)
 */
function WindowSideboard({
  position = [0, 0, -5.4],
  width = 4.4,
  height = 0.62,
  depth = 0.45,
}: {
  position?: [number, number, number];
  width?: number;
  height?: number;
  depth?: number;
}) {
  return (
    <group position={position}>
      {/* Oak Credenza Main Body with Rounded Bevel */}
      <RoundedBox radius={0.025} smoothness={4} args={[width, height, depth]} position={[0, height / 2, 0]} castShadow receiveShadow>
        <meshStandardMaterial color={OAK_COLOR} roughness={0.58} />
      </RoundedBox>

      {/* Credenza Top Surface */}
      <RoundedBox radius={0.015} smoothness={3} args={[width + 0.04, 0.03, depth + 0.04]} position={[0, height + 0.015, 0]} castShadow receiveShadow>
        <meshStandardMaterial color={OAK_COLOR} roughness={0.52} />
      </RoundedBox>

      {/* Front Panel Divisions / Cubby lines */}
      {[-1.1, 0, 1.1].map((x, i) => (
        <mesh key={`div-${i}`} position={[x, height / 2, depth / 2 + 0.002]}>
          <boxGeometry args={[0.02, height - 0.06, 0.005]} />
          <meshStandardMaterial color={OAK_DARK} roughness={0.7} />
        </mesh>
      ))}

      {/* Props on Credenza Top */}
      {/* 1. Warm Glowing Orb Globe Lamp */}
      <group position={[1.4, height + 0.03, 0]}>
        <mesh position={[0, 0.02, 0]} castShadow>
          <cylinderGeometry args={[0.07, 0.09, 0.04, 16]} />
          <meshStandardMaterial color={OAK_COLOR} roughness={0.5} />
        </mesh>
        <mesh position={[0, 0.16, 0]}>
          <sphereGeometry args={[0.12, 24, 24]} />
          <meshStandardMaterial
            color="#FFF4D4"
            emissive="#FFE094"
            emissiveIntensity={1.4}
            roughness={0.2}
          />
        </mesh>
        <pointLight position={[0, 0.22, 0]} intensity={0.65} color="#FFE6BD" distance={2.4} decay={2} />
      </group>

      {/* 2. Ceramic Vase with Decorative Twigs */}
      <group position={[-1.4, height + 0.03, 0]}>
        <mesh position={[0, 0.1, 0]} castShadow>
          <cylinderGeometry args={[0.06, 0.08, 0.2, 16]} />
          <meshStandardMaterial color="#E8E2D5" roughness={0.4} />
        </mesh>
        <mesh position={[0, 0.25, 0]} rotation={[0.1, 0.2, 0]}>
          <cylinderGeometry args={[0.006, 0.006, 0.22, 6]} />
          <meshStandardMaterial color={OAK_DARK} />
        </mesh>
      </group>

      {/* 3. Horizontal Stacks of Art & Architecture Books */}
      <group position={[-0.4, height + 0.03, 0.05]}>
        <mesh position={[0, 0.015, 0]} castShadow>
          <boxGeometry args={[0.26, 0.03, 0.32]} />
          <meshStandardMaterial color="#30353E" roughness={0.8} />
        </mesh>
        <mesh position={[0.02, 0.04, 0]} castShadow>
          <boxGeometry args={[0.24, 0.025, 0.3]} />
          <meshStandardMaterial color="#D98078" roughness={0.8} />
        </mesh>
        <mesh position={[-0.01, 0.06, 0]} castShadow>
          <boxGeometry args={[0.22, 0.02, 0.28]} />
          <meshStandardMaterial color="#FAF9F5" roughness={0.8} />
        </mesh>
      </group>
    </group>
  );
}

/**
 * Vertical Acoustic Oak Wood Slats Wall Panel (Behind Lounge Area)
 * Fixed: Backing panel has physical depth and is offset forward to prevent any Z-fighting with the back wall.
 * Slats have realistic architectural depth with clean spacing and shadow acne eliminated.
 */
function AcousticWoodSlatsWall({
  position = [4.6, 1.6, -5.68],
  width = 2.8,
  height = 3.2,
  slatCount = 32,
}: {
  position?: [number, number, number];
  width?: number;
  height?: number;
  slatCount?: number;
}) {
  const slatW = 0.048; // 48mm warm oak slat
  const slatD = 0.012; // 12mm realistic architectural slat depth
  const slatH = height - 0.12; // Sits neatly above the 12cm oak baseboard

  return (
    <group position={position}>
      {/* 1. Solid Dark Acoustic Felt Backing Panel (Offset forward to eliminate any wall Z-fighting) */}
      <mesh position={[0, 0.06, 0.006]}>
        <boxGeometry args={[width, slatH, 0.01]} />
        <meshStandardMaterial color="#1B1E24" roughness={0.96} />
      </mesh>

      {/* 2. Individual Vertical Oak Slats with smooth spacing and no shadow acne */}
      {Array.from({ length: slatCount }).map((_, i) => {
        const x = -width / 2 + (i + 0.5) * (width / slatCount);
        return (
          <mesh
            key={`slat-${i}`}
            position={[x, 0.06, 0.011 + slatD / 2]}
            castShadow={false}
            receiveShadow
          >
            <boxGeometry args={[slatW, slatH, slatD]} />
            <meshStandardMaterial
              color={OAK_COLOR}
              roughness={0.52}
              metalness={0.0}
            />
          </mesh>
        );
      })}

      {/* 3. Top Architectural Oak Trim Capping */}
      <mesh position={[0, height / 2, 0.016]}>
        <boxGeometry args={[width + 0.02, 0.03, 0.028]} />
        <meshStandardMaterial color={OAK_DARK} roughness={0.5} />
      </mesh>
    </group>
  );
}

/**
 * Foreground Entrance Planter Pedestal with Sculpted Sphere Boxwood
 */
function EntrancePlanterPedestal({ position = [0, 0, 0] }: { position?: [number, number, number] }) {
  return (
    <group position={position}>
      {/* Concrete pedestal plinth with soft rounded bevel */}
      <RoundedBox radius={0.02} smoothness={3} args={[0.55, 0.72, 0.55]} position={[0, 0.36, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#4A505A" roughness={0.82} />
      </RoundedBox>
      <mesh position={[0, 0.725, 0]}>
        <boxGeometry args={[0.57, 0.03, 0.57]} />
        <meshStandardMaterial color={CAPPING_CHARCOAL} roughness={0.6} />
      </mesh>

      {/* Dense Sculpted Sphere Boxwood Bush */}
      <mesh position={[0, 0.98, 0]} castShadow>
        <sphereGeometry args={[0.26, 16, 16]} />
        <meshStandardMaterial color="#2E5C32" roughness={0.85} />
      </mesh>

      {/* Soft Ground Inground Uplight */}
      <pointLight position={[0, 0.76, 0.2]} intensity={0.4} color="#FFF2DB" distance={1.2} decay={2} />
    </group>
  );
}

/**
 * Ceiling Perimeter Spotlight Track Rails (ArchViz High-End Studio Lighting)
 */
function CeilingPerimeterSpotTracks() {
  const railH = 3.12;
  const spotPositionsBack = [-4.6, -3.0, -1.4, 0.2, 1.8, 3.4];
  const spotPositionsLeft = [-4.0, -2.2, -0.4, 1.4, 3.2];

  return (
    <group>
      {/* Back Wall Rail (Along Z = -5.45) */}
      <mesh position={[-0.6, railH, -5.45]} castShadow>
        <boxGeometry args={[9.5, 0.035, 0.04]} />
        <meshStandardMaterial color={STEEL_BLACK} roughness={0.3} metalness={0.8} />
      </mesh>
      {spotPositionsBack.map((x, i) => (
        <group key={`spot-b-${i}`} position={[x, railH - 0.05, -5.45]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.035, 0.04, 0.08, 12]} />
            <meshStandardMaterial color={STEEL_BLACK} roughness={0.3} metalness={0.7} />
          </mesh>
          <mesh position={[0, -0.041, 0]}>
            <circleGeometry args={[0.028, 10]} />
            <meshStandardMaterial color="#FFE8B5" emissive="#FFE8B5" emissiveIntensity={1.2} />
          </mesh>
        </group>
      ))}

      {/* Left Wall Rail (Along X = -6.45) */}
      <mesh position={[-6.45, railH, -0.4]} rotation={[0, Math.PI / 2, 0]} castShadow>
        <boxGeometry args={[9.0, 0.035, 0.04]} />
        <meshStandardMaterial color={STEEL_BLACK} roughness={0.3} metalness={0.8} />
      </mesh>
      {spotPositionsLeft.map((z, i) => (
        <group key={`spot-l-${i}`} position={[-6.45, railH - 0.05, z]}>
          <mesh castShadow>
            <cylinderGeometry args={[0.035, 0.04, 0.08, 12]} />
            <meshStandardMaterial color={STEEL_BLACK} roughness={0.3} metalness={0.7} />
          </mesh>
          <mesh position={[0, -0.041, 0]}>
            <circleGeometry args={[0.028, 10]} />
            <meshStandardMaterial color="#FFE8B5" emissive="#FFE8B5" emissiveIntensity={1.2} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

export function RoomEnvironment({ currentNode, activeWorkerPos }: RoomEnvironmentProps) {
  const W = 13.5;    // Room width (X: -6.75 to +6.75)
  const D = 11.5;    // Room depth (Z: -5.75 to +5.75)
  const H = 3.2;     // Full wall height
  const HW = W / 2;  // 6.75
  const HD = D / 2;  // 5.75
  const CUTAWAY_H = 0.45; // Height of low cutaway walls

  // PBR Textures for Light Honey Oak Floor and Landscape Artwork
  const [diffMap, norMap, roughMap, aoMap, landscapeMap] = useTexture([
    '/assets/textures/floor/wooden_floor_01_diff_2k.jpg',
    '/assets/textures/floor/wooden_floor_01_nor_gl_2k.jpg',
    '/assets/textures/floor/wooden_floor_01_rough_2k.jpg',
    '/assets/textures/floor/wooden_floor_01_ao_2k.jpg',
    '/assets/textures/landscape_painting.jpg',
  ]);

  useMemo(() => {
    [diffMap, norMap, roughMap, aoMap].forEach((tex) => {
      tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
      tex.repeat.set(7, 6);
    });
  }, [diffMap, norMap, roughMap, aoMap]);

  // Dedicated High-Resolution Canvas Texture for Bauhaus Abstract Art Print
  // Completely eliminates coplanar Z-fighting and ensures razor-sharp 2K circle anti-aliasing
  const abstractArtMap = useMemo(() => {
    if (typeof document === 'undefined') return null;
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 1400;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      // 1. Off-white fine gallery paper background
      ctx.fillStyle = '#FAF8F3';
      ctx.fillRect(0, 0, 1024, 1400);

      // 2. White clean mat / passe-partout margin
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(56, 56, 1024 - 112, 1400 - 112);

      // 3. Inner creamy print area
      ctx.fillStyle = '#F5F2EB';
      ctx.fillRect(72, 72, 1024 - 144, 1400 - 144);

      // 4. Smooth Terracotta / Dusty-Coral Circle (Perfect 2K Antialiasing, No Polygonal Facets)
      ctx.fillStyle = '#D98078';
      ctx.beginPath();
      ctx.arc(512, 530, 260, 0, Math.PI * 2);
      ctx.fill();

      // 5. Overlapping Charcoal Modern Base Block
      ctx.fillStyle = '#2D333B';
      ctx.fillRect(332, 750, 360, 230);

      // 6. Minimalist Scandinavian Ochre Accent Line
      ctx.fillStyle = '#C89D66';
      ctx.fillRect(412, 1030, 200, 14);

      // 7. Subtle Typography detail at bottom
      ctx.fillStyle = '#A09C94';
      ctx.font = '600 18px sans-serif';
      ctx.fillText('NO. 04 — SCANDINAVIAN COLLECTION', 110, 1260);
    }
    const tex = new THREE.CanvasTexture(canvas);
    tex.generateMipmaps = true;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.anisotropy = 8;
    return tex;
  }, []);

  return (
    <group>
      {/* =========================================================================
          1. LIGHTING SETUP — Matching Reference Image
         ========================================================================= */}
      {/* Main Daylight Sun streaming in through Back Window */}
      <directionalLight
        position={[-1.0, 9.2, -11.0]}
        target-position={[0, 0.4, 0.5]}
        intensity={1.5}
        color={DAYLIGHT_COLOR}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-left={-8}
        shadow-camera-right={8}
        shadow-camera-top={8}
        shadow-camera-bottom={-8}
        shadow-camera-near={1.0}
        shadow-camera-far={28}
        shadow-bias={-0.0003}
        shadow-normalBias={0.02}
      />

      {/* Front-Right Elevated Soft Fill Light */}
      <directionalLight
        position={[8.5, 10.0, 8.5]}
        intensity={0.45}
        color="#EAF0F8"
      />

      {/* Warm Interior Ambient Fill */}
      <ambientLight intensity={0.5} color="#F6F2EA" />

      {/* Hemisphere Light (Soft Sky Blue to Warm Oak Floor bounce) */}
      <hemisphereLight
        color="#E8EFF8"
        groundColor="#C89D66"
        intensity={0.4}
      />

      {/* =========================================================================
          2. SEAMLESS PBR OAK PARQUET FLOOR — ZERO Z-FIGHTING / PBR REALISM
         ========================================================================= */}
      <mesh position={[0, -0.02, 0]} receiveShadow>
        <boxGeometry args={[W, 0.04, D]} />
        <meshStandardMaterial
          map={diffMap}
          normalMap={norMap}
          normalScale={new THREE.Vector2(0.6, 0.6)}
          roughnessMap={roughMap}
          aoMap={aoMap}
          aoMapIntensity={1.0}
          color="#FFFFFF"
          roughness={0.62}
          metalness={0.0}
        />
      </mesh>

      {/* Architectural Foundation Plinth (Strictly below the floor at y <= -0.04) */}
      <mesh position={[0, -0.09, 0]} receiveShadow>
        <boxGeometry args={[W + 0.4, 0.1, D + 0.4]} />
        <meshStandardMaterial color="#1E222A" roughness={0.7} />
      </mesh>

      {/* Embedded Entrance Welcome Mat in Foreground */}
      <mesh position={[0, 0.002, HD - 0.75]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[2.2, 1.2]} />
        <meshStandardMaterial color={MAT_GREY} roughness={0.92} />
      </mesh>

      {/* =========================================================================
          3. FAR BACK WALL (Z = -HD = -5.75) — Solid Gallery Wall with Landscape Painting
         ========================================================================= */}
      {/* Full Solid Back Wall */}
      <mesh position={[0, H / 2, -HD]} receiveShadow>
        <boxGeometry args={[W, H, 0.2]} />
        <meshStandardMaterial color={WALL_OFFWHITE} roughness={0.88} />
      </mesh>

      {/* Back Wall Oak Baseboard */}
      <mesh position={[0, 0.06, -HD + 0.11]}>
        <boxGeometry args={[W, 0.12, 0.03]} />
        <meshStandardMaterial color={BASEBOARD_COLOR} roughness={0.6} />
      </mesh>

      {/* Large Framed Nature Landscape Artwork (Replaces Tree Spheres) */}
      <BackWallPainting position={[0, 1.85, -HD + 0.11]} width={4.6} height={1.8} texture={landscapeMap} />

      {/* Long Oak Sideboard underneath the Painting */}
      <WindowSideboard position={[0, 0, -HD + 0.35]} width={4.4} height={0.62} depth={0.45} />

      {/* Acoustic Wood Slats Wall on Upper Right (Behind Lounge) */}
      <AcousticWoodSlatsWall position={[4.6, H / 2, -HD + 0.11]} width={2.8} height={H} slatCount={32} />

      {/* Framed Abstract Modern Art Print on Left of Painting (Smooth 2K Canvas Texture, Zero Z-Fighting) */}
      <group position={[-3.8, 2.05, -HD + 0.12]}>
        <RoundedBox radius={0.02} smoothness={3} args={[0.85, 1.05, 0.03]} castShadow>
          <meshStandardMaterial color={OAK_COLOR} roughness={0.5} />
        </RoundedBox>
        <mesh position={[0, 0, 0.017]}>
          <planeGeometry args={[0.75, 0.95]} />
          {abstractArtMap ? (
            <meshStandardMaterial map={abstractArtMap} roughness={0.55} />
          ) : (
            <meshStandardMaterial color="#F8F6F0" roughness={0.6} />
          )}
        </mesh>
      </group>

      {/* =========================================================================
          4. LEFT FULL WALL (X = -HW = -6.75)
         ========================================================================= */}
      {/* Full Left Wall */}
      <mesh position={[-HW, H / 2, 0]} receiveShadow>
        <boxGeometry args={[0.2, H, D]} />
        <meshStandardMaterial color={WALL_OFFWHITE} roughness={0.88} />
      </mesh>

      {/* Left Wall Baseboard */}
      <mesh position={[-HW + 0.11, 0.06, 0]}>
        <boxGeometry args={[0.03, 0.12, D]} />
        <meshStandardMaterial color={BASEBOARD_COLOR} roughness={0.6} />
      </mesh>

      {/* Framed Wall Art on Left Wall */}
      <group position={[-HW + 0.12, 1.95, 0.8]} rotation={[0, Math.PI / 2, 0]}>
        <RoundedBox radius={0.02} smoothness={3} args={[0.7, 0.9, 0.03]} castShadow>
          <meshStandardMaterial color={OAK_COLOR} roughness={0.5} />
        </RoundedBox>
        <mesh position={[0, 0, 0.016]}>
          <planeGeometry args={[0.6, 0.8]} />
          <meshStandardMaterial color="#F8F6F0" roughness={0.6} />
        </mesh>
        <mesh position={[0, 0, 0.018]}>
          <planeGeometry args={[0.45, 0.55]} />
          <meshStandardMaterial color="#8DA895" roughness={0.7} />
        </mesh>
      </group>

      {/* =========================================================================
          5. RIGHT FULL WALL (X = +HW = +6.75) & INDUSTRIAL GLASS DOOR
         ========================================================================= */}
      {/* Full Solid Right Wall — Completely solid from back to front corner, eliminating all missing wall bugs */}
      <mesh position={[HW, H / 2, 0]} receiveShadow>
        <boxGeometry args={[0.2, H, D]} />
        <meshStandardMaterial color={WALL_OFFWHITE} roughness={0.88} />
      </mesh>

      {/* Right Wall Baseboard */}
      <mesh position={[HW - 0.11, 0.06, 0]}>
        <boxGeometry args={[0.03, 0.12, D]} />
        <meshStandardMaterial color={BASEBOARD_COLOR} roughness={0.6} />
      </mesh>

      {/* Industrial Black Metal Glass Partition Door (Right Wall) */}
      <group position={[HW - 0.02, 1.45, -3.2]} rotation={[0, -Math.PI / 2, 0]}>
        {/* Steel Outer Door Frame */}
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[1.5, 2.7, 0.06]} />
          <meshStandardMaterial color={STEEL_BLACK} roughness={0.4} metalness={0.8} />
        </mesh>
        {/* Translucent Frosted Glass */}
        <mesh position={[0, 0, 0]}>
          <planeGeometry args={[1.38, 2.58]} />
          <meshStandardMaterial color="#EBF4F6" transparent opacity={0.4} roughness={0.1} />
        </mesh>
        {/* Steel Muntin Grid */}
        {[-0.6, 0, 0.6].map((y, i) => (
          <mesh key={`transom-${i}`} position={[0, y, 0.02]}>
            <boxGeometry args={[1.38, 0.03, 0.02]} />
            <meshStandardMaterial color={STEEL_BLACK} roughness={0.4} metalness={0.8} />
          </mesh>
        ))}
      </group>

      {/* Framed Wall Art on Right Wall */}
      <group position={[HW - 0.12, 1.95, 1.8]} rotation={[0, -Math.PI / 2, 0]}>
        <RoundedBox radius={0.02} smoothness={3} args={[0.65, 0.85, 0.03]} castShadow>
          <meshStandardMaterial color={OAK_COLOR} roughness={0.5} />
        </RoundedBox>
        <mesh position={[0, 0, 0.016]}>
          <planeGeometry args={[0.55, 0.75]} />
          <meshStandardMaterial color="#F8F6F0" roughness={0.6} />
        </mesh>
        <mesh position={[0, 0, 0.018]}>
          <planeGeometry args={[0.4, 0.55]} />
          <meshStandardMaterial color="#354A60" roughness={0.7} />
        </mesh>
      </group>

      {/* =========================================================================
          6. ARCHITECTURAL CUTAWAY LOW WALLS & FOREGROUND THRESHOLD
         ========================================================================= */}
      {/* Front Left Cutaway Wall (Z = +HD = +5.75) */}
      <group position={[-3.8, 0, HD]}>
        <mesh position={[0, CUTAWAY_H / 2, 0]} receiveShadow>
          <boxGeometry args={[HW - 0.9, CUTAWAY_H, 0.2]} />
          <meshStandardMaterial color={WALL_OFFWHITE} roughness={0.88} />
        </mesh>
        {/* Charcoal Architectural Capping Ledge */}
        <mesh position={[0, CUTAWAY_H + 0.015, 0]} castShadow>
          <boxGeometry args={[HW - 0.85, 0.03, 0.24]} />
          <meshStandardMaterial color={CAPPING_CHARCOAL} roughness={0.6} />
        </mesh>
      </group>

      {/* Front Right Cutaway Wall (Z = +HD = +5.75) */}
      <group position={[3.8, 0, HD]}>
        <mesh position={[0, CUTAWAY_H / 2, 0]} receiveShadow>
          <boxGeometry args={[HW - 0.9, CUTAWAY_H, 0.2]} />
          <meshStandardMaterial color={WALL_OFFWHITE} roughness={0.88} />
        </mesh>
        <mesh position={[0, CUTAWAY_H + 0.015, 0]} castShadow>
          <boxGeometry args={[HW - 0.85, 0.03, 0.24]} />
          <meshStandardMaterial color={CAPPING_CHARCOAL} roughness={0.6} />
        </mesh>
      </group>

      {/* Foreground Entrance Planter Pedestals */}
      <EntrancePlanterPedestal position={[-1.4, 0, HD - 0.35]} />
      <EntrancePlanterPedestal position={[1.4, 0, HD - 0.35]} />

      {/* =========================================================================
          7. ARCHVIZ CEILING PERIMETER SPOTLIGHT TRACK RAILS
         ========================================================================= */}
      <CeilingPerimeterSpotTracks />
    </group>
  );
}
