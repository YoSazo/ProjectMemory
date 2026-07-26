from __future__ import annotations

from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


CODING_UNDERSTAND = "coding_understand"
CODING_INFER_CHANGE = "coding_infer_change"
CODING_IMPLEMENT = "coding_implement"
CODING_VERIFY_REPAIR = "coding_verify_repair"
RETRIEVAL_GROUNDING = "retrieval_grounding"
META_TRANSFER = "meta_transfer"

CODING_FORTRESS_PHASES = (
    CODING_UNDERSTAND,
    CODING_INFER_CHANGE,
    CODING_IMPLEMENT,
    CODING_VERIFY_REPAIR,
    RETRIEVAL_GROUNDING,
    META_TRANSFER,
)

MUTATION_SAME = "same"
MUTATION_MUTATED = "mutated"
MUTATION_SIBLING = "sibling"
MUTATION_CROSS_DOMAIN = "cross_domain"

MUTATION_TIERS = (
    MUTATION_SAME,
    MUTATION_MUTATED,
    MUTATION_SIBLING,
    MUTATION_CROSS_DOMAIN,
)

SUCCESS_OUTCOMES = {"success", "passed", "ok", "verified"}

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
}

_SYNONYM_CANONICALS = {
    "auth": "authentication",
    "authenticated": "authentication",
    "authenticate": "authentication",
    "authorization": "authentication",
    "boundary": "boundary",
    "contract": "contract",
    "caller": "caller",
    "callers": "caller",
    "downstream": "downstream",
    "earlier": "early",
    "early": "early",
    "enforce": "enforcement",
    "enforced": "enforcement",
    "enforcement": "enforcement",
    "guard": "middleware",
    "middleware": "middleware",
    "request": "request",
    "requests": "request",
    "schema": "schema",
    "test": "verifier",
    "tests": "verifier",
    "typecheck": "verifier",
    "verify": "verifier",
    "verified": "verifier",
    "verifier": "verifier",
}


def _normalize_token(token: str) -> str:
    text = str(token or "").strip().lower().replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9+]+", " ", text)
    text = " ".join(text.split())
    if not text:
        return ""
    if text in _SYNONYM_CANONICALS:
        return _SYNONYM_CANONICALS[text]
    if text.endswith("ies") and len(text) > 4:
        text = text[:-3] + "y"
    elif text.endswith("ing") and len(text) > 5:
        text = text[:-3]
    elif text.endswith("ed") and len(text) > 4:
        text = text[:-2]
    elif text.endswith("es") and len(text) > 4:
        text = text[:-2]
    elif text.endswith("s") and len(text) > 3:
        text = text[:-1]
    return _SYNONYM_CANONICALS.get(text, text)


def _tokenize(value: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9_+-]+", value or ""):
        token = _normalize_token(raw)
        if len(token) >= 3 and token not in _STOPWORDS:
            tokens.add(token)
    return tokens


def _dedupe(values: list[str] | tuple[str, ...] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        clean = " ".join(str(raw or "").strip().split())
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


def _list_tokens(values: list[str] | tuple[str, ...] | None) -> set[str]:
    merged: set[str] = set()
    for value in values or []:
        merged.update(_tokenize(str(value or "")))
    return merged


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 4)


def _text_similarity(left: str, right: str) -> float:
    clean_left = " ".join(str(left or "").strip().lower().split())
    clean_right = " ".join(str(right or "").strip().lower().split())
    if not clean_left and not clean_right:
        return 1.0
    if not clean_left or not clean_right:
        return 0.0
    sequence = SequenceMatcher(None, clean_left, clean_right).ratio()
    token_overlap = _jaccard(_tokenize(clean_left), _tokenize(clean_right))
    return round((0.45 * sequence) + (0.55 * token_overlap), 4)


