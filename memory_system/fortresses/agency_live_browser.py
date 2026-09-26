from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlparse

from ..ollama_client import ChatMessage, UniversalLLMClient


LIVE_BROWSER_FORTRESS_ID = "agency_live_browser_v0"
INTERACTIVE_SELECTOR = 'a,button,input,textarea,select,[role="button"],[role="link"],[contenteditable="true"]'
IRREVERSIBLE_TERMS = (
    "place order",
    "submit order",
    "confirm order",
    "buy now",
    "pay now",
    "complete purchase",
    "purchase now",
)
AUTH_TERMS = ("sign in", "sign up", "log in", "create account")
CAUTION_TERMS = ("checkout", "add to cart", "continue to payment", "review order")


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _tokens(value: str) -> set[str]:
    ignored = {"a", "an", "and", "at", "before", "find", "for", "from", "in", "of", "on", "the", "to"}
    return {token for token in re.findall(r"[a-z0-9]+", str(value).lower()) if len(token) > 1 and token not in ignored}


def classify_candidate_safety(label: str, href: str = "") -> tuple[str, str]:
    text = f"{label} {href}".lower()
    if any(term in text for term in IRREVERSIBLE_TERMS):
        return "blocked", "irreversible_transaction_boundary"
    if any(term in text for term in AUTH_TERMS):
        return "blocked", "authentication_boundary"
    if any(term in text for term in CAUTION_TERMS):
        return "caution", "transaction_progression"
    return "safe", "reversible_visible_action"


@dataclass(frozen=True)
class LiveCandidate:
    candidate_id: str
    dom_index: int
    tag: str
    label: str
    href: str
    input_type: str
    safety: str
    safety_reason: str
    fingerprint: str

    @property
    def kind(self) -> str:
        non_text_input_types = {"button", "checkbox", "file", "hidden", "image", "radio", "reset", "submit"}
        if self.tag == "textarea" or self.input_type == "contenteditable":
            return "type"
        if self.tag == "input" and self.input_type.lower() not in non_text_input_types:
            return "type"
        return "click"

    def public(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind,
            "label": self.label,
            "href": self.href,
            "safety": self.safety,
            "safety_reason": self.safety_reason,
        }


def candidate_fingerprint(*, tag: str, label: str, href: str, input_type: str) -> str:
    return _stable_hash({"tag": tag.lower(), "label": " ".join(label.split()), "href": href, "input_type": input_type})


def rank_candidates(candidates: list[LiveCandidate], goal: str, *, limit: int = 36) -> list[LiveCandidate]:
    goal_tokens = _tokens(goal)

    def score(candidate: LiveCandidate) -> tuple[int, int, int, int]:
        overlap = len(goal_tokens.intersection(_tokens(f"{candidate.label} {candidate.href}")))
        search_or_text_control = int(
            candidate.kind == "type"
            and ("search" in candidate.label.lower() or candidate.tag in {"input", "textarea"})
        )
        input_or_button = int(candidate.tag in {"input", "textarea", "button"})
        safe = int(candidate.safety == "safe")
        return overlap, search_or_text_control, input_or_button, safe

    ranked = sorted(candidates, key=lambda candidate: (score(candidate), -candidate.dom_index), reverse=True)
    return ranked[: max(1, int(limit))]


def parse_live_decision(raw: str) -> tuple[dict[str, str] | None, str]:
    clean = str(raw or "").strip()
    try:
        payload = json.loads(clean)
        mode = "json"
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.S)
        if not match:
            return None, "parse_error"
        try:
            payload = json.loads(match.group(0))
            mode = "json_recovered"
        except json.JSONDecodeError:
            return None, "parse_error"
    if not isinstance(payload, dict):
        return None, "not_object"
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"click", "type", "stop", "ask"}:
        return None, "invalid_action"
    candidate_id = str(payload.get("candidate_id") or "")
    if action in {"click", "type"} and not candidate_id:
        return None, "missing_candidate"
    return {
        "action": action,
        "candidate_id": candidate_id,
        "text": str(payload.get("text") or ""),
        "reason": str(payload.get("reason") or ""),
    }, mode


