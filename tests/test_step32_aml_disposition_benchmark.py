from __future__ import annotations

import json
from pathlib import Path

from memory_system.cli import main
from memory_system.distillation.aml_disposition_benchmark import (
    AmlDecision,
    backtest_aml_decision,
    evaluate_aml_alert_rules,
    load_aml_disposition_cases,
    render_aml_disposition_markdown,
    run_aml_disposition_benchmark,
)


def _load_case(tmp_path: Path, payload: dict) -> object:
    cases_path = tmp_path / "aml_cases.jsonl"
    cases_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return load_aml_disposition_cases(str(cases_path))[0]


def test_evaluate_aml_alert_rules_detects_fuzzy_sanctions_false_positive_signals(tmp_path):
    case = _load_case(
        tmp_path,
        {
            "case_id": "fuzzy_case",
            "prompt": "Fuzzy sanctions match with jurisdiction and entity-type differences.",
            "alert": {"alert_id": "AL-1", "alert_type": "sanctions_screening"},
            "customer": {"legal_name": "Atlas Trading LLC", "jurisdiction": "US-IL", "entity_type": "LLC"},
            "screening_hits": [
                {
                    "hit_type": "sanctions",
                    "matched_name": "Atlas Trading",
                    "match_score": 0.71,
                    "listed_jurisdiction": "TR",
                    "entity_type": "sole_proprietorship",
                }
            ],
            "evidence": {"identity_verified": True, "ubo_documented": True, "adverse_media": []},
            "controls": {"auto_clear_threshold": 0.85, "high_risk_jurisdictions": ["IR"]},
            "expected_outcome": "clear",
            "expected_rule_hits": [],
            "expected_actions": [],
            "expected_evidence_updates": {},
        },
    )
    hits = evaluate_aml_alert_rules(case)
    rule_ids = {hit.rule_id for hit in hits}
    assert "fuzzy_name_only" in rule_ids
    assert "jurisdiction_mismatch" in rule_ids
    assert "entity_type_mismatch" in rule_ids


def test_backtest_aml_decision_allows_clear_for_explainable_soft_hits(tmp_path):
    case = _load_case(
        tmp_path,
        {
            "case_id": "clear_case",
            "prompt": "Clear the fuzzy sanctions false positive.",
            "alert": {"alert_id": "AL-2", "alert_type": "sanctions_screening"},
            "customer": {"legal_name": "Atlas Trading LLC", "jurisdiction": "US-IL", "entity_type": "LLC"},
            "screening_hits": [
                {
                    "hit_type": "sanctions",
                    "matched_name": "Atlas Trading",
                    "match_score": 0.71,
                    "listed_jurisdiction": "TR",
                    "entity_type": "sole_proprietorship",
                }
            ],
            "evidence": {"identity_verified": True, "ubo_documented": True, "adverse_media": []},
            "controls": {"auto_clear_threshold": 0.85, "high_risk_jurisdictions": ["IR"]},
            "expected_outcome": "clear",
            "expected_rule_hits": [],
            "expected_actions": [],
            "expected_evidence_updates": {},
        },
    )
    decision = AmlDecision(
        decision="clear",
        predicted_rule_hits=["fuzzy_name_only"],
        next_actions=["document_entity_difference"],
        evidence_updates={},
        audit_narrative="Different jurisdiction and entity type support clearing.",
        rationale="False positive.",
        response_text="",
        parse_mode="json",
    )
    result = backtest_aml_decision(case, decision)
    assert result.compliance_passed is True
    assert result.final_status == "clear_ok"


def test_backtest_aml_decision_blocks_unsafe_clear_on_hard_hit(tmp_path):
    case = _load_case(
        tmp_path,
        {
            "case_id": "hard_hit_case",
            "prompt": "Exact sanctions match must not be cleared.",
            "alert": {"alert_id": "AL-3", "alert_type": "sanctions_screening"},
            "customer": {"legal_name": "North Sea Trading Ltd", "jurisdiction": "GB", "entity_type": "corporation"},
            "screening_hits": [
                {
                    "hit_type": "sanctions",
                    "matched_name": "North Sea Trading Ltd",
                    "match_score": 0.97,
                    "listed_jurisdiction": "GB",
                    "entity_type": "corporation",
                    "exact_match": True,
                }
            ],
            "evidence": {"identity_verified": True, "ubo_documented": True, "adverse_media": []},
            "controls": {"auto_clear_threshold": 0.85, "high_risk_jurisdictions": ["IR"]},
            "expected_outcome": "reject",
            "expected_rule_hits": [],
            "expected_actions": [],
            "expected_evidence_updates": {},
        },
    )
    decision = AmlDecision(
        decision="clear",
        predicted_rule_hits=["exact_sanctions_match"],
        next_actions=[],
        evidence_updates={},
        audit_narrative="Attempted unsafe clear.",
        rationale="Bad call.",
        response_text="",
        parse_mode="json",
    )
    result = backtest_aml_decision(case, decision)
    assert result.compliance_passed is False
    assert result.final_status == "unsafe_clear_with_hard_hit"


