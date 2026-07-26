# Memla Master Context

> Canonical handoff for continuing Memla on the main PC.
>
> Last updated: 2026-07-26
>
> Repository observed on branch: `import-yosazo`
>
> Repository commit before this document was added: `293edf2`

## Instructions For The Next Codex Session

Read this document completely before changing code.

Then inspect the repository and verify every claim against the current files. This
document is a map, not authority over code that may have changed after it was
written. Preserve unrelated user changes. Do not replace working systems merely
to make the architecture resemble this document.

The immediate mission is deliberately narrow:

> Use NVIDIA's hosted DeepSeek V4 Flash as a teacher to help a local Qwen-class
> 7B model become substantially more reliable at DoorDash tasks by extracting,
> compressing, retrieving, executing, and testing reusable constraint
> transmutations.

Do not begin with custom hardware, arbitrary apps, or broad claims about general
intelligence. First make the complete teacher-to-bank-to-student-to-verifier loop
work on one hard DoorDash family and prove improvement on held-out mutations.

Never put an API key in this repository, a trace, a report, a shell history
example, or a prompt artifact. Use environment variables. The NVIDIA key should
be called `NVIDIA_API_KEY` in the user's shell and mapped to `LLM_API_KEY` only
for the process that needs it.

Do not place a real order during development. The default terminal state is
`checkout_ready`, with a hard stop before payment or order submission.

## One-Sentence Definition

Memla is a verifier-backed constraint-transmutation runtime that helps a small
local model act more like a stronger model by retrieving reusable ways to
understand, preserve, transform, verify, and repair constraints.

## The Actual Bet

The project is not betting that a 7B model can physically contain all of a
frontier model's knowledge or reproduce every capability of a frontier model.

The narrower, testable bet is:

1. A large portion of useful intelligence in bounded workflows appears as
   recurring constraint-handling patterns.
2. Those patterns can be elicited inside carefully designed environments.
3. They can be represented more compactly than raw conversations.
4. A smaller model can retrieve and apply them at runtime.
5. Some patterns transfer to mutated tasks, sibling apps, and eventually other
   domains.
6. A meta-layer can measure that transfer, retain useful patterns, reject
   harmful ones, and decide where teacher calls are still worth paying for.

The target system is therefore larger than the 7B weights:

`student model + transmutation bank + retrieval + tools + verifier + repair loop`

That complete system is the thing being compared with a teacher, not the bare
student model in isolation.

## C2A In Plain Language

C2A starts from the view that intelligence is visible in what happens to
constraints.

A request is not just a sentence. It creates a set of conditions that must remain
true while the world changes. An intelligent system notices those conditions,
resolves ambiguities, converts them into actions, preserves them through
intermediate states, and proves they still hold at the end.

For:

> DoorDash me two large cheese pizzas from Domino's and stop before payment.

the obvious constraints include:

- service is DoorDash
- restaurant is Domino's
- item is cheese pizza
- size is large
- quantity is exactly two
- the cart must preserve the requested configuration
- no payment or final order submission may occur

The application adds derived constraints that were not explicit in the prompt:

- the restaurant must be selected before an item can be configured
- the item may be called "Build Your Own Pizza"
- size may be a required radio selection
- quantity may be hidden in a stepper or only visible in the cart
- stale page state must not be mistaken for post-action evidence
- a button label may be ambiguous without its surrounding UI
- checkout navigation may be allowed while "Place order" remains forbidden

Intelligence is the ability to carry the original and derived constraints
through these transitions without silently dropping one.

## Core Vocabulary

### Constraint

A condition that must be satisfied, preserved, avoided, or verified.

Examples:

- `quantity == 2`
- `restaurant == Domino's`
- `current page contains an enabled quantity control`
- `do not cross the payment boundary`
- `the post-action screen must provide fresh evidence`

Constraints may come from the user, the environment, safety policy, prior state,
or a verifier.

### Transmutation

A reusable description of how one constraint state becomes another useful
constraint state.

Example:

> Trade vague cart progress for explicit cardinality preservation: locate the
> item quantity control, increment until visible count equals two, re-inspect,
> and refuse checkout until cart-level count evidence confirms two.

A strong transmutation contains more than advice. It includes:

- when it applies
- observations that support it
- preconditions
- the action family
- the expected postcondition
- a verifier
- a repair policy
- a stop or escalation condition
- known transfer targets
- confidence and provenance

### Fortress

A fortress is a controlled task environment built to make constraint handling
observable and testable.

It is not merely a long prompt. It contains:

- a world or task state
- explicit and hidden constraints
- available observations
- legal and illegal actions
- traps and ambiguity
- mutation axes
- verifiers
- failure and repair opportunities
- a boundary condition
- a clearance rule

The model clears a fortress only when its actions preserve the required
constraints and the verifier confirms the intended state.

Difficulty is useful only when it is diagnostic. Random complication produces
noise. A good fortress makes a particular capability necessary and makes failure
attributable.

### Trace

A trace is the observable record emitted while clearing a fortress. It should
capture decisions that can be scored and reused. It is not a demand for private
hidden chain-of-thought.

The trace records:

- observed state and evidence
- active constraints
- missing evidence
- chosen action family
- why that action is justified by observable evidence
- expected state change
- verifier
- result
- residual constraints
- repair or stop decision

### Transmutation Bank

The bank stores compressed, reusable transmutations plus evidence about where
they work.

The bank is not a pile of complete transcripts inserted into every prompt. Raw
teacher traces remain cold storage. Runtime retrieval should return a small
number of relevant, validated rules.

### Meta-Fortress

The meta-fortress observes many fortress runs. Its job is not mystical
self-improvement. Its concrete jobs are:

- identify recurring failure families
- create targeted micro-fortresses
- decide whether an existing rule is sufficient
- request teacher help only when necessary
- compare teacher and student constraint motion
- measure same-task and transfer performance
- promote, demote, merge, or quarantine rules
- detect negative transfer
- select the next curriculum cases by information gain

The meta-fortress is what turns many local lessons into a governed learning
system.

## How A Fortress Returns To C2A