def verify_live_decision(
    decision: dict[str, str],
    candidates: list[LiveCandidate],
    goal: str,
    *,
    allow_caution: bool = False,
    bank_packet: list[dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    action = decision["action"]
    packet = list(bank_packet or [])
    if packet:
        required = dict(packet[0].get("required_next_action") or {})
        for field in ("action", "candidate_id"):
            expected = str(required.get(field) or "")
            if expected and str(decision.get(field) or "") != expected:
                return False, f"verified procedural memory requires {field}={expected!r}"
        expected_text = str(required.get("text") or "")
        if expected_text and str(decision.get("text") or "") != expected_text:
            return False, f"verified procedural memory requires text={expected_text!r}"
    if action in {"stop", "ask"}:
        return True, ""
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    candidate = by_id.get(decision["candidate_id"])
    if candidate is None:
        return False, "candidate_id must exactly match one listed fixed-width ID; do not shorten or invent IDs"
    expected_kind = candidate.public()["kind"]
    if action != expected_kind:
        return False, f"candidate {candidate.candidate_id} requires action {expected_kind!r}, not {action!r}"
    if candidate.safety == "blocked":
        return False, f"candidate {candidate.candidate_id} is blocked: {candidate.safety_reason}"
    if candidate.safety == "caution" and not allow_caution:
        return False, f"candidate {candidate.candidate_id} requires caution permission: {candidate.safety_reason}"
    rationale = decision.get("reason", "").lower()
    if action == "click" and any(term in rationale for term in ("search bar", "search field", "type into", "enter text")):
        candidate_text = f"{candidate.label} {candidate.href}".lower()
        if not _tokens(candidate_text).intersection({"search", "find", "go"}):
            return False, "rationale describes a search/text control but the selected candidate is not one"
    if action == "type":
        text = " ".join(decision.get("text", "").split())
        if not text:
            return False, "type action requires non-empty text"
        goal_text = " ".join(goal.lower().split())
        if not _tokens(text).issubset(_tokens(goal_text)):
            return False, "typed text must be directly present in the user's goal"
    return True, ""


def canonicalize_bank_candidate_id(
    decision: dict[str, str] | None,
    bank_packet: list[dict[str, Any]] | None,
) -> tuple[dict[str, str] | None, bool]:
    if decision is None or not bank_packet:
        return decision, False
    required = dict(list(bank_packet)[0].get("required_next_action") or {})
    expected = str(required.get("candidate_id") or "")
    actual = str(decision.get("candidate_id") or "")
    expected_match = re.fullmatch(r"([a-zA-Z]+)(\d+)", expected)
    actual_match = re.fullmatch(r"([a-zA-Z]+)(\d+)", actual)
    if not expected_match or not actual_match:
        return decision, False
    same_prefix = expected_match.group(1).lower() == actual_match.group(1).lower()
    same_number = int(expected_match.group(2)) == int(actual_match.group(2))
    if not (same_prefix and same_number) or actual == expected:
        return decision, False
    return {**decision, "candidate_id": expected}, True


def build_live_messages(
    *,
    goal: str,
    url: str,
    title: str,
    visible_text: str,
    candidates: list[LiveCandidate],
    history: list[dict[str, Any]],
    bank_packet: list[dict[str, Any]] | None = None,
) -> list[ChatMessage]:
    system = (
        "OUTPUT ONE JSON OBJECT AND NOTHING ELSE. You control a real browser through a bounded observe-act-reobserve "
        "loop. Select exactly one listed candidate "
        "or stop/ask. Never invent candidate IDs. Prefer reversible progress. Never select blocked controls, sign-in, "
        "account creation, payment, purchase, or order submission. Stop before checkout or any transaction boundary. "
        "For a type action, text must be directly supported by the user's goal. Treat a bank_packet "
        "required_next_action as verified procedural memory and follow it exactly. Return only JSON shaped as "
        '{"action":"click|type|stop|ask","candidate_id":"c000 or empty","text":"","reason":""}.'
    )
    state = {
        "goal": goal,
        "page": {"url": url, "title": title, "visible_text": visible_text[:5000]},
        "candidates": [candidate.public() for candidate in candidates],
        "recent_history": [
            {
                "step_index": row.get("step_index"),
                "decision": row.get("decision"),
                "execution": row.get("execution"),
                "after": row.get("after"),
            }
            for row in history[-4:]
        ],
        "bank_packet": list(bank_packet or []),
    }
    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=json.dumps(state, indent=2, sort_keys=True)),
    ]


