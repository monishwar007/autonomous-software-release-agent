import React from 'react';

export default function LogsViewer({ history = [], filter = 'all', onFilterChange }) {
    const formatTime = (ts) => {
        if (!ts) return '';
        const d = new Date(ts);
        const diff = (Date.now() - d.getTime()) / 1000;
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    const riskColor = (s) =>
        s >= 0.7 ? '#ef4444' : s >= 0.4 ? '#f59e0b' : '#22c55e';

    const icons = { approve: '✓', reject: '✗', hold: '⏸' };
    const filters = [
        { key: 'all', label: 'All' },
        { key: 'approve', label: 'Approved' },
        { key: 'reject', label: 'Rejected' },
        { key: 'hold', label: 'On Hold' },
    ];

    return (
        <div className="history-panel glass-panel">
            <div className="glass-panel__head">
                <div>
                    <div className="glass-panel__title">
                        <span className="material-icons-outlined" style={{ fontSize: 18 }}>history</span>
                        Decision History
                    </div>
                    <div className="glass-panel__sub">Complete log of all release decisions</div>
                </div>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{history.length} entries</span>
            </div>

            {/* Filter buttons */}
            <div className="history-filters">
                {filters.map(f => (
                    <button key={f.key}
                        className={`filter-btn ${filter === f.key ? 'filter-btn--active' : ''}`}
                        onClick={() => onFilterChange?.(f.key)}>
                        {f.label}
                    </button>
                ))}
            </div>

            {history.length === 0 ? (
                <div className="empty">
                    <div className="empty__icon">📊</div>
                    <div className="empty__title">No Analyses Yet</div>
                    <div className="empty__desc">Run your first release analysis to see decision history. Click "New Analysis" to get started.</div>
                </div>
            ) : (
                <div style={{ overflowX: 'auto' }}>
                    <table className="history-table">
                        <thead>
                            <tr>
                                <th>Commit</th>
                                <th>Author</th>
                                <th>Message</th>
                                <th>Decision</th>
                                <th>Risk</th>
                                <th>Tests</th>
                                <th>Security</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history.map((e, i) => (
                                <tr key={e.id || i}>
                                    <td><span className="td-hash">{e.commit_id}</span></td>
                                    <td>{e.author}</td>
                                    <td><span className="td-msg">{e.message}</span></td>
                                    <td>
                                        <span className={`decision-pill decision-pill--${e.decision}`}>
                                            {icons[e.decision]} {e.decision}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="risk-mini">
                                            <div className="risk-mini__bar">
                                                <div className="risk-mini__fill" style={{
                                                    width: `${e.risk_score * 100}%`,
                                                    background: riskColor(e.risk_score),
                                                }} />
                                            </div>
                                            <span className="risk-mini__pct" style={{ color: riskColor(e.risk_score) }}>
                                                {Math.round(e.risk_score * 100)}%
                                            </span>
                                        </div>
                                    </td>
                                    <td>
                                        <span className={e.test_passed ? 'td-pass' : 'td-fail'}>
                                            {e.test_passed ? '✓ Pass' : '✗ Fail'}
                                        </span>
                                    </td>
                                    <td>
                                        {e.security_critical > 0 ? (
                                            <span className="td-fail">{e.security_critical} Critical</span>
                                        ) : (
                                            <span className="td-pass">Clean</span>
                                        )}
                                    </td>
                                    <td><span className="td-time">{formatTime(e.timestamp)}</span></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
