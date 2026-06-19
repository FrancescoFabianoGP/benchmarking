# Implementation Plan

## Recommended Project Placement

Use a split architecture:

- **Talos repo:** insurance profile, demo UX, blueprints, and Talos-facing tools.
- **Reasoning Engine repo:** deterministic insurance rule evaluation and solver-backed logic.
- **Ontology location:** wherever the team already maintains GP ontology artifacts; expose a stable schema/API to the benchmark.
- **New benchmark harness:** a separate package or repo for cases, gold labels, runners, score calculations, and reports.

Do not bury the benchmark harness entirely inside Talos. The benchmark needs to run competitors, reruns, scoring, and reports independently.

## Minimal Architecture

```text
cases/
  case-0001/
    packet.json
    docs/
    gold.json
    adversarial.json

harness/
  runners/
    raw_llm_runner
    rag_runner
    generic_tools_runner
    talos_gp_stack_runner
  scoring/
    decision_score
    evidence_score
    constraint_score
    trace_score
    cost_latency_score
  reports/
    scorecard
    case_diff
    rule_change_report

talos_gp_stack/
  talos_profile
  talos_tools
  ontology_mapping
  reasoning_engine_client
```

## Workstream 0: Alignment

Decisions:

- Which line of insurance to use first.
- Whether cases are synthetic, anonymized real cases, or hybrid.
- Which rules are canonical enough to encode.
- Where the ontology lives.
- Which competitor arms to include in the first run.
- Which model providers are allowed.

Deliverables:

- Final case schema.
- Final output schema.
- First scorecard template.
- Ownership map.

## Workstream 1: Thin Benchmark Harness

Build:

- Case loader.
- Output validator.
- Scoring skeleton.
- Raw LLM runner.
- Report generator.
- Initial target case set.

Goal:

Prove the evaluation loop works before deep integration, using the same 25-50 case target rather than creating a separate smaller benchmark.

## Workstream 2: Talos Integration

Build:

- Talos runner that can process one benchmark case.
- Tool interface for retrieving source docs and structured facts.
- Initial ontology mapping for the chosen insurance domain.
- Initial Reasoning Engine call for a few deterministic constraints.
- Trace output mapped back to the benchmark schema.

Goal:

Run the target case set through raw LLM, LLM + RAG, and the GP insurance stack.

## Workstream 3: Rule Change Shock

Build:

- Versioned rule bundle.
- One controlled rule update.
- Affected/unaffected case set.
- Update-time tracking.
- Rule-change report.

Goal:

Show that GP updates explicit business logic more reliably than prompt/RAG-only systems.

## Workstream 4: Demo Report

Build:

- 50-case scorecard.
- Case-by-case diff viewer or static report.
- Top failure examples.
- Rule-change before/after report.
- GP stack trace walkthrough.

Goal:

Make the story legible to buyers and internal stakeholders.

## Team Asks

### Insurance SME

- Pick initial line of insurance.
- Author or review 25-50 cases.
- Validate gold decisions.
- Identify realistic exclusions, endorsements, and jurisdiction rules.

### Ontology Lead

- Define minimum concept model.
- Map case facts to ontology concepts.
- Identify required relations and constraints.
- Decide versioning strategy.

### Reasoning Engine Lead

- Encode initial deterministic rules.
- Return machine-readable constraint results.
- Support rule-bundle versioning.
- Provide trace output.

### Talos Engineer

- Create insurance profile or demo configuration.
- Expose benchmark runner through Talos.
- Implement tool calls for docs, structured facts, ontology mapping, and RE evaluation.
- Capture trace and evidence.

### Evaluation Engineer

- Build harness.
- Implement runners.
- Implement scoring.
- Produce reports.
- Track cost/latency/rerun stability.

## Minimum Ontology Slice

Start small:

- `Policy`
- `PolicyForm`
- `Coverage`
- `Peril`
- `LossEvent`
- `Claim`
- `Claimant`
- `Insured`
- `Exclusion`
- `Endorsement`
- `Jurisdiction`
- `Limit`
- `Sublimit`
- `Deductible`
- `RequiredDocument`
- `MissingInformation`
- `Decision`
- `ReasonCode`
- `EvidenceSpan`

Useful relations:

- `claim_has_loss_event`
- `policy_has_coverage`
- `coverage_applies_to_peril`
- `exclusion_applies_to_loss_event`
- `endorsement_modifies_exclusion`
- `jurisdiction_modifies_rule`
- `decision_requires_evidence`
- `missing_information_blocks_decision`
- `limit_caps_payment`

## API Readiness Cut

The first benchmark should keep the same case target. The critical dependency is not reducing case count; it is making the Reasoning Engine and ontology callable from the Talos path.

In scope:

- 25-50 cases.
- One product line.
- A compact output schema.
- Raw LLM, LLM + RAG, and GP insurance stack arms.
- Three to five deterministic constraints in the Reasoning Engine.
- A lightweight ontology slice covering the rules under test.
- One rule-change shock.
- A static Markdown or CSV scorecard.

Out of scope:

- 250-500 cases.
- Full claims lifecycle simulation.
- Multimodal claims.
- Production UI polish.
- Formal external benchmark publication.
- Broad ontology coverage across many insurance products.
- Exhaustive jurisdiction coverage.

What can block execution:

- No one owns final gold decisions.
- The team debates the ontology instead of choosing the minimum concept slice.
- The Reasoning Engine and ontology layer do not expose a stable callable API for Talos.
- RAG/document retrieval setup consumes the week.
- The first case set tries to cover too many insurance lines.
- The scorecard tries to satisfy external-audit standards before the internal proof works.

## Main Risks

- Case labels are underspecified or contested.
- Ontology scope expands too quickly.
- RE rules try to cover too many edge cases before the harness works.
- Benchmark arms are unfairly configured.
- Evidence spans are not labeled consistently.
- RAG quality becomes a confounder.
- The demo becomes about UI polish instead of decision reliability.

## Practical Recommendation

Start with one insurance line, one product, and a narrow but painful rule family. Build the first 25-50 cases so they include:

- easy approvals,
- easy denials,
- endorsement overrides,
- missing-info escalations,
- one jurisdiction twist,
- and one rule-change shock.

That is enough to show why GP's components form a governed decision stack, not just another chatbot. Once the RE + ontology API is available to Talos, the benchmark run itself should be straightforward to execute and repeat.
