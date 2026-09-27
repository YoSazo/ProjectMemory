from __future__ import annotations

import json
from types import SimpleNamespace

import memory_system.fortresses.agency_live_browser as live_browser
from memory_system.fortresses.agency_live_browser import (
    LiveCandidate,
    build_live_transfer_proof,
    candidate_fingerprint,
    canonicalize_bank_candidate_id,
    classify_candidate_safety,
    compile_live_teacher_bank,
    compile_live_teacher_trace,
    parse_live_decision,
    rank_candidates,
    retrieve_live_teacher_packet,
    live_goal_state,
    required_choice_packet,
    _answer_choices,
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


def test_required_choice_question_and_two_group_resolution():
    candidates = [
        _candidate(10, "Make 2 required selections", tag="button"),
        _candidate(11, "Tangy BBQ Dipping Sauce 45 cal", tag="button"),
        _candidate(12, "Sweet and Sour Dipping Sauce 50 cal", tag="button"),
        _candidate(21, "Tangy BBQ Dipping Sauce 45 cal", tag="button"),
        _candidate(22, "Sweet and Sour Dipping Sauce 50 cal", tag="button"),
    ]
    observation = {"candidates": candidates, "dialog_title": "10 pc. Chicken McNuggets", "state_hash": "abc"}
    state = live_goal_state("Get Nuggets quantity 2", observation, [])
    assert state["required_choices_remaining"] == 2
    assert state["visible_quantity"] is None
    assert live_goal_state("quantity 2", {"candidates": [], "visible_text": "Make 2 required selections"}, [])[
        "required_choices_remaining"
    ] == 2
    question = required_choice_packet(state, candidates, [])
    assert question[0]["required_next_action"]["action"] == "ask"
    assert "Tangy BBQ" in question[0]["required_next_action"]["text"]
    choices = _answer_choices("Tangy BBQ and Sweet and Sour", state["choice_options"], 2)
    assert len(choices) == 2
    first = required_choice_packet(state, candidates, choices)
    assert first[0]["required_next_action"]["candidate_id"] == "c011"
    state["confirmed_choices"] = 1
    state["required_choices_remaining"] = 1
    second = required_choice_packet(state, candidates, choices)
    assert second[0]["required_next_action"]["candidate_id"] == "c022"
    assert not _answer_choices("whatever", state["choice_options"], 2)
    assert _answer_choices("BBQ twice", ["BBQ"], 2) == ["BBQ", "BBQ"]


def test_unresolved_required_choices_and_quantity_cannot_stop():
    stop = {"action": "stop", "candidate_id": "", "text": "", "reason": "done"}
    state = {"required_choices_remaining": 1, "requested_quantity": 2, "visible_quantity": None}
    assert not verify_live_decision(stop, [], "quantity 2", goal_state=state)[0]
    state["required_choices_remaining"] = 0
    assert not verify_live_decision(stop, [], "quantity 2", goal_state=state)[0]
    state["verified_quantity"] = 2
    assert verify_live_decision(stop, [], "quantity 2", goal_state=state)[0]


def test_required_choice_run_pauses_resumes_and_verifies(monkeypatch, tmp_path):
    class Bridge:
        remaining = 2
        quantity = 1

        def __init__(self, _url):
            pass

        def observe(self, _goal):
            candidates = [_candidate(11, "Tangy BBQ Dipping Sauce 45 cal", tag="button"),
                          _candidate(12, "Sweet N Sour Dipping Sauce 50 cal", tag="button"),
                          _candidate(21, "Tangy BBQ Dipping Sauce 45 cal", tag="button"),
                          _candidate(22, "Sweet N Sour Dipping Sauce 50 cal", tag="button")]
            if self.remaining:
                candidates.insert(0, _candidate(10, f"Make {self.remaining} required selection" +
                                              ("s" if self.remaining > 1 else ""), tag="button"))
            else:
                candidates.extend([_candidate(30, "Increase quantity by 1", tag="button"),
                                   _candidate(31, f"Current quantity is {self.quantity}", tag="input")])
            return {"url": "https://www.doordash.com/store/test", "title": "DoorDash",
                    "dialog_title": "10 pc. Chicken McNuggets", "visible_text": "Nuggets",
                    "candidates": candidates, "all_candidate_count": len(candidates),
                    "scrollable_regions": [], "state_hash": f"{self.remaining}:{self.quantity}"}

        def execute(self, decision, _observation, **_kwargs):
            if decision["action"] == "ask" or decision["action"] == "stop":
                return {"status": decision["action"], "executed": False, "reason": ""}
            if self.remaining:
                self.remaining -= 1
            else:
                self.quantity += 1
            return {"status": "executed", "executed": True, "reason": ""}

        def screenshot(self, _path):
            pass

        def close(self):
            pass

    class Client:
        def chat_response(self, **kwargs):
            state = json.loads(kwargs["messages"][-1].content)
            packet = state["bank_packet"]
            action = packet[0]["required_next_action"] if packet else (
                {"action": "click", "candidate_id": "c030", "text": ""}
                if state["goal_state"]["visible_quantity"] == 1 else
                {"action": "stop", "candidate_id": "", "text": ""})
            return SimpleNamespace(content=json.dumps({**action, "reason": "goal progress"}))

    bridge = Bridge("")
    monkeypatch.setattr(live_browser, "PlaywrightCDPBridge", lambda _url: bridge)
    common = {"goal": "Get Nuggets quantity 2", "client": Client(), "model": "test:student",
              "out_dir": tmp_path, "max_steps": 5}
    paused = live_browser.run_live_browser_fortress(**common)
    assert paused["stop_reason"] == "clarification_required"
    assert len(paused["rows"]) == 1
    resumed = live_browser.run_live_browser_fortress(
        **common, resume_report=paused, clarification_answer="Tangy BBQ and Sweet N Sour")
    assert [row["decision"]["action"] for row in resumed["rows"]] == ["ask", "click", "click", "click", "stop"]
    assert resumed["rows"][1]["goal_state_after"]["required_choices_remaining"] == 1
    assert resumed["rows"][2]["goal_state_after"]["required_choices_remaining"] == 0
    assert resumed["rows"][3]["goal_state_after"]["visible_quantity"] == 2
    assert resumed["clarification"]["choices"] == ["Tangy BBQ Dipping Sauce 45 cal", "Sweet N Sour Dipping Sauce 50 cal"]
    assert "Tangy BBQ and Sweet" not in json.dumps(resumed)

    bridge.remaining, bridge.quantity = 2, 1
    manual_common = {**common, "out_dir": tmp_path / "manual"}
    paused_manual = live_browser.run_live_browser_fortress(**manual_common)
    bridge.remaining = 0
    resumed_manual = live_browser.run_live_browser_fortress(**manual_common, resume_report=paused_manual)
    assert resumed_manual["clarification"]["choice_method"] == "manual_ui"
    assert resumed_manual["rows"][-1]["decision"]["action"] == "stop"


def test_live_verifier_rejects_scroll_past_strongly_goal_aligned_item():
    candidates = [
        _candidate(55, "Chicken Quesadilla $7.55", tag="button"),
        _candidate(75, "Cantina Chicken Menu", tag="button"),
    ]
    ok, reason = verify_live_decision(
        {"action": "scroll", "candidate_id": "", "text": "down", "reason": "find item"},
        candidates,
        "Select a Chicken Quesadilla from Taco Bell",
    )
    assert ok is False
    assert "c055" in reason


def test_live_quantity_verifier_only_allows_progress_toward_requested_count():
    plus = _candidate(2, "Increase quantity by 1")
    next_control = _candidate(4, "Next")
    at_one = [plus, _candidate(3, "Current quantity is 1", tag="input")]
    at_two = [plus, _candidate(3, "Current quantity is 2", tag="input")]
    decision = {"action": "click", "candidate_id": "c002", "text": "", "reason": "quantity"}
    assert verify_live_decision(decision, at_one, "set quantity to 2")[0]
    ok, reason = verify_live_decision(
        {"action": "click", "candidate_id": "c004", "text": "", "reason": ""},
        [*at_one, next_control],
        "set quantity to 2",
    )
    assert ok is False
    assert "click c002" in reason
    ok, reason = verify_live_decision(decision, at_two, "set quantity to 2")
    assert ok is False
    assert "moves visible quantity 2 away" in reason


def test_live_verifier_rejects_unrequested_paid_and_negative_modifiers():
    candidates = [
        _candidate(2, "Extra Chicken +$1.59", tag="button"),
        _candidate(3, "No Chicken", tag="button"),
        _candidate(4, "Large +$2.88", tag="button"),
    ]
    extra = {"action": "click", "candidate_id": "c002", "text": "", "reason": ""}
    no_chicken = {"action": "click", "candidate_id": "c003", "text": "", "reason": ""}
    large = {"action": "click", "candidate_id": "c004", "text": "", "reason": ""}
    assert not verify_live_decision(extra, candidates, "Select a Chicken Quesadilla")[0]
    assert not verify_live_decision(no_chicken, candidates, "Select a Chicken Quesadilla")[0]
    assert verify_live_decision(large, candidates, "Select a large pizza")[0]


def test_quantity_trace_repeats_adjustment_without_consuming_next_teacher_rule():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Select cheese, set quantity to 2, then select large",
        "rows": [
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(1, "Cheese Pizza").public()],
                },
                "decision": {"action": "click", "candidate_id": "c001", "text": "", "reason": "item"},
                "execution": {"executed": True},
            },
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(2, "Increase quantity by 1", tag="button").public()],
                },
                "decision": {"action": "click", "candidate_id": "c002", "text": "", "reason": "quantity"},
                "execution": {"executed": True},
            },
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(3, "Large", tag="label").public()],
                },
                "decision": {"action": "click", "candidate_id": "c003", "text": "", "reason": "size"},
                "execution": {"executed": True},
            },
        ],
    }
    trace = compile_live_teacher_trace(report)
    plus = _candidate(7, "Increase quantity by 1", tag="button")
    large = _candidate(8, "Large", tag="label")

    def observation(quantity: int) -> dict:
        return {
            "url": "https://www.doordash.com/store/example",
            "candidates": [plus, _candidate(9, f"Current quantity is {quantity}", tag="input"), large],
        }

    item_history = [
        {
            "execution": {"executed": True},
            "bank_packet": [{"trace_index": 0, "trace_consumes_step": True}],
        }
    ]
    first_increment = retrieve_live_teacher_packet(
        compiled_trace=trace,
        observation=observation(1),
        history=item_history,
        goal="Select cheese, set quantity to 3, then select large",
    )
    assert first_increment[0]["binding_mode"] == "state_conditioned_quantity"
    assert first_increment[0]["trace_consumes_step"] is True
    assert first_increment[0]["required_next_action"]["candidate_id"] == "c007"

    increment_history = item_history + [
        {
            "execution": {"executed": True},
            "bank_packet": first_increment,
        }
    ]
    second_increment = retrieve_live_teacher_packet(
        compiled_trace=trace,
        observation=observation(2),
        history=increment_history,
        goal="Select cheese, set quantity to 3, then select large",
    )
    assert second_increment[0]["trace_index"] == 1
    assert second_increment[0]["trace_consumes_step"] is False

    completed_quantity_history = increment_history + [
        {
            "execution": {"executed": True},
            "bank_packet": second_increment,
        }
    ]
    next_rule = retrieve_live_teacher_packet(
        compiled_trace=trace,
        observation=observation(3),
        history=completed_quantity_history,
        goal="Select cheese, set quantity to 3, then select large",
    )
    assert next_rule[0]["trace_index"] == 2
    assert next_rule[0]["required_next_action"]["candidate_id"] == "c008"

    minus = _candidate(10, "Decrease quantity by 1", tag="button")
    decrement = retrieve_live_teacher_packet(
        compiled_trace=trace,
        observation={
            "url": "https://www.doordash.com/store/example",
            "candidates": [minus, _candidate(9, "Current quantity is 3", tag="input"), large],
        },
        history=item_history,
        goal="Select cheese, set quantity to 2, then select large",
    )
    assert decrement[0]["quantity_policy"]["direction"] == "decrease"
    assert decrement[0]["required_next_action"]["candidate_id"] == "c010"


