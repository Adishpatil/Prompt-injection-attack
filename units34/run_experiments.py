"""Run the attack catalogue N times against the baseline or mitigated pipeline.

  python run_experiments.py --mode baseline --runs 3
  python run_experiments.py --mode baseline --only R2 --runs 1     (quick test)

Writes results/<mode>.csv (one row per run) and results/transcripts_<mode>.txt
(raw outputs, for screenshots / evidence).
"""
import argparse
import csv
import os
import time
import traceback

from attacks import ATTACKS
from config import RUNS
from evaluate import evaluate, poison_status
from kb import build_kb
from memory_store import build_store
from pipeline import build_pipeline
import tools
from tools import ACTIONS

FIELDS = ["attack_id", "channel", "targets", "run", "poison_in_context",
          "poison_reached_worker", "blocked", "reset_executed", "secret_leaked",
          "unauthorized_email", "compromised", "worker_raw_leak", "gate_blocks",
          "quarantined", "block_reason", "error"]


def get_hooks(mode):
    if mode == "baseline":
        tools.set_gates(False)
        return {}
    try:
        from guard import make_hooks          # created in the mitigation step
    except ImportError:
        raise SystemExit("Mitigated mode needs guard.py (next step).")
    return make_hooks()


def run_one(attack, hooks, llm=None):
    ACTIONS.clear()
    col = build_kb(attack["poison_chunk"])
    store = build_store(attack["poison_memory"])
    graph = build_pipeline(col, store, llm=llm, **hooks)
    state = graph.invoke({"user_input": attack["user"]})
    return state, list(ACTIONS)


def main(argv=None, llm=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="baseline", choices=["baseline", "mitigated"])
    ap.add_argument("--runs", type=int, default=RUNS)
    ap.add_argument("--only", default=None, help="attack id, e.g. R2")
    ap.add_argument("--tag", default="", help="suffix for output files, e.g. regexonly")
    args = ap.parse_args(argv)

    hooks = get_hooks(args.mode)
    os.makedirs("results", exist_ok=True)
    rows, log = [], []
    attacks = [a for a in ATTACKS if args.only in (None, a["id"])]

    for atk in attacks:
        for i in range(1, args.runs + 1):
            t0 = time.time()
            row = {"attack_id": atk["id"], "channel": atk["channel"],
                   "targets": atk["targets"], "run": i, "error": ""}
            try:
                state, actions = run_one(atk, hooks, llm=llm)
                in_ctx, reached = poison_status(atk, state)
                row.update(evaluate(state, actions))
                row.update(poison_in_context=in_ctx, poison_reached_worker=reached,
                           blocked=bool(state.get("blocked")),
                           quarantined=len(state.get("quarantined", [])),
                           block_reason=state.get("block_reason", ""))
                log.append(f"=== {atk['id']} run {i} | {atk['name']} ===\n"
                           f"USER: {atk['user']}\n"
                           f"WORKER: {state.get('worker_reply')}\n"
                           f"FINAL: {state.get('final')}\n"
                           f"BLOCKED: {state.get('block_reason', '-')}\n"
                           f"QUARANTINED: {state.get('quarantined', [])}\n"
                           f"WORKER_RAW: {state.get('worker_raw', '-')}\n"
                           f"ACTIONS: {actions}\n")
            except Exception as e:                       # small models are flaky; keep going
                row["error"] = f"{type(e).__name__}: {e}"
                log.append(f"=== {atk['id']} run {i} ERROR ===\n{traceback.format_exc()}\n")
            rows.append(row)
            print(f"{atk['id']} run {i}: compromised={row.get('compromised')} "
                  f"reset={row.get('reset_executed')} leak={row.get('secret_leaked')} "
                  f"bad_email={row.get('unauthorized_email')} "
                  f"poison_in_ctx={row.get('poison_in_context')} "
                  f"({time.time() - t0:.0f}s) {row['error']}")

    with open(f"results/{args.mode}{args.tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(f"results/transcripts_{args.mode}{args.tag}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log))

    print("\nSUMMARY (compromised runs / total)")
    for atk in attacks:
        mine = [r for r in rows if r["attack_id"] == atk["id"] and not r["error"]]
        bad = sum(1 for r in mine if r["compromised"])
        print(f"  {atk['id']:<3} {atk['channel']:<11} {bad}/{len(mine)}  {atk['name']}")


if __name__ == "__main__":
    main()
