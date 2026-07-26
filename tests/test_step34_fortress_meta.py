from __future__ import annotations

from memory_system.fortresses.coding_fortress import (
    CODING_INFER_CHANGE,
    CODING_UNDERSTAND,
    MUTATION_CROSS_DOMAIN,
    MUTATION_MUTATED,
    MUTATION_SAME,
    MUTATION_SIBLING,
    RETRIEVAL_GROUNDING,
    TransmutationTrace,
    build_mutation_plan,
    coding_fortress_v0_spec,
    score_transmutation_trace,
    transmutation_similarity,
)
from memory_system.fortresses.meta_fortress import (
    GlobalTransmutationLedger,
    build_ledger_entry,
    extract_model_ascent_delta,
)


def _teacher_boundary_trace(trace_id: str = "teacher_auth_boundary") -> TransmutationTrace:
    return TransmutationTrace(
        trace_id=trace_id,
        fortress_id="coding_fortress_v0",
        phase=CODING_INFER_CHANGE,
        model="frontier-teacher",
        prompt="Fix auth requests that slip past the route handler.",
        constraints_before=[
            "auth session integrity is ambiguous downstream",
            "caller contract expects unauthorized requests to fail early",
        ],
        constraints_after=[
            "authentication boundary is enforced before handler execution",
            "caller contract remains stable",
        ],
        observations=[
            "the route handler receives unauthenticated requests",
            "middleware is the shared boundary",
        ],
        preconditions=[
            "request crosses public auth boundary",
            "tests assert caller-visible rejection behavior",
        ],
        transmutation="Trade permissive request flow for stricter authentication boundary enforcement.",
        action_family="early boundary enforcement",
        target_artifacts=["src/middleware.ts", "tests/auth.test.ts"],
        retrieval_queries=["framework middleware auth guard official docs"],
        retrieval_sources=["official framework middleware docs"],
        verifier=["auth rejection test", "full regression test"],
        outcome="success",
        mutation_tier=MUTATION_SAME,
        domain="coding",
        repo_family="ts_backend_security",
    )


def _student_boundary_trace(
    *,
    trace_id: str,
    mutation_tier: str,
    outcome: str = "success",
    residual_constraints: list[str] | None = None,
) -> TransmutationTrace:
    return TransmutationTrace(
        trace_id=trace_id,
        fortress_id="coding_fortress_v0",
        phase=CODING_INFER_CHANGE,
        model="qwen-7b-fortress",
        prompt="Repair the login guard so unauthenticated API requests stop before the endpoint.",
        constraints_before=[
            "authentication check happens too late",
            "caller contract needs early unauthorized rejection",
        ],
        constraints_after=[
            "auth boundary is enforced before handler execution",
            "public caller contract remains stable",
        ],
        observations=["middleware is the common request boundary"],
        preconditions=[
            "request crosses public auth boundary",
            "test checks caller-visible rejection",
        ],
        transmutation="Move auth enforcement to the shared boundary while preserving the caller contract.",
        action_family="early boundary enforcement",
        target_artifacts=["app/http_guard.ts", "test/auth_boundary.test.ts"],
        retrieval_queries=["middleware auth guard documentation"],
        retrieval_sources=["official framework middleware docs"],
        verifier=["auth rejection test", "regression test"],
        outcome=outcome,
        residual_constraints=residual_constraints or [],
        mutation_tier=mutation_tier,
        domain="coding",
        repo_family="ts_backend_security",
    )


def test_coding_fortress_v0_spec_exposes_four_phases_plus_retrieval_and_meta():
    spec = coding_fortress_v0_spec()
    phases = [phase["phase"] for phase in spec["phases"]]

    assert spec["fortress_id"] == "coding_fortress_v0"
    assert phases[:4] == [
        "coding_understand",
        "coding_infer_change",
        "coding_implement",
        "coding_verify_repair",
    ]
    assert "retrieval_grounding" in phases
    assert "meta_transfer" in phases
    assert spec["gate_policy"]["promotion_requires_mutation_tier"] == "mutated"


