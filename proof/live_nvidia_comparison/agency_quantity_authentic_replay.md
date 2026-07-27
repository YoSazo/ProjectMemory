# Agency Quantity Authentic Replay

- Student model: `mistral:7b-instruct`
- Trials per holdout: 10
- Primary bank lane: `authentic_nvidia_condition_action_policy`
- Raw successes: 62
- Primary bank successes: 76
- Delta: 14
- Teacher calls: 1

## Authenticity

- bank_packet_only_intentional_difference: `True`
- candidate_metadata_visible: `True`
- candidate_rule_from_nvidia_response: `True`
- expected_student_request_count: `556`
- external_teacher_requests_in_student_lanes: `0`
- hardcoded_policy_selected_student_actions: `False`
- holdouts_frozen_before_teacher: `True`
- legacy_replay_was_deterministic_policy: `True`
- model_authentic_replay_enabled: `True`
- nvidia_response_hash: `9dcb5339ae724ff3d3165f6fa1c23fb260c4777a0f78521cdf6f0c64b4b274c9`
- provider_response_metadata_present: `True`
- retrieved_rule_ids: `['agency_numeric_quantity_visible_evidence_v1', 'atm_numeric_1b355ba923c4']`
- retrieved_rule_provenance_hash_mismatch_count: `0`
- state_machine_scored_resulting_state: `True`
- student_action_executed_count: `533`
- student_lanes_attempted_requests: `True`
- student_lanes_executed_actions: `False`
- student_lanes_made_real_requests: `True`
- student_lanes_parsed_responses: `False`
- student_lanes_received_responses: `True`
- student_request_attempt_count: `556`
- student_response_parsed_count: `533`
- student_response_received_count: `556`
- teacher_free_student_lanes: `True`

## Paired Discordance

| Lane | Raw Only | Lane Only | p |
| --- | ---: | ---: | ---: |
| seeded_full_rule | 3 | 28 | 5e-06 |
| authentic_nvidia_full_rule | 8 | 7 | 1.0 |
| authentic_nvidia_condition_action_policy | 11 | 25 | 0.028817 |

## Teacher

- Status: `completed`
- Model: `deepseek-ai/deepseek-v4-flash`
- Rule ID: `atm_numeric_1b355ba923c4`
- Teacher trace: `trace_ungrounded_numeric_50ea464239a2`
- Raw response hash: `9dcb5339ae724ff3d3165f6fa1c23fb260c4777a0f78521cdf6f0c64b4b274c9`
- Compressed rule hash: `185fcd6b74fe6cda26fe41473a61fe1fb233532f3e25eaf4bf90ce9db0b239e9`

## Constraint Families

| Family | Lane | Success | Trials |
| --- | --- | ---: | ---: |
| boundary_stop_no_applicable_control | authentic_nvidia_condition_action_policy | 0 | 10 |
| boundary_stop_no_applicable_control | authentic_nvidia_full_rule | 0 | 10 |
| boundary_stop_no_applicable_control | raw | 0 | 10 |
| boundary_stop_no_applicable_control | seeded_full_rule | 0 | 10 |
| item_alias_numeric_distractor | authentic_nvidia_condition_action_policy | 0 | 10 |
| item_alias_numeric_distractor | authentic_nvidia_full_rule | 0 | 10 |
| item_alias_numeric_distractor | raw | 0 | 10 |
| item_alias_numeric_distractor | seeded_full_rule | 0 | 10 |
| multi_step_quantity_adjustment | authentic_nvidia_condition_action_policy | 28 | 30 |
| multi_step_quantity_adjustment | authentic_nvidia_full_rule | 10 | 30 |
| multi_step_quantity_adjustment | raw | 10 | 30 |
| multi_step_quantity_adjustment | seeded_full_rule | 29 | 30 |
| quantity_already_grounded | authentic_nvidia_condition_action_policy | 19 | 20 |
| quantity_already_grounded | authentic_nvidia_full_rule | 20 | 20 |
| quantity_already_grounded | raw | 20 | 20 |
| quantity_already_grounded | seeded_full_rule | 18 | 20 |
| quantity_increment_repair | authentic_nvidia_condition_action_policy | 20 | 20 |
| quantity_increment_repair | authentic_nvidia_full_rule | 20 | 20 |
| quantity_increment_repair | raw | 15 | 20 |
| quantity_increment_repair | seeded_full_rule | 20 | 20 |
| scoped_affordance_grounding | authentic_nvidia_condition_action_policy | 8 | 10 |
| scoped_affordance_grounding | authentic_nvidia_full_rule | 10 | 10 |
| scoped_affordance_grounding | raw | 10 | 10 |
| scoped_affordance_grounding | seeded_full_rule | 10 | 10 |
| sibling_app_transfer | authentic_nvidia_condition_action_policy | 1 | 10 |
| sibling_app_transfer | authentic_nvidia_full_rule | 1 | 10 |
| sibling_app_transfer | raw | 7 | 10 |
| sibling_app_transfer | seeded_full_rule | 10 | 10 |
