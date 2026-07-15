"use client";

/**
 * PolyhedronCanvas — Animated 3D icosahedron background using React Three Fiber.
 *
 * Renders a wireframe polyhedron with smooth auto-rotation and subtle
 * mouse-follow interactivity. Used as the landing page backdrop.
 */

import { useRef, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import * as THREE from "three";

function Ripples({ count = 2 }: { count?: number }) {
  const ripplesRef = useRef<THREE.Mesh[]>([]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    // Sync with the breathing animation: Math.sin(t * 3)
    // The sine wave period is (Math.PI * 2) / 3
    const period = (Math.PI * 2) / 3;
    const maxScale = 1.32;

    ripplesRef.current.forEach((mesh, index) => {
      if (!mesh) return;
      // Stagger the ripples
      const offset = (index * period) / count;
      const progress = ((t + offset) % period) / period;

      // Scale from 1.0 to maxScale
      const scale = 1.0 + progress * (maxScale - 1.0);
      mesh.scale.set(scale, scale, scale);

      // Opacity fades out as it expands
      const opacity = 0.5 * (1.0 - Math.pow(progress, 1.5));
      (mesh.material as THREE.MeshBasicMaterial).opacity = Math.max(0, opacity);
    });
  });

  return (
    <group>
      {Array.from({ length: count }).map((_, i) => (
        <mesh key={i} ref={(el) => { if (el) ripplesRef.current[i] = el; }}>
          <ringGeometry args={[3.25, 3.27, 64]} />
          <meshBasicMaterial color="#22C55E" transparent opacity={0} side={THREE.DoubleSide} />
        </mesh>
      ))}
    </group>
  );
}

function RotatingPolyhedron({ isMobile, mode }: { isMobile: boolean; mode: 'background' | 'mascot' }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const wireRef = useRef<THREE.LineSegments>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (meshRef.current) {
      meshRef.current.rotation.x = t * 0.08;
      meshRef.current.rotation.y = t * 0.12;

      if (mode === 'mascot') {
        const scale = 1 + Math.sin(t * 3) * 0.04;
        meshRef.current.scale.set(scale, scale, scale);
      }
    }
    if (wireRef.current) {
      wireRef.current.rotation.x = t * 0.08;
      wireRef.current.rotation.y = t * 0.12;

      if (mode === 'mascot') {
        const scale = 1 + Math.sin(t * 3) * 0.04;
        wireRef.current.scale.set(scale, scale, scale);
      }
    }
    if (ringRef.current && mode === 'mascot') {
      const scale = 1 + Math.sin(t * 3) * 0.04;
      ringRef.current.scale.set(scale, scale, scale);
    }
  });

  const radius = mode === 'mascot' ? 2.5 : (isMobile ? 2.0 : 3.3);
  const geometry = new THREE.IcosahedronGeometry(radius, mode === 'mascot' ? 0 : 1);
  const edges = new THREE.EdgesGeometry(geometry);

  return (
    <Float speed={mode === 'mascot' ? 2.5 : 1.5} rotationIntensity={mode === 'mascot' ? 0.8 : 0.3} floatIntensity={mode === 'mascot' ? 1.0 : 0.5}>
      <group>
        {mode === 'mascot' && (
          <>
            <mesh ref={ringRef}>
              <ringGeometry args={[3.25, 3.28, 64]} />
              <meshBasicMaterial color="#22C55E" transparent opacity={0.6} side={THREE.DoubleSide} />
            </mesh>
            <Ripples count={2} />
          </>
        )}
        {/* Solid faces with very low opacity */}
        <mesh ref={meshRef} geometry={geometry}>
          <meshBasicMaterial
            color="#22C55E"
            transparent
            opacity={mode === 'mascot' ? 0.05 : 0.03}
            side={THREE.DoubleSide}
          />
        </mesh>
        {/* Wireframe edges only */}
        <lineSegments ref={wireRef} geometry={edges}>
          <lineBasicMaterial color="#22C55E" transparent opacity={mode === 'mascot' ? 1.0 : 0.8} />
        </lineSegments>
      </group>
    </Float>
  );
}

function InnerParticles({ isMobile, mode }: { isMobile: boolean; mode: 'background' | 'mascot' }) {
  const pointsRef = useRef<THREE.Points>(null);
  const count = mode === 'mascot' ? 20 : (isMobile ? 150 : 400);

  const positions = new Float32Array(count * 3);
  const baseRadius = mode === 'mascot' ? 2.5 : (isMobile ? 2.0 : 3.3);

  for (let i = 0; i < count; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = (baseRadius - 0.8) + Math.random() * 1.6;
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);
  }

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.getElapsedTime() * 0.05;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#22C55E"
        size={mode === 'mascot' ? 0.2 : 0.025}
        transparent
        opacity={1.0}
        sizeAttenuation
      />
    </points>
  );
}

export default function PolyhedronCanvas({ isMobile: isMobileProp, mode = 'background', onLoad }: { isMobile?: boolean, mode?: 'background' | 'mascot', onLoad?: () => void }) {
  const [loaded, setLoaded] = useState(false);
  const isMobile = isMobileProp ?? (typeof window !== 'undefined' && window.innerWidth < 768);

  useEffect(() => {
    if (loaded && onLoad) {
      onLoad();
    }
  }, [loaded, onLoad]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        opacity: mode === 'mascot' ? 1 : (loaded ? 0.6 : 0),
        transition: mode === 'mascot' ? "none" : "opacity 1s ease-in-out",
        position: "relative",
        zIndex: mode === 'background' ? 0 : 1,
      }}
    >
      <Canvas
        camera={{ position: [0, 0, mode === 'mascot' ? 9.5 : 6], fov: 50 }}
        style={{ background: "transparent" }}
        gl={{ alpha: true, antialias: !isMobile }}
        dpr={isMobile ? [1, 1.5] : [1, 2]}
        onCreated={() => setLoaded(true)}
      >
        <ambientLight intensity={0.5} />
        <RotatingPolyhedron isMobile={isMobile} mode={mode} />
        {mode === 'background' && <InnerParticles isMobile={isMobile} mode={mode} />}
      </Canvas>
    </div>
  );
}
