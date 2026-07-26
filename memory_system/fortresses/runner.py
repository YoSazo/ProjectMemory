from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re
import time
from pathlib import Path
from typing import Any

from ..ollama_client import ChatMessage, UniversalLLMClient
from .coding_fortress import (
    CODING_IMPLEMENT,
    CODING_INFER_CHANGE,
    CODING_UNDERSTAND,
    CODING_VERIFY_REPAIR,
    META_TRANSFER,
    MUTATION_CROSS_DOMAIN,
    MUTATION_MUTATED,
    MUTATION_SAME,
    MUTATION_SIBLING,
    RETRIEVAL_GROUNDING,
    MUTATION_TIERS,
    TransmutationTrace,
    coding_fortress_v0_spec,
    score_transmutation_trace,
    write_trace_jsonl,
)
from .meta_fortress import GlobalTransmutationLedger, build_ledger_entry


@dataclass(frozen=True)
class CodingFortressCase:
    case_id: str
    prompt: str
    phase: str
    mutation_tier: str = MUTATION_SAME
    domain: str = "coding"
    repo_family: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    expected_constraints: list[str] = field(default_factory=list)
    expected_action_family: str = ""
    expected_verifier: list[str] = field(default_factory=list)
    expected_retrieval_sources: list[str] = field(default_factory=list)
    mutation_axes: list[str] = field(default_factory=list)
    transfer_source_case_id: str = ""

    def normalized(self) -> "CodingFortressCase":
        phase = str(self.phase or CODING_INFER_CHANGE).strip()
        mutation_tier = str(self.mutation_tier or MUTATION_SAME).strip()
        if mutation_tier not in MUTATION_TIERS:
            mutation_tier = MUTATION_SAME
        return CodingFortressCase(
            case_id=str(self.case_id or "").strip(),
            prompt=" ".join(str(self.prompt or "").split()),
            phase=phase,
            mutation_tier=mutation_tier,
            domain=str(self.domain or "coding").strip() or "coding",
            repo_family=str(self.repo_family or "").strip(),
            context=dict(self.context or {}),
            expected_constraints=[str(item).strip() for item in list(self.expected_constraints or []) if str(item).strip()],
            expected_action_family=" ".join(str(self.expected_action_family or "").strip().lower().split()),
            expected_verifier=[str(item).strip() for item in list(self.expected_verifier or []) if str(item).strip()],
            expected_retrieval_sources=[
                str(item).strip() for item in list(self.expected_retrieval_sources or []) if str(item).strip()
            ],
            mutation_axes=[str(item).strip() for item in list(self.mutation_axes or []) if str(item).strip()],
            transfer_source_case_id=str(self.transfer_source_case_id or "").strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CodingFortressCase":
        data = dict(payload or {})
        return cls(
            case_id=str(data.get("case_id") or ""),
            prompt=str(data.get("prompt") or ""),
            phase=str(data.get("phase") or CODING_INFER_CHANGE),
            mutation_tier=str(data.get("mutation_tier") or MUTATION_SAME),
            domain=str(data.get("domain") or "coding"),
            repo_family=str(data.get("repo_family") or ""),
            context=dict(data.get("context") or {}),
            expected_constraints=[str(item) for item in list(data.get("expected_constraints") or [])],
            expected_action_family=str(data.get("expected_action_family") or ""),
            expected_verifier=[str(item) for item in list(data.get("expected_verifier") or [])],
            expected_retrieval_sources=[str(item) for item in list(data.get("expected_retrieval_sources") or [])],
            mutation_axes=[str(item) for item in list(data.get("mutation_axes") or [])],
            transfer_source_case_id=str(data.get("transfer_source_case_id") or ""),
        ).normalized()


@dataclass(frozen=True)
class ModelTraceResult:
    case: CodingFortressCase
    trace: TransmutationTrace
    raw_response: str
    parse_mode: str = "json"
    residuals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case": self.case.to_dict(),
            "trace": self.trace.to_dict(),
            "raw_response": self.raw_response,
            "parse_mode": self.parse_mode,
            "residuals": list(self.residuals),
        }


