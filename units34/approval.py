"""Human approval for sensitive actions.

  APPROVAL_POLICY=deny         (default, for automated experiments: always refuses)
  APPROVAL_POLICY=interactive  (demo: asks a real human at the terminal)
  APPROVAL_POLICY=approve      (only for testing that an approved action does execute)
"""
import os


def request_approval(action, details):
    policy = os.environ.get("APPROVAL_POLICY", "deny")
    if policy == "approve":
        return True
    if policy == "interactive":
        answer = input(f"\n[HUMAN APPROVAL NEEDED] Allow {action} {details}? (y/n): ")
        return answer.strip().lower() == "y"
    return False
