# Agency Quantity Authentic Replay

- Student model: `mistral:7b-instruct`
- Trials per holdout: 1
- Raw successes: 7
- Full-rule successes: 7
- Delta: 0
- Teacher calls: 0

## Authenticity

- bank_packet_only_intentional_difference: `True`
- candidate_metadata_visible: `False`
- candidate_rule_from_nvidia_response: `False`
- expected_student_request_count: `48`
- external_teacher_requests_in_student_lanes: `0`
- hardcoded_policy_selected_student_actions: `False`
- holdouts_frozen_before_teacher: `True`
- legacy_replay_was_deterministic_policy: `True`
- model_authentic_replay_enabled: `True`
- provider_response_metadata_present: `True`
- retrieved_rule_ids: `['agency_numeric_quantity_visible_evidence_v1']`
- retrieved_rule_provenance_hash_mismatch_count: `0`
- state_machine_scored_resulting_state: `True`
- student_action_executed_count: `47`
- student_lanes_attempted_requests: `True`
- student_lanes_executed_actions: `False`
- student_lanes_made_real_requests: `True`
- student_lanes_parsed_responses: `False`
- student_lanes_received_responses: `True`
- student_request_attempt_count: `48`
- student_response_parsed_count: `47`
- student_response_received_count: `48`
- teacher_free_student_lanes: `True`

## Paired Discordance

| Lane | Raw Only | Lane Only | p |
| --- | ---: | ---: | ---: |
| full_rich_rule | 0 | 0 | 1.0 |
| transmutation_sentence | 0 | 0 | 1.0 |
| condition_action_policy | 1 | 0 | 1.0 |
| verifier_only | 2 | 0 | 0.5 |
| boundary_policy_only | 1 | 0 | 1.0 |
