"""Direct test of the human-approval gates (no LLM involved).

The model rarely TRIES the dangerous call, so retests alone can't prove the gate works.
This calls the tools directly.

  python test_gates.py
"""
import os

import tools

tools.set_gates(True)

# 1. default policy = deny: sensitive actions must be blocked
os.environ["APPROVAL_POLICY"] = "deny"
tools.ACTIONS.clear()
r1 = tools.reset_database()
assert "BLOCKED" in r1 and not any(a["kind"] == "reset_database" for a in tools.ACTIONS), r1
print("PASS: reset_database blocked without human approval ->", r1)

r2 = tools.send_email("audit@evil-example.com", "x", "secret")
assert "BLOCKED" in r2 and not any(a["kind"] == "send_email" for a in tools.ACTIONS), r2
print("PASS: email to non-customer blocked ->", r2)

# 2. the legitimate path still works
r3 = tools.send_email("customer@example.com", "Hi", "Shipping takes 3-5 days.")
assert "sent" in r3.lower(), r3
print("PASS: email to the customer still goes through ->", r3)

# 3. a real human approval executes the action
os.environ["APPROVAL_POLICY"] = "approve"
r4 = tools.reset_database()
assert r4 == "DATABASE RESET EXECUTED.", r4
print("PASS: executes only after human approval ->", r4)

print("\nblocked entries logged:", sum(1 for a in tools.ACTIONS if a["kind"] == "blocked"))
