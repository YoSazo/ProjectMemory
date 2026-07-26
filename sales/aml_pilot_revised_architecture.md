# AML Alert Disposition Pilot — Revised Architecture

The original "anonymized CSV to vendor" model is **retired** for sanctions fuzzy-match work. It fails InfoSec, destroys semantic signal, and produces a pilot that proves nothing on production-like data.

This document replaces `sales/aml_alert_disposition_pilot_scope.md` as the operational truth.

---

## Three sinkholes (acknowledged)

| Problem | Why the old pitch failed | Revised approach |
| --- | --- | --- |
| **Anonymization paradox** | Fuzzy sanctions disposition requires real entity strings; "Entity A" vs "Entity B" is not a test | **Client-hosted execution** — data never egresses |
| **MRM / SR 11-7** | Verifier does not exempt the LLM from model risk governance | **Decision-support tiering** + MRM defense packet; no auto-decision in pilot |
| **Schema delusion** | Clean booleans do not exist in Actimize exports | **Evidence provenance layer** + untrusted extraction → escalate, never clear |

---

## Pilot tiers (sequential, not optional)

### Tier 0 — Architecture proof (no client data)

- **Where:** Public demo cases (`cases/aml_alert_public_eval_cases.jsonl`)
- **Cost:** Free / already in repo
- **Proves:** Verifier blocks unsafe clears; iteration traces; hard-hit gates
- **Does not prove:** Your export format, your alert mix, your MRM acceptance

### Tier A — Client-hosted replay (real alerts, no egress)

- **Where:** Bank VPC / sandbox VM / analyst workstation
- **Data:** 50–100 **real** alert rows — names intact — **never leave bank environment**
- **Memla provides:** CLI package, case schema, ETL mapping template, runbook
- **Bank runs:** `memla aml benchmark-disposition` internally
- **Output stays internal:** JSON/MD report reviewed in room with Marcus + engineer
- **Timeline:** 2 weeks wall-clock (1 week InfoSec sandbox approval + 1 week replay)
- **Fee:** $5,000–$15,000 depending on Memla engineer hours for ETL support on-site or remote

**This is the first paid pilot that counts.**

### Tier B — Structured evidence intake (schema reality)

Before automating Actimize ETL, bank analyst fills **structured evidence confirmation** for each alert:

```json
{
  "identity_verified": true,
  "provenance": {
    "identity_verified": {
      "source": "analyst_confirmed",
      "confidence": 1.0,
      "citation": "IDV vendor pass 2024-03-12"
    }
  }
}
```

- Untrusted NLP extraction (`source: nlp_extracted`) **cannot** satisfy clear path
- Contradictory analyst notes → `evidence_contradiction` → forced escalate
- Proves disposition loop on **honest inputs** before attacking 20 years of technical debt

### Tier C — Messy export ETL (technical debt)

- Memla + bank engineer map Actimize / NICE / Oracle export → case schema
- Extraction confidence attached to every inferred boolean
- Low-confidence fields → escalate, never clear
- **This is a separate SOW**, not bundled into 5-day pilot

---

## What we no longer ask for

- Anonymized entity names for sanctions fuzzy-match pilots
- Raw PII exported to Memla cloud
- Claim that synthetic data proves production readiness
- Claim that verifier exempts LLM from MRM review

---

## InfoSec answer (specific)

> "We do not have a magic obfuscation that preserves fuzzy sanctions semantics and satisfies InfoSec. **That technique does not exist in a portable form.** We run inside your environment on real data, or we run Tier 0 on public cases only. Those are the options."

Optional accelerators banks already use:

| Path | Notes |
| --- | --- |
| **Bank-managed sandbox VM** | Memla installs CLI; bank loads alerts; no egress |
| **Memla engineer on-site** | Behind bank laptop, no data on Memla hardware |
| **Clean-room session** | Bank projects screen; Memla guides; extreme but works for first 10 rows |

---

## MRM answer (specific)

The LLM is **Tier 2 decision support**, not Tier 1 automated decisioning, in pilot scope:

| Control | Implementation |
| --- | --- |
| Human disposition authority | Analyst retains final clear/reject/escalate in all pilot tiers |
| Bounded output | JSON schema only — no free-text actions executed |
| Deterministic verifier | Blocks unsafe proposals before they become recommendations |
| Challenger | Raw lane vs Memla lane on same cases — drift visible |
| Limitations doc | Known failure modes: untrusted evidence, contradictory notes, novel name scripts |
| No training on bank data | Default; contractual |

**MRM defense packet:** `sales/aml_mrm_defense_packet_outline.md`

We do **not** claim an unvalidated LLM enters production because a Python script catches errors. We claim:

1. Pilot is offline replay with human authority unchanged
2. Verifier is a **control**, documented in the model use case
3. Full MRM validation is a **Phase 2 gate**, not bypassed

---

## Schema / ETL answer (specific)

The verifier is only as safe as evidence provenance.

| Evidence source | Can support `clear` on fuzzy match? |
| --- | --- |
| `analyst_confirmed` | Yes, if no contradictions |
| `idv_vendor` / `core_system` | Yes |
| `nlp_extracted` from legacy notes | **No** — triggers `evidence_extraction_unverified` |
| Contradictory analyst notes | **No** — triggers `evidence_contradiction` → escalate |

Garbage in does not get a rubber-stamp clear. It gets escalated.

---

## Revised success gates

| Gate | Tier A requirement |
| --- | --- |
| Hard-hit safety | Zero verifier-passed clears on hard-hit cases |
| Evidence integrity | Zero clears when `evidence_extraction_unverified` or `evidence_contradiction` present |
| Semantic validity | Real entity names used — no anonymization |
| ETL honesty | Field mapping documented; unresolved fields default to escalate |
| MRM posture | Decision-support tier documented; human authority unchanged |

---

## Procurement (unchanged reality)

Expect 6–12 weeks for vendor onboarding at $400B institutions. **Tier A avoids data egress review** — smaller InfoSec surface than "send us your alerts." Still need SOW, MRM awareness, sandbox approval.

**Day-after-yes packet:**

- W-9
- SOW (this document + tier selection)
- Data handling summary (client-hosted variant)
- MRM defense packet outline
- Sandbox runbook

---

## Bottom line for Marcus

> "You were right. Anonymized CSV to a vendor is the wrong pilot for sanctions fuzzy matching. We run in your sandbox on real alerts, we attach provenance to every evidence flag, and we bring an MRM packet that treats the LLM as decision support — not a validated auto-decision engine. Tier 0 proves the verifier. Tier A proves it on your data. Tier C is when we earn the right to talk about your Actimize export."
