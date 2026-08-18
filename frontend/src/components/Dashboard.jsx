import React, { useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import Scene from './Scene';
import ScrambleText from './ScrambleText';
import { ErrorBoundary } from '../ErrorBoundary';
import RiskChart from './RiskChart';
import SecurityChart from './SecurityChart';
import TestSummary from './TestSummary';
import DecisionCard from './DecisionCard';
import LogsViewer from './LogsViewer';
import CommitInfo from './CommitInfo';
import Recommendations from './Recommendations';
import { triggerAnalysis, getHistory, getStats, getMockAnalysis, getMockHistory } from '../services/api';

export default function Dashboard() {
    const [analysisResult, setAnalysisResult] = useState(null);
    const [history, setHistory] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [formData, setFormData] = useState({ repoUrl: '', commitId: '', branch: 'main' });
    const [activeNav, setActiveNav] = useState('dashboard');
    const [historyFilter, setHistoryFilter] = useState('all');
    const [notification, setNotification] = useState(null);

    useEffect(() => { 
        if (notification) {
            const timer = setTimeout(() => setNotification(null), 4000);
            return () => clearTimeout(timer);
        }
    }, [notification]);

    useEffect(() => { loadData(); }, []);

    async function loadData() {
        try {
            const [histRes, statsRes] = await Promise.all([getHistory(), getStats()]);
            setHistory(histRes.history || []);
            setStats(statsRes.stats || null);

            if (histRes.history && histRes.history.length > 0) {
                const latest = histRes.history[0];
                setAnalysisResult({
                    analysis: {
                        commit: { commit_id: latest.commit_id, author: latest.author, message: latest.message, additions: 0, deletions: 0, files_changed: [] },
                        tests: { passed: latest.test_passed, total_tests: 24, passed_tests: latest.test_passed ? 24 : 18, failed_tests: latest.test_passed ? 0 : 6 },
                        security: { critical: latest.security_critical, high: latest.security_high || 0, medium: 0, low: 0 },
                        risk_score: latest.risk_score,
                        decision: latest.decision ? latest.decision.toLowerCase() : 'hold',
                        reasoning: latest.reasoning,
                        timestamp: latest.timestamp,
                    }
                });
            }
        } catch (err) {
            console.error('Failed to load live data:', err);
        }
    }

    async function handleAnalysis(e) {
        e.preventDefault();
        setLoading(true);
        setShowModal(false);
        try {
            const result = await triggerAnalysis(formData.repoUrl, formData.commitId, formData.branch);
            setAnalysisResult(result);
            const entry = {
                id: history.length + 1,
                commit_id: result.analysis.commit.commit_id,
                author: result.analysis.commit.author,
                message: result.analysis.commit.message,
                decision: result.analysis.decision,
                risk_score: result.analysis.risk_score,
                reasoning: result.analysis.reasoning,
                test_passed: result.analysis.tests.passed,
                security_critical: result.analysis.security.critical,
                security_high: result.analysis.security.high,
                timestamp: result.analysis.timestamp,
            };
            setHistory(prev => [entry, ...prev]);
            setStats(prev => {
                const total = (prev?.total_analyses || 0) + 1;
                return {
                    total_analyses: total,
                    approved: (prev?.approved || 0) + (result.analysis.decision === 'approve' ? 1 : 0),
                    rejected: (prev?.rejected || 0) + (result.analysis.decision === 'reject' ? 1 : 0),
                    held: (prev?.held || 0) + (result.analysis.decision === 'hold' ? 1 : 0),
                    average_risk_score: parseFloat((((prev?.average_risk_score || 0) * (total - 1) + result.analysis.risk_score) / total).toFixed(2)),
                };
            });
        } catch (err) {
            console.error('Analysis failed:', err);
        } finally {
            setLoading(false);
        }
    }

    function handleExportReport(e) {
        if (e) e.preventDefault();
        
        try {
            setNotification({ type: 'info', message: 'Generating audit report...' });
            
            const s = stats || { total_analyses: 0, approved: 0, rejected: 0, held: 0, average_risk_score: 0 };
            
            const reportContent = `==================================================
SENTINEL AUTONOMOUS RELEASE ENGINE - AUDIT REPORT
==================================================
Generated: ${new Date().toLocaleString()}
Operator: Developer (Software Developer)
Engine Version: V2.4.0

--------------------------------------------------
1. EXECUTIVE SUMMARY
--------------------------------------------------
Total Analyses: ${s.total_analyses}
Approved: ${s.approved}
Rejected: ${s.rejected}
On Hold: ${s.held}
Average Risk Score: ${Math.round((s.average_risk_score || 0) * 100)}%

--------------------------------------------------
2. LATEST RELEASE STATUS
--------------------------------------------------
${analysisResult && analysisResult.analysis ? `
Commit: ${analysisResult.analysis.commit?.commit_id || 'N/A'}
Author: ${analysisResult.analysis.commit?.author || 'N/A'}
Decision: ${(analysisResult.analysis.decision || 'HOLD').toUpperCase()}
Risk Score: ${Math.round((analysisResult.analysis.risk_score || 0) * 100)}%
Reasoning: ${analysisResult.analysis.reasoning || 'No reasoning provided.'}
` : 'No active analysis data available.'}

--------------------------------------------------
3. DECISION HISTORY LOG
--------------------------------------------------
${history && history.length > 0 ? history.map(h => `
[${h.timestamp ? new Date(h.timestamp).toLocaleString() : 'Unknown Date'}]
Commit: ${(h.commit_id || 'N/A').substring(0, 8)}
Author: ${h.author || 'N/A'}
Decision: ${(h.decision || 'HOLD').toUpperCase()}
Risk: ${Math.round((h.risk_score || 0) * 100)}%
Message: ${h.message || 'No message'}
--------------------------------------------------`).join('\n') : 'No history records found.'}

==================================================
END OF REPORT
==================================================`;

            const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
            const url = window.URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `sentinel-report-${new Date().getTime()}.txt`;
            
            document.body.appendChild(link);
            link.click();
            
            setTimeout(() => {
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
                setNotification({ type: 'success', message: 'Report downloaded successfully.' });
            }, 1000);

        } catch (err) {
            console.error('Export error:', err);
            setNotification({ type: 'error', message: 'Report generation failed.' });
        }
    }

    const a = analysisResult?.analysis;
    const sec = a?.security || { critical: 0, high: 2, medium: 4, low: 7 };
    const test = a?.tests || { passed: true, total_tests: 24, passed_tests: 22, failed_tests: 2 };
    const risk = a?.risk_score ?? stats?.average_risk_score ?? 0;

    const filteredHistory = historyFilter === 'all' ? history : history.filter(h => h.decision === historyFilter);

    const navItems = [
        { id: 'dashboard', icon: 'dashboard', label: 'Dashboard' },
        { id: 'analysis', icon: 'search', label: 'New Analysis', action: () => setShowModal(true) },
        { id: 'history', icon: 'history', label: 'History', badge: history.length || null },
    ];
    const navMonitor = [
        { id: 'security', icon: 'shield', label: 'Security' },
        { id: 'tests', icon: 'science', label: 'Tests' },
        { id: 'risk', icon: 'warning_amber', label: 'Risk Engine' },
    ];
    const navSettings = [
        { id: 'config', icon: 'settings', label: 'Configuration' },
        { id: 'webhooks', icon: 'link', label: 'Webhooks' },
    ];

    return (
        <div className="app-layout">
            <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0, pointerEvents: 'none' }}>
                <Canvas camera={{ position: [0, 0, 15], fov: 60 }}>
                    <Scene riskScore={risk * 100} />
                </Canvas>
            </div>
            
            {/* ===== NOTIFICATION TOAST ===== */}
            {notification && (
                <div className={`notification-toast notification-toast--${notification.type}`}>
                    <span className="material-icons-outlined">
                        {notification.type === 'success' ? 'check_circle' : notification.type === 'error' ? 'error' : 'info'}
                    </span>
                    {notification.message}
                </div>
            )}

            {/* ===== SIDEBAR ===== */}
            <aside className="sidebar">
                <div className="sidebar__brand">
                    <div className="sidebar__brand-icon" style={{ background: 'var(--gradient-brand)' }}>
                        <span className="material-icons-outlined" style={{ fontSize: 24, color: '#fff' }}>shield</span>
                    </div>
                    <div className="sidebar__brand-text">
                        <span className="sidebar__brand-name">
                            <ScrambleText text="SENTINEL" speed={60} />
                        </span>
                        <span className="sidebar__brand-sub">
                            <ScrambleText text="RELEASE ENGINE" speed={30} delay={500} />
                        </span>
                    </div>
                </div>

                <nav className="sidebar__nav">
                    <div className="sidebar__section">Main</div>
                    {navItems.map(n => (
                        <div key={n.id}
                            className={`sidebar__item ${activeNav === n.id ? 'sidebar__item--active' : ''} `}
                            onClick={() => {
                                const targetNav = (n.id === 'analysis' || n.id === 'history') ? 'dashboard' : n.id;
                                setActiveNav(targetNav);
                                
                                if (n.action) {
                                    n.action();
                                } else if (n.id === 'history') {
                                    setTimeout(() => {
                                        document.getElementById('history-section')?.scrollIntoView({ behavior: 'smooth' });
                                    }, 10);
                                } else if (n.id === 'dashboard') {
                                    window.scrollTo({ top: 0, behavior: 'smooth' });
                                }
                            }}>
                            <span className="sidebar__item-icon material-icons-outlined">{n.icon}</span>
                            {n.label}
                            {n.badge && <span className="sidebar__badge">{n.badge}</span>}
                        </div>
                    ))}

                    <div className="sidebar__section">Monitoring</div>
                    {navMonitor.map(n => (
                        <div key={n.id}
                            className={`sidebar__item ${activeNav === n.id ? 'sidebar__item--active' : ''} `}
                            onClick={() => {
                                setActiveNav('dashboard');
                                setTimeout(() => {
                                    document.getElementById(`${n.id}-section`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                }, 10);
                            }}>
                            <span className="sidebar__item-icon material-icons-outlined">{n.icon}</span>
                            {n.label}
                        </div>
                    ))}

                    <div className="sidebar__section">Settings</div>
                    {navSettings.map(n => (
                        <div key={n.id}
                            className={`sidebar__item ${activeNav === n.id ? 'sidebar__item--active' : ''} `}
                            onClick={() => setActiveNav(n.id)}>
                            <span className="sidebar__item-icon material-icons-outlined">{n.icon}</span>
                            {n.label}
                        </div>
                    ))}
                </nav>

                <div className="sidebar__footer">
                    <div className="sidebar__user">
                        <div className="sidebar__avatar">DV</div>
                        <div className="sidebar__user-info">
                            <div className="sidebar__user-name">Developer</div>
                            <div className="sidebar__user-role">Software Developer</div>
                        </div>
                    </div>
                    <div className="sidebar__status">
                        <div className="sidebar__status-dot"></div>
                        <span className="sidebar__status-text">Agent Online</span>
                    </div>
                </div>
            </aside>

            {/* ===== MAIN ===== */}
            <main className="main">
                <header className="header">
                    <div className="header__left">
                        <div className="header__title">
                            <ScrambleText text="SENTINEL DASHBOARD" speed={50} />
                        </div>
                        <div className="header__subtitle">
                            <ScrambleText text="AUTONOMOUS AI-POWERED RELEASE DECISION ENGINE" speed={20} delay={800} />
                        </div>
                    </div>
                    <div className="header__actions">
                        <button className="btn" onClick={loadData}>
                            <span className="material-icons-outlined" style={{ fontSize: 15 }}>refresh</span>
                            Refresh
                        </button>
                        <button className="btn btn--primary" onClick={() => setShowModal(true)}>
                            <span className="material-icons-outlined" style={{ fontSize: 15 }}>bolt</span>
                            New Analysis
                        </button>
                    </div>
                </header>

                <div className="page">
                    {activeNav === 'dashboard' && (
                        <ErrorBoundary>
                            {/* Profile Details Section */}
                            <div className="glass-panel" style={{ marginBottom: 24, padding: '32px', borderLeft: '4px solid var(--accent-blue)' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
                                    <div className="sidebar__avatar" style={{ width: 100, height: 100, fontSize: 40, borderRadius: '20px' }}>DV</div>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                            <div>
                                                <h1 style={{ fontSize: 32, fontWeight: 800, marginBottom: 4 }}>
                                                    <ScrambleText text="DEVELOPER" speed={40} />
                                                </h1>
                                                <div style={{ color: 'var(--accent-blue)', fontWeight: 600, fontSize: 14, letterSpacing: '1px', textTransform: 'uppercase' }}>
                                                    Software Developer
                                                </div>
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>SECURITY CLEARANCE</div>
                                                <div style={{ color: 'var(--color-success)', fontWeight: 700 }}>LEVEL 4 (ALPHA)</div>
                                            </div>
                                        </div>
                                        
                                        <div style={{ display: 'flex', gap: 24, marginTop: 20 }}>
                                            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
                                                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>PRIMARY TECH</div>
                                                <div style={{ fontSize: 13, fontWeight: 600 }}>Python / React / Go</div>
                                            </div>
                                            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
                                                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>DEPLOYMENTS</div>
                                                <div style={{ fontSize: 13, fontWeight: 600 }}>128 Successful</div>
                                            </div>
                                            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
                                                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>UPTIME</div>
                                                <div style={{ fontSize: 13, fontWeight: 600 }}>99.9% Reliable</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Stat Cards */}
                            <ErrorBoundary>
                                <div className="stats-row">
                                    <div className="stat-card">
                                        <div className="stat-card__top">
                                            <div className="stat-card__icon stat-card__icon--blue">
                                                <span className="material-icons-outlined">analytics</span>
                                            </div>
                                        </div>
                                        <div className="stat-card__value">{stats?.total_analyses || 0}</div>
                                        <div className="stat-card__label">Total Analyses</div>
                                    </div>
                                    <div className="stat-card">
                                        <div className="stat-card__top">
                                            <div className="stat-card__icon stat-card__icon--green">
                                                <span className="material-icons-outlined">check_circle</span>
                                            </div>
                                        </div>
                                        <div className="stat-card__value">{stats?.approved || 0}</div>
                                        <div className="stat-card__label">Approved</div>
                                    </div>
                                    <div className="stat-card">
                                        <div className="stat-card__top">
                                            <div className="stat-card__icon stat-card__icon--red">
                                                <span className="material-icons-outlined">cancel</span>
                                            </div>
                                        </div>
                                        <div className="stat-card__value">{stats?.rejected || 0}</div>
                                        <div className="stat-card__label">Rejected</div>
                                    </div>
                                    <div className="stat-card">
                                        <div className="stat-card__top">
                                            <div className="stat-card__icon stat-card__icon--purple">
                                                <span className="material-icons-outlined">pause_circle</span>
                                            </div>
                                        </div>
                                        <div className="stat-card__value">{stats?.held || 0}</div>
                                        <div className="stat-card__label">On Hold</div>
                                    </div>
                                    <div className="stat-card">
                                        <div className="stat-card__top">
                                            <div className="stat-card__icon stat-card__icon--cyan">
                                                <span className="material-icons-outlined">speed</span>
                                            </div>
                                        </div>
                                        <div className="stat-card__value">{Math.round((stats?.average_risk_score || 0) * 100)}%</div>
                                        <div className="stat-card__label">Avg Risk Score</div>
                                    </div>
                                </div>
                            </ErrorBoundary>

                            {/* Detailed Monitoring Panels */}
                            <div className="panel-grid">
                                <div id="risk-section"><ErrorBoundary><RiskChart riskScore={risk} commit={a?.commit} /></ErrorBoundary></div>
                                <div id="security-section"><ErrorBoundary><SecurityChart data={sec} /></ErrorBoundary></div>
                            </div>

                            <div className="panel-grid" id="tests-section">
                                <ErrorBoundary><TestSummary data={test} /></ErrorBoundary>
                                <ErrorBoundary><CommitInfo commit={a?.commit} /></ErrorBoundary>
                            </div>

                            {/* AI Recommendations */}
                            <ErrorBoundary><Recommendations analysis={a} security={sec} test={test} /></ErrorBoundary>

                            {/* Decision History */}
                            <div id="history-section">
                                <ErrorBoundary><LogsViewer history={filteredHistory} filter={historyFilter} onFilterChange={setHistoryFilter} /></ErrorBoundary>
                            </div>
                        </ErrorBoundary>
                    )}

                    {activeNav === 'config' && (
                        <div className="glass-panel" style={{ minHeight: '600px' }}>
                            <div className="glass-panel__head">
                                <div>
                                    <div className="glass-panel__title">
                                        <span className="material-icons-outlined" style={{ fontSize: 18 }}>settings</span>
                                        Configuration Engine
                                    </div>
                                    <div className="glass-panel__sub">Adjust automated release rules and AI model parameters</div>
                                </div>
                            </div>
                            <div style={{ padding: '20px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                                <h3 style={{ fontSize: 13, marginBottom: 12, color: 'var(--text-secondary)' }}>Model Selection</h3>
                                <div style={{ display: 'flex', gap: 12 }}>
                                    <button className="btn btn--primary" style={{ padding: '8px 14px' }}>llama-3.3-70b-versatile</button>
                                    <button className="btn">gpt-4o</button>
                                    <button className="btn">claude-3.5-sonnet</button>
                                </div>
                            </div>
                            <div style={{ padding: '20px 0' }}>
                                <h3 style={{ fontSize: 13, marginBottom: 12, color: 'var(--text-secondary)' }}>Risk Thresholds</h3>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: 16, borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Auto-Reject Risk Score threshold</div>
                                        <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-danger)' }}>&gt; 0.70</div>
                                    </div>
                                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: 16, borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Auto-Hold Risk Score threshold</div>
                                        <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-hold)' }}>&gt; 0.40</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeNav === 'webhooks' && (
                        <div className="glass-panel" style={{ minHeight: '600px' }}>
                            <div className="glass-panel__head">
                                <div>
                                    <div className="glass-panel__title">
                                        <span className="material-icons-outlined" style={{ fontSize: 18 }}>link</span>
                                        Webhook Integrations
                                    </div>
                                    <div className="glass-panel__sub">Manage external system hooks and API triggers</div>
                                </div>
                                <button className="btn btn--primary">+ Add Webhook</button>
                            </div>
                            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase' }}>
                                        <th style={{ padding: '12px 8px' }}>Service</th>
                                        <th style={{ padding: '12px 8px' }}>Status</th>
                                        <th style={{ padding: '12px 8px' }}>Last Triggered</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                                        <td style={{ padding: '16px 8px', fontSize: 13 }}>GitHub Actions (torvalds/linux)</td>
                                        <td style={{ padding: '16px 8px' }}><span className="stat-card__trend stat-card__trend--up">Active</span></td>
                                        <td style={{ padding: '16px 8px', fontSize: 12, color: 'var(--text-secondary)' }}>Just now</td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                                        <td style={{ padding: '16px 8px', fontSize: 13 }}>Slack Notifications (#devops)</td>
                                        <td style={{ padding: '16px 8px' }}><span className="stat-card__trend stat-card__trend--up">Active</span></td>
                                        <td style={{ padding: '16px 8px', fontSize: 12, color: 'var(--text-secondary)' }}>12m ago</td>
                                    </tr>
                                    <tr>
                                        <td style={{ padding: '16px 8px', fontSize: 13 }}>PagerDuty (Criticals)</td>
                                        <td style={{ padding: '16px 8px' }}><span className="stat-card__trend stat-card__trend--neutral">Inactive</span></td>
                                        <td style={{ padding: '16px 8px', fontSize: 12, color: 'var(--text-secondary)' }}>Never</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Footer */}

                    <footer className="page-footer">
                        <span>© 2026 Autonomous Release Agent • Engine V2.4.0</span>
                        <div style={{ display: 'flex', gap: 16 }}>
                            <button 
                                onClick={handleExportReport}
                                style={{ 
                                    background: 'none', 
                                    border: 'none', 
                                    color: 'var(--accent-blue)', 
                                    cursor: 'pointer', 
                                    padding: 0, 
                                    font: 'inherit', 
                                    textDecoration: 'none' 
                                }}
                                onMouseOver={(e) => e.target.style.textDecoration = 'underline'}
                                onMouseOut={(e) => e.target.style.textDecoration = 'none'}
                            >
                                Export Report
                            </button>
                            <a href="#">API Documentation</a>
                        </div>
                    </footer>
                </div>
            </main>

            {/* ===== ANALYSIS MODAL ===== */}
            {showModal && (
                <div className="modal-backdrop" onClick={() => setShowModal(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <div className="modal__head">
                            <h2>⚡ New Release Analysis</h2>
                            <button className="modal__close" onClick={() => setShowModal(false)}>✕</button>
                        </div>
                        <form className="modal__form" onSubmit={handleAnalysis}>
                            <div>
                                <label className="field__label">Repository (optional)</label>
                                <input className="field__input" placeholder="owner/repo" value={formData.repoUrl}
                                    onChange={e => setFormData(p => ({ ...p, repoUrl: e.target.value }))} />
                            </div>
                            <div>
                                <label className="field__label">Commit ID (optional)</label>
                                <input className="field__input" placeholder="a1b2c3d4" value={formData.commitId}
                                    onChange={e => setFormData(p => ({ ...p, commitId: e.target.value }))} />
                            </div>
                            <div>
                                <label className="field__label">Branch</label>
                                <input className="field__input" placeholder="main" value={formData.branch}
                                    onChange={e => setFormData(p => ({ ...p, branch: e.target.value }))} />
                            </div>
                            <button className="btn--submit" type="submit" disabled={loading}>
                                {loading ? '🔄 Analyzing…' : '🚀 Run Analysis'}
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {loading && (
                <div className="loading-screen">
                    <div className="loading-spinner"></div>
                    <div className="loading-text">Running automated release analysis…</div>
                </div>
            )}
        </div>
    );
}