def default_coding_fortress_cases() -> list[CodingFortressCase]:
    return [
        CodingFortressCase(
            case_id="understand_auth_boundary_v1",
            prompt="Understand why unauthenticated requests are reaching a protected route before proposing a patch.",
            phase=CODING_UNDERSTAND,
            repo_family="ts_backend_security",
            context={
                "repo_map": ["src/routes/account.ts", "src/middleware/auth.ts", "tests/account-auth.test.ts"],
                "symptoms": ["account route sees anonymous request", "test expects 401 before handler side effects"],
                "available_files": {
                    "src/middleware/auth.ts": "export function authGuard(req, next) { return next() }",
                    "src/routes/account.ts": "export async function accountRoute(req) { return account(req.user.id) }",
                },
            },
            expected_constraints=[
                "authentication boundary must be identified before editing",
                "caller-visible 401 behavior is the invariant",
            ],
            expected_action_family="repo boundary understanding",
            expected_verifier=["relevant file recall", "boundary symbol identified"],
        ),
        CodingFortressCase(
            case_id="infer_change_auth_boundary_mutated",
            prompt="Repair the login guard so unauthenticated API callers stop before the endpoint, even though files were renamed.",
            phase=CODING_INFER_CHANGE,
            mutation_tier=MUTATION_MUTATED,
            repo_family="ts_backend_security",
            context={
                "mutation_axes": ["renamed middleware file", "prompt paraphrase", "test moved"],
                "candidate_files": ["app/http_guard.ts", "app/account_endpoint.ts", "test/auth_boundary.test.ts"],
                "observations": ["endpoint currently checks user after doing work", "guard file wraps all API requests"],
            },
            expected_constraints=[
                "authentication boundary is enforced before handler execution",
                "public caller contract remains stable",
            ],
            expected_action_family="early boundary enforcement",
            expected_verifier=["auth rejection test", "regression test"],
        ),
        CodingFortressCase(
            case_id="infer_change_cli_schema_sibling",
            prompt="A CLI accepts malformed JSON config and fails later; figure out the right change before editing.",
            phase=CODING_INFER_CHANGE,
            mutation_tier=MUTATION_SIBLING,
            repo_family="python_cli",
            context={
                "sibling_of": "early boundary enforcement",
                "candidate_files": ["memory_system/cli.py", "memory_system/config_schema.py", "tests/test_cli_config.py"],
                "observations": ["invalid config reaches execution path", "tests expect early error message"],
            },
            expected_constraints=[
                "input schema is validated before execution",
                "CLI contract returns stable early error",
            ],
            expected_action_family="early boundary enforcement",
            expected_verifier=["cli malformed config test"],
        ),
        CodingFortressCase(
            case_id="implement_schema_validation_v1",
            prompt="Implement the smallest patch that validates an OpenAPI payload before service execution.",
            phase=CODING_IMPLEMENT,
            repo_family="python_api",
            context={
                "allowed_files": ["app/routes/orders.py", "app/schemas/order.py", "tests/test_order_schema.py"],
                "selected_transmutation": "Trade loose input handling for stricter schema-driven validation.",
                "style_constraints": ["use existing pydantic models", "do not change response shape"],
            },
            expected_constraints=[
                "schema validation happens before service execution",
                "external API response contract is preserved",
            ],
            expected_action_family="minimal structured edit",
            expected_verifier=["schema validation test", "API contract regression"],
        ),
        CodingFortressCase(
            case_id="verify_repair_callback_payload_v1",
            prompt="The patch applies but OAuth callback tests fail because the payload shape changed; repair from verifier output.",
            phase=CODING_VERIFY_REPAIR,
            repo_family="python_api",
            context={
                "verifier_output": "AssertionError: expected callback_state['next_url']; got callback_state['redirect']",
                "patch_files": ["app/oauth/callback.py"],
                "residuals": ["provider callback payload contract changed"],
            },
            expected_constraints=[
                "provider callback payload contract is restored",
                "repair targets the failing assertion not unrelated auth code",
            ],
            expected_action_family="residual constraint repair",
            expected_verifier=["oauth callback regression"],
        ),
        CodingFortressCase(
            case_id="retrieval_sdk_webhook_docs_v1",
            prompt="Find how the current SDK validates webhook signatures before deciding the patch.",
            phase=RETRIEVAL_GROUNDING,
            mutation_tier=MUTATION_MUTATED,
            repo_family="ts_backend_security",
            context={
                "missing_knowledge": ["current SDK helper name", "signature header contract", "version-specific docs"],
                "bad_sources": ["old blog post", "StackOverflow answer for previous SDK major"],
                "desired_sources": ["official SDK docs", "release notes", "installed package source"],
            },
            expected_constraints=[
                "webhook signature verification uses official version-matched SDK helper",
                "stale examples are rejected",
            ],
            expected_action_family="official source grounding",
            expected_verifier=["source authority", "version match", "retrieved helper appears in source"],
            expected_retrieval_sources=["official SDK docs", "release notes"],
        ),
        CodingFortressCase(
            case_id="cross_domain_checkout_boundary_v1",
            prompt="Transfer the boundary idea to a browser workflow: get to checkout but stop before payment confirmation.",
            phase=META_TRANSFER,
            mutation_tier=MUTATION_CROSS_DOMAIN,
            domain="browser_workflow",
            repo_family="commerce_flow",
            context={
                "source_transmutation": "early boundary enforcement",
                "workflow": ["search restaurant", "select item", "customize", "cart", "checkout", "payment"],
                "hard_stop": "do not submit order or payment",
            },
            expected_constraints=[
                "irreversible payment boundary is identified before final action",
                "safe stop occurs at confirmation screen",
            ],
            expected_action_family="confirmation boundary enforcement",
            expected_verifier=["no payment submitted", "checkout screen reached"],
            transfer_source_case_id="infer_change_auth_boundary_mutated",
        ),
        CodingFortressCase(
            case_id="understand_async_cache_race_v1",
            prompt="Understand why a cached async profile endpoint sometimes returns a previous user's data before proposing a fix.",
            phase=CODING_UNDERSTAND,
            repo_family="python_async_api",
            context={
                "repo_map": ["app/profile.py", "app/cache.py", "tests/test_profile_cache.py"],
                "symptoms": ["intermittent cross-user response", "test fails only when two requests overlap"],
                "available_files": {
                    "app/cache.py": "profile_cache = {}",
                    "app/profile.py": "return await get_or_set('profile', load_profile)",
                },
            },
            expected_constraints=[
                "cache key must include the user identity boundary",
                "concurrent requests must not share mutable user payloads",
            ],
            expected_action_family="identity-scoped state understanding",
            expected_verifier=["race reproduction test", "cache key symbol identified"],
        ),
        CodingFortressCase(
            case_id="understand_migration_contract_v1",
            prompt="Understand a data migration that passes locally but violates an existing nullable-column contract in production.",
            phase=CODING_UNDERSTAND,
            mutation_tier=MUTATION_MUTATED,
            repo_family="rails_data_migration",
            context={
                "repo_map": ["db/migrate/20260701010101_backfill_status.rb", "app/models/order.rb", "spec/migrations/status_spec.rb"],
                "symptoms": ["production rows have NULL status", "model validation assumes legacy imports can be blank"],
                "observations": ["migration backfills only active orders", "new index rejects NULL later"],
            },
            expected_constraints=[
                "legacy nullable data contract is mapped before schema tightening",
                "migration ordering preserves production rows",
            ],
            expected_action_family="migration invariant mapping",
            expected_verifier=["migration replay with null fixtures", "schema contract check"],
        ),
        CodingFortressCase(
            case_id="infer_change_cache_ttl_mutated",
            prompt="A renamed cache layer returns stale authorization decisions; infer the correct change without over-invalidating everything.",
            phase=CODING_INFER_CHANGE,
            mutation_tier=MUTATION_MUTATED,
            repo_family="go_service_authz",
            context={
                "mutation_axes": ["renamed cache module", "policy object renamed", "TTL moved to config"],
                "candidate_files": ["internal/decision_cache.go", "internal/policy_eval.go", "tests/authz_cache_test.go"],
                "observations": ["policy updates should take effect quickly", "cache stampede protection is still needed"],
            },
            expected_constraints=[
                "authorization cache invalidates on policy version changes",
                "stampede protection is preserved while stale decisions are bounded",
            ],
            expected_action_family="versioned cache invalidation",
            expected_verifier=["policy update invalidation test", "cache concurrency regression"],
        ),
        CodingFortressCase(
            case_id="infer_change_public_api_contract_sibling",
            prompt="An API refactor changed a public response field name; infer the smallest compatibility-preserving change.",
            phase=CODING_INFER_CHANGE,
            mutation_tier=MUTATION_SIBLING,
            repo_family="node_public_api",
            context={
                "sibling_of": "provider callback payload contract",
                "candidate_files": ["src/orders/serializer.ts", "src/orders/controller.ts", "tests/orders.contract.test.ts"],
                "observations": ["internal model renamed total_cents", "external clients still expect total"],
            },
            expected_constraints=[
                "public response field contract is preserved",
                "internal rename does not leak to external clients",
            ],
            expected_action_family="compatibility wrapper repair",
            expected_verifier=["public contract test", "serializer regression"],
        ),
        CodingFortressCase(
            case_id="implement_idempotency_guard_v1",
            prompt="Implement an idempotency guard for a payment callback using the repo's existing persistence pattern.",
            phase=CODING_IMPLEMENT,
            mutation_tier=MUTATION_MUTATED,
            repo_family="python_payments",
            context={
                "allowed_files": ["app/payments/callback.py", "app/payments/models.py", "tests/test_payment_callbacks.py"],
                "selected_transmutation": "Trade replay-prone side effects for keyed idempotent callback handling.",
                "style_constraints": ["use existing transaction helper", "do not alter provider response status"],
            },
            expected_constraints=[
                "payment side effect is committed at most once per provider event id",
                "provider-visible callback response stays compatible",
            ],
            expected_action_family="idempotent side-effect guard",
            expected_verifier=["duplicate callback test", "provider response contract regression"],
        ),
        CodingFortressCase(
            case_id="implement_feature_flag_scope_v1",
            prompt="Implement a feature flag check so the new serializer is only used for opted-in tenants.",
            phase=CODING_IMPLEMENT,
            mutation_tier=MUTATION_SIBLING,
            repo_family="multi_tenant_saas",
            context={
                "allowed_files": ["app/serializers/invoice.py", "app/flags.py", "tests/test_invoice_flags.py"],
                "selected_transmutation": "Trade global rollout for tenant-scoped constraint gating.",
                "style_constraints": ["use existing flag helper", "avoid branching in every caller"],
            },
            expected_constraints=[
                "new behavior is gated by tenant feature flag",
                "default tenant behavior is unchanged",
            ],
            expected_action_family="scoped rollout guard",
            expected_verifier=["flagged tenant test", "default tenant regression"],
        ),
        CodingFortressCase(
            case_id="verify_repair_timezone_boundary_v1",
            prompt="A date-boundary patch passes unit tests but fails integration because midnight is evaluated in UTC instead of tenant time.",
            phase=CODING_VERIFY_REPAIR,
            mutation_tier=MUTATION_MUTATED,
            repo_family="python_scheduling",
            context={
                "verifier_output": "expected renewal date 2026-03-09 America/Chicago; got 2026-03-10 UTC",
                "patch_files": ["app/billing/renewal.py", "tests/test_renewal_timezone.py"],
                "residuals": ["tenant timezone contract was not applied at date boundary"],
            },
            expected_constraints=[
                "tenant timezone defines the date boundary",
                "UTC conversion happens after local renewal date selection",
            ],
            expected_action_family="verifier-localized repair",
            expected_verifier=["timezone integration test", "DST boundary regression"],
        ),
        CodingFortressCase(
            case_id="verify_repair_import_cycle_v1",
            prompt="The behavior patch is correct but tests fail on an import cycle; repair structure without changing the new contract.",
            phase=CODING_VERIFY_REPAIR,
            mutation_tier=MUTATION_SIBLING,
            repo_family="python_package",
            context={
                "verifier_output": "ImportError: cannot import name 'Policy' from partially initialized module",
                "patch_files": ["app/policy/__init__.py", "app/policy/evaluator.py"],
                "residuals": ["new helper import introduced cycle"],
            },
            expected_constraints=[
                "public behavior contract remains unchanged",
                "dependency direction is restored to avoid import cycle",
            ],
            expected_action_family="structural residual repair",
            expected_verifier=["import smoke test", "original behavior regression"],
        ),
        CodingFortressCase(
            case_id="retrieval_auth_library_version_v1",
            prompt="Find the version-correct way to verify JWT audience claims for the installed auth library before patching.",
            phase=RETRIEVAL_GROUNDING,
            mutation_tier=MUTATION_MUTATED,
            repo_family="python_api_security",
            context={
                "missing_knowledge": ["installed library major version", "audience verification helper", "exception contract"],
                "bad_sources": ["tutorial for old major", "blog that disables verification"],
                "desired_sources": ["installed package source", "official library docs", "changelog"],
            },
            expected_constraints=[
                "JWT audience verification follows the installed library version",
                "examples that disable verification are rejected",
            ],
            expected_action_family="version-matched auth retrieval",
            expected_verifier=["installed version check", "official helper match", "negative source rejection"],
            expected_retrieval_sources=["installed package source", "official library docs", "changelog"],
        ),
        CodingFortressCase(
            case_id="retrieval_framework_migration_v1",
            prompt="Search how the current framework version replaced a deprecated routing hook and decide the safe migration path.",
            phase=RETRIEVAL_GROUNDING,
            mutation_tier=MUTATION_MUTATED,
            repo_family="web_framework_migration",
            context={
                "missing_knowledge": ["replacement hook name", "deprecation version", "migration caveats"],
                "bad_sources": ["pre-release discussion", "answer for previous router"],
                "desired_sources": ["official migration guide", "release notes", "current API reference"],
            },
            expected_constraints=[
                "replacement hook is supported by the current framework version",
                "migration preserves route matching semantics",
            ],
            expected_action_family="migration-guide grounding",
            expected_verifier=["current API reference match", "route behavior regression"],
            expected_retrieval_sources=["official migration guide", "release notes", "current API reference"],
        ),
        CodingFortressCase(
            case_id="retrieval_cve_patch_advisory_v1",
            prompt="Find the minimum secure dependency upgrade for a CVE without jumping across a major version unnecessarily.",
            phase=RETRIEVAL_GROUNDING,
            mutation_tier=MUTATION_SIBLING,
            repo_family="dependency_security",
            context={
                "missing_knowledge": ["affected version range", "patched version range", "breaking changes"],
                "bad_sources": ["generic vulnerability scanner summary without patch range"],
                "desired_sources": ["vendor security advisory", "package release notes", "lockfile"],
            },
            expected_constraints=[
                "upgrade target is inside patched non-breaking version range when possible",
                "security advisory outranks generic summaries",
            ],
            expected_action_family="advisory-grounded upgrade",
            expected_verifier=["patched range evidence", "lockfile update check", "security regression"],
            expected_retrieval_sources=["vendor security advisory", "package release notes", "lockfile"],
        ),
        CodingFortressCase(
            case_id="retrieval_error_message_source_v1",
            prompt="Use an unfamiliar runtime error message to find the real failing subsystem before editing code.",
            phase=RETRIEVAL_GROUNDING,
            mutation_tier=MUTATION_MUTATED,
            repo_family="python_runtime",
            context={
                "missing_knowledge": ["error provenance", "library issue thread", "known workaround"],
                "bad_sources": ["unrelated issue with same words", "AI-generated snippet"],
                "desired_sources": ["official issue tracker", "library docs", "local stack trace"],
            },
            expected_constraints=[
                "error message is tied to the correct library and version",
                "local stack trace remains the grounding anchor",
            ],
            expected_action_family="error-provenance retrieval",
            expected_verifier=["stack trace frame match", "version-specific issue match"],
            expected_retrieval_sources=["official issue tracker", "library docs", "local stack trace"],
        ),
        CodingFortressCase(
            case_id="retrieval_package_source_truth_v1",
            prompt="Docs disagree with installed behavior; inspect local package source to decide what patch is valid.",
            phase=RETRIEVAL_GROUNDING,
            mutation_tier=MUTATION_SIBLING,
            repo_family="python_sdk_integration",
            context={
                "missing_knowledge": ["installed function signature", "runtime defaults", "doc/source mismatch"],
                "bad_sources": ["latest docs for a newer version"],
                "desired_sources": ["installed package source", "package metadata", "versioned docs"],
            },
            expected_constraints=[
                "installed package source outranks latest unversioned docs",
                "patch matches runtime signature actually present locally",
            ],
            expected_action_family="local-source grounding",
            expected_verifier=["local source signature match", "installed metadata check"],
            expected_retrieval_sources=["installed package source", "package metadata", "versioned docs"],
        ),
        CodingFortressCase(
            case_id="retrieval_test_pattern_official_v1",
            prompt="Find the official testing pattern for mocking a streaming API without copying outdated community snippets.",
            phase=RETRIEVAL_GROUNDING,
            mutation_tier=MUTATION_MUTATED,
            repo_family="python_streaming_api",
            context={
                "missing_knowledge": ["stream mock object shape", "async iterator contract", "test helper availability"],
                "bad_sources": ["gist for old sync client", "StackOverflow answer with sleeps"],
                "desired_sources": ["official SDK test docs", "SDK examples", "installed test helpers"],
            },
            expected_constraints=[
                "mock preserves async streaming contract",
                "official SDK testing pattern replaces timing-based snippets",
            ],
            expected_action_family="official testing-pattern retrieval",
            expected_verifier=["async stream unit test", "no sleep-based verifier"],
            expected_retrieval_sources=["official SDK test docs", "SDK examples", "installed test helpers"],
        ),
        CodingFortressCase(
            case_id="retrieval_api_limits_contract_v1",
            prompt="Find current API rate-limit and pagination rules before changing a sync job that drops records.",
            phase=RETRIEVAL_GROUNDING,
            mutation_tier=MUTATION_MUTATED,
            repo_family="data_sync_job",
            context={
                "missing_knowledge": ["current page token contract", "rate limit headers", "retry-after semantics"],
                "bad_sources": ["pricing page summary", "SDK v1 example"],
                "desired_sources": ["official API reference", "rate limit docs", "SDK source"],
            },
            expected_constraints=[
                "pagination follows the current API token contract",
                "rate limit handling respects retry-after semantics",
            ],
            expected_action_family="API contract retrieval",
            expected_verifier=["pagination fixture", "rate-limit retry test"],
            expected_retrieval_sources=["official API reference", "rate limit docs", "SDK source"],
        ),
        CodingFortressCase(
            case_id="cross_domain_email_send_boundary_v1",
            prompt="Transfer irreversible-boundary reasoning to an email workflow: prepare the campaign but stop before sending.",
            phase=META_TRANSFER,
            mutation_tier=MUTATION_CROSS_DOMAIN,
            domain="business_workflow",
            repo_family="marketing_ops",
            context={
                "source_transmutation": "confirmation boundary enforcement",
                "workflow": ["select audience", "edit template", "preview", "schedule", "send"],
                "hard_stop": "do not send or schedule the campaign",
            },
            expected_constraints=[
                "irreversible send boundary is identified before final action",
                "safe stop occurs at preview or unsent confirmation",
            ],
            expected_action_family="irreversible action boundary",
            expected_verifier=["campaign not sent", "preview reached"],
            transfer_source_case_id="cross_domain_checkout_boundary_v1",
        ),
        CodingFortressCase(
            case_id="cross_domain_file_delete_boundary_v1",
            prompt="Transfer destructive-action reasoning to a file cleanup workflow: identify delete candidates but stop before removal.",
            phase=META_TRANSFER,
            mutation_tier=MUTATION_CROSS_DOMAIN,
            domain="terminal_workflow",
            repo_family="ops_cleanup",
            context={
                "source_transmutation": "irreversible action boundary",
                "workflow": ["scan files", "rank stale candidates", "show deletion plan", "delete"],
                "hard_stop": "do not remove files",
            },
            expected_constraints=[
                "destructive filesystem boundary is explicit before action",
                "candidate list is produced without deletion",
            ],
            expected_action_family="destructive action boundary",
            expected_verifier=["no files removed", "candidate plan produced"],
            transfer_source_case_id="cross_domain_email_send_boundary_v1",
        ),
    ]


