# Thursday Meeting Brief — IT Risk + MRM

**Audience:** Head of IT Risk, Lead Model Validator, Marcus Velez (Operations)  
**Goal:** Architecture approval to **begin** sandbox provisioning — not sell, not promise 5-day delivery  
**Duration:** 45–60 minutes

---

## Agenda

| Time | Topic | Lead |
| --- | --- | --- |
| 0–5 min | Scope: Tier A offline replay, zero egress, no production integration | Operations |
| 5–15 min | Verifier truth table + provenance layer (live walkthrough) | Memla |
| 15–25 min | Deployment spec: VM sizing, container, network, no VDI | IT Risk |
| 25–35 min | MRM packet: decision-support tiering, automation bias plan | Model Validation |
| 35–45 min | Timeline honesty + parallel path (Tier 0 now, Tier A when VM ready) | All |
| 45–60 min | Open objections | All |

---

## Opening (do not sell)

> "Thank you for the time. We're not asking you to approve production AI in AML today. We're asking whether a **client-hosted, zero-egress batch replay** on a sandbox server VM is architecturally acceptable — and what you need from us to start your review clock. Operations has already seen the verifier. Today is about your gates."

---

## Section 1 — Verifier truth table (MRM + IT Risk)

**Show:** `memory_system/distillation/aml_disposition_benchmark.py` → `backtest_aml_decision()`

Key messages:

1. LLM proposes JSON; Python verifier decides if proposal is policy-valid
2. Hard hits (`exact_sanctions_match`, `pep_direct_match`, `adverse_media_confirmed`) **block clear**
3. Untrusted evidence (`nlp_extracted`) **blocks clear**
4. Contradictory notes → **escalate only**
5. Every iteration logged — examiner-ready trace

**Live demo case:** `sanctions_fuzzy_name_clear` — iteration 1 reject blocked → iteration 2 clear with provenance

**Hard-hit gate in report:** `pilot_hard_hit_gate_passed`

---

## Section 2 — Provenance layer (MRM)

**Show evidence schema:**

```json
"provenance": {
  "identity_verified": {
    "source": "analyst_confirmed",
    "confidence": 1.0,
    "citation": "IDV vendor pass 2024-03-12"
  }
}
```

Trusted: `analyst_confirmed`, `idv_vendor`, `core_system`, `screening_engine`  
Untrusted: `nlp_extracted` → cannot clear

**Message:** Verifier doesn't trust booleans. Garbage in → escalate, not rubber-stamp.

---

## Section 3 — Deployment (IT Risk) — expect hard questions

### Q: "You can't install on our VDI."

**A:** Correct. **Sandbox server VM only.** Analysts never run the model.

### Q: "Sandbox takes 6 months."

**A:** Correct for net-new. We parallel-path: Tier 0 public cases prove verifier now; Tier A waits for your VM. Memla install is 1–2 days once VM exists.

### Q: "SOC 2?"

**A:** Not available. Tier A avoids vendor custody — alert data stays here. Evaluate container + zero-egress, not vendor cloud cert.

### Q: "Internet egress?"

**A:** Zero-egress mode: `network_mode: none`. LLM via localhost or **your internal gateway** — Path B often fastest approval.

### Q: "Compute?"

**A:** Hand them `sales/aml_tier_a_deployment_spec.md` Section 4:

| Path | VM size |
| --- | --- |
| Internal LLM gateway | 4 vCPU / 4 GB (Memla only) |
| Local Ollama 9B CPU | 16 vCPU / 32 GB RAM |
| Local Ollama 9B GPU | 8 vCPU / 16 GB + 8 GB VRAM |

### Q: "Container approval?"

**A:** `Dockerfile.aml-replay` — open, scannable, non-root, no privileged mode. Bank scans and imports to internal registry — standard process.

---

## Section 4 — Automation bias (MRM) — don't wait for them to raise it

**Acknowledge proactively:**

> "Human-in-the-loop is not free. If analysts approve in 4 seconds, examiners will call it automated. Phase 2 shadow mode includes dwell-time gates, evidence acknowledgment, fast-click QA flags, and agreement-rate monitoring. Tier A offline replay doesn't include UI telemetry — we're documenting Phase 2 controls now so you know we're not hand-waving oversight."

See MRM packet Section 7a.

---

## Section 5 — What we need from this meeting

| Ask | Owner |
| --- | --- |
| Is client-hosted / zero-egress architecturally acceptable in principle? | IT Risk |
| Preferred inference path: internal gateway vs local Ollama? | IT Risk + Platform |
| Sandbox VM sizing approval (see spec) | Platform |
| MRM: is offline decision-support replay acceptable scope for Tier A? | Model Validation |
| Parallel Tier 0 review while sandbox provisions? | All |

**Do not ask:** Sign-off today. Production deployment. Auto-clear authorization.

---

## Documents to send Marcus today (before Thursday)

1. `sales/aml_pilot_sow_one_page.md`
2. `sales/aml_tier_a_data_handling_summary.md`
3. `sales/aml_tier_a_deployment_spec.md`
4. `sales/aml_mrm_defense_packet_outline.md` (with Section 7a automation bias)
5. `Dockerfile.aml-replay` + `docker-compose.aml-tier-a.yml`
6. W-9 (fill in — placeholder for user)

---

## Closing

> "We're not asking you to trust our marketing. We're asking whether this architecture — verifier-first, provenance-aware, client-hosted, zero egress — is worth a sandbox review clock. Operations has the W-9 conversation. You have the architecture conversation. We'll answer every technical objection; we won't pretend sandbox provisioning is a 5-day job."

---

## Forbidden in this room

- "Magic" / "AI-powered" / "replace Actimize"
- Fake SOC 2 claim
- "Install on analyst laptops"
- "5-day pilot" without VM caveat
- Arguing with Marcus in front of IT Risk

## Required

- Verifier truth table walkthrough
- Provenance demo
- Honest SOC 2 / timeline answer
- Path B internal LLM gateway as preferred option