The relationship is:

```text
C2A thesis
  intelligence is visible as constraint transformation
        |
        v
Fortress
  creates a world where the transformation is necessary and observable
        |
        v
Trace
  records the observable constraint motion
        |
        v
Transmutation bank
  compresses recurring successful motion into reusable rules
        |
        v
Student runtime
  retrieves and applies those rules in new states
        |
        v
Meta-fortress
  measures transfer, failures, and what should be learned next
```

## What Would Count As Evidence

The thesis gains evidence if:

- the raw 7B baseline fails a held-out task
- the same frozen 7B model succeeds after retrieving bank rules
- the successful rule came from a distinct training case
- the holdout differs in wording, page state, controls, or app family
- deterministic evidence confirms the requested state
- success repeats across multiple runs
- catastrophic boundary violations remain zero

The thesis does not gain meaningful evidence if:

- the test prompt is identical to the teacher prompt
- the answer is memorized by case ID
- teacher output is silently used at evaluation time
- a human manually repairs the run
- success is judged only by another model's opinion
- the model claims success without state evidence
- a brittle app-specific selector is mistaken for general reasoning

## Honest Scope Of The Claim

If the complete Memla system matches a strong teacher across understanding,
planning, acting, verification, and repair on a bounded DoorDash suite, then it
is teacher-like on that suite.

That alone does not prove universal equivalence. Transfer must be measured at
increasing distance:

1. same task, new run
2. paraphrased prompt
3. changed item or modifier
4. changed UI state or control form
5. different merchant in DoorDash
6. sibling food app such as Uber Eats
7. sibling transaction app such as shopping
8. cross-domain workflow such as messaging or calendar

Each step is a stronger claim. The project should celebrate the exact rung it
has demonstrated and immediately test the next rung.

## Immediate DoorDash Mission

Start with the known hard case:

> DoorDash me two large cheese pizzas from Domino's and stop before payment.

This case is useful because the current code can already represent restaurant,
item, size, toppings, add-ons, and tip, but quantity is not a first-class field
in `OrderSpec`. The prompt therefore exposes a real representational hole rather
than a fabricated benchmark.

The first complete proof should be:

1. compile the request into typed constraints, including quantity and boundary
2. observe the current DoorDash state
3. retrieve relevant transmutations
4. have the local student propose the next action and verifier
5. execute only an allowed action
6. capture fresh post-action evidence
7. verify or repair
8. call the teacher only when the bank and student cannot safely proceed
9. compress a successful teacher rescue
10. replay the case without the teacher
11. test held-out mutations
12. report baseline versus bank-assisted results

## Current Repository State

The repository is not starting from zero. The following systems already exist.

### General Runtime And Retrieval

- [`memory_system/natural_terminal.py`](memory_system/natural_terminal.py)
  contains the broad terminal and web planning/retrieval loops. It is important
  prior art for how Memla builds context, asks models for plans, runs bounded
  tools, and produces verifier-backed reports.
- [`memory_system/ollama_client.py`](memory_system/ollama_client.py) contains
  `UniversalLLMClient`, with Ollama, generic OpenAI-compatible, Anthropic,
  GitHub Models, and Gemini paths.
- [`memory_system/cli.py`](memory_system/cli.py) exposes the project's commands.
- [`memory_system/distillation/`](memory_system/distillation/) contains earlier
  trace-bank, policy-bank, transfer-evaluation, coding, and benchmark systems.
  Reuse these patterns where they fit.

### Coding Fortress

- [`memory_system/fortresses/coding_fortress.py`](memory_system/fortresses/coding_fortress.py)
  defines normalized observable `TransmutationTrace` records, the coding phases,
  and four mutation tiers: `same`, `mutated`, `sibling`, and `cross_domain`.
- [`memory_system/fortresses/runner.py`](memory_system/fortresses/runner.py)
  runs teacher and student lanes and writes comparison artifacts.
- [`memory_system/fortresses/meta_fortress.py`](memory_system/fortresses/meta_fortress.py)
  provides the global ledger and rule promotion logic.
- [`memory_system/fortresses/gpt_seed_bank.py`](memory_system/fortresses/gpt_seed_bank.py)
  provides a built-in seed bank.

The coding fortress embodies the original four-step framing:

1. understand the existing code
2. infer the correct change
3. implement the change
4. verify and repair

It also includes retrieval grounding and cross-domain transfer phases.

### Agency Fortress

- [`memory_system/fortresses/agency_fortress.py`](memory_system/fortresses/agency_fortress.py)
  defines the agency fortress, state snapshots, element observations, actions,
  traces, cases, and scoring.
- [`memory_system/fortresses/agency_automation.py`](memory_system/fortresses/agency_automation.py)
  detects unresolved constraints, creates a targeted micro-fortress, builds a
  teacher request, compresses the response, and adds it to a global ledger.
- [`tests/test_step36_agency_fortress.py`](tests/test_step36_agency_fortress.py)
  covers the fortress structures and scoring.
- [`tests/test_step37_agency_automation.py`](tests/test_step37_agency_automation.py)
  covers quantity detection, micro-fortress generation, teacher-response
  compression, artifact writing, and CLI behavior.

The agency fortress phases are:

1. `agency_prompt_capsule`
2. `agency_observe_state`
3. `agency_ground_affordances`
4. `agency_select_action`
5. `agency_execute_verify`
6. `agency_repair`
7. `agency_boundary_stop`
8. `agency_transfer`

There are currently 18 hard agency cases in the generated V0 pack.

### Existing Agency Automation Artifacts

Generated examples live in:

- [`memla_reports/agency_fortress_v0/`](memla_reports/agency_fortress_v0/)
- [`memla_reports/agency_automation_20260710_105427/`](memla_reports/agency_automation_20260710_105427/)
- [`memla_reports/gpt_seed_teacher_bank/`](memla_reports/gpt_seed_teacher_bank/)

The hard DoorDash dry run previously:

- found six constraints
- correctly focused confusion on `quantity must equal 2`
- generated same, mutated, sibling, and cross-domain micro-cases
- estimated about 3,099 teacher input tokens and 1,800 output tokens
- skipped the teacher because it was a dry run

