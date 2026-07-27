# Agency Quantity Authentic Replay

- Student model: `mistral:7b-instruct`
- Trials per holdout: 10
- Primary bank lane: `nvidia_semantic_compiled`
- Raw successes: 62
- Primary bank successes: 89
- Delta: 27
- Teacher calls: 0

## Authenticity

- bank_packet_only_intentional_difference: `True`
- candidate_metadata_visible: `True`
- candidate_rule_from_nvidia_response: `True`
- compiler_only_no_teacher_uses_control_compiler: `True`
- expected_student_request_count: `948`
- external_teacher_requests_in_student_lanes: `0`
- hardcoded_policy_selected_student_actions: `False`
- holdouts_frozen_before_teacher: `True`
- legacy_replay_was_deterministic_policy: `True`
- model_authentic_replay_enabled: `True`
- nvidia_quarantine_reason: `prior measured negative transfer and live rule transfer scope omits ubereats; retrieval requires explicit transfer target`
- nvidia_rule_quarantined_from_ubereats: `True`
- nvidia_semantic_compiler_clause_rule_ids: `['atm_numeric_1b355ba923c4']`
- nvidia_semantic_compiler_invents_quantity_actions: `False`
- nvidia_ubereats_retrieval_count: `0`
- placebo_numeric_rule_uses_control_compiler: `True`
- provider_response_metadata_present: `True`
- retrieved_rule_ids: `['agency_numeric_quantity_visible_evidence_v1', 'atm_numeric_1b355ba923c4', 'compiler_only_numeric_control_v0', 'placebo_numeric_rule_v0']`
- retrieved_rule_provenance_hash_mismatch_count: `0`
- state_machine_scored_resulting_state: `True`
- student_action_executed_count: `852`
- student_lanes_attempted_requests: `True`
- student_lanes_executed_actions: `False`
- student_lanes_made_real_requests: `True`
- student_lanes_parsed_responses: `False`
- student_lanes_received_responses: `True`
- student_request_attempt_count: `948`
- student_response_parsed_count: `852`
- student_response_received_count: `948`
- teacher_free_student_lanes: `True`

## Paired Discordance

| Lane | Raw Only | Lane Only | p |
| --- | ---: | ---: | ---: |
| compiler_only_no_teacher | 29 | 12 | 0.011508 |
| placebo_numeric_rule_compiled | 22 | 21 | 1.0 |
| nvidia_constraint_family_only | 10 | 7 | 0.629059 |
| nvidia_semantic_compiled | 1 | 28 | 0.0 |
| authentic_nvidia_full_rule | 8 | 7 | 1.0 |
| seeded_full_rule | 6 | 28 | 0.000195 |

## Teacher

- Status: `completed`
- Model: `deepseek-ai/deepseek-v4-flash`
- Rule ID: `atm_numeric_1b355ba923c4`
- Teacher trace: `trace_ungrounded_numeric_50ea464239a2`
- Raw response hash: `9dcb5339ae724ff3d3165f6fa1c23fb260c4777a0f78521cdf6f0c64b4b274c9`
- Compressed rule hash: `185fcd6b74fe6cda26fe41473a61fe1fb233532f3e25eaf4bf90ce9db0b239e9`

## Compressed Teacher Rule Fields

- Constraint family: `numeric`
- Transmutation: `ground_numeric_constraint_same`
- Action schema: `adjust quantity via stepper or plus/minus button until visible count equals 2, then verify in cart`
- Transfer targets: `['same app', 'current page-kind', 'numeric cardinality preservation', 'cart verification']`
- Boundary policy: `['do not cross payment/order boundary', 'stop before final confirmation']`
- Teacher clauses: `{'applicability_conditions': ['quantity control shows 2', 'cart summary shows 2'], 'comparison_operation': 'compare_visible_count_to_requested_quantity', 'action_when_below_target': 'choose increment/plus/stepper control scoped to requested item', 'action_when_above_target': 'choose decrement/minus/stepper control scoped to requested item', 'action_when_equal': 'verify visible count; do not adjust', 'target_scoping_rule': 'requested item scope required', 'expected_postcondition': 'visible quantity equals 2 in item modal or cart; price alone is not accepted as quantity evidence', 'verifier': ['visible quantity equals 2 in item modal or cart', 'price alone is not accepted as quantity evidence'], 'repair': ['find plus/minus, stepper, dropdown, or duplicate-item control', 'after changing quantity, re-inspect and compare visible count', 'if no count evidence exists, stop and request clarification before checkout'], 'negative_preconditions': [], 'transfer_scope': ['same app', 'current page-kind', 'numeric cardinality preservation', 'cart verification'], 'boundary_stop': 'stop before payment/final confirmation', 'teacher_actions_present': {'below': True, 'above': True, 'equal': True, 'boundary_stop': True}}`

