from __future__ import annotations

import json

from memory_system import cli
from memory_system.fortresses.coding_fortress import (
    META_TRANSFER,
    MUTATION_CROSS_DOMAIN,
    RETRIEVAL_GROUNDING,
)
from memory_system.fortresses.gpt_seed_bank import (
    GPT_SEED_BANK_ID,
    build_gpt_seed_extraction_report,
    build_gpt_seed_trace,
)
from memory_system.fortresses.runner import (
    build_trace_messages,
    default_coding_fortress_cases,
    run_coding_fortress_benchmark,
    run_coding_fortress_extraction,
    run_model_trace,
    summarize_coding_fortress_cases,
    write_coding_fortress_artifacts,
    write_coding_fortress_extraction_artifacts,
)


class _FakeFortressClient:
    def __init__(self, *, label: str, wrap_json: bool = False) -> None:
        self.label = label
        self.wrap_json = wrap_json
        self.calls: list[dict[str, object]] = []

    def chat(self, *, model, messages, temperature=0.2, num_ctx=None):
        payload = json.loads(messages[-1].content)
        case = payload["case"]
        self.calls.append(
            {
                "model": model,
                "case_id": case["case_id"],
                "lane": payload["lane"],
                "temperature": temperature,
                "num_ctx": num_ctx,
            }
        )
        action_family = case.get("expected_action_family") or "constraint repair"
        expected_constraints = list(case.get("expected_constraints") or ["target constraint is satisfied"])
        expected_verifier = list(case.get("expected_verifier") or ["target verifier"])
        expected_sources = list(case.get("expected_retrieval_sources") or [])
        response = {
            "constraints_before": [
                f"{case['case_id']} has unresolved constraints",
                "current behavior violates the caller-visible contract",
            ],
            "constraints_after": expected_constraints,
            "observations": [
                "the target artifact carries the boundary",
                "the verifier names the visible contract",
            ],
            "preconditions": [
                "the expected verifier still defines correctness",
                "the boundary is shared by the failing workflow",
            ],
            "transmutation": f"Trade loose task handling for {action_family}.",
            "action_family": action_family,
            "target_artifacts": list(case.get("context", {}).get("candidate_files") or ["target/path.py"]),
            "retrieval_queries": ["official version matched docs"] if expected_sources else [],
            "retrieval_sources": expected_sources,
            "verifier": expected_verifier,
            "residual_constraints": [],
            "outcome": "success",
        }
        body = json.dumps(response)
        if self.wrap_json:
            return f"Here is the trace:\n{body}\nDone."
        return body


def test_default_coding_fortress_cases_cover_retrieval_and_cross_domain_transfer():
    cases = default_coding_fortress_cases()
    phases = {case.phase for case in cases}
    mutation_tiers = {case.mutation_tier for case in cases}
    retrieval_cases = [case for case in cases if case.phase == RETRIEVAL_GROUNDING]

    assert RETRIEVAL_GROUNDING in phases
    assert META_TRANSFER in phases
    assert MUTATION_CROSS_DOMAIN in mutation_tiers
    assert len(cases) >= 20
    assert len(retrieval_cases) >= 8
    assert any(case.case_id == "retrieval_package_source_truth_v1" for case in retrieval_cases)


def test_summarize_coding_fortress_cases_estimates_retrieval_heavy_token_footprint():
    summary = summarize_coding_fortress_cases(default_coding_fortress_cases())

    assert summary["case_count"] >= 20
    assert summary["retrieval_case_count"] >= 8
    assert summary["phase_counts"][RETRIEVAL_GROUNDING] >= 8
    assert summary["estimated_teacher_input_tokens"] > 0
    assert summary["estimated_total_tokens_two_lanes"] > summary["estimated_input_tokens_two_lanes"]
    assert "retrieval_auth_library_version_v1" in summary["retrieval_case_ids"]


