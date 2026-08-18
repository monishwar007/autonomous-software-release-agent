import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const PARTICLE_COUNT = 600;

export default function ParticleBackground() {
  const meshRef = useRef();

  // Pre-compute random positions, velocities, and sizes
  const { positions, velocities, sizes } = useMemo(() => {
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const velocities = new Float32Array(PARTICLE_COUNT * 3);
    const sizes = new Float32Array(PARTICLE_COUNT);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      // Spread particles across a wide volume
      positions[i3]     = (Math.random() - 0.5) * 40;  // x
      positions[i3 + 1] = (Math.random() - 0.5) * 30;  // y
      positions[i3 + 2] = (Math.random() - 0.5) * 20;  // z

      // Very slow drift velocities for subtle motion
      velocities[i3]     = (Math.random() - 0.5) * 0.004;
      velocities[i3 + 1] = (Math.random() - 0.5) * 0.003;
      velocities[i3 + 2] = (Math.random() - 0.5) * 0.002;

      // Vary particle sizes for depth
      sizes[i] = Math.random() * 0.08 + 0.02;
    }

    return { positions, velocities, sizes };
  }, []);

  // Animate particles each frame
  useFrame(() => {
    if (!meshRef.current) return;
    const posAttr = meshRef.current.geometry.attributes.position;
    const arr = posAttr.array;

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;

      arr[i3]     += velocities[i3];
      arr[i3 + 1] += velocities[i3 + 1];
      arr[i3 + 2] += velocities[i3 + 2];

      // Wrap around boundaries so particles never disappear
      if (arr[i3]     >  20) arr[i3]     = -20;
      if (arr[i3]     < -20) arr[i3]     =  20;
      if (arr[i3 + 1] >  15) arr[i3 + 1] = -15;
      if (arr[i3 + 1] < -15) arr[i3 + 1] =  15;
      if (arr[i3 + 2] >  10) arr[i3 + 2] = -10;
      if (arr[i3 + 2] < -10) arr[i3 + 2] =  10;
    }

    posAttr.needsUpdate = true;
  });

  return (
    <points ref={meshRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={PARTICLE_COUNT}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-size"
          array={sizes}
          count={PARTICLE_COUNT}
          itemSize={1}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        color="#00e5ff"
        transparent
        opacity={0.35}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
