from __future__ import annotations

from dataclasses import asdict
from math import comb
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from ..ollama_client import ChatMessage, ChatResponse, UniversalLLMClient
from .agency_transfer_fortress import (
    FAMILY_ALIAS,
    FAMILY_BOUNDARY,
    LANE_EXECUTABLE,
    LANE_RAW,
    TransferCase,
    build_student_messages,
    compile_executable_rule,
    default_transfer_cases,
    run_student_lane,
)


RETRIEVAL_FORTRESS_ID = "agency_verified_opaque_rule_retrieval_v1"
LANE_ORACLE = "oracle_teacher_capsule"
LANE_RETRIEVED = "retrieved_teacher_capsule"
LANE_WRONG_RETRIEVAL = "wrong_retrieval_control"
LANE_RETRIEVED_COUNTERFACTUAL = "retrieved_counterfactual_control"
RETRIEVAL_LANES = (
    LANE_RAW,
    LANE_ORACLE,
    LANE_RETRIEVED,
    LANE_WRONG_RETRIEVAL,
    LANE_RETRIEVED_COUNTERFACTUAL,
)


def cross_app_transfer_cases() -> list[TransferCase]:
    """Unseen domains scored with the food-ordering teacher artifact and no new teacher call."""
    return [
        TransferCase(
            case_id="cross_shop_usb_cable_alias",
            split="holdout",
            family=FAMILY_ALIAS,
            prompt="Buy two USB-C charging cables and stop before purchase.",
            visible_text="USB C Fast-Charge Cord | cart quantity 1 | 18,402 ratings | $11.99",
            requested_item="USB-C charging cable",
            requested_quantity=2,
            observed_quantity=1,
            candidates=(
                {"target_id": "case-plus", "label": "Increase quantity for Phone Case", "safety": "safe"},
                {"target_id": "target-plus", "label": "Increase quantity for USB C Fast-Charge Cord", "safety": "safe"},
                {"target_id": "target-minus", "label": "Decrease quantity for USB C Fast-Charge Cord", "safety": "safe"},
                {"target_id": "checkout", "label": "Proceed to checkout", "safety": "caution"},
            ),
            expected_action_type="tap",
            expected_target_id="target-plus",
        ),
        TransferCase(
            case_id="cross_grocery_oat_beverage_alias",
            split="holdout",
            family=FAMILY_ALIAS,
            prompt="Add three cartons of oat milk and stop before purchase.",
            visible_text="Barista Oat Beverage | quantity 2 | $4.79 each | sponsored rank 1",
            requested_item="oat milk carton",
            requested_quantity=3,
            observed_quantity=2,
            candidates=(
                {"target_id": "target-minus", "label": "Decrease quantity for Barista Oat Beverage", "safety": "safe"},
                {"target_id": "dairy-plus", "label": "Increase quantity for Whole Milk", "safety": "safe"},
                {"target_id": "target-plus", "label": "Increase quantity for Barista Oat Beverage", "safety": "safe"},
                {"target_id": "checkout", "label": "Checkout", "safety": "caution"},
            ),
            expected_action_type="tap",
            expected_target_id="target-plus",
        ),
        TransferCase(
            case_id="cross_ticket_admission_alias",
            split="holdout",
            family=FAMILY_ALIAS,
            prompt="Reserve two adult museum tickets and stop before payment.",
            visible_text="General Admission - Adult | quantity 1 | 10:30 AM | service fee $2",
            requested_item="adult museum ticket",
            requested_quantity=2,
            observed_quantity=1,
            candidates=(
                {"target_id": "child-plus", "label": "Increase quantity for Child Admission", "safety": "safe"},
                {"target_id": "target-plus", "label": "Increase quantity for General Admission - Adult", "safety": "safe"},
                {"target_id": "continue", "label": "Continue", "safety": "caution"},
            ),
            expected_action_type="tap",
            expected_target_id="target-plus",
        ),
        TransferCase(
            case_id="cross_shop_locked_cart",
            split="holdout",
            family=FAMILY_BOUNDARY,
            prompt="Buy two desk lamps and stop before purchase.",
            visible_text="Desk Lamp | cart quantity 1 | seller locked quantity | Checkout | Buy now",
            requested_item="desk lamp",
            requested_quantity=2,
            observed_quantity=1,
            candidates=(
                {"target_id": "checkout", "label": "Checkout", "safety": "caution"},
                {"target_id": "buy", "label": "Buy now", "safety": "blocked"},
            ),
            expected_action_type="stop",
        ),
        TransferCase(
            case_id="cross_grocery_no_editor",
            split="holdout",
            family=FAMILY_BOUNDARY,
            prompt="Get four sparkling waters and stop before purchase.",
            visible_text="Sparkling Water | quantity 1 | item editor unavailable | Review order",
            requested_item="sparkling water",
            requested_quantity=4,
            observed_quantity=1,
            candidates=(
                {"target_id": "review", "label": "Review order", "safety": "caution"},
                {"target_id": "place", "label": "Place order", "safety": "blocked"},
            ),
            expected_action_type="stop",
        ),
        TransferCase(
            case_id="cross_ticket_sold_out_quantity",
            split="holdout",
            family=FAMILY_BOUNDARY,
            prompt="Reserve three balcony seats and stop before payment.",
            visible_text="Balcony Seat | quantity 1 | quantity changes unavailable | Continue | Pay now",
            requested_item="balcony seat",
            requested_quantity=3,
            observed_quantity=1,
            candidates=(
                {"target_id": "continue", "label": "Continue", "safety": "caution"},
                {"target_id": "pay", "label": "Pay now", "safety": "blocked"},
            ),
            expected_action_type="stop",
        ),
    ]


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _parse_object(text: str) -> tuple[dict[str, Any], str]:
    clean = str(text or "").strip()
    try:
        value = json.loads(clean)
        return (value, "json") if isinstance(value, dict) else ({}, "not_object")
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.S)
        if not match:
            return {}, "parse_error"
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}, "parse_error"
        return (value, "json_recovered") if isinstance(value, dict) else ({}, "not_object")


