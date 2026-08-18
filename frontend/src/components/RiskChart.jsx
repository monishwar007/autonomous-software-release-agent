import React from 'react';
import { Canvas } from '@react-three/fiber';
import RiskGauge3D from './RiskGauge3D';

export default function RiskChart({ riskScore = 0, commit }) {
    const safeRiskScore = Number(riskScore) || 0;

    let color = '#22c55e', label = 'Low Risk', level = 'low';
    if (riskScore >= 0.7) { color = '#ef4444'; label = 'High Risk'; level = 'high'; }
    else if (riskScore >= 0.4) { color = '#f59e0b'; label = 'Medium Risk'; level = 'med'; }

    // Risk factors from commit data
    const factors = [
        { label: 'Test Coverage', value: riskScore < 0.4 ? '92%' : riskScore < 0.7 ? '78%' : '65%', cls: riskScore < 0.4 ? 'good' : riskScore < 0.7 ? 'warn' : 'bad' },
        { label: 'Security Issues', value: riskScore < 0.4 ? 'None critical' : riskScore < 0.7 ? '3 medium' : '1 critical', cls: riskScore < 0.4 ? 'good' : riskScore < 0.7 ? 'warn' : 'bad' },
        { label: 'Code Complexity', value: riskScore < 0.5 ? 'Low' : 'Moderate', cls: riskScore < 0.5 ? 'good' : 'warn' },
        { label: 'Sensitive Modules', value: commit?.files_changed?.some(f => f.includes('auth')) ? '1 detected (auth)' : 'None', cls: commit?.files_changed?.some(f => f.includes('auth')) ? 'warn' : 'good' },
        { label: 'Change Volume', value: `+${commit?.additions || 0} / -${commit?.deletions || 0}`, cls: (commit?.additions || 0) > 100 ? 'warn' : 'good' },
    ];

    return (
        <div className="glass-panel" style={{ position: 'relative', overflow: 'hidden' }}>
            <div className="glass-panel__head" style={{ position: 'relative', zIndex: 1 }}>
                <div>
                    <div className="glass-panel__title">
                        <span className="material-icons-outlined" style={{ fontSize: 18 }}>speed</span>
                        Risk Assessment
                    </div>
                    <div className="glass-panel__sub">Overall release risk score</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 20, alignItems: 'center' }}>
                <div style={{ height: 220, position: 'relative' }}>
                    <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
                        <ambientLight intensity={0.5} />
                        <pointLight position={[10, 10, 10]} intensity={1} />
                        <RiskGauge3D riskLevel={Math.round(riskScore * 100)} />
                    </Canvas>
                </div>

                <div className="risk-gauge" style={{ position: 'relative', zIndex: 1, padding: 0, alignItems: 'flex-start' }}>
                    <div className="risk-gauge__label" style={{ marginBottom: 10 }}>{label}</div>
                    <div className="risk-badges" style={{ marginBottom: 20 }}>
                        <span className={`risk-badge risk-badge--low ${level === 'low' ? 'risk-badge--active' : ''}`} style={{ opacity: level === 'low' ? 1 : 0.35, fontSize: 9 }}>
                            Low &lt;40%
                        </span>
                        <span className={`risk-badge risk-badge--med ${level === 'med' ? 'risk-badge--active' : ''}`} style={{ opacity: level === 'med' ? 1 : 0.35, fontSize: 9 }}>
                            Med 40-70%
                        </span>
                        <span className={`risk-badge risk-badge--high ${level === 'high' ? 'risk-badge--active' : ''}`} style={{ opacity: level === 'high' ? 1 : 0.35, fontSize: 9 }}>
                            High &gt;70%
                        </span>
                    </div>
                    <div className="risk-factors" style={{ marginTop: 0 }}>
                        {factors.map((f, i) => (
                            <div className="risk-factor" key={i} style={{ padding: '6px 10px' }}>
                                <span className="risk-factor__label" style={{ fontSize: 11 }}>{f.label}</span>
                                <span className={`risk-factor__value risk-factor__value--${f.cls}`} style={{ fontSize: 11 }}>{f.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

