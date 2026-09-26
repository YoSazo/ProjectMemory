# Agency Opaque Retrieval Proof

- Teacher: `qwen2.5:32b`
- Student/retriever: `mistral:7b-instruct`
- Case pack: `cross-app`
- Holdouts: `6`
- Trials per holdout: `3`
- Retrieval accuracy: `1.0`
- Raw model proposal accuracy: `1.0`
- Teacher calls in student lanes: `0`
- Teacher/evaluation case overlap: `0`

## Lane Results

| Lane | First pass | Final |
| --- | ---: | ---: |
| raw | 9 | 9 |
| retrieved_counterfactual_control | 3 | 0 |
| retrieved_teacher_capsule | 10 | 17 |
| wrong_retrieval_control | 6 | 0 |

## Retrieval

- `alias_numeric_role_grounding`: `9/9`
- `missing_affordance_boundary_stop`: `9/9`

## Case-Clustered Comparisons

- `retrieved_teacher_capsule`: first pass better/worse `2/1` (p `1.0`); final better/worse `4/0` (p `0.125`).
- `wrong_retrieval_control`: first pass better/worse `2/3` (p `1.0`); final better/worse `0/4` (p `0.125`).
- `retrieved_counterfactual_control`: first pass better/worse `0/3` (p `0.25`); final better/worse `0/4` (p `0.125`).

## Authenticity

- action_hidden_oracle_leaks: `0`
- action_prompt_difference_is_bank_only: `True`
- action_prompt_mismatches: `0`
- contract_repair_attempts: `25`
- contract_repair_requests: `39`
- deterministic_policy_selected_actions: `False`
- deterministic_retriever_selected_rules: `False`
- final_retrieval_uses_only_teacher_declared_predicates: `True`
- model_proposals_select_rules_before_verification: `True`
- opaque_rule_keys: `True`
- retrieval_hidden_oracle_leaks: `0`
- retrieval_model_requests_made: `18`
- retriever_catalog_hides_actions: `True`
- teacher_predicate_repairs: `0`
- evaluation_teacher_case_overlap: `[]`