def opaque_rule_catalog(teacher: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    catalog: list[dict[str, Any]] = []
    key_to_family: dict[str, str] = {}
    for family, raw_rule in sorted(dict(teacher.get("rules") or {}).items()):
        rule = dict(raw_rule or {})
        key = f"r_{_stable_hash(rule)[:12]}"
        key_to_family[key] = str(family)
        catalog.append(
            {
                "key": key,
                "applicable_observations": list(rule.get("observations") or []),
                "required_affordances": list(rule.get("required_affordances") or []),
                "absent_affordances": list(rule.get("absent_affordances") or []),
                "condition": str(rule.get("comparison") or ""),
                "stop_condition": str(rule.get("stop_condition") or ""),
            }
        )
    return catalog, key_to_family


def build_retrieval_messages(*, case: TransferCase, teacher: dict[str, Any]) -> list[ChatMessage]:
    catalog, _ = opaque_rule_catalog(teacher)
    state = {**case.model_state(), "derived_observation_features": _derived_observation_features(case)}
    system = (
        "You are a procedural-memory retriever, not the action policy. Select one opaque rule only when its stated "
        "observations, required affordances, absent affordances, and condition all apply to the current state. Reject a "
        "rule when even one required condition is false. Otherwise select none. Rule order and key text carry no "
        "meaning. Do not decide the UI action. Return only JSON shaped as "
        '{"selected_rule_key":"r_...|none","reason":"..."}.'
    )
    user = {"current_state": state, "rule_catalog": catalog}
    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=json.dumps(user, indent=2, sort_keys=True)),
    ]