These artifacts prove the automation scaffold works. They do not prove the local
student has learned or that live DoorDash transfer works.

### iOS Browser Agent

- [`ios/README.md`](ios/README.md) documents the SwiftUI and `WKWebView` shell.
- [`ios/MemlaApp/Sources/MemlaBrowserView.swift`](ios/MemlaApp/Sources/MemlaBrowserView.swift)
  contains the actual web action loop.

Important existing behavior includes:

- page inspection
- DoorDash and Uber Eats page classification
- candidate extraction and ranking
- safe and caution tap policies
- automatic re-inspection after an action
- residual constraint reporting
- capsule verification from visible evidence
- hard blocking of payment, purchase, send, booking, deletion, and other final
  sensitive actions

Important functions in `MemlaBrowserView.swift` include:

- `tapButtonCandidate`
- `classifyDoorDashPage`
- `classifyUberEatsPage`
- `candidateActions`
- `residualsForPage`
- `capsuleVerificationForPage`

This is the historical reason DoorDash behavior transferred to Uber Eats: the
loop already contains generic page-state, candidate, safety, and verification
abstractions, with app-specific classifiers underneath.

### Action Capsules And Current Representational Gap

[`memory_system/action_capsules.py`](memory_system/action_capsules.py) currently
defines food order fields for:

- service
- restaurant
- item
- size
- toppings
- add-ons
- tip

It does not currently make quantity, crust, exclusions, exact variant, price
ceiling, or substitution policy first-class `OrderSpec` fields.

The initial DoorDash corpus in
[`cases/consumer_v1_doordash_cases.jsonl`](cases/consumer_v1_doordash_cases.jsonl)
contains ten Domino's pizza cases, mainly size and topping mutations. It does not
currently include quantity two.

The broader benchmark design is in
[`proof/consumer_v1_benchmark_spec.md`](proof/consumer_v1_benchmark_spec.md).

### Hardware Work Is Parked

[`hardware/memla_touch_bench_v0_spec.md`](hardware/memla_touch_bench_v0_spec.md)
specifies a future physical touch bench: fixed dock, camera, XY gantry, and a
conductive stylus. That remains strategically relevant because it can control
interfaces without privileged app APIs.

It is not the first implementation target on the PC. Prove the software learning
loop in the existing `WKWebView` environment first. The physical bench becomes
valuable after the policy can reliably decide what to touch.

## What Is Implemented Versus Missing

### Implemented

- structured coding and agency fortress schemas
- same/mutated/sibling/cross-domain mutation taxonomy
- deterministic trace scoring components
- confusion detection
- dynamic constraint inference for the hard quantity prompt
- micro-fortress generation
- teacher prompt generation
- teacher-response compression
- global transmutation ledger
- basic promotion decisions
- OpenAI-compatible HTTP client path
- local Ollama client path
- iOS page inspection and guided execution
- DoorDash and Uber Eats page classifiers
- checkout/payment safety boundaries
- DoorDash benchmark cases

### Missing Or Incomplete

- a first-class NVIDIA provider configuration and reasoning-output capture
- a live observation bridge from the iOS page inspector into agency automation
- quantity as a typed action-capsule constraint
- quantity-specific DOM/accessibility grounding and verification
- a durable bank shared across repeated automation runs
- runtime retrieval from the agency bank into the student's action prompt
- a complete local Qwen student lane for agency tasks
- automatic teacher escalation during a live stalled run
- replay of a teacher-cleared micro-fortress without teacher access
- held-out mutation generation with train/eval leakage controls
- baseline versus bank-assisted agency evaluation
- student imitation dataset export
- optional QLoRA/SFT pipeline
- calibrated uncertainty and abstention tests
- robust screenshot/vision observation support
- proof that any transmutation transfers beyond its source case

The next session should treat these as the actual backlog.

## Target Runtime Architecture

```text
User request
    |
    v
Prompt capsule / typed constraint graph
    |
    v
Live observation packet
  DOM + accessibility + visible text + screenshot ref + page state
    |
    v
Constraint reconciler
  grounded / ungrounded / contradicted / satisfied / blocked
    |
    +------------------------------+
    |                              |
    v                              v
Bank retriever                 Safety governor
top relevant rules            legal actions + hard boundary
    |                              |
    +---------------+--------------+
                    v
              Local Qwen student
        next action + expected postcondition
        verifier + confidence + residuals
                    |
                    v
               Action executor
                    |
                    v
            Fresh observation packet
                    |
                    v
          Deterministic verifier first
                    |
          success / repair / abstain
                    |
        unresolved and teacher-worthy?
                    |
              yes   v
            Meta-fortress
         builds minimal micro-fortress
                    |
                    v
         DeepSeek V4 Flash teacher
                    |
                    v
        trace validation + compression
                    |
                    v
          candidate bank rule
                    |
                    v
       replay + mutations + promotion
```

The teacher is not in the happy path forever. The teacher is a temporary rescue
and curriculum source. A rule is valuable only if later runs can retrieve and
use it without another teacher call.

## The Agency Fortress In Detail

### Phase 1: Prompt Capsule

Compile the request into typed constraints.

For the initial task, the capsule should eventually include:

```json
{
  "service": "DoorDash",
  "restaurant": "Domino's",
  "items": [
    {
      "item": "cheese pizza",
      "size": "large",
      "quantity": 2
    }
  ],
  "boundary": "stop_before_payment"
}
```

Each field needs provenance, confidence, criticality, and clarification status.
Do not represent quantity only in prose.

### Phase 2: Observe State

Capture only facts available from the current UI:

- URL and title
- page kind
- visible text
- interactive elements
- roles, labels, values, selected/checked state
- stable element fingerprints
- bounds when available
- screenshot reference
- timestamp or state version

Never let a pre-action observation satisfy a post-action verifier. Freshness is a
constraint.

### Phase 3: Ground Affordances

Connect active constraints to possible UI controls:

- restaurant query to search box
- Domino's to merchant result
- cheese pizza to menu item
- large to size selector
- quantity two to stepper, dropdown, or cart line item
- stop boundary to checkout versus final purchase controls

The output should include candidate actions and the evidence supporting each
candidate. If evidence is missing, the correct action may be inspect, scroll,
wait, search, or ask the user.

### Phase 4: Select Action

The student selects one bounded action, not an entire unverified click sequence.

The proposal should include:

- action type
- target fingerprint
- active constraint being advanced
- preconditions
- expected postcondition
- verifier
- risk level
- confidence
- alternatives considered at an observable summary level
- stop condition

### Phase 5: Execute And Verify

Execute only after the safety governor accepts the action.

Then capture a fresh state and verify:

- did the expected state change occur?
- did any required constraint become contradicted?
- did the action accidentally cross a boundary?
- what residual constraints remain?

Deterministic checks should take priority over a model judge whenever possible.

### Phase 6: Repair

When a verifier fails:

1. classify the residual constraint
2. decide whether the action failed, the observation was stale, the target was
   wrong, or the model's expectation was wrong
3. retrieve a repair rule
4. take a bounded repair action
5. re-verify
6. stop if the repair budget is exhausted

Repeated action without new evidence is a loop and must be blocked.

### Phase 7: Boundary Stop

The initial definition of success is reaching a correct cart or checkout-ready
state without submitting payment.

The system must distinguish:

- safe navigation toward checkout
- a review-required transition
- an irreversible action such as `Place order`

No model confidence may override the hard boundary.

### Phase 8: Transfer

After a successful trace, generate tests at four distances:

- same: replay with equivalent state
- mutated: paraphrase, changed quantity, hidden stepper, cart-only quantity
- sibling: Uber Eats quantity control
- cross-domain: Amazon quantity dropdown or another cardinality workflow

The source trace is not promoted as generally transferable until these cases
provide evidence.

## Productive Fortress Difficulty

"Harder is better" is only partly true.

A fortress should be hard because it requires richer constraint handling:

- ambiguous item aliases
- controls that appear only after scroll
- quantity visible only after adding to cart
- stale DOM after asynchronous update
- visually similar wrong merchant
- disabled controls
- duplicate labels
- backtracking after a wrong branch
- dynamic price or availability
- login or location interruption
- boundary controls near safe controls

It should not be hard because of uncontrolled noise:

- random timeouts with no state signal
- impossible tasks
- hidden answers the agent could never observe
- flaky verification
- teacher prompts so large that the relevant issue is buried

Every difficulty axis should correspond to a hypothesis and a measurable failure
mode.

## Teacher Extraction Protocol

The teacher should not simply answer "what should I click?"

For each micro-fortress, require the teacher to emit structured JSON containing:

- root cause
- constraint family
- constraints before
- observations and cues
- preconditions
- transmutation
- action schema
- expected constraints after
- verifier
- repair policy
- boundary policy
- stop conditions
- transfer targets
- adversarial mutations
- confidence

The existing `build_teacher_messages` and `compress_teacher_response` functions
already implement a first version of this contract.

The teacher's prose rationale is useful only insofar as it can be converted into
observable policy. Do not depend on proprietary hidden chain-of-thought. The
fortress should force useful behavior to leave evidence through choices,
predictions, counterfactuals, verification, and repair.

### Teacher Roles

One hosted model may initially fill several logical roles, but keep the roles
separate in artifacts:

- actor: proposes how to clear the micro-fortress
- critic: finds missing constraints and unsafe assumptions
- mutator: creates near-neighbor and transfer cases
- compressor: converts raw trace into a reusable rule
- judge: grades semantic quality when deterministic grading is insufficient

Do not let the model be the only judge of its own action. Environment evidence
and deterministic checks remain primary.

### Counterfactual Extraction

To elicit richer behavior, ask:

- what evidence would change the action?
- what similar-looking control must be rejected?
- what would make the action unsafe?
- what if quantity were represented by a dropdown instead of a stepper?
- what if the item count were visible only in the cart?
- what is the minimum evidence needed before proceeding?
- when should the model abstain?

These questions reveal decision boundaries more usefully than unrestricted
reasoning text.

## NVIDIA DeepSeek V4 Flash Teacher

As of 2026-07-26, NVIDIA documents a free hosted endpoint for:

- model: `deepseek-ai/deepseek-v4-flash`
- base endpoint: `https://integrate.api.nvidia.com/v1`
- API shape: OpenAI-compatible chat completions
- advertised context: up to 1M tokens
- advertised output limit on the hosted reference: up to 16,384 tokens
- reasoning modes: none, high, and max

Official references:

