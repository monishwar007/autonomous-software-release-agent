import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Sphere, Line } from '@react-three/drei';
import * as THREE from 'three';

export default function Scene({ riskScore = 30 }) {
  const group = useRef();

  // Determine colors based on risk
  const isHighRisk = riskScore > 50;
  const primaryColor = isHighRisk ? '#ef4444' : '#3b82f6';
  const secondaryColor = isHighRisk ? '#fbbf24' : '#8b5cf6';

  // Generate nodes representing files/commits
  const nodes = useMemo(() => {
    return Array.from({ length: 40 }).map(() => ({
      position: [
        (Math.random() - 0.5) * 15,
        (Math.random() - 0.5) * 15,
        (Math.random() - 0.5) * 15
      ],
      color: Math.random() > 0.7 ? secondaryColor : primaryColor,
      size: Math.random() * 0.15 + 0.05
    }));
  }, [primaryColor, secondaryColor]);

  // Generate lines connecting nearby nodes
  const lines = useMemo(() => {
    const linesArr = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const d = new THREE.Vector3(...nodes[i].position).distanceTo(new THREE.Vector3(...nodes[j].position));
        if (d < 5) {
          linesArr.push([nodes[i].position, nodes[j].position]);
        }
      }
    }
    return linesArr;
  }, [nodes]);

  useFrame((state, delta) => {
    if (group.current) {
      group.current.rotation.y += delta * 0.05;
      group.current.rotation.x += delta * 0.03;
    }
  });

  return (
    <group ref={group}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={2} color={primaryColor} />
      <pointLight position={[-10, -10, -10]} intensity={1} color={secondaryColor} />
      
      {nodes.map((node, i) => (
        <Sphere key={`node-${i}`} args={[node.size, 16, 16]} position={node.position}>
          <meshStandardMaterial 
            color={node.color} 
            emissive={node.color} 
            emissiveIntensity={1.5} 
            toneMapped={false} 
            transparent 
            opacity={0.9}
          />
        </Sphere>
      ))}

      {lines.map((line, i) => (
        <Line 
          key={`line-${i}`}
          points={line} 
          color={primaryColor} 
          lineWidth={0.5} 
          transparent 
          opacity={0.15} 
        />
      ))}
    </group>
  );
}