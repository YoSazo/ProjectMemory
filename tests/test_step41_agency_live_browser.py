from __future__ import annotations

from memory_system.fortresses.agency_live_browser import (
    LiveCandidate,
    candidate_fingerprint,
    classify_candidate_safety,
    parse_live_decision,
    rank_candidates,
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


def test_live_decision_parser_is_strict_about_actions_and_candidate_ids():
    decision, mode = parse_live_decision(
        '{"action":"click","candidate_id":"c002","text":"","reason":"city matches goal"}'
    )
    assert mode == "json"
    assert decision and decision["candidate_id"] == "c002"
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
