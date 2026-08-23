Your task: Analyze the following AI signal and decide whether it should be kept for deeper analysis or discarded as noise.

Signal Details:
- Title: {{title}}
- Source: {{source}}
- Summary: {{summary}}

Filter Criteria (Score each 0-1):
1. Agent Relevance
2. Capability Change
3. Real-World Impact
4. Security Implications
5. Unexpected Behavior
6. X Discussion Potential

Output (JSON only):
{
  "decision": "KEEP" | "DISCARD",
  "reason": "explanation",
  "confidence": 0.0-1.0,
  "scores": { ... }
}