# GP Insurance Benchmark Handoff

## Purpose

This packet frames a benchmark for the GP insurance decision stack. The goal is not to prove that Talos is "a better Claude." The goal is to test whether GP's stack of components can outperform model-only and generic-agent approaches on governed insurance decisioning.

The stack being tested is:

- Talos for agent orchestration, planning, tool use, evidence gathering, and trace capture.
- GP ontology for formal insurance concepts and relationships.
- GP Reasoning Engine for deterministic rule and constraint evaluation.
- Domain tools for policy lookup, claim-state lookup, jurisdiction logic, endorsement lookup, and scoring.
- Frontier LLMs as language and flexible reasoning components, not the sole source of decision authority.

## Recommended Benchmark Shape

Build a small, defensible custom benchmark first, then optionally supplement it with public agent and insurance datasets.

The two highest-signal tests are:

1. **Coverage Decision Gauntlet**
   - 25-50 curated insurance decision cases for the first version.
   - Each case includes source documents, structured facts, gold decision, required evidence spans, expected constraint trace, and missing-info expectations.
   - Score decision accuracy, hard-constraint violations, evidence quality, trace quality, escalation behavior, latency, and cost.

2. **Rule Change Shock**
   - Introduce a new endorsement, exclusion, state-specific rule, treaty attachment rule, notice deadline, or sublimit.
   - Measure how quickly each system updates, whether affected cases flip correctly, whether unaffected cases remain stable, and whether traces cite the new rule.

## Competitive Ladder

Compare GP against a ladder, not a strawman:

1. Raw GPT/Claude/Gemini with the case packet in context.
2. GPT/Claude/Gemini plus RAG over policy and jurisdiction documents.
3. GPT/Claude/Gemini plus generic tools.
4. Best plausible enterprise agent with tools and a semantic layer.
5. GP insurance stack: including Talos, GP ontology, GP Reasoning Engine, and domain tools.

## Execution Readiness Framing

Keep the first benchmark at the same case scale:

- 25-50 curated or synthetic cases.
- One line of insurance and one product.
- Three to five deterministic rules.
- One rule-change shock.
- Raw LLM, LLM + RAG, and GP insurance stack arms.
- A simple scorecard instead of a polished product UI.

The benchmark can execute quickly once the Reasoning Engine and ontology layer expose a stable API that Talos can call. Until then, the useful work is case/gold-label preparation, output schema finalization, competitor-arm setup, and scorecard design.

## Files In This Packet

- [POSITIONING.md](POSITIONING.md): how to explain the GP stack, including Talos, RE, ontology, tools, and LLM competitors.
- [BENCHMARK_DESIGN.md](BENCHMARK_DESIGN.md): proposed tests, schemas, metrics, and competitor arms.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): implementation plan, team asks, architecture, and API-readiness cut.
- [EXECUTION_CHECKLIST.md](EXECUTION_CHECKLIST.md): decisions, owners, critical path, and minimum inputs.
- [API_CONTRACT.md](API_CONTRACT.md): minimum RE + ontology API shape Talos needs to call.
- [PUBLIC_BENCHMARKS.md](PUBLIC_BENCHMARKS.md): public benchmark candidates and how to use them without overclaiming.
