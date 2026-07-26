# AML Tier A — Deployment Specification (IT Risk / Platform Engineering)

For Head of IT Risk, platform engineering, and sandbox approval boards.  
**Not a SOC 2 report.** Honest interim security documentation for client-hosted pilot.

---

## 1. Executive summary

Memla Tier A runs as a **batch CLI replay job** on a **dedicated sandbox Linux VM** inside the bank perimeter. It does **not** run on analyst VDI. It does **not** require alert data to egress the bank. LLM inference is **client-provided** (local Ollama or bank-internal LLM gateway).

| Question | Answer |
| --- | --- |
| Is this a net-new SaaS integration? | **No** — batch job on client VM |
| Does alert PII leave the bank? | **No** (Tier A default) |
| Does the job require internet egress? | **No** (zero-egress mode) |
| Does Memla have SOC 2 Type II? | **No** — evaluate client-hosted deployment instead |
| Typical sandbox approval timeline | **4–6 months** net-new; **days** if pre-approved VM exists |

---

## 2. Architecture diagram

```text
┌─────────────────────────────────────────────────────────────┐
│  Bank non-production zone (sandbox VPC / VLAN)                │
│                                                             │
│  ┌──────────────────┐      ┌─────────────────────────────┐  │
│  │  Sandbox Linux   │      │  Optional: same VM or      │  │
│  │  VM (replay)     │─────▶│  adjacent LLM inference    │  │
│  │                  │ HTTP │  (Ollama or bank gateway)  │  │
│  │  memla-replay    │ only │  localhost / internal DNS  │  │
│  │  container       │      └─────────────────────────────┘  │
│  │                  │                                       │
│  │  /input  (ro)    │◀── alert JSONL from client export     │
│  │  /output (rw)    │──▶ replay report JSON/MD              │
│  └──────────────────┘                                       │
│           │ no outbound internet (zero-egress mode)           │
└───────────┴─────────────────────────────────────────────────┘

Analyst VDI ──▶ Actimize (existing)     [no Memla on VDI]
Platform engineer ──▶ sandbox VM only
```

---

## 3. Components

| Component | Image / artifact | Purpose |
| --- | --- | --- |
| **memla-replay** | `Dockerfile.aml-replay` → `memla-aml-replay:0.2.0` | Batch disposition replay CLI |
| **Ollama** (optional) | `ollama/ollama:0.6.5` | Local LLM inference — **not bundled in Memla image** |
| **Bank LLM gateway** (preferred at many banks) | Client-operated OpenAI-compatible API | Private inference — Memla calls internal URL only |

Memla container contains: Python 3.11, `memla` CLI, public demo cases, verifier engine.  
Memla container does **not** contain: model weights, GPU drivers, Actimize connectors.

---

## 4. Compute requirements

### 4.1 Memla replay container (verifier + orchestration only)

| Resource | Minimum | Recommended |
| --- | --- | --- |
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB |
| Disk | 2 GB free | 10 GB free (reports + logs) |
| GPU | **Not required** | N/A |

### 4.2 LLM inference (client-provided — separate from Memla container)

Choose **one** path:

#### Path A — Local Ollama on sandbox VM

| Model (example) | RAM (CPU inference) | GPU (optional) | Notes |
| --- | --- | --- | --- |
| `qwen3.5:4b` | 8 GB system RAM | 4 GB VRAM if GPU | Slow on CPU; acceptable for 50–100 row pilot |
| `qwen3.5:9b` | 16 GB system RAM | 8 GB VRAM if GPU | Recommended minimum for 9B |
| `qwen3.5:9b` (quantized Q4) | 12 GB system RAM | 6 GB VRAM | Common pilot configuration |

**Pilot sizing recommendation:** Sandbox VM with **16 vCPU / 32 GB RAM** (CPU path) **or** **8 vCPU / 16 GB RAM + 1× GPU (8 GB VRAM)**.

#### Path B — Bank internal LLM gateway (often fastest approval)

| Resource | Requirement |
| --- | --- |
| Memla VM | 4 vCPU / 4 GB RAM only |
| Inference | Bank-operated service already approved by MRM/InfoSec |
| Memla config | `--memla-provider openai --memla-base-url https://[internal-gateway]` |

**This path avoids deploying Ollama entirely.**

#### Path C — Deterministic verifier-only dry run (no LLM)

| Use | Limitation |
| --- | --- |
| Prove verifier blocks unsafe clears on canned proposals | Does not test LLM disposition quality |
| IT Risk architecture review only | Not sufficient for Operations go/no-go |

---

## 5. What does NOT run on analyst VDI

| Environment | Supported? |
| --- | --- |
| Analyst VDI thin client | **No** — insufficient RAM; violates least privilege |
| Dedicated sandbox server VM | **Yes** — primary target |
| Kubernetes non-prod namespace | **Yes** — with bank-standard pod security |
| Memla vendor cloud | **No** for Tier A |

---

## 6. Network and egress

### 6.1 Zero-egress mode (default for IT Risk review)

Reference compose supports `network_mode: none` on `memla-replay`.

| Connection | Required? | Destination |
| --- | --- | --- |
| LLM inference | Yes | `localhost:11434` or internal gateway DNS |
| Internet outbound | **No** | — |
| Actimize / case management | **No** | Batch file input only |
| Memla vendor callback | **No** | No telemetry built in |