def test_build_trace_messages_include_case_contract_and_schema():
    case = default_coding_fortress_cases()[0]
    messages = build_trace_messages(case, lane="teacher")
    payload = json.loads(messages[-1].content)

    assert messages[0].role == "system"
    assert payload["lane"] == "teacher"
    assert payload["case"]["case_id"] == case.case_id
    assert payload["phase_contract"]["phase"] == case.phase
    assert "transmutation" in payload["output_schema"]


def test_run_model_trace_recovers_wrapped_json_and_preserves_case_metadata():
    case = default_coding_fortress_cases()[1]
    client = _FakeFortressClient(label="teacher", wrap_json=True)

    result = run_model_trace(
        client=client,
        model="gemini-2.0-flash-lite",
        case=case,
        lane="teacher",
        temperature=0.05,
        num_ctx=8192,
    )

    assert result.parse_mode == "json_recovered"
    assert result.trace.model == "gemini-2.0-flash-lite"
    assert result.trace.phase == case.phase
    assert result.trace.metadata["case_id"] == case.case_id
    assert result.trace.metadata["lane"] == "teacher"
    assert result.residuals == []
    assert client.calls[0]["num_ctx"] == 8192


def test_run_coding_fortress_benchmark_scores_teacher_student_and_builds_ledger():
    teacher = _FakeFortressClient(label="teacher")
    student = _FakeFortressClient(label="student")

    report = run_coding_fortress_benchmark(
        cases=default_coding_fortress_cases(),
        teacher_model="gemini-2.0-flash-lite",
        student_model="qwen-7b-fortress",
        teacher_client=teacher,
        student_client=student,
        limit=4,
    )

    assert report["case_count"] == 4
    assert report["completed_case_count"] == 4
    assert report["failure_count"] == 0
    assert report["case_summary"]["case_count"] == 4
    assert report["avg_weighted_score"] >= 0.9
    assert report["ledger_summary"]["entry_count"] == 4
    assert teacher.calls[0]["lane"] == "teacher"
    assert student.calls[0]["lane"] == "student"
    assert all(row["score"]["negative_transfer"] is False for row in report["rows"])


