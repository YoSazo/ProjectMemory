# Agency Quantity Authentic Replay

- Student model: `mistral:7b-instruct`
- Trials per holdout: 10
- Raw successes: 73
- Full-rule successes: 90
- Delta: 17
- Teacher calls: 0

## Authenticity

- bank_packet_only_intentional_difference: `True`
- candidate_metadata_visible: `False`
- candidate_rule_from_nvidia_response: `False`
- expected_student_request_count: `547`
- external_teacher_requests_in_student_lanes: `0`
- hardcoded_policy_selected_student_actions: `False`
- holdouts_frozen_before_teacher: `True`
- legacy_replay_was_deterministic_policy: `True`
- model_authentic_replay_enabled: `True`
- provider_response_metadata_present: `True`
- retrieved_rule_ids: `['agency_numeric_quantity_visible_evidence_v1']`
- retrieved_rule_provenance_hash_mismatch_count: `0`
- state_machine_scored_resulting_state: `True`
- student_action_executed_count: `521`
- student_lanes_attempted_requests: `True`
- student_lanes_executed_actions: `False`
- student_lanes_made_real_requests: `True`
- student_lanes_parsed_responses: `False`
- student_lanes_received_responses: `True`
- student_request_attempt_count: `547`
- student_response_parsed_count: `521`
- student_response_received_count: `547`
- teacher_free_student_lanes: `True`

## Paired Discordance

| Lane | Raw Only | Lane Only | p |
| --- | ---: | ---: | ---: |
| full_rich_rule | 0 | 17 | 1.5e-05 |
| condition_action_policy | 16 | 12 | 0.571588 |
| seeded_full_rule | 0 | 17 | 1.5e-05 |

## Constraint Families

| Family | Lane | Success | Trials |
| --- | --- | ---: | ---: |
| boundary_stop_no_applicable_control | condition_action_policy | 0 | 10 |
| boundary_stop_no_applicable_control | full_rich_rule | 0 | 10 |
| boundary_stop_no_applicable_control | raw | 0 | 10 |
| boundary_stop_no_applicable_control | seeded_full_rule | 0 | 10 |
| item_alias_numeric_distractor | condition_action_policy | 0 | 10 |
| item_alias_numeric_distractor | full_rich_rule | 0 | 10 |
| item_alias_numeric_distractor | raw | 0 | 10 |
| item_alias_numeric_distractor | seeded_full_rule | 0 | 10 |
| multi_step_quantity_adjustment | condition_action_policy | 23 | 30 |
| multi_step_quantity_adjustment | full_rich_rule | 30 | 30 |
| multi_step_quantity_adjustment | raw | 21 | 30 |
| multi_step_quantity_adjustment | seeded_full_rule | 30 | 30 |
| quantity_already_grounded | condition_action_policy | 14 | 20 |
| quantity_already_grounded | full_rich_rule | 20 | 20 |
| quantity_already_grounded | raw | 16 | 20 |
| quantity_already_grounded | seeded_full_rule | 20 | 20 |
| quantity_increment_repair | condition_action_policy | 14 | 20 |
| quantity_increment_repair | full_rich_rule | 20 | 20 |
| quantity_increment_repair | raw | 16 | 20 |
| quantity_increment_repair | seeded_full_rule | 20 | 20 |
| scoped_affordance_grounding | condition_action_policy | 10 | 10 |
| scoped_affordance_grounding | full_rich_rule | 10 | 10 |
| scoped_affordance_grounding | raw | 10 | 10 |
| scoped_affordance_grounding | seeded_full_rule | 10 | 10 |
| sibling_app_transfer | condition_action_policy | 8 | 10 |
| sibling_app_transfer | full_rich_rule | 10 | 10 |
| sibling_app_transfer | raw | 10 | 10 |
| sibling_app_transfer | seeded_full_rule | 10 | 10 |
