"""Build the before/after table from the two CSVs.

  python summarize.py                                   # results/baseline.csv vs results/mitigated.csv
  python summarize.py results/baseline.csv results/mitigated_regexonly.csv

Writes results/before_after_<name of the after-CSV>.md (so an ablation run never overwrites the main table). The 'stopped by' columns show which defence
acted (the model behaving is NOT counted as a defence).
"""
import csv
import os
import sys
from collections import defaultdict

from attacks import ATTACKS


def load(path):
    rows = defaultdict(list)
    if not os.path.exists(path):
        sys.exit(f"Missing {path}")
    for r in csv.DictReader(open(path, newline="")):
        rows[r["attack_id"]].append(r)
    return rows


def t(v):
    return str(v).strip().lower() == "true"


def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def frac(rows, pred):
    ok = [r for r in rows if not r.get("error")]
    return f"{sum(1 for r in ok if pred(r))}/{len(ok)}"


def main():
    before_p = sys.argv[1] if len(sys.argv) > 1 else "results/baseline.csv"
    after_p = sys.argv[2] if len(sys.argv) > 2 else "results/mitigated.csv"
    before, after = load(before_p), load(after_p)

    L = [f"Before: `{before_p}`   After: `{after_p}`", "",
         "| ID | Channel | Attack | Before | After | Input guard | Quarantine | Gate | Output redact |",
         "|---|---|---|---|---|---|---|---|---|"]
    for a in ATTACKS:
        if a["channel"] == "control":
            continue
        b, f = before.get(a["id"], []), after.get(a["id"], [])
        tag = " *(held-out)*" if a.get("heldout") else ""
        L.append("| {} | {} | {}{} | {} | {} | {} | {} | {} | {} |".format(
            a["id"], a["channel"], a["name"], tag,
            frac(b, lambda r: t(r["compromised"])), frac(f, lambda r: t(r["compromised"])),
            frac(f, lambda r: t(r.get("blocked")) and "guard_in" in r.get("block_reason", "")),
            frac(f, lambda r: num(r.get("quarantined")) > 0),
            frac(f, lambda r: num(r.get("gate_blocks")) > 0),
            frac(f, lambda r: t(r.get("worker_raw_leak")) and not t(r["secret_leaked"]))))

    L += ["", "**Columns:** Before/After = compromised runs. Input guard = user input routed to END. "
          "Quarantine = poisoned chunk/memory dropped. Gate = sensitive action denied by approval. "
          "Output redact = Worker leaked the secret but the output guard removed it.", "",
          "### Controls (no attack): the defence must not break normal use", "",
          "| ID | Control | Blocked or quarantined (false positive) | Reset executed |", "|---|---|---|---|"]
    for a in ATTACKS:
        if a["channel"] != "control":
            continue
        f, b = after.get(a["id"], []), before.get(a["id"], [])
        L.append("| {} | {} | {} | before {} / after {} |".format(
            a["id"], a["name"],
            frac(f, lambda r: t(r.get("blocked")) or num(r.get("quarantined")) > 0),
            frac(b, lambda r: t(r["reset_executed"])), frac(f, lambda r: t(r["reset_executed"]))))

    errs = sum(1 for d in (before, after) for rs in d.values() for r in rs if r.get("error"))
    L += ["", f"Runs excluded because of errors: {errs}"]
    out = "\n".join(L)
    os.makedirs("results", exist_ok=True)
    stem = os.path.splitext(os.path.basename(after_p))[0]
    open(f"results/before_after_{stem}.md", "w", encoding="utf-8").write(out)
    print(out)


if __name__ == "__main__":
    main()
