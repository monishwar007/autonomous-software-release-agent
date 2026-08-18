import React from 'react';

export default function DecisionCard({ analysis }) {
    if (!analysis) return null;

    const d = analysis.decision;
    const icons = { approve: '✅', reject: '❌', hold: '⏸️' };
    const labels = { approve: 'Release Approved', reject: 'Release Rejected', hold: 'Release On Hold' };

    const time = analysis.timestamp ? new Date(analysis.timestamp).toLocaleString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    }) : '';

    return (
        <div className={`release-banner release-banner--${d}`}>
            <div className="release-banner__icon">{icons[d] || '❔'}</div>
            <div className="release-banner__body">
                <div className="release-banner__decision">{labels[d] || 'Unknown'}</div>
                <div className="release-banner__reason">
                    {analysis.reasoning || 'Automated analysis complete. Review metrics below for details.'}
                </div>
            </div>
            <div className="release-banner__meta">
                <div className="release-banner__commit">
                    #{analysis.commit?.commit_id || 'N/A'}
                </div>
                <div className="release-banner__time">{time}</div>
            </div>
        </div>
    );
}
