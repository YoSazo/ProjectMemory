from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from .coding_fortress import (
    MUTATION_CROSS_DOMAIN,
    MUTATION_MUTATED,
    MUTATION_SAME,
    MUTATION_SIBLING,
    MUTATION_TIERS,
    PhaseTraceScore,
    TransmutationTrace,
    _dedupe,
    _jaccard,
    _list_tokens,
    _normalize_token,
    _tokenize,
)


_TIER_WEIGHTS = {
    MUTATION_SAME: 0.55,
    MUTATION_MUTATED: 1.0,
    MUTATION_SIBLING: 1.25,
    MUTATION_CROSS_DOMAIN: 1.55,
}


def _slug(value: str, *, limit: int = 40) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    if not text:
        text = "transmutation"
    return text[:limit].strip("_") or "transmutation"


def _rule_hash(*parts: str) -> str:
    blob = "\n".join(str(part or "") for part in parts)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:10]


def _rule_id(transmutation: str, action_family: str, constraints_after: list[str]) -> str:
    label = _slug(action_family or transmutation)
    digest = _rule_hash(transmutation, action_family, "|".join(sorted(constraints_after)))
    return f"tm_{label}_{digest}"


def _tier_at_least(tier: str, minimum: str) -> bool:
    order = list(MUTATION_TIERS)
    current = tier if tier in order else MUTATION_SAME
    required = minimum if minimum in order else MUTATION_MUTATED
    return order.index(current) >= order.index(required)


def _token_match_score(prompt: str, values: list[str]) -> float:
    prompt_tokens = _tokenize(prompt)
    value_tokens = _list_tokens(values)
    return _jaccard(prompt_tokens, value_tokens)


