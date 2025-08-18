import os
import sys
import json
import csv
import argparse
from typing import Any, Dict, List, Optional


def _ensure_sindi_on_path():
    override = os.getenv("SINDI_REPO_ROOT")
    if override:
        sys.path.append(override)
        return
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root_guess = os.path.abspath(os.path.join(here, "..", ".."))
    sys.path.append(repo_root_guess)

_ensure_sindi_on_path()

import src.sindi.comparator as cp  
from src.sindi.comparator_light import ComparatorRulesOnly as LightComparator

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _get_pred(arg_list: Any, idx: int = 0) -> Optional[str]:
    """
    Safely return a string element from a list-like at index `idx`.
    """
    try:
        if isinstance(arg_list, (list, tuple)) and len(arg_list) > idx:
            val = arg_list[idx]
            return val if isinstance(val, str) else None
    except Exception:
        pass
    return None

def compare_pair(comparator, old_pred: Optional[str], new_pred: Optional[str]) -> str:
    if not old_pred or not new_pred:
        return "SKIPPED (predicate missing)"
    try:
        return comparator.compare(old_pred, new_pred)
    except Exception as e:
        return f"ERROR: {e}"

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Batch compare old vs new invariants using SInDi API.")
    ap.add_argument("-i", "--input", required=True, help="Path to JSON file (list of records).")
    ap.add_argument("-o", "--output", required=True, help="Path to output CSV.")
    ap.add_argument("--light", action="store_true", help="Use solver-free light comparator (if available).")
    ap.add_argument("--print-summary", action="store_true", help="Print a verdict histogram at the end.")
    args = ap.parse_args()

    # Choose comparator
    if args.light:
        if LightComparator is None:
            print("[warn] --light requested but light comparator not importable; falling back to full comparator.")
            comparator = cp.Comparator()
        else:
            comparator = LightComparator()
    else:
        comparator = cp.Comparator()

    # Load JSON
    with open(args.input, "r", encoding="utf-8") as f:
        try:
            records = json.load(f)
        except Exception as e:
            print(f"[error] Failed to parse JSON: {e}", file=sys.stderr)
            return 2

    # Prepare output CSV
    fieldnames = [
        "idx",
        "contract_pair",
        "function",
        "require_index",
        "cond_changed",
        "msg_changed",
        "old_predicate",
        "new_predicate",
        "verdict",
    ]
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    out_f = open(args.output, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    writer.writeheader()

    # Iterate
    verdict_counts: Dict[str, int] = {}
    for i, rec in enumerate(records):
        old_pred = _get_pred(rec.get("old_norm_args"))
        new_pred = _get_pred(rec.get("new_norm_args"))
        verdict = compare_pair(comparator, old_pred, new_pred)

        row = {
            "idx": i,
            "contract_pair": rec.get("contract_pair"),
            "function": rec.get("function"),
            "require_index": rec.get("require_index"),
            "cond_changed": rec.get("cond_changed"),
            "msg_changed": rec.get("msg_changed"),
            "old_predicate": old_pred,
            "new_predicate": new_pred,
            "verdict": verdict,
        }
        writer.writerow(row)

        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

    out_f.close()

    # Summary
    if args.print-summary:  # typo-safe fallback will be corrected just below
        pass
    # argparse stores "--print-summary" as "print_summary"
    if getattr(args, "print_summary", False):
        print("\nVerdict summary:")
        for k, v in sorted(verdict_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"{k:55s} {v}")

    print(f"\n[done] Wrote: {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())