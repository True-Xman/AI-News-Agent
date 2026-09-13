# AI Signal Scout: Sieve

Classify every supplied AI-news candidate as `KEEP` or `DISCARD` for deeper analysis.

Score each criterion from 0.0 through 1.0:

1. `agent_relevance`
2. `capability_change`
3. `real_world_impact`
4. `security_implications`
5. `unexpected_behavior`
6. `discussion_potential`

Return JSON only: one array with exactly one object for every input candidate. Preserve each input `url_hash` exactly. Do not add, omit, or duplicate candidates. Every `reason` must be concise English even when the source text is not English.

Each object must have this exact shape:

```json
{
  "url_hash": "input hash",
  "decision": "KEEP",
  "reason": "Concise English reason",
  "confidence": 0.85,
  "scores": {
    "agent_relevance": 0.9,
    "capability_change": 0.8,
    "real_world_impact": 0.7,
    "security_implications": 0.2,
    "unexpected_behavior": 0.5,
    "discussion_potential": 0.8
  }
}
```