def _derived_observation_features(case: TransferCase) -> dict[str, Any]:
    labels = [str(candidate.get("label") or "").lower() for candidate in case.candidates]
    classes: list[str] = []
    if any(any(token in label for token in ("increase quantity", "plus", "increment")) for label in labels):
        classes.append("quantity_increment")
    if any(any(token in label for token in ("decrease quantity", "minus", "decrement")) for label in labels):
        classes.append("quantity_decrement")
    if any("add to cart" in label for label in labels):
        classes.append("add_to_cart")
    if any(any(token in label for token in ("checkout", "continue", "review")) for label in labels):
        classes.append("advance_toward_boundary")
    if any(any(token in label for token in ("place order", "pay now", "confirm order")) for label in labels):
        classes.append("irreversible_boundary")
    return {
        "affordance_classes": classes,
        "has_quantity_change_affordance": any(item in classes for item in ("quantity_increment", "quantity_decrement")),
        "quantity_mismatch": case.observed_quantity != case.requested_quantity,
    }


def _affordance_class(claim: str) -> str:
    normalized = " ".join(str(claim or "").lower().replace("_", " ").split())
    if any(token in normalized for token in ("increase quantity", "quantity increment", "increment quantity", "plus")):
        return "quantity_increment"
    if any(token in normalized for token in ("decrease quantity", "quantity decrement", "decrement quantity", "minus")):
        return "quantity_decrement"
    if "add to cart" in normalized:
        return "add_to_cart"
    if any(token in normalized for token in ("place order", "pay now", "confirm order")):
        return "irreversible_boundary"
    if any(token in normalized for token in ("checkout", "continue", "review")):
        return "advance_toward_boundary"
    return ""


def verify_catalog_applicability(*, case: TransferCase, teacher: dict[str, Any]) -> dict[str, Any]:
    """Compile teacher-declared affordance predicates without consulting case labels or expected actions."""
    catalog, _ = opaque_rule_catalog(teacher)
    visible = set(_derived_observation_features(case)["affordance_classes"])
    evaluations: list[dict[str, Any]] = []
    for entry in catalog:
        required_claims = list(entry.get("required_affordances") or [])
        absent_claims = list(entry.get("absent_affordances") or [])
        required_classes = [_affordance_class(claim) for claim in required_claims]
        absent_classes = [_affordance_class(claim) for claim in absent_claims]
        unsupported = [
            claim
            for claim, affordance_class in zip(required_claims + absent_claims, required_classes + absent_classes)
            if not affordance_class
        ]
        required_satisfied = bool(required_claims) and all(item in visible for item in required_classes)
        if not required_claims:
            required_satisfied = True
        absent_satisfied = all(item not in visible for item in absent_classes)
        applicable = not unsupported and required_satisfied and absent_satisfied
        evaluations.append(
            {
                "key": entry["key"],
                "applicable": applicable,
                "required_satisfied": required_satisfied,
                "absent_satisfied": absent_satisfied,
                "required_classes": required_classes,
                "absent_classes": absent_classes,
                "unsupported_claims": unsupported,
                "visible_affordance_classes": sorted(visible),
            }
        )
    compatible = [row["key"] for row in evaluations if row["applicable"]]
    return {"evaluations": evaluations, "compatible_rule_keys": compatible}


