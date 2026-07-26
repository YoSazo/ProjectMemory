from __future__ import annotations

import json
import tempfile
from pathlib import Path

from memory_system.distillation.aml_disposition_benchmark import (
    evaluate_aml_alert_rules,
    load_aml_disposition_cases,
)
from memory_system.distillation.amlsim_case_converter import (
    convert_amlsim_archive_to_cases,
    write_amlsim_cases_jsonl,
)

ARCHIVE_PATH = "archive.zip.gz"


def _load_inline_case(payload: dict):
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as handle:
        handle.write(json.dumps(payload) + "\n")
        path = Path(handle.name)
    try:
        return load_aml_disposition_cases(str(path))[0]
    finally:
        path.unlink(missing_ok=True)


def test_convert_amlsim_archive_produces_reject_and_clear_cases():
    cases = convert_amlsim_archive_to_cases(ARCHIVE_PATH, max_cases=40, reject_ratio=0.5, seed=7)
    assert len(cases) == 40
    outcomes = {case["expected_outcome"] for case in cases}
    assert outcomes == {"reject", "clear"}
    reject_cases = [case for case in cases if case["expected_outcome"] == "reject"]
    clear_cases = [case for case in cases if case["expected_outcome"] == "clear"]
    assert len(reject_cases) == 20
    assert len(clear_cases) == 20
    assert all(case["screening_hits"][0].get("exact_match") for case in reject_cases)
    assert all(not case["screening_hits"][0].get("exact_match") for case in clear_cases)


def test_converted_cases_align_with_rule_engine():
    cases = convert_amlsim_archive_to_cases(ARCHIVE_PATH, max_cases=12, reject_ratio=0.5, seed=3)
    for payload in cases:
        loaded = _load_inline_case(payload)
        rule_ids = {hit.rule_id for hit in evaluate_aml_alert_rules(loaded)}
        assert set(payload["expected_rule_hits"]) == rule_ids
        if payload["expected_outcome"] == "reject":
            assert "exact_sanctions_match" in rule_ids
        if payload["expected_outcome"] == "clear":
            assert "fuzzy_name_only" in rule_ids


def test_write_amlsim_cases_jsonl(tmp_path):
    output_path = tmp_path / "amlsim_cases.jsonl"
    summary = write_amlsim_cases_jsonl(
        ARCHIVE_PATH,
        output_path,
        max_cases=8,
        reject_ratio=0.5,
        seed=1,
    )
    assert summary["total"] == 8
    assert summary["reject"] == 4
    assert summary["clear"] == 4
    loaded = load_aml_disposition_cases(str(output_path))
    assert len(loaded) == 8
