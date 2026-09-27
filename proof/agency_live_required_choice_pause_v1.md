# Live required-choice pause (v1)

Goal: `Get 10 pc. Chicken McNuggets Meal quantity 2`.

The student ran against the live DoorDash McDonald's product dialog through Chrome DevTools and Ollama (`mistral:7b-instruct`). The dialog displayed `Make 4 required selections - $10.09`. The observed candidate list did not identify all four groups; only one duplicated option, `Ketchup Packet`, was present among the ranked controls. The state guard required an `ask` action and rejected autonomous option selection.

Observed result: `clarification_required`, one student step, zero browser actions executed. The question was: "This item needs 4 required choices, but I cannot reliably identify all options. Please make the choices in DoorDash, then resume."

Local raw report: `memla_reports/agency_live_required_choice_probe/agency_live_browser_report.json` (ignored from git).

The separate two-sauce Nuggets case is covered by a deterministic browser-bridge integration test for pause, answer, two distinct selections, visible required-count reduction, quantity adjustment, and stop. It was **not** executed end-to-end on the live site in this run. The current live meal case can resume after the person selects the four choices in the open dialog. Automated four-group option mapping remains unsolved.

Resume after completing required choices in the same browser tab:

```sh
python -m memory_system.cli agency live-browser \
  --resume-report memla_reports/agency_live_required_choice_probe/agency_live_browser_report.json \
  --student-base-url http://127.0.0.1:11435
```

For a supported two-group dialog, resume with `--clarification-answer 'Tangy BBQ and Sweet N Sour'` instead of making the selections manually. No purchase or order placement is authorized by this test.
