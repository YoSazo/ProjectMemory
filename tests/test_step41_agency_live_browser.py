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
    assert classify_candidate_safety("Add item to cart")[0] == "caution"
    assert classify_candidate_safety("Add Cheese Pizza to the cart")[0] == "caution"
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
    scroll, mode = parse_live_decision(
        '{"action":"scroll","candidate_id":"","text":"down","reason":"options below"}'
    )
    assert mode == "json"
    assert scroll and verify_live_decision(scroll, [], "find large size")[0]
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


def test_live_teacher_trace_preserves_terminal_stop_rule():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "select large and stop",
        "rows": [
            {
                "before": {"url": "https://www.doordash.com/store/example", "candidates": []},
                "decision": {"action": "stop", "candidate_id": "", "text": "", "reason": "goal complete"},
                "execution": {"executed": False, "status": "stop"},
            }
        ],
    }
    compiled = compile_live_teacher_trace(report)
    packet = retrieve_live_teacher_packet(
        compiled_trace=compiled,
        observation={"url": "https://www.doordash.com/store/example", "candidates": []},
        history=[],
        goal=report["goal"],
    )
    assert compiled["rules"][0]["action"] == "stop"
    assert packet[0]["binding_mode"] == "terminal_boundary"
    assert packet[0]["required_next_action"]["action"] == "stop"


def test_live_teacher_trace_adapts_search_text_and_result_to_new_goal():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Find Domino's DoorDash page for Chicago",
        "rows": [
            {
                "before": {"url": "https://www.google.com/", "candidates": [_candidate(17, "Search", tag="input").public()]},
                "decision": {"action": "type", "candidate_id": "c017", "text": "Domino's DoorDash Chicago", "reason": "search"},
                "execution": {"executed": True},
            }
        ],
    }
    compiled = compile_live_teacher_trace(report)
    packet = retrieve_live_teacher_packet(
        compiled_trace=compiled,
        observation={"url": "https://www.google.com/", "candidates": [_candidate(4, "Search", tag="input")]},
        history=[],
        goal="Find Pizza Hut DoorDash page for Dallas",
    )
    assert packet[0]["goal_adapted"] is True
    assert packet[0]["required_next_action"]["text"] == ""
    assert "current goal" in packet[0]["text_policy"]
    assert packet[0]["teacher_reason"] == ""


def test_goal_adapted_result_preserves_teacher_destination_domain():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Find Domino's DoorDash page for Chicago",
        "rows": [
            {
                "before": {
                    "url": "https://www.google.com/search?q=dominos",
                    "candidates": [
                        _candidate(
                            8,
                            "Domino's Locations in Chicago DoorDash https://www.doordash.com/city/chicago",
                            href="https://www.doordash.com/city/chicago",
                        ).public()
                    ],
                },
                "decision": {"action": "click", "candidate_id": "c008", "text": "", "reason": "result"},
                "execution": {"executed": True},
            }
        ],
    }
    compiled = compile_live_teacher_trace(report)
    maps = _candidate(1, "Maps Pizza Hut DoorDash Dallas Texas", href="https://www.google.com/maps?q=pizza+hut")
    doordash = _candidate(
        2,
        "Pizza Hut locations Dallas DoorDash https://www.doordash.com/city/dallas",
        href="https://www.doordash.com/city/dallas",
    )
    packet = retrieve_live_teacher_packet(
        compiled_trace=compiled,
        observation={"url": "https://www.google.com/search?q=pizza", "candidates": [maps, doordash]},
        history=[],
        goal="Find Pizza Hut DoorDash page for Dallas Texas",
    )
    assert compiled["rules"][0]["target_domain"] == "doordash.com"
    assert packet[0]["required_next_action"]["candidate_id"] == "c002"
    assert packet[0]["destination_domain_mode"] == "preserved_teacher_domain"


