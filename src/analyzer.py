"""LLM-powered project analyzer — scores projects for tokenization potential."""

import json
import logging
import re
from typing import Optional

from . import config

log = logging.getLogger("surgescout.analyzer")

# ---------------------------------------------------------------------------
# Scoring model
# ---------------------------------------------------------------------------

ANALYSIS_SYSTEM_PROMPT = """You are SurgeScout, an AI deal-flow analyst for Internet Capital Markets (ICM).
You evaluate projects discovered on Moltbook (the AI agent social network) for their
tokenization potential on the SURGE launchpad.

Your job: analyze a project and produce a structured JSON assessment.

## Scoring Dimensions (each 0-100)

1. **market_fit** — Is there a real market need? Who are the users?
2. **team_signal** — Agent reputation, GitHub activity, past projects, community engagement
3. **technical_quality** — Code quality, architecture, deployed contracts, working demo
4. **tokenomics_feasibility** — Can this project meaningfully tokenize? Revenue model? Utility?
5. **traction** — Votes, comments, community buzz, social proof on Moltbook

## Output Format (strict JSON)

```json
{
  "project_name": "...",
  "summary": "2-3 sentence summary of what the project does",
  "scores": {
    "market_fit": 0-100,
    "team_signal": 0-100,
    "technical_quality": 0-100,
    "tokenomics_feasibility": 0-100,
    "traction": 0-100
  },
  "overall_score": 0-100,
  "verdict": "STRONG_LAUNCH | PROMISING | NEEDS_WORK | SKIP",
  "tokenomics_advice": {
    "suggested_name": "$TICKER",
    "suggested_supply": "1000000",
    "bonding_curve": "linear | exponential | sigmoid",
    "initial_price_usd": "0.001",
    "rationale": "Why these parameters"
  },
  "risks": ["risk 1", "risk 2"],
  "strengths": ["strength 1", "strength 2"],
  "recommendation": "Detailed recommendation for the creator"
}
```

Be honest and critical. Not every project deserves a token. Only recommend STRONG_LAUNCH
for projects with genuine utility, traction, and a clear tokenomics model.
"""


def _get_llm_client():
    """Get the appropriate LLM client."""
    if config.AI_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        import anthropic
        return "anthropic", anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    elif config.OPENAI_API_KEY:
        import openai
        return "openai", openai.OpenAI(api_key=config.OPENAI_API_KEY)
    else:
        raise RuntimeError("No API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")


