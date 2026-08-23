Analyze these AI news candidate signals and rank them by importance for discussion on X (Twitter). 

Scoring weights:
- Capability Shift: 25%
- Real World Impact: 20%
- Agent Relevance: 20%
- X Discussion Potential: 15%
- Novelty: 10%
- Source Quality: 10%

Top 5 signals only.

For each selected signal generate:
- title
- what_happened (maximum 3 lines)
- why_it_matters
- eli5
- x_angle
- score (0-100)
- source_url

Output Format (JSON):
{
  "selected_signals": [
    {
      "title": "...",
      "score": ...,
      "what_happened": "...",
      "why_it_matters": "...",
      "eli5": "...",
      "x_angle": "...",
      "source_url": "...",
      "score_breakdown": { ... }
    }
  ]
}