def _weighted_score(parts: dict[str, tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in parts.values())
    if total_weight <= 0:
        return 0.0
    score = sum(float(value) * float(weight) for value, weight in parts.values()) / total_weight
    return round(score, 4)


def _trace_hash(*parts: str) -> str:
    blob = "\n".join(str(part or "") for part in parts)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class TransmutationTrace:
    """Observable phase trace emitted by a teacher or student inside a fortress.

    This is intentionally not a free-form chain of thought. It captures the
    constraint motion we can score, distill, mutate, and transfer.
    """

    trace_id: str
    fortress_id: str
    phase: str
    model: str
    prompt: str
    constraints_before: list[str] = field(default_factory=list)
    constraints_after: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    transmutation: str = ""
    action_family: str = ""
    target_artifacts: list[str] = field(default_factory=list)
    retrieval_queries: list[str] = field(default_factory=list)
    retrieval_sources: list[str] = field(default_factory=list)
    verifier: list[str] = field(default_factory=list)
    residual_constraints: list[str] = field(default_factory=list)
    outcome: str = "unknown"
    mutation_tier: str = MUTATION_SAME
    domain: str = "coding"
    repo_family: str = ""
    source_trace_id: str = ""
    generated_ts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "TransmutationTrace":
        phase = str(self.phase or "").strip() or CODING_INFER_CHANGE
        mutation_tier = str(self.mutation_tier or MUTATION_SAME).strip()
        if mutation_tier not in MUTATION_TIERS:
            mutation_tier = MUTATION_SAME
        trace_id = str(self.trace_id or "").strip()
        if not trace_id:
            trace_id = _trace_hash(
                self.fortress_id,
                phase,
                self.model,
                self.prompt,
                self.transmutation,
                self.action_family,
            )
        return TransmutationTrace(
            trace_id=trace_id,
            fortress_id=str(self.fortress_id or "coding_fortress_v0").strip(),
            phase=phase,
            model=str(self.model or "").strip(),
            prompt=" ".join(str(self.prompt or "").split()),
            constraints_before=_dedupe(self.constraints_before),
            constraints_after=_dedupe(self.constraints_after),
            observations=_dedupe(self.observations),
            preconditions=_dedupe(self.preconditions),
            transmutation=" ".join(str(self.transmutation or "").split()),
            action_family=" ".join(str(self.action_family or "").strip().lower().split()),
            target_artifacts=_dedupe(self.target_artifacts),
            retrieval_queries=_dedupe(self.retrieval_queries),
            retrieval_sources=_dedupe(self.retrieval_sources),
            verifier=_dedupe(self.verifier),
            residual_constraints=_dedupe(self.residual_constraints),
            outcome=str(self.outcome or "unknown").strip().lower() or "unknown",
            mutation_tier=mutation_tier,
            domain=str(self.domain or "coding").strip() or "coding",
            repo_family=str(self.repo_family or "").strip(),
            source_trace_id=str(self.source_trace_id or "").strip(),
            generated_ts=int(self.generated_ts or time.time()),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TransmutationTrace":
        data = dict(payload or {})
        return cls(
            trace_id=str(data.get("trace_id") or ""),
            fortress_id=str(data.get("fortress_id") or ""),
            phase=str(data.get("phase") or ""),
            model=str(data.get("model") or ""),
            prompt=str(data.get("prompt") or ""),
            constraints_before=[str(item) for item in list(data.get("constraints_before") or [])],
            constraints_after=[str(item) for item in list(data.get("constraints_after") or [])],
            observations=[str(item) for item in list(data.get("observations") or [])],
            preconditions=[str(item) for item in list(data.get("preconditions") or [])],
            transmutation=str(data.get("transmutation") or ""),
            action_family=str(data.get("action_family") or ""),
            target_artifacts=[str(item) for item in list(data.get("target_artifacts") or [])],
            retrieval_queries=[str(item) for item in list(data.get("retrieval_queries") or [])],
            retrieval_sources=[str(item) for item in list(data.get("retrieval_sources") or [])],
            verifier=[str(item) for item in list(data.get("verifier") or [])],
            residual_constraints=[str(item) for item in list(data.get("residual_constraints") or [])],
            outcome=str(data.get("outcome") or "unknown"),
            mutation_tier=str(data.get("mutation_tier") or MUTATION_SAME),
            domain=str(data.get("domain") or "coding"),
            repo_family=str(data.get("repo_family") or ""),
            source_trace_id=str(data.get("source_trace_id") or ""),
            generated_ts=int(data.get("generated_ts") or 0),
            metadata=dict(data.get("metadata") or {}),
        ).normalized()


@dataclass(frozen=True)
class PhaseTraceScore:
    teacher_trace_id: str
    student_trace_id: str
    fortress_id: str
    phase: str
    mutation_tier: str
    transmutation_similarity: float
    constraint_overlap: float
    precondition_overlap: float
    action_similarity: float
    retrieval_similarity: float
    verifier_overlap: float
    outcome_match: float
    weighted_score: float
    residual_gap: list[str] = field(default_factory=list)
    negative_transfer: bool = False
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FortressMutationPlan:
    base_case_id: str
    mutated_case_id: str
    mutation_tier: str
    mutation_axes: list[str] = field(default_factory=list)
    invariant_constraints: list[str] = field(default_factory=list)
    expected_transfer: list[str] = field(default_factory=list)
    verifier_requirements: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def coding_fortress_v0_spec() -> dict[str, Any]:
    """Return the first concrete fortress contract for coding transmutations."""

    phases = [
        {
            "phase": CODING_UNDERSTAND,
            "intent": "Turn a prompt and repository into a bounded map of relevant files, symbols, contracts, and uncertainty.",
            "required_trace_fields": [
                "observations",
                "constraints_before",
                "target_artifacts",
                "preconditions",
                "verifier",
            ],
            "verifier": [
                "relevant_file_recall",
                "line_or_symbol_grounding",
                "uncertainty_is_explicit",
            ],
        },
        {
            "phase": CODING_INFER_CHANGE,
            "intent": "Convert understood constraints into the smallest correct change strategy.",
            "required_trace_fields": [
                "constraints_before",
                "constraints_after",
                "transmutation",
                "action_family",
                "rejected_hypotheses",
                "verifier",
            ],
            "verifier": [
                "expected_constraint_delta",
                "teacher_student_transmutation_match",
                "heldout_mutation_success",
            ],
        },
        {
            "phase": CODING_IMPLEMENT,
            "intent": "Apply the selected transmutation as a minimal structured edit or patch.",
            "required_trace_fields": [
                "target_artifacts",
                "action_family",
                "constraints_after",
                "verifier",
            ],
            "verifier": [
                "patch_applies",
                "minimal_file_surface",
                "style_convention_preserved",
            ],
        },
        {
            "phase": CODING_VERIFY_REPAIR,
            "intent": "Translate verifier output into residual constraints and repair moves.",
            "required_trace_fields": [
                "observations",
                "residual_constraints",
                "transmutation",
                "verifier",
            ],
            "verifier": [
                "failure_localized",
                "repair_reduces_residual",
                "regression_guard_passes",
            ],
        },
        {
            "phase": RETRIEVAL_GROUNDING,
            "intent": "Recover missing external knowledge by searching authoritative sources and extracting usable constraints.",
            "required_trace_fields": [
                "retrieval_queries",
                "retrieval_sources",
                "observations",
                "constraints_after",
                "verifier",
            ],
            "verifier": [
                "source_authority",
                "version_or_date_match",
                "contradiction_handled",
                "retrieved_fact_used",
            ],
        },
        {
            "phase": META_TRANSFER,
            "intent": "Promote only transmutations that survive same, mutated, sibling, and cross-domain transfer tests.",
            "required_trace_fields": [
                "preconditions",
                "constraints_before",
                "constraints_after",
                "transmutation",
                "negative_transfer",
            ],
            "verifier": [
                "heldout_improvement",
                "negative_transfer_bounded",
                "rule_compression_gain",
            ],
        },
    ]
    return {
        "fortress_id": "coding_fortress_v0",
        "intent": "Extract, verify, mutate, and transfer coding constraint transmutations across phase-specific fortresses.",
        "phases": phases,
        "mutation_tiers": list(MUTATION_TIERS),
        "gate_policy": {
            "same_case_min_score": 0.78,
            "mutated_case_min_score": 0.72,
            "sibling_case_min_score": 0.66,
            "cross_domain_min_score": 0.58,
            "negative_transfer_max_rate": 0.15,
            "promotion_requires_mutation_tier": MUTATION_MUTATED,
        },
    }


def transmutation_similarity(teacher: TransmutationTrace, student: TransmutationTrace) -> float:
    teacher = teacher.normalized()
    student = student.normalized()
    text = _text_similarity(teacher.transmutation, student.transmutation)
    before = _jaccard(_list_tokens(teacher.constraints_before), _list_tokens(student.constraints_before))
    after = _jaccard(_list_tokens(teacher.constraints_after), _list_tokens(student.constraints_after))
    preconditions = _jaccard(_list_tokens(teacher.preconditions), _list_tokens(student.preconditions))
    action = _text_similarity(teacher.action_family, student.action_family)
    score = _weighted_score(
        {
            "text": (text, 0.26),
            "before": (before, 0.18),
            "after": (after, 0.24),
            "preconditions": (preconditions, 0.14),
            "action": (action, 0.18),
        }
    )
    if action >= 0.92 and after >= 0.72 and preconditions >= 0.58:
        score = max(score, 0.7)
    elif action >= 0.92 and after >= 0.72:
        score = max(score, 0.64)
    return round(score, 4)


def score_transmutation_trace(teacher: TransmutationTrace, student: TransmutationTrace) -> PhaseTraceScore:
    teacher = teacher.normalized()
    student = student.normalized()
    constraint_before = _jaccard(_list_tokens(teacher.constraints_before), _list_tokens(student.constraints_before))
    constraint_after = _jaccard(_list_tokens(teacher.constraints_after), _list_tokens(student.constraints_after))
    constraint_overlap = round((constraint_before + constraint_after) / 2.0, 4)
    precondition_overlap = _jaccard(_list_tokens(teacher.preconditions), _list_tokens(student.preconditions))
    action_similarity = _text_similarity(teacher.action_family, student.action_family)
    retrieval_similarity = round(
        (
            _jaccard(_list_tokens(teacher.retrieval_queries), _list_tokens(student.retrieval_queries))
            + _jaccard(_list_tokens(teacher.retrieval_sources), _list_tokens(student.retrieval_sources))
        )
        / 2.0,
        4,
    )
    verifier_overlap = _jaccard(_list_tokens(teacher.verifier), _list_tokens(student.verifier))
    transmutation_score = transmutation_similarity(teacher, student)
    teacher_success = teacher.outcome in SUCCESS_OUTCOMES
    student_success = student.outcome in SUCCESS_OUTCOMES
    outcome_match = 1.0 if teacher_success == student_success else 0.0
    residual_gap = [
        item
        for item in student.residual_constraints
        if _normalize_token(item) not in {_normalize_token(value) for value in teacher.residual_constraints}
    ]
    negative_transfer = bool(teacher_success and not student_success)
    weighted = _weighted_score(
        {
            "transmutation": (transmutation_score, 0.3),
            "constraints": (constraint_overlap, 0.2),
            "preconditions": (precondition_overlap, 0.12),
            "action": (action_similarity, 0.12),
            "retrieval": (retrieval_similarity, 0.08),
            "verifier": (verifier_overlap, 0.13),
            "outcome": (outcome_match, 0.05),
        }
    )
    reasons: list[str] = []
    if transmutation_score >= 0.74:
        reasons.append("transmutation_semantically_matched")
    if constraint_overlap >= 0.55:
        reasons.append("constraint_motion_matched")
    if verifier_overlap >= 0.6:
        reasons.append("verifier_plan_matched")
    if negative_transfer:
        reasons.append("teacher_success_student_failed")
    if residual_gap:
        reasons.append("student_residual_constraints_remain")
    return PhaseTraceScore(
        teacher_trace_id=teacher.trace_id,
        student_trace_id=student.trace_id,
        fortress_id=teacher.fortress_id or student.fortress_id,
        phase=teacher.phase or student.phase,
        mutation_tier=student.mutation_tier or teacher.mutation_tier,
        transmutation_similarity=transmutation_score,
        constraint_overlap=constraint_overlap,
        precondition_overlap=precondition_overlap,
        action_similarity=action_similarity,
        retrieval_similarity=retrieval_similarity,
        verifier_overlap=verifier_overlap,
        outcome_match=outcome_match,
        weighted_score=weighted,
        residual_gap=residual_gap,
        negative_transfer=negative_transfer,
        reasons=reasons,
    )


def build_mutation_plan(
    *,
    base_case_id: str,
    mutated_case_id: str,
    mutation_tier: str,
    teacher_trace: TransmutationTrace,
    mutation_axes: list[str] | None = None,
    notes: str = "",
) -> FortressMutationPlan:
    trace = teacher_trace.normalized()
    tier = mutation_tier if mutation_tier in MUTATION_TIERS else MUTATION_MUTATED
    return FortressMutationPlan(
        base_case_id=str(base_case_id or trace.trace_id).strip(),
        mutated_case_id=str(mutated_case_id or f"{base_case_id}_{tier}").strip(),
        mutation_tier=tier,
        mutation_axes=_dedupe(mutation_axes or []),
        invariant_constraints=_dedupe(trace.constraints_after or trace.constraints_before),
        expected_transfer=_dedupe([trace.transmutation, trace.action_family]),
        verifier_requirements=_dedupe(trace.verifier),
        notes=str(notes or "").strip(),
    )


def write_trace_jsonl(path: str | Path, traces: list[TransmutationTrace]) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace.to_dict(), ensure_ascii=True) + "\n")
    return target


def load_trace_jsonl(path: str | Path) -> list[TransmutationTrace]:
    target = Path(path).expanduser().resolve()
    traces: list[TransmutationTrace] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean:
            continue
        traces.append(TransmutationTrace.from_dict(json.loads(clean)))
    return traces
