from __future__ import annotations

import json

from memory_system import cli
from memory_system.fortresses.agency_automation import (
    AGENCY_AUTOMATION_ID,
    DEFAULT_AGENCY_AUTOMATION_TEACHER_MODEL,
    agency_automation_architecture_spec,
    build_micro_fortress_plan,
    compress_teacher_response,
    detect_confusion,
    infer_dynamic_constraints,
    run_agency_automation,
    write_agency_automation_artifacts,
)
from memory_system.ollama_client import ChatResponse


class _FakeAgencyTeacher:
    def __init__(self, *, wrap_json: bool = False) -> None:
        self.wrap_json = wrap_json
        self.calls: list[dict[str, object]] = []

    def chat(self, *, model, messages, temperature=0.2, num_ctx=None):
        payload = (
            json.loads(messages[-1].content)
            if messages
            else {"micro_fortress": {"micro_fortress_id": "manual_micro_fortress"}}
        )
        self.calls.append(
            {
                "model": model,
                "temperature": temperature,
                "num_ctx": num_ctx,
                "micro_fortress_id": payload["micro_fortress"]["micro_fortress_id"],
            }
        )
        body = {
            "teacher_trace_id": "teacher_quantity_001",
            "constraint_family": "numeric",
            "root_cause": "The quantity constraint was present in the prompt but not grounded by a visible count control.",
            "transmutations": [
                {
                    "transmutation": "Trade vague cart progress for numeric cardinality preservation with visible count evidence.",
                    "action_schema": "quantity stepper grounding",
                    "constraints_before": ["quantity must equal 2", "item modal or cart is visible"],
                    "constraints_after": ["visible quantity equals 2 before checkout", "cart summary confirms quantity"],
                    "observation_cues": ["plus or increment control", "quantity text", "cart line item count"],
                    "verifier": ["modal or cart shows quantity 2", "price alone is not accepted as count evidence"],
                    "repair_policy": ["if the count does not change after tap, inspect again and choose a different control"],
                    "boundary_policy": ["stop before checkout if quantity cannot be verified"],
                    "transfer_targets": ["Uber Eats item modal", "Amazon quantity dropdown", "Instacart cart quantity"],
                    "acceptance_tests": ["quantity two survives same, mutated, and sibling cases"],
                    "confidence": 0.92,
                }
            ],
            "fortress_mutations": ["hidden stepper", "cart-only count", "sibling app dropdown"],
            "teacher_stop_conditions": ["no visible count evidence", "payment boundary visible"],
        }
        text = json.dumps(body)
        if self.wrap_json:
            return f"Teacher trace follows:\n{text}\nEnd."
        return text


class _FakeReasoningTeacher(_FakeAgencyTeacher):
    provider = "nvidia"

    def chat_response(self, *, model, messages, temperature=0.2, num_ctx=None, max_tokens=None, reasoning_effort=None):
        content = self.chat(model=model, messages=messages, temperature=temperature, num_ctx=num_ctx)
        return ChatResponse(
            content=content,
            reasoning_content="teacher inspected missing quantity evidence",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            request_metadata={
                "provider": "nvidia",
                "model": model,
                "reasoning_effort": reasoning_effort,
                "max_tokens": max_tokens,
            },
        )


def test_agency_automation_spec_is_meta_fortress_centered_and_easy_to_run():
    spec = agency_automation_architecture_spec()
    component_names = {component["name"] for component in spec["components"]}

    assert spec["automation_id"] == AGENCY_AUTOMATION_ID
    assert spec["happy_path"]["default_teacher_model"] == DEFAULT_AGENCY_AUTOMATION_TEACHER_MODEL
    assert "meta_fortress_router" in component_names
    assert "micro_fortress_factory" in component_names
    assert "trace_compressor" in component_names
    assert "global_transmutation_ledger" in component_names
    assert "budget_controller" in component_names


def test_dynamic_constraints_find_quantity_boundary_and_exact_item():
    prompt = "Doordash me two large cheese pizzas from Dominos and stop before payment."

    constraints = infer_dynamic_constraints(prompt)
    kinds = {constraint.kind for constraint in constraints}
    labels = " ".join(constraint.label for constraint in constraints).lower()

    assert "numeric" in kinds
    assert "boundary" in kinds
    assert "exact_match" in kinds
    assert "quantity must equal 2" in labels
    assert "large" in labels
    assert "dominos" in labels


