const API_BASE = '/webhook';

export async function triggerAnalysis(repoUrl = '', commitId = '', branch = 'main') {
    const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            repo_url: repoUrl,
            commit_id: commitId,
            branch: branch,
        }),
    });
    if (!response.ok) throw new Error('Failed to start analysis');
    const { job_id } = await response.json();
    return pollAnalysisJob(job_id);
}

// Analysis now runs as a background job (clone + isolated venv + pytest +
// bandit can take anywhere from a few seconds to a couple of minutes), so
// the backend returns a job_id immediately instead of the full result.
// This polls for completion so callers (Dashboard.jsx) can keep awaiting
// triggerAnalysis() exactly as before, without needing to know about jobs.
async function pollAnalysisJob(jobId, { intervalMs = 2000, timeoutMs = 180000 } = {}) {
    const start = Date.now();

    while (Date.now() - start < timeoutMs) {
        const response = await fetch(`${API_BASE}/analyze/${jobId}`);
        if (!response.ok) throw new Error('Failed to fetch analysis status');
        const data = await response.json();

        if (data.status === 'completed') {
            return {
                status: 'success',
                analysis: {
                    commit: data.analysis.commit,
                    tests: data.analysis.tests,
                    security: {
                        critical: data.analysis.security.critical,
                        high: data.analysis.security.high,
                        medium: data.analysis.security.medium,
                        low: data.analysis.security.low,
                        issues: data.analysis.security.issues || [],
                        scanned_files: data.analysis.security.scanned_files || 0,
                        duration: data.analysis.security.duration || 0
                    },
                    risk_score: data.analysis.risk_score,
                    decision: data.analysis.decision.toLowerCase(),
                    reasoning: data.analysis.reasoning,
                    timestamp: data.analysis.timestamp,
                },
            };
        }

        if (data.status === 'failed') {
            throw new Error(data.error || 'Analysis failed');
        }

        // status is 'pending' or 'running' - wait and poll again
        await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }

    throw new Error('Analysis timed out waiting for a result');
}

export async function getHistory() {
    const response = await fetch(`${API_BASE}/history`);
    if (!response.ok) throw new Error('Failed to fetch history');
    return response.json();
}

export async function getStats() {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
}

// Mock data for demo when backend is not available
export function getMockAnalysis() {
    const decisions = ['approve', 'reject', 'hold'];
    const decision = decisions[Math.floor(Math.random() * 3)];
    const riskScore = decision === 'approve' ? Math.random() * 0.3 : decision === 'hold' ? 0.3 + Math.random() * 0.3 : 0.6 + Math.random() * 0.4;

    return {
        status: 'success',
        analysis: {
            commit: {
                commit_id: Math.random().toString(36).substring(2, 10),
                author: ['Alex Chen', 'Sarah Kim', 'DevOps Bot', 'James Wilson'][Math.floor(Math.random() * 4)],
                message: [
                    'feat: add OAuth2 authentication flow',
                    'fix: resolve memory leak in connection pool',
                    'refactor: optimize database queries',
                    'chore: update security dependencies',
                    'feat: implement rate limiting middleware',
                ][Math.floor(Math.random() * 5)],
                timestamp: new Date().toISOString(),
                files_changed: ['src/auth/login.py', 'src/middleware/rate_limit.py', 'tests/test_auth.py'],
                additions: Math.floor(Math.random() * 200) + 20,
                deletions: Math.floor(Math.random() * 80) + 5,
            },
            tests: {
                passed: decision !== 'reject',
                total_tests: 24,
                passed_tests: decision === 'reject' ? 18 : 24,
                failed_tests: decision === 'reject' ? 6 : 0,
                raw_output: 'Test execution complete',
            },
            security: {
                critical: decision === 'reject' ? Math.floor(Math.random() * 2) + 1 : 0,
                high: Math.floor(Math.random() * 3),
                medium: Math.floor(Math.random() * 5) + 1,
                low: Math.floor(Math.random() * 8) + 2,
            },
            risk_score: parseFloat(riskScore.toFixed(2)),
            decision: decision,
            reasoning: decision === 'approve'
                ? 'All tests pass with no critical security vulnerabilities. Code changes are well-scoped and follow best practices. Safe to proceed with release.'
                : decision === 'hold'
                    ? 'Moderate risk detected. Some non-critical security issues found. Recommend manual review of changed modules before proceeding.'
                    : 'High risk detected. Critical security vulnerabilities found and multiple test failures. Immediate remediation required before release.',
            timestamp: new Date().toISOString(),
        },
    };
}

export function getMockHistory() {
    const entries = [];
    const authors = ['Alex Chen', 'Sarah Kim', 'DevOps Bot', 'James Wilson', 'Maria Garcia'];
    const messages = [
        'feat: add user authentication',
        'fix: resolve XSS vulnerability',
        'refactor: optimize API endpoints',
        'chore: update dependencies',
        'feat: implement caching layer',
        'fix: database connection timeout',
        'feat: add rate limiting',
        'fix: memory leak in worker process',
    ];

    for (let i = 0; i < 8; i++) {
        const decisions = ['approve', 'reject', 'hold'];
        const decision = decisions[Math.floor(Math.random() * 3)];
        const riskScore = decision === 'approve' ? Math.random() * 0.3 : decision === 'hold' ? 0.3 + Math.random() * 0.3 : 0.6 + Math.random() * 0.4;

        const date = new Date();
        date.setHours(date.getHours() - i * 3);

        entries.push({
            id: i + 1,
            commit_id: Math.random().toString(36).substring(2, 10),
            author: authors[i % authors.length],
            message: messages[i],
            decision: decision,
            risk_score: parseFloat(riskScore.toFixed(2)),
            reasoning: 'Automated analysis complete',
            test_passed: decision !== 'reject',
            security_critical: decision === 'reject' ? 1 : 0,
            security_high: Math.floor(Math.random() * 3),
            timestamp: date.toISOString(),
        });
    }

    return entries;
}