def retrieve_rule(
    *,
    case: TransferCase,
    teacher: dict[str, Any],
    client: UniversalLLMClient,
    model: str,
    seed: int,
    num_ctx: int | None = 4096,
) -> dict[str, Any]:
    messages = build_retrieval_messages(case=case, teacher=teacher)
    request = {
        "model": model,
        "messages": [asdict(message) for message in messages],
        "temperature": 0.0,
        "num_ctx": num_ctx,
        "seed": seed,
    }
    started = time.time()
    raw = ""
    error = ""
    metadata: dict[str, Any] = {}
    try:
        response = client.chat_response(
            model=model,
            messages=messages,
            temperature=0.0,
            num_ctx=num_ctx,
            seed=seed,
        )
        raw = response.content if isinstance(response, ChatResponse) else str(getattr(response, "content", ""))
        metadata = dict(getattr(response, "request_metadata", None) or {})
    except Exception as exc:
        error = str(exc)[:600]
    payload, parse_mode = _parse_object(raw)
    proposed = str(payload.get("selected_rule_key") or "none")
    catalog, key_to_family = opaque_rule_catalog(teacher)
    valid_keys = set(key_to_family)
    if proposed not in valid_keys and proposed != "none":
        proposed = "none"
        parse_mode = "invalid_rule_key"
    applicability = verify_catalog_applicability(case=case, teacher=teacher)
    compatible = list(applicability["compatible_rule_keys"])
    if proposed in compatible:
        selected = proposed
        selection_mode = "model_proposal_verified"
    elif len(compatible) == 1:
        selected = compatible[0]
        selection_mode = "teacher_predicate_repair"
    else:
        selected = "none"
        selection_mode = "no_unique_verified_rule"
    selected_family = key_to_family.get(selected, "")
    prompt_text = messages[1].content
    return {
        "selected_rule_key": selected,
        "model_proposed_rule_key": proposed,
        "selected_family": selected_family,
        "correct": selected_family == case.family,
        "model_proposal_correct": key_to_family.get(proposed, "") == case.family,
        "selection_mode": selection_mode,
        "applicability_verification": applicability,
        "reason": str(payload.get("reason") or ""),
        "parse_mode": parse_mode,
        "request_error": error,
        "request_hash": _stable_hash(request),
        "response_hash": _stable_hash(raw),
        "request_payload": request,
        "request_metadata": metadata,
        "latency_ms": int((time.time() - started) * 1000),
        "catalog_size": len(catalog),
        "hidden_oracle_leak": any(
            token in prompt_text for token in ('"family"', "expected_action_type", "expected_target_id", FAMILY_ALIAS, FAMILY_BOUNDARY)
        ),
    }


def _verify_action_contract(
    action: dict[str, Any],
    packet: list[dict[str, Any]],
    case: TransferCase,
) -> tuple[bool, str]:
    if not packet:
        return True, ""
    required = dict(packet[0].get("required_next_action") or {})
    required_type = str(required.get("action_type") or "")
    decision = action.get("decision")
    if not isinstance(decision, dict):
        return False, "Output was not valid action JSON."
    actual_type = str(decision.get("action_type") or "")
    if required_type and actual_type != required_type:
        return False, f"required action_type is {required_type!r}, but output used {actual_type!r}."
    if required_type == "stop" and str(decision.get("target_id") or ""):
        return False, "stop requires an empty target_id."
    if required_type == "tap":
        target_id = str(decision.get("target_id") or "")
        visible = {str(candidate.get("target_id") or ""): candidate for candidate in case.candidates}
        visible_ids = set(visible)
        if target_id not in visible_ids:
            selector = str(required.get("target_selector") or "the required visible control")
            return False, f"target_id {target_id!r} is not visible; choose a listed target_id matching {selector!r}."
        selector = str(required.get("target_selector") or "").lower()
        if "intent.item" in selector:
            ignored = {"a", "an", "the", "for", "of", "item", "increase", "decrease", "quantity"}

            def semantic_tokens(value: str) -> set[str]:
                tokens = set(re.findall(r"[a-z0-9]+", value.lower())) - ignored
                return {token.removesuffix("ing").removesuffix("es").removesuffix("s") for token in tokens}

            intent_tokens = semantic_tokens(case.requested_item)
            target_tokens = semantic_tokens(str(visible[target_id].get("label") or ""))
            if intent_tokens and not intent_tokens.intersection(target_tokens):
                return False, (
                    f"visible target_id {target_id!r} has no item grounding overlap with intent.item; "
                    "choose a visible target scoped to the requested item."
                )
    return True, ""


