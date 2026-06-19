# Public Benchmark Candidates

## How To Use Public Benchmarks

Public benchmarks are useful for credibility and calibration, but they should not replace the custom GP Insurance Decision Gauntlet.

Use public benchmarks to show:

- The GP stack can participate in known insurance or agent reliability tasks.
- GP is not only testing against a self-authored dataset.
- The team understands where model-only systems are already strong.

Use the custom benchmark to show:

- deterministic constraint adherence,
- ontology value,
- rule-change behavior,
- auditable insurance traces,
- and governed decisioning.

## Candidate: Insurance AI Reliability Benchmark

Link: https://huggingface.co/datasets/pashas/insurance-ai-reliability-benchmark

Best use:

- Public smoke test for insurance conversational reliability.
- Routing, claim intake, claim status, policy inquiry, escalation, compliance flags, error recovery, and edge cases.

How the GP stack could run it:

- Treat each scenario as a case.
- Require structured output for intent, routing, required action, compliance flags, and response.
- Compare the GP stack against raw LLM and LLM + RAG.

Limitations:

- It is closer to operational routing and conversational guardrails than full coverage decisioning.
- It will not fully prove ontology or Reasoning Engine value by itself.

## Candidate: Galileo Agent Leaderboard v2

Link: https://huggingface.co/datasets/galileo-ai/agent-leaderboard-v2

Best use:

- Public agent/tool-use comparison.
- Useful for showing that the GP stack can compete in a broader agentic workflow framing.

How the GP stack could run it:

- Adapt the insurance-sector rows as generic agent tasks.
- Compare tool-use planning, final answer correctness, and operational reliability.

Limitations:

- Small insurance slice.
- Not designed around deep insurance policy logic, deterministic constraints, or rule-change shock.

## Candidate: Bitext Insurance LLM Chatbot Training Dataset

Link: https://huggingface.co/datasets/bitext/Bitext-insurance-llm-chatbot-training-dataset

Best use:

- Intent classification.
- Chatbot baseline.
- Synthetic paraphrase generation.
- Training or testing simple insurance support flows.

Limitations:

- Not a strong benchmark for coverage decisions, evidence spans, or ontology-backed reasoning.
- Better as supporting data than as the headline evaluation.

## Candidate: INS-MMBench

Link: https://github.com/FDU-INS/INS-MMBench

Best use:

- Phase-two multimodal claims demo.
- Auto damage, property damage, health, or agriculture scenarios with images plus text.

Limitations:

- More about visual insurance question answering than governed policy decisioning.
- Adds multimodal complexity before the core reasoning story is proven.

## Candidate: tau-bench Style

Link: https://github.com/sierra-research/tau-bench

Best use:

- Design inspiration for the custom GP benchmark.
- tau-bench-style tasks evaluate agents that must follow policy, interact with tools, maintain state, and complete workflows.

How to apply:

- Build an insurance domain with policies, claim records, tools, user messages, and expected final state.
- Measure pass rate and consistency over repeated trials.

Limitations:

- The public benchmark domains do not directly cover the insurance decision logic we need.
- The value is the benchmark pattern, not the exact dataset.

## Recommendation

For a first public-plus-custom story:

1. Run a small public reliability benchmark to show basic insurance agent competence.
2. Build the GP Insurance Decision Gauntlet to show GP's differentiated stack.
3. Add a rule-change shock test to make ontology and Reasoning Engine value obvious.