def test_write_coding_fortress_artifacts_outputs_report_traces_and_ledger(tmp_path):
    report = run_coding_fortress_benchmark(
        cases=default_coding_fortress_cases(),
        teacher_model="gemini-2.0-flash-lite",
        student_model="qwen-7b-fortress",
        teacher_client=_FakeFortressClient(label="teacher"),
        student_client=_FakeFortressClient(label="student"),
        limit=2,
    )

    artifacts = write_coding_fortress_artifacts(report=report, out_dir=tmp_path)

    assert set(artifacts) == {
        "report_json",
        "report_markdown",
        "teacher_traces_jsonl",
        "student_traces_jsonl",
        "ledger_json",
    }
    for path in artifacts.values():
        assert path.startswith(str(tmp_path.resolve()))
    loaded_report = json.loads((tmp_path / "coding_fortress_report.json").read_text(encoding="utf-8"))
    loaded_ledger = json.loads((tmp_path / "global_transmutation_ledger.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "coding_fortress_report.md").read_text(encoding="utf-8")

    assert loaded_report["completed_case_count"] == 2
    assert loaded_report["case_summary"]["case_count"] == 2
    assert len(loaded_ledger["entries"]) == 2
    assert "# Coding Fortress Report" in markdown
    assert "Estimated total tokens" in markdown


def test_teacher_only_extraction_writes_transmutation_bank_artifacts(tmp_path):
    report = run_coding_fortress_extraction(
        cases=default_coding_fortress_cases(),
        teacher_model="gemini-2.0-flash-lite",
        teacher_client=_FakeFortressClient(label="teacher"),
        limit=3,
    )

    artifacts = write_coding_fortress_extraction_artifacts(report=report, out_dir=tmp_path)

    assert report["completed_case_count"] == 3
    assert report["case_summary"]["case_count"] == 3
    assert set(artifacts) == {"report_json", "report_markdown", "teacher_traces_jsonl"}
    loaded_report = json.loads((tmp_path / "coding_fortress_extraction_report.json").read_text(encoding="utf-8"))
    traces = (tmp_path / "teacher_traces.jsonl").read_text(encoding="utf-8").strip().splitlines()
    markdown = (tmp_path / "coding_fortress_extraction_report.md").read_text(encoding="utf-8")

    assert loaded_report["completed_case_count"] == 3
    assert len(traces) == 3
    assert "# Coding Fortress Extraction Report" in markdown


def test_gpt_seed_bank_covers_all_default_cases_with_retrieval_behavior(tmp_path):
    report = build_gpt_seed_extraction_report(cases=default_coding_fortress_cases())
    retrieval_rows = [row for row in report["rows"] if row["phase"] == RETRIEVAL_GROUNDING]

    assert report["seed_bank_id"] == GPT_SEED_BANK_ID
    assert report["completed_case_count"] == len(default_coding_fortress_cases())
    assert report["failure_count"] == 0
    assert len(retrieval_rows) >= 8
    assert all(row["teacher_parse_mode"] == "gpt_seed" for row in report["rows"])
    assert all(row["teacher_trace"]["metadata"]["observable_trace_only"] is True for row in report["rows"])
    assert all(row["teacher_trace"]["retrieval_queries"] for row in retrieval_rows)
    assert all(row["teacher_trace"]["retrieval_sources"] for row in retrieval_rows)

    artifacts = write_coding_fortress_extraction_artifacts(report=report, out_dir=tmp_path)
    traces = (tmp_path / "teacher_traces.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert set(artifacts) == {"report_json", "report_markdown", "teacher_traces_jsonl"}
    assert len(traces) == report["completed_case_count"]


def test_gpt_seed_trace_for_checkout_transfer_keeps_hard_stop_boundary():
    case = next(case for case in default_coding_fortress_cases() if case.case_id == "cross_domain_checkout_boundary_v1")

    trace = build_gpt_seed_trace(case)

    assert trace.phase == META_TRANSFER
    assert trace.mutation_tier == MUTATION_CROSS_DOMAIN
    assert "payment" in " ".join(trace.constraints_before + trace.transmutation.split()).lower()
    assert "no payment submitted" in trace.verifier


def test_coding_fortress_cli_dry_run_skips_client_construction(monkeypatch, capsys):
    def fail_build_client(*, provider="", base_url=""):
        raise AssertionError("dry-run should not construct model clients")

    monkeypatch.setattr(cli, "_build_universal_llm_client", fail_build_client)

    exit_code = cli.main(
        [
            "coding",
            "benchmark-fortress",
            "--teacher-model",
            "gemini-2.0-flash-lite",
            "--student-model",
            "qwen2.5-coder:7b",
            "--dry-run",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["case_count"] >= 20
    assert payload["retrieval_case_count"] >= 8


def test_coding_fortress_cli_gpt_seed_writes_bank_without_clients(monkeypatch, tmp_path, capsys):
    def fail_build_client(*, provider="", base_url=""):
        raise AssertionError("gpt-seed should not construct model clients")

    monkeypatch.setattr(cli, "_build_universal_llm_client", fail_build_client)

    exit_code = cli.main(
        [
            "coding",
            "benchmark-fortress",
            "--teacher-model",
            "codex-gpt5-seed",
            "--gpt-seed",
            "--out-dir",
            str(tmp_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["seed_bank_id"] == GPT_SEED_BANK_ID
    assert payload["completed_case_count"] == len(default_coding_fortress_cases())
    assert (tmp_path / "teacher_traces.jsonl").exists()


def test_coding_fortress_cli_teacher_only_skips_student_client(monkeypatch, tmp_path, capsys):
    built_clients: list[dict[str, str]] = []

    def fake_build_client(*, provider="", base_url=""):
        built_clients.append({"provider": provider, "base_url": base_url})
        return _FakeFortressClient(label=provider or "env")

    def fake_run_extraction(**kwargs):
        return {
            "teacher_model": kwargs["teacher_model"],
            "case_count": 1,
            "completed_case_count": 1,
            "failure_count": 0,
            "teacher_residual_count": 0,
            "case_summary": {"case_count": 1, "retrieval_case_count": 0},
            "rows": [],
            "failures": [],
        }

    def fake_write_extraction_artifacts(*, report, out_dir):
        return {
            "report_json": str(out_dir / "coding_fortress_extraction_report.json"),
            "report_markdown": str(out_dir / "coding_fortress_extraction_report.md"),
            "teacher_traces_jsonl": str(out_dir / "teacher_traces.jsonl"),
        }

    monkeypatch.setattr(cli, "_build_universal_llm_client", fake_build_client)
    monkeypatch.setattr(cli, "run_coding_fortress_extraction", fake_run_extraction)
    monkeypatch.setattr(cli, "write_coding_fortress_extraction_artifacts", fake_write_extraction_artifacts)

    exit_code = cli.main(
        [
            "coding",
            "benchmark-fortress",
            "--teacher-model",
            "gemini-2.0-flash-lite",
            "--teacher-provider",
            "gemini",
            "--teacher-only",
            "--out-dir",
            str(tmp_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert built_clients == [{"provider": "gemini", "base_url": ""}]
    assert payload["teacher_model"] == "gemini-2.0-flash-lite"
    assert payload["completed_case_count"] == 1


def test_coding_fortress_cli_uses_provider_flags_without_live_api(monkeypatch, tmp_path, capsys):
    built_clients: list[dict[str, str]] = []

    def fake_build_client(*, provider="", base_url=""):
        built_clients.append({"provider": provider, "base_url": base_url})
        return _FakeFortressClient(label=provider or "env")

    def fake_run_benchmark(**kwargs):
        return {
            "teacher_model": kwargs["teacher_model"],
            "student_model": kwargs["student_model"],
            "case_count": 1,
            "completed_case_count": 1,
            "failure_count": 0,
            "avg_weighted_score": 0.91,
            "negative_transfer_count": 0,
            "active_rule_count": 0,
            "ledger_summary": {"entry_count": 1},
            "promotion_decisions": [],
            "rows": [],
            "failures": [],
        }

    def fake_write_artifacts(*, report, out_dir):
        return {
            "report_json": str(out_dir / "coding_fortress_report.json"),
            "report_markdown": str(out_dir / "coding_fortress_report.md"),
            "teacher_traces_jsonl": str(out_dir / "teacher_traces.jsonl"),
            "student_traces_jsonl": str(out_dir / "student_traces.jsonl"),
            "ledger_json": str(out_dir / "global_transmutation_ledger.json"),
        }

    monkeypatch.setattr(cli, "_build_universal_llm_client", fake_build_client)
    monkeypatch.setattr(cli, "run_coding_fortress_benchmark", fake_run_benchmark)
    monkeypatch.setattr(cli, "write_coding_fortress_artifacts", fake_write_artifacts)

    exit_code = cli.main(
        [
            "coding",
            "benchmark-fortress",
            "--teacher-model",
            "gemini-2.0-flash-lite",
            "--student-model",
            "qwen2.5-coder:7b",
            "--teacher-provider",
            "gemini",
            "--student-provider",
            "ollama",
            "--out-dir",
            str(tmp_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert built_clients == [
        {"provider": "gemini", "base_url": ""},
        {"provider": "ollama", "base_url": ""},
    ]
    assert payload["teacher_model"] == "gemini-2.0-flash-lite"
    assert payload["student_model"] == "qwen2.5-coder:7b"
    assert payload["avg_weighted_score"] == 0.91
