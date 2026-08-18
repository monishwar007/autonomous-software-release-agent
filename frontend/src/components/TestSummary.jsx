import React from 'react';
import { Canvas } from '@react-three/fiber';
import TestBox3D from './TestBox3D';

export default function TestSummary({ data }) {
    const { total_tests = 24, passed_tests = 22, failed_tests = 2 } = data || {};
    const pct = total_tests > 0 ? Math.round((passed_tests / total_tests) * 100) : 100;
    const circ = 2 * Math.PI * 58;
    const offset = circ * (1 - pct / 100);

    // Suite breakdown
    const suites = [
        { name: 'Unit Tests', total: 15, passed: 15 },
        { name: 'Integration Tests', total: 7, passed: failed_tests > 0 ? 5 : 7 },
        { name: 'E2E Tests', total: 2, passed: 2 },
    ];

    return (
        <div className="glass-panel" style={{ position: 'relative', overflow: 'hidden' }}>
            <div className="glass-panel__head" style={{ position: 'relative', zIndex: 1 }}>
                <div>
                    <div className="glass-panel__title">
                        <span className="material-icons-outlined" style={{ fontSize: 18 }}>science</span>
                        Test Summary
                    </div>
                    <div className="glass-panel__sub">Latest test execution results</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'center' }}>
                <div className="test-donut" style={{ position: 'relative', zIndex: 1 }}>
                    <div className="test-donut__ring" style={{ width: 120, height: 120 }}>
                        <svg className="test-donut__svg" width="120" height="120" viewBox="0 0 150 150">
                            <circle className="test-donut__bg" cx="75" cy="75" r="58" />
                            <circle className="test-donut__pass" cx="75" cy="75" r="58"
                                strokeDasharray={circ} strokeDashoffset={offset} />
                        </svg>
                        <div className="test-donut__center">
                            <div className="test-donut__pct" style={{ fontSize: 24 }}>{pct}%</div>
                            <div className="test-donut__pct-label" style={{ fontSize: 9 }}>Passed</div>
                        </div>
                    </div>

                    <div className="test-legend" style={{ fontSize: 11, gap: 10 }}>
                        <div className="test-legend__item">
                            <div className="test-legend__dot test-legend__dot--pass"></div>
                            Passed: <span className="test-legend__val">{passed_tests}</span>
                        </div>
                        <div className="test-legend__item">
                            <div className="test-legend__dot test-legend__dot--fail"></div>
                            Failed: <span className="test-legend__val">{failed_tests}</span>
                        </div>
                    </div>
                </div>
                
                <div style={{ height: 200, position: 'relative' }}>
                    <Canvas camera={{ position: [0, 0, 8], fov: 40 }}>
                        <ambientLight intensity={0.5} />
                        <pointLight position={[10, 10, 10]} intensity={1} />
                        <TestBox3D total={total_tests} passed={passed_tests} />
                    </Canvas>
                </div>
            </div>

            <div className="test-suites" style={{ position: 'relative', zIndex: 1 }}>
                {suites.map((s, i) => {
                    const allPass = s.passed === s.total;
                    return (
                        <div className="test-suite" key={i}>
                            <span className="test-suite__name">{s.name}</span>
                            <span className={`test-suite__result ${allPass ? 'test-suite__result--pass' : 'test-suite__result--fail'}`}>
                                {s.passed}/{s.total} {allPass ? '✓' : '✗'}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

