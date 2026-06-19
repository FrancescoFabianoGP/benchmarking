# Execution Checklist

## Definition Of Done

The first benchmark is done when the team can run the same 25-50 cases through each benchmark arm and produce a scorecard showing:

- Decision accuracy.
- Hard-constraint violation rate.
- Evidence precision/recall or evidence match score.
- Missing-information escalation accuracy.
- Trace completeness/correctness.
- Rerun stability.
- Cost and latency.
- Rule-change shock results.

## Required Decisions

Make these decisions before implementation expands:

- Initial insurance line and product.
- Case source: synthetic, anonymized real cases, or hybrid.
- Case count target within the 25-50 range.
- Competitor arms for the first run.
- Model providers and model versions.
- Whether RAG is shared across arms or separately configured.
- Which rules are canonical enough for deterministic evaluation.
- Where ontology artifacts live.
- Where benchmark artifacts live outside GitHub, if needed.
- Who can approve gold labels.

## Required Owners

Assign one accountable owner for each:

| Area | Owner Needed | Output |
|---|---|---|
| Benchmark lead | Yes | Scope, sequencing, final decisions |
| Insurance SME | Yes | Case facts, gold labels, rule realism |
| Ontology | Yes | Concept model and mappings |
| Reasoning Engine | Yes | Deterministic rule API and trace output |
| Talos | Yes | Tool integration and run path |
| Evaluation harness | Yes | Runners, scoring, reports |
| Data/privacy | Yes | Anonymization and handling rules |

## Critical Path

1. Pick one product line and rule family.
2. Finalize the output schema.
3. Draft 25-50 cases and gold labels.
4. Expose RE + ontology API for Talos.
5. Build raw LLM and LLM + RAG baselines.
6. Build GP insurance stack runner.
7. Run each arm with fixed settings.
8. Run rule-change shock.
9. Produce scorecard and case-level diffs.

## Things To Avoid

- Letting the ontology become a broad enterprise modeling project before the first benchmark runs.
- Creating cases without gold evidence spans.
- Using different document access across competitor arms without documenting the difference.
- Scoring prose quality instead of decision reliability.
- Letting model choice become the headline instead of stack behavior.
- Making the demo UI the dependency for executing the benchmark.

## Minimum Inputs Needed From The Team

- 25-50 case packets.
- Gold decisions for each case.
- Gold evidence spans for each case.
- Three to five deterministic rules.
- One explicit rule-change scenario.
- API endpoint or callable function for RE + ontology evaluation.
- Model credentials and allowed model list.
- Agreement on where run artifacts should be stored.

## Recommended First Rule Family

Choose a rule family where the GP stack should naturally beat model-only approaches:

- Exclusion plus endorsement override.
- Missing required document blocks decision.
- Jurisdiction modifies notice deadline.
- Sublimit caps payout.
- Underwriting referral threshold.

The best first choice is probably **exclusion plus endorsement override** because it is intuitive, common, easy to explain, and exposes why traceable rule application matters.
