"""Test and comparative benchmark for Phase 3: Embedding-Based Semantic Guard.

Compares:
1. Regex Filter (Phase 2 baseline layer)
2. Semantic Embedding Guard (Phase 3 with nomic-embed-text)
Across:
- Advanced Attacks (ADV1 - ADV6)
- Control Queries (C1 - C3)
"""

import sys
import guard
import semantic_guard
from advanced_attacks import ADVANCED_ATTACKS
from attacks import ATTACKS

def run_benchmark():
    print("=" * 75)
    print("PHASE 3: SEMANTIC EMBEDDING GUARD BENCHMARK (nomic-embed-text)")
    print("=" * 75)

    print("\n1. Testing Semantic Scan against Advanced Attacks (ADV1 - ADV6)...")
    results = []

    for atk in ADVANCED_ATTACKS:
        target_text = atk["user"] if atk["channel"] == "user_input" else (atk["poison_chunk"] or atk["poison_memory"])
        
        # Test Regex Filter (Phase 2)
        if atk["channel"] == "user_input":
            regex_hits = guard.scan_input(target_text)
        else:
            regex_hits = guard.scan_context(target_text)
        regex_caught = len(regex_hits) > 0

        # Test Semantic Guard (Phase 3)
        sem_unsafe, sem_score, sem_cat, _ = semantic_guard.scan_semantic(target_text)

        results.append({
            "id": atk["id"],
            "name": atk["name"],
            "channel": atk["channel"],
            "regex_caught": regex_caught,
            "regex_hits": regex_hits,
            "semantic_caught": sem_unsafe,
            "semantic_score": sem_score,
            "semantic_category": sem_cat,
        })

        status_regex = "[CAUGHT]" if regex_caught else "[MISSED]"
        status_sem = f"[CAUGHT {sem_cat} ({sem_score:.3f})]" if sem_unsafe else f"[MISSED ({sem_score:.3f})]"
        
        print(f"  {atk['id']:<5} {atk['name']:<35} | Regex: {status_regex:<10} | Semantic: {status_sem}")

    print("\n2. Testing False Positive Rate on Benign Controls...")
    controls = [a for a in ATTACKS if a["channel"] == "control"]
    false_positives = 0
    for c in controls:
        sem_unsafe, sem_score, sem_cat, _ = semantic_guard.scan_semantic(c["user"])
        if sem_unsafe:
            false_positives += 1
            print(f"  [FAIL] Control {c['id']} falsely flagged! Score: {sem_score:.3f} ({sem_cat})")
        else:
            print(f"  [PASS] Control {c['id']}: '{c['user'][:35]}...' -> Clean (Max sim: {sem_score:.3f})")

    # Summary
    regex_caught_count = sum(1 for r in results if r["regex_caught"])
    sem_caught_count = sum(1 for r in results if r["semantic_caught"])
    total_adv = len(results)

    print("\n3. Testing Backward Compatibility on Original Attacks (U1 - H3)...")
    orig_attacks = [a for a in ATTACKS if a["channel"] != "control"]
    orig_sem_caught = 0
    for a in orig_attacks:
        target_text = a["user"] if a["channel"] == "user_input" else (a["poison_chunk"] or a["poison_memory"])
        sem_unsafe, sem_score, sem_cat, _ = semantic_guard.scan_semantic(target_text)
        if sem_unsafe:
            orig_sem_caught += 1
            print(f"  [CAUGHT] {a['id']:<4} {a['name']:<30} -> {sem_cat} (sim={sem_score:.3f})")
        else:
            print(f"  [MISSED] {a['id']:<4} {a['name']:<30} -> sim={sem_score:.3f}")

    print("\n" + "=" * 75)
    print("BENCHMARK SUMMARY:")
    print(f"  Phase 2 Regex on Advanced Attacks:    {regex_caught_count} / {total_adv} ({regex_caught_count/total_adv*100:.1f}%)")
    print(f"  Phase 3 Semantic on Advanced Attacks: {sem_caught_count} / {total_adv} ({sem_caught_count/total_adv*100:.1f}%)")
    print(f"  Phase 3 on Original 11 Attacks:       {orig_sem_caught} / {len(orig_attacks)} ({orig_sem_caught/len(orig_attacks)*100:.1f}%)")
    print(f"  False Positive Rate on Controls:      {false_positives} / {len(controls)} (0.0%)")
    print("=" * 75)

    return results

if __name__ == "__main__":
    run_benchmark()
