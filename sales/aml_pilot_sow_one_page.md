# Statement of Work — AML Alert Disposition Replay Pilot (Tier A)

**Vendor:** Memla  
**Client:** [Institution name]  
**Effective date:** [Date]  
**Fee:** $[5,000–15,000] flat (per tier scope below)  
**SOW version:** 1.0 — client-hosted, zero egress

---

## Scope

Memla provides software, documentation, and remote/on-site support for an **offline, client-hosted** replay of 50–100 historical AML alert rows through a verifier-backed disposition loop. Alert data **does not leave** the client environment.

## Deliverables

| # | Deliverable |
| --- | --- |
| 1 | Memla CLI replay package (container image or signed install bundle) |
| 2 | Tier A deployment specification (compute, network, zero-egress) |
| 3 | Case schema + ETL mapping template for client export format |
| 4 | Sandbox runbook for IT Risk / platform team |
| 5 | MRM defense packet outline + verifier truth table appendix |
| 6 | Row-level replay report (JSON + Markdown) generated **inside client environment** |
| 7 | Executive summary and go/no-go recommendation review call (1 hour) |

## Client responsibilities

| # | Responsibility |
| --- | --- |
| 1 | Provision approved sandbox **server VM** (not analyst VDI) per deployment spec |
| 2 | Provide 50–100 real alert rows accessible only inside sandbox |
| 3 | Provide threshold sheet / desk playbook for policy controls |
| 4 | Designate pilot owner (Operations), IT Risk contact, MRM contact |
| 5 | Tier B (optional): analyst structured evidence confirmation per alert |

## Success gates (hard)

Pilot succeeds only if all gates pass:

- Zero verifier-passed `clear` on hard-hit cases
- Zero clears with `evidence_extraction_unverified` or `evidence_contradiction`
- Real entity names preserved (no anonymization)
- ETL field mapping documented; unresolved fields default to escalate

Utility scores rank lanes. **Gates decide go/no-go.**

## Explicit exclusions

- No production system integration or write-back
- No screening engine replacement or threshold changes
- No automated Actimize ETL (Tier C — separate SOW if requested)
- No legal or regulatory opinion
- No SOC 2 Type II certification (interim security attestation provided; see deployment spec)

## Timeline (realistic)

| Phase | Duration | Owner |
| --- | --- | --- |
| SOW + NDA + vendor registration | 2–4 weeks | Client procurement |
| Sandbox VM provisioning | 4–24 weeks (institution-dependent) | Client IT |
| Memla install + first replay | 1–2 business days | Memla + Client IT |
| Report + review call | 2–3 business days after replay | Memla |
| **Total wall-clock** | **Often 90–120 days** if net-new sandbox; **1–2 weeks** if pre-approved VM exists |

Memla replay work is **not** a 5-day engagement unless sandbox is already approved.

## Fee and payment

- Flat fee: $[amount] invoiced on SOW signature or [Net 30] per client policy
- Travel/on-site engineer (optional): quoted separately
- No success fee; no production licensing implied

## Data handling

- Client-hosted execution; zero alert egress to Memla
- No model training on client data (contractual)
- Source files deleted per client retention policy
- See `sales/aml_tier_a_data_handling_summary.md`

## Acceptance

Client pilot owner signs acceptance when:

1. Replay report delivered inside client environment
2. Review call completed
3. Go/no-go memo issued by Memla

## Signatures

| | Name | Title | Date |
| --- | --- | --- | --- |
| **Client** | | | |
| **Memla** | | | |