def test_confusion_builds_quantity_micro_fortress_with_transfer_cases():
    prompt = "Doordash me two large cheese pizzas from Dominos and stop before payment."
    constraints = infer_dynamic_constraints(prompt)
    confusion = detect_confusion(
        prompt=prompt,
        constraints=constraints,
        observation="DoorDash item modal shows Large Cheese Pizza and Add to cart, but no quantity evidence.",
        page_kind="dd_item_modal",
    )
    plan = build_micro_fortress_plan(confusion=confusion, constraints=constraints)

    assert confusion.uncertainty_type == "ungrounded_numeric_constraint"
    assert confusion.teacher_required is True
    assert plan.parent_fortress_id == AGENCY_AUTOMATION_ID
    assert plan.teacher_prompt_budget["estimated_teacher_input_tokens"] > 0
    assert len(plan.cases) == 4
    assert {case["mutation_tier"] for case in plan.cases} >= {"same", "mutated", "sibling", "cross_domain"}
    assert all("quantity must equal 2" == case["focus_constraint"] for case in plan.cases)
    assert any("teacher trace" in gate for gate in plan.clearance_gates)


def test_teacher_response_compresses_into_transferable_rule():
    prompt = "Doordash me two large cheese pizzas from Dominos and stop before payment."
    constraints = infer_dynamic_constraints(prompt)
    confusion = detect_confusion(prompt=prompt, constraints=constraints)
    plan = build_micro_fortress_plan(confusion=confusion, constraints=constraints)
    raw = _FakeAgencyTeacher().chat(model="gemini-2.0-flash-lite", messages=[], temperature=0.1)

    compressed = compress_teacher_response(
        raw_response=raw,
        parse_mode="json",
        plan=plan,
        confusion=confusion,
        teacher_model="gemini-2.0-flash-lite",
    )

    assert len(compressed) == 1
    rule = compressed[0]
    assert rule.constraint_family == "numeric"
    assert rule.confidence >= 0.9
    assert "quantity stepper grounding" == rule.action_schema
    assert "Uber Eats item modal" in rule.transfer_targets
    assert rule.to_ledger_entry(app_family="doordash").domain == "agency"


def test_run_agency_automation_dry_run_skips_teacher_and_estimates_budget():
    report = run_agency_automation(
        prompt="Doordash me two large cheese pizzas from Dominos and stop before payment.",
        observation="DoorDash item modal visible.",
        dry_run=True,
    )

    assert report["teacher_call_status"] == "skipped_dry_run"
    assert report["compressed_transmutation_count"] == 0
    assert report["micro_fortress"]["parent_fortress_id"] == AGENCY_AUTOMATION_ID
    assert report["micro_fortress"]["teacher_prompt_budget"]["estimated_teacher_input_tokens"] > 0
    assert report["ledger_summary"]["entry_count"] == 0


