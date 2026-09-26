from __future__ import annotations

import json

from memory_system.fortresses.agency_transfer_fortress import (
    FAMILY_ALIAS,
    FAMILY_BOUNDARY,
    LANE_EXECUTABLE,
    LANE_MINIMAL,
    LANE_RAW,
    LANE_TEACHER,
    build_student_messages,
    build_teacher_messages,
    default_transfer_cases,
    extract_teacher_rules,
    run_transfer_proof,
    score_student_decision,
    write_transfer_artifacts,
)
from memory_system.ollama_client import ChatResponse


def _teacher_payload() -> dict:
    return {
        "train_decisions": [
            {"case_id": "train_alias_pizza_pie", "action_type": "tap", "target_id": "target-plus", "why": "scoped match"},
            {"case_id": "train_missing_quantity_affordance", "action_type": "stop", "target_id": "", "why": "no repair"},
        ],
        "rules": [
            {
                "family": FAMILY_ALIAS,
                "observations": ["requested item and quantity", "candidate item labels", "numbers by semantic role"],
                "comparison": "match food identity and modifiers; compare only quantity-role numbers",
                "action_type": "tap",
                "target_selector": "requested item's increment control",
                "reject": ["delivery, rating, price, promotion, or another item's control", "Add to cart as quantity repair"],
                "postcondition": "requested item's visible quantity moves toward requested quantity",
                "stop_condition": "stop if no scoped quantity-changing control is visible",
            },
            {
                "family": FAMILY_BOUNDARY,
                "observations": ["quantity mismatch", "visible candidate affordances"],
                "comparison": "test whether any visible candidate can change or verify quantity",
                "action_type": "stop",
                "target_selector": "none",
                "reject": ["Add to cart, checkout, or payment as quantity evidence"],
                "postcondition": "unverified quantity never crosses the order boundary",
                "stop_condition": "stop before any irreversible or non-repair action",
            },
        ],
        "shared_principle": "advance only through an affordance that can establish the unresolved invariant",
    }


class FakeTeacher:
    provider = "ollama"

    def chat_response(self, **kwargs):
        return ChatResponse(
            content=json.dumps(_teacher_payload()),
            request_metadata={"provider": "ollama", "model": kwargs["model"]},
        )


class RepairingTeacher:
    provider = "ollama"

    def __init__(self):
        self.calls = 0

    def chat_response(self, **kwargs):
        self.calls += 1
        payload = _teacher_payload()
        if self.calls == 1:
            boundary = next(rule for rule in payload["rules"] if rule["family"] == FAMILY_BOUNDARY)
            boundary["action_type"] = "tap"
            boundary["target_selector"] = "Add to cart"
        return ChatResponse(
            content=json.dumps(payload),
            request_metadata={"provider": "ollama", "model": kwargs["model"]},
        )


class FakeStudent:
    provider = "ollama"

    def chat_response(self, **kwargs):
        state = json.loads(kwargs["messages"][1].content)
        packet = list(state.get("bank_packet") or [])
        candidates = list(state["candidate_actions"])
        if packet and any("required_next_action" in row for row in packet):
            action = packet[0]["required_next_action"]
            if action.get("action_type") == "stop":
                decision = {"action_type": "stop", "target_id": "", "rationale": "capsule", "verifier": []}
            else:
                decision = {"action_type": "tap", "target_id": "target-plus", "rationale": "capsule", "verifier": []}
        elif packet and any("action_type" in row for row in packet):
            if any(str(row.get("action_type") or "") == "stop" for row in packet):
                decision = {"action_type": "stop", "target_id": "", "rationale": "rule", "verifier": []}
            else:
                decision = {"action_type": "tap", "target_id": "target-plus", "rationale": "rule", "verifier": []}
        else:
            target = next((row["target_id"] for row in candidates if row["target_id"] == "add-cart"), candidates[0]["target_id"])
            decision = {"action_type": "tap", "target_id": target, "rationale": "raw", "verifier": []}
        return ChatResponse(content=json.dumps(decision), request_metadata={"provider": "ollama", "model": kwargs["model"]})


def test_teacher_sees_only_train_states_and_must_clear_them():
    messages = build_teacher_messages()
    content = messages[1].content
    assert "train_alias_pizza_pie" in content
    assert "train_missing_quantity_affordance" in content
    assert "holdout_" not in content
    artifact = extract_teacher_rules(client=FakeTeacher(), model="teacher")
    assert artifact["train_clearance"] == {
        "train_alias_pizza_pie": True,
        "train_missing_quantity_affordance": True,
    }
    assert set(artifact["rules"]) == {FAMILY_ALIAS, FAMILY_BOUNDARY}


def test_teacher_rule_must_match_cleared_decision_before_promotion():
    client = RepairingTeacher()
    artifact = extract_teacher_rules(client=client, model="teacher")
    assert client.calls == 2
    assert artifact["teacher_calls"] == 2
    assert artifact["teacher_attempts"][0]["train_clearance"]["train_missing_quantity_affordance"] is True
    assert artifact["teacher_attempts"][0]["rules_match_cleared_decisions"][FAMILY_BOUNDARY] is False
    assert artifact["teacher_attempts"][1]["rules_match_cleared_decisions"][FAMILY_BOUNDARY] is True


def test_student_prompt_contains_no_hidden_family_or_expected_action():
    case = next(item for item in default_transfer_cases() if item.split == "holdout")
    messages = build_student_messages(case=case, bank_packet=[])
    content = messages[1].content
    assert '"family"' not in content
    assert "expected_action_type" not in content
    assert "expected_target_id" not in content


def test_hidden_oracle_scores_alias_and_boundary_actions():
    cases = default_transfer_cases()
    alias = next(item for item in cases if item.case_id == "holdout_alias_margherita_pie")
    boundary = next(item for item in cases if item.case_id == "holdout_boundary_cart_no_edit")
    assert score_student_decision(alias, {"action_type": "tap", "target_id": "target-plus"})["success"] is True
    assert score_student_decision(boundary, {"action_type": "stop", "target_id": ""})["success"] is True
    assert score_student_decision(boundary, {"action_type": "tap", "target_id": "place-order"})["boundary_violation"] is True


def test_transfer_proof_keeps_teacher_out_of_student_lanes_and_audits_prompts(tmp_path):
    teacher = extract_teacher_rules(client=FakeTeacher(), model="teacher")
    report = run_transfer_proof(
        teacher=teacher,
        student_client=FakeStudent(),
        student_model="student",
        trials=1,
        lanes=(LANE_RAW, LANE_MINIMAL, LANE_TEACHER, LANE_EXECUTABLE),
    )
    assert report["teacher_calls_in_student_lanes"] == 0
    assert report["authenticity"]["prompt_difference_is_bank_packet_only"] is True
    assert report["authenticity"]["hidden_oracle_leaks"] == 0
    assert report["success_counts"][LANE_EXECUTABLE] == 10
    assert report["success_counts"][LANE_RAW] < report["success_counts"][LANE_EXECUTABLE]
    artifacts = write_transfer_artifacts(report=report, teacher=teacher, out_dir=tmp_path)
    assert set(artifacts) == {"train_cases", "holdout_cases", "teacher_extraction", "report_json", "report_markdown"}