@dataclass(frozen=True)
class TransferLedgerEntry:
    entry_id: str
    rule_id: str
    transmutation: str
    action_family: str
    source_fortress: str
    source_phase: str
    target_fortress: str
    target_phase: str
    mutation_tier: str
    domain: str
    repo_family: str = ""
    constraints_before: list[str] = field(default_factory=list)
    constraints_after: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    verifier: list[str] = field(default_factory=list)
    retrieval_sources: list[str] = field(default_factory=list)
    score: float = 0.0
    outcome: str = "unknown"
    negative_transfer: bool = False
    teacher_trace_id: str = ""
    student_trace_id: str = ""
    source_model: str = ""
    student_model: str = ""
    generated_ts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "TransferLedgerEntry":
        mutation_tier = self.mutation_tier if self.mutation_tier in MUTATION_TIERS else MUTATION_SAME
        rule_id = str(self.rule_id or "").strip() or _rule_id(
            self.transmutation,
            self.action_family,
            self.constraints_after,
        )
        entry_id = str(self.entry_id or "").strip() or _rule_hash(
            rule_id,
            self.teacher_trace_id,
            self.student_trace_id,
            self.target_fortress,
            self.target_phase,
            mutation_tier,
        )
        return TransferLedgerEntry(
            entry_id=entry_id,
            rule_id=rule_id,
            transmutation=" ".join(str(self.transmutation or "").split()),
            action_family=" ".join(str(self.action_family or "").strip().lower().split()),
            source_fortress=str(self.source_fortress or "").strip(),
            source_phase=str(self.source_phase or "").strip(),
            target_fortress=str(self.target_fortress or "").strip(),
            target_phase=str(self.target_phase or "").strip(),
            mutation_tier=mutation_tier,
            domain=str(self.domain or "").strip() or "unknown",
            repo_family=str(self.repo_family or "").strip(),
            constraints_before=_dedupe(self.constraints_before),
            constraints_after=_dedupe(self.constraints_after),
            preconditions=_dedupe(self.preconditions),
            verifier=_dedupe(self.verifier),
            retrieval_sources=_dedupe(self.retrieval_sources),
            score=round(float(self.score or 0.0), 4),
            outcome=str(self.outcome or "unknown").strip().lower() or "unknown",
            negative_transfer=bool(self.negative_transfer),
            teacher_trace_id=str(self.teacher_trace_id or "").strip(),
            student_trace_id=str(self.student_trace_id or "").strip(),
            source_model=str(self.source_model or "").strip(),
            student_model=str(self.student_model or "").strip(),
            generated_ts=int(self.generated_ts or time.time()),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TransferLedgerEntry":
        data = dict(payload or {})
        return cls(
            entry_id=str(data.get("entry_id") or ""),
            rule_id=str(data.get("rule_id") or ""),
            transmutation=str(data.get("transmutation") or ""),
            action_family=str(data.get("action_family") or ""),
            source_fortress=str(data.get("source_fortress") or ""),
            source_phase=str(data.get("source_phase") or ""),
            target_fortress=str(data.get("target_fortress") or ""),
            target_phase=str(data.get("target_phase") or ""),
            mutation_tier=str(data.get("mutation_tier") or MUTATION_SAME),
            domain=str(data.get("domain") or ""),
            repo_family=str(data.get("repo_family") or ""),
            constraints_before=[str(item) for item in list(data.get("constraints_before") or [])],
            constraints_after=[str(item) for item in list(data.get("constraints_after") or [])],
            preconditions=[str(item) for item in list(data.get("preconditions") or [])],
            verifier=[str(item) for item in list(data.get("verifier") or [])],
            retrieval_sources=[str(item) for item in list(data.get("retrieval_sources") or [])],
            score=float(data.get("score") or 0.0),
            outcome=str(data.get("outcome") or "unknown"),
            negative_transfer=bool(data.get("negative_transfer")),
            teacher_trace_id=str(data.get("teacher_trace_id") or ""),
            student_trace_id=str(data.get("student_trace_id") or ""),
            source_model=str(data.get("source_model") or ""),
            student_model=str(data.get("student_model") or ""),
            generated_ts=int(data.get("generated_ts") or 0),
            metadata=dict(data.get("metadata") or {}),
        ).normalized()


@dataclass(frozen=True)
class ActiveTransmutationRule:
    rule_id: str
    transmutation: str
    action_family: str
    phases: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    repo_families: list[str] = field(default_factory=list)
    constraints_before: list[str] = field(default_factory=list)
    constraints_after: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    negative_preconditions: list[str] = field(default_factory=list)
    verifier: list[str] = field(default_factory=list)
    retrieval_sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    support_count: int = 0
    failure_count: int = 0
    transfer_tiers: list[str] = field(default_factory=list)
    source_models: list[str] = field(default_factory=list)
    evidence_entry_ids: list[str] = field(default_factory=list)
    generated_ts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromotionDecision:
    rule_id: str
    promote: bool
    confidence: float
    support_count: int
    failure_count: int
    transfer_score: float
    negative_transfer_rate: float
    best_mutation_tier: str
    reasons: list[str] = field(default_factory=list)
    residuals: list[str] = field(default_factory=list)
    rule: ActiveTransmutationRule | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["rule"] = self.rule.to_dict() if self.rule is not None else None
        return payload


@dataclass(frozen=True)
class ModelAscentDelta:
    weaker_model: str
    stronger_model: str
    fortress_id: str
    phase: str
    prompt: str
    stronger_only_constraints: list[str] = field(default_factory=list)
    stronger_only_preconditions: list[str] = field(default_factory=list)
    stronger_only_verifier: list[str] = field(default_factory=list)
    stronger_only_retrieval: list[str] = field(default_factory=list)
    stronger_action_family: str = ""
    weaker_action_family: str = ""
    candidate_transmutation: str = ""
    evidence_trace_ids: list[str] = field(default_factory=list)
    novelty_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_ledger_entry(
    *,
    teacher_trace: TransmutationTrace,
    student_trace: TransmutationTrace,
    score: PhaseTraceScore,
    target_fortress: str = "",
    target_phase: str = "",
) -> TransferLedgerEntry:
    teacher = teacher_trace.normalized()
    student = student_trace.normalized()
    rule_id = _rule_id(teacher.transmutation, teacher.action_family, teacher.constraints_after)
    entry = TransferLedgerEntry(
        entry_id="",
        rule_id=rule_id,
        transmutation=teacher.transmutation,
        action_family=teacher.action_family,
        source_fortress=teacher.fortress_id,
        source_phase=teacher.phase,
        target_fortress=target_fortress or student.fortress_id,
        target_phase=target_phase or student.phase,
        mutation_tier=student.mutation_tier,
        domain=student.domain or teacher.domain,
        repo_family=student.repo_family or teacher.repo_family,
        constraints_before=teacher.constraints_before,
        constraints_after=teacher.constraints_after,
        preconditions=teacher.preconditions,
        verifier=teacher.verifier,
        retrieval_sources=teacher.retrieval_sources,
        score=score.weighted_score,
        outcome=student.outcome,
        negative_transfer=score.negative_transfer,
        teacher_trace_id=teacher.trace_id,
        student_trace_id=student.trace_id,
        source_model=teacher.model,
        student_model=student.model,
        metadata={"score_reasons": list(score.reasons), "residual_gap": list(score.residual_gap)},
    )
    return entry.normalized()


def _merge_entry_rule(rule_id: str, entries: list[TransferLedgerEntry]) -> ActiveTransmutationRule:
    positives = [entry for entry in entries if not entry.negative_transfer]
    failures = [entry for entry in entries if entry.negative_transfer]
    source = (positives or entries)[0]
    support_weight = sum(_TIER_WEIGHTS.get(entry.mutation_tier, 0.55) * max(float(entry.score), 0.0) for entry in positives)
    failure_weight = sum(_TIER_WEIGHTS.get(entry.mutation_tier, 0.55) * max(float(entry.score), 0.25) for entry in failures)
    denominator = support_weight + failure_weight
    confidence = round(support_weight / denominator, 4) if denominator else 0.0

    def _collect(field_name: str) -> list[str]:
        values: list[str] = []
        for entry in positives or entries:
            raw = getattr(entry, field_name)
            if isinstance(raw, list):
                values.extend(str(item) for item in raw)
            elif raw:
                values.append(str(raw))
        return _dedupe(values)

    negative_preconditions: list[str] = []
    positive_precondition_tokens = _list_tokens(_collect("preconditions"))
    for entry in failures:
        for precondition in entry.preconditions:
            if _normalize_token(precondition) not in positive_precondition_tokens:
                negative_preconditions.append(precondition)
        for residual in list(entry.metadata.get("residual_gap") or []):
            negative_preconditions.append(f"avoid_when_residual:{residual}")

    return ActiveTransmutationRule(
        rule_id=rule_id,
        transmutation=source.transmutation,
        action_family=source.action_family,
        phases=_dedupe([entry.target_phase or entry.source_phase for entry in positives or entries]),
        domains=_dedupe([entry.domain for entry in positives or entries]),
        repo_families=_dedupe([entry.repo_family for entry in positives or entries]),
        constraints_before=_collect("constraints_before"),
        constraints_after=_collect("constraints_after"),
        preconditions=_collect("preconditions"),
        negative_preconditions=_dedupe(negative_preconditions),
        verifier=_collect("verifier"),
        retrieval_sources=_collect("retrieval_sources"),
        confidence=confidence,
        support_count=len(positives),
        failure_count=len(failures),
        transfer_tiers=_dedupe([entry.mutation_tier for entry in positives]),
        source_models=_dedupe([entry.source_model for entry in positives or entries]),
        evidence_entry_ids=[entry.entry_id for entry in positives or entries],
        generated_ts=int(time.time()),
    )


class GlobalTransmutationLedger:
    """Meta-fortress ledger for transfer, promotion, and negative-transfer control."""

    def __init__(self, entries: list[TransferLedgerEntry] | None = None) -> None:
        self.entries = [entry.normalized() for entry in (entries or [])]

    def add_entry(self, entry: TransferLedgerEntry) -> None:
        normalized = entry.normalized()
        if all(existing.entry_id != normalized.entry_id for existing in self.entries):
            self.entries.append(normalized)

    def grouped(self) -> dict[str, list[TransferLedgerEntry]]:
        groups: dict[str, list[TransferLedgerEntry]] = defaultdict(list)
        for entry in self.entries:
            groups[entry.rule_id].append(entry)
        return dict(groups)

    def summarize(self) -> dict[str, Any]:
        tier_counts: dict[str, int] = defaultdict(int)
        domain_counts: dict[str, int] = defaultdict(int)
        negative_count = 0
        for entry in self.entries:
            tier_counts[entry.mutation_tier] += 1
            domain_counts[entry.domain] += 1
            if entry.negative_transfer:
                negative_count += 1
        return {
            "entry_count": len(self.entries),
            "rule_count": len(self.grouped()),
            "negative_transfer_count": negative_count,
            "mutation_tier_counts": dict(sorted(tier_counts.items())),
            "domain_counts": dict(sorted(domain_counts.items())),
        }

    def promotion_decisions(
        self,
        *,
        min_support: int = 2,
        min_confidence: float = 0.72,
        min_score: float = 0.66,
        max_negative_transfer_rate: float = 0.18,
        require_tier: str = MUTATION_MUTATED,
    ) -> list[PromotionDecision]:
        decisions: list[PromotionDecision] = []
        for rule_id, raw_entries in sorted(self.grouped().items()):
            entries = [entry.normalized() for entry in raw_entries]
            positives = [entry for entry in entries if not entry.negative_transfer and entry.score >= min_score]
            failures = [entry for entry in entries if entry.negative_transfer]
            rule = _merge_entry_rule(rule_id, entries)
            support_count = len(positives)
            failure_count = len(failures)
            total_count = max(support_count + failure_count, 1)
            negative_rate = round(failure_count / total_count, 4)
            best_tier = MUTATION_SAME
            for tier in MUTATION_TIERS:
                if any(entry.mutation_tier == tier and not entry.negative_transfer for entry in positives):
                    best_tier = tier
            transfer_score = round(
                sum(_TIER_WEIGHTS.get(entry.mutation_tier, 0.55) * float(entry.score) for entry in positives),
                4,
            )
            reasons: list[str] = []
            residuals: list[str] = []
            if support_count >= min_support:
                reasons.append("support_count_met")
            else:
                residuals.append("insufficient_positive_support")
            if rule.confidence >= min_confidence:
                reasons.append("confidence_met")
            else:
                residuals.append("confidence_below_threshold")
            if negative_rate <= max_negative_transfer_rate:
                reasons.append("negative_transfer_bounded")
            else:
                residuals.append("negative_transfer_rate_too_high")
            if _tier_at_least(best_tier, require_tier):
                reasons.append("mutation_tier_met")
            else:
                residuals.append("no_sufficient_mutation_transfer")
            promote = not residuals
            decisions.append(
                PromotionDecision(
                    rule_id=rule_id,
                    promote=promote,
                    confidence=rule.confidence,
                    support_count=support_count,
                    failure_count=failure_count,
                    transfer_score=transfer_score,
                    negative_transfer_rate=negative_rate,
                    best_mutation_tier=best_tier,
                    reasons=reasons,
                    residuals=residuals,
                    rule=rule if promote else None,
                )
            )
        return decisions

    def active_rules(self, **kwargs: Any) -> list[ActiveTransmutationRule]:
        return [decision.rule for decision in self.promotion_decisions(**kwargs) if decision.promote and decision.rule is not None]

    def suggest_priors(
        self,
        *,
        prompt: str,
        phase: str = "",
        domain: str = "",
        limit: int = 5,
        rules: list[ActiveTransmutationRule] | None = None,
    ) -> list[dict[str, Any]]:
        active = rules if rules is not None else self.active_rules()
        suggestions: list[dict[str, Any]] = []
        for rule in active:
            if phase and rule.phases and phase not in rule.phases:
                continue
            if domain and rule.domains and domain not in rule.domains:
                continue
            match = _token_match_score(
                prompt,
                list(rule.constraints_before)
                + list(rule.constraints_after)
                + list(rule.preconditions)
                + [rule.transmutation, rule.action_family],
            )
            score = round((0.65 * match) + (0.35 * rule.confidence), 4)
            if score <= 0:
                continue
            suggestions.append(
                {
                    "rule_id": rule.rule_id,
                    "transmutation": rule.transmutation,
                    "action_family": rule.action_family,
                    "confidence": rule.confidence,
                    "match_score": match,
                    "score": score,
                    "preconditions": list(rule.preconditions),
                    "verifier": list(rule.verifier),
                }
            )
        suggestions.sort(key=lambda item: (float(item["score"]), float(item["confidence"])), reverse=True)
        return suggestions[: max(int(limit), 0)]

    def residual_failure_clusters(self) -> list[dict[str, Any]]:
        clusters: dict[str, list[TransferLedgerEntry]] = defaultdict(list)
        for entry in self.entries:
            if not entry.negative_transfer:
                continue
            residuals = [str(item) for item in list(entry.metadata.get("residual_gap") or []) if str(item).strip()]
            key = residuals[0] if residuals else entry.action_family or entry.transmutation
            clusters[key].append(entry)
        rows: list[dict[str, Any]] = []
        for key, entries in clusters.items():
            rows.append(
                {
                    "cluster": key,
                    "count": len(entries),
                    "rule_ids": _dedupe([entry.rule_id for entry in entries]),
                    "mutation_tiers": _dedupe([entry.mutation_tier for entry in entries]),
                    "domains": _dedupe([entry.domain for entry in entries]),
                    "candidate_question": f"What missing precondition would prevent negative transfer for {key}?",
                }
            )
        rows.sort(key=lambda item: int(item["count"]), reverse=True)
        return rows

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_ts": int(time.time()),
            "summary": self.summarize(),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GlobalTransmutationLedger":
        return cls(entries=[TransferLedgerEntry.from_dict(item) for item in list((payload or {}).get("entries") or [])])

    def write_json(self, path: str | Path) -> Path:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    @classmethod
    def read_json(cls, path: str | Path) -> "GlobalTransmutationLedger":
        payload = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
        return cls.from_dict(payload)


def _left_only(left: list[str], right: list[str]) -> list[str]:
    right_keys = {_normalize_token(item) for item in right}
    out: list[str] = []
    seen: set[str] = set()
    for item in left:
        key = _normalize_token(item)
        if not key or key in right_keys or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def extract_model_ascent_delta(
    *,
    weaker_trace: TransmutationTrace,
    stronger_trace: TransmutationTrace,
) -> ModelAscentDelta:
    weak = weaker_trace.normalized()
    strong = stronger_trace.normalized()
    stronger_only_constraints = _dedupe(
        _left_only(strong.constraints_before + strong.constraints_after, weak.constraints_before + weak.constraints_after)
    )
    stronger_only_preconditions = _dedupe(_left_only(strong.preconditions, weak.preconditions))
    stronger_only_verifier = _dedupe(_left_only(strong.verifier, weak.verifier))
    stronger_only_retrieval = _dedupe(
        _left_only(strong.retrieval_queries + strong.retrieval_sources, weak.retrieval_queries + weak.retrieval_sources)
    )
    novelty_parts = [
        0.28 if stronger_only_constraints else 0.0,
        0.24 if stronger_only_preconditions else 0.0,
        0.22 if stronger_only_verifier else 0.0,
        0.16 if stronger_only_retrieval else 0.0,
        0.10 if strong.action_family and strong.action_family != weak.action_family else 0.0,
    ]
    candidate_bits = [strong.transmutation]
    if stronger_only_preconditions:
        candidate_bits.append("Requires " + ", ".join(stronger_only_preconditions[:3]))
    if stronger_only_verifier:
        candidate_bits.append("Verify with " + ", ".join(stronger_only_verifier[:3]))
    candidate = " | ".join(bit for bit in candidate_bits if bit).strip()
    return ModelAscentDelta(
        weaker_model=weak.model,
        stronger_model=strong.model,
        fortress_id=strong.fortress_id or weak.fortress_id,
        phase=strong.phase or weak.phase,
        prompt=strong.prompt or weak.prompt,
        stronger_only_constraints=stronger_only_constraints,
        stronger_only_preconditions=stronger_only_preconditions,
        stronger_only_verifier=stronger_only_verifier,
        stronger_only_retrieval=stronger_only_retrieval,
        stronger_action_family=strong.action_family,
        weaker_action_family=weak.action_family,
        candidate_transmutation=candidate,
        evidence_trace_ids=_dedupe([weak.trace_id, strong.trace_id]),
        novelty_score=round(sum(novelty_parts), 4),
    )