def load_coding_fortress_cases(path: str | Path) -> list[CodingFortressCase]:
    target = Path(path).expanduser().resolve()
    cases: list[CodingFortressCase] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if clean:
            cases.append(CodingFortressCase.from_dict(json.loads(clean)))
    return cases


def write_coding_fortress_cases(path: str | Path, cases: list[CodingFortressCase]) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(case.to_dict(), ensure_ascii=True) for case in cases]
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return target


def _extract_json_object(text: str) -> tuple[dict[str, Any], str]:
    clean = str(text or "").strip()
    if not clean:
        return {}, "empty"
    try:
        data = json.loads(clean)
        return (data if isinstance(data, dict) else {}), "json"
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
    if not match:
        return {}, "no_json"
    blob = re.sub(r",(\s*[}\]])", r"\1", match.group(0))
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return {}, "invalid_json"
    return (data if isinstance(data, dict) else {}), "json_recovered"


def _phase_contract(phase: str) -> dict[str, Any]:
    spec = coding_fortress_v0_spec()
    for item in spec["phases"]:
        if item["phase"] == phase:
            return dict(item)
    return dict(spec["phases"][1])


def _system_prompt() -> str:
    return (
        "You are inside a Memla coding fortress. Emit observable constraint transmutation traces, "
        "not hidden chain-of-thought and not a final patch.\n"
        "Return strict JSON only. The trace must explain constraint motion that can be verified, mutated, and transferred.\n"
        "Do not include markdown fences. Do not include prose outside JSON."
    )


