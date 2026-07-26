# Memla AML Disposition — MRM Defense Packet Outline

For bank Model Risk Management / Compliance review. Not a legal opinion. Expand each section with institution-specific details at engagement.

---

## 1. Model use case summary

| Field | Value |
| --- | --- |
| **Intended use** | Offline alert disposition **recommendation** for analyst review |
| **Not intended for** | Autonomous clear/reject, SAR filing, screening list matching, production threshold changes |
| **Decision authority** | Human analyst retains final disposition in all pilot phases |
| **Regulatory framing** | SR 11-7 decision-support tool with human override; FinCEN CDD evidence alignment |

---

## 2. Model inventory

| Component | Type | Tier (proposed) | Role |
| --- | --- | --- | --- |
| LLM (e.g. Qwen 9B) | Generative text → JSON | Tier 2 decision support | Proposes disposition, rule hits, narrative |
| `evaluate_aml_alert_rules()` | Deterministic Python | Control / policy engine | Computes rule hits from structured inputs |
| `backtest_aml_decision()` | Deterministic Python | Control | Validates proposal against policy |
| Decision loop | Orchestration | Control | Feeds verifier residuals to next attempt |

**Key MRM statement:** The LLM is not the decision engine. It is a proposal generator bounded by schema and blocked by deterministic controls.

---

## 3. Inputs and outputs

### Inputs (structured case)

- Alert metadata, screening hits, customer profile
- Evidence flags with **provenance** (source, confidence, citation)
- Bank policy controls (thresholds, high-risk jurisdictions)

### Outputs (per alert)

- Proposed disposition: `clear | reject | escalate | request_docs`
- Predicted rule hits and next actions
- Audit narrative and rationale
- Iteration trace with verifier status per attempt

### Output does NOT

- Write to case management
- Clear alerts in screening engine
- File SARs
- Modify thresholds

---

## 4. Known limitations

Document honestly in validation plan:

| Limitation | Mitigation |
| --- | --- |
| LLM may propose unsafe clear | Verifier blocks; `unsafe_clear_with_hard_hit` logged |
| LLM may hallucinate rule hits | Normalized against known rule ontology; verifier uses deterministic hits |
| Untrusted evidence extraction | `evidence_extraction_unverified` blocks clear path |
| Contradictory analyst notes | `evidence_contradiction` forces escalate |
| Name-script / transliteration edge cases | Escalate; do not clear on low confidence |
| Prompt injection via customer data | Schema-only output; no tool execution; input length bounds |

---

## 5. Validation approach (pilot phase)

| Phase | Activity | MRM artifact |
| --- | --- | --- |
| Tier 0 | Public case benchmark | Architecture validation report |
| Tier A | Client-hosted replay on 50–100 real alerts | Disposition comparison vs analyst baseline |
| Tier A | Hard-hit safety gate | Zero verifier-passed clears on hard hits |
| Tier A | Evidence integrity gate | Zero clears with unverified extraction |
| Tier B | Structured evidence intake | Provenance audit sample |
| Phase 2 | Shadow mode | Side-by-side recommendation; analyst override rate |

**Not in pilot scope:** Full production model validation, drift monitoring at scale, demographic bias testing across full customer population. These are Phase 2+ requirements if model moves toward assisted production.

---

## 6. Bias and fairness (honest scope)

**Pilot acknowledgment:** Full demographic bias testing across name origins, transliterations, and PEP geographies requires institution-specific sample design and is **not complete in Tier A**.

**Pilot mitigations:**

- Hard hits never auto-clear regardless of name pattern
- Soft-hit clears require trusted evidence provenance
- Over-reject and over-escalate rates tracked by case type
- Worst-slice reporting in benchmark (sanctions fuzzy, PEP associate, high-risk jurisdiction)

**Phase 2 commitment:** Stratified replay by name script / jurisdiction / entity type with institution-provided labels.

---

## 7. Monitoring (Phase 2 shadow mode)

| Metric | Threshold action |
| --- | --- |
| `unsafe_clear_with_hard_hit` attempts | Any → halt shadow, root-cause |
| Verifier-passed clear on hard-hit case | Zero tolerance |
| Analyst override rate | Track; high override → retrain / policy bank |
| Outcome match vs analyst | Track by alert type |
| Evidence unverified clear attempts | Escalate to MRM review |

---

## 7a. Automation bias controls (Phase 2 / Phase 3 — required before production assist)

**Regulatory basis:** OCC/FINRA guidance on human oversight of AI-assisted decisions. If analysts approve Memla recommendations in seconds without review, examiners may treat the system as **functionally automated** regardless of "human-in-the-loop" labeling.

**Problem:** Beautiful audit narratives become rubber-stamp crutches under quota pressure.

**Controls (shadow mode minimum):**

| Control | Metric / implementation |
| --- | --- |
| **Minimum dwell time** | Approve button disabled until analyst views evidence panel for ≥ N seconds (configurable, e.g. 30s on fuzzy-match clears) |
| **Evidence acknowledgment** | Analyst must check each conflicting evidence item before approve on clear/escalate |
| **Override reason capture** | Required free-text or coded reason when analyst deviates from Memla recommendation |
| **Fast-click detection** | Flag cases where approve time < threshold (e.g. 10s) for QA sample |
| **Time-on-task telemetry** | Log: panel expand events, scroll depth, time on evidence tab, time to disposition |
| **Agreement rate monitoring** | If analyst-Memla agreement > 95% **and** median approve time < threshold → MRM alert (automation bias risk) |
| **Random QA sample** | 5–10% of shadow cases independently reviewed by L2 regardless of agreement |
| **Narrative edit detection** | Track whether analyst edited audit narrative before submit; zero edits + fast approve = bias flag |

**Phase 3 gate:** MRM must approve automation bias monitoring dashboard before moving from shadow to assist.

**Honest pilot scope:** Tier A offline replay does **not** include UI telemetry. Automation bias controls are **Phase 2 shadow mode deliverables**, documented here so MRM knows we are not claiming human oversight without measuring it.

---

## 8. Human oversight

| Control | Implementation |
| --- | --- |
| Final disposition | Analyst only in pilot and shadow |
| Override | Always available; logged |
| Escalation path | L2 for PEP, adverse media, high-risk jurisdiction |
| Rollback | Disable Memla routing; analyst-only workflow |

---

## 9. Data handling (Tier A)

- Execution client-hosted; no alert egress
- No model training on bank data (contractual default)
- Source files deleted per bank retention policy
- Subprocessor list: LLM provider if not bank-hosted inference

---

## 10. Open items for MRM review (do not hide)

1. LLM vendor and version used in replay
2. Whether inference is bank-hosted or vendor-hosted
3. Actimize ETL automation scope (Tier C — separate validation)
4. Timeline for full Tier 1/2 model validation if shadow succeeds
5. Integration with existing case management audit trail

---

## 11. What we ask MRM to approve (pilot only)

> Approval to run **offline, client-hosted, human-in-the-loop disposition replay** on 50–100 historical alerts for comparison and control testing — **not** approval for automated production decisioning.

---

## Appendix: Verifier truth table reference

See `memory_system/distillation/aml_disposition_benchmark.py` — `backtest_aml_decision()` and `evaluate_aml_alert_rules()`.

Hard-hit gate: `pilot_safety_summary.pilot_hard_hit_gate_passed` in benchmark report.

Evidence integrity: clears blocked when `evidence_extraction_unverified` or `evidence_contradiction` present.
