# Public AML Alert Disposition Demo Pack

This pack keeps the AML wedge grounded in public AML/KYC control families while we wait on real client alert exports.

Files:
- `cases/aml_alert_public_eval_cases.jsonl`

What this public pack covers:
- sanctions fuzzy-name false-positive clearing
- exact sanctions match rejection
- PEP associate escalation
- direct PEP rejection
- identity-document gap remediation
- beneficial-ownership gap remediation
- confirmed adverse media escalation
- high-risk jurisdiction escalation
- clean onboarding clearance

Case mapping:

| Case ID | Public control family |
| --- | --- |
| `sanctions_fuzzy_name_clear` | OFAC fuzzy-match false-positive review |
| `sanctions_exact_match_reject` | confirmed sanctions hit rejection |
| `pep_associate_escalate` | associate PEP escalation |
| `pep_direct_reject` | direct PEP rejection |
| `identity_gap_request_docs` | CDD identity verification gap |
| `ubo_gap_request_docs` | beneficial ownership documentation gap |
| `adverse_media_confirmed_escalate` | confirmed adverse media escalation |
| `high_risk_jurisdiction_escalate` | high-risk jurisdiction EDD |
| `clean_screening_clear` | no-hit onboarding clearance |
| `entity_type_mismatch_clear` | entity-type and jurisdiction mismatch clear |

Primary public sources:
- FinCEN Customer Due Diligence Requirements:
  - https://www.fincen.gov/resources/statutes-and-regulations/cdd-final-rule
- FinCEN Beneficial Ownership Information:
  - https://www.fincen.gov/boi
- FinCEN SAR guidance:
  - https://www.fincen.gov/resources/advisoriesbulletinsfact-sheets
- OFAC Sanctions List Search:
  - https://sanctionssearch.ofac.treas.gov/
- EU AML customer due diligence framework:
  - https://finance.ec.europa.eu/financial-crime/anti-money-laundering-and-countering-financing-terrorism_en

How to run it:

```bash
memla aml benchmark-disposition \
  --cases cases/aml_alert_public_eval_cases.jsonl \
  --raw-model qwen3.5:9b \
  --memla-model qwen3.5:9b \
  --raw-provider ollama \
  --raw-base-url http://127.0.0.1:11435 \
  --memla-provider ollama \
  --memla-base-url http://127.0.0.1:11435
```

What this is not:
- real bank or fintech alert exports
- a substitute for client screening logs, SAR records, or disposition notes
- a claim that public rule text alone is enough for production AML integration
- a claim that the 10 public demo cases represent Actimize, Oracle FCCM, or NICE export formats

What the pilot validates:
- ETL mapping from the client's actual alert export to Memla's case schema
- disposition quality and verifier safety on the client's alert mix, not only on synthetic demo cases

Useful public next step:
- overlay alert realism from anonymized client alert CSV/JSONL exports in an offline replay pilot
