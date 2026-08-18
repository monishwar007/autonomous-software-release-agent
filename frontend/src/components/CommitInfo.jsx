import React from 'react';

export default function CommitInfo({ commit }) {
    if (!commit) {
        return (
            <div className="glass-panel">
                <div className="glass-panel__head">
                    <div>
                        <div className="glass-panel__title">
                            <span className="material-icons-outlined" style={{ fontSize: 18 }}>commit</span>
                            Latest Commit
                        </div>
                        <div className="glass-panel__sub">Most recent analyzed commit</div>
                    </div>
                </div>
                <div className="empty">
                    <div className="empty__icon">📝</div>
                    <div className="empty__desc">Run an analysis to see commit details</div>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-panel">
            <div className="glass-panel__head">
                <div>
                    <div className="glass-panel__title">
                        <span className="material-icons-outlined" style={{ fontSize: 18 }}>commit</span>
                        Latest Commit
                    </div>
                    <div className="glass-panel__sub">Most recent analyzed commit</div>
                </div>
            </div>
            <div className="commit-info">
                <div className="commit-hash-row">
                    <span className="commit-hash">#{commit.commit_id}</span>
                    <span className="commit-author">by {commit.author}</span>
                </div>
                <p className="commit-message">{commit.message}</p>
                <div className="commit-stats">
                    <span className="commit-stat--add">+{commit.additions || 0} additions</span>
                    <span className="commit-stat--del">-{commit.deletions || 0} deletions</span>
                    <span>{commit.files_changed?.length || 0} files changed</span>
                </div>
                {commit.files_changed?.length > 0 && (
                    <div className="commit-files">
                        {commit.files_changed.slice(0, 5).map((f, i) => (
                            <span className="commit-file" key={i}>
                                <span className="material-icons-outlined" style={{ fontSize: 14, opacity: 0.4 }}>description</span>
                                {f}
                            </span>
                        ))}
                        {commit.files_changed.length > 5 && (
                            <span style={{ fontSize: 11, color: 'var(--text-muted)', paddingLeft: 20 }}>
                                +{commit.files_changed.length - 5} more files
                            </span>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
