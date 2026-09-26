from __future__ import annotations

import json

from memory_system.fortresses.agency_retrieval_fortress import (
    LANE_ORACLE,
    LANE_RAW,
    LANE_RETRIEVED,
    LANE_RETRIEVED_COUNTERFACTUAL,
    LANE_WRONG_RETRIEVAL,
    _verify_action_contract,
    build_retrieval_messages,
    cross_app_transfer_cases,
    opaque_rule_catalog,
    retrieve_rule,
    run_retrieval_proof,
    verify_catalog_applicability,
)
from memory_system.fortresses.agency_transfer_fortress import (
    FAMILY_ALIAS,
    FAMILY_BOUNDARY,
    default_transfer_cases,
)
from memory_system.ollama_client import ChatResponse


def _teacher() -> dict:
    return {
        "teacher_model": "teacher",
        "raw_response_hash": "teacher_hash",
        "rules": {
            FAMILY_ALIAS: {
                "family": FAMILY_ALIAS,
                "observations": ["item alias", "quantity below target", "scoped increment is visible"],
                "required_affordances": ["Increase quantity for requested item"],
                "absent_affordances": [],
                "comparison": "match requested food identity to candidate label",
                "action_type": "tap",
                "target_selector": "requested item's increment control",
                "reject": ["irrelevant numbers and other item controls"],
                "postcondition": "quantity moves toward target",
                "stop_condition": "target quantity reached",
            },
            FAMILY_BOUNDARY: {
                "family": FAMILY_BOUNDARY,
                "observations": ["quantity mismatch", "no quantity-changing candidate"],
                "required_affordances": [],
                "absent_affordances": ["Increase quantity for requested item"],
                "comparison": "no visible candidate can repair or verify quantity",
                "action_type": "stop",
                "target_selector": "none",
                "reject": ["checkout and payment are not repair"],
                "postcondition": "unverified constraint does not cross boundary",
                "stop_condition": "no repair affordance exists",
            },
        },
    }


class FakeRetrievalStudent:
    provider = "ollama"

    def chat_response(self, **kwargs):
        user = json.loads(kwargs["messages"][1].content)
        if "rule_catalog" in user:
            candidates = list(user["current_state"]["candidate_actions"])
            has_increment = any("Increase quantity" in row["label"] for row in candidates)
            wanted = "item alias" if has_increment else "no quantity-changing candidate"
            selected = next(
                row["key"]
                for row in user["rule_catalog"]
                if wanted in " ".join(row["applicable_observations"])
            )
            return ChatResponse(
                content=json.dumps({"selected_rule_key": selected, "reason": "applicability"}),
                request_metadata={"provider": "ollama", "model": kwargs["model"]},
            )
        packet = list(user.get("bank_packet") or [])
        if packet and packet[0].get("required_next_action", {}).get("action_type") == "stop":
            decision = {"action_type": "stop", "target_id": "", "rationale": "capsule", "verifier": []}
        elif packet:
            decision = {"action_type": "tap", "target_id": "target-plus", "rationale": "capsule", "verifier": []}
        else:
            candidates = list(user["candidate_actions"])
            decision = {"action_type": "tap", "target_id": candidates[0]["target_id"], "rationale": "raw", "verifier": []}
        return ChatResponse(
            content=json.dumps(decision),
            request_metadata={"provider": "ollama", "model": kwargs["model"]},
        )


def test_opaque_catalog_hides_family_and_action_fields():
    catalog, mapping = opaque_rule_catalog(_teacher())
    assert len(catalog) == 2
    assert set(mapping.values()) == {FAMILY_ALIAS, FAMILY_BOUNDARY}
    text = json.dumps(catalog, sort_keys=True)
    assert FAMILY_ALIAS not in text
    assert FAMILY_BOUNDARY not in text
    assert "action_type" not in text
    assert "target_selector" not in text


def test_retrieval_prompt_hides_oracle_fields():
    case = next(case for case in default_transfer_cases() if case.split == "holdout")
    content = build_retrieval_messages(case=case, teacher=_teacher())[1].content
    assert '"family"' not in content
    assert "expected_action_type" not in content
    assert "expected_target_id" not in content


def test_teacher_predicates_route_without_case_family_or_expected_action():
    cases = [case for case in default_transfer_cases() if case.split == "holdout"]
    for case in cases:
        verification = verify_catalog_applicability(case=case, teacher=_teacher())
        assert len(verification["compatible_rule_keys"]) == 1
        prompt_free_payload = json.dumps(
            {
                "teacher": _teacher(),
                "state": case.model_state(),
                "verification": verification,
            }
        )
        assert "expected_action_type" not in prompt_free_payload
        assert "expected_target_id" not in prompt_free_payload


def test_teacher_predicate_verifier_repairs_inapplicable_model_proposal():
    class AlwaysFirstRetriever:
        provider = "ollama"

        def chat_response(self, **kwargs):
            user = json.loads(kwargs["messages"][1].content)
            return ChatResponse(
                content=json.dumps({"selected_rule_key": user["rule_catalog"][0]["key"], "reason": "guess"}),
                request_metadata={"provider": "ollama"},
            )

    case = next(case for case in default_transfer_cases() if case.case_id == "holdout_boundary_add_is_not_repair")
    result = retrieve_rule(case=case, teacher=_teacher(), client=AlwaysFirstRetriever(), model="student", seed=1)
    assert result["model_proposal_correct"] is False
    assert result["correct"] is True
    assert result["selection_mode"] == "teacher_predicate_repair"


def test_food_teacher_predicates_cover_cross_app_cases_without_new_labels():
    cases = cross_app_transfer_cases()
    assert {case.family for case in cases} == {FAMILY_ALIAS, FAMILY_BOUNDARY}
    for case in cases:
        verification = verify_catalog_applicability(case=case, teacher=_teacher())
        assert len(verification["compatible_rule_keys"]) == 1


def test_contract_verifier_rejects_visible_but_ungrounded_distractor():
    case = next(case for case in cross_app_transfer_cases() if case.case_id == "cross_shop_usb_cable_alias")
    packet = [{"required_next_action": {"action_type": "tap", "target_selector": "Increase quantity for intent.item"}}]
    action = {"decision": {"action_type": "tap", "target_id": "case-plus"}}
    passed, feedback = _verify_action_contract(action, packet, case)
    assert passed is False
    assert "no item grounding overlap" in feedback


def test_model_retrieval_routes_rules_without_family_oracle():
    report = run_retrieval_proof(
        teacher=_teacher(),
        student_client=FakeRetrievalStudent(),
        student_model="student",
        trials=1,
        lanes=(LANE_RAW, LANE_ORACLE, LANE_RETRIEVED, LANE_WRONG_RETRIEVAL, LANE_RETRIEVED_COUNTERFACTUAL),
    )
    assert report["retrieval_accuracy"] == 1.0
    assert report["success_counts"][LANE_RETRIEVED] == 10
    assert report["success_counts"][LANE_RAW] < report["success_counts"][LANE_RETRIEVED]
    assert report["success_counts"][LANE_WRONG_RETRIEVAL] == 0
    assert report["success_counts"][LANE_RETRIEVED_COUNTERFACTUAL] == 0
    assert report["first_pass_success_counts"][LANE_RETRIEVED] == 10
    assert report["case_clustered_comparison"]
    assert report["authenticity"]["retrieval_hidden_oracle_leaks"] == 0
    assert report["authenticity"]["action_hidden_oracle_leaks"] == 0
    assert report["authenticity"]["action_prompt_difference_is_bank_only"] is True
