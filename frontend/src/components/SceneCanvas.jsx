import React from 'react';
import { Canvas } from '@react-three/fiber';
import Scene from './Scene';

// The animated 3D background. Kept in its own module so Dashboard can load it
// lazily and three.js stays out of the initial bundle.
export default function SceneCanvas({ riskScore }) {
    return (
        <Canvas camera={{ position: [0, 0, 15], fov: 60 }}>
            <Scene riskScore={riskScore} />
        </Canvas>
    );
}
