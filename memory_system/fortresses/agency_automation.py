from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from ..ollama_client import ChatMessage, UniversalLLMClient
from .agency_fortress import (
    AGENCY_BOUNDARY_STOP,
    AGENCY_EXECUTE_VERIFY,
    AGENCY_FORTRESS_ID,
    AGENCY_GROUND_AFFORDANCES,
    AGENCY_OBSERVE_STATE,
    AGENCY_PROMPT_CAPSULE,
    AGENCY_REPAIR,
    AGENCY_SELECT_ACTION,
    AGENCY_TRANSFER,
)
from .coding_fortress import (
    MUTATION_CROSS_DOMAIN,
    MUTATION_MUTATED,
    MUTATION_SAME,
    MUTATION_SIBLING,
)
from .meta_fortress import GlobalTransmutationLedger, TransferLedgerEntry


AGENCY_AUTOMATION_ID = "agency_meta_automation_v0"
DEFAULT_AGENCY_AUTOMATION_TEACHER_PROVIDER = "gemini"
DEFAULT_AGENCY_AUTOMATION_TEACHER_MODEL = "gemini-2.0-flash-lite"

CONSTRAINT_STATUS_GROUNDED = "grounded"
CONSTRAINT_STATUS_UNGROUNDED = "ungrounded"
CONSTRAINT_STATUS_BLOCKED = "blocked"
CONSTRAINT_STATUS_UNKNOWN = "unknown"

CONSTRAINT_STATUSES = {
    CONSTRAINT_STATUS_GROUNDED,
    CONSTRAINT_STATUS_UNGROUNDED,
    CONSTRAINT_STATUS_BLOCKED,
    CONSTRAINT_STATUS_UNKNOWN,
}

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_BOUNDARY = "boundary"


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_BOUNDARY_TERMS = {
    "book",
    "buy",
    "charge",
    "confirm",
    "delete",
    "pay",
    "payment",
    "place order",
    "purchase",
    "request",
    "schedule",
    "send",
    "submit",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _slug(value: str, *, limit: int = 54) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return (text or "agency")[:limit].strip("_") or "agency"


def _hash(*parts: Any, limit: int = 12) -> str:
    blob = "\n".join(str(part or "") for part in parts)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:limit]


def _dedupe(values: list[str] | tuple[str, ...] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        value = _clean(raw)
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _rough_token_count(value: Any) -> int:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value or "")
    return max(1, int(len(text) / 4))


def _normalize_text(value: Any) -> str:
    text = _clean(value).lower().replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9$.\s]+", " ", text)
    return " ".join(text.split())


def _recover_json_object(raw: str) -> tuple[dict[str, Any], str]:
    text = str(raw or "").strip()
    if not text:
        return {}, "empty"
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload, "json"
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(text[start : end + 1])
            if isinstance(payload, dict):
                return payload, "json_recovered"
        except json.JSONDecodeError:
            pass
    return {}, "text_fallback"


