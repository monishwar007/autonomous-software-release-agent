import json
from app.utils.logger import logger
from app.config import GROQ_API_KEY, GROQ_MODEL

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False


def get_ai_evaluation(commit_data: dict, test_results: dict, security_results: dict) -> str:
    """Use Groq LLM to evaluate release readiness."""
    if not HAS_GROQ or not GROQ_API_KEY:
        logger.warning("Groq not available, using rule-based evaluation")
        return _rule_based_evaluation(commit_data, test_results, security_results)

    try:
        client = Groq(api_key=GROQ_API_KEY)

        prompt = f"""Analyze the following release data and provide a release readiness assessment.

Commit Data:
- Author: {commit_data.get('author', 'Unknown')}
- Message: {commit_data.get('message', '')}
- Files Changed: {len(commit_data.get('files_changed', []))}
- Lines Added: {commit_data.get('additions', 0)}
- Lines Deleted: {commit_data.get('deletions', 0)}

Test Results:
- All Passed: {test_results.get('passed', False)}
- Total Tests: {test_results.get('total_tests', 0)}
- Passed: {test_results.get('passed_tests', 0)}
- Failed: {test_results.get('failed_tests', 0)}

Security Scan:
- Critical Issues: {security_results.get('critical', 0)}
- High Issues: {security_results.get('high', 0)}
- Medium Issues: {security_results.get('medium', 0)}
- Low Issues: {security_results.get('low', 0)}

You MUST respond with ONLY a valid JSON object (no extra text, no markdown, no code fences) with exactly these fields:
- "decision": one of "approve", "reject", or "hold"
- "risk_score": a number from 0.0 to 1.0
- "reasoning": a detailed explanation string
- "recommendations": an array of action item strings
"""

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a DevOps release assessment AI. You MUST return ONLY valid JSON with no additional text, no markdown formatting, and no code fences. Just the raw JSON object."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=1024,
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from AI")
            return _rule_based_evaluation(commit_data, test_results, security_results)
            
        raw = content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines).strip()

        # Validate it's valid JSON
        json.loads(raw)
        logger.info(f"Groq AI evaluation successful using {GROQ_MODEL}")
        return raw

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return _rule_based_evaluation(commit_data, test_results, security_results)


def _rule_based_evaluation(commit_data: dict, test_results: dict, security_results: dict) -> str:
    """Fallback rule-based evaluation when AI is unavailable."""
    risk_score = 0.0

    # Test failures increase risk
    if not test_results.get("passed", False):
        risk_score += 0.4

    failed_tests = test_results.get("failed_tests", 0)
    total_tests = test_results.get("total_tests", 1)
    if total_tests > 0:
        risk_score += (failed_tests / total_tests) * 0.2

    # Security issues increase risk
    critical = security_results.get("critical", 0)
    high = security_results.get("high", 0)
    medium = security_results.get("medium", 0)

    risk_score += critical * 0.15
    risk_score += high * 0.08
    risk_score += medium * 0.03

    # Large changes increase risk
    files_changed = len(commit_data.get("files_changed", []))
    if files_changed > 10:
        risk_score += 0.1
    elif files_changed > 5:
        risk_score += 0.05

    # Sensitive modules increase risk
    sensitive_modules = ["auth", "payment", "security", "database", "migration"]
    for f in commit_data.get("files_changed", []):
        for module in sensitive_modules:
            if module in f.lower():
                risk_score += 0.05

    risk_score = min(risk_score, 1.0)

    # Make decision
    if risk_score >= 0.7 or critical > 0:
        decision = "reject"
        reasoning = "High risk detected. Critical security issues or significant test failures require attention before release."
    elif risk_score >= 0.4:
        decision = "hold"
        reasoning = "Moderate risk detected. Some concerns need review before proceeding with the release."
    else:
        decision = "approve"
        reasoning = "Low risk. All tests pass and no critical security issues found. Safe to proceed with release."

    recommendations = []
    if critical > 0:
        recommendations.append("Fix all critical security vulnerabilities immediately")
    if high > 0:
        recommendations.append(f"Address {high} high-severity security issues")
    if failed_tests > 0:
        recommendations.append(f"Fix {failed_tests} failing tests before release")
    if files_changed > 10:
        recommendations.append("Consider breaking this into smaller releases due to large changeset")
    if not recommendations:
        recommendations.append("No immediate action required. Proceed with standard release process.")

    result = {
        "decision": decision,
        "risk_score": round(risk_score, 2),
        "reasoning": reasoning,
        "recommendations": recommendations,
    }

    return json.dumps(result, indent=2)
