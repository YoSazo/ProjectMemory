# Agency Opaque Retrieval Proof

- Teacher: `qwen2.5:32b`
- Student/retriever: `mistral:7b-instruct`
- Holdouts: `10`
- Trials per holdout: `3`
- Retrieval accuracy: `1.0`
- Raw model proposal accuracy: `0.8`
- Teacher calls in student lanes: `0`

## Lane Results

| Lane | First pass | Final |
| --- | ---: | ---: |
| raw | 9 | 9 |
| retrieved_counterfactual_control | 12 | 2 |
| retrieved_teacher_capsule | 16 | 30 |
| wrong_retrieval_control | 10 | 5 |

## Retrieval

- `alias_numeric_role_grounding`: `15/15`
- `missing_affordance_boundary_stop`: `15/15`

## Case-Clustered Comparisons

- `retrieved_teacher_capsule`: first pass better/worse `3/0` (p `0.25`); final better/worse `7/0` (p `0.015625`).
- `wrong_retrieval_control`: first pass better/worse `4/3` (p `1.0`); final better/worse `0/2` (p `0.5`).
- `retrieved_counterfactual_control`: first pass better/worse `3/1` (p `0.625`); final better/worse `0/3` (p `0.25`).

## Authenticity

- action_hidden_oracle_leaks: `0`
- action_prompt_difference_is_bank_only: `True`
- action_prompt_mismatches: `0`
- contract_repair_attempts: `46`
- deterministic_policy_selected_actions: `False`
- deterministic_retriever_selected_rules: `True`
- final_retrieval_uses_only_teacher_declared_predicates: `True`
- model_proposals_select_rules_before_verification: `True`
- opaque_rule_keys: `True`
- retrieval_hidden_oracle_leaks: `0`
- retrieval_model_requests_made: `30`
- retriever_catalog_hides_actions: `True`
- teacher_predicate_repairs: `6`