@dataclass(frozen=True)
class DynamicConstraintAtom:
    constraint_id: str
    label: str
    kind: str = "semantic"
    value: str = ""
    source: str = "prompt"
    criticality: str = "required"
    confidence: float = 0.0
    status: str = CONSTRAINT_STATUS_UNGROUNDED
    evidence_needed: list[str] = field(default_factory=list)
    grounding_queries: list[str] = field(default_factory=list)
    verifier: list[str] = field(default_factory=list)
    repair_policy: list[str] = field(default_factory=list)
    transfer_families: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "DynamicConstraintAtom":
        status = _clean(self.status).lower() or CONSTRAINT_STATUS_UNGROUNDED
        if status not in CONSTRAINT_STATUSES:
            status = CONSTRAINT_STATUS_UNGROUNDED
        label = _clean(self.label)
        kind = _clean(self.kind).lower() or "semantic"
        constraint_id = _clean(self.constraint_id) or f"c_{_slug(kind)}_{_hash(label, self.value)}"
        return DynamicConstraintAtom(
            constraint_id=constraint_id,
            label=label,
            kind=kind,
            value=_clean(self.value),
            source=_clean(self.source) or "prompt",
            criticality=_clean(self.criticality).lower() or "required",
            confidence=round(max(0.0, min(float(self.confidence or 0.0), 1.0)), 4),
            status=status,
            evidence_needed=_dedupe(self.evidence_needed),
            grounding_queries=_dedupe(self.grounding_queries),
            verifier=_dedupe(self.verifier),
            repair_policy=_dedupe(self.repair_policy),
            transfer_families=_dedupe(self.transfer_families),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DynamicConstraintAtom":
        data = dict(payload or {})
        return cls(
            constraint_id=str(data.get("constraint_id") or ""),
            label=str(data.get("label") or ""),
            kind=str(data.get("kind") or "semantic"),
            value=str(data.get("value") or ""),
            source=str(data.get("source") or "prompt"),
            criticality=str(data.get("criticality") or "required"),
            confidence=float(data.get("confidence") or 0.0),
            status=str(data.get("status") or CONSTRAINT_STATUS_UNGROUNDED),
            evidence_needed=[str(item) for item in list(data.get("evidence_needed") or [])],
            grounding_queries=[str(item) for item in list(data.get("grounding_queries") or [])],
            verifier=[str(item) for item in list(data.get("verifier") or [])],
            repair_policy=[str(item) for item in list(data.get("repair_policy") or [])],
            transfer_families=[str(item) for item in list(data.get("transfer_families") or [])],
            metadata=dict(data.get("metadata") or {}),
        ).normalized()


@dataclass(frozen=True)
class ConfusionSignal:
    confusion_id: str
    prompt: str
    app_family: str = ""
    page_kind: str = ""
    observation: str = ""
    blocked_constraint: str = ""
    known_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    failed_actions: list[str] = field(default_factory=list)
    uncertainty_type: str = "unknown_constraint_family"
    risk_level: str = RISK_MEDIUM
    teacher_required: bool = True
    teacher_reason: str = ""
    generated_ts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "ConfusionSignal":
        prompt = _clean(self.prompt)
        observation = _clean(self.observation)
        uncertainty = _clean(self.uncertainty_type).lower() or "unknown_constraint_family"
        risk = _clean(self.risk_level).lower() or RISK_MEDIUM
        if risk not in {RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_BOUNDARY}:
            risk = RISK_MEDIUM
        confusion_id = _clean(self.confusion_id) or f"conf_{_slug(uncertainty)}_{_hash(prompt, observation)}"
        return ConfusionSignal(
            confusion_id=confusion_id,
            prompt=prompt,
            app_family=_clean(self.app_family).lower(),
            page_kind=_clean(self.page_kind).lower(),
            observation=observation,
            blocked_constraint=_clean(self.blocked_constraint),
            known_evidence=_dedupe(self.known_evidence),
            missing_evidence=_dedupe(self.missing_evidence),
            failed_actions=_dedupe(self.failed_actions),
            uncertainty_type=uncertainty,
            risk_level=risk,
            teacher_required=bool(self.teacher_required),
            teacher_reason=_clean(self.teacher_reason),
            generated_ts=int(self.generated_ts or time.time()),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())


@dataclass(frozen=True)
class MicroFortressPlan:
    micro_fortress_id: str
    parent_fortress_id: str
    source_confusion_id: str
    title: str
    objective: str
    app_family: str
    task_class: str
    phases: list[str] = field(default_factory=list)
    constraint_atoms: list[DynamicConstraintAtom] = field(default_factory=list)
    cases: list[dict[str, Any]] = field(default_factory=list)
    mutation_axes: list[str] = field(default_factory=list)
    clearance_gates: list[str] = field(default_factory=list)
    acceptance_tests: list[str] = field(default_factory=list)
    teacher_prompt_budget: dict[str, int] = field(default_factory=dict)
    prior_suggestions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "MicroFortressPlan":
        objective = _clean(self.objective)
        micro_id = _clean(self.micro_fortress_id) or f"micro_{_slug(self.task_class)}_{_hash(self.source_confusion_id, objective)}"
        return MicroFortressPlan(
            micro_fortress_id=micro_id,
            parent_fortress_id=_clean(self.parent_fortress_id) or AGENCY_AUTOMATION_ID,
            source_confusion_id=_clean(self.source_confusion_id),
            title=_clean(self.title) or "Agency micro-fortress",
            objective=objective,
            app_family=_clean(self.app_family).lower() or "unknown",
            task_class=_clean(self.task_class).lower() or "agency_confusion",
            phases=_dedupe(self.phases),
            constraint_atoms=[atom.normalized() for atom in self.constraint_atoms],
            cases=[dict(case or {}) for case in self.cases],
            mutation_axes=_dedupe(self.mutation_axes),
            clearance_gates=_dedupe(self.clearance_gates),
            acceptance_tests=_dedupe(self.acceptance_tests),
            teacher_prompt_budget=dict(self.teacher_prompt_budget or {}),
            prior_suggestions=list(self.prior_suggestions or []),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        plan = self.normalized()
        return {
            "micro_fortress_id": plan.micro_fortress_id,
            "parent_fortress_id": plan.parent_fortress_id,
            "source_confusion_id": plan.source_confusion_id,
            "title": plan.title,
            "objective": plan.objective,
            "app_family": plan.app_family,
            "task_class": plan.task_class,
            "phases": list(plan.phases),
            "constraint_atoms": [atom.to_dict() for atom in plan.constraint_atoms],
            "cases": list(plan.cases),
            "mutation_axes": list(plan.mutation_axes),
            "clearance_gates": list(plan.clearance_gates),
            "acceptance_tests": list(plan.acceptance_tests),
            "teacher_prompt_budget": dict(plan.teacher_prompt_budget),
            "prior_suggestions": list(plan.prior_suggestions),
            "metadata": dict(plan.metadata),
        }


@dataclass(frozen=True)
class CompressedTransmutation:
    rule_id: str
    source_confusion_id: str
    micro_fortress_id: str
    constraint_family: str
    transmutation: str
    action_schema: str
    constraints_before: list[str] = field(default_factory=list)
    constraints_after: list[str] = field(default_factory=list)
    observation_cues: list[str] = field(default_factory=list)
    verifier: list[str] = field(default_factory=list)
    repair_policy: list[str] = field(default_factory=list)
    boundary_policy: list[str] = field(default_factory=list)
    transfer_targets: list[str] = field(default_factory=list)
    acceptance_tests: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_model: str = ""
    source_teacher_trace_id: str = ""
    raw_trace_excerpt: str = ""
    generated_ts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "CompressedTransmutation":
        transmutation = _clean(self.transmutation)
        family = _clean(self.constraint_family).lower() or "agency_constraint"
        rule_id = _clean(self.rule_id) or f"atm_{_slug(family)}_{_hash(transmutation, self.action_schema)}"
        return CompressedTransmutation(
            rule_id=rule_id,
            source_confusion_id=_clean(self.source_confusion_id),
            micro_fortress_id=_clean(self.micro_fortress_id),
            constraint_family=family,
            transmutation=transmutation,
            action_schema=_clean(self.action_schema),
            constraints_before=_dedupe(self.constraints_before),
            constraints_after=_dedupe(self.constraints_after),
            observation_cues=_dedupe(self.observation_cues),
            verifier=_dedupe(self.verifier),
            repair_policy=_dedupe(self.repair_policy),
            boundary_policy=_dedupe(self.boundary_policy),
            transfer_targets=_dedupe(self.transfer_targets),
            acceptance_tests=_dedupe(self.acceptance_tests),
            confidence=round(max(0.0, min(float(self.confidence or 0.0), 1.0)), 4),
            source_model=_clean(self.source_model),
            source_teacher_trace_id=_clean(self.source_teacher_trace_id),
            raw_trace_excerpt=_clean(self.raw_trace_excerpt)[:900],
            generated_ts=int(self.generated_ts or time.time()),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    def to_ledger_entry(self, *, app_family: str, phase: str = AGENCY_TRANSFER) -> TransferLedgerEntry:
        item = self.normalized()
        tier = MUTATION_CROSS_DOMAIN if item.transfer_targets else MUTATION_MUTATED
        return TransferLedgerEntry(
            entry_id=f"entry_{_hash(item.rule_id, item.source_confusion_id, item.micro_fortress_id)}",
            rule_id=item.rule_id,
            transmutation=item.transmutation,
            action_family=item.action_schema,
            source_fortress=item.micro_fortress_id,
            source_phase=phase,
            target_fortress=AGENCY_FORTRESS_ID,
            target_phase=phase,
            mutation_tier=tier,
            domain="agency",
            repo_family=app_family,
            constraints_before=item.constraints_before,
            constraints_after=item.constraints_after,
            preconditions=item.observation_cues + item.boundary_policy,
            verifier=item.verifier,
            retrieval_sources=["teacher_micro_fortress", "meta_fortress_confusion_bank"],
            score=item.confidence,
            outcome="teacher_extracted",
            negative_transfer=False,
            teacher_trace_id=item.source_teacher_trace_id,
            student_trace_id="",
            source_model=item.source_model,
            student_model="",
            metadata={
                "source_confusion_id": item.source_confusion_id,
                "constraint_family": item.constraint_family,
                "repair_policy": item.repair_policy,
                "acceptance_tests": item.acceptance_tests,
            },
        ).normalized()


def agency_automation_architecture_spec() -> dict[str, Any]:
    return {
        "automation_id": AGENCY_AUTOMATION_ID,
        "purpose": "Meta-fortress automation loop for turning live agency confusion into teacher-cleared micro-fortresses and compressed transmutation rules.",
        "happy_path": {
            "cli": "memla agency automate --api-key $GEMINI_API_KEY",
            "env_only": "GEMINI_API_KEY=... memla agency automate",
            "default_teacher_provider": DEFAULT_AGENCY_AUTOMATION_TEACHER_PROVIDER,
            "default_teacher_model": DEFAULT_AGENCY_AUTOMATION_TEACHER_MODEL,
        },
        "components": [
            {
                "name": "local_agent_runtime",
                "job": "small model proposes reversible actions from retrieved transmutation rules and current UI evidence",
            },
            {
                "name": "dynamic_constraint_graph",
                "job": "turn prompts and observations into constraint atoms that can be grounded, verified, repaired, or blocked",
            },
            {
                "name": "confusion_detector",
                "job": "detect when Memla cannot safely transmute a constraint, including missing evidence, failed action deltas, and boundary risk",
            },
            {
                "name": "meta_fortress_router",
                "job": "connect confusion to the global transmutation ledger, retrieve priors, and decide whether teacher help is needed",
            },
            {
                "name": "micro_fortress_factory",
                "job": "generate a focused fortress with same, mutated, sibling, boundary, and transfer cases around the missing constraint family",
            },
            {
                "name": "teacher_lane",
                "job": "ask the strongest available model to clear the micro-fortress with observable why-traces only",
            },
            {
                "name": "trace_compressor",
                "job": "compress raw teacher traces into constraint families, action schemas, verifiers, repair policies, and transfer targets",
            },
            {
                "name": "global_transmutation_ledger",
                "job": "promote compressed rules only after support, confidence, and negative-transfer gates are met",
            },
            {
                "name": "budget_controller",
                "job": "keep raw traces cold, retrieve only top rules, and spend teacher tokens only on unresolved constraint families",
            },
        ],
        "loop": [
            "capture prompt, page kind, observation, candidates, failures, and missing evidence",
            "infer dynamic constraint atoms",
            "classify confusion and risk",
            "retrieve active priors from the global ledger",
            "if priors ground the constraint, continue locally",
            "if not, spin a micro-fortress",
            "call teacher once for the micro-fortress",
            "compress teacher trace into reusable transmutation rules",
            "write artifacts and ledger entries",
            "future local runs retrieve the compressed rule instead of calling the teacher",
        ],
        "hard_gates": [
            "no irreversible action without explicit human boundary approval",
            "no transmutation accepted without visible evidence or a verifier",
            "no silent substitution when a user constraint is unavailable",
            "no repeated blind click after a failed state transition",
            "no promotion when negative-transfer residuals exceed the ledger threshold",
        ],
    }


def infer_app_family(prompt: str, observation: str = "") -> str:
    text = _normalize_text(f"{prompt} {observation}")
    if "doordash" in text or "door dash" in text:
        return "doordash"
    if "uber eats" in text or "ubereats" in text:
        return "ubereats"
    if "uber" in text or "lyft" in text:
        return "rideshare"
    if "message" in text or "text " in text or "send " in text or "email" in text:
        return "messaging"
    if "calendar" in text or "schedule" in text:
        return "calendar"
    if "amazon" in text or "instacart" in text or "cart" in text:
        return "commerce"
    return "agency"


def _constraint(
    *,
    kind: str,
    label: str,
    value: str = "",
    confidence: float,
    status: str = CONSTRAINT_STATUS_UNGROUNDED,
    criticality: str = "required",
    evidence_needed: list[str] | None = None,
    verifier: list[str] | None = None,
    repair_policy: list[str] | None = None,
    transfer_families: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DynamicConstraintAtom:
    return DynamicConstraintAtom(
        constraint_id=f"c_{_slug(kind)}_{_hash(label, value)}",
        label=label,
        kind=kind,
        value=value,
        confidence=confidence,
        status=status,
        criticality=criticality,
        evidence_needed=evidence_needed or [],
        grounding_queries=[label, value] if value else [label],
        verifier=verifier or [],
        repair_policy=repair_policy or [],
        transfer_families=transfer_families or [],
        metadata=metadata or {},
    ).normalized()


def infer_dynamic_constraints(prompt: str, observation: str = "") -> list[DynamicConstraintAtom]:
    raw = _clean(prompt)
    text = _normalize_text(raw)
    constraints: list[DynamicConstraintAtom] = []
    app_family = infer_app_family(prompt, observation)
    if app_family != "agency":
        constraints.append(
            _constraint(
                kind="service",
                label=f"service/app family must remain {app_family}",
                value=app_family,
                confidence=0.9,
                evidence_needed=["visible app or URL evidence matches requested service"],
                verifier=["page family remains compatible with requested service"],
                transfer_families=["service routing", "merchant search"],
            )
        )

    restaurant = ""
    restaurant_match = re.search(r"\bfrom\s+([^,.]+?)(?:\s+with|\s+and|\s+but|\s+stop|\s+to\b|$)", raw, flags=re.IGNORECASE)
    if restaurant_match:
        restaurant = _clean(restaurant_match.group(1))
        constraints.append(
            _constraint(
                kind="entity",
                label=f"merchant/entity must match {restaurant}",
                value=restaurant,
                confidence=0.88,
                evidence_needed=["merchant card, title, URL, or cart summary names the requested entity"],
                verifier=["selected merchant/entity text matches prompt before item selection"],
                repair_policy=["if candidate is ambiguous, inspect context instead of tapping the first result"],
                transfer_families=["exact entity match", "ranked candidate selection"],
            )
        )

    size_match = re.search(r"\b(x[\s-]?large|extra large|large|medium|small)\b", text)
    if size_match:
        size = size_match.group(1).replace(" ", "-")
        constraints.append(
            _constraint(
                kind="option",
                label=f"size option must be {size}",
                value=size,
                confidence=0.92,
                evidence_needed=["selected option or cart line shows requested size"],
                verifier=["requested size is visible after option selection and before cart commit"],
                repair_policy=["if default size differs, select requested size before toppings or add-to-cart"],
                transfer_families=["required option group", "selected-state verification"],
            )
        )

    number_value = 0
    number_source = ""
    for word, value in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text):
            number_value = value
            number_source = word
            break
    digit_match = re.search(r"(?<![$.])\b([2-9]|10)\b(?![.\d])", text)
    if digit_match:
        number_value = int(digit_match.group(1))
        number_source = digit_match.group(1)
    if number_value > 1:
        constraints.append(
            _constraint(
                kind="numeric",
                label=f"quantity must equal {number_value}",
                value=str(number_value),
                confidence=0.86,
                evidence_needed=[
                    "quantity control shows the requested count",
                    "cart summary shows the requested count",
                ],
                verifier=[
                    f"visible quantity equals {number_value} in item modal or cart",
                    "price alone is not accepted as quantity evidence",
                ],
                repair_policy=[
                    "find plus/minus, stepper, dropdown, or duplicate-item control",
                    "after changing quantity, re-inspect and compare visible count",
                    "if no count evidence exists, stop and request clarification before checkout",
                ],
                transfer_families=["numeric cardinality preservation", "cart verification"],
                metadata={"source_token": number_source},
            )
        )

    item_match = re.search(
        r"\b(?:get|order|buy|grab|doordash|uber eats)\s+(?:me\s+)?(.+?)(?:\s+from\b|\s+with\b|\s+and\b|\s+but\b|\s+stop\b|$)",
        raw,
        flags=re.IGNORECASE,
    )
    if item_match:
        item = _clean(item_match.group(1))
        item = re.sub(r"^(?:a|an|the|me)\s+", "", item, flags=re.IGNORECASE)
        item = re.sub(
            r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|[0-9]+|x[\s-]?large|extra large|large|medium|small)\b",
            "",
            item,
            flags=re.IGNORECASE,
        )
        item = _clean(item)
        if item:
            constraints.append(
                _constraint(
                    kind="exact_match",
                    label=f"requested item must match {item}",
                    value=item,
                    confidence=0.82,
                    evidence_needed=["item card, item modal, or cart line contains requested item terms"],
                    verifier=["selected item evidence matches the prompt before commit"],
                    repair_policy=["prefer exact menu item over coupon, bundle, category, or nearby similar item"],
                    transfer_families=["semantic item candidate selection", "exact variant match"],
                )
            )

    modifier_match = re.search(r"\bwith\s+(.+?)(?:\s+and\s+stop|\s+stop|\s+but|\s+checkout|$)", raw, flags=re.IGNORECASE)
    if modifier_match:
        modifiers = _clean(modifier_match.group(1))
        if modifiers and not modifiers.lower().startswith(("no ", "without ")):
            constraints.append(
                _constraint(
                    kind="modifier",
                    label=f"modifiers/toppings must include {modifiers}",
                    value=modifiers,
                    confidence=0.82,
                    evidence_needed=["selected modifier rows include all requested terms"],
                    verifier=["each requested modifier is visible as selected before cart commit"],
                    repair_policy=["handle hidden options, side choosers, and duplicate modifier groups explicitly"],
                    transfer_families=["modifier traversal", "multi-option preservation"],
                )
            )

    if re.search(r"\b(no|without|remove|hold)\b", text):
        constraints.append(
            _constraint(
                kind="negative_option",
                label="requested removals or exclusions must be preserved",
                value="",
                confidence=0.78,
                evidence_needed=["customizer or cart shows excluded/default-removed option"],
                verifier=["removed ingredient or excluded default is visible before commit"],
                repair_policy=["if removal evidence cannot be seen, stop instead of assuming default was removed"],
                transfer_families=["negative constraint preservation", "default option repair"],
            )
        )

    boundary_requested = re.search(r"\b(stop before|do not|don't|dont|but not|without (?:paying|sending|booking)|checkout)\b", text)
    boundary_visible = any(term in _normalize_text(observation) for term in _BOUNDARY_TERMS)
    if boundary_requested or boundary_visible:
        constraints.append(
            _constraint(
                kind="boundary",
                label="irreversible action boundary must not be crossed",
                value="stop_before_final_confirmation",
                confidence=0.97,
                status=CONSTRAINT_STATUS_UNGROUNDED,
                evidence_needed=["final purchase/send/request/submit control is classified as boundary"],
                verifier=["no final purchase, send, request, delete, or submit action is executed"],
                repair_policy=["if boundary control is nearby, emit stop or ask_user rather than tap"],
                transfer_families=["irreversible boundary stop", "human confirmation gate"],
            )
        )

    return [atom.normalized() for atom in constraints]


def detect_confusion(
    *,
    prompt: str,
    constraints: list[DynamicConstraintAtom],
    observation: str = "",
    app_family: str = "",
    page_kind: str = "",
    known_evidence: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    failed_actions: list[str] | None = None,
) -> ConfusionSignal:
    normalized_observation = _normalize_text(observation)
    known = _dedupe(known_evidence or [])
    missing = _dedupe(missing_evidence or [])
    failed = _dedupe(failed_actions or [])
    ungrounded = [atom for atom in constraints if atom.status != CONSTRAINT_STATUS_GROUNDED]

    def _blocked_label_for_kind(kind: str) -> str:
        found = next((atom for atom in ungrounded if atom.kind == kind), None)
        return found.label if found else ""

    blocked_constraint = ungrounded[0].label if ungrounded else ""
    all_text = _normalize_text(" ".join([prompt, observation, " ".join(missing), " ".join(failed)]))

    if any(atom.kind == "numeric" for atom in ungrounded) or "quantity" in all_text:
        uncertainty = "ungrounded_numeric_constraint"
        risk = RISK_MEDIUM
        reason = "numeric intent needs visible count evidence before action can be trusted"
        blocked_constraint = _blocked_label_for_kind("numeric") or blocked_constraint
    elif any(atom.kind == "exact_match" for atom in ungrounded) and ("specific" in all_text or "variant" in all_text):
        uncertainty = "exact_variant_ambiguity"
        risk = RISK_MEDIUM
        reason = "requested exact item or variant lacks decisive candidate evidence"
        blocked_constraint = _blocked_label_for_kind("exact_match") or blocked_constraint
    elif any(atom.kind == "boundary" for atom in ungrounded) or any(term in normalized_observation for term in _BOUNDARY_TERMS):
        uncertainty = "irreversible_boundary_nearby"
        risk = RISK_BOUNDARY
        reason = "boundary action is visible or requested stop must be enforced"
        blocked_constraint = _blocked_label_for_kind("boundary") or blocked_constraint
    elif failed:
        uncertainty = "post_action_transition_unclear"
        risk = RISK_MEDIUM
        reason = "previous action did not produce a verified state delta"
    elif "login" in all_text or "captcha" in all_text or "bot" in all_text:
        uncertainty = "manual_auth_or_bot_gate"
        risk = RISK_HIGH
        reason = "authentication or bot-check state requires manual bridge"
    elif not observation:
        uncertainty = "cold_start_constraint_discovery"
        risk = RISK_MEDIUM
        reason = "no live state evidence is available yet"
    else:
        uncertainty = "unknown_constraint_family"
        risk = RISK_MEDIUM
        reason = "constraint is not grounded by current evidence or active priors"

    teacher_required = bool(ungrounded or failed or risk in {RISK_HIGH, RISK_BOUNDARY})
    return ConfusionSignal(
        confusion_id=f"conf_{_slug(uncertainty)}_{_hash(prompt, observation, blocked_constraint)}",
        prompt=prompt,
        app_family=app_family or infer_app_family(prompt, observation),
        page_kind=page_kind,
        observation=observation,
        blocked_constraint=blocked_constraint,
        known_evidence=known,
        missing_evidence=missing or [item for atom in ungrounded for item in atom.evidence_needed[:2]],
        failed_actions=failed,
        uncertainty_type=uncertainty,
        risk_level=risk,
        teacher_required=teacher_required,
        teacher_reason=reason,
        metadata={"ungrounded_constraint_count": len(ungrounded)},
    ).normalized()


def _case_payload(
    *,
    case_id: str,
    prompt: str,
    app_family: str,
    mutation_tier: str,
    focus: str,
    expected_action_family: str,
    required_evidence: list[str],
    verifier: list[str],
    mutation_axes: list[str],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "prompt": prompt,
        "app_family": app_family,
        "mutation_tier": mutation_tier,
        "focus_constraint": focus,
        "expected_action_family": expected_action_family,
        "required_evidence": _dedupe(required_evidence),
        "forbidden_actions": [
            "place order",
            "pay now",
            "submit order",
            "confirm order",
            "send",
            "request ride",
            "delete",
        ],
        "verifier": _dedupe(verifier),
        "mutation_axes": _dedupe(mutation_axes),
    }


def build_micro_fortress_plan(
    *,
    confusion: ConfusionSignal,
    constraints: list[DynamicConstraintAtom],
    ledger: GlobalTransmutationLedger | None = None,
    prior_limit: int = 5,
) -> MicroFortressPlan:
    signal = confusion.normalized()
    atoms = [atom.normalized() for atom in constraints]
    focus_atom = next((atom for atom in atoms if atom.label == signal.blocked_constraint), atoms[0] if atoms else None)
    focus = focus_atom.label if focus_atom else signal.blocked_constraint or signal.uncertainty_type
    family = focus_atom.kind if focus_atom else signal.uncertainty_type
    app_family = signal.app_family or infer_app_family(signal.prompt, signal.observation)
    prior_suggestions = []
    if ledger is not None:
        prior_suggestions = ledger.suggest_priors(
            prompt=f"{signal.prompt} {focus}",
            phase=AGENCY_TRANSFER,
            domain="agency",
            limit=prior_limit,
        )

    gates = [
        "every action must name the constraint it preserves",
        "each preserved constraint must have visible evidence or an explicit missing-evidence stop",
        "after a tap/type/scroll action, re-inspect before advancing",
        "irreversible actions are boundary actions unless human approval is explicit",
        "teacher trace must include verifier and repair policy, not only next click",
    ]
    phases = [
        AGENCY_PROMPT_CAPSULE,
        AGENCY_OBSERVE_STATE,
        AGENCY_GROUND_AFFORDANCES,
        AGENCY_SELECT_ACTION,
        AGENCY_EXECUTE_VERIFY,
        AGENCY_REPAIR,
        AGENCY_BOUNDARY_STOP,
        AGENCY_TRANSFER,
    ]
    verifier = list(focus_atom.verifier if focus_atom else []) or [
        "visible evidence satisfies the blocked constraint",
        "agent stops if evidence cannot be grounded",
    ]
    evidence = list(focus_atom.evidence_needed if focus_atom else []) or list(signal.missing_evidence)
    action_family = {
        "numeric": "numeric constraint grounding and cart verification",
        "exact_match": "exact item or variant disambiguation",
        "modifier": "modifier option traversal and selected-state verification",
        "negative_option": "negative option preservation",
        "boundary": "irreversible boundary stop",
    }.get(family, "unknown constraint grounding")
    cases = [
        _case_payload(
            case_id=f"{signal.confusion_id}_same",
            prompt=signal.prompt,
            app_family=app_family,
            mutation_tier=MUTATION_SAME,
            focus=focus,
            expected_action_family=action_family,
            required_evidence=evidence,
            verifier=verifier,
            mutation_axes=["same app", "current page-kind", "visible evidence required"],
        ),
        _case_payload(
            case_id=f"{signal.confusion_id}_mutated",
            prompt=f"Resolve the same constraint when the control is hidden, renamed, or split across modal and cart: {focus}",
            app_family=app_family,
            mutation_tier=MUTATION_MUTATED,
            focus=focus,
            expected_action_family=action_family,
            required_evidence=evidence + ["post-action state delta is observed"],
            verifier=verifier + ["failed action causes inspect/repair rather than blind retry"],
            mutation_axes=["hidden control", "renamed label", "stale DOM index"],
        ),
        _case_payload(
            case_id=f"{signal.confusion_id}_sibling",
            prompt=f"Transfer the same constraint to a sibling consumer app: {focus}",
            app_family="ubereats" if app_family == "doordash" else "sibling_app",
            mutation_tier=MUTATION_SIBLING,
            focus=focus,
            expected_action_family=action_family,
            required_evidence=evidence + ["app-specific labels are not assumed"],
            verifier=verifier + ["constraint is preserved despite different UI grammar"],
            mutation_axes=["sibling app", "different labels", "same user intent"],
        ),
        _case_payload(
            case_id=f"{signal.confusion_id}_boundary",
            prompt=f"Stop safely if {focus} cannot be verified before a final confirmation boundary.",
            app_family=app_family,
            mutation_tier=MUTATION_CROSS_DOMAIN,
            focus=focus,
            expected_action_family="missing-evidence boundary stop",
            required_evidence=["missing evidence is explicitly named", "boundary action is blocked"],
            verifier=["no irreversible action executed", "ask_user or stop is emitted with missing evidence"],
            mutation_axes=["missing verifier", "checkout/send/request boundary", "manual bridge"],
        ),
    ]
    plan_payload = {
        "signal": signal.to_dict(),
        "constraints": [atom.to_dict() for atom in atoms],
        "cases": cases,
        "gates": gates,
        "priors": prior_suggestions,
    }
    budget = {
        "estimated_teacher_input_tokens": _rough_token_count(plan_payload) + 900,
        "estimated_teacher_output_tokens": 1800,
        "estimated_compressed_rule_tokens": 320,
        "case_count": len(cases),
    }
    return MicroFortressPlan(
        micro_fortress_id=f"micro_{_slug(signal.uncertainty_type)}_{_hash(signal.confusion_id, focus)}",
        parent_fortress_id=AGENCY_AUTOMATION_ID,
        source_confusion_id=signal.confusion_id,
        title=f"Micro-fortress: {signal.uncertainty_type.replace('_', ' ')}",
        objective=f"Teach Memla how to ground and verify: {focus}",
        app_family=app_family,
        task_class=signal.uncertainty_type,
        phases=phases,
        constraint_atoms=atoms,
        cases=cases,
        mutation_axes=["same", "mutated", "sibling", "cross-domain boundary"],
        clearance_gates=gates,
        acceptance_tests=[
            "compressed rule includes evidence requirements",
            "compressed rule includes verifier",
            "compressed rule includes repair policy",
            "compressed rule includes transfer target or explicit no-transfer boundary",
        ],
        teacher_prompt_budget=budget,
        prior_suggestions=prior_suggestions,
        metadata={"blocked_constraint": focus, "constraint_family": family},
    ).normalized()


def build_teacher_messages(*, plan: MicroFortressPlan, confusion: ConfusionSignal) -> list[ChatMessage]:
    normalized_plan = plan.normalized()
    payload = {
        "automation_id": AGENCY_AUTOMATION_ID,
        "mode": "teacher_micro_fortress_clearance",
        "instruction": (
            "Clear this agency micro-fortress. Emit only JSON. Every transmutation must explain how constraints "
            "are grounded in visible evidence, which reversible action schema follows, how to verify it, how to "
            "repair failure, and when to stop or ask the user."
        ),
        "confusion": confusion.to_dict(),
        "micro_fortress": normalized_plan.to_dict(),
        "output_schema": {
            "teacher_trace_id": "string",
            "constraint_family": "numeric | exact_match | modifier | boundary | unknown",
            "root_cause": "string",
            "transmutations": [
                {
                    "transmutation": "string",
                    "action_schema": "string",
                    "constraints_before": ["string"],
                    "constraints_after": ["string"],
                    "observation_cues": ["string"],
                    "verifier": ["string"],
                    "repair_policy": ["string"],
                    "boundary_policy": ["string"],
                    "transfer_targets": ["string"],
                    "acceptance_tests": ["string"],
                    "confidence": 0.0,
                }
            ],
            "fortress_mutations": ["string"],
            "teacher_stop_conditions": ["string"],
        },
    }
    system = (
        "You are the teacher lane inside Memla's meta fortress. You produce observable transmutation logic, "
        "not hidden chain-of-thought. Your output is a compact JSON object only. Never recommend crossing "
        "payment, send, booking, delete, or submit boundaries without explicit human approval."
    )
    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=json.dumps(payload, indent=2, sort_keys=True)),
    ]


