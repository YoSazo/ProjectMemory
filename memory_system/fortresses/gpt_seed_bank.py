from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .coding_fortress import (
    CODING_IMPLEMENT,
    CODING_INFER_CHANGE,
    CODING_UNDERSTAND,
    CODING_VERIFY_REPAIR,
    META_TRANSFER,
    RETRIEVAL_GROUNDING,
    TransmutationTrace,
)
from .runner import (
    CodingFortressCase,
    default_coding_fortress_cases,
    load_coding_fortress_cases,
    summarize_coding_fortress_cases,
    write_coding_fortress_extraction_artifacts,
)


GPT_SEED_MODEL = "codex-gpt5-seed"
GPT_SEED_BANK_ID = "gpt_seed_coding_fortress_v0"


_SEED_OVERRIDES: dict[str, dict[str, Any]] = {
    "understand_auth_boundary_v1": {
        "constraints_before": [
            "the route handler is being treated as the first trustworthy auth boundary",
            "anonymous requests can reach code that assumes req.user exists",
        ],
        "observations": [
            "authGuard currently delegates without checking identity",
            "accountRoute dereferences req.user.id after the guard should have stopped anonymous callers",
            "the test expresses the public 401 contract before handler side effects",
        ],
        "preconditions": [
            "the route is public-facing and caller identity is required",
            "the guard wraps the route before accountRoute executes",
        ],
        "transmutation": "Trade handler-local trust in req.user for an explicit middleware authentication boundary before side effects.",
        "target_artifacts": ["src/middleware/auth.ts", "src/routes/account.ts", "tests/account-auth.test.ts"],
    },
    "infer_change_auth_boundary_mutated": {
        "constraints_before": [
            "authentication is discovered after endpoint work has already started",
            "renamed files obscure that app/http_guard.ts is the shared request boundary",
        ],
        "observations": [
            "endpoint currently checks user after doing work",
            "guard file wraps all API requests",
            "the moved test still encodes the same early rejection invariant",
        ],
        "preconditions": [
            "the guard executes before the endpoint",
            "the unauthenticated path has a stable public 401 or equivalent rejection contract",
        ],
        "transmutation": "Trade late endpoint rejection for early shared-boundary enforcement while preserving the external auth contract.",
        "target_artifacts": ["app/http_guard.ts", "app/account_endpoint.ts", "test/auth_boundary.test.ts"],
    },
    "infer_change_cli_schema_sibling": {
        "constraints_before": [
            "malformed config is allowed to flow into execution",
            "the CLI reports a late failure instead of the input contract violation",
        ],
        "observations": [
            "invalid config reaches execution path",
            "the expected test names an early CLI error",
            "the schema module is the natural boundary between parsing and execution",
        ],
        "preconditions": [
            "the CLI has a single parse or config-load point before execution",
            "invalid config should fail without starting the side-effecting command path",
        ],
        "transmutation": "Transfer early boundary enforcement from auth to configuration: reject malformed input at the schema boundary before execution.",
        "target_artifacts": ["memory_system/cli.py", "memory_system/config_schema.py", "tests/test_cli_config.py"],
    },
    "implement_schema_validation_v1": {
        "constraints_before": [
            "payload shape is trusted until service execution",
            "service code is carrying validation work that belongs at the API boundary",
        ],
        "observations": [
            "existing pydantic models are already the repo's structured validation mechanism",
            "the response shape is an external contract and should not change",
        ],
        "preconditions": [
            "route code owns the last boundary before service execution",
            "the existing schema model can express the required payload invariant",
        ],
        "transmutation": "Trade loose route payload acceptance for schema-driven admission control while leaving service and response contracts stable.",
        "target_artifacts": ["app/routes/orders.py", "app/schemas/order.py", "tests/test_order_schema.py"],
    },
    "verify_repair_callback_payload_v1": {
        "constraints_before": [
            "the patch changed the callback payload vocabulary",
            "the failing assertion identifies a provider contract, not a new auth policy problem",
        ],
        "observations": [
            "verifier expected callback_state['next_url']",
            "actual payload exposed callback_state['redirect']",
            "the failure localizes repair to callback payload shape",
        ],
        "preconditions": [
            "the verifier output is from the callback contract regression",
            "the provider-facing payload key is part of the public integration contract",
        ],
        "transmutation": "Trade broad auth repair for verifier-local payload restoration: preserve the provider callback key that the integration contract names.",
        "target_artifacts": ["app/oauth/callback.py"],
    },
    "retrieval_sdk_webhook_docs_v1": {
        "constraints_before": [
            "webhook verification is under-specified and memory may use a stale SDK helper",
            "examples from previous SDK majors can silently validate the wrong header contract",
        ],
        "observations": [
            "the needed facts are helper name, signature header contract, and version-specific behavior",
            "official docs and local installed source outrank older community examples",
        ],
        "preconditions": [
            "the installed SDK version can be identified",
            "the chosen helper appears in either official versioned docs or package source",
        ],
        "transmutation": "Trade memory-based SDK guessing for version-matched source authority before selecting the webhook verification patch.",
        "target_artifacts": ["official SDK docs", "release notes", "installed package source"],
        "retrieval_queries": [
            "official SDK webhook signature verification current version helper",
            "installed SDK source webhook signature verify header contract",
            "SDK release notes webhook signature verification breaking change",
        ],
    },
    "cross_domain_checkout_boundary_v1": {
        "constraints_before": [
            "the workflow contains reversible setup actions and an irreversible payment action",
            "a task-completion objective can overrun the safety boundary if the final action is not separated",
        ],
        "observations": [
            "search, selection, customization, cart, and checkout are preparatory states",
            "payment submission is the irreversible boundary",
        ],
        "preconditions": [
            "checkout can be reached without submitting payment",
            "the final confirmation or submit control is distinguishable from review/setup controls",
        ],
        "transmutation": "Transfer early boundary enforcement into workflow control: advance through reversible setup, then stop at the irreversible payment boundary.",
        "target_artifacts": ["workflow:search restaurant", "workflow:cart", "workflow:checkout", "boundary:payment submit"],
    },
    "understand_async_cache_race_v1": {
        "constraints_before": [
            "cache identity is global while profile data is user-scoped",
            "overlapping async requests can observe shared mutable state",
        ],
        "observations": [
            "profile_cache uses a shared key shape",
            "profile endpoint calls get_or_set without visible user identity in the key",
            "the failing test requires concurrent reproduction, not only single-request correctness",
        ],
        "preconditions": [
            "cached data is specific to an authenticated user",
            "the cache layer is reused across concurrent requests",
        ],
        "transmutation": "Trade global cache reuse for identity-scoped cache constraints that preserve concurrency without cross-user leakage.",
        "target_artifacts": ["app/profile.py", "app/cache.py", "tests/test_profile_cache.py"],
    },
    "understand_migration_contract_v1": {
        "constraints_before": [
            "local fixtures hide production rows where status is NULL",
            "schema tightening is considered before the legacy nullable data contract is mapped",
        ],
        "observations": [
            "migration backfills only active orders",
            "model validation still permits legacy imports to be blank",
            "the later index rejects NULL after the incomplete backfill",
        ],
        "preconditions": [
            "production contains rows outside the local happy-path fixture set",
            "schema migration order can be replayed with legacy null fixtures",
        ],
        "transmutation": "Trade local-pass migration confidence for production-invariant mapping before tightening the nullable column contract.",
        "target_artifacts": [
            "db/migrate/20260701010101_backfill_status.rb",
            "app/models/order.rb",
            "spec/migrations/status_spec.rb",
        ],
    },
    "infer_change_cache_ttl_mutated": {
        "constraints_before": [
            "authorization decisions can remain valid only because TTL has not expired",
            "over-invalidating the cache would remove stampede protection",
        ],
        "observations": [
            "policy updates should take effect quickly",
            "cache stampede protection is still needed",
            "policy version is the missing invalidation boundary",
        ],
        "preconditions": [
            "policy evaluations have a version or revision that can key cache entries",
            "authorization correctness matters more than reusing stale TTL entries",
        ],
        "transmutation": "Trade time-only cache freshness for policy-version-bound authorization caching that keeps concurrency protection.",
        "target_artifacts": ["internal/decision_cache.go", "internal/policy_eval.go", "tests/authz_cache_test.go"],
    },
    "infer_change_public_api_contract_sibling": {
        "constraints_before": [
            "internal model vocabulary has leaked into the public serializer",
            "external clients depend on the old response field name",
        ],
        "observations": [
            "internal model renamed total_cents",
            "external clients still expect total",
            "serializer is the correct compatibility boundary",
        ],
        "preconditions": [
            "the public contract is intentionally backward-compatible",
            "the serializer can map internal names to external names without changing domain code",
        ],
        "transmutation": "Trade internal rename leakage for a compatibility wrapper at the serializer boundary.",
        "target_artifacts": ["src/orders/serializer.ts", "src/orders/controller.ts", "tests/orders.contract.test.ts"],
    },
    "implement_idempotency_guard_v1": {
        "constraints_before": [
            "provider retries can replay the same payment side effect",
            "callback execution is not keyed to the provider event identity",
        ],
        "observations": [
            "repo already has a transaction helper",
            "provider response status is externally visible and should remain stable",
        ],
        "preconditions": [
            "callback payload includes a stable provider event id",
            "the persistence layer can atomically record processed event ids",
        ],
        "transmutation": "Trade replay-prone callback side effects for transaction-scoped idempotency keyed by provider event identity.",
        "target_artifacts": ["app/payments/callback.py", "app/payments/models.py", "tests/test_payment_callbacks.py"],
    },
    "implement_feature_flag_scope_v1": {
        "constraints_before": [
            "new serializer behavior is globally reachable",
            "default tenants can observe a rollout they did not opt into",
        ],
        "observations": [
            "existing flag helper should be the gating primitive",
            "branching in every caller would spread the rollout constraint across the codebase",
        ],
        "preconditions": [
            "tenant identity is available at the serializer boundary or an immediate wrapper",
            "the flag helper has a stable default-off behavior",
        ],
        "transmutation": "Trade global behavior switch for tenant-scoped rollout gating at the narrow serializer boundary.",
        "target_artifacts": ["app/serializers/invoice.py", "app/flags.py", "tests/test_invoice_flags.py"],
    },
    "verify_repair_timezone_boundary_v1": {
        "constraints_before": [
            "the patch chose the renewal date after converting to UTC",
            "unit tests missed the tenant-local midnight boundary",
        ],
        "observations": [
            "integration expected 2026-03-09 America/Chicago",
            "actual result was 2026-03-10 UTC",
            "DST-sensitive date selection is the residual failure",
        ],
        "preconditions": [
            "tenant timezone is part of billing correctness",
            "UTC storage or transport should happen after local date selection",
        ],
        "transmutation": "Trade globally convenient UTC boundary logic for tenant-local date selection before UTC conversion.",
        "target_artifacts": ["app/billing/renewal.py", "tests/test_renewal_timezone.py"],
    },
    "verify_repair_import_cycle_v1": {
        "constraints_before": [
            "the behavior fix introduced an invalid dependency direction",
            "the import cycle is structural and separate from the new public contract",
        ],
        "observations": [
            "ImportError names a partially initialized module",
            "the helper import crosses from package initializer into evaluator",
            "the original behavior regression should remain green",
        ],
        "preconditions": [
            "the new behavior contract is already correct",
            "the helper can move behind a lower-level module or lazy boundary without semantic change",
        ],
        "transmutation": "Trade behavior-focused repair for dependency-direction repair while preserving the newly fixed contract.",
        "target_artifacts": ["app/policy/__init__.py", "app/policy/evaluator.py"],
    },
    "retrieval_auth_library_version_v1": {
        "constraints_before": [
            "JWT audience verification behavior depends on installed auth library version",
            "old tutorials may disable the exact verification that must be enforced",
        ],
        "observations": [
            "the required facts are installed major version, helper signature, and exception contract",
            "package source can settle discrepancies between docs and local runtime",
        ],
        "preconditions": [
            "the installed distribution version can be read from metadata or lockfile",
            "the selected API path verifies audience rather than only decoding the token",
        ],
        "transmutation": "Trade tutorial-driven JWT handling for installed-version-grounded audience verification.",
        "target_artifacts": ["installed package source", "official library docs", "changelog"],
        "retrieval_queries": [
            "installed auth library version JWT audience verification helper",
            "official library docs verify audience claim current major",
            "auth library changelog audience verification exception contract",
        ],
    },
    "retrieval_framework_migration_v1": {
        "constraints_before": [
            "deprecated routing hook replacement is unknown",
            "pre-release or previous-router advice can preserve compilation while changing route semantics",
        ],
        "observations": [
            "replacement hook name and deprecation version must be grounded together",
            "migration guide and current API reference should agree before patching",
        ],
        "preconditions": [
            "the app's framework version is known",
            "route behavior can be regression-tested after the migration",
        ],
        "transmutation": "Trade ad hoc deprecation repair for migration-guide-grounded replacement that preserves route matching semantics.",
        "target_artifacts": ["official migration guide", "release notes", "current API reference"],
        "retrieval_queries": [
            "current framework version deprecated routing hook replacement migration guide",
            "framework release notes routing hook deprecation version",
            "current API reference replacement routing hook semantics",
        ],
    },
    "retrieval_cve_patch_advisory_v1": {
        "constraints_before": [
            "dependency is vulnerable but the safe patched range is not yet known",
            "jumping across a major version may create avoidable migration risk",
        ],
        "observations": [
            "vendor advisory should define affected and fixed ranges",
            "lockfile reveals current version and transitive placement",
        ],
        "preconditions": [
            "a patched non-breaking range exists or can be ruled out",
            "the advisory identity matches the package actually present in the lockfile",
        ],
        "transmutation": "Trade generic vulnerability urgency for advisory-grounded minimum secure upgrade selection.",
        "target_artifacts": ["vendor security advisory", "package release notes", "lockfile"],
        "retrieval_queries": [
            "vendor security advisory CVE affected versions patched versions package",
            "package release notes CVE fixed version breaking changes",
            "lockfile current package version transitive dependency path",
        ],
    },
    "retrieval_error_message_source_v1": {
        "constraints_before": [
            "the runtime error string is ambiguous across unrelated subsystems",
            "editing from the message alone can target the wrong layer",
        ],
        "observations": [
            "local stack trace is the anchor for library and call-site provenance",
            "official issue tracker can distinguish same-word unrelated failures",
        ],
        "preconditions": [
            "the local stack frame identifies the library and version involved",
            "retrieved issue or docs match both message and version",
        ],
        "transmutation": "Trade error-message keyword search for stack-trace-anchored provenance retrieval.",
        "target_artifacts": ["official issue tracker", "library docs", "local stack trace"],
        "retrieval_queries": [
            "exact runtime error message library version official issue tracker",
            "stack trace top library frame error message known workaround",
            "library docs error condition version-specific behavior",
        ],
    },
    "retrieval_package_source_truth_v1": {
        "constraints_before": [
            "latest docs describe a signature that may not exist in the installed package",
            "patch validity depends on runtime behavior present locally",
        ],
        "observations": [
            "installed package source can reveal the actual function signature",
            "package metadata and versioned docs explain the doc/source mismatch",
        ],
        "preconditions": [
            "local package files are accessible or reproducible from the lockfile",
            "patch code calls the signature actually installed in the environment",
        ],
        "transmutation": "Trade unversioned documentation trust for local-source-grounded integration repair.",
        "target_artifacts": ["installed package source", "package metadata", "versioned docs"],
        "retrieval_queries": [
            "installed package source function signature runtime default",
            "package metadata installed version docs mismatch",
            "versioned docs function signature package version",
        ],
    },
    "retrieval_test_pattern_official_v1": {
        "constraints_before": [
            "streaming test can pass by timing accident if copied from outdated sync snippets",
            "async iterator contract must be preserved in the mock",
        ],
        "observations": [
            "official SDK test docs and examples should define the mock shape",
            "installed test helpers may already encode the expected stream object",
        ],
        "preconditions": [
            "the production client uses async streaming semantics",
            "the chosen verifier does not depend on sleeps or wall-clock timing",
        ],
        "transmutation": "Trade community timing snippets for official async streaming test-pattern retrieval.",
        "target_artifacts": ["official SDK test docs", "SDK examples", "installed test helpers"],
        "retrieval_queries": [
            "official SDK testing streaming API async iterator mock",
            "SDK examples mock streaming response async tests",
            "installed SDK test helpers streaming mock object shape",
        ],
    },
    "retrieval_api_limits_contract_v1": {
        "constraints_before": [
            "sync job drops records because pagination and rate-limit contracts are underspecified",
            "old SDK examples may hide current page-token or retry-after semantics",
        ],
        "observations": [
            "official API reference should define page-token progression",
            "rate-limit docs should define retry-after handling and backoff constraints",
        ],
        "preconditions": [
            "the current API version is known",
            "the sync verifier can simulate pagination and rate-limit responses",
        ],
        "transmutation": "Trade best-effort sync looping for API-contract-grounded pagination and retry handling.",
        "target_artifacts": ["official API reference", "rate limit docs", "SDK source"],
        "retrieval_queries": [
            "official API reference pagination page token current version",
            "API rate limit docs retry-after header semantics",
            "SDK source pagination retry handling sync job",
        ],
    },
    "cross_domain_email_send_boundary_v1": {
        "constraints_before": [
            "campaign preparation is reversible but send or schedule actions are externally visible",
            "completion pressure can convert a draft task into an irreversible send",
        ],
        "observations": [
            "audience selection, template editing, and preview are preparatory states",
            "send and schedule controls cross the irreversible communication boundary",
        ],
        "preconditions": [
            "preview or draft state can be reached without send/schedule",
            "the final action control is separable from save or preview controls",
        ],
        "transmutation": "Transfer payment-boundary restraint into business workflow control: prepare evidence-rich draft state, then stop before send/schedule.",
        "target_artifacts": ["workflow:audience", "workflow:template", "workflow:preview", "boundary:send or schedule"],
    },
    "cross_domain_file_delete_boundary_v1": {
        "constraints_before": [
            "file cleanup analysis is reversible until deletion mutates the filesystem",
            "candidate identification and removal are distinct action classes",
        ],
        "observations": [
            "scan and ranking can produce a deletion plan without side effects",
            "delete command crosses the destructive filesystem boundary",
        ],
        "preconditions": [
            "candidate paths can be listed without invoking removal commands",
            "the verifier can observe that no files were removed",
        ],
        "transmutation": "Transfer irreversible-boundary reasoning into terminal cleanup: produce a grounded candidate plan and stop before destructive removal.",
        "target_artifacts": ["workflow:scan files", "workflow:rank stale candidates", "artifact:deletion plan", "boundary:delete"],
    },
}


