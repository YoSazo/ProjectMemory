"""Convert IBM AMLSim CSV exports into Memla AML disposition benchmark cases."""

from __future__ import annotations

import csv
import gzip
import io
import json
import random
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from memory_system.distillation.aml_disposition_benchmark import (
    AmlDispositionCase,
    evaluate_aml_alert_rules,
    load_aml_disposition_cases,
)

# Public OFAC SDN-style names (government-published sanctions list entries).
OFAC_SDN_PROFILES: tuple[dict[str, str], ...] = (
    {"name": "Rosneft Oil Company", "jurisdiction": "RU", "entity_type": "corporation"},
    {"name": "Gazprombank Joint Stock Company", "jurisdiction": "RU", "entity_type": "corporation"},
    {"name": "Islamic Revolutionary Guard Corps", "jurisdiction": "IR", "entity_type": "corporation"},
    {"name": "Bank Melli Iran", "jurisdiction": "IR", "entity_type": "corporation"},
    {"name": "Hizballah", "jurisdiction": "LB", "entity_type": "corporation"},
    {"name": "Wagner Group", "jurisdiction": "RU", "entity_type": "corporation"},
    {"name": "North Korea Mining Development Trading Corporation", "jurisdiction": "KP", "entity_type": "corporation"},
    {"name": "Syrian Petroleum Company", "jurisdiction": "SY", "entity_type": "corporation"},
    {"name": "Viktor Bout", "jurisdiction": "RU", "entity_type": "individual"},
    {"name": "Semion Mogilevich", "jurisdiction": "RU", "entity_type": "individual"},
    {"name": "Dandong Hongxiang Industrial Development Company Limited", "jurisdiction": "CN", "entity_type": "corporation"},
    {"name": "Petroleos de Venezuela SA", "jurisdiction": "VE", "entity_type": "corporation"},
    {"name": "Al-Qaida Organization", "jurisdiction": "AF", "entity_type": "corporation"},
    {"name": "Taliban", "jurisdiction": "AF", "entity_type": "corporation"},
    {"name": "Lazarus Group", "jurisdiction": "KP", "entity_type": "corporation"},
    {"name": "Korea Mining Development Trading Corporation", "jurisdiction": "KP", "entity_type": "corporation"},
    {"name": "Central Bank of Iran", "jurisdiction": "IR", "entity_type": "corporation"},
    {"name": "Sberbank of Russia", "jurisdiction": "RU", "entity_type": "corporation"},
    {"name": "VTB Bank Public Joint Stock Company", "jurisdiction": "RU", "entity_type": "corporation"},
    {"name": "Nicolas Maduro Moros", "jurisdiction": "VE", "entity_type": "individual"},
)

DEFAULT_CONTROLS: dict[str, Any] = {
    "auto_clear_threshold": 0.85,
    "high_risk_jurisdictions": ["IR", "KP", "SY"],
}

AMLSIM_CITATION = (
    "Synthetic sanctions-screening dress-up of IBM AMLSim alert/account exports "
    "(Toyotaro Suzumura and Hiroki Kanezashi, AMLSim, 2021)."
)


@dataclass(frozen=True)
class AmlSimTables:
    accounts: dict[str, dict[str, str]]
    alerts: list[dict[str, str]]
    alert_account_ids: frozenset[str]
    account_alert_types: dict[str, str]