def _confidence_from_transmutation(item: dict[str, Any]) -> float:
    score = 0.45
    if item.get("constraints_after"):
        score += 0.1
    if item.get("observation_cues"):
        score += 0.1
    if item.get("verifier"):
        score += 0.15
    if item.get("repair_policy"):
        score += 0.1
    if item.get("boundary_policy"):
        score += 0.05
    if item.get("transfer_targets"):
        score += 0.05
    raw = item.get("confidence")
    try:
        raw_score = float(raw)
    except (TypeError, ValueError):
        raw_score = 0.0
    if raw_score:
        score = (score + raw_score) / 2
    return round(max(0.0, min(score, 0.97)), 4)


def compress_teacher_response(
    *,
    raw_response: str,
    parse_mode: str,
    plan: MicroFortressPlan,
    confusion: ConfusionSignal,
    teacher_model: str,
) -> list[CompressedTransmutation]:
    payload, recovered_mode = _recover_json_object(raw_response)
    mode = recovered_mode if recovered_mode != "empty" else parse_mode
    plan = plan.normalized()
    signal = confusion.normalized()
    trace_id = _clean(payload.get("teacher_trace_id")) or f"teacher_{_hash(raw_response, plan.micro_fortress_id)}"
    family = _clean(payload.get("constraint_family")) or str(plan.metadata.get("constraint_family") or signal.uncertainty_type)
    raw_items = payload.get("transmutations")
    if not isinstance(raw_items, list) or not raw_items:
        raw_items = [
            {
                "transmutation": _clean(payload.get("root_cause")) or _clean(raw_response)[:300] or plan.objective,
                "action_schema": str(plan.metadata.get("blocked_constraint") or "unknown constraint grounding"),
                "constraints_before": [signal.blocked_constraint] if signal.blocked_constraint else [],
                "constraints_after": ["constraint is either visibly grounded or execution stops"],
                "observation_cues": signal.known_evidence + signal.missing_evidence,
                "verifier": ["visible evidence satisfies the blocked constraint"],
                "repair_policy": ["if evidence is missing, ask_user or stop before irreversible action"],
                "boundary_policy": ["never cross final confirmation while evidence is missing"],
                "transfer_targets": [],
                "acceptance_tests": plan.acceptance_tests,
            }
        ]
    compressed: list[CompressedTransmutation] = []
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            raw_item = {"transmutation": str(raw_item)}
        transmutation = _clean(raw_item.get("transmutation")) or plan.objective
        action_schema = _clean(raw_item.get("action_schema")) or str(plan.metadata.get("blocked_constraint") or plan.task_class)
        item_family = _clean(raw_item.get("constraint_family")) or family
        confidence = _confidence_from_transmutation(raw_item)
        compressed.append(
            CompressedTransmutation(
                rule_id=f"atm_{_slug(item_family)}_{_hash(transmutation, action_schema, index)}",
                source_confusion_id=signal.confusion_id,
                micro_fortress_id=plan.micro_fortress_id,
                constraint_family=item_family,
                transmutation=transmutation,
                action_schema=action_schema,
                constraints_before=[str(x) for x in list(raw_item.get("constraints_before") or [])],
                constraints_after=[str(x) for x in list(raw_item.get("constraints_after") or [])],
                observation_cues=[str(x) for x in list(raw_item.get("observation_cues") or [])],
                verifier=[str(x) for x in list(raw_item.get("verifier") or [])],
                repair_policy=[str(x) for x in list(raw_item.get("repair_policy") or [])],
                boundary_policy=[str(x) for x in list(raw_item.get("boundary_policy") or [])],
                transfer_targets=[str(x) for x in list(raw_item.get("transfer_targets") or [])],
                acceptance_tests=[str(x) for x in list(raw_item.get("acceptance_tests") or plan.acceptance_tests)],
                confidence=confidence,
                source_model=teacher_model,
                source_teacher_trace_id=trace_id,
                raw_trace_excerpt=raw_response[:900],
                metadata={
                    "parse_mode": mode,
                    "root_cause": _clean(payload.get("root_cause")),
                    "fortress_mutations": [str(x) for x in list(payload.get("fortress_mutations") or [])],
                    "teacher_stop_conditions": [str(x) for x in list(payload.get("teacher_stop_conditions") or [])],
                },
            ).normalized()
        )
    return compressed


