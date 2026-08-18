import React from 'react';

export default function Recommendations({ analysis, security, test }) {
    if (!analysis) return null;

    const cards = [];

    // Test recommendation
    if (test?.passed) {
        cards.push({
            icon: '✅', cls: 'green',
            title: 'Test Integrity',
            desc: 'All tests passing with high confidence. No immediate remediation action required for the current candidate.',
        });
    } else {
        cards.push({
            icon: '❌', cls: 'yellow',
            title: 'Test Failures Detected',
            desc: `${test?.failed_tests || 0} test(s) failed. Review failing test cases and fix before proceeding with the release.`,
        });
    }

    // Security recommendation
    if (security?.critical > 0) {
        cards.push({
            icon: '🛡️', cls: 'yellow',
            title: 'Critical Security Alert',
            desc: `${security.critical} critical vulnerability found. Immediate patching required before any release activity.`,
        });
    } else if ((security?.medium || 0) > 0) {
        cards.push({
            icon: '🔍', cls: 'yellow',
            title: 'Security Review',
            desc: `Review ${security.medium} medium security findings identified in dependency tree. Consider updating non-breaking patches.`,
        });
    } else {
        cards.push({
            icon: '🛡️', cls: 'green',
            title: 'Security Clear',
            desc: 'No critical or high severity security issues detected. Dependencies are up to date.',
        });
    }

    // Module recommendation
    const hasAuth = analysis.commit?.files_changed?.some(f =>
        f.toLowerCase().includes('auth') || f.toLowerCase().includes('login') || f.toLowerCase().includes('security')
    );

    if (hasAuth) {
        cards.push({
            icon: '⚠️', cls: 'purple',
            title: 'Auth Module Alert',
            desc: 'Authentication module changes detected. Suggested manual peer review due to risk sensitivity.',
        });
    } else {
        cards.push({
            icon: '📦', cls: 'green',
            title: 'Standard Changeset',
            desc: 'No sensitive module modifications detected. Changes follow established patterns and can proceed normally.',
        });
    }

    return (
        <div className="reco-grid">
            {cards.map((c, i) => (
                <div className={`reco-card reco-card--${c.cls}`} key={i}>
                    <div className="reco-card__icon">{c.icon}</div>
                    <div className="reco-card__title">{c.title}</div>
                    <div className="reco-card__desc">{c.desc}</div>
                </div>
            ))}
        </div>
    );
}
