# Agency Quantity Authentic Replay

- Student model: `mistral:7b-instruct`
- Trials per holdout: 2
- Raw successes: 11
- Full-rule successes: 18
- Delta: 7
- Teacher calls: 0

## Authenticity

- bank_packet_only_intentional_difference: `True`
- candidate_metadata_visible: `True`
- candidate_rule_from_nvidia_response: `False`
- expected_student_request_count: `80`
- external_teacher_requests_in_student_lanes: `0`
- hardcoded_policy_selected_student_actions: `False`
- holdouts_frozen_before_teacher: `True`
- legacy_replay_was_deterministic_policy: `True`
- model_authentic_replay_enabled: `True`
- provider_response_metadata_present: `True`
- retrieved_rule_ids: `['agency_numeric_quantity_visible_evidence_v1']`
- retrieved_rule_provenance_hash_mismatch_count: `0`
- state_machine_scored_resulting_state: `True`
- student_action_executed_count: `80`
- student_lanes_attempted_requests: `True`
- student_lanes_executed_actions: `True`
- student_lanes_made_real_requests: `True`
- student_lanes_parsed_responses: `True`
- student_lanes_received_responses: `True`
- student_request_attempt_count: `80`
- student_response_parsed_count: `80`
- student_response_received_count: `80`
- teacher_free_student_lanes: `True`

## Paired Discordance

| Lane | Raw Only | Lane Only | p |
| --- | ---: | ---: | ---: |
| full_rich_rule | 0 | 7 | 0.015625 |
| condition_action_policy | 0 | 7 | 0.015625 |