def build_trace_messages(case: CodingFortressCase, *, lane: str) -> list[ChatMessage]:
    normalized = case.normalized()
    contract = _phase_contract(normalized.phase)
    schema = {
        "constraints_before": ["current hard constraint before the move"],
        "constraints_after": ["new or tightened constraint after the move"],
        "observations": ["repo/source/verifier observation"],
        "preconditions": ["when this transmutation is valid"],
        "transmutation": "Trade weaker constraint handling for stronger constraint handling.",
        "action_family": "short canonical action family",
        "target_artifacts": ["repo/path.py or external source"],
        "retrieval_queries": ["query if external knowledge is needed"],
        "retrieval_sources": ["official docs or source categories"],
        "verifier": ["test, check, or evidence that validates the move"],
        "residual_constraints": ["remaining blocker if any"],
        "outcome": "success|failed|unknown",
    }
    user_payload = {
        "lane": lane,
        "case": normalized.to_dict(),
        "phase_contract": contract,
        "output_schema": schema,
        "scoring_reminder": [
            "prefer reusable constraint transformations over task-specific phrasing",
            "include retrieval behavior when missing knowledge matters",
            "include negative preconditions or residual constraints when transfer is unsafe",
            "success means the transmutation is valid under the stated verifier, not that code was patched",
        ],
    }
    return [
        ChatMessage(role="system", content=_system_prompt()),
        ChatMessage(role="user", content=json.dumps(user_payload, indent=2, sort_keys=True)),
    ]


