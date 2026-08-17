from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ReleaseDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    HOLD = "hold"


class SecurityIssue(BaseModel):
    issue_text: str
    issue_severity: str
    filename: str
    line_number: str
    code: str
    test_id: str

class SecuritySummary(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    issues: List[SecurityIssue] = []
    scanned_files: int = 0
    duration: float = 0.0


class TestResult(BaseModel):
    __test__ = False
    passed: bool
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    raw_output: str = ""


class CommitData(BaseModel):
    commit_id: str
    author: str
    message: str
    timestamp: str
    files_changed: List[str] = []
    additions: int = 0
    deletions: int = 0


class ReleaseAnalysis(BaseModel):
    commit_data: CommitData
    test_results: TestResult
    security_results: SecuritySummary
    risk_score: float = 0.0
    decision: ReleaseDecision = ReleaseDecision.HOLD
    ai_reasoning: str = ""
    timestamp: str = ""


class WebhookPayload(BaseModel):
    ref: Optional[str] = None
    repository: Optional[Dict[str, Any]] = None
    commits: Optional[List[Dict[str, Any]]] = None
    head_commit: Optional[Dict[str, Any]] = None


class AnalysisRequest(BaseModel):
    repo_url: Optional[str] = ""
    commit_id: Optional[str] = ""
    branch: Optional[str] = "main"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJob(BaseModel):
    """Tracks a single background analysis run. Analysis is slow (clone +
    isolated venv + dependency install + pytest + bandit can take anywhere
    from a few seconds to a couple of minutes), so requests don't block on
    it -- they get a job_id immediately and poll this record for progress.
    """
    job_id: str
    status: JobStatus = JobStatus.PENDING
    repo: str = ""
    branch: str = "main"
    commit_sha: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[ReleaseAnalysis] = None
    error: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
