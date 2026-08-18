import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text, Torus } from '@react-three/drei';

export default function RiskGauge3D({ riskLevel = 15 }) {
  const ringRef = useRef();

  // Determine the glowing color based on the DevOps risk percentage
  let gaugeColor = "#4ade80"; // Green for safe/low risk
  if (riskLevel >= 40) gaugeColor = "#fbbf24"; // Yellow for warning/medium
  if (riskLevel >= 75) gaugeColor = "#ef4444"; // Red for danger/high

  // Animate the outer ring to spin and gently float
  useFrame((state, delta) => {
    if (ringRef.current) {
      ringRef.current.rotation.z -= delta * 0.8;
      ringRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.5) * 0.15;
      ringRef.current.rotation.y = Math.cos(state.clock.elapsedTime * 0.5) * 0.15;
    }
  });

  return (
    <group>
      {/* Dimmed Background Track */}
      <Torus args={[2, 0.1, 16, 100]}>
        <meshStandardMaterial color="#1f2937" transparent opacity={0.4} />
      </Torus>

      {/* Active Glowing Risk Ring */}
      <Torus 
        ref={ringRef}
        args={[2.2, 0.04, 16, 100, (riskLevel / 100) * Math.PI * 2]} 
        rotation={[0, 0, Math.PI / 2]}
      >
        <meshStandardMaterial 
          color={gaugeColor} 
          emissive={gaugeColor} 
          emissiveIntensity={1.5} 
          toneMapped={false} 
        />
      </Torus>

      {/* Center Text displaying the exact risk percentage */}
      <Text
        position={[0, 0.2, 0]}
        fontSize={0.9}
        color={gaugeColor}
        anchorX="center"
        anchorY="middle"
        font="https://fonts.gstatic.com/s/roboto/v18/KFOmCnqEu92Fr1Mu4mxM.woff"
      >
        {`${riskLevel}%`}
      </Text>
      
      <Text
        position={[0, -0.6, 0]}
        fontSize={0.25}
        color="#9ca3af"
        anchorX="center"
        anchorY="middle"
        letterSpacing={0.1}
      >
        RELEASE RISK
      </Text>
    </group>
  );
}