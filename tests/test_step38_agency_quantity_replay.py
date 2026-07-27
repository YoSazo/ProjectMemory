from __future__ import annotations

import json

import pytest

from memory_system.cli import main
from memory_system.fortresses.agency_quantity_replay import (
    DEFAULT_AGENCY_LEDGER_PATH,
    LANE_NVIDIA_NO_ABOVE,
    LANE_NVIDIA_NO_BELOW,
    LANE_NVIDIA_NO_VERIFIER,
    LANE_NVIDIA_SWAP_DIRECTION,
    LANE_NVIDIA_FAMILY_ONLY,
    LANE_NVIDIA_SEMANTIC,
    LANE_LABEL_PRICE,
    LANE_LABEL_QUANTITY,
    LANE_LABEL_RANDOM,
    LANE_LABEL_TEXT,
    QUANTITY_RULE_ID,
    _semantic_compiled_runtime_policy,
    _student_bank_packet,
    build_quantity_student_messages,
    default_quantity_replay_cases,
    extract_live_quantity_teacher_rule,
    quantity_transmutation_to_ledger_entry,
    retrieve_quantity_rules,
    run_quantity_model_authentic_replay,
    run_quantity_model_student_lane,
    run_quantity_replay_proof,
    run_quantity_student_lane,
    seed_quantity_teacher_transmutation,
    write_quantity_manifests,
    write_sanitized_quantity_proof,
)
from memory_system.fortresses.meta_fortress import GlobalTransmutationLedger
from memory_system.ollama_client import ChatResponse


class FakeStudentClient:
    def __init__(self, *, malformed: bool = False) -> None:
        self.calls = []
        self.malformed = malformed

    def chat_response(self, **kwargs):
        self.calls.append(kwargs)
        if self.malformed:
            return ChatResponse(content="not json", request_metadata={"provider": "ollama", "fake": True})
        user = json.loads(kwargs["messages"][1].content)
        bank = list(user.get("bank_packet") or [])
        current = int(user.get("current_quantity") or 0)
        requested = int(user.get("requested_quantity") or 0)
        candidates = list(user.get("candidate_actions") or [])
        if not bank:
            target = "add-to-cart"
        elif current == requested or user.get("boundary_state") == "near_boundary":
            return ChatResponse(
                content=json.dumps(
                    {
                        "action_type": "stop",
                        "target_id": "",
                        "target_label": "quantity already verified",
                        "rationale": "bank says verify or stop at boundary",
                        "verifier": ["fresh quantity evidence"],
                    }
                ),
                request_metadata={"provider": "ollama", "fake": True},
            )
        else:
            action = "increment" if current < requested else "decrement"
            target = next(
                row["target_id"]
                for row in candidates
                if row.get("metadata", {}).get("quantity_action") == action
                and "cheese pizza" in str(row.get("metadata", {}).get("item_context", "")).lower()
            )
        return ChatResponse(
            content=json.dumps(
                {
                    "action_type": "tap",
                    "target_id": target,
                    "target_label": target,
                    "rationale": "selected from model output",
                    "verifier": ["fresh quantity evidence"],
                }
            ),
            request_metadata={"provider": "ollama", "fake": True},
        )


class FakeTeacherClient:
    def chat_response(self, **kwargs):
        payload = {
            "teacher_trace_id": "live_fake_deepseek_trace",
            "constraint_family": "numeric",
            "root_cause": "The student treated quantity as cart progress instead of a slot invariant.",
            "transmutations": [
                {
                    "transmutation": "Require item-scoped quantity evidence before Add to cart.",
                    "action_schema": "adjust_quantity_then_reinspect",
                    "constraints_before": ["quantity missing"],
                    "constraints_after": ["quantity verified"],
                    "observation_cues": ["increase quantity", "quantity"],
                    "verifier": ["fresh observation shows requested quantity"],
                    "repair_policy": ["tap item-scoped increment/decrement"],
                    "boundary_policy": ["stop before payment while quantity unverified"],
                    "transfer_targets": ["doordash", "ubereats"],
                    "confidence": 0.91,
                }
            ],
        }
        return ChatResponse(
            content=json.dumps(payload),
            reasoning_content="teacher inspected missing quantity evidence",
            usage={"total_tokens": 123},
            request_metadata={"provider": "nvidia", "model": kwargs["model"]},
        )


