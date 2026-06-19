# Positioning: GP Insurance Stack vs LLMs

## One-Sentence Position

The GP insurance decision stack uses Talos for orchestration, GP ontology for structured insurance knowledge, the Reasoning Engine for deterministic constraints, and LLMs for language understanding and flexible reasoning.

## What We Are Not Claiming

We should not position this as:

> Talos is smarter than Claude.

That framing is too narrow and creates the wrong comparison. Claude, GPT, and Gemini are foundation models. Talos can use foundation models. The GP stack is not just a model; it is a governed enterprise decision environment around models.

## What We Are Claiming

We should position this as:

> High-stakes insurance decisions require more than a foundation model. They require evidence retrieval, formal business semantics, deterministic constraints, auditable traces, stable rule updates, and safe escalation. The GP stack demonstrates that GP can combine agent flexibility with governed insurance reasoning.

## Stack Roles

| Component | Role |
|---|---|
| Talos | Agent orchestration, planning, tool use, data/document access, evidence gathering, trace capture |
| GP Ontology | Formal model of policy, peril, exclusion, endorsement, claimant, jurisdiction, treaty, limits, dates, and obligations |
| GP Reasoning Engine | Deterministic evaluation of rules, constraints, eligibility, overrides, missing information, and decision gates |
| LLM | Language interface, extraction aid, flexible reasoning, explanation drafting, and tool-use planner |
| RAG | Retrieval layer for relevant documents and passages |
| Domain Tools | Canonical APIs for policy lookup, claim lookup, jurisdiction lookup, rule lookup, document lookup, and scoring |

## Competitive Ladder

The benchmark should compare against increasingly capable alternatives:

| Arm | Description | Why It Matters |
|---|---|---|
| Raw LLM | GPT/Claude/Gemini receives the case packet directly | Tests model-only reasoning |
| LLM + RAG | Model retrieves policy and jurisdiction docs | Tests common enterprise chatbot architecture |
| LLM + Tools | Model can call claim, policy, and rule tools | Tests generic agent approach |
| Enterprise Semantic Agent | Best plausible Fabric/Databricks-style agent with semantic layer | Tests the strongest competitor narrative |
| GP Insurance Stack | Includes Talos, ontology, Reasoning Engine, and domain tools | Tests GP's differentiated decision stack |

## Why This Difference Matters In Insurance

Insurance decisions are not just question answering. They require:

- Correct application of exclusions, endorsements, sublimits, deductibles, waiting periods, notice rules, and jurisdiction-specific obligations.
- Stable behavior across reruns.
- Refusal or escalation when required facts are missing.
- Evidence traceability to policy language, claim facts, and rule logic.
- Fast updates when rules change.
- Auditability for internal review and regulator-facing workflows.

This is exactly where a model-only system is weakest and where a governed agent plus ontology plus deterministic reasoning should show a measurable advantage.

## Suggested Talk Track

The GP stack is not competing with Claude as a chatbot. It is competing with the idea that a chatbot plus retrieval is enough for enterprise insurance decisions. Talos is one GP component in that stack.

The proof point is not whether the answer sounds good. The proof point is whether the system:

- reaches the correct decision,
- cites the right evidence,
- obeys hard constraints,
- escalates missing information,
- updates cleanly when a rule changes,
- and produces a reproducible trace.

## Headline Metric

Lead with **hard-constraint violation rate**, not subjective answer quality.

A polished denial or approval that violates an exclusion, endorsement, jurisdiction rule, or missing-information gate should be scored as a failure even if the prose is persuasive.