def _call_llm(system: str, user: str) -> str:
    """Call the LLM and return the response text."""
    provider, client = _get_llm_client()

    if provider == "anthropic":
        model = config.AI_MODEL or "claude-sonnet-4-20250514"
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text
    else:
        model = config.AI_MODEL or "gpt-4o"
        resp = client.chat.completions.create(
            model=model,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code block
    m = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding first { ... }
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {"error": "Failed to parse LLM response", "raw": text[:500]}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_project(project: dict) -> dict:
    """Analyze a single project and return structured assessment.

    Args:
        project: dict with keys like title, body, author, github_urls,
                 token_mentions, votes, comments, etc.

    Returns:
        Structured analysis dict with scores, verdict, and tokenomics advice.
    """
    # Build context for the LLM
    context_parts = [
        f"**Project Title:** {project.get('title', 'Unknown')}",
        f"**Author:** {project.get('author', 'Unknown')}",
        f"**Description:**\n{project.get('body', 'No description')}",
    ]

    if project.get("github_urls"):
        context_parts.append(f"**GitHub:** {', '.join(project['github_urls'])}")
    if project.get("token_mentions"):
        context_parts.append(f"**Token Mentions:** {', '.join('$' + t for t in project['token_mentions'])}")
    if project.get("votes"):
        context_parts.append(f"**Votes:** {project['votes']}")
    if project.get("comments"):
        context_parts.append(f"**Comments:** {project['comments']}")
    if project.get("url"):
        context_parts.append(f"**URL:** {project['url']}")

    user_msg = (
        "Analyze this project discovered on Moltbook for tokenization potential on SURGE:\n\n"
        + "\n".join(context_parts)
        + "\n\nProvide your analysis as the specified JSON format."
    )

    log.info(f"Analyzing project: {project.get('title', '?')}")

    try:
        raw = _call_llm(ANALYSIS_SYSTEM_PROMPT, user_msg)
        analysis = _extract_json(raw)
        analysis["_source_project_id"] = project.get("id", "")
        analysis["_analyzed_at"] = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()
        return analysis
    except Exception as e:
        log.error(f"Analysis failed: {e}")
        return {
            "error": str(e),
            "project_name": project.get("title", "Unknown"),
            "overall_score": 0,
            "verdict": "ERROR",
        }


def analyze_batch(projects: list[dict], min_score: int = 0) -> list[dict]:
    """Analyze multiple projects and return sorted results.

    Args:
        projects: List of project dicts from the scout.
        min_score: Only return projects scoring above this threshold.

    Returns:
        List of analysis dicts, sorted by overall_score descending.
    """
    import time

    results = []
    for i, proj in enumerate(projects):
        log.info(f"Analyzing project {i+1}/{len(projects)}: {proj.get('title', '?')[:50]}")

        # Try up to 2 times per project (retry on rate limit)
        analysis = None
        for attempt in range(2):
            analysis = analyze_project(proj)
            if not analysis.get("error"):
                break
            err = str(analysis.get("error", ""))
            if "429" in err or "rate" in err.lower():
                log.warning(f"Rate limited, waiting 10s before retry...")
                time.sleep(10)
            else:
                break  # Non-rate-limit error, don't retry

        score = analysis.get("overall_score", 0)
        if analysis.get("error"):
            log.warning(f"Analysis error for {proj.get('title', '?')}: {analysis.get('error')}")
        if score >= min_score:
            results.append(analysis)
        # Rate limit: wait 3s between API calls to avoid 429 errors
        if i < len(projects) - 1:
            time.sleep(3)

    results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    log.info(f"Batch analysis complete: {len(results)}/{len(projects)} above threshold {min_score}")
    return results


def generate_launch_report(analysis: dict) -> str:
    """Generate a human-readable launch report from an analysis."""
    if analysis.get("error"):
        return f"Analysis failed: {analysis['error']}"

    scores = analysis.get("scores", {})
    verdict = analysis.get("verdict", "UNKNOWN")
    token_advice = analysis.get("tokenomics_advice", {})

    verdict_emoji = {
        "STRONG_LAUNCH": "[LAUNCH]",
        "PROMISING": "[WATCH]",
        "NEEDS_WORK": "[WAIT]",
        "SKIP": "[SKIP]",
    }.get(verdict, "[?]")

    lines = [
        f"# {verdict_emoji} SurgeScout Analysis: {analysis.get('project_name', '?')}",
        "",
        f"**Overall Score:** {analysis.get('overall_score', 0)}/100 — {verdict}",
        "",
        f"> {analysis.get('summary', 'No summary')}",
        "",
        "## Scores",
        f"- Market Fit: {scores.get('market_fit', 0)}/100",
        f"- Team Signal: {scores.get('team_signal', 0)}/100",
        f"- Technical Quality: {scores.get('technical_quality', 0)}/100",
        f"- Tokenomics Feasibility: {scores.get('tokenomics_feasibility', 0)}/100",
        f"- Traction: {scores.get('traction', 0)}/100",
        "",
    ]

    if token_advice and verdict in ("STRONG_LAUNCH", "PROMISING"):
        lines.extend([
            "## Tokenomics Recommendation",
            f"- Ticker: {token_advice.get('suggested_name', '?')}",
            f"- Supply: {token_advice.get('suggested_supply', '?')}",
            f"- Bonding Curve: {token_advice.get('bonding_curve', '?')}",
            f"- Initial Price: ${token_advice.get('initial_price_usd', '?')}",
            f"- Rationale: {token_advice.get('rationale', '')}",
            "",
        ])

    if analysis.get("strengths"):
        lines.append("## Strengths")
        for s in analysis["strengths"]:
            lines.append(f"- {s}")
        lines.append("")

    if analysis.get("risks"):
        lines.append("## Risks")
        for r in analysis["risks"]:
            lines.append(f"- {r}")
        lines.append("")

    if analysis.get("recommendation"):
        lines.extend(["## Recommendation", analysis["recommendation"], ""])

    lines.append("---")
    lines.append("*Powered by SurgeScout — AI Deal Flow for Internet Capital Markets*")

    return "\n".join(lines)