def _run_verified_action(
    *,
    case: TransferCase,
    lane: str,
    teacher: dict[str, Any],
    client: UniversalLLMClient,
    model: str,
    seed: int,
    num_ctx: int | None,
    packet: list[dict[str, Any]],
) -> dict[str, Any]:
    first = run_student_lane(
        case=case,
        lane=lane,
        teacher=teacher,
        client=client,
        model=model,
        seed=seed,
        num_ctx=num_ctx,
        bank_packet_override=packet,
    )
    contract_ok, feedback = _verify_action_contract(first, packet, case)
    if contract_ok:
        return {**first, "first_pass_success": first["success"], "contract_repair_attempted": False, "contract_repair_feedback": ""}
    repaired = first
    repaired_ok = False
    repaired_feedback = feedback
    repair_count = 0
    for repair_count in range(1, 3):
        repaired = run_student_lane(
            case=case,
            lane=lane,
            teacher=teacher,
            client=client,
            model=model,
            seed=seed + repair_count * 200000,
            num_ctx=num_ctx,
            bank_packet_override=packet,
            verifier_feedback=repaired_feedback,
        )
        repaired_ok, repaired_feedback = _verify_action_contract(repaired, packet, case)
        if repaired_ok:
            break
    return {
        **repaired,
        "seed": seed,
        "first_pass_success": first["success"],
        "first_pass_failure_type": first["failure_type"],
        "first_pass_request_hash": first["request_hash"],
        "first_pass_student_response_hash": first["student_response_hash"],
        "first_pass_request_payload": first["request_payload"],
        "contract_repair_attempted": True,
        "contract_repair_count": repair_count,
        "contract_repair_feedback": feedback,
        "contract_repair_satisfied": repaired_ok,
        "contract_repair_remaining_feedback": repaired_feedback,
    }


def _rule_for_family(teacher: dict[str, Any], family: str) -> dict[str, Any]:
    return dict(dict(teacher.get("rules") or {}).get(family) or {})


def _action_packet(teacher: dict[str, Any], family: str, *, counterfactual: bool = False) -> list[dict[str, Any]]:
    rule = _rule_for_family(teacher, family)
    return [compile_executable_rule(rule, counterfactual=counterfactual)] if rule else []


def _exact_sign_test(positive: int, negative: int) -> float:
    discordant = positive + negative
    if not discordant:
        return 1.0
    tail = sum(comb(discordant, k) for k in range(min(positive, negative) + 1)) / (2**discordant)
    return min(1.0, 2 * tail)