def estimate_trace_prompt_tokens(case: CodingFortressCase, *, lane: str = "teacher") -> int:
    messages = build_trace_messages(case, lane=lane)
    char_count = sum(len(message.content) for message in messages)
    return max(1, int((char_count + 3) // 4))


def summarize_coding_fortress_cases(
    cases: list[CodingFortressCase] | None = None,
    *,
    cases_path: str = "",
) -> dict[str, Any]:
    selected_cases = load_coding_fortress_cases(cases_path) if cases_path else list(cases or default_coding_fortress_cases())
    normalized_cases = [case.normalized() for case in selected_cases]

    def _counts(values: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for value in values:
            key = value or "unknown"
            counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items()))

    teacher_prompt_tokens = [estimate_trace_prompt_tokens(case, lane="teacher") for case in normalized_cases]
    student_prompt_tokens = [estimate_trace_prompt_tokens(case, lane="student") for case in normalized_cases]
    retrieval_cases = [case for case in normalized_cases if case.phase == RETRIEVAL_GROUNDING]
    transfer_cases = [case for case in normalized_cases if case.phase == META_TRANSFER]
    estimated_output_tokens_per_lane = 520
    total_teacher_input = sum(teacher_prompt_tokens)
    total_student_input = sum(student_prompt_tokens)
    return {
        "case_count": len(normalized_cases),
        "phase_counts": _counts([case.phase for case in normalized_cases]),
        "mutation_tier_counts": _counts([case.mutation_tier for case in normalized_cases]),
        "domain_counts": _counts([case.domain for case in normalized_cases]),
        "repo_family_counts": _counts([case.repo_family for case in normalized_cases]),
        "retrieval_case_count": len(retrieval_cases),
        "cross_domain_transfer_case_count": len(transfer_cases),
        "avg_teacher_prompt_tokens": round(sum(teacher_prompt_tokens) / len(teacher_prompt_tokens), 1)
        if teacher_prompt_tokens
        else 0.0,
        "avg_student_prompt_tokens": round(sum(student_prompt_tokens) / len(student_prompt_tokens), 1)
        if student_prompt_tokens
        else 0.0,
        "estimated_teacher_input_tokens": total_teacher_input,
        "estimated_student_input_tokens": total_student_input,
        "estimated_input_tokens_two_lanes": total_teacher_input + total_student_input,
        "estimated_output_tokens_two_lanes": len(normalized_cases) * estimated_output_tokens_per_lane * 2,
        "estimated_total_tokens_two_lanes": total_teacher_input
        + total_student_input
        + len(normalized_cases) * estimated_output_tokens_per_lane * 2,
        "retrieval_case_ids": [case.case_id for case in retrieval_cases],
        "case_ids": [case.case_id for case in normalized_cases],
    }


def _coerce_trace(
    *,
    case: CodingFortressCase,
    model: str,
    payload: dict[str, Any],
    lane: str,
) -> tuple[TransmutationTrace, list[str]]:
    normalized = case.normalized()
    residuals: list[str] = []
    def _list(key: str) -> list[str]:
        raw = payload.get(key)
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        if isinstance(raw, str) and raw.strip():
            return [raw.strip()]
        return []

    if not payload:
        residuals.append("missing_trace_payload")
    constraints_after = _list("constraints_after") or list(normalized.expected_constraints)
    action_family = str(payload.get("action_family") or "").strip() or normalized.expected_action_family
    verifier = _list("verifier") or list(normalized.expected_verifier)
    retrieval_sources = _list("retrieval_sources") or list(normalized.expected_retrieval_sources)
    trace = TransmutationTrace(
        trace_id=str(payload.get("trace_id") or f"{lane}_{normalized.case_id}"),
        fortress_id=str(payload.get("fortress_id") or "coding_fortress_v0"),
        phase=str(payload.get("phase") or normalized.phase),
        model=model,
        prompt=normalized.prompt,
        constraints_before=_list("constraints_before"),
        constraints_after=constraints_after,
        observations=_list("observations"),
        preconditions=_list("preconditions"),
        transmutation=str(payload.get("transmutation") or "").strip()
        or f"Apply {action_family or 'the selected transmutation'} to satisfy {', '.join(constraints_after[:2])}.",
        action_family=action_family,
        target_artifacts=_list("target_artifacts"),
        retrieval_queries=_list("retrieval_queries"),
        retrieval_sources=retrieval_sources,
        verifier=verifier,
        residual_constraints=_list("residual_constraints"),
        outcome=str(payload.get("outcome") or "unknown"),
        mutation_tier=normalized.mutation_tier,
        domain=normalized.domain,
        repo_family=normalized.repo_family,
        source_trace_id=normalized.transfer_source_case_id,
        metadata={"case_id": normalized.case_id, "lane": lane, "mutation_axes": list(normalized.mutation_axes)},
    ).normalized()
    if not trace.constraints_before:
        residuals.append("missing_constraints_before")
    if not trace.preconditions:
        residuals.append("missing_preconditions")
    if not trace.transmutation:
        residuals.append("missing_transmutation")
    return trace, residuals


def run_model_trace(
    *,
    client: UniversalLLMClient,
    model: str,
    case: CodingFortressCase,
    lane: str,
    temperature: float = 0.1,
    num_ctx: int | None = None,
) -> ModelTraceResult:
    messages = build_trace_messages(case, lane=lane)
    raw = client.chat(model=model, messages=messages, temperature=temperature, num_ctx=num_ctx).strip()
    payload, parse_mode = _extract_json_object(raw)
    trace, residuals = _coerce_trace(case=case, model=model, payload=payload, lane=lane)
    return ModelTraceResult(case=case.normalized(), trace=trace, raw_response=raw, parse_mode=parse_mode, residuals=residuals)


def run_coding_fortress_benchmark(
    *,
    cases: list[CodingFortressCase] | None = None,
    cases_path: str = "",
    teacher_model: str,
    student_model: str,
    teacher_client: UniversalLLMClient,
    student_client: UniversalLLMClient,
    temperature: float = 0.1,
    num_ctx: int | None = None,
    limit: int = 0,
) -> dict[str, Any]:
    selected_cases = load_coding_fortress_cases(cases_path) if cases_path else list(cases or default_coding_fortress_cases())
    if limit:
        selected_cases = selected_cases[: max(int(limit), 0)]
    case_summary = summarize_coding_fortress_cases(selected_cases)

    teacher_results: list[ModelTraceResult] = []
    student_results: list[ModelTraceResult] = []
    score_rows: list[dict[str, Any]] = []
    ledger = GlobalTransmutationLedger()
    failures: list[dict[str, Any]] = []

    for case in selected_cases:
        normalized = case.normalized()
        try:
            teacher_result = run_model_trace(
                client=teacher_client,
                model=teacher_model,
                case=normalized,
                lane="teacher",
                temperature=temperature,
                num_ctx=num_ctx,
            )
            student_result = run_model_trace(
                client=student_client,
                model=student_model,
                case=normalized,
                lane="student",
                temperature=temperature,
                num_ctx=num_ctx,
            )
            score = score_transmutation_trace(teacher_result.trace, student_result.trace)
            entry = build_ledger_entry(
                teacher_trace=teacher_result.trace,
                student_trace=student_result.trace,
                score=score,
                target_fortress=student_result.trace.fortress_id,
                target_phase=student_result.trace.phase,
            )
            ledger.add_entry(entry)
            teacher_results.append(teacher_result)
            student_results.append(student_result)
            score_rows.append(
                {
                    "case_id": normalized.case_id,
                    "phase": normalized.phase,
                    "mutation_tier": normalized.mutation_tier,
                    "domain": normalized.domain,
                    "repo_family": normalized.repo_family,
                    "teacher_trace": teacher_result.trace.to_dict(),
                    "student_trace": student_result.trace.to_dict(),
                    "teacher_parse_mode": teacher_result.parse_mode,
                    "student_parse_mode": student_result.parse_mode,
                    "teacher_residuals": list(teacher_result.residuals),
                    "student_residuals": list(student_result.residuals),
                    "score": score.to_dict(),
                    "ledger_entry": entry.to_dict(),
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "case_id": normalized.case_id,
                    "phase": normalized.phase,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    weighted_scores = [float(row["score"]["weighted_score"]) for row in score_rows]
    avg_score = round(sum(weighted_scores) / len(weighted_scores), 4) if weighted_scores else 0.0
    negative_count = sum(1 for row in score_rows if bool(row["score"]["negative_transfer"]))
    decisions = ledger.promotion_decisions()
    return {
        "generated_ts": int(time.time()),
        "case_count": len(selected_cases),
        "completed_case_count": len(score_rows),
        "failure_count": len(failures),
        "teacher_model": teacher_model,
        "student_model": student_model,
        "case_summary": case_summary,
        "avg_weighted_score": avg_score,
        "negative_transfer_count": negative_count,
        "ledger_summary": ledger.summarize(),
        "promotion_decisions": [decision.to_dict() for decision in decisions],
        "active_rule_count": sum(1 for decision in decisions if decision.promote),
        "rows": score_rows,
        "failures": failures,
    }


def run_coding_fortress_extraction(
    *,
    cases: list[CodingFortressCase] | None = None,
    cases_path: str = "",
    teacher_model: str,
    teacher_client: UniversalLLMClient,
    temperature: float = 0.1,
    num_ctx: int | None = None,
    limit: int = 0,
) -> dict[str, Any]:
    selected_cases = load_coding_fortress_cases(cases_path) if cases_path else list(cases or default_coding_fortress_cases())
    if limit:
        selected_cases = selected_cases[: max(int(limit), 0)]
    case_summary = summarize_coding_fortress_cases(selected_cases)

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for case in selected_cases:
        normalized = case.normalized()
        try:
            teacher_result = run_model_trace(
                client=teacher_client,
                model=teacher_model,
                case=normalized,
                lane="teacher",
                temperature=temperature,
                num_ctx=num_ctx,
            )
            rows.append(
                {
                    "case_id": normalized.case_id,
                    "phase": normalized.phase,
                    "mutation_tier": normalized.mutation_tier,
                    "domain": normalized.domain,
                    "repo_family": normalized.repo_family,
                    "teacher_trace": teacher_result.trace.to_dict(),
                    "teacher_parse_mode": teacher_result.parse_mode,
                    "teacher_residuals": list(teacher_result.residuals),
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "case_id": normalized.case_id,
                    "phase": normalized.phase,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    residual_count = sum(len(row.get("teacher_residuals") or []) for row in rows)
    return {
        "generated_ts": int(time.time()),
        "case_count": len(selected_cases),
        "completed_case_count": len(rows),
        "failure_count": len(failures),
        "teacher_model": teacher_model,
        "case_summary": case_summary,
        "teacher_residual_count": residual_count,
        "rows": rows,
        "failures": failures,
    }


def write_coding_fortress_artifacts(*, report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "coding_fortress_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = out / "coding_fortress_report.md"
    markdown_path.write_text(render_coding_fortress_markdown(report), encoding="utf-8")
    teacher_traces = [TransmutationTrace.from_dict(row["teacher_trace"]) for row in report.get("rows", [])]
    student_traces = [TransmutationTrace.from_dict(row["student_trace"]) for row in report.get("rows", [])]
    teacher_path = write_trace_jsonl(out / "teacher_traces.jsonl", teacher_traces)
    student_path = write_trace_jsonl(out / "student_traces.jsonl", student_traces)
    ledger = GlobalTransmutationLedger(
        [build_ledger_entry(
            teacher_trace=TransmutationTrace.from_dict(row["teacher_trace"]),
            student_trace=TransmutationTrace.from_dict(row["student_trace"]),
            score=score_transmutation_trace(
                TransmutationTrace.from_dict(row["teacher_trace"]),
                TransmutationTrace.from_dict(row["student_trace"]),
            ),
        ) for row in report.get("rows", [])]
    )
    ledger_path = ledger.write_json(out / "global_transmutation_ledger.json")
    return {
        "report_json": str(report_path),
        "report_markdown": str(markdown_path),
        "teacher_traces_jsonl": str(teacher_path),
        "student_traces_jsonl": str(student_path),
        "ledger_json": str(ledger_path),
    }


def write_coding_fortress_extraction_artifacts(*, report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "coding_fortress_extraction_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = out / "coding_fortress_extraction_report.md"
    markdown_path.write_text(render_coding_fortress_extraction_markdown(report), encoding="utf-8")
    teacher_traces = [TransmutationTrace.from_dict(row["teacher_trace"]) for row in report.get("rows", [])]
    teacher_path = write_trace_jsonl(out / "teacher_traces.jsonl", teacher_traces)
    return {
        "report_json": str(report_path),
        "report_markdown": str(markdown_path),
        "teacher_traces_jsonl": str(teacher_path),
    }


def render_coding_fortress_markdown(report: dict[str, Any]) -> str:
    case_summary = dict(report.get("case_summary") or {})
    lines = [
        "# Coding Fortress Report",
        "",
        f"- Teacher model: `{report.get('teacher_model', '')}`",
        f"- Student model: `{report.get('student_model', '')}`",
        f"- Cases: `{report.get('completed_case_count', 0)}/{report.get('case_count', 0)}`",
        f"- Avg weighted score: `{report.get('avg_weighted_score', 0.0)}`",
        f"- Negative transfer count: `{report.get('negative_transfer_count', 0)}`",
        f"- Active rule count: `{report.get('active_rule_count', 0)}`",
        f"- Retrieval cases: `{case_summary.get('retrieval_case_count', 0)}`",
        f"- Estimated total tokens, two lanes: `{case_summary.get('estimated_total_tokens_two_lanes', 0)}`",
        "",
        "## Rows",
        "",
    ]
    for row in report.get("rows", []):
        score = dict(row.get("score") or {})
        teacher = dict(row.get("teacher_trace") or {})
        student = dict(row.get("student_trace") or {})
        lines.extend(
            [
                f"### {row.get('case_id', '')}",
                "",
                f"- Phase: `{row.get('phase', '')}`",
                f"- Mutation tier: `{row.get('mutation_tier', '')}`",
                f"- Score: `{score.get('weighted_score', 0.0)}`",
                f"- Transmutation similarity: `{score.get('transmutation_similarity', 0.0)}`",
                f"- Negative transfer: `{score.get('negative_transfer', False)}`",
                f"- Teacher move: {teacher.get('transmutation', '')}",
                f"- Student move: {student.get('transmutation', '')}",
                "",
            ]
        )
    failures = list(report.get("failures") or [])
    if failures:
        lines.extend(["## Failures", ""])
        for failure in failures:
            lines.append(f"- `{failure.get('case_id', '')}` {failure.get('error_type', '')}: {failure.get('message', '')}")
    return "\n".join(lines).strip() + "\n"


def render_coding_fortress_extraction_markdown(report: dict[str, Any]) -> str:
    case_summary = dict(report.get("case_summary") or {})
    lines = [
        "# Coding Fortress Extraction Report",
        "",
        f"- Teacher model: `{report.get('teacher_model', '')}`",
        f"- Cases: `{report.get('completed_case_count', 0)}/{report.get('case_count', 0)}`",
        f"- Retrieval cases: `{case_summary.get('retrieval_case_count', 0)}`",
        f"- Teacher residual count: `{report.get('teacher_residual_count', 0)}`",
        f"- Estimated teacher input tokens: `{case_summary.get('estimated_teacher_input_tokens', 0)}`",
        "",
        "## Traces",
        "",
    ]
    for row in report.get("rows", []):
        trace = dict(row.get("teacher_trace") or {})
        lines.extend(
            [
                f"### {row.get('case_id', '')}",
                "",
                f"- Phase: `{row.get('phase', '')}`",
                f"- Mutation tier: `{row.get('mutation_tier', '')}`",
                f"- Action family: `{trace.get('action_family', '')}`",
                f"- Transmutation: {trace.get('transmutation', '')}",
                "",
            ]
        )
    failures = list(report.get("failures") or [])
    if failures:
        lines.extend(["## Failures", ""])
        for failure in failures:
            lines.append(f"- `{failure.get('case_id', '')}` {failure.get('error_type', '')}: {failure.get('message', '')}")
    return "\n".join(lines).strip() + "\n"
