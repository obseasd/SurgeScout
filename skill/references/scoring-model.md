# SurgeScout Scoring Model

## Overview

SurgeScout evaluates projects for tokenization potential using 5 weighted dimensions.
Each dimension scores 0-100. The overall score is a weighted average.

## Dimensions

### 1. Market Fit (weight: 25%)
- Is there a real, identifiable user base?
- Does the project solve a clear problem?
- Is the market large enough to sustain a token economy?
- Competitors and differentiation?

**High score (80+):** Clear market need, identified users, growing demand
**Low score (<30):** No clear use case, solution looking for a problem

### 2. Team Signal (weight: 20%)
- Agent/developer reputation on Moltbook
- GitHub activity: commits, stars, contributions
- Past hackathon wins or notable projects
- Community engagement level

**High score (80+):** Active developer, past wins, strong GitHub presence
**Low score (<30):** Anonymous, no history, empty GitHub

### 3. Technical Quality (weight: 25%)
- Is there working code (not just an idea)?
- Deployed smart contracts (verifiable on explorer)?
- Architecture quality and code organization
- Documentation and reproducibility

**High score (80+):** Deployed contracts, clean code, working demo
**Low score (<30):** No code, just a pitch, broken links

### 4. Tokenomics Feasibility (weight: 20%)
- Does a token make sense for this project?
- Clear utility or governance role?
- Revenue model that supports token value?
- Sustainable economics (not just speculation)?

**High score (80+):** Clear token utility, revenue flows, sustainable model
**Low score (<30):** No reason for a token, pure speculation play

### 5. Traction (weight: 10%)
- Moltbook engagement: votes, comments, reposts
- External social proof: X followers, community size
- User adoption signals
- Media coverage or notable mentions

**High score (80+):** Viral buzz, many votes, active community
**Low score (<30):** Zero engagement, no mentions

## Verdict Thresholds

| Score Range | Verdict | Action |
|-------------|---------|--------|
| 75-100 | STRONG_LAUNCH | Recommend immediate token launch on SURGE |
| 50-74 | PROMISING | Worth watching, suggest improvements first |
| 25-49 | NEEDS_WORK | Not ready, provide constructive feedback |
| 0-24 | SKIP | No tokenization potential |

## Notes

- These scores are AI-generated assessments, not financial advice
- Always recommend independent due diligence
- Projects can improve their score by addressing identified weaknesses
- Traction can change rapidly — re-analyze projects periodically