def _quantity_ledger() -> GlobalTransmutationLedger:
    transmutation = seed_quantity_teacher_transmutation()
    entry = quantity_transmutation_to_ledger_entry(transmutation)
    return GlobalTransmutationLedger([entry])


def _nvidia_quantity_ledger(*, transfer_targets: list[str] | None = None) -> tuple[GlobalTransmutationLedger, str, str]:
    raw_hash = "live_hash_for_test"
    base = seed_quantity_teacher_transmutation(source_model="deepseek-ai/deepseek-v4-flash")
    data = base.to_dict()
    data.update(
        {
            "rule_id": "atm_numeric_live_test",
            "source_teacher_trace_id": "trace_live_deepseek_test",
            "action_schema": "adjust quantity via stepper or plus/minus button until visible count equals 2, then verify in cart",
            "transfer_targets": transfer_targets or ["same app", "current page-kind", "numeric cardinality preservation"],
        }
    )
    metadata = dict(data.get("metadata") or {})
    metadata["raw_teacher_response_hash"] = raw_hash
    metadata["teacher_provider"] = "nvidia"
    data["metadata"] = metadata
    transmutation = base.__class__(**data).normalized()
    entry = quantity_transmutation_to_ledger_entry(transmutation)
    return GlobalTransmutationLedger([entry]), raw_hash, transmutation.rule_id