def test_quantity_trace_skips_teacher_adjustment_when_target_is_already_met():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Set quantity to 2 and select large",
        "rows": [
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(2, "Increase quantity by 1", tag="button").public()],
                },
                "decision": {"action": "click", "candidate_id": "c002", "text": "", "reason": "quantity"},
                "execution": {"executed": True},
            },
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(3, "Large", tag="label").public()],
                },
                "decision": {"action": "click", "candidate_id": "c003", "text": "", "reason": "size"},
                "execution": {"executed": True},
            },
        ],
    }
    trace = compile_live_teacher_trace(report)
    packet = retrieve_live_teacher_packet(
        compiled_trace=trace,
        observation={
            "url": "https://www.doordash.com/store/example",
            "candidates": [
                _candidate(7, "Increase quantity by 1", tag="button"),
                _candidate(8, "Current quantity is 1", tag="input"),
                _candidate(9, "Large", tag="label"),
            ],
        },
        history=[],
        goal="Set quantity to 1 and select large",
    )
    assert packet[0]["trace_index"] == 1
    assert packet[0]["required_next_action"]["candidate_id"] == "c009"


def test_quantity_rule_never_rebinds_without_visible_quantity_state():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Select item and set quantity to 2",
        "rows": [
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(1, "Item").public()],
                },
                "decision": {"action": "click", "candidate_id": "c001", "text": "", "reason": "item"},
                "execution": {"executed": True},
            },
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(2, "Increase quantity by 1", tag="button").public()],
                },
                "decision": {"action": "click", "candidate_id": "c002", "text": "", "reason": "quantity"},
                "execution": {"executed": True},
            },
        ],
    }
    trace = compile_live_teacher_trace(report)
    packet = retrieve_live_teacher_packet(
        compiled_trace=trace,
        observation={
            "url": "https://www.doordash.com/store/example",
            "candidates": [_candidate(7, "Close Item", tag="button"), _candidate(8, "Next", tag="button")],
        },
        history=[
            {
                "execution": {"executed": True},
                "bank_packet": [{"trace_index": 0, "trace_consumes_step": True}],
            }
        ],
        goal="Select item and set quantity to 2",
    )
    assert packet == []


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