def _context_targets(case: CodingFortressCase) -> list[str]:
    context = dict(case.context or {})
    for key in ("candidate_files", "allowed_files", "patch_files", "repo_map", "desired_sources", "workflow"):
        raw = context.get(key)
        if isinstance(raw, list):
            values = [str(item).strip() for item in raw if str(item).strip()]
            if values:
                return values
    return []


def _fallback_before(case: CodingFortressCase) -> list[str]:
    if case.phase == RETRIEVAL_GROUNDING:
        return [
            "missing external knowledge can force an implementation guess",
            "source authority and version match are not yet established",
        ]
    if case.phase == CODING_UNDERSTAND:
        return [
            "the relevant boundary and artifact set are not yet isolated",
            "symptoms may be mistaken for the root constraint",
        ]
    if case.phase == CODING_INFER_CHANGE:
        return [
            "the desired change is underconstrained by symptoms alone",
            "multiple plausible edits compete without a chosen invariant",
        ]
    if case.phase == CODING_IMPLEMENT:
        return [
            "the selected move is not yet mapped to the smallest local edit",
            "repo style constraints can be violated by a generic patch",
        ]
    if case.phase == CODING_VERIFY_REPAIR:
        return [
            "verifier output names a residual constraint after the first patch",
            "broad repair risks disturbing behavior that already works",
        ]
    if case.phase == META_TRANSFER:
        return [
            "a known coding transmutation has not yet been mapped to the new domain boundary",
            "domain actions differ in reversibility and evidence requirements",
        ]
    return ["the active constraints are not yet transformed into a reusable move"]