def run_agency_automation(
    *,
    prompt: str,
    observation: str = "",
    app_family: str = "",
    page_kind: str = "",
    known_evidence: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    failed_actions: list[str] | None = None,
    teacher_model: str = DEFAULT_AGENCY_AUTOMATION_TEACHER_MODEL,
    teacher_client: UniversalLLMClient | None = None,
    temperature: float = 0.1,
    num_ctx: int | None = None,
    dry_run: bool = False,
    ledger: GlobalTransmutationLedger | None = None,
) -> dict[str, Any]:
    resolved_app_family = app_family or infer_app_family(prompt, observation)
    constraints = infer_dynamic_constraints(prompt, observation)
    signal = detect_confusion(
        prompt=prompt,
        constraints=constraints,
        observation=observation,
        app_family=resolved_app_family,
        page_kind=page_kind,
        known_evidence=known_evidence,
        missing_evidence=missing_evidence,
        failed_actions=failed_actions,
    )
    working_ledger = ledger or GlobalTransmutationLedger()
    plan = build_micro_fortress_plan(confusion=signal, constraints=constraints, ledger=working_ledger)
    messages = build_teacher_messages(plan=plan, confusion=signal)

    raw_response = ""
    teacher_parse_mode = "skipped_dry_run"
    compressed: list[CompressedTransmutation] = []
    failures: list[dict[str, Any]] = []
    if not dry_run:
        if teacher_client is None:
            raise RuntimeError("teacher_client is required unless dry_run=True.")
        try:
            raw_response = teacher_client.chat(
                model=teacher_model,
                messages=messages,
                temperature=temperature,
                num_ctx=num_ctx,
            )
            _, teacher_parse_mode = _recover_json_object(raw_response)
            compressed = compress_teacher_response(
                raw_response=raw_response,
                parse_mode=teacher_parse_mode,
                plan=plan,
                confusion=signal,
                teacher_model=teacher_model,
            )
            for item in compressed:
                working_ledger.add_entry(item.to_ledger_entry(app_family=resolved_app_family))
        except Exception as exc:  # pragma: no cover - exercised through CLI/live use.
            failures.append(
                {
                    "stage": "teacher_micro_fortress",
                    "error": str(exc),
                    "micro_fortress_id": plan.micro_fortress_id,
                }
            )
            teacher_parse_mode = "teacher_error"

    promotion_decisions = working_ledger.promotion_decisions(min_support=1, min_confidence=0.6, require_tier=MUTATION_MUTATED)
    active_rules = [decision.rule.to_dict() for decision in promotion_decisions if decision.promote and decision.rule is not None]
    return {
        "automation_id": AGENCY_AUTOMATION_ID,
        "generated_ts": int(time.time()),
        "teacher_model": teacher_model,
        "teacher_call_status": "skipped_dry_run" if dry_run else ("failed" if failures else "completed"),
        "teacher_parse_mode": teacher_parse_mode,
        "prompt": _clean(prompt),
        "observation": _clean(observation),
        "constraint_count": len(constraints),
        "ungrounded_constraint_count": int(signal.metadata.get("ungrounded_constraint_count", 0)),
        "constraints": [atom.to_dict() for atom in constraints],
        "confusion": signal.to_dict(),
        "micro_fortress": plan.to_dict(),
        "teacher_messages": [{"role": message.role, "content": message.content} for message in messages],
        "raw_teacher_response": raw_response,
        "compressed_transmutations": [item.to_dict() for item in compressed],
        "compressed_transmutation_count": len(compressed),
        "ledger": working_ledger.to_dict(),
        "ledger_summary": working_ledger.summarize(),
        "promotion_decisions": [decision.to_dict() for decision in promotion_decisions],
        "active_rules": active_rules,
        "failure_count": len(failures),
        "failures": failures,
        "architecture_spec": agency_automation_architecture_spec(),
    }