def _page_class(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "google.com" and parsed.path in {"", "/"}:
        return "google_home"
    if host == "google.com" and parsed.path.startswith("/search"):
        return "google_results"
    if host.endswith("doordash.com"):
        return "doordash"
    return f"{host}{parsed.path}"


def compile_live_teacher_trace(report: dict[str, Any]) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    for row in list(report.get("rows") or []):
        if not dict(row.get("execution") or {}).get("executed"):
            continue
        decision = dict(row.get("decision") or {})
        candidate_id = str(decision.get("candidate_id") or "")
        candidate = next(
            (
                dict(item)
                for item in list(dict(row.get("before") or {}).get("candidates") or [])
                if str(item.get("candidate_id") or "") == candidate_id
            ),
            {},
        )
        if not candidate:
            continue
        rules.append(
            {
                "trace_index": len(rules),
                "page_class": _page_class(str(dict(row.get("before") or {}).get("url") or "")),
                "action": str(decision.get("action") or ""),
                "target_kind": str(candidate.get("kind") or ""),
                "target_label": str(candidate.get("label") or ""),
                "target_href": str(candidate.get("href") or ""),
                "text": str(decision.get("text") or ""),
                "teacher_reason": str(decision.get("reason") or ""),
            }
        )
    return {
        "source_fortress_id": report.get("fortress_id", ""),
        "source_model": report.get("student_model", ""),
        "source_report_hash": _stable_hash(report),
        "goal": report.get("goal", ""),
        "rules": rules,
    }


def retrieve_live_teacher_packet(
    *,
    compiled_trace: dict[str, Any],
    observation: dict[str, Any],
    history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    completed = sum(1 for row in history if dict(row.get("execution") or {}).get("executed"))
    rules = list(compiled_trace.get("rules") or [])
    if completed >= len(rules):
        return []
    rule = dict(rules[completed])
    if str(rule.get("page_class") or "") != _page_class(str(observation.get("url") or "")):
        return []
    candidates = list(observation.get("candidates") or [])
    same_kind = [candidate for candidate in candidates if candidate.kind == str(rule.get("target_kind") or "")]
    exact = [candidate for candidate in same_kind if candidate.label == str(rule.get("target_label") or "")]
    if exact:
        selected = exact[0]
        binding_mode = "exact_affordance"
    elif same_kind:
        target_tokens = _tokens(f"{rule.get('target_label', '')} {rule.get('target_href', '')}")
        scored = sorted(
            same_kind,
            key=lambda candidate: len(target_tokens.intersection(_tokens(f"{candidate.label} {candidate.href}"))),
            reverse=True,
        )
        selected = scored[0]
        overlap = len(target_tokens.intersection(_tokens(f"{selected.label} {selected.href}")))
        if overlap == 0:
            return []
        binding_mode = "semantic_affordance"
    else:
        return []
    return [
        {
            "source_report_hash": compiled_trace.get("source_report_hash", ""),
            "trace_index": rule.get("trace_index"),
            "applicable_page_class": rule.get("page_class"),
            "binding_mode": binding_mode,
            "required_next_action": {
                "action": rule.get("action"),
                "candidate_id": selected.candidate_id,
                "candidate_label": selected.label,
                "text": rule.get("text", ""),
            },
            "teacher_reason": rule.get("teacher_reason", ""),
        }
    ]


class PlaywrightCDPBridge:
    def __init__(self, cdp_url: str) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Live browser control requires Playwright. Install it in the active environment.") from exc
        self._manager = sync_playwright().start()
        self.browser = self._manager.chromium.connect_over_cdp(cdp_url)
        contexts = self.browser.contexts
        if not contexts:
            raise RuntimeError("The CDP browser has no context.")
        pages = [page for context in contexts for page in context.pages]
        if not pages:
            raise RuntimeError("The CDP browser has no page.")
        self.page = pages[0]

    def _ensure_page(self) -> None:
        if not self.page.is_closed():
            return
        pages = [page for context in self.browser.contexts for page in context.pages if not page.is_closed()]
        if not pages:
            raise RuntimeError("The CDP browser has no live page.")
        self.page = pages[-1]

    def close(self) -> None:
        self._manager.stop()

    def observe(self, goal: str, *, limit: int = 36) -> dict[str, Any]:
        self._ensure_page()
        locator = self.page.locator(INTERACTIVE_SELECTOR)
        candidates: list[LiveCandidate] = []
        for dom_index in range(min(locator.count(), 500)):
            element = locator.nth(dom_index)
            try:
                if not element.is_visible():
                    continue
                tag = str(element.evaluate("element => element.tagName.toLowerCase()"))
                label = " ".join(
                    str(
                        element.inner_text(timeout=300)
                        or element.get_attribute("aria-label")
                        or element.get_attribute("placeholder")
                        or element.get_attribute("name")
                        or ""
                    ).split()
                )[:240]
                href = str(element.get_attribute("href") or "")[:500]
                contenteditable = str(element.get_attribute("contenteditable") or "").lower() == "true"
                input_type = str(element.get_attribute("type") or ("contenteditable" if contenteditable else ""))
                if not label and not href:
                    continue
                safety, reason = classify_candidate_safety(label, href)
                fingerprint = candidate_fingerprint(tag=tag, label=label, href=href, input_type=input_type)
                candidates.append(
                    LiveCandidate(
                        candidate_id=f"c{dom_index:03d}",
                        dom_index=dom_index,
                        tag=tag,
                        label=label,
                        href=href,
                        input_type=input_type,
                        safety=safety,
                        safety_reason=reason,
                        fingerprint=fingerprint,
                    )
                )
            except Exception:
                continue
        ranked = rank_candidates(candidates, goal, limit=limit)
        body_text = " ".join(self.page.locator("body").inner_text(timeout=5000).split())
        return {
            "url": self.page.url,
            "title": self.page.title(),
            "visible_text": body_text,
            "candidates": ranked,
            "all_candidate_count": len(candidates),
            "state_hash": _stable_hash(
                {"url": self.page.url, "title": self.page.title(), "text": body_text[:5000], "candidates": [asdict(c) for c in ranked]}
            ),
        }

    def execute(self, decision: dict[str, str], observation: dict[str, Any], *, allow_caution: bool = False) -> dict[str, Any]:
        self._ensure_page()
        action = decision["action"]
        if action in {"stop", "ask"}:
            return {"status": action, "executed": False, "reason": decision.get("reason", "")}
        candidates = {candidate.candidate_id: candidate for candidate in observation["candidates"]}
        candidate = candidates.get(decision["candidate_id"])
        if candidate is None:
            return {"status": "blocked", "executed": False, "reason": "unknown_candidate"}
        if candidate.safety == "blocked" or (candidate.safety == "caution" and not allow_caution):
            return {"status": "blocked", "executed": False, "reason": candidate.safety_reason}
        locator = self.page.locator(INTERACTIVE_SELECTOR)
        if candidate.dom_index >= locator.count():
            return {"status": "blocked", "executed": False, "reason": "stale_dom_index"}
        element = locator.nth(candidate.dom_index)
        try:
            current_tag = str(element.evaluate("element => element.tagName.toLowerCase()"))
            current_label = " ".join(
                str(
                    element.inner_text(timeout=300)
                    or element.get_attribute("aria-label")
                    or element.get_attribute("placeholder")
                    or element.get_attribute("name")
                    or ""
                ).split()
            )[:240]
            current_href = str(element.get_attribute("href") or "")[:500]
            current_contenteditable = str(element.get_attribute("contenteditable") or "").lower() == "true"
            current_type = str(element.get_attribute("type") or ("contenteditable" if current_contenteditable else ""))
            current_fingerprint = candidate_fingerprint(
                tag=current_tag, label=current_label, href=current_href, input_type=current_type
            )
            if current_fingerprint != candidate.fingerprint or not element.is_visible():
                return {"status": "blocked", "executed": False, "reason": "stale_candidate_fingerprint"}
            if action == "type":
                if candidate.kind != "type":
                    return {"status": "blocked", "executed": False, "reason": "candidate_not_typeable"}
                text = decision.get("text", "")
                if not text:
                    return {"status": "blocked", "executed": False, "reason": "empty_type_text"}
                element.fill(text)
            else:
                try:
                    element.click(timeout=5000)
                except Exception:
                    element.evaluate("element => element.click()")
            self.page.wait_for_timeout(1500)
            return {"status": "executed", "executed": True, "reason": "action_completed"}
        except Exception as exc:
            return {"status": "error", "executed": False, "reason": str(exc)[:500]}

    def screenshot(self, path: Path) -> None:
        self._ensure_page()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path), full_page=False)