def _fallback_transmutation(case: CodingFortressCase) -> str:
    action = case.expected_action_family or "constraint transmutation"
    if case.phase == RETRIEVAL_GROUNDING:
        return f"Trade memory-based guessing for source-grounded {action}."
    if case.phase == CODING_UNDERSTAND:
        return f"Trade symptom-level reading for artifact-grounded {action}."
    if case.phase == CODING_INFER_CHANGE:
        return f"Trade broad edit search for invariant-selected {action}."
    if case.phase == CODING_IMPLEMENT:
        return f"Trade generic patching for repo-style-preserving {action}."
    if case.phase == CODING_VERIFY_REPAIR:
        return f"Trade broad second patching for verifier-localized {action}."
    if case.phase == META_TRANSFER:
        return f"Trade domain-specific imitation for transferred {action}."
    return f"Apply {action} to satisfy the active constraints."


def build_gpt_seed_trace(case: CodingFortressCase, *, model: str = GPT_SEED_MODEL) -> TransmutationTrace:
    normalized = case.normalized()
    override = dict(_SEED_OVERRIDES.get(normalized.case_id) or {})
    desired_sources = list(dict(normalized.context or {}).get("desired_sources") or [])
    retrieval_sources = override.get("retrieval_sources") or normalized.expected_retrieval_sources or desired_sources
    retrieval_queries = override.get("retrieval_queries") or []
    if normalized.phase == RETRIEVAL_GROUNDING and not retrieval_queries:
        retrieval_queries = [
            f"{normalized.repo_family} official docs {normalized.expected_action_family}",
            f"{normalized.repo_family} installed source {normalized.expected_action_family}",
        ]
    trace = TransmutationTrace(
        trace_id=f"gpt_seed_{normalized.case_id}",
        fortress_id="coding_fortress_v0",
        phase=normalized.phase,
        model=model,
        prompt=normalized.prompt,
        constraints_before=list(override.get("constraints_before") or _fallback_before(normalized)),
        constraints_after=list(override.get("constraints_after") or normalized.expected_constraints),
        observations=list(override.get("observations") or dict(normalized.context or {}).get("observations") or []),
        preconditions=list(
            override.get("preconditions")
            or [
                "the named verifier is the authority for success",
                "the move applies only when the expected invariant is the active constraint",
            ]
        ),
        transmutation=str(override.get("transmutation") or _fallback_transmutation(normalized)),
        action_family=str(override.get("action_family") or normalized.expected_action_family),
        target_artifacts=list(override.get("target_artifacts") or _context_targets(normalized)),
        retrieval_queries=list(retrieval_queries),
        retrieval_sources=[str(item) for item in retrieval_sources],
        verifier=list(override.get("verifier") or normalized.expected_verifier),
        residual_constraints=list(override.get("residual_constraints") or []),
        outcome="success",
        mutation_tier=normalized.mutation_tier,
        domain=normalized.domain,
        repo_family=normalized.repo_family,
        source_trace_id=normalized.transfer_source_case_id,
        generated_ts=1783600000,
        metadata={
            "case_id": normalized.case_id,
            "lane": "teacher",
            "seed_bank_id": GPT_SEED_BANK_ID,
            "seed_author": "codex",
            "observable_trace_only": True,
        },
    )
    return trace.normalized()


