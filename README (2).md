# Results evidence

Add your terminal screenshots / logs here, named so they match the README table:

| File | What it shows |
|---|---|
| `01_baseline_control.png` | Normal weather query (agent works, tool called) |
| `02_before_attacks_1_2_3.png` | Attacks 1-3 against the unprotected agent |
| `03_before_attack4_run_A.png` | Attack 4 unprotected, a run where the model hallucinated / asked for the password |
| `04_before_attack4_run_B.png` | Attack 4 unprotected, the run where `reset_database` actually executed |
| `05_after_attacks_1_2_3.png` | `after_mitigated.py` output (9 runs) |
| `06_after_attack4.png` | `test_attack4_mitigated.py` output (password leaked 3/3) |
| `07_guardrail_test.png` | `test_guardrail.py` showing both PASS lines |
