# neatlogs trace: drift demo #2 (`interlock.land`)

Pulled from neatlogs through the neatlogs MCP (`scripts/neatlogs_mcp.py`, `get_trace_context`), not a screenshot.

- trace_id `01f314416618f766c98ba1f50110a89c` · status **success** · 154s · **244 spans** (208 tool calls, 4 LLM calls)
- detections fired on this trace (neatlogs detections we created for Interlock): Interlock: acceptance test arbitrated, Interlock: intent test repaired
- Note: neatlogs reports 0 tokens/cost at trace level because the LiteLLM model names (`claude-haiku`, `nova-*`) aren't in its price table. Interlock records the real cost from LiteLLM's `x-litellm-response-cost` header on its `llm.*` spans (`interlock.cost_usd`).

## Span tree (tool calls aggregated per parent)

- `interlock.land` (workflow, 154.1s) · tools: tool.git×4, tool.pytest×1
  - `plan` (agent_action, 2.0s) · tools: tool.git×3, tool.entire×3
  - `land.agent/issue-4` (chain, 4.6s) · tools: tool.git×10, tool.pytest×1
  - `land.agent/issue-5` (chain, 22.8s) · tools: tool.git×22, tool.pytest×2
    - `interlock.prove` (workflow, 8.5s) · tools: tool.git×13, tool.pytest×1
      - `planner` (agent_action, 2.7s) · tools: tool.entire×7
      - `intent` (agent_action, 1.3s) · tools: tool.git×2, tool.entire×7
      - `cleared_by_graph` (chain, 0.0s)
    - `drift` (agent_action, 4.9s) · tools: tool.git×6, tool.entire×19
  - `land.agent/issue-1` (chain, 120.9s) · tools: tool.git×13, tool.pytest×1
    - `interlock.prove` (workflow, 44.3s) · tools: tool.git×14, tool.pytest×1
      - `planner` (agent_action, 5.1s) · tools: tool.entire×20
      - `resolver` (agent_action, 3.9s) · tools: tool.git×3
        - `llm.resolve_conflict` (chain, 3.8s)
          - `claude-sonnet-4.6` (llm, 3.8s)
      - `intent` (agent_action, 2.9s) · tools: tool.git×2, tool.entire×15
      - `prove.agent/issue-1` (agent_action, 8.1s) · tools: tool.git×2, tool.pytest×2
        - `synthesize.claude-haiku` (chain, 3.6s) · tools: tool.pytest×1
          - `llm.synthesize_test` (chain, 0.0s)
      - `prove.interlock-drift` (agent_action, 19.7s) · tools: tool.git×2, tool.pytest×2
        - `synthesize.claude-haiku` (chain, 8.8s) · tools: tool.pytest×2
          - `llm.synthesize_test` (chain, 0.0s)
          - `recover.repair_test` (chain, 4.6s)
            - `llm.repair_test` (chain, 4.6s)
              - `claude-haiku` (llm, 4.6s)
        - `verify.confirm` (chain, 9.8s) · tools: tool.pytest×2
          - `llm.confirm_intent` (chain, 8.9s)
            - `claude-sonnet-4.6` (llm, 8.9s)
    - `interlock.resolve` (workflow, 72.7s) · tools: tool.git×2
      - `decide` (agent_action, 0.0s)
      - `llm.summarize_change` (chain, 0.0s)
      - `round.1` (chain, 72.6s) · tools: tool.entire×1, tool.git×8, tool.pytest×4
        - `agent_message` (agent_action, 45.1s) · tools: tool.claude×1
        - `arbitrate.reexpress` (agent_action, 16.9s) · tools: tool.git×7, tool.pytest×2
          - `llm.reexpress_acceptance` (chain, 9.4s)
            - `claude-sonnet-4.6` (llm, 9.4s)
