import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Icosahedron, Text } from '@react-three/drei';

export default function FloatingDecisionIcon({ status = 'ANALYZING' }) {
  const meshRef = useRef();

  // Determine color and wireframe state based on the agent's decision
  let color = "#3b82f6"; // Blue for analyzing
  let isWireframe = true;

  if (status === 'APPROVED') {
    color = "#10b981"; // Green for approved
    isWireframe = false;
  } else if (status === 'REJECTED') {
    color = "#ef4444"; // Red for rejected
    isWireframe = false;
  }

  // Animate the icon to float up and down while rotating
  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * 0.5;
      meshRef.current.rotation.y += delta * 0.5;
      // Math.sin creates a smooth up-and-down hovering effect
      meshRef.current.position.y = Math.sin(state.clock.elapsedTime * 2) * 0.2 + 0.5; 
    }
  });

  return (
    <group>
      <Icosahedron ref={meshRef} args={[1, 0]} position={[0, 0.5, 0]}>
        <meshStandardMaterial 
          color={color} 
          wireframe={isWireframe} 
          emissive={color}
          emissiveIntensity={0.5}
        />
      </Icosahedron>
      
      <Text
        position={[0, -1, 0]}
        fontSize={0.35}
        color={color}
        anchorX="center"
        anchorY="middle"
        letterSpacing={0.1}
        font="https://fonts.gstatic.com/s/roboto/v18/KFOmCnqEu92Fr1Mu4mxM.woff"
      >
        {status}
      </Text>
    </group>
  );
}