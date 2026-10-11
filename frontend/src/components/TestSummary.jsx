import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import TestBox3D from './TestBox3D';

export default function TestSummary({ data }) {
    // No demo fallbacks: until an analysis has run, every count is 0.
    const { total_tests = 0, passed_tests = 0, failed_tests = 0 } = data || {};
    const hasTests = total_tests > 0;
    const pct = hasTests ? Math.round((passed_tests / total_tests) * 100) : 0;
    const circ = 2 * Math.PI * 58;
    const offset = circ * (1 - pct / 100);

    // The backend counts skipped tests in the total but does not report them
    // separately, so derive them rather than leaving passed + failed != total.
    const skipped = Math.max(total_tests - passed_tests - failed_tests, 0);

    // Overall breakdown, computed only from the real counts. (The backend does
    // not report a per-suite split, so none is shown.)
    const rows = [{ name: 'Total tests', value: String(total_tests) }];
    if (skipped > 0) rows.push({ name: 'Skipped', value: String(skipped) });
    if (!hasTests) rows.push({ name: 'Result', value: 'No tests collected' });
    else if (failed_tests > 0) rows.push({ name: 'Result', value: `${failed_tests} failing ✗`, cls: 'fail' });
    else rows.push({ name: 'Result', value: 'All passing ✓', cls: 'pass' });

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
                            <div className="test-donut__pct" style={{ fontSize: 24 }}>{hasTests ? `${pct}%` : '—'}</div>
                            <div className="test-donut__pct-label" style={{ fontSize: 9 }}>{hasTests ? 'Passed' : 'No tests'}</div>
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
                    <Suspense fallback={null}>
                        <Canvas camera={{ position: [0, 0, 8], fov: 40 }}>
                            <ambientLight intensity={0.5} />
                            <pointLight position={[10, 10, 10]} intensity={1} />
                            <TestBox3D total={total_tests} passed={passed_tests} />
                        </Canvas>
                    </Suspense>
                </div>
            </div>

            <div className="test-suites" style={{ position: 'relative', zIndex: 1 }}>
                {rows.map((r) => (
                    <div className="test-suite" key={r.name}>
                        <span className="test-suite__name">{r.name}</span>
                        <span className={`test-suite__result${r.cls ? ` test-suite__result--${r.cls}` : ''}`}>
                            {r.value}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}