def test_backtest_aml_decision_request_docs_closes_identity_gap(tmp_path):
    case = _load_case(
        tmp_path,
        {
            "case_id": "docs_case",
            "prompt": "Request identity documents before disposition.",
            "alert": {"alert_id": "AL-4", "alert_type": "sanctions_screening"},
            "customer": {"legal_name": "Blue Harbor Imports LLC", "jurisdiction": "US-FL", "entity_type": "LLC"},
            "screening_hits": [
                {
                    "hit_type": "sanctions",
                    "matched_name": "Blue Harbor Imports",
                    "match_score": 0.61,
                    "listed_jurisdiction": "US",
                    "entity_type": "LLC",
                }
            ],
            "evidence": {"identity_verified": False, "ubo_documented": True, "adverse_media": []},
            "controls": {"auto_clear_threshold": 0.85, "high_risk_jurisdictions": ["IR"]},
            "expected_outcome": "request_docs",
            "expected_rule_hits": [],
            "expected_actions": [],
            "expected_evidence_updates": {"identity_verified": True},
        },
    )
    decision = AmlDecision(
        decision="request_docs",
        predicted_rule_hits=["identity_document_gap"],
        next_actions=["request_identity_documents"],
        evidence_updates={"identity_verified": True},
        audit_narrative="Hold until identity is verified.",
        rationale="Missing ID docs.",
        response_text="",
        parse_mode="json",
    )
    result = backtest_aml_decision(case, decision)
    assert result.compliance_passed is True
    assert result.final_status == "request_docs_ok"