### 6.2 Internal-only mode (if Ollama on adjacent VM)

| From | To | Port | Protocol |
| --- | --- | --- | --- |
| memla-replay | ollama (internal) | 11434 | HTTP |
| Platform admin | sandbox VM | 22/SSH | Client jump box only |

Firewall rule: **deny all outbound to internet** from sandbox subnet.

### 6.3 Zero-egress verification procedure (for IT Risk)

Run on sandbox VM after install:

```bash
# 1. Confirm no outbound routes (platform team)
ip route

# 2. Run replay with network isolated container
docker run --rm --network none \
  -v /pilot/input:/input:ro -v /pilot/output:/output:rw \
  memla-aml-replay:0.2.0 \
  aml benchmark-disposition --help

# 3. Full replay uses internal LLM only — verify curl fails to public IP from container namespace
docker run --rm --network none curlimages/curl:8.5.0 \
  curl -m 5 https://example.com || echo "egress blocked as expected"
```

If using bank LLM gateway, verify gateway URL resolves to **internal RFC1918 or bank private DNS** only.

---

## 7. Container security profile

| Property | memla-replay container |
| --- | --- |
| Base image | `python:3.11-slim-bookworm` |
| Runtime user | Non-root `memla` |
| Shell | Not required at runtime |
| Privileged mode | **Not required** |
| Host mounts | `/input` (ro), `/output` (rw) only |
| Secrets | None in image; API keys via env at runtime if using internal gateway |
| Package source | PyPI `memla` or bank-scanned image import |

### SBOM / image provenance

| Artifact | Location |
| --- | --- |
| Dockerfile | `Dockerfile.aml-replay` |
| Python dependencies | `pyproject.toml` (requests, sympy) |
| Compose reference | `docker-compose.aml-tier-a.yml` |

Bank may: scan image in Quay/Twistlock, re-sign, import to internal registry — **expected**.

---

## 8. SOC 2 and vendor security (honest)

| Question | Answer |
| --- | --- |
| Memla SOC 2 Type II | **Not available at pilot stage** |
| Why pilot can proceed without it | **No client alert data custodied by Memla** in Tier A |
| Interim controls | Client-hosted deployment, zero egress, open Dockerfile, deterministic verifier auditable in source |
| Production productionization path | SOC 2 / ISO 27001 roadmap if vendor-hosted or shadow UI phases require it |

Do not tell IT Risk "we're SOC 2 compliant." Tell them **where data lives** and **what the container does**.

---

## 9. Installation runbook (summary)

### Prerequisites (client)

- [ ] Approved sandbox VM provisioned
- [ ] Docker or Podman allowed in sandbox zone
- [ ] Internal LLM path chosen (Ollama local **or** bank gateway)
- [ ] Alert export converted to Memla case JSONL (ETL template provided)
- [ ] Jump box access for Memla engineer if remote support desired

### Steps

1. Import or build `memla-aml-replay:0.2.0` from `Dockerfile.aml-replay`
2. Pull Ollama image if using Path A; load approved model weights into air-gapped registry
3. Mount `/input/alerts.jsonl` and `/output`
4. Run benchmark command (see compose file comments)
5. Collect report from `/output` — remains inside bank

**Memla engineer time:** 1–2 days once VM exists.

---

## 10. Timeline reality (McKinsey-aligned)

| Milestone | Typical duration | Owner |
| --- | --- | --- |
| Vendor registration + SOW | 2–4 weeks | Procurement |
| Sandbox architecture review | 4–6 months (net-new) | IT Risk / Architecture |
| Pre-approved non-prod VM reuse | 1–2 weeks | Platform |
| Memla install + replay | 1–2 days | Platform + Memla |
| Operations review | 1 week | AML Operations |

**Parallel-path recommendation:** Start IT Risk review **now** while Operations reviews verifier logic on Tier 0 public cases (no bank data, no install).

---

## 11. IT Risk FAQ

**Q: Why not SaaS?**  
A: Compliance — fuzzy sanctions matching requires real entity names; client-hosted avoids egress review for alert PII.

**Q: Can we use our existing internal LLM?**  
A: Yes — preferred at many Tier 2 banks. Memla speaks OpenAI-compatible APIs.

**Q: What if sandbox takes 6 months?**  
A: Tier 0 public benchmark proves verifier now. Tier A waits for VM. No fake 5-day pilot claim.

**Q: What ports open externally?**  
A: None in zero-egress mode.

**Q: Who patches the container?**  
A: Client imports updated image after bank vulnerability scan — standard third-party container process.

---

## 12. Reference files in repo

| File | Purpose |
| --- | --- |
| `Dockerfile.aml-replay` | Container build |
| `docker-compose.aml-tier-a.yml` | Reference compose (zero-egress option) |
| `memory_system/distillation/aml_disposition_benchmark.py` | Verifier source |
| `cases/aml_alert_public_eval_cases.jsonl` | Tier 0 test cases |
| `sales/aml_tier_a_data_handling_summary.md` | Legal/InfoSec summary |
| `sales/aml_mrm_defense_packet_outline.md` | MRM packet |

---

## 13. Contact for Thursday IT Risk review

Walk through: **verifier truth table → provenance layer → this deployment spec → zero-egress verification procedure.**

Do not sell. Show the architecture.
