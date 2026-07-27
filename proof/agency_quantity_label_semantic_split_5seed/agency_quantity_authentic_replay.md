# Agency Quantity Authentic Replay

- Student model: `mistral:7b-instruct`
- Trials per holdout: 5
- Primary bank lane: `nvidia_semantic_compiled`
- Raw successes: 45
- Primary bank successes: 29
- Delta: -16
- Teacher calls: 0

## Authenticity

- bank_packet_only_intentional_difference: `True`
- candidate_metadata_visible: `True`
- candidate_rule_from_nvidia_response: `True`
- compiler_only_no_teacher_uses_control_compiler: `False`
- empty_retrieval_prompt_mismatch_count: `0`
- empty_retrieval_prompt_pair_count: `50`
- empty_retrieval_prompts_match_raw: `True`
- expected_student_request_count: `949`
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
- placebo_numeric_rule_uses_control_compiler: `False`
- provider_response_metadata_present: `True`
- retrieved_rule_ids: `['atm_numeric_1b355ba923c4', 'minimal_label_numeric_price_control_v0', 'minimal_label_numeric_quantity_control_v0', 'minimal_label_random_control_v0', 'minimal_label_text_identity_control_v0']`
- retrieved_rule_provenance_hash_mismatch_count: `0`
- state_machine_scored_resulting_state: `True`
- student_action_executed_count: `852`
- student_lanes_attempted_requests: `True`
- student_lanes_executed_actions: `False`
- student_lanes_made_real_requests: `True`
- student_lanes_parsed_responses: `False`
- student_lanes_received_responses: `True`
- student_request_attempt_count: `949`
- student_response_parsed_count: `852`
- student_response_received_count: `949`
- teacher_free_student_lanes: `True`

## Paired Discordance

