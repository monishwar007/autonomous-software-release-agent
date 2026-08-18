import React from 'react';
import { Canvas } from '@react-three/fiber';
import SecurityShield3D from './SecurityShield3D';

export default function SecurityChart({ data }) {
    const { critical = 0, high = 0, medium = 0, low = 0 } = data || {};
    const max = Math.max(critical, high, medium, low, 1);

    const bars = [
        { label: 'Critical', value: critical, cls: 'critical' },
        { label: 'High', value: high, cls: 'high' },
        { label: 'Medium', value: medium, cls: 'medium' },
        { label: 'Low', value: low, cls: 'low' },
    ];

    const total = critical + high + medium + low;

    return (
        <div className="glass-panel" style={{ position: 'relative', overflow: 'hidden' }}>
            <div className="glass-panel__head" style={{ position: 'relative', zIndex: 1 }}>
                <div>
                    <div className="glass-panel__title">
                        <span className="material-icons-outlined" style={{ fontSize: 18 }}>shield</span>
                        Security Scan Results
                    </div>
                    <div className="glass-panel__sub">Vulnerability breakdown by severity</div>
                </div>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{total} total issues</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 20, alignItems: 'center' }}>
                <div className="sec-chart" style={{ position: 'relative', zIndex: 1 }}>
                    {bars.map(b => (
                        <div className="sec-bar" key={b.cls}>
                            <span className="sec-bar__label">{b.label}</span>
                            <div className="sec-bar__track">
                                <div className={`sec-bar__fill sec-bar__fill--${b.cls}`}
                                    style={{ width: `${max > 0 ? (b.value / max) * 100 : 0}%` }} />
                            </div>
                            <span className="sec-bar__count">{b.value}</span>
                        </div>
                    ))}
                </div>
                
                <div style={{ height: 180, position: 'relative' }}>
                    <Canvas camera={{ position: [0, 0, 8], fov: 45 }}>
                        <ambientLight intensity={0.5} />
                        <pointLight position={[10, 10, 10]} intensity={1} />
                        <SecurityShield3D critical={critical} high={high} />
                    </Canvas>
                </div>
            </div>

            {/* Scan metadata bar */}
            <div style={{
                marginTop: 20, display: 'flex', gap: 20, flexWrap: 'wrap',
                padding: '10px 14px', borderRadius: 8,
                background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)',
                fontSize: 11, color: 'var(--text-muted)',
                position: 'relative', zIndex: 1
            }}>
                <span>Scanner: <b style={{ color: 'var(--text-secondary)' }}>Bandit v1.7.5</b></span>
                <span>Duration: <b style={{ color: 'var(--text-secondary)' }}>3.2s</b></span>
                <span>Files: <b style={{ color: 'var(--text-secondary)' }}>47 scanned</b></span>
                <span>Last Scan: <b style={{ color: 'var(--text-secondary)' }}>Just now</b></span>
            </div>
        </div>
    );
}

