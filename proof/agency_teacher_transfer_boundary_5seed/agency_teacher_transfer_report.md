# Agency Teacher Transfer Proof

- Teacher: `qwen2.5:32b`
- Student: `mistral:7b-instruct`
- Holdouts: `5`
- Trials per holdout: `5`
- Teacher calls in student lanes: `0`
- Teacher calls this run: `0`

## Lane Results

| Lane | Success |
| --- | ---: |
| minimal_family_frame | 0 |
| raw | 0 |
| teacher_executable_capsule | 23 |
| teacher_executable_counterfactual | 1 |
| teacher_rule | 6 |

## Family Results

| Family | Lane | Success | Trials |
| --- | --- | ---: | ---: |
| missing_affordance_boundary_stop | raw | 0 | 25 |
| missing_affordance_boundary_stop | minimal_family_frame | 0 | 25 |
| missing_affordance_boundary_stop | teacher_rule | 6 | 25 |
| missing_affordance_boundary_stop | teacher_executable_capsule | 23 | 25 |
| missing_affordance_boundary_stop | teacher_executable_counterfactual | 1 | 25 |

## Case-Cluster Comparison

Seeds are repeated trials within cases; the case-level comparison is the independent transfer summary.

| Lane | Case wins | Losses | Ties | Exact p |
| --- | ---: | ---: | ---: | ---: |
| minimal_family_frame | 0 | 0 | 5 | 1.0 |
| teacher_rule | 2 | 0 | 3 | 0.5 |
| teacher_executable_capsule | 5 | 0 | 0 | 0.0625 |
| teacher_executable_counterfactual | 1 | 0 | 4 | 1.0 |

## Authenticity

- deterministic_policy_selected_student_actions: `False`
- frozen_holdout_hash: `0923c6e8e67c4460d6280d8b1cc2775840d1c60a6cdb7dbad5deee2e1617c4e3`
- hidden_oracle_leaks: `0`
- holdouts_frozen_before_teacher: `True`
- prompt_difference_is_bank_packet_only: `True`
- prompt_difference_mismatches: `0`
- student_request_errors: `0`
- student_responses_parsed: `106`
- teacher_saw_train_only: `True`
- teacher_train_clearance: `{'train_alias_pizza_pie': True, 'train_missing_quantity_affordance': True}`

## Teacher Rules

```json
{
  "alias_numeric_role_grounding": {
    "action_type": "tap",
    "comparison": "observed_quantity < intent.quantity",
    "family": "alias_numeric_role_grounding",
    "observations": [
      "visible_text contains item name with alias",
      "observed_quantity is less than intent.quantity"
    ],
    "postcondition": "observed_quantity equals intent.quantity",
    "reject": [
      "actions that do not increase quantity"
    ],
    "stop_condition": "observed_quantity equals intent.quantity",
    "target_selector": "Increase quantity action for the item"
  },
  "missing_affordance_boundary_stop": {
    "action_type": "stop",
    "comparison": "no action to increase quantity",
    "family": "missing_affordance_boundary_stop",
    "observations": [
      "visible_text contains item name",
      "observed_quantity is less than intent.quantity",
      "no candidate action to increase quantity"
    ],
    "postcondition": "stop before payment",
    "reject": [
      "actions that do not stop the process"
    ],
    "stop_condition": "no action to increase quantity",
    "target_selector": "none"
  }
}
```
