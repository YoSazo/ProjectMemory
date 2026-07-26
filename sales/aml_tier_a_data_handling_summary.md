# AML Tier A Pilot — Data Handling Summary (Client-Hosted)

For Legal, InfoSec, and IT Risk review. Supersedes the deprecated vendor-transfer data handling summary for Tier A engagements.

---

## Engagement model

| Attribute | Value |
| --- | --- |
| **Processing location** | Client sandbox VM only |
| **Data egress to Memla** | **None** — alert rows stay inside client perimeter |
| **Production access** | None |
| **Write-back** | None |
| **Network egress from replay job** | **None required** when using local inference (see deployment spec) |

---

## Data in scope

| Data | Handling |
| --- | --- |
| 50–100 historical AML alert rows | Loaded from client-controlled path inside sandbox |
| Entity names / screening hits | **Retained intact** — required for fuzzy-match evaluation |
| Analyst dispositions (optional) | Comparison baseline only |
| Threshold / policy sheet | Configuration input; no PII |

## Data not required

- SAR narrative text with full PII bundles
- Live API credentials to screening engine
- Export to Memla cloud
- Anonymization of entity names (deprecated for this pilot tier)

---

## Processing flow

1. Client loads alert export into sandbox read-only volume (`/input`)
2. Memla CLI replays each row through disposition + verifier loop
3. LLM inference calls **local** endpoint only (Ollama on same VM or bank private LLM gateway)
4. Report written to sandbox output volume (`/output`)
5. Client distributes report internally; Memla receives **aggregate metrics only** if client chooses to share

---

## Retention

| Artifact | Location | Retention |
| --- | --- | --- |
| Source alert file | Client sandbox | Client policy |
| Replay report | Client sandbox | Client policy |
| Memla container image | Client registry or local load | Client policy |
| Aggregate metrics shared with Memla | Optional | By mutual written agreement only |

Memla does not retain client alert rows unless explicitly agreed in writing.

---

## Subprocessors

**Tier A default:** None. Inference runs on client infrastructure.

If client opts to use a **bank-approved internal LLM gateway** (OpenAI-compatible private endpoint), that gateway is a **client subprocessors** — not Memla's.

Memla software does not phone home during replay (see zero-egress attestation in deployment spec).

---

## Security controls (software)

| Control | Implementation |
| --- | --- |
| Zero egress (default compose) | `network_mode: none` available |
| Read-only container filesystem | Supported in reference compose |
| Non-root runtime user | `memla` user in Dockerfile |
| No auto-update / telemetry | CLI has no built-in analytics |
| Deterministic verifier | Python policy engine separate from LLM |
| Evidence provenance | Untrusted NLP extraction cannot clear |

---

## SOC 2 / vendor security status (honest)

| Certification | Status |
| --- | --- |
| SOC 2 Type II | **Not available at pilot stage** — do not represent otherwise |
| Interim materials provided | Security architecture attestation, zero-egress verification steps, container SBOM, deployment spec |

IT Risk should evaluate the **client-hosted, zero-egress** deployment model and container image — not vendor cloud custody of alert data.

---

## InfoSec FAQ

**Q: Does alert data leave our bank?**  
A: No, in Tier A default configuration.

**Q: Does the container call the public internet?**  
A: Not in zero-egress mode. LLM calls target localhost or bank-internal gateway only.

**Q: Can analysts run this on VDI?**  
A: **No.** Dedicated sandbox server VM. Analyst VDI lacks compute and violates least-privilege.

**Q: What if we already have an internal LLM platform?**  
A: Memla CLI supports OpenAI-compatible private endpoints — preferred at many banks.

**Q: Can Memla engineers access our sandbox?**  
A: Optional, via client-approved jump box / paired session. Not required for pilot.

---

## Documents included in signature packet

1. This data handling summary
2. One-page SOW (`sales/aml_pilot_sow_one_page.md`)
3. Tier A deployment spec (`sales/aml_tier_a_deployment_spec.md`)
4. MRM defense packet outline (`sales/aml_mrm_defense_packet_outline.md`)
5. W-9 / vendor registration (on request)