def test_transmutation_score_matches_mutated_equivalent_boundary_move():
    teacher = _teacher_boundary_trace()
    student = _student_boundary_trace(trace_id="student_mutated", mutation_tier=MUTATION_MUTATED)

    similarity = transmutation_similarity(teacher, student)
    score = score_transmutation_trace(teacher, student)

    assert similarity >= 0.62
    assert score.weighted_score >= 0.72
    assert score.negative_transfer is False
    assert "constraint_motion_matched" in score.reasons
    assert score.mutation_tier == MUTATION_MUTATED


def test_mutation_plan_preserves_invariant_constraints_and_verifiers():
    teacher = _teacher_boundary_trace()

    plan = build_mutation_plan(
        base_case_id="auth_base",
        mutated_case_id="auth_renamed_files",
        mutation_tier=MUTATION_MUTATED,
        teacher_trace=teacher,
        mutation_axes=["renamed files", "prompt paraphrase", "test moved"],
    )

    assert plan.mutation_tier == MUTATION_MUTATED
    assert "authentication boundary is enforced before handler execution" in plan.invariant_constraints
    assert "auth rejection test" in plan.verifier_requirements
    assert "early boundary enforcement" in plan.expected_transfer


def test_meta_ledger_promotes_only_after_mutated_or_sibling_success():
    teacher = _teacher_boundary_trace()
    same_student = _student_boundary_trace(trace_id="student_same", mutation_tier=MUTATION_SAME)
    mutated_student = _student_boundary_trace(trace_id="student_mutated", mutation_tier=MUTATION_MUTATED)
    sibling_student = _student_boundary_trace(trace_id="student_sibling", mutation_tier=MUTATION_SIBLING)

    ledger = GlobalTransmutationLedger()
    for student in (same_student, mutated_student, sibling_student):
        score = score_transmutation_trace(teacher, student)
        ledger.add_entry(build_ledger_entry(teacher_trace=teacher, student_trace=student, score=score))

    decisions = ledger.promotion_decisions(min_support=2, require_tier=MUTATION_MUTATED)
    promoted = [decision for decision in decisions if decision.promote]

    assert len(promoted) == 1
    assert promoted[0].rule is not None
    assert promoted[0].rule.support_count == 3
    assert MUTATION_MUTATED in promoted[0].rule.transfer_tiers
    assert MUTATION_SIBLING in promoted[0].rule.transfer_tiers
    assert promoted[0].negative_transfer_rate == 0.0


def test_meta_ledger_blocks_promotion_when_negative_transfer_is_too_high():
    teacher = _teacher_boundary_trace()
    success = _student_boundary_trace(trace_id="student_mutated", mutation_tier=MUTATION_MUTATED)
    failure = _student_boundary_trace(
        trace_id="student_cross_fail",
        mutation_tier=MUTATION_CROSS_DOMAIN,
        outcome="failed",
        residual_constraints=["checkout confirmation boundary was unrelated to auth"],
    )

    ledger = GlobalTransmutationLedger()
    for student in (success, failure):
        score = score_transmutation_trace(teacher, student)
        ledger.add_entry(build_ledger_entry(teacher_trace=teacher, student_trace=student, score=score))

    decisions = ledger.promotion_decisions(min_support=1, max_negative_transfer_rate=0.2)
    decision = decisions[0]
    clusters = ledger.residual_failure_clusters()

    assert decision.promote is False
    assert "negative_transfer_rate_too_high" in decision.residuals
    assert clusters
    assert clusters[0]["count"] == 1
    assert "checkout confirmation boundary was unrelated to auth" in clusters[0]["cluster"]


def test_meta_ledger_suggests_active_rule_for_matching_prompt():
    teacher = _teacher_boundary_trace()
    mutated_student = _student_boundary_trace(trace_id="student_mutated", mutation_tier=MUTATION_MUTATED)
    sibling_student = _student_boundary_trace(trace_id="student_sibling", mutation_tier=MUTATION_SIBLING)
    ledger = GlobalTransmutationLedger(
        [
            build_ledger_entry(
                teacher_trace=teacher,
                student_trace=mutated_student,
                score=score_transmutation_trace(teacher, mutated_student),
            ),
            build_ledger_entry(
                teacher_trace=teacher,
                student_trace=sibling_student,
                score=score_transmutation_trace(teacher, sibling_student),
            ),
        ]
    )

    suggestions = ledger.suggest_priors(
        prompt="API auth middleware should reject callers before the route handler.",
        phase=CODING_INFER_CHANGE,
        domain="coding",
    )

    assert suggestions
    assert suggestions[0]["action_family"] == "early boundary enforcement"
    assert "auth rejection test" in suggestions[0]["verifier"]