def build_gpt_seed_extraction_report(
    *,
    cases: list[CodingFortressCase] | None = None,
    cases_path: str = "",
    model: str = GPT_SEED_MODEL,
    limit: int = 0,
) -> dict[str, Any]:
    selected_cases = load_coding_fortress_cases(cases_path) if cases_path else list(cases or default_coding_fortress_cases())
    if limit:
        selected_cases = selected_cases[: max(int(limit), 0)]
    normalized_cases = [case.normalized() for case in selected_cases]
    rows: list[dict[str, Any]] = []
    for case in normalized_cases:
        trace = build_gpt_seed_trace(case, model=model)
        rows.append(
            {
                "case_id": case.case_id,
                "phase": case.phase,
                "mutation_tier": case.mutation_tier,
                "domain": case.domain,
                "repo_family": case.repo_family,
                "teacher_trace": trace.to_dict(),
                "teacher_parse_mode": "gpt_seed",
                "teacher_residuals": [],
            }
        )
    return {
        "generated_ts": int(time.time()),
        "case_count": len(normalized_cases),
        "completed_case_count": len(rows),
        "failure_count": 0,
        "teacher_model": model,
        "case_summary": summarize_coding_fortress_cases(normalized_cases),
        "teacher_residual_count": 0,
        "seed_bank_id": GPT_SEED_BANK_ID,
        "rows": rows,
        "failures": [],
    }


def write_gpt_seed_teacher_bank(
    *,
    out_dir: str | Path,
    cases: list[CodingFortressCase] | None = None,
    cases_path: str = "",
    model: str = GPT_SEED_MODEL,
    limit: int = 0,
) -> dict[str, str]:
    report = build_gpt_seed_extraction_report(cases=cases, cases_path=cases_path, model=model, limit=limit)
    return write_coding_fortress_extraction_artifacts(report=report, out_dir=out_dir)
