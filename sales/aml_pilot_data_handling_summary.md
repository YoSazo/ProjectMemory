# AML Pilot — Data Handling Summary (Legal / InfoSec)

> **Deprecated for Tier A.** Use `sales/aml_tier_a_data_handling_summary.md` (client-hosted, zero egress, real entity names).

One-page summary for vendor-transfer pilots only (legacy). Full DPA available at signature.

## Engagement type

Offline batch replay. No production system access. No API integration. No write-back to case management.

## Data received

| Field | Requirement |
| --- | --- |
| Volume | 50–100 alert rows |
| Identifiers | Anonymized alert IDs only — no customer SSN, account numbers, or full legal names required |
| Format | CSV or JSONL export from screening / case management |
| Content | Alert metadata, screening hits, disposition flags, policy thresholds |

## Data not required

- Live credentials
- SAR filings or narrative text with PII
- Production network access
- Non-anonymized customer records

## Processing

1. Client transmits encrypted file (SFTP, secure file share, or client-provided channel)
2. Memla maps export fields to replay case schema (ETL documented in pilot deliverable)
3. Batch replay runs in isolated environment
4. Report generated — JSON, CSV, PDF
5. Source files deleted per retention schedule below

## Retention

| Artifact | Default retention |
| --- | --- |
| Client source file | Deleted within 30 days of report delivery unless extended in writing |
| Pilot report | Retained by Memla for 90 days for support questions, then deleted |
| Aggregated metrics (no row-level PII) | May be retained for product improvement with written client consent |

Client may request immediate deletion after report delivery.

## Subprocessors

LLM inference (if not run on client infrastructure):

- Client may require on-prem / private VPC execution — Memla CLI runs fully client-side
- If Memla-hosted inference is used, subprocessor list provided in DPA

## Security controls

- Encryption in transit (TLS 1.2+)
- Access limited to named project staff
- No commingling with other client datasets
- No model training on client alert data without explicit written consent

## InfoSec FAQ

**Q: Does alert data leave our environment?**  
A: Optional. Client can run `memla aml benchmark-disposition` internally. Memla receives only anonymized exports if client-hosted inference is preferred.

**Q: Is this a new production integration?**  
A: No. Read-only batch file. No connectivity to screening engine.

**Q: What if our export contains residual PII?**  
A: Client should anonymize before transfer. Memla will reject non-anonymized production identifiers if identified and request re-export.

## Documents available at signature

- Pilot Statement of Work (scope, fee, timeline)
- Mutual NDA (if required)
- Data Processing Addendum
- W-9 / vendor registration packet