def test_run_aml_disposition_benchmark_repairs_unsafe_clear(monkeypatch, tmp_path):
    cases_path = tmp_path / "aml_cases.jsonl"
    cases_path.write_text(
        json.dumps(
            {
                "case_id": "repair_clear_case",
                "prompt": "Clear the fuzzy sanctions false positive with supporting evidence.",
                "alert": {"alert_id": "AL-5", "alert_type": "sanctions_screening"},
                "customer": {"legal_name": "Atlas Trading LLC", "jurisdiction": "US-IL", "entity_type": "LLC"},
                "screening_hits": [
                    {
                        "hit_type": "sanctions",
                        "matched_name": "Atlas Trading",
                        "match_score": 0.71,
                        "listed_jurisdiction": "TR",
                        "entity_type": "sole_proprietorship",
                    }
                ],
                "evidence": {"identity_verified": True, "ubo_documented": True, "adverse_media": []},
                "controls": {"auto_clear_threshold": 0.85, "high_risk_jurisdictions": ["IR"]},
                "expected_outcome": "clear",
                "expected_rule_hits": ["fuzzy_name_only"],
                "expected_actions": ["document_entity_difference"],
                "expected_evidence_updates": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    class DummyClient:
        def __init__(self, provider: str):
            self.provider = provider
            self.calls = 0

        def chat(self, **kwargs):
            self.calls += 1
            if self.provider == "github_models":
                return json.dumps(
                    {
                        "decision": "reject",
                        "predicted_rule_hits": ["fuzzy_name_only"],
                        "next_actions": ["block_relationship"],
                        "evidence_updates": {},
                        "audit_narrative": "Reject without review.",
                        "rationale": "Too aggressive.",
                    }
                )
            if self.calls == 1:
                return json.dumps(
                    {
                        "decision": "reject",
                        "predicted_rule_hits": ["fuzzy_name_only"],
                        "next_actions": ["block_relationship"],
                        "evidence_updates": {},
                        "audit_narrative": "Reject without review.",
                        "rationale": "Too aggressive.",
                    }
                )
            return json.dumps(
                {
                    "decision": "clear",
                    "predicted_rule_hits": ["fuzzy_name_only", "jurisdiction_mismatch", "entity_type_mismatch"],
                    "next_actions": ["document_entity_difference"],
                    "evidence_updates": {},
                    "audit_narrative": "Different jurisdiction and entity type support clearing.",
                    "rationale": "False positive.",
                }
            )

    monkeypatch.setattr(
        "memory_system.distillation.aml_disposition_benchmark._build_llm_client",
        lambda provider=None, base_url=None, api_key=None: DummyClient(provider or "ollama"),
    )

    report = run_aml_disposition_benchmark(
        cases_path=str(cases_path),
        raw_model="grok-3",
        memla_model="qwen3.5:9b",
        raw_provider="github_models",
        memla_provider="ollama",
    )

    assert report["cases"] == 1
    assert report["avg_memla_backtest_passed"] > report["avg_raw_backtest_passed"]
    assert report["avg_memla_aml_utility"] > report["avg_raw_aml_utility"]
    row = report["rows"][0]
    assert row["raw_decision"] == "reject"
    assert row["memla_decision"] == "clear"
    assert len(row["memla_iteration_trace"]) == 2

    md = render_aml_disposition_markdown(report)
    assert "# AML Alert Disposition Benchmark" in md
    assert "AML utility" in md


def test_memla_aml_disposition_benchmark_writes_report_bundle(monkeypatch, capsys, tmp_path):
    def _fake_aml_benchmark(**kwargs):
        return {
            "avg_raw_aml_utility": 0.25,
            "avg_memla_aml_utility": 0.82,
            "memla_vs_raw_aml_utility_index": 3.28,
            "rows": [],
        }

    monkeypatch.setattr(
        "memory_system.cli.run_aml_disposition_benchmark",
        _fake_aml_benchmark,
    )
    monkeypatch.setattr(
        "memory_system.cli.render_aml_disposition_markdown",
        lambda report: "# AML Alert Disposition Benchmark\n",
    )

    out_dir = tmp_path / "aml_report"
    rc = main(
        [
            "aml",
            "benchmark-disposition",
            "--cases",
            "cases/aml_alert_public_eval_cases.jsonl",
            "--raw-model",
            "Meta-Llama-3.1-405B-Instruct",
            "--memla-model",
            "qwen3.5:9b",
            "--out-dir",
            str(out_dir),
        ]
    )

    assert rc == 0
    assert (out_dir / "aml_disposition_benchmark_report.json").exists()
    assert (out_dir / "aml_disposition_benchmark_report.md").exists()
    out = capsys.readouterr().out
    assert "Wrote AML benchmark JSON" in out
    assert "memla utility 0.82" in out


def test_backtest_aml_decision_blocks_clear_on_unverified_evidence_extraction(tmp_path):
    case = _load_case(
        tmp_path,
        {
            "case_id": "unverified_evidence_case",
            "prompt": "Fuzzy sanctions false positive, but identity flag came from NLP extraction only.",
            "alert": {"alert_id": "AL-X", "alert_type": "sanctions_screening"},
            "customer": {"legal_name": "Atlas Trading LLC", "jurisdiction": "US-IL", "entity_type": "LLC"},
            "screening_hits": [
                {
                    "hit_type": "sanctions",
                    "matched_name": "Atlas Trading",
                    "match_score": 0.71,
                    "listed_jurisdiction": "TR",
                    "entity_type": "sole_proprietorship",
                }
            ],
            "evidence": {
                "identity_verified": True,
                "ubo_documented": True,
                "adverse_media": [],
                "provenance": {
                    "identity_verified": {"source": "nlp_extracted", "confidence": 0.82, "citation": "legacy note parse"}
                },
            },
            "controls": {"auto_clear_threshold": 0.85, "high_risk_jurisdictions": ["IR"]},
            "expected_outcome": "escalate",
            "expected_rule_hits": [],
            "expected_actions": [],
            "expected_evidence_updates": {},
        },
    )
    decision = AmlDecision(
        decision="clear",
        predicted_rule_hits=["fuzzy_name_only"],
        next_actions=["document_entity_difference"],
        evidence_updates={},
        audit_narrative="Attempted clear on unverified evidence.",
        rationale="Bad call.",
        response_text="",
        parse_mode="json",
    )
    result = backtest_aml_decision(case, decision)
    assert result.compliance_passed is False
    assert result.final_status == "clear_insufficient_for_soft_hit"


def test_public_aml_case_pack_loads_ten_cases():
    cases = load_aml_disposition_cases("cases/aml_alert_public_eval_cases.jsonl")
    assert len(cases) == 10
    outcomes = {case.expected_outcome for case in cases}
    assert outcomes == {"clear", "reject", "escalate", "request_docs"}