def test_ascent_delta_extracts_stronger_model_retrieval_and_verifier_moves():
    weaker = TransmutationTrace(
        trace_id="weak",
        fortress_id="coding_fortress_v0",
        phase=CODING_UNDERSTAND,
        model="qwen-7b-raw",
        prompt="Update OAuth callback behavior.",
        constraints_before=["callback route looks broken"],
        constraints_after=["edit callback handler"],
        transmutation="Fix the route handler directly.",
        action_family="route handler edit",
        verifier=["run auth test"],
        outcome="failed",
    )
    stronger = TransmutationTrace(
        trace_id="strong",
        fortress_id="coding_fortress_v0",
        phase=CODING_UNDERSTAND,
        model="frontier-teacher",
        prompt="Update OAuth callback behavior.",
        constraints_before=["callback route looks broken", "provider contract controls callback payload"],
        constraints_after=["preserve provider callback contract before editing handler"],
        preconditions=["inspect official provider callback docs"],
        transmutation="Trade direct handler edits for provider-contract-grounded callback repair.",
        action_family="contract-grounded repair",
        retrieval_queries=["official oauth provider callback docs"],
        retrieval_sources=["official provider docs"],
        verifier=["run auth test", "callback payload regression"],
        outcome="success",
    )

    delta = extract_model_ascent_delta(weaker_trace=weaker, stronger_trace=stronger)

    assert delta.novelty_score >= 0.8
    assert "provider contract controls callback payload" in delta.stronger_only_constraints
    assert "inspect official provider callback docs" in delta.stronger_only_preconditions
    assert "callback payload regression" in delta.stronger_only_verifier
    assert "official provider docs" in delta.stronger_only_retrieval
    assert "provider-contract-grounded" in delta.candidate_transmutation


def test_trace_json_round_trip_through_ledger(tmp_path):
    teacher = _teacher_boundary_trace()
    student = _student_boundary_trace(trace_id="student_mutated", mutation_tier=MUTATION_MUTATED)
    entry = build_ledger_entry(
        teacher_trace=teacher,
        student_trace=student,
        score=score_transmutation_trace(teacher, student),
    )
    ledger = GlobalTransmutationLedger([entry])
    path = ledger.write_json(tmp_path / "ledger.json")

    loaded = GlobalTransmutationLedger.read_json(path)

    assert loaded.summarize()["entry_count"] == 1
    assert loaded.entries[0].rule_id == entry.rule_id
    assert loaded.entries[0].mutation_tier == MUTATION_MUTATED


def test_retrieval_grounding_trace_scores_source_and_query_overlap():
    teacher = TransmutationTrace(
        trace_id="teacher_retrieval",
        fortress_id="coding_fortress_v0",
        phase=RETRIEVAL_GROUNDING,
        model="frontier-teacher",
        prompt="Find how the new SDK validates webhook signatures.",
        constraints_after=["webhook signature verification uses official SDK helper"],
        transmutation="Trade memory guess for authoritative version-matched SDK retrieval.",
        action_family="official source grounding",
        retrieval_queries=["official sdk webhook signature verification docs"],
        retrieval_sources=["official sdk docs", "release notes"],
        verifier=["version match", "retrieved helper appears in source"],
        outcome="success",
    )
    student = TransmutationTrace(
        trace_id="student_retrieval",
        fortress_id="coding_fortress_v0",
        phase=RETRIEVAL_GROUNDING,
        model="qwen-7b-fortress",
        prompt="Find webhook signature validation in current SDK docs.",
        constraints_after=["signature verification uses official SDK helper"],
        transmutation="Use official SDK docs instead of guessing from memory.",
        action_family="official source grounding",
        retrieval_queries=["official sdk webhook signature docs"],
        retrieval_sources=["official sdk docs"],
        verifier=["version match", "helper appears in source"],
        outcome="success",
        mutation_tier=MUTATION_MUTATED,
    )

    score = score_transmutation_trace(teacher, student)

    assert score.retrieval_similarity >= 0.6
    assert score.verifier_overlap >= 0.6
    assert score.weighted_score >= 0.7
