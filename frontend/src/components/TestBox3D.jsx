import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Box, Float } from '@react-three/drei';
import * as THREE from 'three';

export default function TestBox3D({ total = 24, passed = 22 }) {
  const groupRef = useRef();
  const failed = total - passed;
  
  const boxes = useMemo(() => {
    return Array.from({ length: total }).map((_, i) => ({
      position: [
        (i % 5) - 2,
        Math.floor(i / 5) - 2,
        0
      ],
      isPassed: i < passed
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