- [NVIDIA model page](https://build.nvidia.com/deepseek-ai/deepseek-v4-flash)
- [NVIDIA API reference](https://docs.api.nvidia.com/nim/re/reference/deepseek-ai-deepseek-v4-flash-infer)

The current generic OpenAI-compatible client appends
`/v1/chat/completions` to its configured base URL. Therefore the current Memla
configuration must use:

```text
https://integrate.api.nvidia.com
```

not:

```text
https://integrate.api.nvidia.com/v1
```

Otherwise the current client would construct `/v1/v1/chat/completions`.

The generic path should be enough for an initial smoke call. It does not yet send
NVIDIA's `reasoning_effort` or `chat_template_kwargs`, and it only reads
`message.content`. A dedicated NVIDIA-compatible enhancement should preserve
`reasoning_content` when returned while still treating the structured final JSON
as the distillation source.

### Secret Setup On The PC

In the shell:

```bash
export NVIDIA_API_KEY='paste-the-key-locally'
export LLM_API_KEY="$NVIDIA_API_KEY"
```

Do not add these values to `.env` unless `.env` is confirmed ignored. Do not pass
the key with `--api-key`, because command-line arguments may be visible in shell
history and process listings.

### Initial Teacher Dry Run

From the repository root:

```bash
.venv/bin/python -B -m memory_system.cli agency automate \
  --dry-run \
  --teacher-provider openai \
  --teacher-base-url https://integrate.api.nvidia.com \
  --teacher-model deepseek-ai/deepseek-v4-flash \
  --prompt "Doordash me two large cheese pizzas from Dominos and stop before payment." \
  --observation "DoorDash item modal shows a large cheese pizza and Add to cart, but no quantity evidence." \
  --app-family doordash \
  --page-kind dd_item_modal \
  --json
```

### Initial Live Teacher Smoke Call

After the dry-run artifacts look correct:

```bash
LLM_API_KEY="$NVIDIA_API_KEY" \
.venv/bin/python -B -m memory_system.cli agency automate \
  --teacher-provider openai \
  --teacher-base-url https://integrate.api.nvidia.com \
  --teacher-model deepseek-ai/deepseek-v4-flash \
  --prompt "Doordash me two large cheese pizzas from Dominos and stop before payment." \
  --observation "DoorDash item modal shows a large cheese pizza and Add to cart, but no quantity evidence." \
  --app-family doordash \
  --page-kind dd_item_modal \
  --out-dir memla_reports/nvidia_deepseek_v4_flash_smoke \
  --json
```

This call is not yet a live website run. It tests the teacher extraction and
compression lane using a supplied observation.

Inspect:

- `agency_automation_report.json`
- `micro_fortress_plan.json`
- `compressed_transmutation_bank.jsonl`
- `global_transmutation_ledger.json`

The smoke run passes only if:

- teacher status is completed
- response parses as structured JSON
- at least one compressed rule is produced
- the rule contains verifier and repair policy
- quantity two remains explicit
- the payment boundary remains explicit
- no secret appears in any artifact

## Local Student

The user wants a Qwen-class 7B model. On the PC, first run:

```bash
ollama list
```

Record the exact model tag, quantization, and context setting in the experiment
manifest. Do not silently call a 9B model "7B" or compare different quantizations
without recording them.

The user's PC has:

- Ryzen 5 CPU
- RTX 3060 with 12 GB VRAM
- 32 GB system RAM
- 2 TB storage

That is sufficient for a quantized 7B to 9B local student, bank retrieval,
browser observation processing, and experiment storage. It is not sufficient to
self-host DeepSeek V4 Flash at full scale.

### Three Student Stages

Do not jump directly to fine-tuning.

#### Stage A: Frozen Baseline

Run the local student with:

- task capsule
- current observation
- allowed action schema
- safety boundary

No teacher and no bank retrieval.

This establishes what the model can already do.

#### Stage B: Frozen Model Plus Bank

Keep weights identical. Add:

- top relevant compressed transmutations
- their applicability conditions
- verifier and repair policies
- negative-transfer warnings

If this improves held-out performance, the runtime-bank thesis has direct
evidence.

#### Stage C: Optional Fine-Tuning

Only after enough validated traces exist, export training examples for QLoRA or
SFT. Fine-tuning can make frequent transmutations cheaper and faster, while the
bank retains long-tail and changing knowledge.

The bank should remain even after fine-tuning because:

- UI behavior changes
- new apps appear
- rules need provenance and rollback
- rare constraints should not consume weight capacity
- negative-transfer evidence must remain inspectable

## What The Bank Should Store

A candidate agency rule should contain at least:

```json
{
  "rule_id": "numeric_quantity_visible_evidence_v1",
  "constraint_family": "numeric",
  "scope": ["commerce", "line_item_quantity"],
  "app_families": ["doordash"],
  "page_kinds": ["item_modal", "cart"],
  "preconditions": [
    "target item identity is grounded",
    "requested quantity is explicit"
  ],
  "observation_cues": [
    "quantity stepper",
    "quantity dropdown",
    "cart line item count"
  ],
  "transmutation": "Convert requested cardinality into visible UI count evidence before checkout.",
  "action_schema": "adjust_quantity_then_reinspect",
  "expected_postconditions": [
    "visible quantity equals requested quantity",
    "cart summary preserves item identity"
  ],
  "verifier": [
    "fresh observation shows quantity 2",
    "price change alone is not quantity evidence"
  ],
  "repair_policy": [
    "reinspect after asynchronous update",
    "search cart-level quantity control if item modal lacks one"
  ],
  "boundary_policy": [
    "stop before payment",
    "do not continue if quantity is unverified"
  ],
  "transfer_targets": [
    "Uber Eats",
    "Amazon",
    "Instacart"
  ],
  "support": {
    "same": 0,
    "mutated": 0,
    "sibling": 0,
    "cross_domain": 0
  },
  "failures": [],
  "confidence": 0.0,
  "source_trace_ids": []
}
```

Exact schema should follow existing dataclasses where possible. Avoid creating a
second incompatible rule system unless migration is explicit.

## Retrieval Is Part Of Intelligence

Retrieval is not just embedding similarity. A strong retrieval fortress must
teach and test:

- what is missing
- whether missing knowledge is stable or time-sensitive
- which source can answer it
- source authority
- version or app-state match
- query decomposition
- evidence sufficiency
- contradiction handling
- when to search the local bank, UI, web, or ask the teacher
- when retrieved information is unsafe to apply
- when to stop searching

For DoorDash, retrieval initially means:

- retrieve the right transmutation from the bank
- retrieve the right current UI evidence
- retrieve app-specific aliases and page behavior

Web retrieval becomes more important for changing APIs, product facts, and
open-ended tasks. It should be a separate fortress family, connected through the
same meta-ledger.

The student should not retrieve by prompt similarity alone. Ranking should
consider:

- active constraint family
- app family
- page kind
- action family
- observation cues
- risk and boundary
- prior transfer success
- freshness
- negative-transfer history

## Live Observation Contract

The next major integration is to connect `MemlaBrowserView.swift` to the Python
agency runtime.

A live observation packet should look approximately like:

```json
{
  "run_id": "run_...",
  "step_id": 4,
  "captured_at": 1780000000,
  "app_family": "doordash",
  "page_kind": "dd_item_modal",
  "url": "https://...",
  "title": "Domino's",
  "visible_text": "...",
  "capsule_slots": {
    "restaurant": "Domino's",
    "item": "cheese pizza",
    "size": "large",
    "quantity": "2"
  },
  "elements": [
    {
      "element_id": "stable-fingerprint",
      "role": "button",
      "label": "Increase quantity",
      "value": "",
      "selected": false,
      "enabled": true,
      "visible": true,
      "dom_index": 17,
      "bounds": {
        "x": 280,
        "y": 630,
        "width": 44,
        "height": 44
      },
      "safety": "safe"
    }
  ],
  "screenshot_ref": "",
  "state_hash": "..."
}
```

The Python service should return a bounded proposal:

```json
{
  "decision": "act",
  "action": {
    "type": "tap",
    "target_element_id": "stable-fingerprint"
  },
  "advances_constraint": "quantity must equal 2",
  "expected_postcondition": "fresh visible quantity changes from 1 to 2",
  "verifier": [
    "quantity text equals 2"
  ],
  "risk": "low",
  "confidence": 0.91,
  "residual_constraints": [
    "cart-level quantity verification",
    "stop before payment"
  ]
}
```

The iOS client must reject proposals whose fingerprint no longer matches the
live page. Re-observation is safer than tapping stale coordinates.

## Initial Curriculum

### Seed Family: Domino's Quantity

Use a small number of carefully chosen training cases:

- two large cheese pizzas, stepper visible
- two large cheese pizzas, quantity only in cart
- quantity control appears after scroll
- asynchronous update requires wait and reinspection
- duplicated plus buttons near different line items
- count already equals two
- count accidentally equals three and must be decremented
- item is unavailable after configuration
- cart contains a stale different pizza
- checkout visible while quantity remains unverified

### Held-Out Mutations

Hold these out before any teacher generation for training:

- prompt says "a pair of large cheese pizzas"
- quantity is a dropdown
- quantity label uses `2 items`
- a different Domino's pizza alias
- a different restaurant with equivalent flow
- quantity changes only in cart badge
- an accessibility label differs from visible text

### Sibling Transfer

After DoorDash held-outs improve:

- Uber Eats quantity stepper
- Instacart item count
- Amazon quantity dropdown

Do not add sibling traces to the bank before measuring zero-shot transfer from
the DoorDash-derived rule. After measurement, teacher rescue may create
app-specific refinements.

## Evaluation Design

Every serious result should compare at least:

| Lane | Student weights | Bank | Teacher at inference |
| --- | --- | --- | --- |
| A: raw baseline | frozen | none | no |
| B: generic scaffold | frozen | generic safety only | no |
| C: Memla bank | frozen | retrieved learned rules | no |
| D: teacher ceiling | teacher model | optional | yes |

Optional later lanes:

| Lane | Student weights | Bank | Teacher at inference |
| --- | --- | --- | --- |
| E: fine-tuned student | adapted | none | no |
| F: fine-tuned Memla | adapted | retrieved rules | no |

### Primary Metrics

- checkout-ready completion rate
- exact constraint preservation rate
- quantity verification rate
- catastrophic boundary violation rate
- non-boundary human intervention rate
- retry recovery rate
- loop or stall rate
- median and p90 steps to terminal state
- median and p90 wall time
- teacher calls per successful task
- retrieved rule precision
- tokens and cost per successful task

### Transfer Metrics

- same-case gain
- mutated-case gain
- sibling-app gain
- cross-domain gain
- negative-transfer rate
- teacher-dependence decay
- number of successful runs per promoted rule

### Initial Gate

Do not claim success from one demo.

A reasonable first software gate is:

- at least 100 frozen holdout runs across meaningful DoorDash mutations
- at least 90% checkout-ready success
- zero final payment/order submissions
- no hidden teacher calls in the student lanes
- material improvement over the same frozen raw student
- at least one quantity rule succeeds on an unseen UI representation
- all artifacts contain enough evidence to audit each success

The repository's broader consumer funding spec sets a higher DoorDash target of
92% and eventually a weighted V1 target of 93% across app families.

## Meta-Fortress Governance

The meta-fortress should never promote a rule just because one teacher emitted
it.

### Candidate

A newly compressed rule is a candidate. It has provenance but no transfer claim.

### Validated

A rule becomes validated after replay succeeds on its source micro-fortress.

### Promoted

A rule becomes runtime-active after it passes required mutation tiers and meets
minimum confidence and safety thresholds.

### Quarantined

A rule is quarantined when:

- it causes a boundary violation
- it repeatedly retrieves into irrelevant states
- its success depends on an app-specific detail absent from its scope
- it conflicts with a higher-confidence safety rule
- the source UI behavior is obsolete

### Merged

Two rules may be merged when their applicability and verifier behavior are
equivalent. Preserve source provenance and failure history.

### Split

A broad rule should be split when it succeeds in one representation and fails in
another. For example, quantity steppers and quantity dropdowns may share a
parent cardinality rule but need distinct action schemas.

### Curriculum Selection

Prefer the next teacher call that maximizes expected information gain:

- high-frequency failure
- high transfer coverage
- high student uncertainty
- low existing bank support
- strong deterministic verifier
- manageable risk

Do not spend teacher tokens repeatedly on a solved exact case.

## Teacher-Reliance Decay

Teacher reliance approaches zero in a bounded domain when:

- known constraint families cover most tasks
- observations ground those constraints reliably
- bank retrieval selects the right rules
- student uncertainty is calibrated
- repair rules handle common drift
- novel states are rare

It will not literally remain zero forever because websites change, new tasks
appear, and accounts differ. The practical goal is a very low teacher-call rate
with safe abstention when novelty appears.

Track:

```text
teacher reliance = teacher-rescued runs / total eligible runs
```

Also track teacher value:

```text
teacher value = future teacher-free successes attributable to the rescued rule
                / teacher tokens spent creating and validating that rule
```

A teacher call that produces no future independent success is data collection,
not learning.

## Bank Size And Compression

Raw traces may eventually number in the tens of thousands. Runtime intelligence
should not inject all of them.

Use three layers:

1. cold raw traces for audit and future reprocessing
2. compressed canonical rules with provenance
3. tiny per-step retrieval packets

An individual runtime packet should usually contain only a few rules and fit in
hundreds to a few thousand tokens. The bank can grow without making every action
slow if retrieval and compression remain disciplined.

Deduplicate rules by:

- constraint family
- preconditions
- action schema
- expected postcondition
- verifier
- failure boundary

Never merge rules solely because their prose is semantically similar.

## Distillation Terminology

This project uses several forms of distillation:

- behavioral distillation: the teacher demonstrates decisions in fortresses
- trace distillation: demonstrations become structured traces
- policy compression: traces become reusable transmutations
- runtime distillation: the frozen student retrieves those policies
- weight distillation: validated examples later train or adapt the student

The first useful result does not require changing model weights. Calling the
complete process "fortress-guided behavioral distillation" is accurate.

## Safety Model

Safety is part of C2A, not a layer added afterward.

Hard policies:

- no payment or order submission in development
- no password, 2FA, or CAPTCHA bypass
- no action on stale element identity
- no silent substitution of item, merchant, size, or quantity
- no success without fresh state evidence
- no repeated action loop without changed evidence
- no teacher rule may override deterministic boundary policy
- ambiguous irreversible states require user confirmation or abstention

Use test accounts and controlled addresses where possible. Redact personally
identifying text from durable teacher artifacts. The teacher usually needs the
constraint and UI structure, not the user's real name, address, phone number, or
payment details.

## Token And Cost Discipline

The free NVIDIA endpoint is useful for prototyping, but build as though teacher
calls have a real price and quota.

Token controls:

- send a focused observation packet, not the entire session
- retrieve existing rules before teacher escalation
- create one micro-fortress around the blocking constraint
- ask for strict structured output
- keep raw screenshots local unless vision is necessary
- cache static fortress instructions when a provider supports it
- avoid asking the teacher to repeat facts already in the packet
- mutate cases locally when the mutation is mechanical
- use the teacher for judgment-rich cases
- compress once, reuse many times

Record actual input/output token usage when the provider returns it. The current
agency report only estimates token counts.

## First Engineering Milestones

### M0: Reproduce And Protect The Baseline

- create the Python environment on the PC
- run the focused tests
- run the existing agency dry run
- record the exact local Qwen model
- run a raw Qwen baseline on the hard quantity case
- save artifacts under a new experiment directory

Exit criterion: another session can reproduce the same baseline from commands
and committed cases.

### M1: NVIDIA Teacher Adapter

- verify a minimal NVIDIA DeepSeek V4 Flash call
- add a named NVIDIA provider or clean OpenAI-compatible configuration
- support `reasoning_effort` without breaking other providers
- capture `reasoning_content` separately when returned
- keep final structured JSON as the compressor input
- record provider usage and request metadata
- add mocked tests; live test remains opt-in

Exit criterion: one command generates a valid, secret-free compressed quantity
rule from DeepSeek V4 Flash.

### M2: First-Class Quantity Constraints

- add quantity to `OrderSpec`
- extract digits and number words
- preserve per-item quantity
- add quantity verifier requirements
- update serialization/API contracts
- add unit tests and benchmark cases

Exit criterion: the hard prompt deterministically compiles to quantity two.

### M3: Durable Agency Bank And Retrieval

- select a canonical durable location under `.memla/`
- merge ledgers across runs rather than overwrite them
- index by constraint family, app family, page kind, and action schema
- retrieve top rules with scope and negative-transfer filtering
- expose retrieval evidence in each student trace

Exit criterion: a second process retrieves the quantity rule created by the first
process.

### M4: Local Student Agency Lane

- define the student decision JSON schema
- pass capsule, observation, allowed actions, safety rules, and retrieved rules
- parse and validate output
- reject nonexistent or stale targets
- score the student trace against expected constraint motion

Exit criterion: raw and bank-assisted runs use the same frozen local model and
produce directly comparable artifacts.

### M5: iOS Observation And Action Bridge

- send page-inspection snapshots from the iOS shell to the Python service
- return bounded action proposals
- execute safe actions through existing candidate fingerprints
- automatically capture fresh post-action state
- return verifier outcomes to Python
- preserve current final-action blocks

Exit criterion: one live DoorDash step completes through
observe -> retrieve -> student -> act -> verify.

### M6: Teacher Rescue Loop

- detect a genuinely unresolved live constraint
- freeze the relevant state into a micro-fortress
- call DeepSeek
- validate and compress the result
- replay locally without teacher help
- promote only after mutation evidence

Exit criterion: the teacher solves a failure once and the frozen student plus
bank solves the replay independently.

### M7: Holdout Transfer Benchmark

- freeze training and holdout manifests
- run lanes A through D
- include paraphrase, control-form, state, and merchant mutations
- report confidence intervals and all failures
- inspect negative transfer

Exit criterion: bank-assisted Qwen materially exceeds raw Qwen with zero boundary
violations.

### M8: Sibling-App Transfer

- test the DoorDash-derived quantity rule on Uber Eats before adding Uber-specific
  teacher data
- measure zero-shot transfer
- rescue failures with narrow app-specific refinements
- preserve the general parent rule

Exit criterion: at least one independently verified cross-app gain exists.

## Suggested First PC Session

After pulling the branch:

```bash
cd /path/to/Project-Memory
git status --short
python3 --version
```

Create or reuse the environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install pytest
```

Run the focused suite:

```bash
.venv/bin/python -B -m pytest \
  tests/test_step34_fortress_meta.py \
  tests/test_step35_coding_fortress_runner.py \
  tests/test_step36_agency_fortress.py \
  tests/test_step37_agency_automation.py \
  tests/test_ollama_client.py \
  -q
```

Run the agency dry run:

```bash
.venv/bin/python -B -m memory_system.cli agency automate --dry-run --json
```

Inspect the local model:

```bash
ollama list
```

Then complete M1 before attempting large teacher batches.

## Concrete First Ticket For Codex On The PC

Use this as the first implementation request:

> Read `MEMLA_MASTER_CONTEXT.md` completely. Inspect the existing
> `UniversalLLMClient`, agency automation CLI, tests, and generated reports.
> Implement a tested NVIDIA NIM teacher path for
> `deepseek-ai/deepseek-v4-flash` without hardcoding credentials. It must use
> the OpenAI-compatible endpoint, support configurable reasoning effort and
> output tokens, preserve reasoning content separately from final content when
> available, and keep existing Ollama/Gemini/OpenAI behavior stable. Add a
> secret-free opt-in smoke command and run the focused tests. Do not call the
> live endpoint until I confirm the environment variable is set.

After M1, the second ticket should be:

> Make quantity a first-class per-item constraint in action capsules and agency
> traces. Add parsing for digits and number words, verifier requirements,
> serialization tests, and hard DoorDash cases. Preserve existing capsule API
> behavior.

The third ticket should be:

> Implement durable agency-bank retrieval into a frozen local Qwen student lane,
> then build a baseline versus bank-assisted replay benchmark. No fine-tuning
> yet.

## Experiment Manifest

Every run directory should contain a manifest with:

- git commit and dirty-state flag
- timestamp
- fortress version
- case-pack hash
- train/holdout assignment
- teacher provider and exact model
- student provider and exact model
- quantization
- context limits
- temperature, seed, and reasoning mode
- bank version or hash
- retrieved rule IDs
- teacher-access policy for the lane
- safety policy version
- app and page-state identifiers
- token usage and estimated cost
- result and verifier evidence

Without this, improvements will be difficult to reproduce and easy to
misattribute.

## Important Experimental Warnings

### Data Leakage

Generate and freeze holdouts before teacher extraction. Similar prompts can still
leak the answer if the state structure is identical, so mutate representation
and environment, not only wording.

### Teacher Mimicry Without Competence

A student can learn to produce impressive transmutation prose while still
clicking the wrong element. Score environment outcomes separately from trace
similarity.

### Judge Bias

Teacher and student language style may affect semantic scoring. Prefer
deterministic state checks, and use a separate judge or rubric for the remainder.

### App Drift

DoorDash changes frequently. Store semantic observations and screenshots or
state hashes, not brittle selectors alone. Mark stale rules rather than silently
continuing to use them.

### Over-Broad Rules

"Always click plus until quantity matches" is unsafe when there are multiple
items. Scope rules by item identity, page state, control relationship, and
verifier.

### False Generality

DoorDash-to-Uber Eats transfer is meaningful but does not prove universal
transfer. Keep the mutation-distance label attached to every result.

### Teacher Dependency Hidden In Retrieval

A bank built from teacher traces is allowed; a fresh teacher response during a
teacher-free evaluation lane is not. Log every external call.

## Definition Of A Rich Transmutation

A rich transmutation is not long. It is complete.

It should answer:

1. What constraint is currently blocked?
2. What evidence is present?
3. What evidence is missing?
4. What state transformation is needed?
5. Which action family can produce it?
6. What preconditions make that action legal?
7. What fresh evidence will verify success?
8. What can go wrong?
9. How should failure be repaired?
10. When must the system stop or ask?
11. Which other states may share this logic?
12. What evidence supports that transfer claim?

Length without these fields is not richness.

## Long-Term Fortress Families

After the DoorDash proof, likely fortress families include:

- perception and UI state understanding
- intent and constraint extraction
- affordance grounding
- action selection
- verification and repair
- retrieval and source judgment
- clarification
- boundary and authorization
- messaging and response composition
- calendar and scheduling
- calling and reservation handling
- notification compression
- privacy and redaction
- speech understanding
- natural spoken response
- spatial display and attention allocation
- thermal, battery, and compute routing
- multi-device continuity
- coding: understand, infer, implement, verify/repair

Do not create all of these now. A fortress is justified when a recurring failure
family has a measurable verifier.

## Long-Term Product Direction

The broader product concept is:

- a dock or bridge operates the user's existing phone
- Memla sees the screen and controls it as a human would
- a lightweight ear/bracelet device carries voice, authentication, input, and
  haptics
- display glasses show decision cards by default and a full "Ghost Phone" stream
  when needed
- the phone remains the credential and application substrate while Memla becomes
  the interaction layer

The software wedge comes first:

1. reliable bounded agency in DoorDash
2. transfer to sibling phone workflows
3. low teacher dependence
4. physical touch bridge
5. remote audio and visual loop
6. broader consumer and enterprise workflows

The hardware is compelling only if the agent can act reliably. The current
software proof should therefore optimize for audited task completion, not
industrial design.

## The Core Research Questions

The project should be able to answer these with experiments:

1. How much does a retrieved transmutation bank improve a frozen 7B student?
2. Which constraint families transfer most strongly?
3. How does transfer decay with mutation distance?
4. How many validated traces are needed before teacher reliance drops?
5. Which failures come from missing knowledge versus weak constraint handling?
6. When does bank retrieval cause negative transfer?
7. Which transmutations belong in weights versus external memory?
8. Can the meta-fortress choose teacher queries more efficiently than random
   curriculum generation?
9. Can a rule extracted from one app improve an unseen sibling app?
10. Can observable decision traces predict actual action success?

These are stronger than asking whether "real intelligence emerged." They make
the idea falsifiable and cumulative.

## North-Star Rule

Every time Memla fails, ask:

> Which constraint was missing, lost, contradicted, poorly grounded, poorly
> transformed, or insufficiently verified?

Then create the smallest fortress that makes that exact capability necessary.

Every time a teacher clears that fortress, ask:

> Can the lesson be compressed into a rule that lets the frozen student clear a
> meaningfully different case without the teacher?

If yes, the bank learned something.

If no, keep the trace as evidence, diagnose why transfer failed, and do not
pretend accumulation alone is intelligence.

## Final Direction To The Next Session

Start small enough to measure and complete enough to matter.

The first victory is not "Qwen 7B is now DeepSeek." The first victory is:

> The same frozen local Qwen model failed an unseen DoorDash quantity task,
> retrieved a transmutation extracted from a different teacher-cleared fortress,
> completed the task correctly, proved quantity and item identity from fresh UI
> evidence, and stopped before payment, with no teacher call.

That is a real result. Build that loop, measure it honestly, and then widen the
fortress.
