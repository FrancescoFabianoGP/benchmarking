# Benchmark Design

## Benchmark Name

Working name: **GP Insurance Decision Gauntlet**

## Goal

Evaluate whether the GP decision stack can outperform model-only, RAG-only, and generic agent approaches on insurance decision workflows that require evidence, constraints, repeatability, safe escalation, and rule updates.

## Test 1: Coverage Decision Gauntlet

### Summary

Each system receives the same case packet and must produce a structured decision with evidence and trace.

### Case Types

Start with 25-50 cases across:

- Claims coverage decisions.
- Underwriting eligibility.
- Policy exclusion applicability.
- Endorsement override logic.
- Jurisdiction-specific rules.
- Sublimits, deductibles, and waiting periods.
- Reserving or severity classification.
- Treaty attachment or reinsurance edge cases.
- Missing-information escalation.
- Conflicting facts across documents.

### Case Packet Contents

Each case should contain:

- Claim summary or underwriting request.
- Policy declaration.
- Policy form or relevant policy excerpts.
- Endorsements.
- Exclusions.
- Claim notes or adjuster notes.
- Correspondence.
- Jurisdiction note.
- Structured facts extracted from the packet.
- Optional red-team distractors.

### Gold Labels

Each case needs:

- Gold decision: `approve`, `deny`, `partial`, `price_adjust`, `refer`, or `escalate`.
- Required evidence spans.
- Required constraints.
- Expected trace steps.
- Expected missing-information flags.
- Allowed ambiguities.
- Disallowed reasoning paths.

### Output Contract

Every system should return the same JSON-compatible structure:

```json
{
  "case_id": "case-0001",
  "decision": "approve | deny | partial | price_adjust | refer | escalate",
  "confidence": "low | medium | high",
  "covered_amount": null,
  "reason_codes": [],
  "evidence": [
    {
      "source_id": "policy-form-01",
      "span_id": "p12_l4_l9",
      "claim": "The water backup endorsement applies."
    }
  ],
  "constraints_applied": [
    {
      "constraint_id": "endorsement_overrides_exclusion",
      "result": "satisfied | violated | not_applicable | unknown",
      "evidence_refs": []
    }
  ],
  "missing_information": [],
  "escalation_required": false,
  "trace": [
    "Identified loss event.",
    "Mapped peril to policy coverage.",
    "Checked exclusion.",
    "Checked endorsement override.",
    "Applied sublimit."
  ],
  "final_response": "Short business-readable explanation."
}
```

### Metrics

Core metrics:

- Decision accuracy.
- Hard-constraint violation rate.
- Evidence precision.
- Evidence recall.
- Missing-information escalation accuracy.
- Trace completeness.
- Trace correctness.
- Reproducibility across reruns.
- Latency.
- Cost.

Secondary metrics:

- Over-escalation rate.
- Under-escalation rate.
- Hallucinated policy/rule citation rate.
- Inconsistent amount calculation rate.
- Explanation quality.
- Tool-call efficiency.

### Rerun Protocol

Run each case multiple times per arm. For the first internal run, use 5 reruns. For a defensible benchmark, use 30 reruns.

Track:

- Pass rate.
- Majority decision.
- Decision variance.
- Constraint violation variance.
- Evidence citation variance.
- Cost and latency variance.

## Test 2: Rule Change Shock

### Summary

After baseline runs, introduce one controlled rule change and rerun selected cases.

### Example Rule Changes

- New state-specific notice deadline.
- New endorsement that overrides a common exclusion.
- New sublimit for a peril.
- New underwriting referral threshold.
- New treaty attachment condition.
- New jurisdiction-specific claim handling requirement.

### Measurement

Measure:

- Time to update.
- Number of files/prompts/configs/rules changed.
- Number of affected cases that flip correctly.
- Number of unaffected cases that remain stable.
- Whether the trace cites the new rule.
- Whether any arm leaks stale behavior.

### Why This Test Matters

This is the cleanest proof of ontology and Reasoning Engine value. It tests whether business logic is maintained as explicit, inspectable knowledge or hidden inside prompts, embeddings, and model behavior.

## Competitor Arms

### Arm A: Raw LLM

The model receives the case packet and output schema. No tools. No retrieval beyond the packet.

### Arm B: LLM + RAG

The model can retrieve policy, endorsement, exclusion, and jurisdiction text from a document index.

### Arm C: LLM + Generic Tools

The model can call tools such as:

- `lookup_policy`
- `lookup_claim`
- `lookup_jurisdiction_rule`
- `calculate_limit`
- `retrieve_document_span`

### Arm D: Best Plausible Enterprise Build

A strong competitor simulation: model plus RAG plus tools plus semantic data model plus workflow prompts.

### Arm E: GP Insurance Stack

Talos orchestrates the workflow, uses the ontology to map concepts, calls deterministic Reasoning Engine rules, gathers evidence, records trace, and escalates missing information.

## Initial Case Mix

Recommended 50-case first version:

| Category | Count |
|---|---:|
| Straightforward covered claim | 6 |
| Straightforward denial | 6 |
| Exclusion with endorsement override | 8 |
| Missing information escalation | 8 |
| Jurisdiction-specific rule | 6 |
| Sublimit or deductible calculation | 6 |
| Conflicting documents | 4 |
| Underwriting referral | 3 |
| Treaty/reinsurance edge | 3 |

## First Demo Scorecard

For an executive demo, keep the report simple:

| Arm | Decision Accuracy | Hard Constraint Violations | Evidence F1 | Correct Escalation | Rerun Stability | Avg Cost | Avg Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Raw LLM | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| LLM + RAG | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| LLM + Tools | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Enterprise Agent | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| GP Insurance Stack | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
