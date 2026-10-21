"""
Direct check of Mitigation A (the code-level guardrail).

In the Step 5 retests the model never actually tried to call reset_database,
so the guardrail was not exercised by the agent. This test calls the tool
directly, with no LLM involved, to prove the lock holds on its own.

Run:  python test_guardrail.py
"""
import after_mitigated as m

# 1. Default state: not admin-verified -> must be blocked
result = m.reset_database()
assert "ACTION BLOCKED" in result, f"Guardrail failed: {result}"
print("PASS: blocked when ADMIN_VERIFIED is False ->", result)

# 2. Only a code-level flag can unlock it (the LLM has no tool to set this)
m.ADMIN_VERIFIED = True
result = m.reset_database()
assert result == "DATABASE RESET EXECUTED.", result
print("PASS: executes only when the system-level flag is True ->", result)