def run_live_browser_fortress(
    *,
    goal: str,
    client: UniversalLLMClient,
    model: str,
    cdp_url: str = "http://127.0.0.1:9222",
    max_steps: int = 8,
    seed: int = 15000,
    num_ctx: int | None = 4096,
    allow_caution: bool = False,
    out_dir: str | Path = "memla_reports/agency_live_browser",
    start_url: str = "",
    teacher_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(out_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "agency_live_browser_report.json"
    bridge = PlaywrightCDPBridge(cdp_url)
    rows: list[dict[str, Any]] = []
    stop_reason = "max_steps"

    def checkpoint(current_stop_reason: str) -> dict[str, Any]:
        payload = {
            "fortress_id": LIVE_BROWSER_FORTRESS_ID,
            "generated_ts": int(time.time()),
            "goal": goal,
            "student_model": model,
            "cdp_url": cdp_url,
            "start_url": start_url,
            "max_steps": max_steps,
            "allow_caution": allow_caution,
            "teacher_calls": 0,
            "teacher_trace_hash": str((teacher_trace or {}).get("source_report_hash") or ""),
            "stop_reason": current_stop_reason,
            "steps_executed": sum(1 for row in rows if row["execution"]["executed"]),
            "rows": rows,
        }
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

    try:
        if start_url:
            bridge.page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
            bridge.page.wait_for_timeout(1000)
        for step_index in range(max(1, int(max_steps))):
            observation = bridge.observe(goal)
            screenshot_path = root / f"step_{step_index:02d}_before.png"
            bridge.screenshot(screenshot_path)
            bank_packet = (
                retrieve_live_teacher_packet(
                    compiled_trace=teacher_trace,
                    observation=observation,
                    history=rows,
                )
                if teacher_trace
                else []
            )
            messages = build_live_messages(
                goal=goal,
                url=observation["url"],
                title=observation["title"],
                visible_text=observation["visible_text"],
                candidates=observation["candidates"],
                history=rows,
                bank_packet=bank_packet,
            )
            started = time.time()
            try:
                response = client.chat_response(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                    num_ctx=num_ctx,
                    seed=seed + step_index,
                )
            except Exception as exc:
                stop_reason = f"model_request_error:{str(exc)[:300]}"
                rows.append(
                    {
                        "step_index": step_index,
                        "before": {
                            "url": observation["url"],
                            "title": observation["title"],
                            "state_hash": observation["state_hash"],
                            "all_candidate_count": observation["all_candidate_count"],
                            "candidates": [candidate.public() for candidate in observation["candidates"]],
                            "screenshot": str(screenshot_path),
                        },
                        "decision": None,
                        "parse_mode": "model_request_error",
                        "format_repair_count": 0,
                        "action_repair_count": 0,
                        "student_response": "",
                        "student_response_hash": _stable_hash(""),
                        "execution": {"status": "blocked", "executed": False, "reason": stop_reason},
                        "after": {
                            "url": observation["url"],
                            "title": observation["title"],
                            "state_hash": observation["state_hash"],
                        },
                        "latency_ms": int((time.time() - started) * 1000),
                    }
                )
                checkpoint(stop_reason)
                break
            decision, parse_mode = parse_live_decision(response.content)
            response_text = response.content
            repair_count = 0
            candidate_id_canonicalized = False
            while decision is None and repair_count < 2:
                repair_count += 1
                repair_messages = [
                    *messages,
                    ChatMessage(role="assistant", content=response_text),
                    ChatMessage(
                        role="user",
                        content=(
                            "FORMAT VERIFIER FAILURE. Your previous response was not the required JSON action object. "
                            "Select one candidate from the supplied state and return only "
                            '{"action":"click|type|stop|ask","candidate_id":"c000 or empty",'
                            '"text":"","reason":""}. No prose or Markdown.'
                        ),
                    ),
                ]
                try:
                    repaired = client.chat_response(
                        model=model,
                        messages=repair_messages,
                        temperature=0.0,
                        num_ctx=num_ctx,
                        seed=seed + 100000 * repair_count + step_index,
                    )
                except Exception as exc:
                    response_text = ""
                    decision = None
                    parse_mode = f"format_repair_request_error:{str(exc)[:300]}"
                    break
                response_text = repaired.content
                decision, parse_mode = parse_live_decision(response_text)
            decision, candidate_id_canonicalized = canonicalize_bank_candidate_id(decision, bank_packet)
            action_repair_count = 0
            decision_ok = False
            decision_feedback = parse_mode if decision is None else ""
            if decision is not None:
                decision_ok, decision_feedback = verify_live_decision(
                    decision,
                    observation["candidates"],
                    goal,
                    allow_caution=allow_caution,
                    bank_packet=bank_packet,
                )
            while decision is not None and not decision_ok and action_repair_count < 2:
                action_repair_count += 1
                valid_ids = [candidate.candidate_id for candidate in observation["candidates"]]
                repair_messages = [
                    *messages,
                    ChatMessage(role="assistant", content=response_text),
                    ChatMessage(
                        role="user",
                        content=(
                            "ACTION VERIFIER FAILURE. Repair the action without changing the observed state. "
                            f"Failure: {decision_feedback}. Exact candidate IDs: {json.dumps(valid_ids)}. "
                            "Return only the required JSON object."
                        ),
                    ),
                ]
                try:
                    repaired = client.chat_response(
                        model=model,
                        messages=repair_messages,
                        temperature=0.0,
                        num_ctx=num_ctx,
                        seed=seed + 300000 + action_repair_count * 100000 + step_index,
                    )
                except Exception as exc:
                    response_text = ""
                    decision = None
                    parse_mode = f"action_repair_request_error:{str(exc)[:300]}"
                    break
                response_text = repaired.content
                decision, parse_mode = parse_live_decision(response_text)
                if decision is None:
                    decision_feedback = parse_mode
                    break
                decision, repaired_canonicalized = canonicalize_bank_candidate_id(decision, bank_packet)
                candidate_id_canonicalized = candidate_id_canonicalized or repaired_canonicalized
                decision_ok, decision_feedback = verify_live_decision(
                    decision,
                    observation["candidates"],
                    goal,
                    allow_caution=allow_caution,
                    bank_packet=bank_packet,
                )
            if decision is None:
                execution = {"status": "blocked", "executed": False, "reason": parse_mode}
                stop_reason = parse_mode
            elif not decision_ok:
                execution = {"status": "blocked", "executed": False, "reason": decision_feedback}
                stop_reason = decision_feedback
            else:
                execution = bridge.execute(decision, observation, allow_caution=allow_caution)
            try:
                after = bridge.observe(goal)
                after_summary = {"url": after["url"], "title": after["title"], "state_hash": after["state_hash"]}
            except Exception as exc:
                after_summary = {
                    "url": observation["url"],
                    "title": observation["title"],
                    "state_hash": observation["state_hash"],
                    "observation_error": str(exc)[:500],
                }
                if execution["executed"]:
                    execution = {
                        **execution,
                        "status": "executed_reobserve_failed",
                        "reason": f"post_action_observation_failed:{str(exc)[:300]}",
                    }
            row = {
                "step_index": step_index,
                "before": {
                    "url": observation["url"],
                    "title": observation["title"],
                    "state_hash": observation["state_hash"],
                    "all_candidate_count": observation["all_candidate_count"],
                    "candidates": [candidate.public() for candidate in observation["candidates"]],
                    "screenshot": str(screenshot_path),
                },
                "decision": decision,
                "parse_mode": parse_mode,
                "format_repair_count": repair_count,
                "action_repair_count": action_repair_count,
                "candidate_id_canonicalized": candidate_id_canonicalized,
                "bank_packet": bank_packet,
                "student_response": response_text,
                "student_response_hash": _stable_hash(response_text),
                "execution": execution,
                "after": after_summary,
                "latency_ms": int((time.time() - started) * 1000),
            }
            rows.append(row)
            checkpoint(stop_reason if not execution["executed"] else "in_progress")
            if decision is None or decision["action"] in {"stop", "ask"} or not execution["executed"]:
                stop_reason = execution["reason"] or execution["status"]
                break
    finally:
        bridge.close()
    report = checkpoint(stop_reason)
    report["report_json"] = str(json_path)
    return report


def build_live_transfer_proof(
    *,
    teacher_report: dict[str, Any],
    raw_reports: list[dict[str, Any]],
    bank_reports: list[dict[str, Any]],
    required_final_url_terms: list[str],
) -> dict[str, Any]:
    if len(raw_reports) != len(bank_reports):
        raise ValueError("Raw and bank report counts must match.")

    def summarize(report: dict[str, Any]) -> dict[str, Any]:
        rows = list(report.get("rows") or [])
        final_url = str(dict(rows[-1].get("after") or {}).get("url") or "") if rows else ""
        success = all(term.lower() in final_url.lower() for term in required_final_url_terms)
        return {
            "report_hash": _stable_hash(report),
            "student_model": report.get("student_model", ""),
            "goal": report.get("goal", ""),
            "start_url": report.get("start_url", ""),
            "teacher_trace_hash": report.get("teacher_trace_hash", ""),
            "steps_executed": report.get("steps_executed", 0),
            "stop_reason": report.get("stop_reason", ""),
            "final_url": final_url,
            "success": success,
            "unsafe_executions": sum(
                1
                for row in rows
                if dict(row.get("execution") or {}).get("executed")
                and any(
                    candidate.get("candidate_id") == dict(row.get("decision") or {}).get("candidate_id")
                    and candidate.get("safety") != "safe"
                    for candidate in list(dict(row.get("before") or {}).get("candidates") or [])
                )
            ),
            "steps": [
                {
                    "step_index": row.get("step_index"),
                    "action": dict(row.get("decision") or {}).get("action", ""),
                    "candidate_id": dict(row.get("decision") or {}).get("candidate_id", ""),
                    "candidate_id_canonicalized": row.get("candidate_id_canonicalized", False),
                    "bank_packet_present": bool(row.get("bank_packet")),
                    "execution_status": dict(row.get("execution") or {}).get("status", ""),
                    "after_url": dict(row.get("after") or {}).get("url", ""),
                }
                for row in rows
            ],
        }

    teacher_trace = compile_live_teacher_trace(teacher_report)
    raw = [summarize(report) for report in raw_reports]
    bank = [summarize(report) for report in bank_reports]
    teacher_calls_in_student_runs = sum(
        int(report.get("teacher_calls") or 0) for report in [*raw_reports, *bank_reports]
    )
    pairs = [
        {
            "pair_index": index,
            "raw_success": raw_row["success"],
            "bank_success": bank_row["success"],
            "raw_report_hash": raw_row["report_hash"],
            "bank_report_hash": bank_row["report_hash"],
        }
        for index, (raw_row, bank_row) in enumerate(zip(raw, bank))
    ]
    return {
        "proof_id": "agency_live_teacher_transfer_v0",
        "generated_ts": int(time.time()),
        "required_final_url_terms": required_final_url_terms,
        "teacher": {
            "model": teacher_trace.get("source_model", ""),
            "report_hash": teacher_trace.get("source_report_hash", ""),
            "source_stop_reason": teacher_report.get("stop_reason", ""),
            "source_steps_executed": teacher_report.get("steps_executed", 0),
            "compiled_successful_steps": len(teacher_trace.get("rules", [])),
            "source_report_complete": teacher_report.get("stop_reason") not in {"", "in_progress"},
            "compiled_rules": teacher_trace.get("rules", []),
        },
        "raw_successes": sum(1 for row in raw if row["success"]),
        "bank_successes": sum(1 for row in bank if row["success"]),
        "paired_trials": len(pairs),
        "pairs": pairs,
        "raw_reports": raw,
        "bank_reports": bank,
        "authenticity": {
            "teacher_calls_in_student_runs": teacher_calls_in_student_runs,
            "all_bank_runs_use_teacher_trace": all(bool(row["teacher_trace_hash"]) for row in bank),
            "all_raw_runs_have_no_teacher_trace": all(not row["teacher_trace_hash"] for row in raw),
            "all_executed_actions_safe": all(row["unsafe_executions"] == 0 for row in [*raw, *bank]),
            "seed_replications_are_independent_cases": False,
        },
    }


def write_live_transfer_proof(report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    root = Path(out_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "agency_live_teacher_transfer.json"
    markdown_path = root / "agency_live_teacher_transfer.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Agency Live Teacher Transfer Proof",
        "",
        f"- Teacher: `{dict(report.get('teacher') or {}).get('model', '')}`",
        f"- Compiled successful teacher steps: `{dict(report.get('teacher') or {}).get('compiled_successful_steps', 0)}`",
        f"- Teacher source stop reason: `{dict(report.get('teacher') or {}).get('source_stop_reason', '')}`",
        f"- Paired seed replications: `{report.get('paired_trials', 0)}`",
        f"- Raw successes: `{report.get('raw_successes', 0)}/{report.get('paired_trials', 0)}`",
        f"- Bank-assisted successes: `{report.get('bank_successes', 0)}/{report.get('paired_trials', 0)}`",
        f"- Teacher calls in student runs: `{dict(report.get('authenticity') or {}).get('teacher_calls_in_student_runs', 0)}`",
        f"- All executed actions safe: `{dict(report.get('authenticity') or {}).get('all_executed_actions_safe', False)}`",
        "",
        "## Interpretation",
        "",
        "The same frozen teacher trace was compiled into affordance-bound procedural capsules for each live run. "
        "These are seed replications of one task, not independent task cases; this is a live transfer signal, not a generality claim.",
        "The preserved teacher source report contains three successful actions and has stop reason `in_progress`; "
        "only those completed actions were compiled.",
    ]
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"report_json": str(json_path), "report_markdown": str(markdown_path)}
