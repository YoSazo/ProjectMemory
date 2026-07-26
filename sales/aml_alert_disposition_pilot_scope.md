# AML Alert Disposition Replay Pilot

> **Operational note:** For sanctions fuzzy-match work, use `sales/aml_pilot_revised_architecture.md`.  
> The "anonymized CSV to vendor" model below is **deprecated** — it fails InfoSec and destroys semantic signal.

**Fee:** $5,000–$15,000 (Tier A client-hosted; depends on ETL support hours)  
**Timeline:** 2 weeks wall-clock typical (sandbox approval + replay)  
**Volume:** 50–100 **real** alert rows (names intact, no egress)  
**Mode:** Client-hosted offline replay — screening engine untouched, data stays in bank environment

## What this is

Memla replays historical AML alert rows through a verifier-backed disposition loop **inside the bank's sandbox**. For each row it returns:

- recommended disposition (`clear`, `reject`, `escalate`, `request_docs`)
- rule hits and next actions
- audit-ready narrative
- full iteration trace (every attempt, verifier result, residuals)

This pilot does **not** connect to Actimize, NICE, Oracle FCCM, or any live system.  
This pilot does **not** require anonymized entity names.

## What the pilot validates

1. **Disposition quality** — Memla vs. your current analyst outcome on the same rows
2. **Safety** — zero verifier-passed clears on hard-hit cases
3. **Evidence integrity** — zero clears on unverified NLP extraction or contradictory notes
4. **Semantic validity** — real entity strings preserved for fuzzy-match evaluation
5. **ETL fit** — field mapping documented (full automation is Tier C, separate SOW)

## Client provides

- sandbox VM or analyst workstation for Memla CLI execution
- 50–100 real alert rows accessible **only inside bank environment**
- threshold sheet or desk playbook excerpt
- optional: analyst structured evidence confirmation (Tier B) per alert
- optional: current analyst disposition for comparison

**Do not send to Memla cloud:** production alert exports with entity names intact.

## We deliver

- CLI package, schema, ETL mapping template, sandbox runbook
- remote or on-site engineer support for first run (tier-dependent)
- row-by-row JSON/MD output reviewed **inside bank environment**
- executive summary for internal distribution
- MRM defense packet outline (`sales/aml_mrm_defense_packet_outline.md`)
- go / no-go recommendation on shadow-mode next step

## Pilot success gates (hard)

These gates override benchmark utility scores:

| Gate | Requirement |
| --- | --- |
| Hard-hit safety | Zero Memla rows where a hard-hit case receives a verifier-passed `clear` |
| Evidence integrity | Zero clears when evidence provenance is untrusted or contradictory |
| Semantic validity | Real entity names used — no anonymization |
| Unsafe clear attempts | Documented; verifier must block them |
| ETL mapping | Documented; unresolved fields default to escalate |
| Audit sample | Blind review on 10 rows: narrative quality vs. current manual notes |

Utility score ranks lanes. **Safety gates decide go/no-go.**

## Procurement path

Tier A reduces InfoSec surface (no data egress) but still requires sandbox approval and MRM awareness.

| Path | Notes |
| --- | --- |
| **Innovation / sandbox budget** | Preferred |
| **Professional services PO** | Existing consulting vendor vehicle |
| **Pilot SOW + sandbox runbook** | Client-hosted variant — see revised architecture doc |
| **MRM review** | Decision-support tier; human authority unchanged |

**Day-after-yes packet:** W-9, SOW, client-hosted data handling summary, MRM defense packet outline, sandbox runbook.

## What this pilot is not

- not a legal or regulatory opinion
- not a substitute for your screening vendor
- not anonymized export to a vendor cloud
- not full MRM production validation of the LLM
- not automated Actimize ETL (Tier C — separate engagement)
- not production deployment or auto-clear authorization

## Regulatory framing (US institutions)

- **FFIEC SR 11-7** — model use case, limitations, validation plan, human override
- **OCC model risk management** — decision-support tiering in pilot
- **FinCEN CDD rule** — identity and beneficial ownership evidence in disposition

## Honest notes

**Public demo cases** prove verifier architecture only. **Your alerts** prove the product.

**Anonymization paradox:** Fuzzy sanctions disposition requires real names. We run client-hosted or we don't run on your data.

**Schema reality:** Clean booleans are Tier B (structured analyst confirmation) or Tier C (ETL with provenance). The verifier treats untrusted extraction as escalate-only.

See `sales/aml_pilot_revised_architecture.md` for full tier breakdown.
