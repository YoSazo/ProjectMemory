from __future__ import annotations

from memory_system.fortresses.agency_live_browser import (
    LiveCandidate,
    build_live_transfer_proof,
    candidate_fingerprint,
    canonicalize_bank_candidate_id,
    classify_candidate_safety,
    compile_live_teacher_trace,
    parse_live_decision,
    rank_candidates,
    retrieve_live_teacher_packet,
    verify_live_decision,
)


def _candidate(index: int, label: str, *, tag: str = "a", href: str = "", safety: str = "safe") -> LiveCandidate:
    return LiveCandidate(
        candidate_id=f"c{index:03d}",
        dom_index=index,
        tag=tag,
        label=label,
        href=href,
        input_type="text" if tag == "input" else "",
        safety=safety,
        safety_reason="test",
        fingerprint=candidate_fingerprint(tag=tag, label=label, href=href, input_type="text" if tag == "input" else ""),
    )


def test_live_safety_blocks_irreversible_and_authentication_boundaries():
    assert classify_candidate_safety("Place Order")[0] == "blocked"
    assert classify_candidate_safety("Sign In")[0] == "blocked"
    assert classify_candidate_safety("Proceed to checkout")[0] == "caution"
    assert classify_candidate_safety("Chicago")[0] == "safe"


def test_live_candidate_ranking_prioritizes_goal_overlap_and_inputs():
    candidates = [
        _candidate(0, "Sign In"),
        _candidate(1, "Enter delivery address", tag="input"),
        _candidate(2, "Chicago"),
        _candidate(3, "Shop Flowers"),
    ]
    ranked = rank_candidates(candidates, "Find Domino's in Chicago", limit=3)
    assert ranked[0].label == "Chicago"
    assert any(candidate.tag == "input" for candidate in ranked)


def test_submit_input_is_clickable_not_typeable():
    submit = LiveCandidate(
        candidate_id="c001",
        dom_index=1,
        tag="input",
        label="Google Search",
        href="",
        input_type="submit",
        safety="safe",
        safety_reason="test",
        fingerprint="hash",
    )
    assert submit.kind == "click"


def test_live_decision_parser_is_strict_about_actions_and_candidate_ids():
    decision, mode = parse_live_decision(
        '{"action":"click","candidate_id":"c002","text":"","reason":"city matches goal"}'
    )
    assert mode == "json"
    assert decision and decision["candidate_id"] == "c002"
    assert parse_live_decision('{"action":"click","candidate_id":""}')[0] is None
    assert parse_live_decision('{"action":"purchase","candidate_id":"c002"}')[0] is None


def test_live_decision_verifier_requires_exact_visible_safe_candidate():
    candidates = [_candidate(2, "Chicago"), _candidate(3, "Place Order", safety="blocked")]
    assert verify_live_decision(
        {"action": "click", "candidate_id": "c002", "text": "", "reason": ""}, candidates, "Chicago"
    )[0]
    assert not verify_live_decision(
        {"action": "click", "candidate_id": "c2", "text": "", "reason": ""}, candidates, "Chicago"
    )[0]
    assert not verify_live_decision(
        {"action": "click", "candidate_id": "c003", "text": "", "reason": ""}, candidates, "Chicago"
    )[0]
    assert not verify_live_decision(
        {"action": "click", "candidate_id": "c002", "text": "", "reason": "select the search bar"},
        candidates,
        "Chicago",
    )[0]


def test_live_teacher_trace_compiles_and_rebinds_affordance_not_dom_id():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Find Domino's",
        "rows": [
            {
                "before": {"url": "https://www.google.com/", "candidates": [_candidate(17, "Search", tag="input").public()]},
                "decision": {"action": "type", "candidate_id": "c017", "text": "Domino's", "reason": "search"},
                "execution": {"executed": True},
            }
        ],
    }
    compiled = compile_live_teacher_trace(report)
    rebound = _candidate(4, "Search", tag="input")
    packet = retrieve_live_teacher_packet(
        compiled_trace=compiled,
        observation={"url": "https://www.google.com/", "candidates": [rebound]},
        history=[],
    )
    assert packet[0]["binding_mode"] == "exact_affordance"
    assert packet[0]["required_next_action"]["candidate_id"] == "c004"
    wrong = {"action": "click", "candidate_id": "c004", "text": "", "reason": ""}
    assert not verify_live_decision(wrong, [rebound], "Find Domino's", bank_packet=packet)[0]


def test_bank_candidate_id_canonicalizer_only_restores_equivalent_zero_padding():
    packet = [{"required_next_action": {"candidate_id": "c039"}}]
    normalized, changed = canonicalize_bank_candidate_id(
        {"action": "click", "candidate_id": "c39", "text": "", "reason": ""}, packet
    )
    assert changed is True
    assert normalized and normalized["candidate_id"] == "c039"
    untouched, changed = canonicalize_bank_candidate_id(
        {"action": "click", "candidate_id": "c38", "text": "", "reason": ""}, packet
    )
    assert changed is False
    assert untouched and untouched["candidate_id"] == "c38"


def test_live_transfer_proof_keeps_seed_replication_caveat():
    base = {
        "fortress_id": "live",
        "student_model": "mistral",
        "goal": "find domino's",
        "start_url": "https://google.com",
        "stop_reason": "ask",
        "steps_executed": 0,
        "rows": [],
    }
    teacher = {**base, "student_model": "teacher", "stop_reason": "in_progress", "rows": []}
    raw = {**base, "teacher_calls": 0}
    bank = {
        **base,
        "teacher_calls": 0,
        "teacher_trace_hash": "trace",
        "steps_executed": 1,
        "rows": [
            {
                "step_index": 0,
                "decision": {"action": "click", "candidate_id": "c001"},
                "before": {"candidates": [{"candidate_id": "c001", "safety": "safe"}]},
                "execution": {"executed": True, "status": "executed"},
                "after": {"url": "https://doordash.com/dominos/chicago"},
                "bank_packet": [{}],
            }
        ],
    }
    proof = build_live_transfer_proof(
        teacher_report=teacher,
        raw_reports=[raw],
        bank_reports=[bank],
        required_final_url_terms=["doordash", "domino", "chicago"],
    )
    assert proof["raw_successes"] == 0
    assert proof["bank_successes"] == 1
    assert proof["authenticity"]["teacher_calls_in_student_runs"] == 0
    assert proof["authenticity"]["seed_replications_are_independent_cases"] is False
    assert proof["teacher"]["source_report_complete"] is False
