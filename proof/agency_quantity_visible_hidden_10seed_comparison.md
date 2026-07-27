# Agency Quantity Visible/Hidden 10-Seed Comparison

- Student model: `mistral:7b-instruct`
- Cases: 11
- Seeds per case: 10
- Max steps: 4
- Holdout hash: `6ea061bc2126131947a7f7ab696e909407e25986dcc4a2c1446a95c4ef8fca39`
- Train hash: `814ce121c1d4d1e1d16edb92b1cf5575706b1bd2ab170267c71bbfd60f86a986`
- Micro-fortress hash: `19916317a909a0ac3c46611757b1cc60f94b9fb79c01bbee43b7709fbd354ba8`

## Headline

| Suite | Raw | Full Rule | Delta | Parsed/Attempts | Candidate Metadata |
| --- | ---: | ---: | ---: | --- | --- |
| visible | 62 | 86 | 24 | 536/546 | True |
| hidden | 73 | 90 | 17 | 521/547 | False |

## Paired Discordance

| Suite | Lane | Raw Only | Lane Only | p |
| --- | --- | ---: | ---: | ---: |
| visible | full_rich_rule | 3 | 27 | 8e-06 |
| visible | condition_action_policy | 2 | 28 | 1e-06 |
| visible | seeded_full_rule | 3 | 28 | 5e-06 |
| hidden | full_rich_rule | 0 | 17 | 1.5e-05 |
| hidden | condition_action_policy | 16 | 12 | 0.571588 |
| hidden | seeded_full_rule | 0 | 17 | 1.5e-05 |

## Live NVIDIA

- Attempted: `True`
- Status: `blocked_401_unauthorized`
- Student evaluation run: `False`
- Candidate rule from NVIDIA response: `False`

## Constraint Families

See JSON for case-clustered Wilson intervals and constraint-family summaries.