def test_quantity_replay_freezes_train_and_holdout_manifests(tmp_path):
    artifacts = write_quantity_manifests(out_dir=tmp_path)
    train_rows = [
        json.loads(line)
        for line in (tmp_path / "train_quantity_cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    holdout_rows = [
        json.loads(line)
        for line in (tmp_path / "holdout_quantity_cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert artifacts["train_cases"].endswith("train_quantity_cases.jsonl")
    assert [row["case_id"] for row in train_rows] == ["train_two_stepper_visible"]
    assert {row["case_id"] for row in holdout_rows} == {
        "holdout_digit_2",
        "holdout_pair",
        "holdout_already_two",
        "holdout_accidental_three",
        "holdout_overcount_four_to_two",
        "holdout_overcount_five_to_three",
        "holdout_overcount_wrong_item_distractor",
        "holdout_cart_only_quantity",
        "holdout_duplicated_plus_buttons",
        "holdout_checkout_unverified",
        "holdout_ubereats_sibling_stepper",
        "holdout_quantity_three",
        "holdout_quantity_four",
        "holdout_alias_pie_irrelevant_numeric",
    }


def test_quantity_rule_retrieval_uses_observation_cues_and_transfers_to_ubereats():
    ledger = _quantity_ledger()
    ubereats_case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_ubereats_sibling_stepper")

    retrieved = retrieve_quantity_rules(ledger=ledger, snapshot=ubereats_case.snapshot())

    assert retrieved
    assert retrieved[0]["rule_id"] == QUANTITY_RULE_ID
    assert "quantity" in retrieved[0]["cue_text"]


def test_quantity_replay_improves_frozen_student_without_teacher_calls():
    report = run_quantity_replay_proof(ledger=_quantity_ledger(), student_model="mistral:7b-instruct")

    assert report["teacher_calls_in_student_lanes"] == 0
    assert report["case_count"] == 14
    assert report["raw_success_count"] < report["bank_success_count"]
    assert report["bank_success_count"] == 14
    assert report["improvement_count"] == report["bank_success_count"] - report["raw_success_count"]
    duplicated = next(row for row in report["rows"] if row["case"]["case_id"] == "holdout_duplicated_plus_buttons")
    assert duplicated["bank_trace"]["action"]["target_id"] == "pizza-plus"


def test_quantity_student_lane_rejects_teacher_client():
    case = default_quantity_replay_cases()[0]

    with pytest.raises(RuntimeError, match="Teacher client is forbidden"):
        run_quantity_student_lane(case=case, model="mistral:7b-instruct", teacher_client=object())


def test_model_authentic_replay_requires_student_client_calls_and_scores_state():
    client = FakeStudentClient()
    cases = [case for case in default_quantity_replay_cases() if case.split == "train" or case.case_id not in {
        "holdout_quantity_three",
        "holdout_quantity_four",
        "holdout_alias_pie_irrelevant_numeric",
    }]
    report = run_quantity_model_authentic_replay(
        ledger=_quantity_ledger(),
        student_client=client,
        student_model="mistral:7b-instruct",
        cases=cases,
        trials=2,
        seed_base=100,
        lanes=("raw", "full_rich_rule"),
    )
    expected_holdouts = sum(1 for case in cases if case.split == "holdout")
    expected_episodes = expected_holdouts * 2

    assert len(client.calls) == expected_episodes * 2
    assert {call["seed"] for call in client.calls} == {100, 101}
    assert report["authenticity_audit"]["student_lanes_made_real_requests"] is True
    assert report["authenticity_audit"]["student_lanes_received_responses"] is True
    assert report["authenticity_audit"]["student_lanes_parsed_responses"] is True
    assert report["authenticity_audit"]["hardcoded_policy_selected_student_actions"] is False
    assert report["authenticity_audit"]["candidate_rule_from_nvidia_response"] is False
    assert report["teacher_calls_in_student_lanes"] == 0
    assert report["raw_success_count"] < report["bank_success_count"]
    one_step_unsolved = 2 * 2
    assert report["bank_success_count"] == expected_episodes - one_step_unsolved
    assert report["raw_verifier_failure_count"] > 0
    assert report["paired_discordance"][0]["paired_count"] == expected_episodes


def test_model_authentic_lane_records_parse_failure_without_fallback():
    case = default_quantity_replay_cases()[1]
    result = run_quantity_model_student_lane(
        case=case,
        model="mistral:7b-instruct",
        client=FakeStudentClient(malformed=True),
        retrieved_rules=[],
        seed=123,
    )

    assert result["success"] is False
    assert result["parse_failure"] is True
    assert result["execution"]["failure_type"] == "parse_failure"
    assert result["decision"] is None
    assert result["request_attempted"] is True
    assert result["response_received"] is True
    assert result["response_parsed"] is False


def test_live_teacher_extraction_preserves_response_hash_and_holdout_guard():
    extraction = extract_live_quantity_teacher_rule(teacher_client=FakeTeacherClient())

    assert extraction["teacher_call_status"] == "completed"
    assert extraction["teacher_provider"] == "nvidia"
    assert extraction["raw_teacher_response_hash"]
    assert extraction["compressed_transmutation"]["source_teacher_trace_id"] == "live_fake_deepseek_trace"
    assert extraction["holdout_leakage_guard"]["teacher_saw_splits"] == ["train"]
    assert extraction["holdout_leakage_guard"]["teacher_holdout_case_count"] == 0


def test_semantic_compiler_does_not_invent_quantity_actions_without_teacher_fields():
    case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_digit_2")
    snapshot = case.snapshot()
    placebo_rule = {
        "rule_id": "placebo_numeric_rule_v0",
        "transmutation": "numeric constraint exists",
        "action_family": "numeric",
        "preconditions": [],
        "verifier": [],
        "metadata": {"constraint_family": "numeric"},
    }

    policy = _semantic_compiled_runtime_policy(placebo_rule, snapshot)

    assert policy["compiler_invented_actions"] is False
    assert policy["when"] == "current_quantity < requested_quantity"
    assert policy["choose"] == ""
    assert policy["teacher_policy_clauses"]["teacher_actions_present"]["below"] is False


def test_student_prompt_hides_lane_identity_when_bank_is_empty():
    case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_digit_2")
    raw_user = json.loads(
        build_quantity_student_messages(case=case, retrieved_rules=[], trial_index=3, lane="raw")[1].content
    )
    semantic_user = json.loads(
        build_quantity_student_messages(case=case, retrieved_rules=[], trial_index=3, lane=LANE_NVIDIA_SEMANTIC)[1].content
    )

    assert "bank_lane" not in raw_user
    assert "bank_lane" not in semantic_user
    assert semantic_user == raw_user


def test_nvidia_semantic_and_family_only_packets_separate_teacher_knowledge():
    ledger, raw_hash, rule_id = _nvidia_quantity_ledger()
    case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_digit_2")
    retrieved = retrieve_quantity_rules(
        ledger=ledger,
        snapshot=case.snapshot(),
        policy_kind=LANE_NVIDIA_SEMANTIC,
        require_provenance_hash=raw_hash,
        source_filter="nvidia",
    )

    semantic_packet = _student_bank_packet(retrieved, lane=LANE_NVIDIA_SEMANTIC, snapshot=case.snapshot())
    family_packet = _student_bank_packet(retrieved, lane=LANE_NVIDIA_FAMILY_ONLY, snapshot=case.snapshot())

    assert retrieved[0]["rule_id"] == rule_id
    assert semantic_packet[0]["runtime_policy"]["choose"]
    assert "rule_id" not in semantic_packet[0]
    assert "rule_id" not in semantic_packet[0]["runtime_policy"]
    assert semantic_packet[0]["runtime_policy"]["teacher_policy_clauses"]["action_when_below_target"]
    assert family_packet[0]["constraint_frame"] == "numeric quantity constraint"
    assert "rule_id" not in family_packet[0]
    assert "runtime_policy" not in family_packet[0]


def test_nvidia_semantic_clause_ablation_packets_are_causal():
    ledger, raw_hash, _rule_id = _nvidia_quantity_ledger()
    below_case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_quantity_three")
    above_case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_accidental_three")
    equal_case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_already_two")

    below_rule = retrieve_quantity_rules(
        ledger=ledger,
        snapshot=below_case.snapshot(),
        policy_kind=LANE_NVIDIA_SEMANTIC,
        require_provenance_hash=raw_hash,
        source_filter="nvidia",
    )
    above_rule = retrieve_quantity_rules(
        ledger=ledger,
        snapshot=above_case.snapshot(),
        policy_kind=LANE_NVIDIA_SEMANTIC,
        require_provenance_hash=raw_hash,
        source_filter="nvidia",
    )
    equal_rule = retrieve_quantity_rules(
        ledger=ledger,
        snapshot=equal_case.snapshot(),
        policy_kind=LANE_NVIDIA_SEMANTIC,
        require_provenance_hash=raw_hash,
        source_filter="nvidia",
    )

    no_below = _student_bank_packet(below_rule, lane=LANE_NVIDIA_NO_BELOW, snapshot=below_case.snapshot())[0]["runtime_policy"]
    no_above = _student_bank_packet(above_rule, lane=LANE_NVIDIA_NO_ABOVE, snapshot=above_case.snapshot())[0]["runtime_policy"]
    swapped = _student_bank_packet(below_rule, lane=LANE_NVIDIA_SWAP_DIRECTION, snapshot=below_case.snapshot())[0]["runtime_policy"]
    no_verifier = _student_bank_packet(equal_rule, lane=LANE_NVIDIA_NO_VERIFIER, snapshot=equal_case.snapshot())[0]["runtime_policy"]

    assert no_below["when"] == "current_quantity < requested_quantity"
    assert no_below["choose"] == "observe item quantity state without selecting a quantity direction"
    assert no_above["when"] == "current_quantity > requested_quantity"
    assert no_above["choose"] == "observe item quantity state without selecting a quantity direction"
    assert "causal_clause_ablation" not in swapped
    assert swapped["choose"] == "choose decrement/minus/stepper control scoped to requested item"
    assert no_verifier["when"] == "current_quantity == requested_quantity"
    assert no_verifier["choose"] == ""


def test_minimal_label_controls_expose_only_constraint_frame():
    case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_digit_2")
    frames = {}
    for lane in (LANE_LABEL_QUANTITY, LANE_LABEL_PRICE, LANE_LABEL_TEXT, LANE_LABEL_RANDOM):
        packet = _student_bank_packet(
            [
                {
                    "rule_id": f"{lane}_control_v0",
                    "score": 0.0,
                    "metadata": {
                        "constraint_frame": {
                            LANE_LABEL_QUANTITY: "numeric quantity constraint",
                            LANE_LABEL_PRICE: "numeric price constraint",
                            LANE_LABEL_TEXT: "text identity constraint",
                            LANE_LABEL_RANDOM: "calendar color constraint",
                        }[lane]
                    },
                }
            ],
            lane=lane,
            snapshot=case.snapshot(),
        )
        assert list(packet[0]) == ["constraint_frame"]
        frames[lane] = packet[0]["constraint_frame"]

    assert frames[LANE_LABEL_QUANTITY] == "numeric quantity constraint"
    assert frames[LANE_LABEL_PRICE] == "numeric price constraint"
    assert frames[LANE_LABEL_TEXT] == "text identity constraint"
    assert frames[LANE_LABEL_RANDOM] == "calendar color constraint"


def test_nvidia_rule_is_quarantined_from_ubereats_without_explicit_transfer_scope():
    ledger, raw_hash, _rule_id = _nvidia_quantity_ledger(transfer_targets=["same app", "current page-kind"])
    ubereats_case = next(case for case in default_quantity_replay_cases() if case.case_id == "holdout_ubereats_sibling_stepper")
    report = run_quantity_model_authentic_replay(
        ledger=ledger,
        student_client=FakeStudentClient(),
        student_model="mistral:7b-instruct",
        cases=[default_quantity_replay_cases()[0], ubereats_case],
        trials=1,
        seed_base=900,
        lanes=("raw", LANE_NVIDIA_SEMANTIC),
        required_teacher_response_hash=raw_hash,
        candidate_rule_from_nvidia_response=True,
    )

    assert report["authenticity_audit"]["retrieved_rule_provenance_hash_mismatch_count"] == 0
    assert report["authenticity_audit"]["nvidia_rule_quarantined_from_ubereats"] is True
    assert report["authenticity_audit"]["nvidia_ubereats_retrieval_count"] == 0


def test_sanitized_proof_includes_compressed_teacher_rule_fields(tmp_path):
    extraction = extract_live_quantity_teacher_rule(teacher_client=FakeTeacherClient())
    report = {
        "replay_id": "proof_test",
        "student_model": "mistral:7b-instruct",
        "trial_count_per_holdout": 1,
        "lanes": ["raw"],
        "teacher_extraction": extraction,
        "rows": [],
    }

    artifacts = write_sanitized_quantity_proof(report=report, out_dir=tmp_path)
    proof = json.loads((tmp_path / "agency_quantity_authentic_replay.json").read_text(encoding="utf-8"))

    assert artifacts["proof_json"].endswith("agency_quantity_authentic_replay.json")
    assert proof["teacher_compressed_rule_fields"]["action_schema"] == "adjust_quantity_then_reinspect"
    assert proof["teacher_compressed_rule_fields"]["teacher_policy_clauses"]["teacher_actions_present"]["below"] is True


def test_agency_quantity_replay_cli_writes_ledger_and_reports(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "reports"
    rc = main(
        [
            "agency",
            "quantity-replay",
            "--student-model",
            "mistral:7b-instruct",
            "--out-dir",
            str(out_dir),
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["student_model"] == "mistral:7b-instruct"
    assert payload["case_count"] == 14
    assert payload["bank_success_count"] == 14
    assert payload["teacher_calls_in_student_lanes"] == 0
    assert (tmp_path / DEFAULT_AGENCY_LEDGER_PATH).exists()
    assert (out_dir / "quantity_replay_report.json").exists()
    assert (out_dir / "quantity_replay_report.md").exists()
