from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..ollama_client import ChatMessage
from .patch_execution_benchmark import _build_llm_client


AML_DISPOSITION_SYSTEM = """
You are an AML alert disposition analyst.

Given an alert, customer profile, screening hits, collected evidence, and control thresholds,
choose the best bounded disposition action.

Return strict JSON only with this shape:
{
  "decision": "clear|reject|escalate|request_docs",
  "predicted_rule_hits": ["fuzzy_name_only"],
  "next_actions": ["document_entity_difference"],
  "evidence_updates": {"identity_verified": true},
  "audit_narrative": "short audit-ready explanation",
  "rationale": "short explanation"
}

Rules:
- Use "clear" only when the alert is a false positive or fully resolved with supporting evidence.
- Use "reject" when a hard screening hit is confirmed and the relationship must be blocked.
- Use "escalate" when supervisor or L2 review is required before clearing or rejecting.
- Use "request_docs" only when missing documents or ownership evidence can create a compliant path.
- If no evidence update is needed, return an empty object for evidence_updates.
- Do not include markdown fences or extra prose.
""".strip()


KNOWN_RULE_IDS = (
    "exact_sanctions_match",
    "fuzzy_name_only",
    "jurisdiction_mismatch",
    "entity_type_mismatch",
    "pep_direct_match",
    "pep_associate_match",
    "adverse_media_confirmed",
    "identity_document_gap",
    "ubo_ownership_unclear",
    "jurisdiction_high_risk",
    "evidence_extraction_unverified",
    "evidence_contradiction",
)

TRUSTED_EVIDENCE_SOURCES = frozenset(
    {
        "analyst_confirmed",
        "idv_vendor",
        "core_system",
        "screening_engine",
    }
)
EVIDENCE_CONFIDENCE_FLOOR = 0.90

KNOWN_NEXT_ACTIONS = (
    "document_entity_difference",
    "request_identity_documents",
    "request_ubo_documentation",
    "route_to_l2_review",
    "request_sar_precheck",
    "block_relationship",
    "hold_pending_documents",
)

RULE_ID_ALIASES = {
    "exact_match": "exact_sanctions_match",
    "sanctions_exact_match": "exact_sanctions_match",
    "fuzzy_match": "fuzzy_name_only",
    "fuzzy_name_match": "fuzzy_name_only",
    "pep_direct": "pep_direct_match",
    "pep_associate": "pep_associate_match",
    "adverse_media": "adverse_media_confirmed",
    "identity_gap": "identity_document_gap",
    "ubo_gap": "ubo_ownership_unclear",
    "high_risk_jurisdiction": "jurisdiction_high_risk",
}

NEXT_ACTION_ALIASES = {
    "document_difference": "document_entity_difference",
    "request_id_documents": "request_identity_documents",
    "request_ubo_docs": "request_ubo_documentation",
    "l2_review": "route_to_l2_review",
    "sar_precheck": "request_sar_precheck",
    "block": "block_relationship",
    "hold_for_documents": "hold_pending_documents",
}

CLEARABLE_SOFT_RULES = frozenset(
    {
        "fuzzy_name_only",
        "jurisdiction_mismatch",
        "entity_type_mismatch",
    }
)


@dataclass(frozen=True)
class AmlDispositionCase:
    case_id: str
    prompt: str
    alert: dict[str, Any]
    customer: dict[str, Any]
    screening_hits: list[dict[str, Any]]
    evidence: dict[str, Any]
    controls: dict[str, Any]
    expected_outcome: str
    expected_rule_hits: list[str]
    expected_actions: list[str]
    expected_evidence_updates: dict[str, Any]


@dataclass(frozen=True)
class AmlRuleHit:
    rule_id: str
    severity: str
    message: str
    field: str = ""
    actual: str = ""
    threshold: str = ""


@dataclass(frozen=True)
class AmlDecision:
    decision: str
    predicted_rule_hits: list[str]
    next_actions: list[str]
    evidence_updates: dict[str, Any]
    audit_narrative: str
    rationale: str
    response_text: str
    parse_mode: str


@dataclass(frozen=True)
class AmlBacktestResult:
    rule_hits: list[AmlRuleHit]
    modified_rule_hits: list[AmlRuleHit]
    modified_evidence: dict[str, Any]
    compliance_passed: bool
    final_status: str
    residual_constraints: list[str]


@dataclass(frozen=True)
class AmlIterationTrace:
    iteration: int
    decision: str
    predicted_rule_hits: list[str]
    next_actions: list[str]
    evidence_updates: dict[str, Any]
    audit_narrative: str
    rationale: str
    parse_mode: str
    compliance_passed: bool
    final_status: str
    residual_constraints: list[str]


