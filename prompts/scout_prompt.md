Analyze these AI news candidate signals and rank them by importance for discussion on X (Twitter). 

Scoring weights:
- Capability Shift: 25%
- Real World Impact: 20%
- Agent Relevance: 20%
- X Discussion Potential: 15%
- Novelty: 10%
- Source Quality: 10%

CRITICAL INSTRUCTIONS:
1. Base your analysis STRICTLY and ONLY on the provided signal title and snippet data.
2. DO NOT invent facts, extrapolate unsupported claims, or fabricate details.
3. DO NOT use generic fallback sentences (such as "عملکرد بهتر نسبت به نسخه‌های قبلی", "افزایش سرعت توسعه عامل‌های هوشمند", or generic filler). Every description must be specific to the actual news item provided.
4. If the provided information is insufficient to evaluate a specific aspect, explicitly state so in Persian (e.g., "جزئیات کافی در متن موجود نیست").
5. You MUST include the exact `url_hash` and `source_url` provided in the candidate input for each selected signal. Do not generate fake or placeholder URLs.

Top 5 signals only.

For each selected signal generate:
- url_hash
- title
- what_happened (maximum 3 lines, specific to the provided text)
- why_it_matters
- eli5
- x_angle
- score (0-100)
- source_url (must match candidate source_url exactly)

Output Format (JSON):
{
  "selected_signals": [
    {
      "url_hash": "...",
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