def test_goal_adapted_result_can_rebind_teacher_domain_as_platform_slot():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Find Domino's DoorDash page for Chicago",
        "rows": [
            {
                "before": {
                    "url": "https://www.google.com/search?q=dominos",
                    "candidates": [
                        _candidate(
                            8,
                            "Domino's Chicago DoorDash https://www.doordash.com/city/chicago",
                            href="https://www.doordash.com/city/chicago",
                        ).public()
                    ],
                },
                "decision": {"action": "click", "candidate_id": "c008", "text": "", "reason": "result"},
                "execution": {"executed": True},
            }
        ],
    }
    compiled = compile_live_teacher_trace(report)
    maps = _candidate(1, "Maps Taco Bell Uber Eats Houston Texas", href="https://www.google.com/maps?q=taco+bell")
    uber = _candidate(
        2,
        "Taco Bell Houston Uber Eats https://www.ubereats.com/store/taco-bell",
        href="https://www.ubereats.com/store/taco-bell",
    )
    packet = retrieve_live_teacher_packet(
        compiled_trace=compiled,
        observation={"url": "https://www.google.com/search?q=taco", "candidates": [maps, uber]},
        history=[],
        goal="Find Taco Bell Uber Eats page for Houston Texas",
    )
    assert packet[0]["required_next_action"]["candidate_id"] == "c002"
    assert packet[0]["destination_domain_mode"] == "goal_adapted_external_destination"


def test_goal_adapted_affordance_does_not_replay_changed_item_slot():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Select a cheese pizza",
        "rows": [
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(5, "Cheese Pizza $12").public()],
                },
                "decision": {"action": "click", "candidate_id": "c005", "text": "", "reason": "item"},
                "execution": {"executed": True},
            }
        ],
    }
    compiled = compile_live_teacher_trace(report)
    packet = retrieve_live_teacher_packet(
        compiled_trace=compiled,
        observation={
            "url": "https://www.doordash.com/store/example",
            "candidates": [_candidate(5, "Cheese Pizza $12"), _candidate(6, "Pepperoni Pizza $14")],
        },
        history=[],
        goal="Select a pepperoni pizza",
    )
    assert packet[0]["binding_mode"] == "goal_adapted_affordance"
    assert packet[0]["required_next_action"]["candidate_id"] == "c006"


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
    assert proof["authenticity"]["trials_are_independent_task_cases"] is False
    assert proof["teacher"]["source_report_complete"] is False


def test_live_transfer_proof_requires_destination_host_for_mutated_tasks():
    def report(goal: str, url: str, trace: str) -> dict:
        return {
            "fortress_id": "live",
            "student_model": "mistral",
            "goal": goal,
            "start_url": "https://google.com",
            "stop_reason": "max_steps",
            "teacher_calls": 0,
            "teacher_trace_hash": trace,
            "steps_executed": 1,
            "rows": [
                {
                    "step_index": 0,
                    "decision": {"action": "click", "candidate_id": "c001"},
                    "before": {"candidates": [{"candidate_id": "c001", "safety": "safe"}]},
                    "execution": {"executed": True, "status": "executed"},
                    "after": {"url": url},
                    "bank_packet": [{}] if trace else [],
                }
            ],
        }

    teacher = {**report("teacher source", "https://doordash.com/source", ""), "student_model": "teacher"}
    goal = "Find Pizza Hut in Dallas"
    raw = report(goal, "https://google.com/search?q=doordash+pizza+hut+dallas", "")
    bank = report(goal, "https://doordash.com/city/dallas/pizza-hut", "trace")
    proof = build_live_transfer_proof(
        teacher_report=teacher,
        raw_reports=[raw],
        bank_reports=[bank],
        required_final_url_terms=[],
        required_final_url_terms_by_pair=[["pizza-hut", "dallas"]],
        required_final_host="doordash.com",
    )
    assert proof["raw_successes"] == 0
    assert proof["bank_successes"] == 1
    assert proof["authenticity"]["trials_are_independent_task_cases"] is True
    assert proof["authenticity"]["includes_cross_platform_mutation"] is False