def test_run_agency_automation_with_teacher_populates_ledger_and_artifacts(tmp_path):
    teacher = _FakeAgencyTeacher(wrap_json=True)

    report = run_agency_automation(
        prompt="Doordash me two large cheese pizzas from Dominos and stop before payment.",
        observation="DoorDash item modal shows Large Cheese Pizza and Add to cart.",
        teacher_model="gemini-2.0-flash-lite",
        teacher_client=teacher,
        temperature=0.05,
        num_ctx=8192,
    )
    artifacts = write_agency_automation_artifacts(report=report, out_dir=tmp_path)
    loaded = json.loads((tmp_path / "agency_automation_report.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "agency_automation_report.md").read_text(encoding="utf-8")
    compressed_lines = (tmp_path / "compressed_transmutation_bank.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert report["teacher_call_status"] == "completed"
    assert report["teacher_parse_mode"] == "json_recovered"
    assert report["compressed_transmutation_count"] == 1
    assert report["ledger_summary"]["entry_count"] == 1
    assert teacher.calls[0]["num_ctx"] == 8192
    assert set(artifacts) == {
        "report_json",
        "report_markdown",
        "micro_fortress_json",
        "constraints_jsonl",
        "compressed_bank_jsonl",
        "ledger_json",
        "architecture_json",
    }
    assert loaded["compressed_transmutation_count"] == 1
    assert len(compressed_lines) == 1
    assert "# Agency Automation Meta-Fortress" in markdown


def test_run_agency_automation_captures_teacher_reasoning_metadata():
    teacher = _FakeReasoningTeacher()

    report = run_agency_automation(
        prompt="Doordash me two large cheese pizzas from Dominos and stop before payment.",
        observation="DoorDash item modal shows Large Cheese Pizza and Add to cart.",
        teacher_model="deepseek-ai/deepseek-v4-flash",
        teacher_client=teacher,
        teacher_max_tokens=2048,
        teacher_reasoning_effort="high",
    )

    assert report["teacher_provider"] == "nvidia"
    assert report["teacher_call_status"] == "completed"
    assert report["raw_teacher_reasoning_content"] == "teacher inspected missing quantity evidence"
    assert report["teacher_usage"]["total_tokens"] == 150
    assert report["teacher_request_metadata"]["reasoning_effort"] == "high"
    assert report["teacher_request_metadata"]["max_tokens"] == 2048


def test_agency_automation_cli_dry_run_skips_client(monkeypatch, tmp_path, capsys):
    def fail_client(*args, **kwargs):
        raise AssertionError("dry-run should not build a teacher client")

    monkeypatch.setattr(cli, "_build_agency_teacher_client", fail_client)

    exit_code = cli.main(
        [
            "agency",
            "automate",
            "--dry-run",
            "--out-dir",
            str(tmp_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["teacher_call_status"] == "skipped_dry_run"
    assert payload["constraint_count"] >= 3
    assert (tmp_path / "micro_fortress_plan.json").exists()


def test_agency_automation_cli_uses_single_api_key_path(monkeypatch, tmp_path, capsys):
    captured: dict[str, object] = {}

    def fake_run(**kwargs):
        captured["teacher_client"] = kwargs["teacher_client"]
        return {
            "automation_id": AGENCY_AUTOMATION_ID,
            "teacher_model": kwargs["teacher_model"],
            "teacher_call_status": "completed",
            "constraint_count": 1,
            "ungrounded_constraint_count": 1,
            "confusion": {"uncertainty_type": "ungrounded_numeric_constraint"},
            "micro_fortress": {
                "micro_fortress_id": "micro_cli",
                "teacher_prompt_budget": {"estimated_teacher_input_tokens": 100},
            },
            "compressed_transmutation_count": 1,
            "ledger_summary": {"entry_count": 1, "rule_count": 1, "negative_transfer_count": 0},
            "failure_count": 0,
            "constraints": [],
            "compressed_transmutations": [],
            "ledger": {"entries": []},
        }

    monkeypatch.setattr(cli, "run_agency_automation", fake_run)

    exit_code = cli.main(
        [
            "agency",
            "automate",
            "--api-key",
            "test-key",
            "--out-dir",
            str(tmp_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    client = captured["teacher_client"]

    assert exit_code == 0
    assert getattr(client, "provider") == "gemini"
    assert getattr(client, "api_key") == "test-key"
    assert payload["teacher_call_status"] == "completed"
    assert payload["compressed_transmutation_count"] == 1


def test_agency_automation_cli_builds_nvidia_teacher_from_env(monkeypatch, tmp_path, capsys):
    captured: dict[str, object] = {}

    def fake_run(**kwargs):
        captured["teacher_client"] = kwargs["teacher_client"]
        captured["teacher_reasoning_effort"] = kwargs["teacher_reasoning_effort"]
        captured["teacher_max_tokens"] = kwargs["teacher_max_tokens"]
        return {
            "automation_id": AGENCY_AUTOMATION_ID,
            "teacher_model": kwargs["teacher_model"],
            "teacher_provider": "nvidia",
            "teacher_call_status": "completed",
            "teacher_reasoning_effort": kwargs["teacher_reasoning_effort"],
            "teacher_max_tokens": kwargs["teacher_max_tokens"],
            "constraint_count": 1,
            "ungrounded_constraint_count": 1,
            "confusion": {"uncertainty_type": "ungrounded_numeric_constraint"},
            "micro_fortress": {
                "micro_fortress_id": "micro_cli",
                "teacher_prompt_budget": {"estimated_teacher_input_tokens": 100},
            },
            "compressed_transmutation_count": 1,
            "ledger_summary": {"entry_count": 1, "rule_count": 1, "negative_transfer_count": 0},
            "failure_count": 0,
            "constraints": [],
            "compressed_transmutations": [],
            "ledger": {"entries": []},
        }

    monkeypatch.setattr(cli, "run_agency_automation", fake_run)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")

    exit_code = cli.main(
        [
            "agency",
            "automate",
            "--teacher-provider",
            "nvidia",
            "--teacher-base-url",
            "https://integrate.api.nvidia.com/v1",
            "--teacher-model",
            "deepseek-ai/deepseek-v4-flash",
            "--teacher-reasoning-effort",
            "high",
            "--teacher-max-tokens",
            "2048",
            "--out-dir",
            str(tmp_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    client = captured["teacher_client"]

    assert exit_code == 0
    assert getattr(client, "provider") == "nvidia"
    assert getattr(client, "base_url") == "https://integrate.api.nvidia.com"
    assert getattr(client, "api_key") == "nvapi-test"
    assert captured["teacher_reasoning_effort"] == "high"
    assert captured["teacher_max_tokens"] == 2048
    assert payload["teacher_provider"] == "nvidia"


def test_agency_nvidia_smoke_is_dry_by_default(monkeypatch, capsys):
    def fail_run(**kwargs):
        raise AssertionError("nvidia-smoke without --live must not call a model")

    monkeypatch.setattr(cli, "run_agency_automation", fail_run)

    exit_code = cli.main(["agency", "nvidia-smoke", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["live"] is False
    assert payload["teacher_provider"] == "nvidia"
    assert payload["status"] == "ready_dry_run_no_model_called"
