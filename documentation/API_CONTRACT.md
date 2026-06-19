# API Contract Sketch

## Purpose

The benchmark becomes executable once Talos can call the Reasoning Engine and ontology layer through a stable contract. This document sketches the minimum contract needed for the first benchmark.

## Design Principle

The API should not return only a decision. It should return a decision plus the explicit rule results, ontology mappings, evidence references, missing-information gates, and trace steps that explain the decision.

## Minimal Request

```json
{
  "case_id": "case-0001",
  "rule_bundle_id": "gp-property-v0",
  "ontology_version": "insurance-core-v0",
  "decision_task": "coverage_decision",
  "structured_facts": {
    "loss_date": "2026-01-14",
    "notice_date": "2026-01-18",
    "jurisdiction": "TX",
    "policy_id": "policy-001",
    "claim_id": "claim-001",
    "peril": "water_backup",
    "claimed_amount": 42000
  },
  "evidence_refs": [
    {
      "source_id": "policy-form-01",
      "span_id": "p12_l4_l9",
      "text": "..."
    }
  ]
}
```

## Minimal Response

```json
{
  "case_id": "case-0001",
  "rule_bundle_id": "gp-property-v0",
  "ontology_version": "insurance-core-v0",
  "decision": "approve | deny | partial | refer | escalate",
  "decision_reasons": [
    {
      "reason_code": "ENDORSEMENT_OVERRIDES_EXCLUSION",
      "summary": "The endorsement restores limited coverage for the otherwise excluded peril.",
      "evidence_refs": ["policy-form-01:p12_l4_l9"]
    }
  ],
  "constraints": [
    {
      "constraint_id": "exclusion_applies_to_peril",
      "result": "satisfied | violated | not_applicable | unknown",
      "explanation": "The base policy exclusion applies to water backup.",
      "evidence_refs": ["policy-form-01:p10_l2_l7"]
    },
    {
      "constraint_id": "endorsement_modifies_exclusion",
      "result": "satisfied",
      "explanation": "The endorsement modifies the exclusion for this peril.",
      "evidence_refs": ["endorsement-01:p2_l1_l8"]
    }
  ],
  "missing_information": [],
  "amounts": {
    "claimed_amount": 42000,
    "covered_amount": 10000,
    "deductible": 1000,
    "sublimit": 10000
  },
  "ontology_mappings": [
    {
      "input": "water_backup",
      "concept_id": "Peril:WaterBackup",
      "confidence": "high"
    }
  ],
  "trace": [
    "Mapped loss event to peril.",
    "Checked base coverage.",
    "Checked exclusion.",
    "Checked endorsement override.",
    "Applied sublimit."
  ],
  "errors": []
}
```

## Required Behavior

The API should:

- Be deterministic for the same input, rule bundle, and ontology version.
- Include rule bundle and ontology version in every response.
- Distinguish `deny` from `escalate`.
- Return `unknown` or `escalate` when required facts are missing.
- Never silently ignore an unmapped ontology concept.
- Return evidence references alongside constraint results.
- Return machine-readable reason codes.
- Return enough trace data for the benchmark scorer.

## Error Handling

Use explicit error types:

| Error | Meaning |
|---|---|
| `MISSING_REQUIRED_FACT` | A needed fact is absent |
| `UNMAPPED_CONCEPT` | Input cannot be mapped to ontology |
| `UNKNOWN_RULE_BUNDLE` | Rule bundle id is invalid |
| `UNSUPPORTED_DECISION_TASK` | Task is outside current RE scope |
| `CONFLICTING_FACTS` | Structured facts conflict materially |
| `INTERNAL_REASONING_ERROR` | System error, not a business result |

## Talos Integration Need

Talos should be able to call the API as one tool:

```text
evaluate_insurance_decision(
  case_id,
  decision_task,
  structured_facts,
  evidence_refs,
  rule_bundle_id,
  ontology_version
)
```

Talos remains responsible for:

- Reading the case packet.
- Retrieving source documents and spans.
- Extracting candidate facts.
- Calling the RE + ontology API.
- Presenting the decision and trace.
- Recording the benchmark output schema.

The Reasoning Engine and ontology layer remain responsible for:

- Mapping facts to formal concepts.
- Applying deterministic constraints.
- Returning rule-level results.
- Returning missing-information gates.
- Returning versioned trace output.
