# Agency Quantity Authentic Replay

- Student model: `mistral:7b-instruct`
- Trials per holdout: 10
- Raw successes: 62
- Full-rule successes: 86
- Delta: 24
- Teacher calls: 0

## Authenticity

- bank_packet_only_intentional_difference: `True`
- candidate_metadata_visible: `True`
- candidate_rule_from_nvidia_response: `False`
- expected_student_request_count: `546`
- external_teacher_requests_in_student_lanes: `0`
- hardcoded_policy_selected_student_actions: `False`
- holdouts_frozen_before_teacher: `True`
- legacy_replay_was_deterministic_policy: `True`
- model_authentic_replay_enabled: `True`
- provider_response_metadata_present: `True`
- retrieved_rule_ids: `['agency_numeric_quantity_visible_evidence_v1']`
- retrieved_rule_provenance_hash_mismatch_count: `0`
- state_machine_scored_resulting_state: `True`
- student_action_executed_count: `536`
- student_lanes_attempted_requests: `True`
- student_lanes_executed_actions: `False`
- student_lanes_made_real_requests: `True`
- student_lanes_parsed_responses: `False`
- student_lanes_received_responses: `True`
- student_request_attempt_count: `546`
- student_response_parsed_count: `536`
- student_response_received_count: `546`
- teacher_free_student_lanes: `True`

## Paired Discordance

| Lane | Raw Only | Lane Only | p |
| --- | ---: | ---: | ---: |
| full_rich_rule | 3 | 27 | 8e-06 |
| condition_action_policy | 2 | 28 | 1e-06 |
| seeded_full_rule | 3 | 28 | 5e-06 |

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
| multi_step_quantity_adjustment | condition_action_policy | 30 | 30 |
| multi_step_quantity_adjustment | full_rich_rule | 27 | 30 |
| multi_step_quantity_adjustment | raw | 10 | 30 |
| multi_step_quantity_adjustment | seeded_full_rule | 29 | 30 |
| quantity_already_grounded | condition_action_policy | 20 | 20 |
| quantity_already_grounded | full_rich_rule | 19 | 20 |
| quantity_already_grounded | raw | 20 | 20 |
| quantity_already_grounded | seeded_full_rule | 18 | 20 |
| quantity_increment_repair | condition_action_policy | 20 | 20 |
| quantity_increment_repair | full_rich_rule | 20 | 20 |
| quantity_increment_repair | raw | 15 | 20 |
| quantity_increment_repair | seeded_full_rule | 20 | 20 |
| scoped_affordance_grounding | condition_action_policy | 8 | 10 |
| scoped_affordance_grounding | full_rich_rule | 10 | 10 |
| scoped_affordance_grounding | raw | 10 | 10 |
| scoped_affordance_grounding | seeded_full_rule | 10 | 10 |
| sibling_app_transfer | condition_action_policy | 10 | 10 |
| sibling_app_transfer | full_rich_rule | 10 | 10 |
| sibling_app_transfer | raw | 7 | 10 |
| sibling_app_transfer | seeded_full_rule | 10 | 10 |