| Lane | Raw Only | Lane Only | p |
| --- | ---: | ---: | ---: |
| minimal_label_numeric_quantity | 0 | 15 | 6.1035156e-05 |
| minimal_label_numeric_price | 0 | 5 | 0.0625 |
| minimal_label_text_identity | 3 | 1 | 0.625 |
| minimal_label_random | 1 | 1 | 1.0 |
| nvidia_semantic_compiled | 21 | 5 | 0.002493917942 |
| nvidia_semantic_no_below_increment | 34 | 0 | 1.16e-10 |
| nvidia_semantic_no_above_decrement | 16 | 13 | 0.711071103811 |
| nvidia_semantic_swap_increment_decrement | 9 | 11 | 0.823802947998 |
| nvidia_semantic_no_verifier | 0 | 13 | 0.000244140625 |

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
| boundary_stop_no_applicable_control | minimal_label_numeric_price | 0 | 5 |
| boundary_stop_no_applicable_control | minimal_label_numeric_quantity | 0 | 5 |
| boundary_stop_no_applicable_control | minimal_label_random | 0 | 5 |
| boundary_stop_no_applicable_control | minimal_label_text_identity | 0 | 5 |
| boundary_stop_no_applicable_control | nvidia_semantic_compiled | 0 | 5 |
| boundary_stop_no_applicable_control | nvidia_semantic_no_above_decrement | 0 | 5 |
| boundary_stop_no_applicable_control | nvidia_semantic_no_below_increment | 0 | 5 |
| boundary_stop_no_applicable_control | nvidia_semantic_no_verifier | 0 | 5 |
| boundary_stop_no_applicable_control | nvidia_semantic_swap_increment_decrement | 0 | 5 |
| boundary_stop_no_applicable_control | raw | 0 | 5 |
| item_alias_numeric_distractor | minimal_label_numeric_price | 0 | 5 |
| item_alias_numeric_distractor | minimal_label_numeric_quantity | 0 | 5 |
| item_alias_numeric_distractor | minimal_label_random | 0 | 5 |
| item_alias_numeric_distractor | minimal_label_text_identity | 0 | 5 |
| item_alias_numeric_distractor | nvidia_semantic_compiled | 0 | 5 |
| item_alias_numeric_distractor | nvidia_semantic_no_above_decrement | 0 | 5 |
| item_alias_numeric_distractor | nvidia_semantic_no_below_increment | 0 | 5 |
| item_alias_numeric_distractor | nvidia_semantic_no_verifier | 0 | 5 |
| item_alias_numeric_distractor | nvidia_semantic_swap_increment_decrement | 0 | 5 |
| item_alias_numeric_distractor | raw | 0 | 5 |
| multi_step_quantity_adjustment | minimal_label_numeric_price | 16 | 25 |
| multi_step_quantity_adjustment | minimal_label_numeric_quantity | 25 | 25 |
| multi_step_quantity_adjustment | minimal_label_random | 15 | 25 |
| multi_step_quantity_adjustment | minimal_label_text_identity | 15 | 25 |
| multi_step_quantity_adjustment | nvidia_semantic_compiled | 4 | 25 |
| multi_step_quantity_adjustment | nvidia_semantic_no_above_decrement | 16 | 25 |
| multi_step_quantity_adjustment | nvidia_semantic_no_below_increment | 0 | 25 |
| multi_step_quantity_adjustment | nvidia_semantic_no_verifier | 23 | 25 |
| multi_step_quantity_adjustment | nvidia_semantic_swap_increment_decrement | 17 | 25 |
| multi_step_quantity_adjustment | raw | 15 | 25 |
| quantity_already_grounded | minimal_label_numeric_price | 10 | 10 |
| quantity_already_grounded | minimal_label_numeric_quantity | 10 | 10 |
| quantity_already_grounded | minimal_label_random | 10 | 10 |
| quantity_already_grounded | minimal_label_text_identity | 10 | 10 |
| quantity_already_grounded | nvidia_semantic_compiled | 10 | 10 |
| quantity_already_grounded | nvidia_semantic_no_above_decrement | 6 | 10 |
| quantity_already_grounded | nvidia_semantic_no_below_increment | 5 | 10 |
| quantity_already_grounded | nvidia_semantic_no_verifier | 10 | 10 |
| quantity_already_grounded | nvidia_semantic_swap_increment_decrement | 10 | 10 |
| quantity_already_grounded | raw | 10 | 10 |
| quantity_decrement_repair | minimal_label_numeric_price | 5 | 5 |
| quantity_decrement_repair | minimal_label_numeric_quantity | 5 | 5 |
| quantity_decrement_repair | minimal_label_random | 5 | 5 |
| quantity_decrement_repair | minimal_label_text_identity | 5 | 5 |
| quantity_decrement_repair | nvidia_semantic_compiled | 0 | 5 |
| quantity_decrement_repair | nvidia_semantic_no_above_decrement | 0 | 5 |
| quantity_decrement_repair | nvidia_semantic_no_below_increment | 1 | 5 |
| quantity_decrement_repair | nvidia_semantic_no_verifier | 5 | 5 |
| quantity_decrement_repair | nvidia_semantic_swap_increment_decrement | 0 | 5 |
| quantity_decrement_repair | raw | 5 | 5 |
| quantity_increment_repair | minimal_label_numeric_price | 9 | 10 |
| quantity_increment_repair | minimal_label_numeric_quantity | 10 | 10 |
| quantity_increment_repair | minimal_label_random | 5 | 10 |
| quantity_increment_repair | minimal_label_text_identity | 3 | 10 |
| quantity_increment_repair | nvidia_semantic_compiled | 10 | 10 |
| quantity_increment_repair | nvidia_semantic_no_above_decrement | 10 | 10 |
| quantity_increment_repair | nvidia_semantic_no_below_increment | 0 | 10 |
| quantity_increment_repair | nvidia_semantic_no_verifier | 10 | 10 |
| quantity_increment_repair | nvidia_semantic_swap_increment_decrement | 10 | 10 |
| quantity_increment_repair | raw | 5 | 10 |
| scoped_affordance_grounding | minimal_label_numeric_price | 5 | 5 |
| scoped_affordance_grounding | minimal_label_numeric_quantity | 5 | 5 |
| scoped_affordance_grounding | minimal_label_random | 5 | 5 |
| scoped_affordance_grounding | minimal_label_text_identity | 5 | 5 |
| scoped_affordance_grounding | nvidia_semantic_compiled | 0 | 5 |
| scoped_affordance_grounding | nvidia_semantic_no_above_decrement | 5 | 5 |
| scoped_affordance_grounding | nvidia_semantic_no_below_increment | 0 | 5 |
| scoped_affordance_grounding | nvidia_semantic_no_verifier | 5 | 5 |
| scoped_affordance_grounding | nvidia_semantic_swap_increment_decrement | 5 | 5 |
| scoped_affordance_grounding | raw | 5 | 5 |
| sibling_app_transfer | minimal_label_numeric_price | 5 | 5 |
| sibling_app_transfer | minimal_label_numeric_quantity | 5 | 5 |
| sibling_app_transfer | minimal_label_random | 5 | 5 |
| sibling_app_transfer | minimal_label_text_identity | 5 | 5 |
| sibling_app_transfer | nvidia_semantic_compiled | 5 | 5 |
| sibling_app_transfer | nvidia_semantic_no_above_decrement | 5 | 5 |
| sibling_app_transfer | nvidia_semantic_no_below_increment | 5 | 5 |
| sibling_app_transfer | nvidia_semantic_no_verifier | 5 | 5 |
| sibling_app_transfer | nvidia_semantic_swap_increment_decrement | 5 | 5 |
| sibling_app_transfer | raw | 5 | 5 |
