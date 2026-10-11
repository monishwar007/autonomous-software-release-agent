import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Box, Float } from '@react-three/drei';
import * as THREE from 'three';

// One cube per test would be unreadable (and slow) for a real suite with
// hundreds of tests, so draw at most MAX_BOXES cubes, keeping the pass ratio.
const MAX_BOXES = 30;

export default function TestBox3D({ total = 0, passed = 0 }) {
  const groupRef = useRef();

  const boxes = useMemo(() => {
    const shown = Math.min(total, MAX_BOXES);
    const shownPassed = total > MAX_BOXES ? Math.round((passed / total) * MAX_BOXES) : passed;
    return Array.from({ length: shown }).map((_, i) => ({
      position: [
        (i % 5) - 2,
        Math.floor(i / 5) - 2,
        0
      ],
      isPassed: i < shownPassed
    }));
  }, [total, passed]);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(state.clock.getElapsedTime() * 0.3) * 0.2;
    }
  });

  return (
    <group ref={groupRef} scale={0.6}>
      {boxes.map((box, i) => (
        <Float 
          key={i} 
          speed={box.isPassed ? 1 : 5} 
          rotationIntensity={box.isPassed ? 0.2 : 2} 
          floatIntensity={box.isPassed ? 0.2 : 2}
        >
          <Box args={[0.6, 0.6, 0.6]} position={box.position}>
            <meshStandardMaterial 
              color={box.isPassed ? "#22c55e" : "#ef4444"} 
              emissive={box.isPassed ? "#22c55e" : "#ef4444"}
              emissiveIntensity={box.isPassed ? 0.5 : 2}
              metalness={0.8}
              roughness={0.2}
            />
          </Box>
        </Float>
      ))}
    </group>
  );
}