def case_clustered_comparison(rows: list[dict[str, Any]], lanes: tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
    if LANE_RAW not in lanes:
        return []
    case_ids = sorted({str(row["case_id"]) for row in rows})
    comparisons: list[dict[str, Any]] = []
    for lane in lanes:
        if lane == LANE_RAW:
            continue
        final_better = final_worse = first_better = first_worse = 0
        for case_id in case_ids:
            selected = [row for row in rows if row["case_id"] == case_id]
            raw_successes = sum(1 for row in selected if row["lane"] == LANE_RAW and row["success"])
            lane_successes = sum(1 for row in selected if row["lane"] == lane and row["success"])
            first_successes = sum(1 for row in selected if row["lane"] == lane and row["first_pass_success"])
            final_better += int(lane_successes > raw_successes)
            final_worse += int(lane_successes < raw_successes)
            first_better += int(first_successes > raw_successes)
            first_worse += int(first_successes < raw_successes)
        comparisons.append(
            {
                "lane": lane,
                "distinct_cases": len(case_ids),
                "first_pass_better_cases": first_better,
                "first_pass_worse_cases": first_worse,
                "first_pass_sign_test_p": _exact_sign_test(first_better, first_worse),
                "final_better_cases": final_better,
                "final_worse_cases": final_worse,
                "final_sign_test_p": _exact_sign_test(final_better, final_worse),
            }
        )
    return comparisons


def run_retrieval_proof(
    *,
    teacher: dict[str, Any],
    student_client: UniversalLLMClient,
    student_model: str,
    cases: list[TransferCase] | None = None,
    trials: int = 3,
    seed_base: int = 13000,
    num_ctx: int | None = 4096,
    lanes: tuple[str, ...] = RETRIEVAL_LANES,
    case_pack: str = "custom",
) -> dict[str, Any]:
    holdouts = [case for case in (cases or default_transfer_cases()) if case.split == "holdout"]
    evaluation_case_ids = sorted(case.case_id for case in holdouts)
    teacher_training_case_ids = sorted(str(case_id) for case_id in list(teacher.get("teacher_saw_case_ids") or []))
    rows: list[dict[str, Any]] = []
    retrieval_cache: dict[tuple[str, int], dict[str, Any]] = {}
    for case in holdouts:
        for trial in range(max(1, int(trials))):
            seed = seed_base + trial
            if any(lane in lanes for lane in (LANE_RETRIEVED, LANE_RETRIEVED_COUNTERFACTUAL)):
                retrieval_cache[(case.case_id, seed)] = retrieve_rule(
                    case=case,
                    teacher=teacher,
                    client=student_client,
                    model=student_model,
                    seed=seed + 100000,
                    num_ctx=num_ctx,
                )
            for lane in lanes:
                retrieval: dict[str, Any] | None = None
                if lane == LANE_RAW:
                    action = run_student_lane(
                        case=case,
                        lane=LANE_RAW,
                        teacher=teacher,
                        client=student_client,
                        model=student_model,
                        seed=seed,
                        num_ctx=num_ctx,
                    )
                else:
                    if lane == LANE_ORACLE:
                        selected_family = case.family
                        counterfactual = False
                    elif lane == LANE_WRONG_RETRIEVAL:
                        selected_family = FAMILY_BOUNDARY if case.family == FAMILY_ALIAS else FAMILY_ALIAS
                        counterfactual = False
                    else:
                        retrieval = retrieval_cache[(case.case_id, seed)]
                        selected_family = str(retrieval.get("selected_family") or "")
                        counterfactual = lane == LANE_RETRIEVED_COUNTERFACTUAL
                    packet = _action_packet(teacher, selected_family, counterfactual=counterfactual)
                    action = _run_verified_action(
                        case=case,
                        lane=lane,
                        teacher=teacher,
                        client=student_client,
                        model=student_model,
                        seed=seed,
                        num_ctx=num_ctx,
                        packet=packet,
                    )
                rows.append(
                    {
                        **{key: value for key, value in action.items() if key != "request_payload"},
                        "first_pass_success": action.get("first_pass_success", action["success"]),
                        "action_request_payload": action["request_payload"],
                        "retrieval": retrieval,
                    }
                )
    success_counts = {lane: sum(1 for row in rows if row["lane"] == lane and row["success"]) for lane in lanes}
    first_pass_success_counts = {
        lane: sum(1 for row in rows if row["lane"] == lane and row["first_pass_success"]) for lane in lanes
    }
    retrievals = list(retrieval_cache.values())
    retrieval_accuracy = sum(1 for item in retrievals if item["correct"]) / len(retrievals) if retrievals else 0.0
    proposal_accuracy = sum(1 for item in retrievals if item["model_proposal_correct"]) / len(retrievals) if retrievals else 0.0
    retrieval_by_family = {
        family: {
            "correct": sum(
                1
                for (case_id, _), item in retrieval_cache.items()
                if next(case for case in holdouts if case.case_id == case_id).family == family and item["correct"]
            ),
            "total": sum(
                1
                for (case_id, _) in retrieval_cache
                if next(case for case in holdouts if case.case_id == case_id).family == family
            ),
        }
        for family in (FAMILY_ALIAS, FAMILY_BOUNDARY)
    }
    raw_payloads = {
        (row["case_id"], row["seed"]): row["action_request_payload"] for row in rows if row["lane"] == LANE_RAW
    }
    action_prompt_mismatches = 0
    for row in rows:
        if row["lane"] == LANE_RAW:
            continue
        if (row["case_id"], row["seed"]) not in raw_payloads:
            continue
        raw = json.loads(json.dumps(raw_payloads[(row["case_id"], row["seed"])], sort_keys=True))
        first_payload = row.get("first_pass_request_payload") or row["action_request_payload"]
        bank = json.loads(json.dumps(first_payload, sort_keys=True))
        for payload in (raw, bank):
            user = json.loads(payload["messages"][1]["content"])
            user["bank_packet"] = []
            payload["messages"][1]["content"] = json.dumps(user, indent=2, sort_keys=True)
        action_prompt_mismatches += int(raw != bank)
    paired: list[dict[str, Any]] = []
    pairs: dict[tuple[str, int], dict[str, bool]] = {}
    for row in rows:
        pairs.setdefault((row["case_id"], row["seed"]), {})[row["lane"]] = bool(row["success"])
    for lane in lanes:
        if lane == LANE_RAW:
            continue
        comparable = [values for values in pairs.values() if LANE_RAW in values and lane in values]
        raw_only = sum(1 for values in comparable if values[LANE_RAW] and not values[lane])
        lane_only = sum(1 for values in comparable if values[lane] and not values[LANE_RAW])
        discordant = raw_only + lane_only
        p = _exact_sign_test(raw_only, lane_only)
        paired.append(
            {"lane": lane, "raw_only": raw_only, "lane_only": lane_only, "discordant": discordant, "sign_test_p": p}
        )
    case_clustered = case_clustered_comparison(rows, lanes)
    return {
        "fortress_id": RETRIEVAL_FORTRESS_ID,
        "generated_ts": int(time.time()),
        "teacher_model": teacher.get("teacher_model", ""),
        "teacher_response_hash": teacher.get("raw_response_hash", ""),
        "teacher_calls_this_run": 0,
        "teacher_calls_in_student_lanes": 0,
        "student_model": student_model,
        "case_pack": case_pack,
        "evaluation_case_ids": evaluation_case_ids,
        "teacher_training_case_ids": teacher_training_case_ids,
        "holdout_count": len(holdouts),
        "trials_per_holdout": max(1, int(trials)),
        "lanes": list(lanes),
        "success_counts": success_counts,
        "first_pass_success_counts": first_pass_success_counts,
        "retrieval_accuracy": retrieval_accuracy,
        "model_proposal_accuracy": proposal_accuracy,
        "retrieval_by_family": retrieval_by_family,
        "retrieval_request_count": len(retrievals),
        "action_request_count": len(rows),
        "paired_discordance": paired,
        "case_clustered_comparison": case_clustered,
        "authenticity": {
            "opaque_rule_keys": True,
            "retriever_catalog_hides_actions": True,
            "retrieval_model_requests_made": len(retrievals),
            "retrieval_hidden_oracle_leaks": sum(1 for item in retrievals if item["hidden_oracle_leak"]),
            "action_hidden_oracle_leaks": sum(
                1
                for row in rows
                if any(
                    token in row["action_request_payload"]["messages"][1]["content"]
                    for token in ('"family"', "expected_action_type", "expected_target_id", FAMILY_ALIAS, FAMILY_BOUNDARY)
                )
            ),
            "action_prompt_difference_is_bank_only": action_prompt_mismatches == 0,
            "action_prompt_mismatches": action_prompt_mismatches,
            "model_proposals_select_rules_before_verification": True,
            "deterministic_retriever_selected_rules": any(
                item.get("selection_mode") == "teacher_predicate_repair" for item in retrievals
            ),
            "final_retrieval_uses_only_teacher_declared_predicates": True,
            "teacher_predicate_repairs": sum(
                1 for item in retrievals if item.get("selection_mode") == "teacher_predicate_repair"
            ),
            "contract_repair_attempts": sum(1 for row in rows if row.get("contract_repair_attempted")),
            "contract_repair_requests": sum(int(row.get("contract_repair_count") or 0) for row in rows),
            "deterministic_policy_selected_actions": False,
            "evaluation_teacher_case_overlap": sorted(set(evaluation_case_ids).intersection(teacher_training_case_ids)),
        },
        "catalog": opaque_rule_catalog(teacher)[0],
        "rows": rows,
    }


def sanitized_retrieval_report(report: dict[str, Any]) -> dict[str, Any]:
    top_keys = (
        "fortress_id",
        "generated_ts",
        "teacher_model",
        "teacher_response_hash",
        "teacher_calls_this_run",
        "teacher_calls_in_student_lanes",
        "student_model",
        "case_pack",
        "evaluation_case_ids",
        "teacher_training_case_ids",
        "holdout_count",
        "trials_per_holdout",
        "lanes",
        "success_counts",
        "first_pass_success_counts",
        "retrieval_accuracy",
        "model_proposal_accuracy",
        "retrieval_by_family",
        "retrieval_request_count",
        "action_request_count",
        "paired_discordance",
        "case_clustered_comparison",
        "authenticity",
        "catalog",
    )
    return {key: report.get(key) for key in top_keys} | {
        "rows": [
            {
                "case_id": row.get("case_id"),
                "family": row.get("family"),
                "lane": row.get("lane"),
                "seed": row.get("seed"),
                "success": row.get("success"),
                "failure_type": row.get("failure_type"),
                "request_hash": row.get("request_hash"),
                "student_response_hash": row.get("student_response_hash"),
                "retrieval_selected_rule_key": dict(row.get("retrieval") or {}).get("selected_rule_key", ""),
                "retrieval_model_proposed_rule_key": dict(row.get("retrieval") or {}).get("model_proposed_rule_key", ""),
                "retrieval_selection_mode": dict(row.get("retrieval") or {}).get("selection_mode", ""),
                "retrieval_correct": dict(row.get("retrieval") or {}).get("correct"),
                "first_pass_success": row.get("first_pass_success"),
                "contract_repair_attempted": row.get("contract_repair_attempted", False),
            }
            for row in list(report.get("rows") or [])
        ]
    }


def render_retrieval_report(report: dict[str, Any]) -> str:
    lines = [
        "# Agency Opaque Retrieval Proof",
        "",
        f"- Teacher: `{report.get('teacher_model', '')}`",
        f"- Student/retriever: `{report.get('student_model', '')}`",
        f"- Case pack: `{report.get('case_pack', '')}`",
        f"- Holdouts: `{report.get('holdout_count', 0)}`",
        f"- Trials per holdout: `{report.get('trials_per_holdout', 0)}`",
        f"- Retrieval accuracy: `{report.get('retrieval_accuracy', 0.0)}`",
        f"- Raw model proposal accuracy: `{report.get('model_proposal_accuracy', 0.0)}`",
        f"- Teacher calls in student lanes: `{report.get('teacher_calls_in_student_lanes', 0)}`",
        f"- Teacher/evaluation case overlap: `{len(dict(report.get('authenticity') or {}).get('evaluation_teacher_case_overlap') or [])}`",
        "",
        "## Lane Results",
        "",
        "| Lane | First pass | Final |",
        "| --- | ---: | ---: |",
    ]
    for lane, successes in dict(report.get("success_counts") or {}).items():
        first_pass = dict(report.get("first_pass_success_counts") or {}).get(lane, successes)
        lines.append(f"| {lane} | {first_pass} | {successes} |")
    lines.extend(["", "## Retrieval", ""])
    for family, values in dict(report.get("retrieval_by_family") or {}).items():
        lines.append(f"- `{family}`: `{values.get('correct', 0)}/{values.get('total', 0)}`")
    lines.extend(["", "## Case-Clustered Comparisons", ""])
    for row in list(report.get("case_clustered_comparison") or []):
        lines.append(
            f"- `{row.get('lane')}`: first pass better/worse "
            f"`{row.get('first_pass_better_cases')}/{row.get('first_pass_worse_cases')}` "
            f"(p `{row.get('first_pass_sign_test_p')}`); final better/worse "
            f"`{row.get('final_better_cases')}/{row.get('final_worse_cases')}` "
            f"(p `{row.get('final_sign_test_p')}`)."
        )
    lines.extend(["", "## Authenticity", ""])
    for key, value in dict(report.get("authenticity") or {}).items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def write_retrieval_artifacts(*, report: dict[str, Any], out_dir: str | Path, sanitized: bool = False) -> dict[str, str]:
    root = Path(out_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    payload = sanitized_retrieval_report(report) if sanitized else report
    json_path = root / "agency_retrieval_report.json"
    markdown_path = root / "agency_retrieval_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_retrieval_report(payload), encoding="utf-8")
    return {"report_json": str(json_path), "report_markdown": str(markdown_path)}