def render_agency_automation_markdown(report: dict[str, Any]) -> str:
    confusion = dict(report.get("confusion") or {})
    micro = dict(report.get("micro_fortress") or {})
    budget = dict(micro.get("teacher_prompt_budget") or {})
    lines = [
        "# Agency Automation Meta-Fortress",
        "",
        f"- Automation: `{report.get('automation_id', AGENCY_AUTOMATION_ID)}`",
        f"- Teacher status: `{report.get('teacher_call_status', '')}`",
        f"- Teacher model: `{report.get('teacher_model', '')}`",
        f"- Constraint count: `{report.get('constraint_count', 0)}`",
        f"- Ungrounded constraints: `{report.get('ungrounded_constraint_count', 0)}`",
        f"- Confusion type: `{confusion.get('uncertainty_type', '')}`",
        f"- Risk: `{confusion.get('risk_level', '')}`",
        f"- Micro-fortress: `{micro.get('micro_fortress_id', '')}`",
        "",
        "## Objective",
        "",
        str(micro.get("objective") or ""),
        "",
        "## Budget",
        "",
        f"- Estimated teacher input tokens: `{budget.get('estimated_teacher_input_tokens', 0)}`",
        f"- Estimated teacher output tokens: `{budget.get('estimated_teacher_output_tokens', 0)}`",
        f"- Estimated compressed rule tokens: `{budget.get('estimated_compressed_rule_tokens', 0)}`",
        "",
        "## Clearance Gates",
        "",
    ]
    lines.extend(f"- {gate}" for gate in list(micro.get("clearance_gates") or []))
    lines.extend(["", "## Generated Cases", ""])
    for case in list(micro.get("cases") or []):
        lines.append(f"- `{case.get('case_id', '')}`: {case.get('focus_constraint', '')} [{case.get('mutation_tier', '')}]")
    lines.extend(["", "## Compressed Rules", ""])
    for rule in list(report.get("compressed_transmutations") or []):
        lines.append(f"- `{rule.get('rule_id', '')}` ({rule.get('constraint_family', '')}, confidence {rule.get('confidence', 0.0)}): {rule.get('transmutation', '')}")
    if not report.get("compressed_transmutations"):
        lines.append("- No teacher-compressed rules yet. Run without `--dry-run` to call the teacher lane.")
    lines.extend(["", "## Ledger", ""])
    ledger_summary = dict(report.get("ledger_summary") or {})
    lines.append(f"- Entries: `{ledger_summary.get('entry_count', 0)}`")
    lines.append(f"- Rules: `{ledger_summary.get('rule_count', 0)}`")
    lines.append(f"- Negative transfer: `{ledger_summary.get('negative_transfer_count', 0)}`")
    return "\n".join(lines).rstrip() + "\n"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def write_agency_automation_artifacts(*, report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "agency_automation_report.json"
    markdown_path = out / "agency_automation_report.md"
    micro_path = out / "micro_fortress_plan.json"
    constraints_path = out / "dynamic_constraints.jsonl"
    compressed_path = out / "compressed_transmutation_bank.jsonl"
    ledger_path = out / "global_transmutation_ledger.json"
    spec_path = out / "agency_automation_architecture.json"

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_agency_automation_markdown(report), encoding="utf-8")
    micro_path.write_text(json.dumps(report.get("micro_fortress") or {}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_jsonl(constraints_path, [dict(item) for item in list(report.get("constraints") or [])])
    write_jsonl(compressed_path, [dict(item) for item in list(report.get("compressed_transmutations") or [])])
    ledger_path.write_text(json.dumps(report.get("ledger") or {}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    spec_path.write_text(json.dumps(agency_automation_architecture_spec(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "report_json": str(report_path),
        "report_markdown": str(markdown_path),
        "micro_fortress_json": str(micro_path),
        "constraints_jsonl": str(constraints_path),
        "compressed_bank_jsonl": str(compressed_path),
        "ledger_json": str(ledger_path),
        "architecture_json": str(spec_path),
    }