## Constraint Families

| Family | Lane | Success | Trials |
| --- | --- | ---: | ---: |
| boundary_stop_no_applicable_control | authentic_nvidia_full_rule | 0 | 10 |
| boundary_stop_no_applicable_control | compiler_only_no_teacher | 0 | 10 |
| boundary_stop_no_applicable_control | nvidia_constraint_family_only | 0 | 10 |
| boundary_stop_no_applicable_control | nvidia_semantic_compiled | 0 | 10 |
| boundary_stop_no_applicable_control | placebo_numeric_rule_compiled | 0 | 10 |
| boundary_stop_no_applicable_control | raw | 0 | 10 |
| boundary_stop_no_applicable_control | seeded_full_rule | 0 | 10 |
| item_alias_numeric_distractor | authentic_nvidia_full_rule | 0 | 10 |
| item_alias_numeric_distractor | compiler_only_no_teacher | 0 | 10 |
| item_alias_numeric_distractor | nvidia_constraint_family_only | 0 | 10 |
| item_alias_numeric_distractor | nvidia_semantic_compiled | 0 | 10 |
| item_alias_numeric_distractor | placebo_numeric_rule_compiled | 0 | 10 |
| item_alias_numeric_distractor | raw | 0 | 10 |
| item_alias_numeric_distractor | seeded_full_rule | 0 | 10 |
| multi_step_quantity_adjustment | authentic_nvidia_full_rule | 10 | 30 |
| multi_step_quantity_adjustment | compiler_only_no_teacher | 13 | 30 |
| multi_step_quantity_adjustment | nvidia_constraint_family_only | 12 | 30 |
| multi_step_quantity_adjustment | nvidia_semantic_compiled | 29 | 30 |
| multi_step_quantity_adjustment | placebo_numeric_rule_compiled | 16 | 30 |
| multi_step_quantity_adjustment | raw | 11 | 30 |
| multi_step_quantity_adjustment | seeded_full_rule | 26 | 30 |
| quantity_already_grounded | authentic_nvidia_full_rule | 20 | 20 |
| quantity_already_grounded | compiler_only_no_teacher | 13 | 20 |
| quantity_already_grounded | nvidia_constraint_family_only | 20 | 20 |
| quantity_already_grounded | nvidia_semantic_compiled | 20 | 20 |
| quantity_already_grounded | placebo_numeric_rule_compiled | 11 | 20 |
| quantity_already_grounded | raw | 20 | 20 |
| quantity_already_grounded | seeded_full_rule | 18 | 20 |
| quantity_increment_repair | authentic_nvidia_full_rule | 20 | 20 |
| quantity_increment_repair | compiler_only_no_teacher | 13 | 20 |
| quantity_increment_repair | nvidia_constraint_family_only | 8 | 20 |
| quantity_increment_repair | nvidia_semantic_compiled | 20 | 20 |
| quantity_increment_repair | placebo_numeric_rule_compiled | 20 | 20 |
| quantity_increment_repair | raw | 14 | 20 |
| quantity_increment_repair | seeded_full_rule | 20 | 20 |
| scoped_affordance_grounding | authentic_nvidia_full_rule | 10 | 10 |
| scoped_affordance_grounding | compiler_only_no_teacher | 1 | 10 |
| scoped_affordance_grounding | nvidia_constraint_family_only | 10 | 10 |
| scoped_affordance_grounding | nvidia_semantic_compiled | 10 | 10 |
| scoped_affordance_grounding | placebo_numeric_rule_compiled | 8 | 10 |
| scoped_affordance_grounding | raw | 10 | 10 |
| scoped_affordance_grounding | seeded_full_rule | 10 | 10 |
| sibling_app_transfer | authentic_nvidia_full_rule | 1 | 10 |
| sibling_app_transfer | compiler_only_no_teacher | 5 | 10 |
| sibling_app_transfer | nvidia_constraint_family_only | 9 | 10 |
| sibling_app_transfer | nvidia_semantic_compiled | 10 | 10 |
| sibling_app_transfer | placebo_numeric_rule_compiled | 6 | 10 |
| sibling_app_transfer | raw | 7 | 10 |
| sibling_app_transfer | seeded_full_rule | 10 | 10 |