def _read_csv_rows(zip_file: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    with zip_file.open(member) as handle:
        return list(csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8")))


def load_amlsim_tables(archive_path: str | Path) -> AmlSimTables:
    path = Path(archive_path)
    if not path.exists():
        raise FileNotFoundError(f"AMLSim archive not found: {path}")

    if path.suffix == ".gz" or path.name.endswith(".zip.gz"):
        with gzip.open(path, "rb") as handle:
            payload = handle.read()
    else:
        payload = path.read_bytes()

    with zipfile.ZipFile(io.BytesIO(payload)) as zip_file:
        account_rows = _read_csv_rows(zip_file, "accounts.csv")
        alert_rows = _read_csv_rows(zip_file, "alerts.csv")

    accounts = {row["ACCOUNT_ID"]: row for row in account_rows}
    alert_account_ids: set[str] = set()
    account_alert_types: dict[str, str] = {}
    for alert in alert_rows:
        for field in ("SENDER_ACCOUNT_ID", "RECEIVER_ACCOUNT_ID"):
            account_id = str(alert.get(field) or "").strip()
            if not account_id:
                continue
            alert_account_ids.add(account_id)
            account_alert_types.setdefault(account_id, str(alert.get("ALERT_TYPE") or "tm_alert"))
    return AmlSimTables(
        accounts=accounts,
        alerts=alert_rows,
        alert_account_ids=frozenset(alert_account_ids),
        account_alert_types=account_alert_types,
    )


def _account_entity_type(account_type: str) -> str:
    token = str(account_type or "").strip().upper()
    if token == "I":
        return "individual"
    if token in {"C", "B"}:
        return "corporation"
    return "LLC"


def _account_jurisdiction(country: str, account_id: str) -> str:
    country_code = str(country or "US").strip().upper() or "US"
    if country_code != "US":
        return country_code
    # AMLSim is US-only; spread states deterministically for variety.
    state_codes = (
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    )
    return f"US-{state_codes[int(account_id) % len(state_codes)]}"


def _pick_sdn_profile(seed: int) -> dict[str, str]:
    return dict(OFAC_SDN_PROFILES[seed % len(OFAC_SDN_PROFILES)])


def _misspell_name(name: str, seed: int) -> str:
    clean = " ".join(str(name or "").split())
    if not clean:
        return "Unknown Trading LLC"
    rng = random.Random(seed)
    words = clean.split()
    target_idx = seed % len(words)
    word = words[target_idx]
    variants = []
    if len(word) > 4:
        idx = 1 + (seed % (len(word) - 2))
        variants.append(word[:idx] + word[idx + 1 :] + word[idx])
    if word.endswith("y"):
        variants.append(word[:-1] + "ie")
    if "o" in word.lower():
        variants.append(re.sub("o", "a", word, count=1, flags=re.IGNORECASE))
    variants.append(word + "s")
    variants.append(word[:-1] if len(word) > 3 else word + "x")
    mutated = rng.choice(variants or [word + "x"])
    words[target_idx] = mutated
    suffix = " LLC" if "LLC" not in clean.upper() else ""
    return " ".join(words) + suffix


def _expected_actions_for_outcome(outcome: str, rule_ids: list[str]) -> list[str]:
    if outcome == "reject":
        return ["block_relationship"]
    if outcome == "escalate":
        actions = ["route_to_l2_review"]
        if "adverse_media_confirmed" in rule_ids:
            actions.insert(0, "request_sar_precheck")
        return actions
    if outcome == "request_docs":
        actions = ["hold_pending_documents"]
        if "identity_document_gap" in rule_ids:
            actions.insert(0, "request_identity_documents")
        if "ubo_ownership_unclear" in rule_ids:
            actions.insert(0, "request_ubo_documentation")
        return actions
    if outcome == "clear" and "fuzzy_name_only" in rule_ids:
        return ["document_entity_difference"]
    return []


def _case_from_payload(payload: dict[str, Any]) -> AmlDispositionCase:
    return load_aml_disposition_cases_from_rows([payload])[0]


def load_aml_disposition_cases_from_rows(rows: list[dict[str, Any]]) -> list[AmlDispositionCase]:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        temp_path = Path(handle.name)
    try:
        return load_aml_disposition_cases(str(temp_path))
    finally:
        temp_path.unlink(missing_ok=True)


def _finalize_case(payload: dict[str, Any]) -> dict[str, Any]:
    case = _case_from_payload(payload)
    rule_ids = [hit.rule_id for hit in evaluate_aml_alert_rules(case)]
    outcome = str(payload.get("expected_outcome") or "").strip().lower()
    payload["expected_rule_hits"] = rule_ids
    payload["expected_actions"] = _expected_actions_for_outcome(outcome, rule_ids)
    payload.setdefault("expected_evidence_updates", {})
    payload.setdefault("source_basis", [AMLSIM_CITATION, "OFAC SDN public list name-matching patterns"])
    return payload


def _build_reject_case(
    *,
    account_id: str,
    account: dict[str, str],
    alert_type: str,
    alert_id: str,
    seed: int,
) -> dict[str, Any]:
    profile = _pick_sdn_profile(seed)
    legal_name = profile["name"]
    jurisdiction = _account_jurisdiction(account.get("COUNTRY", "US"), account_id)
    entity_type = _account_entity_type(account.get("ACCOUNT_TYPE", "I"))
    listed_jurisdiction = jurisdiction.split("-")[0] if jurisdiction.startswith("US-") else jurisdiction
    return {
        "case_id": f"amlsim_reject_{account_id}",
        "prompt": (
            "Corporate onboarding alert derived from an AMLSim transaction-monitoring flag. "
            "The customer name exactly matches a listed OFAC SDN record in the same jurisdiction profile. "
            "Choose the bounded disposition that preserves control."
        ),
        "alert": {
            "alert_id": f"AL-AMLSIM-{alert_id}",
            "alert_type": "sanctions_screening",
            "match_score": 0.97,
            "matched_entity": legal_name,
            "list_source": "OFAC_SDN",
            "amlsim_alert_type": alert_type,
        },
        "customer": {
            "legal_name": legal_name,
            "jurisdiction": jurisdiction,
            "entity_type": entity_type,
            "tax_id_verified": True,
            "amlsim_account_id": account_id,
            "amlsim_customer_id": account.get("CUSTOMER_ID", ""),
            "amlsim_is_fraud": account.get("IS_FRAUD", ""),
        },
        "screening_hits": [
            {
                "hit_type": "sanctions",
                "matched_name": legal_name,
                "match_score": 0.97,
                "list_source": "OFAC_SDN",
                "listed_jurisdiction": listed_jurisdiction,
                "entity_type": entity_type,
                "exact_match": True,
            }
        ],
        "evidence": {
            "identity_verified": True,
            "address_match": True,
            "ubo_documented": True,
            "adverse_media": [],
        },
        "controls": dict(DEFAULT_CONTROLS),
        "expected_outcome": "reject",
        "expected_rule_hits": [],
        "expected_actions": [],
        "expected_evidence_updates": {},
    }


def _build_clear_case(
    *,
    account_id: str,
    account: dict[str, str],
    seed: int,
) -> dict[str, Any]:
    profile = _pick_sdn_profile(seed + 17)
    listed_name = profile["name"]
    customer_name = _misspell_name(listed_name, seed)
    jurisdiction = _account_jurisdiction(account.get("COUNTRY", "US"), account_id)
    return {
        "case_id": f"amlsim_clear_{account_id}",
        "prompt": (
            "Retail onboarding alert derived from an AMLSim account that was not flagged by transaction monitoring. "
            "The screening engine returned a fuzzy OFAC-like name match with jurisdiction and entity-type differences. "
            "Identity and address are verified. Choose the safest bounded disposition."
        ),
        "alert": {
            "alert_id": f"AL-AMLSIM-CLEAR-{account_id}",
            "alert_type": "sanctions_screening",
            "match_score": 0.68,
            "matched_entity": listed_name,
            "list_source": "OFAC_SDN",
        },
        "customer": {
            "legal_name": customer_name,
            "jurisdiction": jurisdiction,
            "entity_type": "individual",
            "tax_id_verified": True,
            "amlsim_account_id": account_id,
            "amlsim_customer_id": account.get("CUSTOMER_ID", ""),
            "amlsim_is_fraud": account.get("IS_FRAUD", ""),
        },
        "screening_hits": [
            {
                "hit_type": "sanctions",
                "matched_name": listed_name,
                "match_score": 0.68,
                "list_source": "OFAC_SDN",
                "listed_jurisdiction": profile["jurisdiction"],
                "entity_type": profile["entity_type"],
            }
        ],
        "evidence": {
            "identity_verified": True,
            "address_match": True,
            "ubo_documented": True,
            "adverse_media": [],
        },
        "controls": dict(DEFAULT_CONTROLS),
        "expected_outcome": "clear",
        "expected_rule_hits": [],
        "expected_actions": [],
        "expected_evidence_updates": {},
    }


def _iter_candidate_accounts(tables: AmlSimTables) -> tuple[list[str], list[str]]:
    reject_ids = sorted(tables.alert_account_ids, key=lambda value: int(value))
    clear_ids = sorted(
        (
            account_id
            for account_id, account in tables.accounts.items()
            if account_id not in tables.alert_account_ids and account.get("IS_FRAUD", "").lower() == "false"
        ),
        key=lambda value: int(value),
    )
    return reject_ids, clear_ids


def convert_amlsim_archive_to_cases(
    archive_path: str | Path,
    *,
    max_cases: int | None = 500,
    reject_ratio: float = 0.5,
    seed: int = 0,
) -> list[dict[str, Any]]:
    tables = load_amlsim_tables(archive_path)
    reject_ids, clear_ids = _iter_candidate_accounts(tables)
    rng = random.Random(seed)

    if max_cases is None or max_cases <= 0:
        selected_reject = reject_ids
        selected_clear = clear_ids
    else:
        reject_count = min(len(reject_ids), max(1, int(round(max_cases * reject_ratio))))
        clear_count = min(len(clear_ids), max(0, max_cases - reject_count))
        selected_reject = reject_ids[:reject_count]
        if clear_count < (max_cases - reject_count):
            reject_count = min(len(reject_ids), max_cases - clear_count)
            selected_reject = reject_ids[:reject_count]
        rng.shuffle(clear_ids)
        selected_clear = clear_ids[:clear_count]

    alert_lookup: dict[str, str] = {}
    for alert in tables.alerts:
        for field in ("SENDER_ACCOUNT_ID", "RECEIVER_ACCOUNT_ID"):
            account_id = str(alert.get(field) or "").strip()
            if account_id and account_id not in alert_lookup:
                alert_lookup[account_id] = str(alert.get("ALERT_ID") or "0")

    cases: list[dict[str, Any]] = []
    for index, account_id in enumerate(selected_reject):
        account = tables.accounts[account_id]
        payload = _build_reject_case(
            account_id=account_id,
            account=account,
            alert_type=tables.account_alert_types.get(account_id, "tm_alert"),
            alert_id=alert_lookup.get(account_id, str(index)),
            seed=seed + int(account_id),
        )
        cases.append(_finalize_case(payload))

    for index, account_id in enumerate(selected_clear):
        account = tables.accounts[account_id]
        payload = _build_clear_case(
            account_id=account_id,
            account=account,
            seed=seed + int(account_id) + index * 31,
        )
        cases.append(_finalize_case(payload))

    return cases


def write_amlsim_cases_jsonl(
    archive_path: str | Path,
    output_path: str | Path,
    *,
    max_cases: int | None = 500,
    reject_ratio: float = 0.5,
    seed: int = 0,
) -> dict[str, int]:
    cases = convert_amlsim_archive_to_cases(
        archive_path,
        max_cases=max_cases,
        reject_ratio=reject_ratio,
        seed=seed,
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, sort_keys=True) + "\n")

    outcome_counts: dict[str, int] = {}
    for case in cases:
        outcome = str(case.get("expected_outcome") or "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    return {"total": len(cases), **outcome_counts}


def iter_amlsim_cases_from_archive(
    archive_path: str | Path,
    *,
    max_cases: int | None = 500,
    reject_ratio: float = 0.5,
    seed: int = 0,
) -> Iterator[dict[str, Any]]:
    yield from convert_amlsim_archive_to_cases(
        archive_path,
        max_cases=max_cases,
        reject_ratio=reject_ratio,
        seed=seed,
    )