def test_live_teacher_bank_composes_goal_matched_item_quantity_and_terminal_rules():
    pizza = {
        "fortress_id": "live",
        "student_model": "teacher-a",
        "goal": "Select cheese pizza, set quantity to 2, and stop",
        "rows": [
            {
                "before": {
                    "url": "https://www.doordash.com/store/pizza",
                    "candidates": [_candidate(1, "Cheese Pizza").public()],
                },
                "decision": {"action": "click", "candidate_id": "c001", "text": "", "reason": "item"},
                "execution": {"executed": True},
            },
            {
                "before": {
                    "url": "https://www.doordash.com/store/pizza",
                    "candidates": [_candidate(2, "Increase quantity by 1", tag="button").public()],
                },
                "decision": {"action": "click", "candidate_id": "c002", "text": "", "reason": "quantity"},
                "execution": {"executed": True},
            },
            {
                "before": {"url": "https://www.doordash.com/store/pizza", "candidates": []},
                "decision": {"action": "stop", "candidate_id": "", "text": "", "reason": "complete"},
                "execution": {"executed": False, "status": "stop"},
            },
        ],
    }
    taco = {
        "fortress_id": "live",
        "student_model": "teacher-b",
        "goal": "Select a Chicken Quesadilla from Taco Bell",
        "rows": [
            {
                "before": {
                    "url": "https://www.doordash.com/store/taco-bell",
                    "candidates": [_candidate(5, "Chicken Quesadilla $7.55").public()],
                },
                "decision": {"action": "click", "candidate_id": "c005", "text": "", "reason": "item"},
                "execution": {"executed": True},
            }
        ],
    }
    bank = compile_live_teacher_bank(
        [pizza, taco],
        goal="Select a Chicken Quesadilla from Taco Bell, set quantity to 3, and stop",
    )
    assert [rule["target_label"] for rule in bank["rules"][:-1]] == [
        "Chicken Quesadilla $7.55",
        "Increase quantity by 1",
    ]
    assert bank["rules"][-1]["action"] == "stop"
    assert bank["rules"][0]["source_rule_model"] == "teacher-b"
    assert bank["rules"][1]["source_rule_model"] == "teacher-a"
    assert len({rule["source_rule_report_hash"] for rule in bank["rules"]}) == 2


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


def test_unbanked_exploration_does_not_consume_teacher_trace_progress():
    report = {
        "fortress_id": "live",
        "student_model": "teacher",
        "goal": "Select a chicken quesadilla",
        "rows": [
            {
                "before": {
                    "url": "https://www.doordash.com/store/example",
                    "candidates": [_candidate(5, "Chicken Quesadilla").public()],
                },
                "decision": {"action": "click", "candidate_id": "c005", "text": "", "reason": "item"},
                "execution": {"executed": True},
            }
        ],
    }
    trace = compile_live_teacher_trace(report)
    packet = retrieve_live_teacher_packet(
        compiled_trace=trace,
        observation={
            "url": "https://www.doordash.com/store/example",
            "candidates": [
                _candidate(7, "Careers", href="https://careers.example.com"),
                _candidate(8, "Double Cheeseburger"),
            ],
        },
        history=[
            {
                "execution": {"executed": True},
                "decision": {"action": "scroll", "candidate_id": "", "text": "down"},
                "bank_packet": [],
            }
        ],
        goal="Select a double cheeseburger",
    )
    assert packet[0]["trace_index"] == 0
    assert packet[0]["required_next_action"]["candidate_id"] == "c008"


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
