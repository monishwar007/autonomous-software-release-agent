import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Sphere } from '@react-three/drei';
import * as THREE from 'three';

export default function SecurityShield3D({ critical = 0, high = 0 }) {
  const meshRef = useRef();
  
  // Determine shield color based on security issues
  let shieldColor = "#3b82f6"; // Blue for safe
  if (high > 0) shieldColor = "#f59e0b"; // Orange for warning
  if (critical > 0) shieldColor = "#ef4444"; // Red for critical

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.5;
    }
  });

  return (
    <group>
      <Float speed={2} rotationIntensity={1} floatIntensity={1}>
        <mesh ref={meshRef}>
          <octahedronGeometry args={[2, 0]} />
          <MeshDistortMaterial
            color={shieldColor}
            speed={2}
            distort={0.4}
            radius={1}
            emissive={shieldColor}
            emissiveIntensity={0.5}
            roughness={0.2}
            metalness={0.8}
            transparent
            opacity={0.8}
          />
        </mesh>
        
        {/* Inner glow sphere */}
        <Sphere args={[1.2, 32, 32]}>
          <meshStandardMaterial
            color={shieldColor}
            emissive={shieldColor}
            emissiveIntensity={2}
            transparent
            opacity={0.3}
          />
        </Sphere>
      </Float>
      
      {/* Dynamic ambient particles around shield */}
      {Array.from({ length: 15 }).map((_, i) => (
        <Float key={i} position={[(Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6]}>
          <mesh>
            <boxGeometry args={[0.1, 0.1, 0.1]} />
            <meshStandardMaterial color={shieldColor} emissive={shieldColor} emissiveIntensity={1} />
          </mesh>
        </Float>
      ))}
    </group>
  );
}