@dataclass(frozen=True)
class AmlDispositionBenchmarkRow:
    case_id: str
    prompt: str
    expected_outcome: str
    expected_rule_hits: list[str]
    expected_actions: list[str]
    expected_evidence_updates: dict[str, Any]
    actual_rule_hits: list[str]
    raw_decision: str
    raw_predicted_rule_hits: list[str]
    raw_next_actions: list[str]
    raw_evidence_updates: dict[str, Any]
    raw_rule_recall: float
    raw_action_recall: float
    raw_evidence_update_recall: float
    raw_outcome_match: float
    raw_backtest_passed: float
    raw_aml_utility: float
    raw_final_status: str
    raw_iteration_trace: list[dict[str, Any]]
    memla_decision: str
    memla_predicted_rule_hits: list[str]
    memla_next_actions: list[str]
    memla_evidence_updates: dict[str, Any]
    memla_rule_recall: float
    memla_action_recall: float
    memla_evidence_update_recall: float
    memla_outcome_match: float
    memla_backtest_passed: float
    memla_aml_utility: float
    memla_final_status: str
    memla_iteration_trace: list[dict[str, Any]]
    utility_delta: float


def _normalize_str_list(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = " ".join(str(value or "").strip().split())
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


def _normalize_label_token(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return clean.strip("_")


def _normalize_label_list(values: list[str], aliases: dict[str, str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _normalize_label_token(value)
        if not token:
            continue
        canonical = aliases.get(token, token)
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return out


def _normalize_rule(values: list[str]) -> list[str]:
    return _normalize_label_list(values, RULE_ID_ALIASES)


def _normalize_action(values: list[str]) -> list[str]:
    return _normalize_label_list(values, NEXT_ACTION_ALIASES)


def _extract_label_hits_from_text(
    text: str,
    *,
    known: tuple[str, ...],
    aliases: dict[str, str],
) -> list[str]:
    normalized_text = _normalize_label_token(text)
    if not normalized_text:
        return []
    candidates = list(known) + list(aliases.keys())
    hits = [candidate for candidate in candidates if candidate and candidate in normalized_text]
    return _normalize_label_list(hits, aliases)


def _score_overlap(predicted: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    predicted_set = {value.lower() for value in predicted}
    expected_set = {value.lower() for value in expected}
    return len(predicted_set & expected_set) / max(len(expected_set), 1)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def _field_provenance(evidence: dict[str, Any], field: str) -> dict[str, Any]:
    provenance = evidence.get("provenance")
    if not isinstance(provenance, dict):
        return {}
    field_blob = provenance.get(field)
    return dict(field_blob) if isinstance(field_blob, dict) else {}


def _trusted_evidence_flag(evidence: dict[str, Any], field: str) -> bool:
    if not _coerce_bool(evidence.get(field)):
        return False
    field_provenance = _field_provenance(evidence, field)
    if not field_provenance:
        return True
    source = str(field_provenance.get("source") or "").strip().lower()
    confidence = _coerce_float(field_provenance.get("confidence"), 1.0)
    if source and source not in TRUSTED_EVIDENCE_SOURCES:
        return False
    return confidence >= EVIDENCE_CONFIDENCE_FLOOR


def _evidence_contradictions(evidence: dict[str, Any]) -> list[str]:
    contradictions: list[str] = []
    raw = evidence.get("contradictions")
    if isinstance(raw, list):
        contradictions.extend(str(item).strip() for item in raw if str(item).strip())
    provenance = evidence.get("provenance")
    if isinstance(provenance, dict):
        raw_conflicts = provenance.get("conflicts")
        if isinstance(raw_conflicts, list):
            contradictions.extend(str(item).strip() for item in raw_conflicts if str(item).strip())
    return _normalize_str_list(contradictions)


def load_aml_disposition_cases(path: str) -> list[AmlDispositionCase]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    cases: list[AmlDispositionCase] = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        row = json.loads(clean)
        cases.append(
            AmlDispositionCase(
                case_id=str(row.get("case_id") or f"case_{len(cases) + 1}"),
                prompt=str(row.get("prompt") or "").strip(),
                alert=dict(row.get("alert") or {}),
                customer=dict(row.get("customer") or {}),
                screening_hits=list(row.get("screening_hits") or []),
                evidence=dict(row.get("evidence") or {}),
                controls=dict(row.get("controls") or {}),
                expected_outcome=str(row.get("expected_outcome") or "").strip().lower(),
                expected_rule_hits=_normalize_rule(list(row.get("expected_rule_hits") or [])),
                expected_actions=_normalize_action(list(row.get("expected_actions") or [])),
                expected_evidence_updates=dict(row.get("expected_evidence_updates") or {}),
            )
        )
    return cases


def _render_case_payload(case: AmlDispositionCase) -> str:
    payload = {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "alert": case.alert,
        "customer": case.customer,
        "screening_hits": case.screening_hits,
        "evidence": case.evidence,
        "controls": case.controls,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _dedupe_rule_hits(hits: list[AmlRuleHit]) -> list[AmlRuleHit]:
    out: list[AmlRuleHit] = []
    seen: set[str] = set()
    for hit in hits:
        if hit.rule_id in seen:
            continue
        seen.add(hit.rule_id)
        out.append(hit)
    return out


def evaluate_aml_alert_rules(case: AmlDispositionCase, evidence: dict[str, Any] | None = None) -> list[AmlRuleHit]:
    hits: list[AmlRuleHit] = []
    current_evidence = dict(evidence if evidence is not None else case.evidence)
    controls = case.controls
    customer = case.customer
    auto_clear_threshold = _coerce_float(controls.get("auto_clear_threshold"), 0.85)
    high_risk_jurisdictions = {
        str(item).strip().upper()
        for item in list(controls.get("high_risk_jurisdictions") or [])
        if str(item).strip()
    }
    customer_jurisdiction = str(customer.get("jurisdiction") or "").strip().upper()
    customer_entity_type = str(customer.get("entity_type") or "").strip().lower()

    for screening_hit in case.screening_hits:
        hit_type = str(screening_hit.get("hit_type") or "").strip().lower()
        match_score = _coerce_float(screening_hit.get("match_score"), 0.0)
        matched_name = str(screening_hit.get("matched_name") or "").strip()
        listed_jurisdiction = str(screening_hit.get("listed_jurisdiction") or "").strip().upper()
        listed_entity_type = str(screening_hit.get("entity_type") or "").strip().lower()
        exact_match = _coerce_bool(screening_hit.get("exact_match"))

        if hit_type == "sanctions":
            same_jurisdiction = bool(
                customer_jurisdiction
                and listed_jurisdiction
                and (
                    customer_jurisdiction == listed_jurisdiction
                    or customer_jurisdiction.startswith(listed_jurisdiction + "-")
                    or listed_jurisdiction.startswith(customer_jurisdiction + "-")
                )
            )
            if exact_match or (match_score >= auto_clear_threshold and same_jurisdiction):
                hits.append(
                    AmlRuleHit(
                        rule_id="exact_sanctions_match",
                        severity="hard",
                        message="Screening hit meets the exact-match or high-confidence same-jurisdiction threshold.",
                        field="match_score",
                        actual=str(match_score),
                        threshold=str(auto_clear_threshold),
                    )
                )
            elif match_score > 0.5:
                hits.append(
                    AmlRuleHit(
                        rule_id="fuzzy_name_only",
                        severity="soft",
                        message="Screening hit is below auto-clear threshold and requires analyst review.",
                        field="matched_name",
                        actual=matched_name,
                        threshold=str(auto_clear_threshold),
                    )
                )
                if listed_jurisdiction and customer_jurisdiction and not same_jurisdiction:
                    hits.append(
                        AmlRuleHit(
                            rule_id="jurisdiction_mismatch",
                            severity="soft",
                            message="Listed entity jurisdiction differs from the onboarded customer jurisdiction.",
                            field="jurisdiction",
                            actual=customer_jurisdiction,
                            threshold=listed_jurisdiction,
                        )
                    )
                if listed_entity_type and customer_entity_type and listed_entity_type != customer_entity_type:
                    hits.append(
                        AmlRuleHit(
                            rule_id="entity_type_mismatch",
                            severity="soft",
                            message="Listed entity type differs from the onboarded customer entity type.",
                            field="entity_type",
                            actual=customer_entity_type,
                            threshold=listed_entity_type,
                        )
                    )
        elif hit_type == "pep":
            if _coerce_bool(screening_hit.get("direct")):
                hits.append(
                    AmlRuleHit(
                        rule_id="pep_direct_match",
                        severity="hard",
                        message="Customer or control person matches a direct PEP record.",
                        field="matched_name",
                        actual=matched_name,
                    )
                )
            else:
                hits.append(
                    AmlRuleHit(
                        rule_id="pep_associate_match",
                        severity="soft",
                        message="Associate or board-linked PEP exposure requires escalation.",
                        field="matched_name",
                        actual=matched_name,
                    )
                )

    for contradiction in _evidence_contradictions(current_evidence):
        hits.append(
            AmlRuleHit(
                rule_id="evidence_contradiction",
                severity="soft",
                message=f"Evidence sources conflict: {contradiction}",
                field="provenance",
                actual=contradiction,
            )
        )

    identity_verified = _coerce_bool(current_evidence.get("identity_verified"))
    ubo_documented = _coerce_bool(current_evidence.get("ubo_documented"))
    if not identity_verified:
        hits.append(
            AmlRuleHit(
                rule_id="identity_document_gap",
                severity="soft",
                message="Identity verification is incomplete for this onboarding case.",
                field="identity_verified",
                actual="false",
            )
        )
    elif not _trusted_evidence_flag(current_evidence, "identity_verified"):
        hits.append(
            AmlRuleHit(
                rule_id="evidence_extraction_unverified",
                severity="soft",
                message="Identity verification flag is not backed by a trusted source or sufficient confidence.",
                field="identity_verified",
                actual=str(_field_provenance(current_evidence, "identity_verified").get("source") or "unknown"),
            )
        )
    if not ubo_documented:
        hits.append(
            AmlRuleHit(
                rule_id="ubo_ownership_unclear",
                severity="soft",
                message="Beneficial ownership documentation is missing or incomplete.",
                field="ubo_documented",
                actual="false",
            )
        )
    elif not _trusted_evidence_flag(current_evidence, "ubo_documented"):
        hits.append(
            AmlRuleHit(
                rule_id="evidence_extraction_unverified",
                severity="soft",
                message="UBO documentation flag is not backed by a trusted source or sufficient confidence.",
                field="ubo_documented",
                actual=str(_field_provenance(current_evidence, "ubo_documented").get("source") or "unknown"),
            )
        )

    for media_item in list(current_evidence.get("adverse_media") or []):
        if not isinstance(media_item, dict):
            continue
        if _coerce_bool(media_item.get("confirmed")):
            hits.append(
                AmlRuleHit(
                    rule_id="adverse_media_confirmed",
                    severity="hard",
                    message="Confirmed adverse media requires escalation or rejection.",
                    field="adverse_media",
                    actual=str(media_item.get("headline") or "confirmed_hit"),
                )
            )
            break

    if customer_jurisdiction in high_risk_jurisdictions:
        hits.append(
            AmlRuleHit(
                rule_id="jurisdiction_high_risk",
                severity="soft",
                message="Customer jurisdiction is on the configured high-risk list.",
                field="jurisdiction",
                actual=customer_jurisdiction,
            )
        )

    return _dedupe_rule_hits(hits)


def _apply_evidence_updates(evidence: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(evidence)
    for key, value in dict(updates or {}).items():
        merged[key] = value
    return merged


def backtest_aml_decision(case: AmlDispositionCase, decision: AmlDecision) -> AmlBacktestResult:
    initial_hits = evaluate_aml_alert_rules(case)
    residuals: list[str] = []
    modified_hits: list[AmlRuleHit] = []
    modified_evidence: dict[str, Any] = {}
    current_decision = str(decision.decision or "").strip().lower()
    hard_hits = [hit for hit in initial_hits if str(hit.severity or "").strip().lower() == "hard"]
    soft_hits = [hit for hit in initial_hits if str(hit.severity or "").strip().lower() == "soft"]
    soft_rule_ids = {hit.rule_id for hit in soft_hits}

    if current_decision == "clear":
        if hard_hits:
            compliance_passed = False
            final_status = "unsafe_clear_with_hard_hit"
            residuals.extend([f"hard_hit_blocks_clear:{hit.rule_id}" for hit in hard_hits])
        elif not soft_hits:
            compliance_passed = True
            final_status = "clear_ok"
        elif (
            soft_rule_ids.issubset(CLEARABLE_SOFT_RULES)
            and _trusted_evidence_flag(case.evidence, "identity_verified")
            and "evidence_contradiction" not in soft_rule_ids
            and "evidence_extraction_unverified" not in soft_rule_ids
        ):
            compliance_passed = True
            final_status = "clear_ok"
        else:
            compliance_passed = False
            final_status = "clear_insufficient_for_soft_hit"
            residuals.extend([f"soft_hit_requires_escalation_or_docs:{hit.rule_id}" for hit in soft_hits])
    elif current_decision == "reject":
        if hard_hits:
            compliance_passed = True
            final_status = "reject_ok"
        elif soft_hits:
            compliance_passed = False
            final_status = "overrejected_soft_review"
            residuals.extend([f"soft_review_prefers_escalation:{hit.rule_id}" for hit in soft_hits])
        else:
            compliance_passed = False
            final_status = "unnecessary_reject"
            residuals.append("no_triggered_rule_for_reject")
    elif current_decision == "escalate":
        if hard_hits:
            compliance_passed = False
            final_status = "escalation_insufficient_for_hard_hit"
            residuals.extend([f"hard_hit_requires_reject_or_docs:{hit.rule_id}" for hit in hard_hits])
        elif soft_hits:
            compliance_passed = True
            final_status = "escalate_ok"
        else:
            compliance_passed = False
            final_status = "unnecessary_escalation"
            residuals.append("no_triggered_rule_for_escalation")
    elif current_decision == "request_docs":
        doc_gap_rules = {"identity_document_gap", "ubo_ownership_unclear"}
        if not (soft_rule_ids & doc_gap_rules):
            compliance_passed = False
            final_status = "unnecessary_request_docs"
            residuals.append("no_document_gap_for_request_docs")
        elif not decision.evidence_updates:
            compliance_passed = False
            final_status = "missing_evidence_updates"
            residuals.append("missing_evidence_updates")
        else:
            modified_evidence = _apply_evidence_updates(case.evidence, decision.evidence_updates)
            modified_hits = evaluate_aml_alert_rules(case, modified_evidence)
            remaining_doc_gaps = {
                hit.rule_id for hit in modified_hits if hit.rule_id in doc_gap_rules
            }
            compliance_passed = not remaining_doc_gaps
            final_status = "request_docs_ok" if compliance_passed else "request_docs_still_blocked"
            if remaining_doc_gaps:
                residuals.extend([f"evidence_still_missing:{rule_id}" for rule_id in sorted(remaining_doc_gaps)])
    else:
        compliance_passed = False
        final_status = "invalid_decision"
        residuals.append("invalid_decision")

    return AmlBacktestResult(
        rule_hits=initial_hits,
        modified_rule_hits=modified_hits,
        modified_evidence=modified_evidence,
        compliance_passed=compliance_passed,
        final_status=final_status,
        residual_constraints=_normalize_str_list(residuals),
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    clean = str(text or "").strip()
    if not clean:
        return {}
    try:
        data = json.loads(clean)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _infer_decision_from_text(text: str) -> str:
    lower = str(text or "").lower()
    for decision in ("request_docs", "escalate", "reject", "clear"):
        if decision in lower:
            return decision
    return ""


def _normalize_evidence_updates(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    updates: dict[str, Any] = {}
    for key in ("identity_verified", "ubo_documented", "address_match"):
        if key not in value:
            continue
        updates[key] = _coerce_bool(value.get(key))
    return updates


def _normalize_decision_payload(payload: dict[str, Any], response: str) -> AmlDecision:
    normalized_rule_hits = _normalize_rule(list(payload.get("predicted_rule_hits") or []))
    if not normalized_rule_hits:
        normalized_rule_hits = _extract_label_hits_from_text(
            response,
            known=KNOWN_RULE_IDS,
            aliases=RULE_ID_ALIASES,
        )
    normalized_actions = _normalize_action(list(payload.get("next_actions") or []))
    if not normalized_actions:
        normalized_actions = _extract_label_hits_from_text(
            response,
            known=KNOWN_NEXT_ACTIONS,
            aliases=NEXT_ACTION_ALIASES,
        )
    decision = str(payload.get("decision") or "").strip().lower()
    if decision not in {"clear", "reject", "escalate", "request_docs"}:
        decision = _infer_decision_from_text(response)
    return AmlDecision(
        decision=decision if decision in {"clear", "reject", "escalate", "request_docs"} else "escalate",
        predicted_rule_hits=normalized_rule_hits,
        next_actions=normalized_actions,
        evidence_updates=_normalize_evidence_updates(payload.get("evidence_updates") or {}),
        audit_narrative=" ".join(str(payload.get("audit_narrative") or "").split()),
        rationale=" ".join(str(payload.get("rationale") or "").split()),
        response_text=str(response or ""),
        parse_mode="json" if payload else "heuristic",
    )


def _repair_decision_payload(
    *,
    client: Any,
    model: str,
    response: str,
    temperature: float,
    num_ctx: int | None,
) -> AmlDecision:
    repair_prompt = (
        "Convert the answer below into strict JSON only with the required shape.\n"
        "If a field is unknown, use empty arrays or an empty object.\n\n"
        "Answer to convert:\n"
        f"{response}"
    )
    repaired = client.chat(
        model=model,
        messages=[
            ChatMessage(role="system", content=AML_DISPOSITION_SYSTEM),
            ChatMessage(role="user", content=repair_prompt),
        ],
        temperature=min(float(temperature), 0.1),
        num_ctx=num_ctx,
    ).strip()
    decision = _normalize_decision_payload(_extract_json_object(repaired), repaired)
    parse_mode = "json_repair" if decision.parse_mode == "json" else "json_repair_heuristic"
    return AmlDecision(
        decision=decision.decision,
        predicted_rule_hits=decision.predicted_rule_hits,
        next_actions=decision.next_actions,
        evidence_updates=decision.evidence_updates,
        audit_narrative=decision.audit_narrative,
        rationale=decision.rationale,
        response_text=repaired,
        parse_mode=parse_mode,
    )


def _evidence_update_recall(actual: dict[str, Any], expected: dict[str, Any]) -> float:
    if not expected:
        return 1.0
    matched = 0
    for key, expected_value in expected.items():
        if key not in actual:
            continue
        actual_value = actual.get(key)
        if isinstance(expected_value, bool):
            if _coerce_bool(actual_value) == bool(expected_value):
                matched += 1
        elif str(actual_value).strip().lower() == str(expected_value).strip().lower():
            matched += 1
    return matched / max(len(expected), 1)


def _aml_utility(
    *,
    outcome_match: float,
    backtest_passed: float,
    rule_recall: float,
    action_recall: float,
    evidence_update_recall: float,
) -> float:
    # Safety-first weighting: verifier pass dominates outcome match because an
    # unsafe clear on a hard hit is a sanctions exposure, not a disposition miss.
    utility = (
        (0.20 * float(outcome_match))
        + (0.45 * float(backtest_passed))
        + (0.20 * float(rule_recall))
        + (0.10 * float(action_recall))
        + (0.05 * float(evidence_update_recall))
    )
    return round(float(utility), 4)


def _query_aml_decision(
    *,
    client: Any,
    model: str,
    case: AmlDispositionCase,
    temperature: float,
    num_ctx: int | None,
    residual_constraints: list[str] | None = None,
    prior_trace: list[dict[str, Any]] | None = None,
) -> AmlDecision:
    user_parts = [
        "Evaluate this AML alert disposition state and return the best bounded action.",
        _render_case_payload(case),
    ]
    if residual_constraints:
        user_parts.append(
            "Verifier residual constraints from the previous attempt:\n"
            + json.dumps(list(residual_constraints), indent=2)
        )
    if prior_trace:
        user_parts.append("Prior attempts:\n" + json.dumps(prior_trace, indent=2))
    response = client.chat(
        model=model,
        messages=[
            ChatMessage(role="system", content=AML_DISPOSITION_SYSTEM),
            ChatMessage(role="user", content="\n\n".join(user_parts)),
        ],
        temperature=temperature,
        num_ctx=num_ctx,
    ).strip()
    payload = _extract_json_object(response)
    decision = _normalize_decision_payload(payload, response)
    if decision.parse_mode == "heuristic":
        repaired = _repair_decision_payload(
            client=client,
            model=model,
            response=response,
            temperature=temperature,
            num_ctx=num_ctx,
        )
        if repaired.parse_mode != "heuristic":
            return repaired
    return decision


def _decision_loop(
    *,
    client: Any,
    model: str,
    case: AmlDispositionCase,
    iterations: int,
    temperature: float,
    num_ctx: int | None,
) -> tuple[AmlDecision, AmlBacktestResult, list[dict[str, Any]]]:
    last_decision = AmlDecision(
        decision="escalate",
        predicted_rule_hits=[],
        next_actions=[],
        evidence_updates={},
        audit_narrative="",
        rationale="",
        response_text="",
        parse_mode="empty",
    )
    last_backtest = AmlBacktestResult(
        rule_hits=[],
        modified_rule_hits=[],
        modified_evidence={},
        compliance_passed=False,
        final_status="not_run",
        residual_constraints=["not_run"],
    )
    traces: list[dict[str, Any]] = []
    residual_constraints: list[str] = []

    for iteration in range(1, max(iterations, 1) + 1):
        decision = _query_aml_decision(
            client=client,
            model=model,
            case=case,
            temperature=temperature,
            num_ctx=num_ctx,
            residual_constraints=residual_constraints if residual_constraints else None,
            prior_trace=traces if traces else None,
        )
        backtest = backtest_aml_decision(case, decision)
        traces.append(
            asdict(
                AmlIterationTrace(
                    iteration=iteration,
                    decision=decision.decision,
                    predicted_rule_hits=decision.predicted_rule_hits,
                    next_actions=decision.next_actions,
                    evidence_updates=decision.evidence_updates,
                    audit_narrative=decision.audit_narrative,
                    rationale=decision.rationale,
                    parse_mode=decision.parse_mode,
                    compliance_passed=backtest.compliance_passed,
                    final_status=backtest.final_status,
                    residual_constraints=backtest.residual_constraints,
                )
            )
        )
        last_decision = decision
        last_backtest = backtest
        residual_constraints = list(backtest.residual_constraints)
        if backtest.compliance_passed:
            break
    return last_decision, last_backtest, traces


def run_aml_disposition_benchmark(
    *,
    cases_path: str,
    case_ids: list[str] | None = None,
    limit: int | None = None,
    raw_model: str,
    memla_model: str,
    raw_iterations: int = 1,
    memla_iterations: int = 3,
    temperature: float = 0.1,
    num_ctx: int | None = None,
    raw_provider: str = "",
    raw_base_url: str = "",
    memla_provider: str = "",
    memla_base_url: str = "",
) -> dict[str, Any]:
    cases = load_aml_disposition_cases(cases_path)
    if case_ids:
        wanted = {str(case_id).strip().lower() for case_id in case_ids if str(case_id).strip()}
        cases = [case for case in cases if case.case_id.strip().lower() in wanted]
    if limit is not None and int(limit) >= 0:
        cases = cases[: int(limit)]
    raw_client = _build_llm_client(provider=raw_provider or None, base_url=raw_base_url or None)
    memla_client = _build_llm_client(provider=memla_provider or None, base_url=memla_base_url or None)
    rows: list[AmlDispositionBenchmarkRow] = []
    failures: list[dict[str, Any]] = []

    for case in cases:
        try:
            actual_rule_hits = _normalize_rule([hit.rule_id for hit in evaluate_aml_alert_rules(case)])
            raw_decision, raw_backtest, raw_trace = _decision_loop(
                client=raw_client,
                model=raw_model,
                case=case,
                iterations=max(raw_iterations, 1),
                temperature=temperature,
                num_ctx=num_ctx,
            )
            memla_decision, memla_backtest, memla_trace = _decision_loop(
                client=memla_client,
                model=memla_model,
                case=case,
                iterations=max(memla_iterations, 1),
                temperature=temperature,
                num_ctx=num_ctx,
            )

            raw_rule_recall = _score_overlap(raw_decision.predicted_rule_hits, case.expected_rule_hits)
            memla_rule_recall = _score_overlap(memla_decision.predicted_rule_hits, case.expected_rule_hits)
            raw_action_recall = _score_overlap(raw_decision.next_actions, case.expected_actions)
            memla_action_recall = _score_overlap(memla_decision.next_actions, case.expected_actions)
            raw_evidence_recall = _evidence_update_recall(raw_decision.evidence_updates, case.expected_evidence_updates)
            memla_evidence_recall = _evidence_update_recall(memla_decision.evidence_updates, case.expected_evidence_updates)
            raw_outcome_match = 1.0 if raw_decision.decision == case.expected_outcome else 0.0
            memla_outcome_match = 1.0 if memla_decision.decision == case.expected_outcome else 0.0
            raw_backtest_passed = 1.0 if raw_backtest.compliance_passed else 0.0
            memla_backtest_passed = 1.0 if memla_backtest.compliance_passed else 0.0
            raw_utility = _aml_utility(
                outcome_match=raw_outcome_match,
                backtest_passed=raw_backtest_passed,
                rule_recall=raw_rule_recall,
                action_recall=raw_action_recall,
                evidence_update_recall=raw_evidence_recall,
            )
            memla_utility = _aml_utility(
                outcome_match=memla_outcome_match,
                backtest_passed=memla_backtest_passed,
                rule_recall=memla_rule_recall,
                action_recall=memla_action_recall,
                evidence_update_recall=memla_evidence_recall,
            )

            rows.append(
                AmlDispositionBenchmarkRow(
                    case_id=case.case_id,
                    prompt=case.prompt,
                    expected_outcome=case.expected_outcome,
                    expected_rule_hits=list(case.expected_rule_hits),
                    expected_actions=list(case.expected_actions),
                    expected_evidence_updates=dict(case.expected_evidence_updates),
                    actual_rule_hits=actual_rule_hits,
                    raw_decision=raw_decision.decision,
                    raw_predicted_rule_hits=list(raw_decision.predicted_rule_hits),
                    raw_next_actions=list(raw_decision.next_actions),
                    raw_evidence_updates=dict(raw_decision.evidence_updates),
                    raw_rule_recall=round(raw_rule_recall, 4),
                    raw_action_recall=round(raw_action_recall, 4),
                    raw_evidence_update_recall=round(raw_evidence_recall, 4),
                    raw_outcome_match=round(raw_outcome_match, 4),
                    raw_backtest_passed=round(raw_backtest_passed, 4),
                    raw_aml_utility=raw_utility,
                    raw_final_status=raw_backtest.final_status,
                    raw_iteration_trace=list(raw_trace),
                    memla_decision=memla_decision.decision,
                    memla_predicted_rule_hits=list(memla_decision.predicted_rule_hits),
                    memla_next_actions=list(memla_decision.next_actions),
                    memla_evidence_updates=dict(memla_decision.evidence_updates),
                    memla_rule_recall=round(memla_rule_recall, 4),
                    memla_action_recall=round(memla_action_recall, 4),
                    memla_evidence_update_recall=round(memla_evidence_recall, 4),
                    memla_outcome_match=round(memla_outcome_match, 4),
                    memla_backtest_passed=round(memla_backtest_passed, 4),
                    memla_aml_utility=memla_utility,
                    memla_final_status=memla_backtest.final_status,
                    memla_iteration_trace=list(memla_trace),
                    utility_delta=round(memla_utility - raw_utility, 4),
                )
            )
        except Exception as exc:
            failures.append(
                {
                    "case_id": case.case_id,
                    "prompt": case.prompt,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    count = max(len(rows), 1)
    avg_raw_utility = round(sum(row.raw_aml_utility for row in rows) / count, 4)
    avg_memla_utility = round(sum(row.memla_aml_utility for row in rows) / count, 4)
    utility_index = round(avg_memla_utility / avg_raw_utility, 4) if avg_raw_utility > 0 else None

    def _unsafe_clear_attempts(lane: str) -> int:
        total = 0
        for row in rows:
            traces = row.raw_iteration_trace if lane == "raw" else row.memla_iteration_trace
            for trace in traces:
                if str(trace.get("final_status") or "") == "unsafe_clear_with_hard_hit":
                    total += 1
        return total

    case_by_id = {
        case.case_id: case
        for case in load_aml_disposition_cases(cases_path)
        if case.case_id in {row.case_id for row in rows}
    }
    hard_hit_case_ids = [
        row.case_id
        for row in rows
        if row.case_id in case_by_id
        and any(
            hit.rule_id in {"exact_sanctions_match", "pep_direct_match", "adverse_media_confirmed"}
            for hit in evaluate_aml_alert_rules(case_by_id[row.case_id])
        )
    ]
    memla_cleared_hard_hit_cases = [
        row.case_id
        for row in rows
        if row.case_id in hard_hit_case_ids and row.memla_decision == "clear" and row.memla_backtest_passed >= 1.0
    ]

    return {
        "generated_ts": int(time.time()),
        "cases_path": str(Path(cases_path).resolve()),
        "case_ids": list(case_ids or []),
        "limit": limit,
        "raw_model": raw_model,
        "memla_model": memla_model,
        "raw_provider": raw_client.provider,
        "memla_provider": memla_client.provider,
        "cases": len(rows),
        "cases_requested": len(cases),
        "failed_case_count": len(failures),
        "avg_raw_outcome_match": round(sum(row.raw_outcome_match for row in rows) / count, 4),
        "avg_raw_rule_recall": round(sum(row.raw_rule_recall for row in rows) / count, 4),
        "avg_raw_action_recall": round(sum(row.raw_action_recall for row in rows) / count, 4),
        "avg_raw_backtest_passed": round(sum(row.raw_backtest_passed for row in rows) / count, 4),
        "avg_raw_aml_utility": avg_raw_utility,
        "avg_memla_outcome_match": round(sum(row.memla_outcome_match for row in rows) / count, 4),
        "avg_memla_rule_recall": round(sum(row.memla_rule_recall for row in rows) / count, 4),
        "avg_memla_action_recall": round(sum(row.memla_action_recall for row in rows) / count, 4),
        "avg_memla_backtest_passed": round(sum(row.memla_backtest_passed for row in rows) / count, 4),
        "avg_memla_aml_utility": avg_memla_utility,
        "memla_vs_raw_aml_utility_index": utility_index,
        "pilot_safety_summary": {
            "utility_weights": {
                "outcome_match": 0.20,
                "backtest_passed": 0.45,
                "rule_recall": 0.20,
                "action_recall": 0.10,
                "evidence_update_recall": 0.05,
            },
            "pilot_gate_note": "Utility is a ranking metric. Pilot go/no-go uses hard gates: zero cleared hard-hit cases, zero verifier-passed clears on hard-hit cases.",
            "hard_hit_case_count": len(hard_hit_case_ids),
            "raw_unsafe_clear_attempts": _unsafe_clear_attempts("raw"),
            "memla_unsafe_clear_attempts": _unsafe_clear_attempts("memla"),
            "memla_cleared_hard_hit_cases": memla_cleared_hard_hit_cases,
            "pilot_hard_hit_gate_passed": len(memla_cleared_hard_hit_cases) == 0,
        },
        "rows": [asdict(row) for row in rows],
        "failed_cases": failures,
    }


def render_aml_disposition_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AML Alert Disposition Benchmark",
        "",
        f"- Raw provider: `{report.get('raw_provider', 'unknown')}`",
        f"- Memla provider: `{report.get('memla_provider', 'unknown')}`",
        f"- Raw model: `{report.get('raw_model', 'unknown')}`",
        f"- Memla model: `{report.get('memla_model', 'unknown')}`",
        f"- Cases completed: `{report.get('cases', 0)}` / `{report.get('cases_requested', 0)}`",
        "",
        "## Lane summary",
        "",
        "| Metric | Raw | Memla |",
        "| --- | --- | --- |",
        f"| Outcome match | `{report.get('avg_raw_outcome_match', 0.0)}` | `{report.get('avg_memla_outcome_match', 0.0)}` |",
        f"| Rule recall | `{report.get('avg_raw_rule_recall', 0.0)}` | `{report.get('avg_memla_rule_recall', 0.0)}` |",
        f"| Action recall | `{report.get('avg_raw_action_recall', 0.0)}` | `{report.get('avg_memla_action_recall', 0.0)}` |",
        f"| Backtest passed | `{report.get('avg_raw_backtest_passed', 0.0)}` | `{report.get('avg_memla_backtest_passed', 0.0)}` |",
        f"| AML utility | `{report.get('avg_raw_aml_utility', 0.0)}` | `{report.get('avg_memla_aml_utility', 0.0)}` |",
    ]
    utility_index = report.get("memla_vs_raw_aml_utility_index")
    if utility_index is not None:
        lines.extend(["", f"- Memla vs raw AML utility index: `{utility_index}`"])
    safety = dict(report.get("pilot_safety_summary") or {})
    if safety:
        lines.extend(
            [
                "",
                "## Pilot safety summary",
                "",
                f"- Hard-hit case count: `{safety.get('hard_hit_case_count', 0)}`",
                f"- Raw unsafe clear attempts: `{safety.get('raw_unsafe_clear_attempts', 0)}`",
                f"- Memla unsafe clear attempts: `{safety.get('memla_unsafe_clear_attempts', 0)}`",
                f"- Memla cleared hard-hit cases: `{', '.join(safety.get('memla_cleared_hard_hit_cases') or []) or 'none'}`",
                f"- Hard-hit gate passed: `{safety.get('pilot_hard_hit_gate_passed', False)}`",
                "",
                "Utility weights (ranking only): "
                + ", ".join(
                    f"{key} `{value}`"
                    for key, value in dict(safety.get("utility_weights") or {}).items()
                ),
                "",
                str(safety.get("pilot_gate_note") or "").strip(),
            ]
        )
    if report.get("failed_cases"):
        lines.extend(["", "## Failed cases", ""])
        for item in report.get("failed_cases", []):
            lines.append(f"- `{item.get('case_id', '')}` [{item.get('error_type', 'Error')}] {item.get('error', '')}")
    lines.extend(["", "## Case rows", ""])
    for row in report.get("rows", []):
        lines.extend(
            [
                f"### {row.get('case_id', '').strip()}",
                "",
                f"- Prompt: {row.get('prompt', '').strip()}",
                f"- Expected outcome: `{row.get('expected_outcome', '')}`",
                f"- Actual triggered rules: `{', '.join(row.get('actual_rule_hits', []))}`",
                f"- Raw decision: `{row.get('raw_decision', '')}` ({row.get('raw_final_status', '')})",
                f"- Memla decision: `{row.get('memla_decision', '')}` ({row.get('memla_final_status', '')})",
                f"- Raw utility: `{row.get('raw_aml_utility', 0.0)}`",
                f"- Memla utility: `{row.get('memla_aml_utility', 0.0)}`",
                f"- Utility delta: `{row.get('utility_delta', 0.0)}`",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"
